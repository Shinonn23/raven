from dataclasses import dataclass

import frappe
from frappe import _

# Reasoning efforts OpenAI accepts, lowest to highest.
EFFORTS = ("none", "minimal", "low", "medium", "high", "xhigh", "max")
PREFERRED_DEFAULT_EFFORT = "medium"


@dataclass(frozen=True)
class ChatbotChoice:
	model: str
	effort: str | None


def efforts_of(row) -> list[str]:
	return [effort.strip() for effort in (row.efforts or "").split(",") if effort.strip()]


def validate_chatbot_models(rows):
	"""Saved in Raven Settings: each model once, with efforts OpenAI knows about."""
	seen = set()
	for row in rows:
		row.model = (row.model or "").strip()
		if row.model in seen:
			frappe.throw(_("Chatbot model {0} is listed twice.").format(row.model))
		seen.add(row.model)
		unknown = [effort for effort in efforts_of(row) if effort not in EFFORTS]
		if unknown:
			frappe.throw(_("Unknown effort {0} for {1}. Use: {2}.").format(", ".join(unknown), row.model, ", ".join(EFFORTS)))
		row.efforts = ",".join(efforts_of(row))


def allowed_models() -> list[dict]:
	"""What users may pick in the chatbot, as set by an admin in Raven Settings. The first row is the default."""
	rows = frappe.get_cached_doc("Raven Settings").chatbot_models
	return [{"model": row.model, "efforts": efforts_of(row)} for row in rows]


def resolve_choice(model: str | None = None, effort: str | None = None) -> ChatbotChoice:
	"""The model and effort to run: the user's pick if the admin allows it, otherwise the defaults.
	An explicit pick that is not allowed is refused, never silently swapped."""
	settings = frappe.get_cached_doc("Raven Settings")
	if not settings.enable_ai_integration:
		frappe.throw(_("AI Integration is not enabled"))
	options = allowed_models()
	if not options:
		frappe.throw(_("No chatbot models are available. Ask an admin to add some in Raven Settings → AI."))

	chosen = next((option for option in options if option["model"] == model), None) if model else options[0]
	if not chosen:
		frappe.throw(_("The model {0} is not available in the chatbot.").format(model), frappe.PermissionError)

	efforts = chosen["efforts"]
	if effort and effort not in efforts:
		frappe.throw(_("The effort {0} is not available for {1}.").format(effort, chosen["model"]), frappe.PermissionError)
	if effort or not efforts:
		return ChatbotChoice(chosen["model"], effort or None)
	return ChatbotChoice(chosen["model"], PREFERRED_DEFAULT_EFFORT if PREFERRED_DEFAULT_EFFORT in efforts else efforts[0])
