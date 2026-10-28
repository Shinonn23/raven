import json

import frappe
from frappe import _

READABLE_EXTENSIONS = {"txt", "md", "csv", "json"}
MAX_CONTEXT_CHARACTERS = 8000


def _clip(text: str) -> str:
	return text[:MAX_CONTEXT_CHARACTERS]


def document_context(doctype: str, docname: str) -> str:
	"""The document as text for the model. Raises if the current user may not read it."""
	doc = frappe.get_doc(doctype, docname)
	doc.check_permission("read")
	return _clip(f"Document {doctype} {docname}:\n{json.dumps(doc.as_dict(), default=str, indent=1)}")


def file_context(file_url: str) -> str:
	"""A file's name, plus its content when it is plain text. Raises if the user may not read it."""
	file = frappe.get_doc("File", {"file_url": file_url})
	file.check_permission("read")
	extension = (file.file_name or "").rsplit(".", 1)[-1].lower()
	if extension not in READABLE_EXTENSIONS:
		return f"Attached file: {file.file_name} (content not readable as text)"
	content = file.get_content()
	content = content.decode(errors="replace") if isinstance(content, bytes) else content
	return _clip(f"Attached file {file.file_name}:\n{content}")


def build_prompt(text: str, files: list[dict], document: dict | None) -> str:
	parts = [text]
	if document:
		parts.append(document_context(document["doctype"], document["docname"]))
	parts.extend(file_context(file["file_url"]) for file in files)
	return "\n\n".join(parts)


def validate_attachments(files, document):
	if document and not (document.get("doctype") and document.get("docname")):
		frappe.throw(_("Document attachment is incomplete"))
	for file in files:
		if not file.get("file_url"):
			frappe.throw(_("File attachment is incomplete"))
