"""Reads company data for the AI as the user who is chatting: every call goes through Frappe's permission checks
(document, field level and user permissions), so the AI sees what that user sees and nothing more."""

import frappe
from frappe.desk.query_report import run as run_report
from frappe.desk.search import search_link
from frappe.model import get_permitted_fields

MAX_ROWS = 100
MAX_REPORT_ROWS = 200
EXAMPLE_RECORDS = 6
MAX_LINK_RESULTS = 10


class DataReader:
	"""Read-only questions about data. Each method returns plain data and raises if the user may not read it."""

	def describe(self, doctype: str) -> dict:
		"""The fields the user may read. A Select field lists its choices; a Link field names the DocType it points to, with a few of its
		records the user may read (`more` when there are others: search them with find_link_values)."""
		frappe.has_permission(doctype, "read", throw=True)
		meta = frappe.get_meta(doctype)
		permitted = set(get_permitted_fields(doctype))
		return {
			"doctype": doctype,
			"is_submittable": bool(meta.is_submittable),
			"title_field": meta.title_field,
			"fields": [self.describe_field(field) for field in meta.fields if field.label and field.fieldname in permitted],
		}

	def describe_field(self, field) -> dict:
		"""One field. `fetched_from` and `read_only` mark a value the system fills in itself: it is not asked for or set; `default` is what a new document starts with."""
		row = {"name": field.fieldname, "label": field.label, "type": field.fieldtype, "required": bool(field.reqd)}
		row.update({key: value for key, value in {"fetched_from": field.fetch_from, "read_only": bool(field.read_only) or None, "default": field.default}.items() if value})
		if field.fieldtype == "Select":
			return {**row, "choices": [choice for choice in (field.options or "").split("\n") if choice]}
		if field.fieldtype == "Link":
			return {**row, "link_to": field.options, **self.example_records(field.options)}
		return {**row, "options": field.options}

	def example_records(self, doctype: str) -> dict:
		meta = frappe.get_meta(doctype)
		if meta.issingle:
			return {}
		if not frappe.has_permission(doctype, "read"):
			return {"readable": False}
		try:
			title = meta.title_field
			fields = ["name", title] if title and title != "name" else ["name"]
			records = frappe.get_list(doctype, fields=fields, limit_page_length=EXAMPLE_RECORDS + 1)
		except frappe.PermissionError:
			return {"readable": False}
		shown = [{"name": record.name, **({"title": record.get(title)} if title and title != "name" else {})} for record in records[:EXAMPLE_RECORDS]]
		return {"examples": shown, "more": len(records) > EXAMPLE_RECORDS}

	def find_link_values(self, doctype: str, fieldname: str, text: str) -> list[dict]:
		"""The values a Link field accepts that match `text`, searched as the form's own dropdown does (the field's filters and the user's permissions)."""
		field = frappe.get_meta(doctype).get_field(fieldname)
		if not field or field.fieldtype != "Link":
			frappe.throw(f"{fieldname} is not a Link field of {doctype}.")
		return search_link(field.options, text or "", reference_doctype=doctype, link_fieldname=fieldname, page_length=MAX_LINK_RESULTS)

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
