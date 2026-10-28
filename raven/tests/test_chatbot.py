import asyncio
import json
import threading
from contextlib import contextmanager
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from raven.ai import chatbot_stream
from raven.ai.chatbot_models import ChatbotChoice, resolve_choice
from raven.ai.manual_sources import ManualSource, configured_sources
from raven.ai.manual_tools import (
	MAX_RESPONSE_BYTES,
	MAX_RESULTS,
	call_manual,
	manual_status,
	manual_tools,
	run_tool,
)
from raven.ai.chatbot_stream import (
	_status_for,
	manual_instruction,
	build_instruction,
	build_orchestrator,
	default_instruction,
)
from raven.api.upload_file import get_attachable_files
from raven.api.chatbot import (
	get_chat_shares,
	get_chatbot_options,
	share_chat,
	unshare_chat,
	get_chat,
	get_chatbot_overview,
	get_recommended_documents,
	get_skills,
	send_message,
)

STREAM = "raven.raven_ai.doctype.raven_chatbot_chat.raven_chatbot_chat.stream_reply"
OWNER = "test1@example.com"
STRANGER = "test2@example.com"


def run_now(method, queue=None, timeout=None, enqueue_after_commit=None, **kwargs):
	frappe.get_attr(method)(**kwargs)


@contextmanager
def bot_answers(answer="Hello from the bot"):
	"""The bot streams `answer`; background jobs run inline so the test sees the saved reply."""
	with patch(STREAM, return_value=answer) as stream, patch("frappe.enqueue", side_effect=run_now):
		yield stream


class TestChatbot(IntegrationTestCase):
	def setUp(self):
		frappe.cache.delete_keys("raven:openai_chat_models")
		for email in (OWNER, STRANGER):
			self.make_raven_user(email)
		frappe.db.set_single_value("Raven Settings", "enable_ai_integration", 1)
		self.allow_models(("test-model", "low,medium,high"), ("plain-model", ""))
		self.no_manual_sources()
		self.bot = frappe.get_doc(
			{
				"doctype": "Raven Bot",
				"bot_name": "Chatbot Test Bot",
				"is_ai_bot": 1,
				"instruction": "Be helpful",
				"model": "local-model",
				"model_provider": "Local LLM",
			}
		).insert()
		frappe.set_user(OWNER)

	@staticmethod
	def allow_models(*rows):
		"""The admin's list of models users may pick; the first row is the default."""
		settings = frappe.get_doc("Raven Settings")
		settings.set("chatbot_models", [{"model": model, "efforts": efforts} for model, efforts in rows])
		settings.flags.ignore_permissions = True
		settings.save()
		frappe.clear_document_cache("Raven Settings", "Raven Settings")

	@staticmethod
	def no_manual_sources():
		"""The tests start from a site with no manual source and no data or document assistant, whatever the real site has set
		(the rollback restores it)."""
		settings = frappe.get_doc("Raven Settings")
		settings.set("manual_sources", [])
		settings.chatbot_data_assistant = settings.chatbot_document_assistant = 0
		settings.flags.ignore_permissions = True
		settings.save()
		frappe.clear_document_cache("Raven Settings", "Raven Settings")

	@staticmethod
	def make_raven_user(email):
		if not frappe.db.exists("User", email):
			frappe.get_doc(
				{"doctype": "User", "email": email, "first_name": email.split("@")[0], "send_welcome_email": 0}
			).insert()
		frappe.get_doc("User", email).add_roles("Raven User")

	def tearDown(self):
		frappe.cache.delete_keys("raven:openai_chat_models")
		frappe.set_user("Administrator")
		frappe.db.rollback()
		frappe.clear_document_cache("Raven Settings", "Raven Settings")

	def test_first_message_creates_a_chat_with_both_messages(self):
		with bot_answers() as ask_agent:
			chat = send_message("What is the status of order 5?")

		self.assertEqual(chat["title"], "What is the status of order 5?")
		self.assertEqual([m["role"] for m in chat["messages"]], ["user"])
		saved = get_chat(chat["name"])
		self.assertEqual([m["role"] for m in saved["messages"]], ["user", "assistant"])
		self.assertEqual(saved["messages"][1]["content"], "Hello from the bot")
		self.assertEqual(ask_agent.call_args.args[0], "What is the status of order 5?")

	def test_follow_up_sends_earlier_messages_as_history(self):
		with bot_answers("one"):
			chat = send_message("first")
		with bot_answers("two") as ask_agent:
			chat = send_message("second", chat=chat["name"])

		self.assertEqual(len(get_chat(chat["name"])["messages"]), 4)
		self.assertEqual(
			ask_agent.call_args.args[1],
			[{"role": "user", "content": "first"}, {"role": "assistant", "content": "one"}],
		)

	def test_chat_can_belong_to_a_project(self):
		project = frappe.get_doc({"doctype": "Raven Chatbot Project", "title": "Reports"}).insert()
		with bot_answers():
			chat = send_message("hi", project=project.name)

		overview = get_chatbot_overview()
		self.assertEqual(overview["projects"][0]["title"], "Reports")
		self.assertEqual(overview["chats"][0]["project"], project.name)
		self.assertEqual(overview["chats"][0]["name"], chat["name"])

	def test_empty_message_is_rejected(self):
		self.assertRaises(frappe.ValidationError, send_message, "   ")

	def test_other_users_cannot_read_or_write_the_chat(self):
		with bot_answers():
			chat = send_message("private")

		frappe.set_user(STRANGER)
		self.assertEqual(get_chatbot_overview()["chats"], [])
		self.assertRaises(frappe.PermissionError, get_chat, chat["name"])
		with bot_answers():
			self.assertRaises(frappe.PermissionError, send_message, "hi", chat["name"])

	def test_deleting_a_project_deletes_its_chats(self):
		project = frappe.get_doc({"doctype": "Raven Chatbot Project", "title": "Temp"}).insert()
		with bot_answers():
			chat = send_message("hi", project=project.name)
		frappe.delete_doc("Raven Chatbot Project", project.name)
		self.assertFalse(frappe.db.exists("Raven Chatbot Chat", chat["name"]))


