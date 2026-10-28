import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class RavenChatbotDocumentUsage(Document):
	@staticmethod
	def record(doctype: str, docname: str):
		"""Count one more use of this document by the current user."""
		filters = {"owner": frappe.session.user, "reference_doctype": doctype, "reference_name": docname}
		name = frappe.db.get_value("Raven Chatbot Document Usage", filters)
		if name:
			usage = frappe.get_doc("Raven Chatbot Document Usage", name)
			usage.use_count += 1
			usage.last_used = now_datetime()
			usage.save()
		else:
			frappe.get_doc(
				{
					"doctype": "Raven Chatbot Document Usage",
					"reference_doctype": doctype,
					"reference_name": docname,
					"last_used": now_datetime(),
				}
			).insert()
