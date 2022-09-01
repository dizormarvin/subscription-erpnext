# Copyright (c) 2022, ossphin and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class MonthlyPSOFProgramBill(Document):
	def make_sales_invoice(self):
		invoice = frappe.get_doc({
			"doctype": "Sales Invoice",
			"customer": self.get("customer"),
			"due_date": self.get("contract_end"),
			"taxes_and_charges": "Philippines Tax - CB",
			"m_psof": self.parent,
			"date_from": self.get("date_from"),
			"date_to": self.get("date_to"),
			"subs_period": self.get("subscription_period"),
			"psof": self.get("psof"),
			"subs_contract": self.get("contract"),
			"contract_start": self.get("contract_start"),
			"contract_end": self.get("contract_end"),
			"m_psof_name": self.get("name"),
			"debit_to": "11070005 - ACCTS. REC. - TRADE (ND) - CB",
		})
		invoice.append("items", {
			"item_name": self.get("subscription_program"),
			"qty": 1,
			"description": self.get("subscription_program"),
			"uom": "Nos",
			"conversion_factor": 1,
			"rate": self.get("subscription_rate"),
			'income_account': frappe.get_doc("Subscription Program", self.get("subscription_program")).get(
				"msf_sales_account")
		})

		for rate in ("decoder", "card", "promo", "freight"):
			if self.get(f"{rate}_rate") > 0:
				invoice.append("items", self.add_invoice_item(rate))

		invoice.save()
		self.db_set("si_no", invoice.get("name"))

	def add_invoice_item(self, rate):
		program = frappe.get_doc("Subscription Program", self.get("subscription_program"))

		for accounts in program.get("accounting_defaults"):
			if rate in accounts.get("item_group").lower():
				return {
					"item_name": accounts.get("item_name"),
					"qty": 1,
					"description": accounts.get("item_name"),
					"uom": accounts.get("uom"),
					"conversion_factor": 1,
					"rate": self.get(f"{rate}_rate"),
					'income_account': accounts.get("sales_account")
				}
