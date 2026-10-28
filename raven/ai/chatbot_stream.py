import asyncio
import dataclasses
import functools
import re
import time
from pathlib import Path

import frappe
from agents import Agent, Runner
from frappe import _
from openai.types.responses import ResponseTextDeltaEvent
from openai.types.shared import Reasoning

from raven.ai.agents_integration import RavenAgentManager
from raven.ai.chatbot_models import ChatbotChoice
from raven.ai.harness.action_log_hooks import ActionLogHooks
from raven.ai.harness.data_tools import data_tools
from raven.ai.harness.document_tools import document_tools
from raven.ai.harness.progress import harness_status
from raven.ai.manual_sources import ManualSource, configured_sources
from raven.ai.manual_tools import manual_status, manual_tools

FLUSH_INTERVAL_SECONDS = 0.1
# The assistant works in a loop until the task is done; these only stop a loop that never ends.
MAX_TURNS = 40
SPECIALIST_MAX_TURNS = 25
# The data and document assistants look things up with tools; thinking long about each step only makes them slow.
SPECIALIST_EFFORT = "low"

PROMPTS = Path(__file__).parent / "prompts"
ASSISTANT_PROMPT_PATH = PROMPTS / "chatbot_assistant.md"
MANUAL_PROMPT_PATH = PROMPTS / "manual_assistant.md"
DATA_PROMPT_PATH = PROMPTS / "data_assistant.md"
DOCUMENT_PROMPT_PATH = PROMPTS / "document_assistant.md"
MANUAL_TOOL_NAME = "manual_assistant"
MANUAL_TOOL_DESCRIPTION = (
	"Researches how the company's ERPNext system works and how its UAT tests are done, by searching and reading the official manuals "
	"as many times as it takes. Give it the user's whole question (and what they already tried). It returns the answer with links to the pages."
)
DATA_TOOL_NAME = "data_assistant"
DATA_TOOL_DESCRIPTION = (
	"Checks the company's data and makes reports, read-only and with the user's own permissions: finds missing values and duplicates, "
	"counts, lists and reads documents, runs reports. Give it the whole question. It returns the findings with the document names."
)
DOCUMENT_TOOL_NAME = "document_assistant"
DOCUMENT_TOOL_DESCRIPTION = (
	"Works on documents for the user: checks values the way saving would, saves drafts, opens a filled form, and submits, cancels, deletes "
	"or updates documents. It can also check data. Give it the whole task in one call, including finding the documents; it looks them up itself."
)
HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)


@functools.cache
def default_instruction() -> str:
	"""The built-in assistant instruction (prompts/chatbot_assistant.md) without its maintainer comments."""
	return HTML_COMMENT.sub("", ASSISTANT_PROMPT_PATH.read_text(encoding="utf-8")).strip()


def current_context() -> str:
	"""Facts that differ per request. Appended after the fixed instruction so the fixed part stays identical
	for every user, which lets OpenAI's prompt caching reuse it."""
	lines = [
		f"- Today: {frappe.utils.getdate().strftime('%A, %d %B %Y')}",
		f"- You are talking to: {frappe.utils.get_fullname(frappe.session.user)} ({frappe.session.user})",
	]
	if company := frappe.defaults.get_user_default("company") or frappe.defaults.get_global_default("company"):
		lines.append(f"- Their default company: {company}")
	return "# Current context\n\n" + "\n".join(lines)


def build_instruction() -> str:
	"""The orchestrator's instruction: the admin's replacement from Raven Settings if set, else the built-in one."""
	base = frappe.get_cached_doc("Raven Settings").chatbot_instruction or default_instruction()
	return f"{base.strip()}\n\n{current_context()}"


