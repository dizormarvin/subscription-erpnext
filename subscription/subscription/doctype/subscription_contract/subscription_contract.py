# -*- coding: utf-8 -*-
# Copyright (c) 2020, ossphin and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import today
from frappe.model.naming import parse_naming_series


class SubscriptionContract (Document):
    def autoname(self):
        if self.is_supersede and self.contract_number:
            prefix = "S"
            if self.bill_expired:
                prefix = "SD"
            contract = self.contract_number.split("-")
            if len(contract) > 1:
                start = 2 if len(contract[1]) > 2 else 1
                self.name = f"{contract[0]}-{prefix}{int(contract[1][start:]) + 1}"
            else:
                self.name = f"{contract[0]}-{prefix}{1}"
        elif not self.is_supersede and self.bill_expired:
            self.name = f'{parse_naming_series("SC.######", doc=self)}-D'

    def on_submit(self):
        if self.is_supersede and self.psof:
            old_contract = frappe.get_doc("Subscription Contract", self.contract_number)
            old_contract.db_set("supersede_date", today())

            frappe.db.delete("PSOF Program Bill", filters={"psof": self.psof, "date_from": [">=", self.start_date]})
            old_psof = frappe.get_doc("PSOF", self.psof)
            old_psof.adjust_program_dates(self.start_date, self.name)
            new_psof = frappe.get_doc({
                "doctype": "PSOF",
                "subscription_contract": self.name,
                "remarks": f"Superseded from Subscription Contract {old_psof.subscription_contract} - PSOF No. {old_psof.name}"
            })

            for program in old_psof.get("programs"):
                sub_programs = program.as_dict().copy()
                sub_programs["start_date"] = self.start_date
                sub_programs["end_date"] = self.expiry_date
                new_psof.append("programs", sub_programs)
            new_psof.save()
