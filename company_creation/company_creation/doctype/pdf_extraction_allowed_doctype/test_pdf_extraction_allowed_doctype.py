# Copyright (c) 2025, Fatiha khassil and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestPDFExtractionAllowedDoctype(FrappeTestCase):
	def test_doctype_is_registered(self):
		meta = frappe.get_meta("PDF Extraction Allowed Doctype")
		self.assertEqual(meta.name, "PDF Extraction Allowed Doctype")
