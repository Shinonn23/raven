"""The manual sites the chatbot may read, as set in Raven Settings. Kept apart from manual_tools so saving the settings
does not load the AI libraries."""

from dataclasses import dataclass
from urllib.parse import urlsplit

import frappe
from frappe import _


@dataclass(frozen=True)
class ManualSource:
	name: str
	description: str
	base_url: str
	api_key: str
	api_secret: str


def validate_manual_sources(rows):
	"""Saved in Raven Settings: each name once, and an http(s) address with no trailing slash."""
	seen = set()
	for row in rows:
		row.source_name = (row.source_name or "").strip()
		if row.source_name in seen:
			frappe.throw(_("Manual source {0} is listed twice.").format(row.source_name))
		seen.add(row.source_name)
		url = urlsplit((row.base_url or "").strip())
		if url.scheme not in ("http", "https") or not url.netloc:
			frappe.throw(_("The site URL of {0} must start with https:// (or http://).").format(row.source_name))
		row.base_url = f"{url.scheme}://{url.netloc}{url.path}".rstrip("/")


def configured_sources() -> list[ManualSource]:
	rows = frappe.get_cached_doc("Raven Settings").manual_sources
	return [
		ManualSource(row.source_name, row.description or "", row.base_url, row.api_key or "", row.get_password("api_secret", raise_exception=False) or "")
		for row in rows
	]




def manual_origins() -> list[str]:
	"""scheme://host of every configured manual site: the only places the chat loads pictures from."""
	origins = []
	for row in frappe.get_cached_doc("Raven Settings").manual_sources:
		url = urlsplit((row.base_url or "").strip())
		origin = f"{url.scheme}://{url.netloc}"
		if url.netloc and origin not in origins:
			origins.append(origin)
	return origins
