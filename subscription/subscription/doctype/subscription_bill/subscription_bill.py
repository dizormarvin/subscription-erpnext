# -*- coding: utf-8 -*-
# Copyright (c) 2021, ossphin and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import now, today


class SubscriptionBill(Document):

    def autoname(self):
        period = frappe.get_doc("Subscription Period", self.subscription_period)
        count = frappe.db.count('Subscription Bill', {'subscription_period': period.name}) + 1
        self.name = f"{period.end_date.strftime('%Y%m')}{str(count).zfill(4)}"

    @frappe.whitelist()
    def createjournal(self):
        period = frappe.get_doc("Subscription Period", self.subscription_period)
        bill = frappe.db.sql("""SELECT * FROM `tabSubscription Bill`
            WHERE name = %s""",
            (self.name), as_dict=1)
        
        for i in bill:
            doc = frappe.new_doc("Journal Entry")
            doc.entry_type = "Journal Entry"
            doc.posting_date = self.bill_date
            doc.bill_no = self.name
            doc.bill_date = self.bill_date
            doc.due_date = period.end_date
            doc.reference_no = self.name
            doc.reference_date = self.bill_date
            doc.user_remark = "Billing Entry For " + self.name
            
            item = frappe.db.sql("""SELECT 
                i.*,
                p.msf_ar_account,
                p.decoder_ar_account,
                p.card_ar_account,
                p.promo_ar_account,
                p.freight_ar_account,
                p.msf_sales_account,
                p.decoder_sales_account,
                p.card_sales_account,
                p.promo_sales_account,
                p.freight_sales_account,
                p.vat_account                
                FROM `tabSubscription Bill Item` i, `tabSubscription Program` p
                WHERE i.parent = %s
                AND i.subscription_program = p.name""",
                (self.name), as_dict=1)
            
            for d in item:
                if d.subscription_rate > 0:
                    doc.append('accounts', {
                        "account": d.msf_ar_account,
                        "party_type": "Customer",
                        "party": self.customer,
                        "debit": d.subscription_fee * self.exchange_rate,
                        "exchange_rate": self.exchange_rate,
                        "debit_in_account_currency": d.subscription_fee
                    })
                    doc.append('accounts', {
                        "account": d.msf_sales_account,
                        "credit": d.subscription_rate * self.exchange_rate,
                        "exchange_rate": self.exchange_rate,
                        "credit_in_account_currency": d.subscription_rate
                    })
                    doc.append('accounts', {
                        "account": d.vat_account,
                        "credit": (d.subscription_fee - d.subscription_rate) * self.exchange_rate,
                        "exchange_rate": self.exchange_rate,
                        "credit_in_account_currency": d.subscription_fee - d.subscription_rate
                    })
                if d.decoder_rate > 0:
                    doc.append('accounts', {
                        "account": d.decoder_ar_account,
                        "party_type": "Customer",
                        "party": self.customer,
                        "debit": d.decoder_rate * self.exchange_rate,
                        "exchange_rate": self.exchange_rate,
                        "debit_in_account_currency": d.decoder_rate
                    })
                    doc.append('accounts', {
                        "account": d.decoder_sales_account,
                        "credit": d.decoder_rate * self.exchange_rate,
                        "exchange_rate": self.exchange_rate,
                        "credit_in_account_currency": d.decoder_rate
                    })
                if d.card_rate > 0:
                    doc.append('accounts', {
                        "account": d.card_ar_account,
                        "party_type": "Customer",
                        "party": self.customer,
                        "debit": d.card_rate * self.exchange_rate,
                        "exchange_rate": self.exchange_rate,
                        "debit_in_account_currency": d.card_rate
                    })
                    doc.append('accounts', {
                        "account": d.card_sales_account,
                        "credit": d.card_rate * self.exchange_rate,
                        "exchange_rate": self.exchange_rate,
                        "credit_in_account_currency": d.card_rate
                    })
                if d.promo_rate > 0:
                    doc.append('accounts', {
                        "account": d.promo_ar_account,
                        "party_type": "Customer",
                        "party": self.customer,
                        "debit": d.promo_rate * self.exchange_rate,
                        "exchange_rate": self.exchange_rate,
                        "debit_in_account_currency": d.promo_rate
                    })
                    doc.append('accounts', {
                        "account": d.promo_sales_account,
                        "credit": d.promo_rate * self.exchange_rate,
                        "exchange_rate": self.exchange_rate,
                        "credit_in_account_currency": d.promo_rate
                    })
                if d.freight_rate > 0:
                    doc.append('accounts', {
                        "account": d.freight_ar_account,
                        "party_type": "Customer",
                        "party": self.customer,
                        "debit": d.freight_rate * self.exchange_rate,
                        "exchange_rate": self.exchange_rate,
                        "debit_in_account_currency": d.freight_rate
                    })
                    doc.append('accounts', {
                        "account": d.freight_sales_account,
                        "credit": d.freight_rate * self.exchange_rate,
                        "exchange_rate": self.exchange_rate,
                        "credit_in_account_currency": d.freight_rate
                    })
                    
            doc.insert()
            self.journal_reference = doc.name