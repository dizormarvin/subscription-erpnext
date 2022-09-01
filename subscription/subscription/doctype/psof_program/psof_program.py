# -*- coding: utf-8 -*-
# Copyright (c) 2020, ossphin and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import flt, rounded


def evaluate_cond(dif):
    return "None" if dif == 0 else "UNDER" if dif < 0 else "OVER"


def diff(period, cost):
    allocation = flt((cost  / period), 2)
    return flt(cost - (allocation * period), 2)


class PSOFProgram(Document):

    def get_name(self):
        return self.name

    def validate(self):
        self.update_amounts()

    def update_status_description(self, action, doc_name, doc_modified, active, date):
        frappe.db.set_value('PSOF Program', self.name, {
            'program_status': f'<b>Status</b>: {action}d from {doc_name} on {doc_modified}',
            'active': active
        })
        self.set_programs_status(action, date)

    def set_generated(self):
        status = []
        status.append("Active") if self.active else status.append("Inactive")
        status.append("Bill Generated") if self.bill_generated else status.append("")
        self.db_set("program_status", f"<b>Status:</b> {' - '.join([stat for stat in status if stat])}")

    def set_programs_status(self, action, date):
        bills = frappe.db.get_list('PSOF Program Bill', filters={
            'subscription_program': self.subscription_program,
            'psof': self.parent,
            'active': 0 if action == 'Activate' else 1,
            "date_from": [">=", date]
        }, fields=['name'])

        for bill in bills:
            program_bill = frappe.get_doc("PSOF Program Bill", bill.get("name"))
            program_bill.update_status(1 if action == 'Activate' else 0)

    def update_amounts(self):
        self.get_allocation_total()
        self.get_allocation_diff()
        self.get_allocation_cond()
        self.compute_tax(tax_type=self.get_tax_type())

    def get_tax_type(self):
        psof = frappe.get_doc("PSOF", self.parent)
        return psof.tax_category

    def get_allocation_diff(self):
        self.decoder_difference = diff(self.decoder_max_bill_div, self.decoder_calculation)
        self.card_difference = diff(self.card_max_bill_divisor, self.card_calculation)
        self.promo_difference = diff(self.promo_max_bill_divisor, self.promo_calculation)
        self.freight_difference = diff(self.freight_max_bill_divisor, self.freight_calculation)

    def get_allocation_total(self):
        total = 0
        total += flt(self.decoder_rate, 2) if self.decoder_allocation_active == 1 else 0
        total += flt(self.card_rate, 2) if self.card_allocation_active == 1 else 0
        total += flt(self.promo_rate, 2) if self.promo_allocation_active == 1 else 0
        total += flt(self.freight_rate, 2) if self.freight_allocation_active == 1 else 0
        self.total = total

    def get_allocation_cond(self):
        self.decoder_condition = cond(self.decoder_difference)
        self.card_condition = cond(self.card_difference)
        self.promo_condition = cond(self.promo_difference)
        self.freight_condition = cond(self.freight_difference)

    def compute_tax(self, tax_type):
        if tax_type == "Taxable":
            self.less_of_vat_original = (self.subscription_fee -  self.total) / 1.12
            self.vat_amount = flt(flt(self.less_of_vat_original * 0.12, 2), 2)
        else:
            self.less_of_vat_original = (self.subscription_fee -  self.total)
            self.vat_amount = 0
        self.grand_total = self.less_of_vat_original + self.total + self.vat_amount
        self.difference_grand_total = self.subscription_fee - self.grand_total
        self.subscription_rate = self.less_of_vat_original + self.difference_grand_total
        self.no_of_subs = rounded(self.less_of_vat_original / self.rate_per_sub)
    