class TestChatbotAttachmentsAndSkills(TestChatbot):
	__test__ = True
	def make_note(self, title="Secret note"):
		return frappe.get_doc({"doctype": "Note", "title": title, "content": "launch plan"}).insert()

	def test_attached_document_reaches_the_model_and_is_remembered(self):
		note = self.make_note()
		with bot_answers() as ask_agent:
			chat = send_message("summarise", document={"doctype": "Note", "docname": note.name})
			send_message("again", chat=chat["name"], document={"doctype": "Note", "docname": note.name})

		self.assertIn("launch plan", ask_agent.call_args_list[0].args[0])
		self.assertEqual(chat["messages"][0]["document"], {"doctype": "Note", "docname": note.name})
		recommended = get_recommended_documents()
		self.assertEqual((recommended[0]["docname"], recommended[0]["use_count"]), (note.name, 2))

	def test_cannot_attach_a_document_the_user_cannot_read(self):
		note = self.make_note()
		frappe.set_user(STRANGER)
		frappe.db.delete("DocShare", {"share_doctype": "Note", "share_name": note.name})
		with bot_answers() as ask_agent:
			with patch("frappe.has_permission", return_value=False):
				self.assertRaises(
					frappe.PermissionError,
					send_message,
					"read it",
					None,
					None,
					None,
					{"doctype": "Note", "docname": note.name},
				)
		ask_agent.assert_not_called()

	def test_recommendations_drop_documents_that_are_gone(self):
		note = self.make_note()
		with bot_answers():
			send_message("hi", document={"doctype": "Note", "docname": note.name})
		frappe.delete_doc("Note", note.name, force=True)
		self.assertEqual(get_recommended_documents(), [])

	def test_personal_skills_are_private_and_company_skills_are_admin_only(self):
		mine = frappe.get_doc(
			{"doctype": "Raven Chatbot Skill", "title": "Mine", "command": "/My-Skill", "prompt": "do x"}
		).insert()
		self.assertEqual(mine.command, "my-skill")
		with self.assertRaises(frappe.PermissionError):
			frappe.get_doc(
				{"doctype": "Raven Chatbot Skill", "title": "Co", "command": "co", "prompt": "p", "is_company": 1}
			).insert()

		frappe.set_user("Administrator")
		frappe.get_doc(
			{"doctype": "Raven Chatbot Skill", "title": "Co", "command": "co", "prompt": "p", "is_company": 1}
		).insert()
		frappe.set_user(STRANGER)
		self.assertEqual([skill.command for skill in get_skills()], ["co"])
		frappe.set_user(OWNER)
		self.assertEqual(sorted(skill.command for skill in get_skills()), ["co", "my-skill"])

	def test_bad_command_is_rejected(self):
		skill = frappe.get_doc(
			{"doctype": "Raven Chatbot Skill", "title": "Bad", "command": "has space", "prompt": "p"}
		)
		self.assertRaises(frappe.ValidationError, skill.insert)

	def test_attachable_files_only_list_what_the_user_may_read(self):
		private = frappe.get_doc(
			{"doctype": "File", "file_name": "mine.txt", "content": "x", "is_private": 1}
		).insert()
		frappe.set_user(STRANGER)
		self.assertNotIn(private.file_url, [file.file_url for file in get_attachable_files()])
		frappe.set_user(OWNER)
		self.assertIn(private.file_url, [file.file_url for file in get_attachable_files("mine")])


