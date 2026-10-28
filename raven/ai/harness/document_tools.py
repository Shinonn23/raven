"""The tools that let the AI work on documents. Every change (create, update, submit, cancel, delete) is held by the harness,
whatever the AI says: the tool only puts a card in the chat, and the work happens when the user approves it."""

import json

import frappe
from agents import FunctionTool, function_tool
from frappe import _

from raven.ai.harness.approved_actions import MAX_DOCUMENTS, editable
from raven.ai.harness.data_tools import answer
from raven.ai.harness.document_drafts import DocumentDraft

SIDEBAR_ACTIONS = ("Assign", "Tag", "Share", "Attach")
PERMISSION_FOR = {"Create": "create", "Update": "write", "Assign": "read", "Tag": "write", "Share": "share", "Attach": "write", "Submit": "submit", "Cancel": "cancel", "Delete": "delete"}
WAITING = {
	"state": "awaiting the user's approval",
	"shown_to_user": "an approval card is in the chat",
	"next": (
		"Say in one short sentence that the request is ready and they only need to approve it in the card. "
		"It is not a failure and nothing is blocked, so do not say it could not be done or is not done yet. You will not be told when they decide, so promise no follow-up. Do not ask again."
	),
}


def display(field, value) -> str:
	"""A value as the user knows it: people by name."""
	if field and field.fieldtype == "Link" and field.options == "User":
		return frappe.utils.get_fullname(value)
	return str(value)


def summarize_sidebar_action(values: dict) -> str:
	"""The card text of Assign, Tag, Share and Attach, which carry users, tags or a file rather than field values."""
	people = lambda users: ", ".join(frappe.utils.get_fullname(user) for user in users)  # noqa: E731
	if "assign_to" in values:
		return _("Assign to: {0}").format(people(values["assign_to"]))
	if "tags" in values:
		return _("Tags: {0}").format(", ".join(values["tags"]))
	if "share_with" in values:
		return _("Share with: {0}").format(people(values["share_with"])) + (_(" (can edit)") if values.get("can_edit") else "")
	if "file_url" in values:
		return _("Attach: {0}").format(frappe.db.get_value("File", {"file_url": values["file_url"]}, "file_name") or values["file_url"])
	return ""


def summarize(doctype: str, values: dict | None) -> str:
	"""What the card shows the user: each field by its label with the value, written by the system from the real values."""
	meta = frappe.get_meta(doctype)
	lines = []
	for fieldname, value in editable(values or {}).items():
		field = meta.get_field(fieldname)
		lines.append(f"{_(field.label) if field and field.label else fieldname}: {display(field, value)}")
	return "\n".join(lines)


def message_count(chat: str | None) -> int:
	"""How many messages the chat has: the card goes under the answer that follows them."""
	if not chat:
		return 0
	document = frappe.get_doc("Raven Chatbot Chat", chat)
	document.check_permission("read")
	return len(document.messages)


def unusable_users(users: list[str] | None) -> list[str]:
	"""The users in the list that do not exist or are disabled."""
	users = users or []
	found = frappe.get_list("User", filters={"name": ["in", users], "enabled": 1}, pluck="name") if users else []
	return [user for user in users or [""] if user not in found]


def request_approval(chat: str | None, action: str, doctype: str, names: list[str] | None = None, values: dict | None = None) -> dict:
	"""Hold the change for the user. It must be allowed for them now, and a new document must pass the checks of saving."""
	names = names or []
	if action == "Create":
		frappe.has_permission(doctype, "create", throw=True)
		checked = DocumentDraft().preview(doctype, values or {})
		if not checked["ok"]:
			return {"not_requested": True, "problems": checked["problems"]}
	else:
		if (people := (values or {}).get("assign_to") or (values or {}).get("share_with")) and (unknown := unusable_users(people)):
			return {"not_requested": True, "problems": [f"Not an enabled user: {', '.join(unknown)}. Use the user id (email) from the User list."]}
		if action == "Attach":
			frappe.get_doc("File", {"file_url": (values or {}).get("file_url")}).check_permission("read")
		if not names or len(names) > MAX_DOCUMENTS:
			frappe.throw(f"Give between 1 and {MAX_DOCUMENTS} documents.")
		for name in names:
			frappe.has_permission(doctype, PERMISSION_FOR[action], doc=frappe.get_doc(doctype, name), throw=True)
	request = {
		"chat": chat,
		"message_position": message_count(chat),
		"action": action,
		"reference_doctype": doctype,
		"names": json.dumps(names),
		"values": json.dumps(values or {}, ensure_ascii=False),
	}
	# Asking again for what is already waiting (the AI may retry when it sees "not done") must not make a second card.
	if not frappe.db.exists("Raven AI Pending Action", {**request, "status": "Pending"}):
		frappe.get_doc({"doctype": "Raven AI Pending Action", **request, "summary": summarize_sidebar_action(values or {}) if action in SIDEBAR_ACTIONS else summarize(doctype, values)}).insert()
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

	@function_tool(
		strict_mode=False,
		name_override="assign_documents",
		description_override=(
			"Assign documents to one or more users with Frappe's Assign (each gets an assignment in their ToDo list). Use this, not a field, "
			"when someone asks to assign a document to people. `users` are user ids (emails); find them with list_documents on User."
		),
	)
	def assign_documents(doctype: str, names: list[str], users: list[str]) -> str:
		return answer(lambda: request_approval(chat, "Assign", doctype, names, {"assign_to": users}))

	@function_tool(
		strict_mode=False,
		name_override="tag_documents",
		description_override="Add tags to documents, like the Tags box in the document sidebar.",
	)
	def tag_documents(doctype: str, names: list[str], tags: list[str]) -> str:
		return answer(lambda: request_approval(chat, "Tag", doctype, names, {"tags": tags}))

	@function_tool(
		strict_mode=False,
		name_override="share_documents",
		description_override=(
			"Share documents with users, like Share in the document sidebar: they can read, and edit if `can_edit`. "
			"`users` are user ids (emails); find them with list_documents on User."
		),
	)
	def share_documents(doctype: str, names: list[str], users: list[str], can_edit: bool = False) -> str:
		return answer(lambda: request_approval(chat, "Share", doctype, names, {"share_with": users, "can_edit": can_edit}))

	@function_tool(
		strict_mode=False,
		name_override="attach_file",
		description_override="Attach a file to a document, like Attachments in the document sidebar. `file_url` is the address of a file the user attached to the chat or may read.",
	)
	def attach_file(doctype: str, name: str, file_url: str) -> str:
		return answer(lambda: request_approval(chat, "Attach", doctype, [name], {"file_url": file_url}))

	@function_tool(strict_mode=False, name_override="submit_document", description_override="Submit a draft document.")
	def submit_document(doctype: str, name: str) -> str:
		return answer(lambda: request_approval(chat, "Submit", doctype, [name]))

	@function_tool(strict_mode=False, name_override="cancel_document", description_override="Cancel a submitted document.")
	def cancel_document(doctype: str, name: str) -> str:
		return answer(lambda: request_approval(chat, "Cancel", doctype, [name]))

	@function_tool(strict_mode=False, name_override="delete_documents", description_override="Delete documents (up to 200).")
	def delete_documents(doctype: str, names: list[str]) -> str:
		return answer(lambda: request_approval(chat, "Delete", doctype, names))

	return [preview_document, open_prefilled_form, create_document, update_documents, assign_documents, tag_documents, share_documents, attach_file, submit_document, cancel_document, delete_documents]
