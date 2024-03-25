# -*- coding: utf-8 -*-
# Copyright (c) 2021, jeowsome and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import datetime
from frappe import _, qb
from frappe.model.mapper import get_mapped_doc
from frappe.model.document import Document
from subscription.subscription.doctype.program_activation_request.program_activation_request import create_req_signature
from datetime import datetime


class ProgramActivation(Document):
    @frappe.whitelist()
    def make_material_request(self, program_items):
        material_request = frappe.new_doc("Material Request")
        material_request.material_request_type = 'Material Issue'
        # material_request.set_warehouse = 'All Warehouses - CB'
        material_request.schedule_date = datetime.now()
        material_request.customer_program_activation = self.customer_name
        material_request.parent_program_activation = self.name
        for item in program_items:
            material_request.append("items", {
                "item_code": item,
                "item_name": item,
                "qty": 1,
                "description": item,
                "uom": 'Unit',
                "stock_uom": 'Unit'
            })
        return material_request.as_dict()

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
            address = frappe.db.sql(
                f"SELECT address_line1 from `tabAddress` where address_title like '%{self.customer_name}%'", as_dict=1)
            contact = frappe.db.sql(
                f"SELECT phone, first_name from `tabContact` where name like '%{self.customer_name}%'", as_dict=1)

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

        is_check = 0
        ird_serialno = psof_program.get("ird_model_serialno") if psof_program.get("ird_model_serialno") else None

        if ird_serialno:
            unit_addr = frappe.db.get_value('Serial No', ird_serialno, 'unit_address', as_dict=1)
        else:
            unit_addr = {'unit_address': ''}

        if psof_program.get("decoder_allocation_active") or psof_program.get("card_allocation_active"):
            is_check = 1

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
                "req_date": psof_program.get("request_date"),
                "is_check": is_check,

                "ird_model": psof_program.get("ird_model") if psof_program.get("ird_model") else None,
                "ird_model_serialno": psof_program.get("ird_model_serialno") if psof_program.get("ird_model_serialno") else None,
                "smart_card": psof_program.get("smart_card") if psof_program.get("smart_card") else None,
                "smart_card_serialno": psof_program.get("smart_card_serialno") if psof_program.get("smart_card_serialno") else None,
                "cam": psof_program.get("cam") if psof_program.get("cam") else None,
                "cam_serialno": psof_program.get("cam_serialno") if psof_program.get("cam_serialno") else None,

                "unit_address": unit_addr.get('unit_address') if unit_addr.get('unit_address') else None
            }
        else:
            data = {
                "package_name": psof_program.get("subscription_program") if packaged else None,
                "active": psof_program.get("active"),
                "psof": self.psof,
                "psof_program": psof_program.get("name"),
                "customer_name": psof_program.get("customer_name"),
                "from_package": packaged,
                "program": doc.get("program") if packaged else psof_program.get("subscription_program"),
                "is_check": is_check,

                "ird_model": psof_program.get("ird_model") if psof_program.get("ird_model") else None,
                "ird_model_serialno": psof_program.get("ird_model_serialno") if psof_program.get(
                    "ird_model_serialno") else None,
                "smart_card": psof_program.get("smart_card") if psof_program.get("smart_card") else None,
                "smart_card_serialno": psof_program.get("smart_card_serialno") if psof_program.get(
                    "smart_card_serialno") else None,
                "cam": psof_program.get("cam") if psof_program.get("cam") else None,
                "cam_serialno": psof_program.get("cam_serialno") if psof_program.get("cam_serialno") else None,

                "unit_address": unit_addr.get('unit_address') if unit_addr.get('unit_address') else None
            }

        self.append("included_programs", data)

    def validate_package(self):
        if frappe.db.exists("Program Activation Item", {"parent": self.name, "from_package": 1}):
            packages = self.get_package_req(
                {(i.get("package_name"), i.get("psof_program"), i.get("date_activation_de_activation")) for i in
                 self.get("included_programs") if i.get("package_name")})
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
            result = frappe.db.get_list("Program Activation Item", {"parent": self.name, "package_name": parent},
                                        ["action"], pluck="action")
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
        psof_program = frappe.db.get_list("PSOF Program", {"parent": self.psof},
                                          ["subscription_program", "active", "psof", "name", "customer_name",
                                           "is_package", "decoder_allocation_active", "card_allocation_active"])

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


# OSSPHINC CUSTOM MATERIAL REQUEST
# @frappe.whitelist()
# def check_material_request_link(program_activation_name):
#     query = frappe.db.sql(f"""
#     SELECT
#         parent_program_activation
#     FROM `tabMaterial Request`
#     WHERE parent_program_activation = '{program_activation_name}' limit 1;""", as_dict=1)
#     if query:
#         return query

# # OSS Custom get mapped
# @frappe.whitelist()
# def create_material_request(source_name, target_doc=None):
#     def update_item(obj, target, source_parent):
#         # ITEM
#         target.qty = 10
#         target.item_code = "NICKELODEON IRD"
#
#     def set_missing_values(source, target):
#         # HEADER
#         target.material_request_type = 'Material Issue'
#
#     doclist = get_mapped_doc(
#         "Program Activation",
#         source_name,
#         {
#             "Program Activation": {
#                 "doctype": "Material Request",
#                 "field_map": {
#                     # "material_request_type": "Material Issue",
#                 },
#                 "validation": {
#                     "docstatus": ["=", 1]
#                 },
#             },
#             "Program Activation Item": {
#                 "doctype": "Material Request Item",
#                 "field_map": {
#                     # "name": "sales_order_item",
#                     # "parent": "sales_order",
#                     # "uom": "stock_uom",
#                 },
#                 "postprocess": update_item,
#                 # "condition": lambda doc: (flt(doc.qty) - flt(doc.transferred_qty)) > 0,
#             },
#         },
#         target_doc,
#         set_missing_values,
#     )
#
#     return doclist
