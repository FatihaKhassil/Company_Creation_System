# Copyright (c) 2025, Fatiha khassil and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestDocumentAnalysis(FrappeTestCase):
	def test_doctype_is_registered(self):
		meta = frappe.get_meta("Document Analysis")
		self.assertEqual(meta.name, "Document Analysis")