class DeltaPublisher:
	"""Sends the chatbot's text to the asking user's browser in small batches, not one event per token."""

	def __init__(self, chat: str):
		self.chat = chat
		self.buffer = ""
		self.last_flush = 0.0

	def add(self, text: str):
		self.buffer += text
		if time.monotonic() - self.last_flush >= FLUSH_INTERVAL_SECONDS:
			self.flush()

	def flush(self):
		if self.buffer:
			frappe.publish_realtime("chatbot_delta", {"chat": self.chat, "text": self.buffer}, user=frappe.session.user)
			self.buffer = ""
		self.last_flush = time.monotonic()

	def status(self, text: str):
		"""A short progress line, e.g. which specialist is being asked."""
		frappe.publish_realtime("chatbot_status", {"chat": self.chat, "text": text}, user=frappe.session.user)


def tool_name_for(bot_name: str) -> str:
	return re.sub(r"[^a-zA-Z0-9_-]+", "_", bot_name).strip("_")[:64]


def working_agent(name: str, instruction: str, choice: ChatbotChoice) -> Agent:
	"""An agent for the chosen model, made like every Raven bot (provider, model settings) from an unsaved Raven Bot.
	It may call several tools in one step, and thinks as hard as the user chose."""
	bot = frappe.get_doc(
		{
			"doctype": "Raven Bot",
			"bot_name": name,
			"is_ai_bot": 1,
			"model_provider": "OpenAI",
			"model": choice.model,
			"instruction": instruction,
		}
	)
	agent = RavenAgentManager(bot).create_agent()
	settings = {"parallel_tool_calls": True}
	if choice.effort:
		settings["reasoning"] = Reasoning(effort=choice.effort)
	agent.model_settings = dataclasses.replace(agent.model_settings, **settings)
	return agent


@functools.cache
def manual_instruction() -> str:
	return HTML_COMMENT.sub("", MANUAL_PROMPT_PATH.read_text(encoding="utf-8")).strip()


def tool_status(tool_name: str, arguments: str) -> str | None:
	return manual_status(tool_name, arguments) or harness_status(tool_name, arguments)


def progress_reporter(publisher: "DeltaPublisher | None"):
	"""A stream handler for a specialist: shows each tool it starts as a line in the chat."""

	async def show_progress(event):
		inner = event["event"]
		if publisher and inner.type == "run_item_stream_event" and inner.item.type == "tool_call_item":
			raw = inner.item.raw_item
			if line := tool_status(getattr(raw, "name", ""), getattr(raw, "arguments", "")):
				publisher.status(line)

	return show_progress


def manual_assistant_tool(
	sources: list[ManualSource], choice: ChatbotChoice, publisher: "DeltaPublisher | None" = None, hooks: ActionLogHooks | None = None
):
	"""The researcher: its own agent with the manual tools, called by the orchestrator like a specialist. Reading pages happens
	in its context, not the orchestrator's, and only the answer comes back."""
	listing = "\n".join(f"- {source.name}: {source.description}" for source in sources)
	agent = working_agent("Manual Assistant", f"{manual_instruction()}\n\n# Sources\n\n{listing}", ChatbotChoice(choice.model, None))
	agent.tools = [*agent.tools, *manual_tools(sources)]
	return agent.as_tool(
		tool_name=MANUAL_TOOL_NAME,
		tool_description=MANUAL_TOOL_DESCRIPTION,
		max_turns=SPECIALIST_MAX_TURNS,
		on_stream=progress_reporter(publisher),
		hooks=hooks,
	)


def harness_tools(access: str, chat: str | None) -> list:
	"""The data tools a Raven Bot's "Chatbot Data Access" level gives; the document tools include the data tools."""
	if access == "Check data and prepare documents":
		return [*data_tools(), *document_tools(chat)]
	return data_tools() if access == "Check data" else []


def harness_assistant_tool(name: str, prompt_path: Path, access: str, description: str, choice, publisher, hooks):
	"""An assistant agent with the data (and document) tools, called by the orchestrator like a specialist."""
	agent = working_agent(name, HTML_COMMENT.sub("", prompt_path.read_text(encoding="utf-8")).strip(), ChatbotChoice(choice.model, SPECIALIST_EFFORT))
	agent.tools = [*agent.tools, *harness_tools(access, publisher.chat if publisher else None)]
	return agent.as_tool(tool_name=tool_name_for(name).lower(), tool_description=description, max_turns=SPECIALIST_MAX_TURNS, hooks=hooks, on_stream=progress_reporter(publisher))


