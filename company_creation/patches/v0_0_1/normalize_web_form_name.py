import frappe


LEGACY_WEBFORM_NAME = "demande-de-création-d’entreprise"
TARGET_WEBFORM_NAME = "demande-de-creation-entreprise"
TARGET_ROUTE = "demande-de-creation-entreprise"


def execute():
	"""Normalize Web Form identifier to an ASCII-safe slug."""
	if not frappe.db.exists("Web Form", LEGACY_WEBFORM_NAME):
		return

	if frappe.db.exists("Web Form", TARGET_WEBFORM_NAME):
		# If target already exists, keep legacy unpublished to avoid duplicate public routes.
		frappe.db.set_value("Web Form", LEGACY_WEBFORM_NAME, "published", 0, update_modified=False)
		return

	frappe.rename_doc(
		"Web Form",
		LEGACY_WEBFORM_NAME,
		TARGET_WEBFORM_NAME,
		force=True,
		merge=False,
	)
	frappe.db.set_value("Web Form", TARGET_WEBFORM_NAME, "route", TARGET_ROUTE, update_modified=False)
