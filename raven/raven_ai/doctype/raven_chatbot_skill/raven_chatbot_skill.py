import re

import frappe
from frappe import _
from frappe.model.document import Document

COMMAND_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")
COMPANY_SKILL_ROLES = {"Raven Admin", "System Manager"}


class RavenChatbotSkill(Document):
	def validate(self):
		self.command = (self.command or "").strip().lstrip("/").lower()
		if not COMMAND_PATTERN.match(self.command):
			frappe.throw(_("Command may only contain lowercase letters, numbers and hyphens."))
		if self.is_company and not COMPANY_SKILL_ROLES & set(frappe.get_roles()):
			frappe.throw(_("Only a Raven Admin can create a company skill."), frappe.PermissionError)


def skill_query(user):
	user = user or frappe.session.user
	if COMPANY_SKILL_ROLES & set(frappe.get_roles(user)):
		return ""
	return f"(`tabRaven Chatbot Skill`.is_company = 1 or `tabRaven Chatbot Skill`.owner = {frappe.db.escape(user)})"


def skill_has_permission(doc, user=None, ptype=None):
	user = user or frappe.session.user
	if ptype == "read" and doc.is_company:
		return True
	return doc.owner == user or bool(COMPANY_SKILL_ROLES & set(frappe.get_roles(user)))
