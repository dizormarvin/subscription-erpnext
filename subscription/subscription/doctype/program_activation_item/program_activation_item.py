# -*- coding: utf-8 -*-
# Copyright (c) 2021, ossphin and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document


class ProgramActivationItem(Document):

    def validate_activation(self):
        self.update_activation_status()
        self.update_bills()

    def update_activation_status(self): 
        self.db_set("active", self.action == "Activate")

    def update_bills(self):
        if not self.from_package:
            psof_program = frappe.get_doc("PSOF Program", self.psof_program)
            psof_program.update_status_description(action=self.action, doc_name=self.parent, doc_modified=self.modified,
                                                   active=self.active, date=self.date_activation_de_activation)