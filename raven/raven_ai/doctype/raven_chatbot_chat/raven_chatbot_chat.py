import frappe
from agents.exceptions import MaxTurnsExceeded
from frappe import _
from frappe.model.document import Document

from raven.ai.chatbot_context import build_prompt, validate_attachments
from raven.ai.chatbot_models import ChatbotChoice, resolve_choice
from raven.ai.chatbot_stream import DeltaPublisher, stream_reply
from raven.raven_ai.doctype.raven_chatbot_document_usage.raven_chatbot_document_usage import (
	RavenChatbotDocumentUsage,
)

TITLE_MAX_LENGTH = 40
REPLY_TIMEOUT_SECONDS = 600


class RavenChatbotChat(Document):
	def add_user_message(
		self,
		text: str,
		files: list[dict] | None = None,
		document: dict | None = None,
		model: str | None = None,
		effort: str | None = None,
	):
		"""Save the user's message (checking they may read what they attached) and queue the chatbot's reply."""
		choice = resolve_choice(model, effort)
		files = files or []
		validate_attachments(files, document)
		prompt = build_prompt(text, files, document)
		history = [{"role": message.role, "content": message.content} for message in self.messages]

		self.append(
			"messages",
			{
				"role": "user",
				"content": text,
				"files": frappe.as_json(files) if files else None,
				"link_doctype": document and document["doctype"],
				"link_document": document and document["docname"],
			},
		)
		if not self.title:
			self.title = text.strip().replace("\n", " ")[:TITLE_MAX_LENGTH]
		self.save()

		frappe.enqueue(
			"raven.raven_ai.doctype.raven_chatbot_chat.raven_chatbot_chat.reply",
			queue="default",
			timeout=REPLY_TIMEOUT_SECONDS,
			enqueue_after_commit=True,
			chat=self.name,
			prompt=prompt,
			history=history,
			model=choice.model,
			effort=choice.effort,
		)
		if document:
			RavenChatbotDocumentUsage.record(document["doctype"], document["docname"])


def reply(chat: str, prompt: str, history: list[dict], model: str, effort: str | None = None):
	"""Background job: stream the bot's answer to the user's browser, then save it as the assistant message."""
	doc = frappe.get_doc("Raven Chatbot Chat", chat)
	failed = False
	try:
		answer = stream_reply(prompt, history, DeltaPublisher(chat), ChatbotChoice(model, effort))
	except MaxTurnsExceeded:
		answer = _("This took more steps than I am allowed to take in one go. Please ask for a smaller part of it and I will continue.")
		failed = True
	except Exception:
		frappe.log_error(title="Chatbot reply failed")
		answer = _("Sorry, I could not answer that. Please try again.")
		failed = True

	doc.reload()
	doc.append("messages", {"role": "assistant", "content": answer})
	doc.flags.ignore_permissions = True
	doc.save()
	frappe.publish_realtime("chatbot_done", {"chat": chat, "failed": failed}, user=frappe.session.user)