class TestChatbotSharing(TestChatbot):
	__test__ = True

	def raven_user_of(self, email):
		return frappe.db.get_value("Raven User", {"user": email}, "name")

	def make_chat(self):
		with bot_answers():
			return send_message("shared question")["name"]

	def test_shared_chat_is_readable_by_the_recipient_only_after_sharing(self):
		chat = self.make_chat()
		frappe.set_user(STRANGER)
		self.assertRaises(frappe.PermissionError, get_chat, chat)

		frappe.set_user(OWNER)
		share_chat(chat, self.raven_user_of(STRANGER))
		frappe.set_user(STRANGER)
		shared = get_chat(chat)
		self.assertEqual((shared["owner"], shared["can_write"]), (OWNER, False))
		self.assertIn(chat, [c.name for c in get_chatbot_overview()["chats"]])

	def test_view_only_recipient_cannot_post_but_editor_can(self):
		chat = self.make_chat()
		share_chat(chat, self.raven_user_of(STRANGER))
		frappe.set_user(STRANGER)
		with bot_answers():
			self.assertRaises(frappe.PermissionError, send_message, "hi", chat)

		frappe.set_user(OWNER)
		share_chat(chat, self.raven_user_of(STRANGER), can_write=True)
		frappe.set_user(STRANGER)
		with bot_answers():
			reply = send_message("my turn", chat)
		self.assertEqual(get_chat(chat)["messages"][-2]["owner"], STRANGER)

	def test_only_the_owner_can_share_and_unsharing_revokes_access(self):
		chat = self.make_chat()
		share_chat(chat, self.raven_user_of(STRANGER))
		frappe.set_user(STRANGER)
		self.assertRaises(frappe.PermissionError, share_chat, chat, self.raven_user_of(OWNER))
		self.assertRaises(frappe.PermissionError, get_chat_shares, chat)

		frappe.set_user(OWNER)
		unshare_chat(chat, STRANGER)
		frappe.set_user(STRANGER)
		self.assertRaises(frappe.PermissionError, get_chat, chat)

	def test_bots_cannot_be_given_access(self):
		chat = self.make_chat()
		self.assertRaises(frappe.ValidationError, share_chat, chat, self.bot.raven_user)


class TestChatbotStreaming(TestChatbot):
	__test__ = True

	def test_failed_answer_is_saved_as_an_apology_and_reported(self):
		with patch(STREAM, side_effect=RuntimeError("model down")), patch(
			"frappe.enqueue", side_effect=run_now
		), patch("frappe.publish_realtime") as publish, patch("frappe.log_error"):
			chat = send_message("hello")

		messages = get_chat(chat["name"])["messages"]
		self.assertEqual(messages[-1]["role"], "assistant")
		self.assertIn("could not answer", messages[-1]["content"])
		publish.assert_called_with("chatbot_done", {"chat": chat["name"], "failed": True}, user=OWNER)

	def test_text_is_published_in_batches_to_the_asking_user(self):
		from raven.ai.chatbot_stream import DeltaPublisher

		publisher = DeltaPublisher("CHAT-1")
		with patch("frappe.publish_realtime") as publish:
			for word in ("a", "b", "c"):
				publisher.add(word)
			publisher.flush()

		sent = "".join(call.args[1]["text"] for call in publish.call_args_list)
		self.assertEqual(sent, "abc")
		self.assertLess(publish.call_count, 3)
		self.assertEqual(publish.call_args.kwargs["user"], OWNER)


