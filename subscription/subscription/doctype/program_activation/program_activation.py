
# -*- coding: utf-8 -*-
# Copyright (c) 2021, ossphin and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document


class ProgramActivation(Document):
	@frappe.whitelist()
	def get_programs(self):
		prog = frappe.db.sql(f"""
		SELECT 
			subscription_program,
			active,
			parent,
			name,
			customer_name
		FROM 
			`tabPSOF Program` 
		WHERE 
			parent = '{self.psof}'
		GROUP BY 
			subscription_program;""", as_dict=1)

		for p in prog:
			self.append('included_programs', {
				"program": p.subscription_program,
				"active": p.active,
				"psof": p.psof,
				"psof_program": p.name,
				"customer_name": p.customer_name
			})

	@frappe.whitelist()
	def before_submit(self):
		for programs in self.get('included_programs'):
			programs.validate_activation()


@frappe.whitelist()
def get_program_serials(doctype, txt, searchfield, start, page_len, filters):

	serials = frappe.db.sql(f"""
	SELECT 
		stock.serial_no, stock.item_code 
	FROM `tabStock Entry Detail` stock 
		LEFT JOIN `tabProgram Activation Item` program
		ON stock.item_code LIKE program.program
	WHERE stock.customer = '{filters['customer']}';""")

	return serials

