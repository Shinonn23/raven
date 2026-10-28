"""Tools that let the chatbot read the company's manuals: search, read a page, list the spaces. Each manual site (the apps
connect_diagnostics_manual and connect_diagnostics_uat_manual) serves /api/method/manual_search.<name> behind an API key.

The tools never raise: a failure comes back as {"error": ...} so the model can change its query or try another source.
They are plain synchronous functions; the Agents SDK runs each in its own thread, so several calls in one step go out together."""

import json

import requests
from agents import FunctionTool, function_tool
from frappe import _

from raven.ai.manual_sources import ManualSource

TIMEOUT_SECONDS = 25
MAX_RESPONSE_BYTES = 300_000
MAX_RESULTS = 10


class ManualError(Exception):
	"""A call to a manual site failed; the message is written for the model to read."""


def describe_failure(status: int, body: bytes) -> str:
	"""What a Frappe error response says, in a line."""
	try:
		data = json.loads(body)
		messages = json.loads(data.get("_server_messages") or "[]")
		if messages:
			return json.loads(messages[0]).get("message", "")[:300]
		return str(data.get("exception") or data.get("message") or "")[:300] or f"HTTP {status}"
	except ValueError:
		return f"HTTP {status}"


def call_manual(source: ManualSource, method: str, params: dict):
	"""GET one method of a manual site and return its `message`. Redirects are not followed (the key would travel with them)."""
	try:
		response = requests.get(
			f"{source.base_url}/api/method/manual_search.{method}",
			params={key: value for key, value in params.items() if value not in (None, "")},
			headers={"Authorization": f"token {source.api_key}:{source.api_secret}"},
			timeout=TIMEOUT_SECONDS,
			allow_redirects=False,
			stream=True,
		)
	except requests.RequestException as error:
		raise ManualError(f"Could not reach {source.name}: {type(error).__name__}") from error
	try:
		body, size = [], 0
		for part in response.iter_content(8192):
			size += len(part)
			if size > MAX_RESPONSE_BYTES:
				raise ManualError(f"{source.name} sent too much data; ask for a narrower search or a later part of the page.")
			body.append(part)
	finally:
		response.close()
	raw = b"".join(body)
	if response.status_code != 200:
		raise ManualError(f"{source.name} answered {response.status_code}: {describe_failure(response.status_code, raw)}")
	try:
		return json.loads(raw)["message"]
	except (ValueError, KeyError) as error:
		raise ManualError(f"{source.name} sent something that is not an answer.") from error


def run_tool(sources: dict[str, ManualSource], source: str, method: str, **params) -> str:
	"""Call a manual and return JSON text for the model, or {"error": ...}."""
	if source not in sources:
		return json.dumps({"error": f"Unknown source {source!r}. Use one of: {', '.join(sources)}."})
	try:
		return json.dumps(call_manual(sources[source], method, params), ensure_ascii=False)
	except ManualError as error:
		return json.dumps({"error": str(error)}, ensure_ascii=False)


def manual_tools(sources: list[ManualSource]) -> list[FunctionTool]:
	"""The three tools over these sources. The source names and what each covers go in the tool descriptions."""
	by_name = {source.name: source for source in sources}
	listing = "; ".join(f"{source.name} = {source.description}" for source in sources)

	@function_tool(
		name_override="list_manual_spaces",
		description_override=f"List the manuals (spaces) of a source with their route and page count. Sources: {listing}",
	)
	def list_manual_spaces(source: str) -> str:
		return run_tool(by_name, source, "list_spaces")

	@function_tool(
		name_override="search_manual",
		description_override=(
			"Search a source for pages that answer a question. Returns up to `limit` pages with title, heading, a snippet, route and URL. "
			"Search in Thai or with the system's English names (DocType, field, button). Pass `space` (a route from list_manual_spaces) to narrow it. "
			f"Sources: {listing}"
		),
	)
	def search_manual(source: str, query: str, space: str | None = None, limit: int = 5) -> str:
		return run_tool(by_name, source, "search", query=query, space=space, limit=min(max(limit, 1), MAX_RESULTS))

	@function_tool(
		name_override="read_manual_page",
		description_override=(
			"Read a page of a source as Markdown, by its route from search_manual. A long page comes in parts: if `next_offset` is not null, "
			"call again with offset=next_offset to read on."
		),
	)
	def read_manual_page(source: str, route: str, offset: int = 0) -> str:
		return run_tool(by_name, source, "get_page", route=route, offset=max(offset, 0))

	return [list_manual_spaces, search_manual, read_manual_page]


def manual_status(tool_name: str, arguments: str) -> str | None:
	"""A short progress line for a tool call of the manual assistant, e.g. "Searching manual: ขอลาป่วย"."""
	try:
		args = json.loads(arguments or "{}")
	except ValueError:
		return None
	if tool_name == "search_manual":
		return _("Searching {0}: {1}").format(args.get("source", ""), args.get("query", ""))
	if tool_name == "read_manual_page":
		return _("Reading {0}").format(args.get("route", ""))
	return None
