# -*- coding: utf-8 -*-
# Copyright (c) 2021, ossphin and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import dateutil.relativedelta
import frappe
import datetime
from frappe.model.document import Document
from erpnext.accounts.party import get_party_account, get_due_date


class MonthlyPSOF(Document):
    """Monthly Sales Generation"""

    def prevent_dbl_click(self):
        if self.is_generated == 0:
            self.db_set("is_generated", 1)
            return
        frappe.throw(title="Error", msg="Get items has already been clicked!")

    def get_items(self):
        self.prevent_dbl_click()
        start_date, end_date = frappe.db.get_value('Subscription Period', self.subscription_period, ['start_date',
                                                                                                     'end_date'])
        previous = frappe.db.get_value('Subscription Period', {
            'start_date': start_date - dateutil.relativedelta.relativedelta(months=1)}, ['code'])

        self.billing_last_month = previous if previous else ""

        start_date = start_date.strftime('%Y-%m-%d')
        end_date = end_date.strftime('%Y-%m-%d')
        srate, sfee, drate, crate, prate, frate = 0, 0, 0, 0, 0, 0

        program_bills = frappe.db.sql(f"""
        SELECT 
            account_manager, psof, customer_name,
            subscription_program, name, date_from, date_to,
            no_of_subs, ROUND(subscription_fee, 2) as sfee,
            ROUND(subscription_rate, 2) as srate, ROUND(decoder_rate, 2) as drate,
            ROUND(card_rate, 2) as crate, ROUND(freight_rate, 2) as frate,
            ROUND(promo_rate, 2) as prate, ROUND(vat_amount, 2) as vat
        FROM 
            `tabPSOF Program Bill` 
        WHERE 
            date_from 
                BETWEEN '{start_date}' AND '{end_date}' AND active = 1
                """, as_dict=1)

        for i in program_bills:
            customer = frappe.get_doc("Customer", i.customer_name)

            self.append('bills', {
                "assistant": customer.billing_assistant,
                "account_manager": i.account_manager,
                "subscription_period": self.subscription_period,
                "psof_program_bill": i.name,
                "psof": i.psof,
                "subscription_program": i.subscription_program,
                "customer": i.customer_name,
                "customer_name": customer.customer_name,
                "date_from": i.date_from,
                "date_to": i.date_to,
                "no_of_subs": i.no_of_subs,
                "subscription_fee": i.sfee,
                "subscription_rate": i.srate,
                "decoder_rate": i.drate,
                "card_rate": i.crate,
                "promo_rate": i.prate,
                "freight_rate": i.frate,
                "vat": i.vat,
            })

            srate += i.srate or 0
            sfee += i.sfee or 0
            crate += i.crate or 0
            drate += i.drate or 0
            frate += i.frate or 0
            prate += i.prate or 0

        self.total_subs_rate = srate
        self.total_subs_fee = sfee
        self.total_card_rate = crate
        self.total_decoder_rate = drate
        self.total_freight_rate = frate
        self.total_promo_rate = prate

    @frappe.whitelist()
    def create_bills(self):
        customer = frappe.db.sql("""
        SELECT 
            d.customer, h.date, h.subscription_period, p.exchange_rate, h.account_manager 
		FROM 
		    `tabMonthly PSOF` h, `tabMonthly PSOF Program Bill` d, `tabSubscription Period` p
		WHERE 
		    h.name = d.parent AND h.name = %s
		    AND 
		        h.subscription_period = p.name
        GROUP BY 
            d.customer, h.date, h.subscription_period, p.exchange_rate;
        """, (self.name), as_dict=1)

        for i in customer:
            doc = frappe.new_doc("Subscription Bill")
            doc.customer = i.customer
            doc.bill_date = i.date
            doc.subscription_period = i.subscription_period
            doc.due_date = get_due_date(
                doc.bill_date, "Customer", doc.customer)
            doc.exchange_rate = i.exchange_rate
            doc.account_manager = i.account_manager

            item = frappe.db.sql("""
                        SELECT * FROM `tabMonthly PSOF Program Bill`
                        WHERE parent = %s
                                AND customer = %s;
                        """, (self.name, i.customer), as_dict=1)

            for p in item:
                doc.append('items', {
                    "subscription_program": p.subscription_program,
                    "no_of_subs": p.no_of_subs,
                    "subscription_fee": p.subscription_fee,
                    "subscription_rate": p.subscription_rate,
                    "decoder_rate": p.decoder_rate,
                    "card_rate": p.card_rate,
                    "promo_rate": p.promo_rate,
                    "freight_rate": p.freight_rate,
                    "monthly_psof_no": p.parent,
                    "psof_no": p.psof,
                    "vat": p.vat,
                })

            doc.flags.ignore_mandatory = True
            doc.insert()

            "Add Details to Bills"
            self.append('billings', {
                "customer": doc.customer,
                "bill_no": doc.name,
                "date": doc.bill_date,
            })

        frappe.msgprint(
            msg='Bill successfully generated',
            title='Success',
            indicator='yellow',
            raise_exception=False
        )