class TestChatbotOrchestrator(TestChatbot):
	__test__ = True

	def make_specialist(self, name, description, available=1):
		frappe.set_user("Administrator")  # only admins manage agents
		return frappe.get_doc(
			{
				"doctype": "Raven Bot",
				"bot_name": name,
				"is_ai_bot": 1,
				"instruction": f"You handle {name}",
				"model": "local-model",
				"model_provider": "Local LLM",
				"description": description,
				"allow_orchestrator_to_call": available,
			}
		).insert()

	def build(self, choice=None):
		from agents import Agent

		class FakeManager:
			def __init__(self, bot):
				self.bot = bot

			def create_agent(self):
				return Agent(name=self.bot.bot_name, instructions=self.bot.instruction)

		with patch("raven.ai.chatbot_stream.RavenAgentManager", FakeManager):
			return build_orchestrator(choice or ChatbotChoice("test-model", None))

	def test_only_agents_marked_available_become_tools(self):
		self.make_specialist("Accounting Helper", "Answers questions about invoices")
		self.make_specialist("Secret Agent", "Not for the chatbot", available=0)

		agent, names = self.build()

		self.assertEqual({tool.name for tool in agent.tools}, {"Accounting_Helper"})
		self.assertEqual(names, {"Accounting_Helper": "Accounting Helper"})
		self.assertEqual(agent.tools[0].description, "Answers questions about invoices")

	def test_orchestrator_uses_the_built_in_or_the_admins_instruction_plus_context(self):
		built_in = self.build()[0].instructions
		self.assertTrue(built_in.startswith(default_instruction()))
		self.assertIn("# Current context", built_in)

		frappe.db.set_single_value("Raven Settings", "chatbot_instruction", "Be terse.")
		frappe.clear_document_cache("Raven Settings", "Raven Settings")
		replaced = self.build()[0].instructions
		self.assertTrue(replaced.startswith("Be terse."))
		self.assertNotIn(default_instruction()[:60], replaced)
		self.assertIn("# Current context", replaced)

	def test_context_names_the_user_and_today_after_the_fixed_text(self):
		instruction = build_instruction()
		fixed, _, context = instruction.partition("# Current context")
		self.assertEqual(fixed.strip(), default_instruction())
		self.assertIn(frappe.utils.get_fullname(OWNER), context)
		self.assertIn(frappe.utils.getdate().strftime("%A, %d %B %Y"), context)

	def test_built_in_instruction_has_no_maintainer_comments_and_covers_the_rules(self):
		text = default_instruction()
		self.assertNotIn("<!--", text)
		for rule in ("Never invent", "explicit", "permissions of the person", "do not yet have a company knowledge base", "same step", "manual assistant"):
			self.assertIn(rule, text)

	def test_agent_offered_to_the_chatbot_needs_a_description(self):
		frappe.set_user("Administrator")
		bot = frappe.get_doc(
			{
				"doctype": "Raven Bot",
				"bot_name": "Mute",
				"is_ai_bot": 1,
				"instruction": "x",
				"model": "m",
				"model_provider": "Local LLM",
				"allow_orchestrator_to_call": 1,
			}
		)
		self.assertRaises(frappe.ValidationError, bot.insert)

	def test_sending_needs_a_chatbot_model(self):
		self.allow_models()
		with bot_answers() as stream:
			self.assertRaises(frappe.ValidationError, send_message, "hi")
		stream.assert_not_called()

	def test_status_names_the_specialist_being_asked(self):
		from types import SimpleNamespace

		def event(kind, tool):
			return SimpleNamespace(type="run_item_stream_event", item=SimpleNamespace(type=kind, raw_item=SimpleNamespace(name=tool)))

		known = {"Accounting_Helper": "Accounting Helper"}
		self.assertEqual(_status_for(event("tool_call_item", "Accounting_Helper"), known), "Asking Accounting Helper…")
		self.assertIsNone(_status_for(event("tool_call_item", "other_tool"), known))
		self.assertIsNone(_status_for(event("message_output_item", "Accounting_Helper"), known))


