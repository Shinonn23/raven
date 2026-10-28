"""What happens when the user approves a card: Create a document, or Update, Submit, Cancel or Delete the listed ones. Every step is
checked against the user's own permissions again at that moment, whatever was checked when the AI asked."""

import json

import frappe
from frappe import _

MAX_DOCUMENTS = 200
PROTECTED_FIELDS = ("name", "owner", "creation", "modified", "modified_by", "docstatus", "doctype", "idx")


def editable(values: dict) -> dict:
	"""The values the AI may set: never ownership, timestamps or the document status."""
	return {key: value for key, value in (values or {}).items() if key not in PROTECTED_FIELDS}


class ApprovedAction:
	"""Does the work of a Raven AI Pending Action; raises if any document cannot be changed."""

	def __init__(self, request):
		self.doctype = request.reference_doctype
		self.names = json.loads(request.names)
		self.values = editable(json.loads(request.values or "{}"))
		self.action = request.action

	def run(self) -> str:
		if self.action == "Create":
			return self.create()
		if len(self.names) > MAX_DOCUMENTS:
			frappe.throw(_("At most {0} documents at a time.").format(MAX_DOCUMENTS))
		change = {"Submit": self.submit, "Cancel": self.cancel, "Delete": self.delete, "Update": self.update}[self.action]
		for name in self.names:
			change(name)
		return _("{0} {1} done.").format(len(self.names), self.doctype)

	def create(self) -> str:
		"""A new draft; the card then shows it, because `names` becomes the new document."""
		document = frappe.get_doc({"doctype": self.doctype, **self.values}).insert()
		self.names = [document.name]
		return _("{0} {1} created.").format(self.doctype, document.name)

	def document(self, name: str, permission: str):
		document = frappe.get_doc(self.doctype, name)
		frappe.has_permission(self.doctype, permission, doc=document, throw=True)
		return document

	def submit(self, name: str):
		self.document(name, "submit").submit()

	def cancel(self, name: str):
		self.document(name, "cancel").cancel()

	def delete(self, name: str):
		self.document(name, "delete")
		frappe.delete_doc(self.doctype, name)

	def update(self, name: str):
		document = self.document(name, "write")
		document.update(self.values)
		document.save()
