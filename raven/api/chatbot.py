import frappe
import frappe.share
from frappe import _

from raven.ai.chatbot_models import allowed_models
from raven.ai.manual_sources import manual_origins

RECOMMENDATION_LIMIT = 5


def _serialize_chat(chat) -> dict:
	return {
		"name": chat.name,
		"title": chat.title,
		"project": chat.project,
		"owner": chat.owner,
		"can_write": chat.has_permission("write"),
		"actions": _actions(chat.name),
		"messages": [
			{
				"role": message.role,
				"owner": message.owner,
				"creation": str(message.creation),
				"content": message.content,
				"files": frappe.parse_json(message.files) if message.files else [],
				"document": message.link_doctype
				and {"doctype": message.link_doctype, "docname": message.link_document},
			}
			for message in chat.messages
		],
	}


def _actions(chat: str) -> list[dict]:
	"""The approval cards of this chat, waiting or answered, oldest first (a user sees only the ones asked of them)."""
	return frappe.get_list(
		"Raven AI Pending Action",
		filters={"chat": chat},
		fields=["name", "action", "reference_doctype", "names", "values", "summary", "status", "result", "creation"],
		order_by="creation asc",
	)


@frappe.whitelist(methods=["POST"])
def decide_action(action: str, approve: bool) -> dict:
	"""Approve (do it now, as the current user) or reject a card the AI asked for. Returns the card with its outcome."""
	doc = frappe.get_doc("Raven AI Pending Action", action)
	doc.check_permission("write")
	doc.decide(approve)
	return {"name": doc.name, "status": doc.status, "result": doc.result}


@frappe.whitelist(methods=["GET"])
def get_chatbot_overview() -> dict:
	"""The current user's projects and chats (without messages), newest first."""
	return {
		"projects": frappe.get_list(
			"Raven Chatbot Project", fields=["name", "title"], order_by="creation asc"
		),
		"chats": frappe.get_list(
			"Raven Chatbot Chat", fields=["name", "title", "project", "modified", "owner"], order_by="modified desc"
		),
	}


@frappe.whitelist(methods=["GET"])
def get_chat(chat: str) -> dict:
	doc = frappe.get_doc("Raven Chatbot Chat", chat)
	doc.check_permission("read")
	return _serialize_chat(doc)


@frappe.whitelist(methods=["POST"])
def send_message(
	text: str,
	chat: str | None = None,
	project: str | None = None,
	files: str | list | None = None,
	document: str | dict | None = None,
	model: str | None = None,
	effort: str | None = None,
) -> dict:
	"""Send a message to the chatbot; creates the chat when `chat` is not given.
	Returns right away with the saved question; the answer streams over realtime and is saved when done."""
	text = (text or "").strip()
	if not (text or files or document):
		frappe.throw(_("Message cannot be empty"))

	if chat:
		doc = frappe.get_doc("Raven Chatbot Chat", chat)
		doc.check_permission("write")
	else:
		doc = frappe.new_doc("Raven Chatbot Chat")
		doc.project = project

	doc.add_user_message(
		text, frappe.parse_json(files or []), frappe.parse_json(document) if document else None, model, effort
	)
	return _serialize_chat(doc)


@frappe.whitelist(methods=["GET"])
def get_skills() -> list[dict]:
	"""Company skills and the current user's own, for the "/" menu."""
	return frappe.get_list(
		"Raven Chatbot Skill",
		fields=["name", "title", "command", "prompt", "is_company"],
		order_by="is_company desc, command asc",
	)


@frappe.whitelist(methods=["GET"])
def get_recommended_documents() -> list[dict]:
	"""The documents this user attaches most, skipping any they can no longer read."""
	usages = frappe.get_list(
		"Raven Chatbot Document Usage",
		fields=["reference_doctype as doctype", "reference_name as docname", "use_count"],
		order_by="use_count desc, last_used desc",
		limit=RECOMMENDATION_LIMIT * 4,
	)
	readable = [
		usage
		for usage in usages
		if frappe.db.exists(usage.doctype, usage.docname)
		and frappe.has_permission(usage.doctype, "read", doc=usage.docname)
	]
	return readable[:RECOMMENDATION_LIMIT]


def _owned_chat(chat: str):
	"""The chat, only if the current user owns it — sharing is an owner's decision."""
	doc = frappe.get_doc("Raven Chatbot Chat", chat)
	if doc.owner != frappe.session.user and "System Manager" not in frappe.get_roles():
		frappe.throw(_("Only the owner can share this chat."), frappe.PermissionError)
	return doc


def _login_of(raven_user: str) -> str:
	"""The Frappe user behind a Raven User, which must be an enabled person (not a bot)."""
	user, user_type, enabled = frappe.db.get_value("Raven User", raven_user, ["user", "type", "enabled"]) or (None,) * 3
	if not user or user_type != "User" or not enabled:
		frappe.throw(_("{0} cannot be given access to a chat.").format(raven_user))
	return user


@frappe.whitelist(methods=["GET"])
def get_chat_shares(chat: str) -> list[dict]:
	doc = _owned_chat(chat)
	return frappe.share.get_users("Raven Chatbot Chat", doc.name)


@frappe.whitelist(methods=["POST"])
def share_chat(chat: str, user: str, can_write: bool = False) -> list[dict]:
	"""Give another user read (optionally write) access to the chat."""
	doc = _owned_chat(chat)
	login = _login_of(user)
	if login == doc.owner:
		frappe.throw(_("You already own this chat."))
	frappe.share.add_docshare("Raven Chatbot Chat", doc.name, login, read=1, write=int(bool(can_write)), flags={"ignore_share_permission": True})
	return frappe.share.get_users("Raven Chatbot Chat", doc.name)


@frappe.whitelist(methods=["POST"])
def unshare_chat(chat: str, user: str) -> list[dict]:
	doc = _owned_chat(chat)
	share = frappe.db.get_value("DocShare", {"share_doctype": "Raven Chatbot Chat", "share_name": doc.name, "user": user})
	if share:
		frappe.delete_doc("DocShare", share, ignore_permissions=True, flags={"ignore_share_permission": True})
	return frappe.share.get_users("Raven Chatbot Chat", doc.name)


@frappe.whitelist(methods=["GET"])
def get_chatbot_options() -> dict:
	"""The models (and efforts per model) an admin lets users pick (the first is the default), and the manual sites whose pictures
	the chat may show."""
	return {"models": allowed_models(), "manual_origins": manual_origins()}