class TestChatbotModels(TestChatbot):
	__test__ = True

	def test_lists_only_models_that_can_chat_for_settings_editors(self):
		from types import SimpleNamespace

		from raven.api.ai_features import get_chatbot_models

		listed = [SimpleNamespace(id=name) for name in ("gpt-a", "gpt-b", "text-embedding-x", "whisper-1", "dall-e-3", "gpt-a")]
		frappe.set_user("Administrator")
		with patch("raven.ai.openai_client.get_openai_models", return_value=listed):
			self.assertEqual(get_chatbot_models(), ["gpt-b", "gpt-a"])

		frappe.set_user(OWNER)
		with patch("raven.ai.openai_client.get_openai_models", return_value=listed):
			self.assertRaises(frappe.PermissionError, get_chatbot_models)

	def test_agent_model_list_is_not_limited_to_old_model_families(self):
		from types import SimpleNamespace

		from raven.api.ai_features import get_openai_available_models

		listed = [SimpleNamespace(id=name) for name in ("gpt-4o", "gpt-6.1-terra", "o4-mini", "text-embedding-3", "tts-1")]
		frappe.set_user("Administrator")
		with patch("raven.ai.openai_client.get_openai_models", return_value=listed):
			self.assertEqual(get_openai_available_models(), ["gpt-6.1-terra", "gpt-4o", "o4-mini"])

	def test_model_list_is_cached_until_settings_change(self):
		from types import SimpleNamespace

		from raven.api.ai_features import get_openai_available_models

		frappe.set_user("Administrator")
		with patch("raven.ai.openai_client.get_openai_models", return_value=[SimpleNamespace(id="gpt-a")]) as listing:
			get_openai_available_models()
			get_openai_available_models()
			self.assertEqual(listing.call_count, 1)

			frappe.db.set_single_value("Raven Settings", "openai_project_id", "proj_changed")
			frappe.clear_document_cache("Raven Settings", "Raven Settings")
			get_openai_available_models()
			self.assertEqual(listing.call_count, 2)

	def test_a_failed_lookup_is_not_cached(self):
		from raven.api.ai_features import get_openai_available_models

		frappe.set_user("Administrator")
		with patch("raven.ai.openai_client.get_openai_models", side_effect=frappe.ValidationError("no key")):
			self.assertRaises(frappe.ValidationError, get_openai_available_models)
		self.assertIsNone(frappe.cache.get_value(f"raven:openai_chat_models:{frappe.get_cached_doc('Raven Settings').modified}"))

	def test_model_list_is_newest_first_without_redundant_dated_snapshots(self):
		from types import SimpleNamespace

		from raven.api.ai_features import get_openai_available_models

		names = ["gpt-5.5", "gpt-5.5-2026-04-23", "gpt-6-sol", "gpt-6.1-terra", "gpt-4o", "o3", "o3-2025-04-16", "gpt-4o-2024-08-06", "o1-2024-12-17"]
		frappe.set_user("Administrator")
		with patch("raven.ai.openai_client.get_openai_models", return_value=[SimpleNamespace(id=name) for name in names]):
			# "o1-2024-12-17" stays: no plain "o1" is listed to stand in for it.
			self.assertEqual(
				get_openai_available_models(),
				["gpt-6.1-terra", "gpt-6-sol", "gpt-5.5", "gpt-4o", "o3", "o1-2024-12-17"],
			)


