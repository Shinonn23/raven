"""Prepares documents for the user as the user: check them the way saving would (without saving), save them as drafts, or
build a link to the real form with the values filled in. Nothing here submits, cancels or deletes: that needs the user's approval."""

from urllib.parse import quote, urlencode

import frappe
from frappe import _
from frappe.utils import strip_html

from raven.ai.harness.approved_actions import editable

SAVEPOINT = "raven_ai_preview"
SHOWN_KEYS_EXCLUDED = ("owner", "creation", "modified", "modified_by", "idx", "docstatus", "doctype")


class DocumentDraft:
	def load(self, doctype: str, values: dict, name: str | None):
		"""A new document with these values, or the existing draft `name` changed to have them."""
		if not name:
			return frappe.get_doc({"doctype": doctype, **editable(values)})
		document = frappe.get_doc(doctype, name)
		if document.docstatus != 0:
			frappe.throw(_("{0} {1} is not a draft; ask the user to approve a change to it.").format(doctype, name))
		document.update(editable(values))
		return document

	def preview(self, doctype: str, values: dict, name: str | None = None) -> dict:
		"""What saving would say, with the fields the system fills in or recalculates. Nothing is kept."""
		document = self.load(doctype, values, name)
		frappe.db.savepoint(SAVEPOINT)
		try:
			self.run_checks(document, bool(name))
			problems = []
		except Exception as error:
			problems = [strip_html(str(error))[:500]]
		finally:
			frappe.db.rollback(save_point=SAVEPOINT)
		warnings = [strip_html(str(message.get("message")))[:300] for message in frappe.get_message_log()]
		frappe.clear_messages()
		shown = {key: value for key, value in document.as_dict().items() if key not in SHOWN_KEYS_EXCLUDED and value not in (None, "", [])}
		return {"ok": not problems, "problems": problems, "warnings": warnings, "document": shown}

	@staticmethod
	def run_checks(document, exists: bool):
		"""The checks of insert() and save(), in their order, without writing."""
		if not exists:
			document.set("__islocal", True)
		document._set_defaults()
		document.set_user_and_timestamp()
		document.set_docstatus()
		document.check_permission("write" if exists else "create")
		document.check_if_latest()
		document._validate_links()
		document.set_parent_in_children()
		document.validate_higher_perm_levels()
		document.flags.in_insert = not exists
		document.run_before_save_methods()
		document._validate()

	def save(self, doctype: str, values: dict, name: str | None = None) -> dict:
		"""Save a draft (new, or a change to an existing draft)."""
		document = self.load(doctype, values, name)
		document.save() if name else document.insert()
		return {"name": document.name, "link": self.form_path(doctype, document.name)}

	def prefilled_link(self, doctype: str, values: dict) -> dict:
		"""A link that opens the real new-document form with these simple values filled in, for the user to finish."""
		frappe.has_permission(doctype, "create", throw=True)
		simple = {key: value for key, value in editable(values).items() if isinstance(value, str | int | float)}
		return {"link": f"{self.form_path(doctype, 'new')}?{urlencode(simple, quote_via=quote)}"}

	@staticmethod
	def form_path(doctype: str, name: str) -> str:
		return f"/app/{frappe.scrub(doctype).replace('_', '-')}/{quote(name)}"
