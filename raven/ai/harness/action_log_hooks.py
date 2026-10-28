"""Records every model call and tool call of one answer, with the technical numbers needed to see where tokens and time go
(tokens by kind, size of what was sent, duration, errors). The rows are kept in memory while the AI works and saved together
at the end by `flush`, so logging never competes with the tools for the database connection."""

import json
import time

import frappe
from agents import RunHooks

from raven.raven_ai.doctype.raven_ai_action_log.raven_ai_action_log import RavenAIActionLog


def milliseconds_since(started: float) -> int:
	return int((time.monotonic() - started) * 1000)


class ActionLogHooks(RunHooks):
	"""Pass to the top-level run and to every `as_tool`, so the work of specialists is recorded too."""

	def __init__(self, chat: str, effort: str | None):
		self.common = {"run": frappe.generate_hash(length=12), "chat": chat, "effort": effort or ""}
		self.rows: list[dict] = []
		self.started: dict = {}

	async def on_llm_start(self, context, agent, system_prompt, input_items):
		request = {"request_chars": len(system_prompt or "") + len(json.dumps(input_items, default=str)), "input_items": len(input_items)}
		self.started[id(context)] = (time.monotonic(), request)

	async def on_llm_end(self, context, agent, response):
		started, request = self.started.pop(id(context), (time.monotonic(), {}))
		usage = response.usage
		self.rows.append(
			{
				**self.common,
				**request,
				"kind": "Model call",
				"agent": agent.name,
				"target": getattr(agent.model, "model", None) or str(agent.model),
				"outcome": "Done",
				"duration_ms": milliseconds_since(started),
				"input_tokens": usage.input_tokens,
				"cached_input_tokens": usage.input_tokens_details.cached_tokens,
				"output_tokens": usage.output_tokens,
				"reasoning_tokens": usage.output_tokens_details.reasoning_tokens,
				"response_id": response.response_id,
			}
		)

	async def on_tool_start(self, context, agent, tool):
		self.started[context.tool_call_id] = time.monotonic()

	async def on_tool_end(self, context, agent, tool, result):
		text = str(result)
		failed = text.startswith('{"error"')
		self.rows.append(
			{
				**self.common,
				"kind": "Tool call",
				"agent": agent.name,
				"target": tool.name,
				"outcome": "Failed" if failed else "Done",
				"duration_ms": milliseconds_since(self.started.pop(context.tool_call_id, time.monotonic())),
				"arguments": context.tool_arguments,
				"result_chars": len(text),
				"detail": text[:300] if failed else None,
				"tool_call_id": context.tool_call_id,
			}
		)

	def flush(self):
		RavenAIActionLog.record_all(self.rows)
		self.rows = []