class TestChatbotModelChoice(TestChatbot):
	__test__ = True

	def chosen_by_stream(self, **pick):
		with bot_answers() as stream:
			send_message("hi", **pick)
		return stream.call_args.args[3]

	def test_defaults_to_the_first_allowed_model_with_a_medium_effort(self):
		self.assertEqual(self.chosen_by_stream(), ChatbotChoice("test-model", "medium"))

	def test_a_models_without_efforts_runs_without_one(self):
		self.assertEqual(self.chosen_by_stream(model="plain-model"), ChatbotChoice("plain-model", None))

	def test_the_users_pick_is_used_when_the_admin_allows_it(self):
		self.assertEqual(self.chosen_by_stream(model="test-model", effort="high"), ChatbotChoice("test-model", "high"))

	def test_picks_the_admin_did_not_allow_are_refused_and_nothing_runs(self):
		with bot_answers() as stream:
			self.assertRaises(frappe.PermissionError, send_message, "hi", model="gpt-secret")
			self.assertRaises(frappe.PermissionError, send_message, "hi", model="test-model", effort="max")
			self.assertRaises(frappe.PermissionError, send_message, "hi", model="plain-model", effort="low")
		stream.assert_not_called()

	def test_options_list_what_the_admin_allows_in_order(self):
		self.assertEqual(
			get_chatbot_options()["models"],
			[{"model": "test-model", "efforts": ["low", "medium", "high"]}, {"model": "plain-model", "efforts": []}],
		)

	def test_the_chosen_effort_reaches_the_agents_model_settings(self):
		agent, _specialists = TestChatbotOrchestrator.build(self, ChatbotChoice("test-model", "high"))
		self.assertEqual(agent.model_settings.reasoning.effort, "high")
		agent, _specialists = TestChatbotOrchestrator.build(self, ChatbotChoice("plain-model", None))
		# No effort picked: the SDK's own default for the model is left alone.
		from agents import Agent

		self.assertEqual(agent.model_settings.reasoning, Agent(name="x").model_settings.reasoning)

	def test_settings_reject_duplicates_and_unknown_efforts(self):
		frappe.set_user("Administrator")
		self.assertRaises(frappe.ValidationError, self.allow_models, ("a", ""), ("a", ""))
		self.assertRaises(frappe.ValidationError, self.allow_models, ("a", "low,ultra"))
		self.allow_models(("a", " low , high "))
		self.assertEqual(resolve_choice().effort, "low")
		self.assertEqual(frappe.get_cached_doc("Raven Settings").chatbot_models[0].efforts, "low,high")


class FakeResponse:
	def __init__(self, status=200, body=b""):
		self.status_code, self.body, self.closed = status, body, False

	def iter_content(self, size):
		for start in range(0, len(self.body), size):
			yield self.body[start : start + size]

	def close(self):
		self.closed = True


def invoke(tool, **arguments):
	"""Run a function tool the way the SDK does, with a tool context."""
	from agents.tool_context import ToolContext

	text = json.dumps(arguments)
	context = ToolContext(None, tool_name=tool.name, tool_call_id="call-1", tool_arguments=text)
	return tool.on_invoke_tool(context, text)


