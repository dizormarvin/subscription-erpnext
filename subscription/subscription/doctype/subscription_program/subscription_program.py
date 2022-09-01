# -*- coding: utf-8 -*-
# Copyright (c) 2020, ossphin and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document


class SubscriptionProgram(Document):
	def map_accounts(self, program, rate):
		if program:
			item = self.get("program_name")
			ac = self.get("msf_ar_account")
			sc = self.get("msf_sales_account")
		else:
			item = self.get(f"{rate}_item")
			ac = self.get(f"{rate}_ar_account")
			sc = self.get(f"{rate}_sales_account")

		self.append("accounting_defaults", {
			"item_name": item,
			"ar_account": ac,
			"sales_account": sc,
			"parent": self.name,
			"vat_account": self.get("vat_account") if item == self.name else None
		})
		self.save()
