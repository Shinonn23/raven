import frappe
from frappe import _
from frappe.model.document import Document

MAX_ANSWER_LENGTH = 2000


class RavenAIQuestion(Document):
	def answer_with(self, answer: str) -> str:
		"""Record the user's answer (a choice or their own words) and return it. Only the person asked may answer, once."""
		if self.owner != frappe.session.user:
			frappe.throw(_("Only the person the AI is asking can answer."), frappe.PermissionError)
		if self.status != "Pending":
			frappe.throw(_("This question has already been answered."))
		answer = (answer or "").strip()
		if not answer or len(answer) > MAX_ANSWER_LENGTH:
			frappe.throw(_("Please give an answer of up to {0} characters.").format(MAX_ANSWER_LENGTH))
		self.status, self.answer = "Answered", answer
		self.save()
		return answer