class TestManualTools(TestChatbot):
	__test__ = True

	def setUp(self):
		super().setUp()
		self.manual = ManualSource("manual", "How to use the system", "https://manual.example", "key1", "secret1")
		self.uat = ManualSource("uat", "UAT test guides", "https://uat.example", "key2", "secret2")

	def reply(self, payload, status=200):
		return FakeResponse(status, json.dumps(payload).encode())

	def test_a_call_carries_the_key_and_never_follows_redirects(self):
		with patch("requests.get", return_value=self.reply({"message": [{"title": "ลา"}]})) as get:
			result = call_manual(self.manual, "search", {"query": "ขอลา", "space": None, "limit": 3})
		self.assertEqual(result, [{"title": "ลา"}])
		args, kwargs = get.call_args
		self.assertEqual(args[0], "https://manual.example/api/method/manual_search.search")
		self.assertEqual(kwargs["params"], {"query": "ขอลา", "limit": 3})  # the empty space is left out
		self.assertEqual(kwargs["headers"], {"Authorization": "token key1:secret1"})
		self.assertFalse(kwargs["allow_redirects"])
		self.assertTrue(kwargs["timeout"])

	def test_failures_come_back_as_errors_the_model_can_read(self):
		forbidden = {"_server_messages": json.dumps([json.dumps({"message": "Not permitted"})])}
		with patch("requests.get", return_value=self.reply(forbidden, 403)):
			self.assertIn("403: Not permitted", run_tool({"manual": self.manual}, "manual", "search", query="x"))
		import requests

		with patch("requests.get", side_effect=requests.ConnectionError("down")):
			self.assertIn("Could not reach manual", run_tool({"manual": self.manual}, "manual", "search", query="x"))
		with patch("requests.get", return_value=FakeResponse(200, b"<html>not json</html>")):
			self.assertIn("not an answer", run_tool({"manual": self.manual}, "manual", "get_page", route="a/b"))
		self.assertIn("Use one of: manual", run_tool({"manual": self.manual}, "nope", "search", query="x"))

	def test_an_oversized_answer_is_refused_and_the_connection_closed(self):
		big = FakeResponse(200, b"x" * (MAX_RESPONSE_BYTES + 10))
		with patch("requests.get", return_value=big):
			self.assertIn("too much data", run_tool({"manual": self.manual}, "manual", "get_page", route="a/b"))
		self.assertTrue(big.closed)

	def test_each_tool_asks_its_own_method_and_limits_its_arguments(self):
		tools = {tool.name: tool for tool in manual_tools([self.manual, self.uat])}
		self.assertEqual(set(tools), {"list_manual_spaces", "search_manual", "read_manual_page"})
		self.assertIn("uat = UAT test guides", tools["search_manual"].description)
		with patch("requests.get", return_value=self.reply({"message": []})) as get:
			asyncio.run(invoke(tools["search_manual"], source="uat", query="ขาย", limit=99))
			asyncio.run(invoke(tools["read_manual_page"], source="manual", route="basics/desk", offset=-5))
		first, second = get.call_args_list
		self.assertTrue(first.args[0].startswith("https://uat.example/") and first.args[0].endswith("manual_search.search"))
		self.assertEqual(first.kwargs["params"]["limit"], MAX_RESULTS)
		self.assertEqual(second.kwargs["params"]["offset"], 0)  # a negative offset becomes the start of the page

	def test_several_tool_calls_in_one_step_run_at_the_same_time(self):
		tools = {tool.name: tool for tool in manual_tools([self.manual])}
		started, release = threading.Event(), threading.Event()
		calls = []

		def slow_get(url, **kwargs):
			calls.append(url)
			if len(calls) == 2:
				release.set()
			started.set()
			self.assertTrue(release.wait(5), "the second call never started while the first was waiting")
			return self.reply({"message": []})

		async def both():
			await asyncio.gather(*(invoke(tools["search_manual"], source="manual", query="x") for _ in range(2)))

		with patch("requests.get", side_effect=slow_get):
			asyncio.run(both())
		self.assertEqual(len(calls), 2)

	def test_status_lines_name_the_query_and_the_page(self):
		self.assertEqual(manual_status("search_manual", json.dumps({"source": "manual", "query": "ขอลา"})), "Searching manual: ขอลา")
		self.assertEqual(manual_status("read_manual_page", json.dumps({"route": "basics/desk"})), "Reading basics/desk")
		self.assertIsNone(manual_status("other", "{}"))
		self.assertIsNone(manual_status("search_manual", "not json"))


class TestManualSources(TestChatbot):
	__test__ = True

	def save_sources(self, *rows):
		frappe.set_user("Administrator")
		settings = frappe.get_doc("Raven Settings")
		settings.set("manual_sources", [dict(source_name=n, base_url=u, description="d", api_key="k", api_secret=s) for n, u, s in rows])
		settings.flags.ignore_permissions = True
		settings.save()
		frappe.clear_document_cache("Raven Settings", "Raven Settings")

	def test_the_address_is_cleaned_and_names_are_unique(self):
		self.save_sources(("manual", " https://manual.example/ ", "s1"))
		self.assertEqual(configured_sources()[0].base_url, "https://manual.example")
		self.assertRaises(frappe.ValidationError, self.save_sources, ("a", "https://x.example", "s"), ("a", "https://y.example", "s"))
		self.assertRaises(frappe.ValidationError, self.save_sources, ("a", "ftp://x.example", "s"))
		self.assertRaises(frappe.ValidationError, self.save_sources, ("a", "manual.example", "s"))

	def test_the_secret_is_stored_encrypted_and_survives_a_save_with_the_masked_value(self):
		self.save_sources(("manual", "https://manual.example", "the-real-secret"))
		self.assertEqual(configured_sources()[0].api_secret, "the-real-secret")
		row = frappe.get_doc("Raven Settings").manual_sources[0]
		self.assertNotEqual(row.api_secret, "the-real-secret")  # what a client reads is masked
		settings = frappe.get_doc("Raven Settings")
		settings.manual_sources[0].api_secret = row.api_secret  # the form sends back what it was shown
		settings.flags.ignore_permissions = True
		settings.save()
		frappe.clear_document_cache("Raven Settings", "Raven Settings")
		self.assertEqual(configured_sources()[0].api_secret, "the-real-secret")


