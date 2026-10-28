"""The tools that let the AI work on documents. Every change (create, update, submit, cancel, delete) is held by the harness,
whatever the AI says: the tool only puts a card in the chat, and the work happens when the user approves it."""

import json

import frappe
from agents import FunctionTool, function_tool
from frappe import _

from raven.ai.harness.approved_actions import MAX_DOCUMENTS, editable
from raven.ai.harness.data_tools import answer
from raven.ai.harness.document_drafts import DocumentDraft

PERMISSION_FOR = {"Create": "create", "Update": "write", "Submit": "submit", "Cancel": "cancel", "Delete": "delete"}
WAITING = {
	"done": False,
	"status": "waiting for the user's decision",
	"next": "Nothing more can be done until they decide. Do not ask again.",
}


def display(field, value) -> str:
	"""A value as the user knows it: people by name."""
	if field and field.fieldtype == "Link" and field.options == "User":
		return frappe.utils.get_fullname(value)
	return str(value)


def summarize(doctype: str, values: dict | None) -> str:
	"""What the card shows the user: each field by its label with the value, written by the system from the real values."""
	meta = frappe.get_meta(doctype)
	lines = []
	for fieldname, value in editable(values or {}).items():
		field = meta.get_field(fieldname)
		lines.append(f"{_(field.label) if field and field.label else fieldname}: {display(field, value)}")
	return "\n".join(lines)


def request_approval(chat: str | None, action: str, doctype: str, names: list[str] | None = None, values: dict | None = None) -> dict:
	"""Hold the change for the user. It must be allowed for them now, and a new document must pass the checks of saving."""
	names = names or []
	if action == "Create":
		frappe.has_permission(doctype, "create", throw=True)
		checked = DocumentDraft().preview(doctype, values or {})
		if not checked["ok"]:
			return {"done": False, "problems": checked["problems"]}
	else:
		if not names or len(names) > MAX_DOCUMENTS:
			frappe.throw(f"Give between 1 and {MAX_DOCUMENTS} documents.")
		for name in names:
			frappe.has_permission(doctype, PERMISSION_FOR[action], doc=frappe.get_doc(doctype, name), throw=True)
	request = {
		"chat": chat,
		"action": action,
		"reference_doctype": doctype,
		"names": json.dumps(names),
		"values": json.dumps(values or {}, ensure_ascii=False),
	}
	# Asking again for what is already waiting (the AI may retry when it sees "not done") must not make a second card.
	if not frappe.db.exists("Raven AI Pending Action", {**request, "status": "Pending"}):
		frappe.get_doc({"doctype": "Raven AI Pending Action", **request, "summary": summarize(doctype, values)}).insert()
	return WAITING


def document_tools(chat: str | None) -> list[FunctionTool]:
	drafts = DocumentDraft()

	@function_tool(
		strict_mode=False,
		name_override="preview_document",
		description_override=(
			"Check a document the way saving would, without saving: returns problems (missing or invalid values), warnings and the document "
			"with the fields the system filled in or calculated. Pass `name` to check changes to an existing draft."
		),
	)
	def preview_document(doctype: str, values: dict, name: str | None = None) -> str:
		return answer(lambda: drafts.preview(doctype, values, name))

	@function_tool(
		strict_mode=False,
		name_override="open_prefilled_form",
		description_override="A link to the real new-document form with simple values filled in, for the user to review and finish themselves.",
	)
	def open_prefilled_form(doctype: str, values: dict) -> str:
		return answer(lambda: drafts.prefilled_link(doctype, values))

	@function_tool(strict_mode=False, name_override="create_document", description_override="Create a new draft document with these values.")
	def create_document(doctype: str, values: dict) -> str:
		return answer(lambda: request_approval(chat, "Create", doctype, None, values))

	@function_tool(
		strict_mode=False,
		name_override="update_documents",
		description_override="Set field values on one or more existing documents (up to 200): the same values on each.",
	)
	def update_documents(doctype: str, names: list[str], values: dict) -> str:
		return answer(lambda: request_approval(chat, "Update", doctype, names, values))

	@function_tool(strict_mode=False, name_override="submit_document", description_override="Submit a draft document.")
	def submit_document(doctype: str, name: str) -> str:
		return answer(lambda: request_approval(chat, "Submit", doctype, [name]))

	@function_tool(strict_mode=False, name_override="cancel_document", description_override="Cancel a submitted document.")
	def cancel_document(doctype: str, name: str) -> str:
		return answer(lambda: request_approval(chat, "Cancel", doctype, [name]))

	@function_tool(strict_mode=False, name_override="delete_documents", description_override="Delete documents (up to 200).")
	def delete_documents(doctype: str, names: list[str]) -> str:
		return answer(lambda: request_approval(chat, "Delete", doctype, names))

	return [preview_document, open_prefilled_form, create_document, update_documents, submit_document, cancel_document, delete_documents]
