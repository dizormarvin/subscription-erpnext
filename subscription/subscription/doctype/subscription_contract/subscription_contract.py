# -*- coding: utf-8 -*-
# Copyright (c) 2020, ossphin and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import today
from frappe.model.naming import parse_naming_series


class SubscriptionContract(Document):
    def autoname(self):
        if self.bill_expired and self.contract_number:
            prefix = "D"
            contract = self.contract_number.split("-")
            count = frappe.db.sql(f"""select count(name) as next_count from `tabSubscription Contract` where name like '{contract[0]}%' and name not like '%A%' and name like '%D%'""", as_dict=1)
            # count = frappe.db.count("Subscription Contract", {"contract_number": self.name})
            frappe.log_error(count, "Custom Script Error")

            if len(contract) > 1:
                start = 2 if len(contract[1]) > 2 else 1
                # self.name = f"{contract[0]}-{prefix}{int(contract[1][start:]) + count}"
                if self.amended_from:
                    self.name = f"{contract[0]}-{contract[1]}-{prefix}{count[0].get('next_count') + 1}"
                else:
                    self.name = f"{contract[0]}-{contract[1]}-{prefix}{count[0].get('next_count') + 1}"
            else:
                self.name = f"{contract[0]}-{prefix}{1}"

        if self.revised and self.reference_contract and self.contract_number:
            prefix = "A"
            contract = self.contract_number.split("-")

            # count = frappe.db.count("Subscription Contract", {"contract_number": ["like", contract[0]]})

            count = frappe.db.sql(f"""
                select count(name) as next_count from `tabSubscription Contract` where name like '{contract[0]}%' and name not like '%D%'
            """, as_dict=1)

            # self.name = f"{contract[0]}-{prefix}{count[0].get('next_count')}"
            #
            if len(contract) > 1:
                self.name = f"{contract[0]}-{contract[1]}-{prefix}{count[0].get('next_count')}"
            else:
                self.name = f"{contract[0]}-{prefix}{count[0].get('next_count')}"
        #
        # if frappe.db.exists("Subscription Contract", {"name": self.name, "bill_expired": 1}):
        #     self.make_sc_name()

    def make_sc_name(self):
        prefix = "D"
        contract = self.name.split("-")
        if len(contract) > 1:
            start = 2 if len(contract[1]) > 2 else 1
            self.name = f"{contract[0]}-{prefix}{int(contract[1][start:]) + 1}"

    def alter_dummy_bills(self):
        begin_date = self.start_date
        if not self.for_cb:
            if self.is_supersede:
                new_psof.supersede_date = self.supersede_date
            begin_date = self.supersede_date
        frappe.db.delete("PSOF Program Bill",
                         filters={"psof": self.psof, "date_from": [">=", begin_date]})
        return frappe.db.get_list("PSOF Program Bill",
                                  filters={"psof": self.psof, "date_from": ["<", begin_date]},
                                  pluck="name")

    def alter_amend_bills(self):
        begin_date = self.start_date
        # frappe.db.delete("PSOF Program Bill",
        #                  filters={"psof": self.psof, "date_from": [">=", begin_date]})
        return frappe.db.get_list("PSOF Program Bill",
                                  filters={"psof": self.psof, "date_from": [">=", begin_date]},
                                  pluck="name")

    def on_submit(self):
        if self.psof and self.bill_expired or self.is_supersede or self.for_cb:
            action = "Dummy" if self.bill_expired else "Superseded"
            old_psof = frappe.get_doc("PSOF", self.psof)

            new_psof = frappe.get_doc({
                "doctype": "PSOF",
                "subscription_contract": self.name,
                "remarks": f"{action} from Subscription Contract {old_psof.subscription_contract} - PSOF No. {old_psof.name}",
                "for_cb": self.for_cb
            })

            if self.is_supersede:
                new_psof.dummy_psof = old_psof.get("name")
                new_psof.dummy_contract = old_psof.get("subscription_contract")
                dummy_bills = self.alter_dummy_bills()

                for bill in dummy_bills:
                    dummy = frappe.get_doc("PSOF Program Bill", bill)
                    dummy.db_set("active", 0)
                    dummy.db_set("dummy_contract", old_psof.get("subscription_contract"))

            for program in old_psof.get("programs"):
                sub_programs = program.as_dict().copy()
                sub_programs["start_date"] = self.start_date
                sub_programs["supersede_date"] = self.supersede_date
                sub_programs["renewal"] = self.is_supersede
                sub_programs["end_date"] = self.expiry_date
                sub_programs["for_cb"] = self.for_cb
                sub_programs["bill_generated"] = 0
                sub_programs["include_in_bill_expired_until_renewed"] = self.bill_expired if not self.is_supersede else 0
                sub_programs["subscription_contract"] = self.name
                new_psof.append("programs", sub_programs)
            new_psof.save()
        self.sc_update_status()

        # 0ssphinc new feature new Sc
        if self.reference_contract:
            old_psof = frappe.get_doc("PSOF", self.psof)
            new_psof = frappe.get_doc({
                "doctype": "PSOF",
                "subscription_contract": self.name,
                "remarks": f"Amended from Subscription Contract {old_psof.subscription_contract} - PSOF No. {old_psof.name}",
                "for_cb": self.for_cb,
                "renewal": 0 if self.revised else 1
            })

            new_psof.dummy_psof = old_psof.get("name")
            new_psof.dummy_contract = old_psof.get("subscription_contract")
            amended_bill = self.alter_amend_bills()

            # Inactive Program BIll/View Bill
            for bill in amended_bill:
                amended = frappe.get_doc("PSOF Program Bill", bill)
                amended.db_set("active", 0)
                amended.db_set("dummy_contract", old_psof.get("subscription_contract"))

            for program in old_psof.get("programs"):
                sub_programs = program.as_dict().copy()
                sub_programs["start_date"] = self.start_date
                sub_programs["supersede_date"] = self.supersede_date
                sub_programs["renewal"] = 0 if self.revised or self.revised_expired else 1
                sub_programs["end_date"] = self.expiry_date
                sub_programs["for_cb"] = self.for_cb
                sub_programs["bill_generated"] = 0
                sub_programs["include_in_bill_expired_until_renewed"] = self.bill_expired if not self.is_supersede else 0
                sub_programs["subscription_contract"] = self.name
                new_psof.append("programs", sub_programs)
            new_psof.save()
        self.sc_update_new_status()

    def sc_update_new_status(self):
        if self.revised and self.contract_number:
            dummy_sc = frappe.get_doc("Subscription Contract", self.contract_number)
            if dummy_sc.revised:
                dummy_sc.db_set("status", "Inactive")
                dummy_sc.db_set("renewed", 1)
        # 0ssphinc end new feature new Sc

    def sc_update_status(self):
        if self.is_supersede and self.contract_number:
            dummy_sc = frappe.get_doc("Subscription Contract", self.contract_number)
            if dummy_sc.bill_expired:
                dummy_sc.db_set("status", "Inactive")
                dummy_sc.db_set("renewed", 1)