def specialist_tools(
	choice: ChatbotChoice, publisher: "DeltaPublisher | None" = None, hooks: ActionLogHooks | None = None
) -> tuple[list, dict[str, str]]:
	"""The tools of the orchestrator: every agent marked "Available to the Chatbot", and the manual assistant when a manual
	source is set up. Also tool name → agent name, for status lines."""
	tools, names = [], {}
	for bot in frappe.get_all(
		"Raven Bot", filters={"is_ai_bot": 1, "allow_orchestrator_to_call": 1}, fields=["name", "description"]
	):
		name = tool_name_for(bot.name)
		doc = frappe.get_doc("Raven Bot", bot.name)
		agent = RavenAgentManager(doc).create_agent()
		agent.tools = [*agent.tools, *harness_tools(doc.chatbot_data_access, publisher.chat if publisher else None)]
		tools.append(agent.as_tool(tool_name=name, tool_description=bot.description, max_turns=SPECIALIST_MAX_TURNS, hooks=hooks, on_stream=progress_reporter(publisher)))
		names[name] = bot.name
	if sources := configured_sources():
		tools.append(manual_assistant_tool(sources, choice, publisher, hooks))
		names[MANUAL_TOOL_NAME] = _("the manuals")
	settings = frappe.get_cached_doc("Raven Settings")
	if settings.chatbot_data_assistant:
		tools.append(harness_assistant_tool("Data Assistant", DATA_PROMPT_PATH, "Check data", DATA_TOOL_DESCRIPTION, choice, publisher, hooks))
		names[DATA_TOOL_NAME] = _("the data")
	if settings.chatbot_document_assistant:
		tools.append(harness_assistant_tool("Document Assistant", DOCUMENT_PROMPT_PATH, "Check data and prepare documents", DOCUMENT_TOOL_DESCRIPTION, choice, publisher, hooks))
		names[DOCUMENT_TOOL_NAME] = _("the documents")
	return tools, names


def build_orchestrator(
	choice: ChatbotChoice, publisher: "DeltaPublisher | None" = None, hooks: ActionLogHooks | None = None
) -> tuple[Agent, dict[str, str]]:
	"""The central agent: Raven Settings' model and instruction, with the specialists as its tools."""
	agent = working_agent("Raven AI", build_instruction(), choice)
	tools, names = specialist_tools(choice, publisher, hooks)
	agent.tools = [*agent.tools, *tools]
	return agent, names


def _input_items(prompt: str, history: list[dict]) -> list[dict]:
	return [*({"role": item["role"], "content": item["content"]} for item in history if item["content"]), {"role": "user", "content": prompt}]


def _status_for(event, specialists: dict[str, str]) -> str | None:
	"""A progress line when the orchestrator starts calling one of its specialists."""
	if event.type != "run_item_stream_event" or event.item.type != "tool_call_item":
		return None
	name = getattr(event.item.raw_item, "name", None)
	return _("Asking {0}…").format(specialists[name]) if name in specialists else None


async def _run_streamed(prompt: str, history: list[dict], publisher: DeltaPublisher, choice: ChatbotChoice) -> str:
	hooks = ActionLogHooks(publisher.chat, choice.effort)
	agent, specialists = build_orchestrator(choice, publisher, hooks)
	result = Runner.run_streamed(agent, _input_items(prompt, history), max_turns=MAX_TURNS, hooks=hooks)
	try:
		async for event in result.stream_events():
			if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
				publisher.add(event.data.delta)
			elif status := _status_for(event, specialists):
				publisher.status(status)
	finally:
		hooks.flush()
	return result.final_output or ""


def stream_reply(prompt: str, history: list[dict], publisher: DeltaPublisher, choice: ChatbotChoice) -> str:
	"""Run the orchestrator, publishing its text as it is written; returns the whole answer."""
	answer = asyncio.run(_run_streamed(prompt, history, publisher, choice))
	publisher.flush()
	return answer
