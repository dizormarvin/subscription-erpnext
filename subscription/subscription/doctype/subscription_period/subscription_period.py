# -*- coding: utf-8 -*-
# Copyright (c) 2020, ossphin and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document


class SubscriptionPeriod(Document):
	def autoname(self):
		self.name = self.code

	def validate(self):
		self.check_date()
		self.check_used_period()

	def check_date(self):
		period_exists = frappe.db.exists("Subscription Period", {"start_date": self.start_date, "end_date": self.end_date})
		if self.start_date > self.end_date:
			frappe.throw("Please check subscription period dates")

		if period_exists:
			frappe.throw(f"Subscription Period from {self.get('start_date')} to {self.get('end_date')} already exists as {period_exists}")

	def check_used_period(self):
		if frappe.db.exists("Monthly PSOF", {"subscription_period": self.name, "docstatus": 1}):
			frappe.throw("Subscription Period already used in a submitted transaction")
