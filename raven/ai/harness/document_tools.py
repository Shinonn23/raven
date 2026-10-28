"""The tools that let the AI prepare documents for the user. It can check and save drafts and open a filled form; everything that
is hard to undo (submit, cancel, delete, changing many documents) only becomes a card the user must approve in the chat."""

import json
from typing import Literal

import frappe
from agents import FunctionTool, function_tool

from raven.ai.harness.approved_actions import MAX_DOCUMENTS
from raven.ai.harness.data_tools import answer
from raven.ai.harness.document_drafts import DocumentDraft

PERMISSION_FOR = {"Submit": "submit", "Cancel": "cancel", "Delete": "delete", "Update many": "write"}


def request_approval(chat: str | None, action: str, doctype: str, names: list[str], values: dict | None, summary: str) -> dict:
	"""Put a card in the chat. The documents must exist and be allowed for the user now; the work happens only when they approve."""
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
			"summary": summary,
		}
	).insert()
	return {"status": "waiting", "note": "The user has been asked. Tell them what you asked to do; do not assume it is done."}


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

	@function_tool(
		strict_mode=False,
		name_override="ask_user_to_approve",
		description_override=(
			"For anything hard to undo: Submit, Cancel, Delete, or Update many (the same `values` on up to 200 documents). This does NOT do it: "
			"it shows the user a card to approve or reject. `summary` says in one plain sentence what will happen."
		),
	)
	def ask_user_to_approve(
		action: Literal["Submit", "Cancel", "Delete", "Update many"],
		doctype: str,
		names: list[str],
		summary: str,
		values: dict | None = None,
	) -> str:
		return answer(lambda: request_approval(chat, action, doctype, names, values, summary))

	return [preview_document, save_draft, open_prefilled_form, ask_user_to_approve]
