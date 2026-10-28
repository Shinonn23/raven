"""The name of a chat is written by the AI from its first message, and saved together with the first answer."""

import asyncio

import frappe
from agents import Runner
from frappe import _

from raven.ai.chatbot_models import ChatbotChoice
from raven.ai.chatbot_stream import working_agent

MAX_LENGTH = 60
FALLBACK_LENGTH = 40
INSTRUCTION = (
	"You name chats. Given the first message of a chat, reply with a title for it: at most six words, in the language of the message, "
	"naming the subject. No quotes, no ending punctuation, nothing else."
)


def placeholder() -> str:
	"""The title a chat has until the AI has named it."""
	return _("New chat")


def suggest_title(text: str, model: str) -> str:
	"""The AI's title for a chat that starts with `text`."""
	agent = working_agent("Chat Namer", INSTRUCTION, ChatbotChoice(model, "low"))
	result = asyncio.run(Runner.run(agent, text[:2000], max_turns=2))
	return " ".join(str(result.final_output or "").split()).strip("\"'“”‘’ .")[:MAX_LENGTH]


def title_for(text: str, model: str) -> str:
	"""The title of a chat that starts with `text`. If the AI cannot name it, the question is the title."""
	try:
		title = suggest_title(text, model)
	except Exception:
		frappe.log_error(title="Chatbot could not name a chat")
		title = ""
	return title or " ".join(text.split())[:FALLBACK_LENGTH]
