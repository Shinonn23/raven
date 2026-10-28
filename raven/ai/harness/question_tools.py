"""The AI asks the user a question when it is not sure. The question shows as a card with choices and a place to type any other answer;
the answer comes back as the user's next message, so the AI carries on with the whole conversation in front of it."""

import json

import frappe
from agents import FunctionTool, function_tool

from raven.ai.harness.data_tools import answer
from raven.ai.harness.document_tools import message_count

MAX_OPTIONS = 6
WAITING = {
	"state": "the question is shown to the user",
	"next": "Stop here and wait: their answer arrives as their next message. Do not guess, and do not ask it again.",
}


def ask(chat: str | None, question: str, options: list[str]) -> dict:
	"""Put the question in the chat, once: asking the same thing again while it waits reuses the card."""
	options = [option.strip() for option in options if option and option.strip()][:MAX_OPTIONS]
	request = {"chat": chat, "message_position": message_count(chat), "question": question.strip(), "options": json.dumps(options, ensure_ascii=False)}
	if not frappe.db.exists("Raven AI Question", {**request, "status": "Pending"}):
		frappe.get_doc({"doctype": "Raven AI Question", **request}).insert()
	return WAITING


def question_tool(chat: str | None) -> FunctionTool:
	@function_tool(
		strict_mode=False,
		name_override="ask_user",
		description_override=(
			"Ask the user to decide when you are not sure and a wrong guess would matter: which field, which document, which person, which "
			"meaning. Give 2 to 6 short likely choices; the user can also type their own answer. Do not ask what you can find out with your tools."
		),
	)
	def ask_user(question: str, options: list[str]) -> str:
		return answer(lambda: ask(chat, question, options))

	return ask_user
