# -*- coding: utf-8 -*-
# Copyright (c) 2020, ossphin and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document


class SubscriptionContract (Document):
    pass

    @frappe.whitelist ()
    def get_items(self):
        total = 0
        items = frappe.db.sql ("""SELECT pi.active, sp.name AS package, pi.item_code, pi.item_name, pi.interval,pi.count, pi.rate, 
			pi.decoder_rate, pi.promo_rate, pi.freight_rate, pi.card_rate,
			pi.max_bill_count, pi.item_after_max_bill 
			FROM `tabSubscription Contract` c, `tabSubscription Contract Packages` p, `tabSubscription Package` sp, `tabSubscription Package Item` pi
			WHERE c.name = p.parent AND p.package = sp.name and sp.name = pi.parent AND pi.active = 1 AND c.name = %s order by pi.name; """,
                               (self.name), as_dict=1)

        for i in items:
            self.append ('items', {
                "active": i.active,
                "package": i.package,
                "item_code": i.item_code,
                "item_name": i.item_name,
                "interval": i.interval,
                "count": i.count,
                "rate": i.rate,
                "decoder_rate": i.decoder_rate,
                "promo_rate": i.promo_rate,
                "freight_rate": i.freight_rate,
                "card_rate": i.card_rate,
                "max_bill_count": i.max_bill_count,
                "item_after_max_bill": i.item_after_max_bill
            })

            total = total + i.rate

        self.total = total

    @frappe.whitelist ()
    def renew_contract(self):
        if self.renewal_contract:
            frappe.throw (
                "Renewal Failed. This contract has been renewed with contract reference " + self.renewal_contract + ".")

        doc = frappe.new_doc ("Subscription Contract")
        doc.contract_number = self.contract_number + "-0"
        doc.customer = self.customer
        doc.customer_name = self.customer_name
        doc.description = self.description
        # doc.contract_date = self.contract_date
        # doc.start_date = self.expiry_date
        # doc.expiry_date = self.expiry_date
        doc.bill_expired_until_renewed = self.bill_expired_until_renewed
        doc.escalation = self.escalation
        doc.currency = self.currency
        doc.total = self.total

        doc.flags.ignore_mandatory = True

        for i in self.items:
            doc.append ('items', {
                "active": i.active,
                "package": i.package,
                "program_code": i.program_code,
                "program_name": i.program_name,
                "interval": i.interval,
                "count": i.count,
                "start_date": i.start_date,
                "max_bill_count": i.max_bill_count,
                "end_date": i.end_date,

                "decoder_allocation_active": i.decoder_allocation_active,
                "card_allocation_active": i.card_allocation_active,
                "promo_allocation_active": i.promo_allocation_active,
                "freight_allocation_active": i.freight_allocation_active,

                "subscription_fee": i.subscription_fee,
                "subscription_rate": i.subscription_rate,
                "rate_per_sub": i.rate_per_sub,
                "no_of_subs": i.no_of_subs,
                "total": i.total,
                "decoder_calculation": i.decoder_calculation,
                "decoder_rate": i.decoder_rate,
                "decoder_max_bill_div": i.decoder_max_bill_div,
                "decoder_max_bill_count": i.decoder_max_bill_count,
                "card_calculation": i.card_calculation,
                "card_rate": i.card_rate,
                "card_max_bill_divisor": i.card_max_bill_divisor,
                "card_max_bill_count": i.card_max_bill_count,
                "promo_calculation": i.promo_calculation,
                "promo_rate": i.promo_rate,
                "promo_max_bill_divisor": i.promo_max_bill_divisor,
                "promo_max_bill_count": i.promo_max_bill_count,
                "freight_calculation": i.freight_calculation,
                "freight_rate": i.freight_rate,
                "freight_max_bill_divisor": i.freight_max_bill_divisor,
                "freight_max_bill_count": i.freight_max_bill_count
            })

        doc.insert ()

        self.renewal_contract = doc.name
        self.save ()
        frappe.msgprint ("Renewal successful. A new contract with reference " + doc.name + " was created.")
