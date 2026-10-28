"""What happens when the user approves a card: Create a document, or Update, Cancel and so on, the sidebar actions and their removals, or Delete the listed ones. Every step is
checked against the user's own permissions again at that moment, whatever was checked when the AI asked."""

import json

import frappe
from frappe import _
import frappe.share
from frappe.desk.doctype.tag.tag import add_tag, remove_tag
from frappe.desk.form import assign_to

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
		change = {"Submit": self.submit, "Cancel": self.cancel, "Delete": self.delete, "Update": self.update, "Assign": self.assign, "Tag": self.tag, "Share": self.share, "Attach": self.attach,
			"Unassign": self.unassign, "Untag": self.untag, "Unshare": self.unshare, "Detach": self.detach,
		}[self.action]
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

	def assign(self, name: str):
		"""Frappe's own Assign: an assignment ToDo for each user, with the sharing it needs. It checks the user's permission."""
		assign_to.add({"doctype": self.doctype, "name": name, "assign_to": self.values["assign_to"]})

	def tag(self, name: str):
		self.document(name, "write")
		for tag in self.values["tags"]:
			add_tag(tag, self.doctype, name)

	def share(self, name: str):
		"""Frappe's Share, which checks that the user may share the document."""
		for user in self.values["share_with"]:
			frappe.share.add(self.doctype, name, user, read=1, write=int(bool(self.values.get("can_edit"))))

	def attach(self, name: str):
		"""Attach a file the user may read, as the sidebar's "attach from library" does."""
		source = frappe.get_doc("File", {"file_url": self.values["file_url"]})
		source.check_permission("read")
		self.document(name, "write")
		frappe.get_doc(
			{
				"doctype": "File",
				"file_url": source.file_url,
				"file_name": source.file_name,
				"is_private": source.is_private,
				"attached_to_doctype": self.doctype,
				"attached_to_name": name,
			}
		).insert()

	def unassign(self, name: str):
		for user in self.values["assign_to"]:
			assign_to.remove(self.doctype, name, user)

	def untag(self, name: str):
		self.document(name, "write")
		for tag in self.values["tags"]:
			remove_tag(tag, self.doctype, name)

	def unshare(self, name: str):
		self.document(name, "share")
		for user in self.values["share_with"]:
			frappe.share.remove(self.doctype, name, user)

	def detach(self, name: str):
		"""Remove attached files; each must really be attached to this document."""
		self.document(name, "write")
		for file_name in self.values["detach"]:
			file = frappe.get_doc("File", file_name)
			if (file.attached_to_doctype, file.attached_to_name) != (self.doctype, name):
				frappe.throw(_("{0} is not attached to {1} {2}.").format(file_name, self.doctype, name))
			frappe.delete_doc("File", file_name)

	def update(self, name: str):
		document = self.document(name, "write")
		document.update(self.values)
		document.save()
