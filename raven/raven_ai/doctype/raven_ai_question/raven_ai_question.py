import json

import frappe
from frappe import _
from frappe.model.document import Document

MAX_ANSWER_LENGTH = 2000


class RavenAIQuestion(Document):
	def answer_with(self, answers: list[str]) -> str:
		"""Record the user's answers, one for each question (choices or their own words), and return them as the message to send.
		Only the person asked may answer, once."""
		if self.owner != frappe.session.user:
			frappe.throw(_("Only the person the AI is asking can answer."), frappe.PermissionError)
		if self.status != "Pending":
			frappe.throw(_("This question has already been answered."))
		questions = json.loads(self.questions)
		answers = [(answer or "").strip() for answer in answers]
		if len(answers) != len(questions) or not all(answers) or any(len(answer) > MAX_ANSWER_LENGTH for answer in answers):
			frappe.throw(_("Please answer every question, in up to {0} characters each.").format(MAX_ANSWER_LENGTH))
		self.status, self.answers = "Answered", json.dumps(answers, ensure_ascii=False)
		self.save()
		return "\n".join(f"- {item['question']}: {answer}" for item, answer in zip(questions, answers, strict=True))
