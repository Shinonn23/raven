"""The tools that let the AI work on documents. Drafts it saves itself. Submit, cancel, delete and updating existing documents are
held by the harness, whatever the AI says: the tool only puts a card in the chat, and the work happens when the user approves it."""

import json
import frappe
from agents import FunctionTool, function_tool

from raven.ai.harness.approved_actions import MAX_DOCUMENTS, editable
from raven.ai.harness.data_tools import answer
from raven.ai.harness.document_drafts import DocumentDraft

PERMISSION_FOR = {"Submit": "submit", "Cancel": "cancel", "Delete": "delete", "Update many": "write"}


def summarize(values: dict | None) -> str:
	"""What an "Update many" card shows the user, written by the system from the real values, not by the AI."""
	return ", ".join(f"{field} = {value}" for field, value in editable(values or {}).items())


def request_approval(chat: str | None, action: str, doctype: str, names: list[str], values: dict | None = None) -> dict:
	"""Hold the change for the user: it shows as a card in the chat and happens only when they approve it. The documents must
	exist and be allowed for the user now."""
	if not names or len(names) > MAX_DOCUMENTS:
		frappe.throw(f"Give between 1 and {MAX_DOCUMENTS} documents.")
	for name in names:
		frappe.has_permission(doctype, PERMISSION_FOR[action], doc=frappe.get_doc(doctype, name), throw=True)
	frappe.get_doc(
		{
			"doctype": "Raven AI Pending Action",
			"chat": chat,
			"action": action,
			"reference_doctype": doctype,
			"names": json.dumps(names),
			"values": json.dumps(values or {}, ensure_ascii=False),
			"summary": summarize(values),
		}
	).insert()
	return {"done": False, "status": "waiting for the user's decision"}


def document_tools(chat: str | None) -> list[FunctionTool]:
	drafts = DocumentDraft()

	@function_tool(
		strict_mode=False,
		name_override="preview_document",
		description_override=(
			"Check a document the way saving would, without saving: returns problems (missing or invalid values), warnings and the document "
			"with the fields the system filled in or calculated. Pass `name` to check changes to an existing draft. Use it before save_draft."
		),
	)
	def preview_document(doctype: str, values: dict, name: str | None = None) -> str:
		return answer(lambda: drafts.preview(doctype, values, name))

	@function_tool(
		strict_mode=False,
		name_override="save_draft",
		description_override="Save a new draft, or changes to an existing draft (docstatus 0). Returns its name and link; give the link to the user.",
	)
	def save_draft(doctype: str, values: dict, name: str | None = None) -> str:
		return answer(lambda: drafts.save(doctype, values, name))

	@function_tool(
		strict_mode=False,
		name_override="open_prefilled_form",
		description_override="A link to the real new-document form with simple values filled in, for the user to review and finish themselves.",
	)
	def open_prefilled_form(doctype: str, values: dict) -> str:
		return answer(lambda: drafts.prefilled_link(doctype, values))

	@function_tool(strict_mode=False, name_override="submit_document", description_override="Submit a draft document.")
	def submit_document(doctype: str, name: str) -> str:
		return answer(lambda: request_approval(chat, "Submit", doctype, [name]))

	@function_tool(strict_mode=False, name_override="cancel_document", description_override="Cancel a submitted document.")
	def cancel_document(doctype: str, name: str) -> str:
		return answer(lambda: request_approval(chat, "Cancel", doctype, [name]))

	@function_tool(strict_mode=False, name_override="delete_documents", description_override="Delete documents (up to 200).")
	def delete_documents(doctype: str, names: list[str]) -> str:
		return answer(lambda: request_approval(chat, "Delete", doctype, names))

	@function_tool(
		strict_mode=False,
		name_override="update_documents",
		description_override="Set the same field values on existing documents (up to 200), submitted or not.",
	)
	def update_documents(doctype: str, names: list[str], values: dict) -> str:
		return answer(lambda: request_approval(chat, "Update many", doctype, names, values))

	return [preview_document, save_draft, open_prefilled_form, submit_document, cancel_document, delete_documents, update_documents]
