import base64
import json
from pathlib import Path

import frappe
from frappe import _

READABLE_EXTENSIONS = {"txt", "md", "csv", "json"}
IMAGE_TYPES = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp", "gif": "image/gif"}
MAX_IMAGE_BYTES = 5_000_000
MAX_CONTEXT_CHARACTERS = 8000


def _clip(text: str) -> str:
	return text[:MAX_CONTEXT_CHARACTERS]


def document_context(doctype: str, docname: str) -> str:
	"""The document as text for the model. Raises if the current user may not read it."""
	doc = frappe.get_doc(doctype, docname)
	doc.check_permission("read")
	return _clip(f"Document {doctype} {docname}:\n{json.dumps(doc.as_dict(), default=str, indent=1)}")


def extension_of(file_name: str | None) -> str:
	return (file_name or "").rsplit(".", 1)[-1].lower()


def image_inputs(files: list[dict]) -> list[dict]:
	"""The attached pictures as model input, so the model can see them. Raises if the user may not read one; skips very large ones."""
	images = []
	for attached in files:
		file = frappe.get_doc("File", {"file_url": attached["file_url"]})
		file.check_permission("read")
		kind = IMAGE_TYPES.get(extension_of(file.file_name))
		content = Path(file.get_full_path()).read_bytes() if kind else b""
		if kind and 0 < len(content) <= MAX_IMAGE_BYTES:
			encoded = base64.b64encode(content).decode()
			images.append({"type": "input_image", "image_url": f"data:{kind};base64,{encoded}", "detail": "auto"})
	return images


def file_context(file_url: str) -> str:
	"""A file's name, plus its content when it is plain text. Raises if the user may not read it."""
	file = frappe.get_doc("File", {"file_url": file_url})
	file.check_permission("read")
	extension = extension_of(file.file_name)
	if extension in IMAGE_TYPES:
		return f"Attached image: {file.file_name} (you can see it; file_url: {file.file_url})"
	if extension not in READABLE_EXTENSIONS:
		return f"Attached file: {file.file_name} (content not readable as text; file_url: {file.file_url})"
	content = file.get_content()
	content = content.decode(errors="replace") if isinstance(content, bytes) else content
	return _clip(f"Attached file {file.file_name} (file_url: {file.file_url}):\n{content}")


ATTACHED_ONLY_REQUEST = (
	"The user attached this without writing a message. Look at it, say briefly what it is, and offer what you can do with it."
)


def build_prompt(text: str, files: list[dict], document: dict | None, reply_to: str | None = None) -> str:
	parts = [f'(You had asked the user: "{reply_to}")'] if reply_to else []
	parts.append(text or ATTACHED_ONLY_REQUEST)
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
