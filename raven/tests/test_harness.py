import asyncio
import json
from types import SimpleNamespace

import frappe
from frappe.tests import IntegrationTestCase

from raven.ai.chatbot_models import ChatbotChoice
from raven.ai.chatbot_stream import DATA_TOOL_NAME, specialist_tools
from raven.ai.harness.action_log_hooks import ActionLogHooks
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
