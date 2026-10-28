"""One-line progress for the data and document tools, shown in the chat while the AI works. Only names of document types,
reports and actions appear, never the values or filters."""

import json

from frappe import _


def harness_status(tool_name: str, arguments: str) -> str | None:
	"""e.g. "Checking data: Customer by customer_group"; None for a tool that has no line."""
	try:
		args = json.loads(arguments or "{}")
	except ValueError:
		return None
	doctype = args.get("doctype", "")
	lines = {
		"describe_doctype": lambda: _("Looking at the fields of {0}").format(doctype),
		"list_documents": lambda: _("Checking data: {0}").format(doctype),
		"count_documents": lambda: _("Counting {0} by {1}").format(doctype, args["group_by"]) if args.get("group_by") else _("Counting {0}").format(doctype),
		"get_document": lambda: _("Reading {0} {1}").format(doctype, args.get("name", "")),
		"run_report": lambda: _("Running report: {0}").format(args.get("report_name", "")),
		"preview_document": lambda: _("Checking the {0} before saving…").format(doctype),
		"create_document": lambda: _("Asking you to approve: Create {0}").format(doctype),
		"open_prefilled_form": lambda: _("Preparing a {0} form…").format(doctype),
		"assign_documents": lambda: _("Asking you to approve: Assign {0}").format(doctype),
		"tag_documents": lambda: _("Asking you to approve: Tag {0}").format(doctype),
		"share_documents": lambda: _("Asking you to approve: Share {0}").format(doctype),
		"attach_file": lambda: _("Asking you to approve: Attach a file to {0}").format(doctype),
		"unassign_documents": lambda: _("Asking you to approve: Unassign {0}").format(doctype),
		"untag_documents": lambda: _("Asking you to approve: Untag {0}").format(doctype),
		"unshare_documents": lambda: _("Asking you to approve: Unshare {0}").format(doctype),
		"detach_files": lambda: _("Asking you to approve: Remove an attachment from {0}").format(doctype),
		"submit_document": lambda: _("Asking you to approve: Submit {0}").format(doctype),
		"cancel_document": lambda: _("Asking you to approve: Cancel {0}").format(doctype),
		"delete_documents": lambda: _("Asking you to approve: Delete {0}").format(doctype),
		"update_documents": lambda: _("Asking you to approve: Update {0}").format(doctype),
	}
	return lines[tool_name]() if tool_name in lines else None