class TestManualPictures(TestManualSources):
	__test__ = True

	def test_the_chat_may_load_pictures_only_from_the_manual_sites(self):
		self.save_sources(
			("manual", "https://manual.example/", "s1"),
			("uat", "https://uat.manual.example/some/path", "s2"),
			("again", "https://manual.example", "s3"),
		)
		frappe.set_user(OWNER)
		self.assertEqual(
			get_chatbot_options()["manual_origins"], ["https://manual.example", "https://uat.manual.example"]
		)

	def test_no_manual_source_means_no_picture_host(self):
		self.save_sources()
		frappe.set_user(OWNER)
		self.assertEqual(get_chatbot_options()["manual_origins"], [])

	def test_the_instructions_tell_it_how_to_choose_and_keep_pictures(self):
		text = manual_instruction()
		for phrase in ("# Pictures", "![text](address)", "Never write or change an address", "At most 4", "กรอบ 9–10"):
			self.assertIn(phrase, text)
		self.assertIn("keep them exactly as given", chatbot_stream.default_instruction())


class TestManualAssistant(TestChatbotOrchestrator):
	__test__ = True

	def sources(self):
		return [ManualSource("manual", "How to use the system", "https://manual.example", "k", "s")]

	def build_with_sources(self, choice=None):
		with patch("raven.ai.chatbot_stream.configured_sources", return_value=self.sources()):
			return self.build(choice)

	def test_the_manual_assistant_is_a_tool_only_when_a_source_is_set(self):
		self.assertNotIn("manual_assistant", {tool.name for tool in self.build()[0].tools})
		agent, names = self.build_with_sources()
		self.assertIn("manual_assistant", {tool.name for tool in agent.tools})
		self.assertEqual(names["manual_assistant"], "the manuals")

	def test_agents_work_in_a_loop_and_can_call_tools_together(self):
		agent, _names = self.build_with_sources(ChatbotChoice("test-model", "high"))
		self.assertTrue(agent.model_settings.parallel_tool_calls)
		self.assertEqual(agent.model_settings.reasoning.effort, "high")
		self.assertGreaterEqual(chatbot_stream.MAX_TURNS, 30)
		self.assertGreaterEqual(chatbot_stream.SPECIALIST_MAX_TURNS, 20)

	def test_the_researcher_knows_its_sources_and_keeps_its_own_instruction(self):
		with patch("raven.ai.chatbot_stream.working_agent", wraps=lambda name, instruction, choice: __import__("agents").Agent(name=name, instructions=instruction)) as make:
			chatbot_stream.manual_assistant_tool(self.sources(), ChatbotChoice("test-model", "high"))
		name, instruction, choice = make.call_args.args
		self.assertEqual(name, "Manual Assistant")
		self.assertIn("- manual: How to use the system", instruction)
		self.assertTrue(instruction.startswith(manual_instruction()))
		self.assertIsNone(choice.effort)  # research does not need the effort the user picked for the conversation

	def test_the_researchers_instruction_describes_a_loop_and_parallel_searches(self):
		text = manual_instruction()
		self.assertNotIn("<!--", text)
		for phrase in ("loop", "at the same time", "Sources:", "never repeat a query", "not instructions"):
			self.assertIn(phrase, text)

	def test_running_out_of_steps_ends_the_reply_politely(self):
		from agents.exceptions import MaxTurnsExceeded

		with patch(STREAM, side_effect=MaxTurnsExceeded("too many")), patch("frappe.enqueue", side_effect=run_now), patch(
			"frappe.publish_realtime"
		) as publish:
			chat = send_message("do everything")
		self.assertIn("more steps", get_chat(chat["name"])["messages"][-1]["content"])
		publish.assert_called_with("chatbot_done", {"chat": chat["name"], "failed": True}, user=OWNER)
