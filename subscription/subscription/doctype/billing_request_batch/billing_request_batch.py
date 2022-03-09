# -*- coding: utf-8 -*-
# Copyright (c) 2020, ossphin and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class BillingRequestBatch(Document):
    pass

    @frappe.whitelist()
    def generate_bills(self):
        period = self.subscription_period
        spartner = self.sales_partner

        # Get Related Contracts
        contracts = frappe.db.sql("""SELECT * FROM tabCustomer c, `tabSubscription Contract` s 
            WHERE c.name = s.customer and s.docstatus=1 AND renewal_contract is null AND sales_partner = %s;""",(spartner), as_dict=1)


        #Create Billing for Each customer
        for c in contracts:
            doc = frappe.new_doc("Billing Request")
            doc.customer = c.customer
            doc.subscription_period = period
            doc.date = self.date
            # doc.currency = self.currency 
            doc.currency = c.currency
            doc.contract = c.contract_number
            doc.subscription_contract = c.name

            # Get Applicable Items for Unexpired Contracts
            items = frappe.db.sql("""SELECT i.* FROM `tabSubscription Contract` h, 
                `tabSubscription Contract Items` i, `tabSubscription Period` p WHERE h.name = i.parent 
                AND h.name = %s AND p.name = %s AND i.active = TRUE
                AND (i.start_date <= p.start_date OR i.start_date BETWEEN p.start_date AND p.end_date)
                AND (i.end_date >= p.end_date OR i.end_date BETWEEN p.start_date AND p.end_date);""",(c.name, period), as_dict=1)

            for i in items:
                # Get Max Bill Count
                decoder_maxbill = 0
                card_maxbill = 0
                promo_maxbill = 0
                freight_maxbill = 0
                decoder_count = 0
                card_count = 0
                promo_count = 0
                freight_count = 0
                decoder_rate = 0
                card_rate = 0
                promo_rate = 0
                freight_rate = 0
                sub_rate = i.subscription_rate

                # Get Total Bill Count
                decoder = frappe.db.sql("""SELECT COUNT(i.name) AS c FROM `tabBilling Request` h, `tabBilling Request Item` i
                    WHERE h.name = i.parent AND h.docstatus = 1 AND i.contract_item = %s 
                    AND decoder_rate > 0""",(i.name), as_dict=1)
                card = frappe.db.sql("""SELECT COUNT(i.name) AS c FROM `tabBilling Request` h, `tabBilling Request Item` i
                    WHERE h.name = i.parent AND h.docstatus = 1 AND i.contract_item = %s 
                    AND card_rate > 0""",(i.name), as_dict=1)
                promo = frappe.db.sql("""SELECT COUNT(i.name) AS c FROM `tabBilling Request` h, `tabBilling Request Item` i
                    WHERE h.name = i.parent AND h.docstatus = 1 AND i.contract_item = %s
                    AND promo_rate > 0""",(i.name), as_dict=1)
                freight = frappe.db.sql("""SELECT COUNT(i.name) AS c FROM `tabBilling Request` h, `tabBilling Request Item` i
                    WHERE h.name = i.parent AND h.docstatus = 1 AND i.contract_item = %s
                    AND freight_rate > 0""",(i.name), as_dict=1)

                if i.decoder_allocation_active:
                    decoder_maxbill = i.decoder_max_bill_count
                    for a in decoder:
                        if decoder_maxbill > a.c:
                            decoder_rate = decoder_rate + i.decoder_rate
                        else:
                            sub_rate = sub_rate + i.decoder_rate

                if i.card_allocation_active:
                    card_maxbill = i.card_max_bill_count
                    for b in card:
                        if card_maxbill > b.c:
                            card_rate = card_rate + i.card_rate
                        else:
                            sub_rate = sub_rate + i.card_rate

                if i.promo_allocation_active:
                    promo_maxbill = i.promo_max_bill_count
                    for c in promo:
                        if decoder_maxbill > c.c:
                            decoder_rate = decoder_rate + i.decoder_rate
                        else:
                            sub_rate = sub_rate + i.decoder_rate

                if i.freight_allocation_active:
                    freight_maxbill = i.freight_max_bill_count
                    for d in freight:
                        if decoder_maxbill > d.c:
                            decoder_rate = decoder_rate + i.decoder_rate
                        else:
                            sub_rate = sub_rate + i.decoder_rate

                ci = doc.append('items',{
                    "program_code": i.program_code,
                    "program_name": i.program_name,
                    "subscription_fee": i.subscription_fee,
                    "subscription_rate": sub_rate,
                    "rate_per_sub": i.rate_per_sub,
                    "no_of_subs": i.no_of_subs,
                    "decoder_calculation": i.decoder_calculation,
                    "decoder_rate": decoder_rate,
                    "card_section": i.card_section,
                    "card_calculation": i.card_calculation,
                    "card_rate": card_rate,
                    "promo_calculation": i.promo_calculation,
                    "promo_rate": promo_rate,
                    "freight_calculation": i.freight_calculation,
                    "freight_rate": freight_rate,
                    "contract_item": i.name
                    })

            doc.flags.ignore_mandatory = True
            doc.insert()

            "Add Invoice Detail on Bill Run"
            self.append('billing_request_batch_bills',{
                "billing_request": doc.name,
                "customer": doc.customer,
                "date":  doc.date,
                "currency": doc.currency,
                "subscription_contract": doc.subscription_contract
            })

    @frappe.whitelist()
    def get_defaults(self):
        if not self.subscription_period:
            self.subscription_period = frappe.db.get_single_value("Subscription Setup", "current_period")

    def on_submit(self):
        for a in self.billing_request_batch_bills:
            doc = frappe.get_doc("Billing Request", a.billing_request)
            doc.submit()

    def on_cancel(self):
        for a in self.billing_request_batch_bills:
            doc = frappe.get_doc("Billing Request", a.billing_request)
            doc.cancel()