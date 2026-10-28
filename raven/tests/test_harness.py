import asyncio
import json
from types import SimpleNamespace

import frappe
from agents.tool_context import ToolContext
from frappe.tests import IntegrationTestCase

from raven.ai.chatbot_models import ChatbotChoice
from raven.ai.chatbot_stream import DATA_TOOL_NAME, specialist_tools
from raven.ai.harness.action_log_hooks import ActionLogHooks
from raven.ai.chatbot_stream import progress_reporter
from raven.ai.harness.progress import harness_status
from raven.ai.harness.document_drafts import DocumentDraft
from raven.ai.harness.document_tools import document_tools, request_approval
from raven.api.chatbot import get_chat
from raven.ai.harness.data_tools import MAX_OUTPUT_CHARACTERS, answer, data_tools

USER = "test1@example.com"


class TestHarness(IntegrationTestCase):
	def setUp(self):
		if not frappe.db.exists("User", USER):
			frappe.get_doc({"doctype": "User", "email": USER, "first_name": "Test", "roles": [{"role": "Raven User"}]}).insert()
		frappe.set_user(USER)

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_tool_names(self):
		self.assertEqual(
			[tool.name for tool in data_tools()],
			["describe_doctype", "list_documents", "count_documents", "get_document", "run_report"],
		)

	def test_a_failure_comes_back_as_an_error(self):
		def refuse():
			raise frappe.PermissionError("No permission")

		self.assertIn("error", json.loads(answer(refuse)))

	def test_a_success_is_returned_as_json(self):
		self.assertEqual(json.loads(answer(lambda: [{"total": 3}])), [{"total": 3}])

	def test_a_long_answer_is_cut(self):
		self.assertIn("[cut", answer(lambda: "x" * (MAX_OUTPUT_CHARACTERS + 10)))

	def test_the_user_cannot_read_what_their_role_does_not_allow(self):
		from raven.ai.harness.data_reader import DataReader

		with self.assertRaises(frappe.PermissionError):
			DataReader().describe("System Settings")

	def test_count_and_list_use_the_users_permissions(self):
		from raven.ai.harness.data_reader import DataReader

		reader = DataReader()
		self.assertTrue(reader.count("Role", None, "disabled"))
		self.assertLessEqual(len(reader.list("Role", None, ["name"], None, 5000)), 100)

	def test_the_data_assistant_is_offered_only_when_switched_on(self):
		settings = frappe.get_doc("Raven Settings")
		for switch in (0, 1):
			settings.db_set("chatbot_data_assistant", switch)
			frappe.clear_document_cache("Raven Settings", "Raven Settings")
			_, names = specialist_tools(ChatbotChoice("gpt-5", None))
			self.assertEqual(DATA_TOOL_NAME in names, bool(switch))


