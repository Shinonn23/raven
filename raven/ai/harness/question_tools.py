"""The AI asks the user questions when it is not sure. They show as one card: each question with choices (one or several) and a place to
type any other answer, and the user sends all the answers at once. The answers come back as the user's next message, so the AI carries
on with the whole conversation in front of it."""

import json

import frappe
from agents import FunctionTool, function_tool

from raven.ai.harness.data_tools import answer
from raven.ai.harness.document_tools import message_count

MAX_QUESTIONS = 4
MAX_OPTIONS = 6
WAITING = {
	"state": "the questions are shown to the user",
	"next": "Stop here and wait: their answers arrive as their next message. Do not guess, and do not ask them again.",
}


def clean(questions: list[dict]) -> list[dict]:
	"""Each question with its short choices; a question without text is dropped."""
	cleaned = []
	for item in questions[:MAX_QUESTIONS]:
		text = str(item.get("question", "")).strip()
		options = [str(option).strip() for option in item.get("options") or [] if str(option).strip()][:MAX_OPTIONS]
		if text:
			cleaned.append({"question": text, "options": options, "multiple": bool(item.get("multiple"))})
	return cleaned


def ask(chat: str | None, questions: list[dict]) -> dict:
	"""Put the questions in the chat, once: asking the same again while they wait reuses the card."""
	questions = clean(questions)
	if not questions:
		frappe.throw("Give at least one question.")
	request = {"chat": chat, "message_position": message_count(chat), "questions": json.dumps(questions, ensure_ascii=False)}
	if not frappe.db.exists("Raven AI Question", {**request, "status": "Pending"}):
		frappe.get_doc({"doctype": "Raven AI Question", **request}).insert()
	return WAITING


def question_tool(chat: str | None) -> FunctionTool:
	@function_tool(
		strict_mode=False,
		name_override="ask_user",
		description_override=(
			"Ask the user to decide when you are not sure and a wrong guess would matter: which field, which document, which person, which "
			f"meaning. `questions` is a list of up to {MAX_QUESTIONS}, each {{question, options: 2 to {MAX_OPTIONS} short likely choices, "
			"multiple: true if several may be picked}. Ask everything you need in one call. The user can also type their own answer to each. "
			"Do not ask what you can find out with your tools."
		),
	)
	def ask_user(questions: list[dict]) -> str:
		return answer(lambda: ask(chat, questions))

	return ask_user
