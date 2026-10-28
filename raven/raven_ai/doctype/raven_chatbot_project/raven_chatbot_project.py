import frappe
from frappe.model.document import Document


class RavenChatbotProject(Document):
	def on_trash(self):
		for chat in frappe.get_all("Raven Chatbot Chat", filters={"project": self.name}, pluck="name"):
			frappe.delete_doc("Raven Chatbot Chat", chat)
