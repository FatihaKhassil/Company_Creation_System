# Copyright (c) 2025, Fatiha khassil and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestExtractedDataItem(FrappeTestCase):
	def test_doctype_is_registered(self):
		meta = frappe.get_meta("Extracted Data Item")
		self.assertEqual(meta.name, "Extracted Data Item")
