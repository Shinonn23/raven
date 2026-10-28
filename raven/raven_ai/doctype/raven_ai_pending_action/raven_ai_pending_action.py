import json

import frappe
from frappe import _
from frappe.model.document import Document

from raven.ai.harness.approved_actions import ApprovedAction

SAVEPOINT = "raven_ai_pending_action"


class RavenAIPendingAction(Document):
	def decide(self, approve: bool):
		"""The owner's answer to the card. Approving does the work now, as them, all or nothing; rejecting only closes the request."""
		if self.owner != frappe.session.user:
			frappe.throw(_("Only the person the AI works for can decide this."), frappe.PermissionError)
		if self.status != "Pending":
			frappe.throw(_("This request has already been answered."))
		if approve:
			self.run()
		else:
			self.status = "Rejected"
		self.save()

	def run(self):
		frappe.db.savepoint(SAVEPOINT)
		try:
			approved = ApprovedAction(self)
			self.result = approved.run()
			self.names = json.dumps(approved.names)
			self.status = "Approved"
		except Exception as error:
			frappe.db.rollback(save_point=SAVEPOINT)
			self.status, self.result = "Failed", str(error)[:300]
