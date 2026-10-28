"""The data tools of the AI, as function tools. A failure comes back as {"error": ...} so the model can change its query.
They are synchronous: the Agents SDK runs each in its own thread, and the threads share one database connection, so reads take turns."""

import json
import threading

from agents import FunctionTool, function_tool

from raven.ai.harness.data_reader import DataReader

MAX_OUTPUT_CHARACTERS = 60_000
DATABASE_TURN = threading.Lock()


def answer(read) -> str:
	"""Run `read` and give the model JSON text (cut when very long) or an error."""
	try:
		with DATABASE_TURN:
			text = json.dumps(read(), ensure_ascii=False, default=str)
	except Exception as error:
		return json.dumps({"error": str(error)[:300]}, ensure_ascii=False)
	if len(text) > MAX_OUTPUT_CHARACTERS:
		return text[:MAX_OUTPUT_CHARACTERS] + " ... [cut: ask for fewer fields or rows, or add filters]"
	return text


def data_tools(reader: DataReader | None = None) -> list[FunctionTool]:
	reader = reader or DataReader()

	@function_tool(
		strict_mode=False,
		name_override="describe_doctype",
		description_override="The fields of a DocType (name, label, type, options, required) the user may read. Use it before filtering or choosing fields.",
	)
	def describe_doctype(doctype: str) -> str:
		return answer(lambda: reader.describe(doctype))

	@function_tool(
		strict_mode=False,
		name_override="list_documents",
		description_override=(
			"List documents of a DocType the user may read: up to 100 rows. `filters` is a Frappe filter list such as "
			'[["status","=","Open"],["posting_date",">=","2026-01-01"]]; use ["field","is","not set"] to find missing values. '
			"`fields` are fieldnames; `order_by` is like \"modified desc\"."
		),
	)
	def list_documents(
		doctype: str, filters: list | None = None, fields: list[str] | None = None, order_by: str | None = None, limit: int = 20
	) -> str:
		return answer(lambda: reader.list(doctype, filters, fields, order_by, limit))

	@function_tool(
		strict_mode=False,
		name_override="count_documents",
		description_override=(
			"Count documents, in total or per value of `group_by` (one fieldname), most frequent first. "
			"To find duplicates, group by the field and look at the values with a total above 1."
		),
	)
	def count_documents(doctype: str, filters: list | None = None, group_by: str | None = None) -> str:
		return answer(lambda: reader.count(doctype, filters, group_by))

	@function_tool(
		strict_mode=False,
		name_override="get_document",
		description_override="Read one whole document, with its tables, by DocType and name.",
	)
	def get_document(doctype: str, name: str) -> str:
		return answer(lambda: reader.get(doctype, name))

	@function_tool(
		strict_mode=False,
		name_override="run_report",
		description_override="Run a report by its name with filters as an object, e.g. {\"company\": \"X\", \"from_date\": \"2026-01-01\"}. Returns columns and up to 200 rows.",
	)
	def run_report(report_name: str, filters: dict | None = None) -> str:
		return answer(lambda: reader.report(report_name, filters))

	return [describe_doctype, list_documents, count_documents, get_document, run_report]
