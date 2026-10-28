"""Reads company data for the AI as the user who is chatting: every call goes through Frappe's permission checks
(document, field level and user permissions), so the AI sees what that user sees and nothing more."""

import frappe
from frappe.desk.query_report import run as run_report
from frappe.model import get_permitted_fields

MAX_ROWS = 100
MAX_REPORT_ROWS = 200


class DataReader:
	"""Read-only questions about data. Each method returns plain data and raises if the user may not read it."""

	def describe(self, doctype: str) -> dict:
		frappe.has_permission(doctype, "read", throw=True)
		meta = frappe.get_meta(doctype)
		permitted = set(get_permitted_fields(doctype))
		return {
			"doctype": doctype,
			"is_submittable": bool(meta.is_submittable),
			"title_field": meta.title_field,
			"fields": [
				{"name": field.fieldname, "label": field.label, "type": field.fieldtype, "options": field.options, "required": bool(field.reqd)}
				for field in meta.fields
				if field.label and field.fieldname in permitted
			],
		}

	def list(self, doctype: str, filters: list | dict | None, fields: list[str] | None, order_by: str | None, limit: int) -> list[dict]:
		return frappe.get_list(
			doctype,
			filters=filters or None,
			fields=fields or ["name"],
			order_by=order_by or None,
			limit_page_length=min(max(limit, 1), MAX_ROWS),
		)

	def count(self, doctype: str, filters: list | dict | None, group_by: str | None) -> list[dict]:
		"""The number of documents, in total or per value of `group_by`, most frequent first."""
		fields = [{"COUNT": "name", "as": "total"}]
		if group_by:
			fields.insert(0, group_by)
		return frappe.get_list(
			doctype, filters=filters or None, fields=fields, group_by=group_by or None, order_by="total desc", limit_page_length=MAX_ROWS
		)

	def get(self, doctype: str, name: str) -> dict:
		document = frappe.get_doc(doctype, name)
		document.check_permission("read")
		document.apply_fieldlevel_read_permissions()
		return {key: value for key, value in document.as_dict().items() if value not in (None, "", [])}

	def report(self, report_name: str, filters: dict | None) -> dict:
		result = run_report(report_name, filters=filters or {}, user=frappe.session.user)
		rows = result.get("result") or []
		return {"columns": result.get("columns"), "rows": rows[:MAX_REPORT_ROWS], "total_rows": len(rows)}
