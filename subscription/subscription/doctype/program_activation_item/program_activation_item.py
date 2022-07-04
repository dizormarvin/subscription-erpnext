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
        if self.action == "Activate":
            self.db_set("active", 1)
        else:
            self.db_set("active", 0)

    def update_bills(self):
        psof_program = frappe.get_doc("PSOF Program", self.psof_program)
        psof_program.update_status_description(action=self.action, doc_name=self.parent, doc_modified=self.modified,
                                               active=self.active, date=self.date_activation_de_activation)
