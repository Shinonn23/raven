import re

import frappe
import openai

from raven.ai.handler import get_variables_for_instructions


@frappe.whitelist(methods=["GET"])
def get_instruction_preview(instruction: str):
	"""
	Function to get the rendered instructions for the bot
	"""
	frappe.has_permission(doctype="Raven Bot", ptype="write", throw=True)

	# Only users who can edit Raven Bots reach this line. The renderer is sandboxed.
	# nosemgrep: frappe-ssti
	instructions = frappe.render_template(instruction, get_variables_for_instructions())
	return instructions


@frappe.whitelist()
def get_saved_prompts(bot: str = None):
	"""
	API to get the saved prompt for a user/bot/global
	"""
	or_filters = [["is_global", "=", 1], ["owner", "=", frappe.session.user]]

	prompts = frappe.get_list(
		"Raven Bot AI Prompt", or_filters=or_filters, fields=["name", "prompt", "is_global", "raven_bot"]
	)

	# Order by ones with the given bot
	prompts = sorted(prompts, key=lambda x: x.get("raven_bot") == bot, reverse=True)

	return prompts


@frappe.whitelist()
def get_open_ai_version():
	"""
	API to get the version of the OpenAI Python client
	"""
	frappe.has_permission(doctype="Raven Bot", ptype="read", throw=True)
	return openai.__version__


@frappe.whitelist()
def get_openai_available_models():
	"""
	API to get the available OpenAI models for agents (every conversational model the account can use)
	"""
	frappe.has_permission(doctype="Raven Bot", ptype="read", throw=True)
	return _openai_chat_model_ids()


# Models that are listed by OpenAI but cannot run a conversation.
NON_CHAT_MODEL_WORDS = (
	"embedding", "whisper", "tts", "dall-e", "image", "moderation", "realtime",
	"transcribe", "audio", "search", "davinci", "babbage", "sora", "computer-use",
)  # fmt: skip


MODEL_LIST_CACHE_KEY = "raven:openai_chat_models"
MODEL_LIST_CACHE_SECONDS = 6 * 60 * 60
DATED_SNAPSHOT = re.compile(r"-\d{4}-\d{2}-\d{2}$")


def _newest_first(model_id: str):
	"""GPT models before the rest, then the highest version first (gpt-6.1 > gpt-6 > gpt-5.5 > gpt-4o)."""
	return (model_id.startswith("gpt"), [int(number) for number in re.findall(r"\d+", model_id)], model_id)


def _without_dated_snapshots(model_ids: set[str]) -> set[str]:
	"""Hide "o4-mini-2025-04-16" when "o4-mini" is listed; the plain name always points at the latest snapshot."""
	return {model_id for model_id in model_ids if DATED_SNAPSHOT.sub("", model_id) == model_id or DATED_SNAPSHOT.sub("", model_id) not in model_ids}


def _openai_chat_model_ids() -> list[str]:
	"""Every model the OpenAI account lists that can hold a conversation, newest names first.
	Excluded by what a model cannot do, not by an allow-list of names, so new model families appear on their own.

	Asking OpenAI is slow, so the list is cached for a few hours per site. The key carries Raven Settings'
	`modified`, so saving settings (a new API key or organization) starts a fresh list straight away."""
	from raven.ai.openai_client import get_openai_models

	key = f"{MODEL_LIST_CACHE_KEY}:{frappe.get_cached_doc('Raven Settings').modified}"
	model_ids = frappe.cache.get_value(key)
	if model_ids is None:
		chat_models = {
			model.id for model in get_openai_models() if not any(word in model.id for word in NON_CHAT_MODEL_WORDS)
		}
		model_ids = sorted(_without_dated_snapshots(chat_models), key=_newest_first, reverse=True)
		frappe.cache.set_value(key, model_ids, expires_in_sec=MODEL_LIST_CACHE_SECONDS)
	return model_ids


@frappe.whitelist(methods=["GET"])
def get_chatbot_models() -> list[str]:
	"""Models the OpenAI account can use for the chatbot, for the picker in AI Settings."""
	frappe.has_permission("Raven Settings", ptype="write", throw=True)
	return _openai_chat_model_ids()


@frappe.whitelist()
def test_llm_configuration(
	provider: str = "OpenAI", api_url: str = None, local_llm_provider: str = None
):
	"""
	Test LLM configuration (OpenAI or Local LLM)
	"""
	frappe.has_permission(doctype="Raven Settings", ptype="write", throw=True)

	# Only System Managers choose which LLM server Raven talks to.
	# Anyone else (like a Raven Admin) can only test the saved one.
	if provider == "Local LLM" and "System Manager" not in frappe.get_roles():
		settings = frappe.get_cached_doc("Raven Settings")
		api_url, local_llm_provider = settings.local_llm_api_url, settings.local_llm_provider

	try:
		if provider == "Local LLM" and api_url:
			# Test local LLM endpoint
			import requests

			# Check if it's OpenAI Compatible and get API key
			api_key = None
			if local_llm_provider == "OpenAI Compatible":
				settings = frappe.get_single("Raven Settings")
				api_key = settings.get_password("openai_compatible_api_key")
				if not api_key:
					return {
						"success": False,
						"message": "OpenAI Compatible API Key is required",
					}

			if api_key:
				# Use OpenAI client for OpenAI Compatible services
				client = openai.OpenAI(api_key=api_key, base_url=api_url)
				models = client.models.list()
				return {
					"success": True,
					"message": f"Successfully connected to OpenAI Compatible service at {api_url}",
					"models": [{"id": m.id} for m in models.data],
				}
			else:
				# For other local LLM providers, use direct HTTP request
				response = requests.get(f"{api_url}/models", timeout=5)
				if response.status_code == 200:
					models = response.json()
					return {
						"success": True,
						"message": f"Successfully connected to {api_url}",
						"models": models.get("data", []),
					}
				else:
					return {
						"success": False,
						"message": f"Failed to connect to {api_url}. Status: {response.status_code}",
					}

		elif provider == "OpenAI":
			# Test OpenAI configuration
			from raven.ai.openai_client import get_open_ai_client

			client = get_open_ai_client()
			# Try to list models
			models = client.models.list()
			return {
				"success": True,
				"message": "Successfully connected to OpenAI",
				"models": [{"id": m.id} for m in models.data[:5]],  # Return first 5 models
			}

	except Exception as e:
		return {"success": False, "message": f"Connection failed: {str(e)}"}
