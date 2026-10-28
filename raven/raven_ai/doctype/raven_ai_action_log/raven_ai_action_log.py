import frappe
from frappe.model.document import Document


class RavenAIActionLog(Document):
	@staticmethod
	def record_all(rows: list[dict]):
		"""Save what the AI did in one answer. Each row is created with the user's own permission to create it."""
		for step, row in enumerate(rows, start=1):
			frappe.get_doc({"doctype": "Raven AI Action Log", "step": step, **row}).insert()
