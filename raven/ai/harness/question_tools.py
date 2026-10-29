"""The AI asks the user questions when it is not sure. They show as one card: each question with choices (one or several) and a place to
type any other answer, and the user sends all the answers at once. The answers come back as the user's next message, so the AI carries
on with the whole conversation in front of it."""

import json

import frappe
from agents import FunctionTool, function_tool

from raven.ai.harness.data_tools import answer
from raven.ai.harness.document_tools import message_count

MAX_QUESTIONS = 3
MAX_OPTIONS = 6
MAX_DESCRIPTION = 200
MAX_PREVIEW = 2000
# A "choice" that only tells the user to type something is not a choice: the question is then a text box.
FILL_IN_PREFIXES = ("ระบุ", "พิมพ์", "กรอก", "อื่นๆ", "อื่น ๆ", "specify", "type ", "enter ", "other", "write ")
WAITING = {
	"state": "the questions are shown to the user",
	"next": "Stop here and wait: their answers arrive as their next message. Do not guess, and do not ask them again.",
}


def clean_option(option) -> dict | None:
	"""A choice as {label, description?, preview?}: a plain string is just a label. A choice without a label is dropped."""
	if not isinstance(option, dict):
		option = {"label": option}
	label = str(option.get("label") or "").strip()
	if not label or label.lower().startswith(FILL_IN_PREFIXES):
		return None
	extras = {"description": str(option.get("description") or "").strip()[:MAX_DESCRIPTION], "preview": str(option.get("preview") or "").strip()[:MAX_PREVIEW]}
	return {"label": label, **{key: value for key, value in extras.items() if value}}


def clean(questions: list[dict]) -> list[dict]:
	"""Each question with its short choices; a question without text is dropped."""
	cleaned = []
	for item in questions[:MAX_QUESTIONS]:
		text = str(item.get("question", "")).strip()
		options = [option for option in map(clean_option, item.get("options") or []) if option][:MAX_OPTIONS]
		if text:
			cleaned.append({"question": text, "options": options, "multiple": bool(item.get("multiple"))})
	return cleaned


def ask(chat: str | None, questions: list[dict]) -> dict:
	"""Put the questions in the chat, once: asking the same again while they wait reuses the card."""
	questions = clean(questions)
	if not questions:
		frappe.throw("Give at least one question.")
	position = message_count(chat)
	# One card per turn: an agent that already asked has handed the question over, and the one above it must not ask it again.
	if not frappe.db.exists("Raven AI Question", {"chat": chat, "message_position": position, "status": "Pending"}):
		request = {"chat": chat, "message_position": position, "questions": json.dumps(questions, ensure_ascii=False)}
		frappe.get_doc({"doctype": "Raven AI Question", **request}).insert()
	return WAITING


def question_tool(chat: str | None) -> FunctionTool:
	@function_tool(
		strict_mode=False,
		name_override="ask_user",
		description_override=(
			"Ask the user to decide when you are not sure and a wrong guess would matter: which field, which document, which person, which "
			f"meaning. Ask only what you truly need, at most {MAX_QUESTIONS} questions in one call, and never what your tools can find out or "
			"what follows from another answer. `questions` is a list, each {question, options, multiple}. `options` are real answers the user can "
			f"pick (2 to {MAX_OPTIONS}); for an open question (a name, a date, an amount) give NO options and the user types the answer. Never make "
			"a choice that only says to type something. `multiple`: true if several may be picked. A choice is a short label, or "
			"{label, description, preview}: `preview` is a short Markdown text shown beside the choice, only when seeing what it would produce "
			"helps. The user can always answer in their own words instead. If something unreadable is the problem (a blurry picture), ask first "
			"whether they can send it again."
		),
	)
	def ask_user(questions: list[dict]) -> str:
		return answer(lambda: ask(chat, questions))

	return ask_user