class TestActionLog(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.chat = frappe.get_doc({"doctype": "Raven Chatbot Chat", "title": "Log test"}).insert()

	def run_hooks(self, hooks):
		usage = SimpleNamespace(
			input_tokens=1200,
			input_tokens_details=SimpleNamespace(cached_tokens=1000),
			output_tokens=300,
			output_tokens_details=SimpleNamespace(reasoning_tokens=200),
		)
		agent = SimpleNamespace(name="Raven AI", model=SimpleNamespace(model="gpt-5"))
		context = SimpleNamespace(tool_call_id="call_1", tool_arguments='{"doctype": "User"}')
		tool = SimpleNamespace(name="list_documents")
		asyncio.run(self.simulate(hooks, agent, context, tool, usage))

	@staticmethod
	async def simulate(hooks, agent, context, tool, usage):
		await hooks.on_llm_start(context, agent, "instruction", [{"role": "user", "content": "hi"}])
		await hooks.on_llm_end(context, agent, SimpleNamespace(usage=usage, response_id="resp_1"))
		await hooks.on_tool_start(context, agent, tool)
		await hooks.on_tool_end(context, agent, tool, '{"error": "boom"}')

	def test_a_log_that_cannot_be_saved_does_not_raise(self):
		hooks = ActionLogHooks("No such chat", None)
		self.run_hooks(hooks)
		hooks.save_log()

	def test_model_and_tool_calls_are_saved_with_their_numbers(self):
		hooks = ActionLogHooks(self.chat.name, "high")
		self.run_hooks(hooks)
		hooks.flush()
		model, tool = frappe.get_all(
			"Raven AI Action Log", filters={"run": hooks.common["run"]}, fields=["*"], order_by="step asc"
		)
		self.assertEqual((model.kind, model.target, model.effort, model.step), ("Model call", "gpt-5", "high", 1))
		self.assertEqual((model.input_tokens, model.cached_input_tokens, model.output_tokens, model.reasoning_tokens), (1200, 1000, 300, 200))
		self.assertEqual((model.input_items, model.response_id), (1, "resp_1"))
		self.assertGreater(model.request_chars, len("instruction"))
		self.assertEqual((tool.kind, tool.target, tool.outcome, tool.result_chars), ("Tool call", "list_documents", "Failed", 17))
		self.assertEqual(json.loads(tool.arguments), {"doctype": "User"})
		self.assertEqual(tool.detail, '{"error": "boom"}')


class TestDocuments(IntegrationTestCase):
	"""Drafts and approvals, as a user who may work with ToDo documents."""

	def setUp(self):
		frappe.set_user("Administrator")
		self.chat = frappe.get_doc({"doctype": "Raven Chatbot Chat", "title": "Docs test"}).insert()
		self.drafts = DocumentDraft()

	def todo(self, **values):
		return frappe.get_doc({"doctype": "ToDo", "description": "Check the stock", **values}).insert()

	def test_preview_reports_a_problem_and_keeps_nothing(self):
		before = frappe.db.count("ToDo")
		result = self.drafts.preview("ToDo", {"description": "x", "reference_type": "DocType that does not exist", "reference_name": "y"})
		self.assertFalse(result["ok"])
		self.assertTrue(result["problems"])
		self.assertEqual(frappe.db.count("ToDo"), before)

	def test_preview_of_a_good_document_shows_what_the_system_fills_in(self):
		result = self.drafts.preview("ToDo", {"description": "Call the supplier"})
		self.assertTrue(result["ok"])
		self.assertEqual(result["document"]["priority"], "Medium")
		self.assertFalse(frappe.db.exists("ToDo", {"description": "Call the supplier"}))

	def test_prefilled_link_carries_simple_values_only(self):
		link = self.drafts.prefilled_link("ToDo", {"description": "A b", "children": [1]})["link"]
		self.assertEqual(link, "/app/todo/new?description=A%20b")

	def ask(self, action, names, values=None):
		request_approval(self.chat.name, action, "ToDo", names, values)
		return frappe.get_last_doc("Raven AI Pending Action")

	def test_asking_changes_nothing_until_approved(self):
		todo = self.todo()
		card = self.ask("Delete", [todo.name])
		self.assertEqual((card.status, card.chat), ("Pending", self.chat.name))
		self.assertTrue(frappe.db.exists("ToDo", todo.name))

	def test_approving_delete_and_bulk_update_do_the_work(self):
		first, second = self.todo(), self.todo()
		self.ask("Update", [first.name, second.name], {"priority": "High", "owner": "x@example.com"}).decide(True)
		self.assertEqual(frappe.db.get_value("ToDo", first.name, ["priority", "owner"]), ("High", "Administrator"))
		card = self.ask("Delete", [first.name])
		card.decide(True)
		self.assertEqual(card.status, "Approved")
		self.assertFalse(frappe.db.exists("ToDo", first.name))

	def test_rejecting_does_nothing_and_cannot_be_decided_twice(self):
		todo = self.todo()
		card = self.ask("Delete", [todo.name])
		card.decide(False)
		self.assertEqual(card.status, "Rejected")
		self.assertTrue(frappe.db.exists("ToDo", todo.name))
		with self.assertRaises(frappe.ValidationError):
			card.decide(True)

	def test_a_failure_changes_nothing(self):
		todo = self.todo()
		card = self.ask("Delete", [todo.name])
		frappe.delete_doc("ToDo", todo.name)
		card.decide(True)
		self.assertEqual(card.status, "Failed")

	def test_only_the_owner_decides(self):
		card = self.ask("Delete", [self.todo().name])
		frappe.set_user("test1@example.com")
		with self.assertRaises(frappe.PermissionError):
			card.decide(True)

	def test_asking_needs_permission_now(self):
		todo = self.todo()
		frappe.set_user("test1@example.com")
		with self.assertRaises(frappe.PermissionError):
			request_approval(self.chat.name, "Delete", "ToDo", [todo.name])

	def test_chat_lists_waiting_cards(self):
		self.ask("Delete", [self.todo().name])
		self.assertEqual([card["action"] for card in get_chat(self.chat.name)["actions"]], ["Delete"])

	def test_a_card_knows_which_answer_it_belongs_under(self):
		self.chat.append("messages", {"role": "user", "content": "one"})
		self.chat.append("messages", {"role": "assistant", "content": "answer"})
		self.chat.save()
		self.ask("Delete", [self.todo().name])
		self.assertEqual(get_chat(self.chat.name)["actions"][0]["message_position"], 2)

	def test_answered_cards_stay_with_their_outcome(self):
		approved, rejected = self.ask("Delete", [self.todo().name]), self.ask("Delete", [self.todo().name])
		approved.decide(True)
		rejected.decide(False)
		self.assertEqual([card["status"] for card in get_chat(self.chat.name)["actions"]], ["Approved", "Rejected"])


class TestProgressLines(IntegrationTestCase):
	def test_lines_name_the_work_but_not_the_values(self):
		args = json.dumps({"doctype": "Customer", "group_by": "customer_group", "filters": [["secret", "=", "x"]]})
		self.assertEqual(harness_status("count_documents", args), "Counting Customer by customer_group")
		self.assertEqual(harness_status("list_documents", args), "Checking data: Customer")
		self.assertNotIn("secret", harness_status("list_documents", args))

	def test_each_tool_has_a_line_and_unknown_ones_none(self):
		args = json.dumps({"doctype": "ToDo", "action": "Delete", "report_name": "Accounts Receivable", "name": "T1"})
		for tool in ("describe_doctype", "get_document", "run_report", "preview_document", "create_document", "open_prefilled_form", "submit_document", "cancel_document", "delete_documents", "update_documents"):
			self.assertTrue(harness_status(tool, args), tool)
		self.assertEqual(harness_status("delete_documents", args), "Asking you to approve: Delete ToDo")
		self.assertIsNone(harness_status("something_else", args))
		self.assertIsNone(harness_status("list_documents", "not json"))

	def test_the_reporter_reads_the_dict_events_the_sdk_sends(self):
		lines = []
		publisher = SimpleNamespace(status=lines.append)
		raw = SimpleNamespace(name="create_document", arguments=json.dumps({"doctype": "ToDo"}))
		event = {"event": SimpleNamespace(type="run_item_stream_event", item=SimpleNamespace(type="tool_call_item", raw_item=raw)), "agent": None}
		asyncio.run(progress_reporter(publisher)(event))
		asyncio.run(progress_reporter(publisher)({"event": SimpleNamespace(type="raw_response_event"), "agent": None}))
		self.assertEqual(lines, ["Asking you to approve: Create ToDo"])


class TestHeldByTheHarness(IntegrationTestCase):
	"""The tools for hard-to-undo changes never do the work, whatever the AI passes to them."""

	def setUp(self):
		frappe.set_user("Administrator")
		self.chat = frappe.get_doc({"doctype": "Raven Chatbot Chat", "title": "Held"}).insert()
		self.todo = frappe.get_doc({"doctype": "ToDo", "description": "Keep me"}).insert()

	def call(self, name, **arguments):
		tool = next(tool for tool in document_tools(self.chat.name) if tool.name == name)
		text = json.dumps(arguments)
		return asyncio.run(tool.on_invoke_tool(ToolContext(context=None, tool_name=name, tool_call_id="call", tool_arguments=text), text))

	def test_delete_and_update_only_make_cards(self):
		for name, arguments in (
			("delete_documents", {"doctype": "ToDo", "names": [self.todo.name]}),
			("update_documents", {"doctype": "ToDo", "names": [self.todo.name], "values": {"priority": "High"}}),
		):
			self.assertIn("approval", json.loads(self.call(name, **arguments))["state"])
		self.assertEqual(frappe.db.get_value("ToDo", self.todo.name, "priority"), "Medium")
		cards = get_chat(self.chat.name)["actions"]
		self.assertEqual([(card["action"], card["summary"]) for card in cards], [("Delete", ""), ("Update", "Priority: High")])

	def test_the_card_text_comes_from_the_real_values(self):
		self.call("update_documents", doctype="ToDo", names=[self.todo.name], values={"priority": "High", "owner": "x@example.com"})
		self.assertEqual(get_chat(self.chat.name)["actions"][0]["summary"], "Priority: High")

	def test_people_are_shown_by_name(self):
		self.call("update_documents", doctype="ToDo", names=[self.todo.name], values={"allocated_to": "Administrator"})
		self.assertEqual(get_chat(self.chat.name)["actions"][0]["summary"], f"Allocated To: {frappe.utils.get_fullname('Administrator')}")

	def test_create_checks_first_and_only_makes_a_card(self):
		before = frappe.db.count("ToDo")
		self.assertIn("approval", json.loads(self.call("create_document", doctype="ToDo", values={"description": "New one"}))["state"])
		self.assertEqual(frappe.db.count("ToDo"), before)
		self.assertEqual([card["action"] for card in get_chat(self.chat.name)["actions"]], ["Create"])

	def test_asking_again_for_the_same_thing_makes_no_second_card(self):
		for _attempt in range(2):
			self.call("create_document", doctype="ToDo", values={"description": "Once"})
		self.call("create_document", doctype="ToDo", values={"description": "Different"})
		self.assertEqual(len(get_chat(self.chat.name)["actions"]), 2)

	def test_an_invalid_new_document_gets_no_card_and_the_problem_goes_back_to_the_ai(self):
		result = json.loads(self.call("create_document", doctype="ToDo", values={"description": "x", "reference_type": "No Such DocType", "reference_name": "y"}))
		self.assertTrue(result["problems"])
		self.assertEqual(get_chat(self.chat.name)["actions"], [])

	def test_approving_create_makes_the_draft_and_the_card_points_at_it(self):
		self.call("create_document", doctype="ToDo", values={"description": "Made on approval"})
		card = frappe.get_last_doc("Raven AI Pending Action")
		card.decide(True)
		name = json.loads(card.names)[0]
		self.assertEqual(frappe.db.get_value("ToDo", name, ["description", "docstatus"]), ("Made on approval", 0))
		self.assertEqual(json.loads(get_chat(self.chat.name)["actions"][0]["names"]), [name])
