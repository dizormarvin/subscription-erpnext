
# -*- coding: utf-8 -*-
# Copyright (c) 2021, jeowsome and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from subscription.subscription.doctype.program_activation_request.program_activation_request import create_req_signature


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
	def get_contact_address(self):
		if not (self.address_line1 or self.customer_contact):
			address = frappe.db.sql(f"SELECT address_line1 from `tabAddress` where address_title like '%{self.customer_name}%'", as_dict=1)
			contact = frappe.db.sql(f"SELECT phone, first_name from `tabContact` where name like '%{self.customer_name}%'", as_dict=1)

			if address[0].get("address_line1"):
				self.db_set("address_line1", address[0].get("address_line1"), commit=True)

			if contact[0].get("phone") or contact[0].get("first_name"):
				self.db_set("customer_contact", contact[0].get("phone"), commit=True)
				self.db_set("contact_person", contact[0].get("first_name"), commit=True)

	@frappe.whitelist()
	def before_submit(self):
		if not self.signature:
			frappe.throw("Please sign first")

		for programs in self.get('included_programs'):
			programs.validate_activation()
		self.validate_package()

	def on_submit(self):
		self.validate_request()

	def validate_request(self):
		if self.activation_req:
			req = frappe.get_doc("Program Activation Request", self.activation_req)
			req.db_set("workflow_state", "Fulfilled")
			req.db_set("status", "Fulfilled")
			req.db_set("req_status", "Fulfilled")
			req.db_set("activation_ref", self.name)
			create_req_signature(self, dt="Program Activation")
			frappe.db.commit()

	def add_incl_program(self, psof_program, doc=None, packaged=0, from_req=0):
		if from_req:
			packaged = psof_program.get("from_package")
			data = {
				"package_name": psof_program.get("package_name") if packaged else None,
				"active": psof_program.get("current_status"),
				"psof": self.psof,
				"psof_program": psof_program.get("psof_program"),
				"from_package": packaged,
				"program": psof_program.get("program"),
				"action": psof_program.get("action"),
				"req_remarks": psof_program.get("remarks"),
				"req_date": psof_program.get("request_date")
			}
		else:
			data = {
				"package_name": psof_program.get("subscription_program") if packaged else None,
				"active": psof_program.get("active"),
				"psof": self.psof,
				"psof_program": psof_program.get("name"),
				"customer_name": psof_program.get("customer_name"),
				"from_package": packaged,
				"program": doc.get("program") if packaged else psof_program.get("subscription_program")
			}

		self.append("included_programs", data)

	def validate_package(self):
		if frappe.db.exists("Program Activation Item", {"parent": self.name, "from_package": 1}):
			packages = self.get_package_req({(i.get("package_name"), i.get("psof_program"), i.get("date_activation_de_activation")) for i in self.get("included_programs") if i.get("package_name")})
			for package in packages:
				if package.get("action"):
					psof_program = frappe.get_doc("PSOF Program", package.get("psof_program"))
					psof_program.update_status_description(action=package.get("action"), doc_name=self.name,
														   doc_modified=self.modified,
														   active=1 if package.get("action") == "Activate" else 0,
														   date=package.get("date"))

	def get_package_req(self, parent_packages):
		data = []
		for i in parent_packages:
			parent, program, date = i
			count_cond = frappe.db.count("Subscription Package Program", {"parent": parent})
			result = frappe.db.get_list("Program Activation Item", {"parent": self.name, "package_name": parent}, ["action"], pluck="action")
			activate = result.count("Activate")
			deactivate = result.count("Deactivate")
			data.append({
				"parent": parent,
				"psof_program": program,
				"action": "Activate" if activate >= 1 else "Deactivate" if deactivate == count_cond else None,
				"date": date
			})
		return data

	@frappe.whitelist()
	def load_req(self):
		if self.activation_req:
			req = frappe.get_doc("Program Activation Request", self.activation_req)
			self.db_set("customer_name", req.customer)
			self.db_set("psof", req.psof)
			self.get_contact_address()

			for program in req.get("programs"):
				self.add_incl_program(program, from_req=1)

	@frappe.whitelist()
	def load_psof_programs(self):
		psof_program = frappe.db.get_list("PSOF Program", {"parent": self.psof}, ["subscription_program", "active", "psof", "name", "customer_name", "is_package"])

		for program in psof_program:
			if program.get("is_package"):
				parent_pack = frappe.get_doc("Subscription Program", program.get("subscription_program"))
				for child in parent_pack.get("packaged_programs"):
					self.add_incl_program(program, child, 1)
			else:
				self.add_incl_program(program)


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

