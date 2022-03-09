
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
			* 
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
	def activate(self):
		for a in self.included_programs:
			if a.action == "Activate":
				frappe.db.set_value('PSOF Program', a.psof_program, {
					'active': 1
				})
				frappe.db.set_value('PSOF Program', a.psof_program, {
					'program_status': f'<b>Status</b>: Activated from {self.name} on {self.modified}'
				})
				frappe.db.set_value('PSOF Program', a.psof_program, {
					'psof': self.psof
				})

				frappe.db.set_value('Program Activation Item', a.name, {
					'active': 1
				})

				bills = frappe.db.get_list('PSOF Program Bill', filters={
					'subscription_program': a.program,
					'psof': self.psof,
					'active': 1,
					"date_from": [">=", a.date_activation_de_activation]
				}, fields=['name'])

				for bill in bills:
					frappe.db.set_value('PSOF Program Bill', bill['name'], {
						'active': 1})

			elif a.action == "Deactivate":
				frappe.db.set_value('PSOF Program', a.psof_program, {
					'active': 0
				})
				frappe.db.set_value('PSOF Program', a.psof_program, {
					'program_status': f'Deactivated from {self.name} on {self.modified}'
				})
				frappe.db.set_value('PSOF Program', a.psof_program, {
					'psof': self.psof
				})

				frappe.db.set_value('Program Activation Item', a.name, {
					'active': 0
				})

				bills = frappe.db.get_list('PSOF Program Bill', filters={
					'subscription_program': a.program,
					'psof': self.psof,
					'active': 0,
					"date_from": [">=", a.date_activation_de_activation]
				}, fields=['name'])

				for bill in bills:
					frappe.db.set_value('PSOF Program Bill', bill['name'], {
						'active': 0})


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

