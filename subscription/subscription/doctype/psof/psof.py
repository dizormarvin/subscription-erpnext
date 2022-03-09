# -*- coding: utf-8 -*-
# Copyright (c) 2020, ossphin and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document
from frappe.utils import flt, getdate, add_months, add_days, get_last_day, fmt_money, nowdate


class PSOF(Document):

    def validate_bills(self, bill):
        if frappe.db.exists({
            'doctype': 'PSOF Program Bill',
            'date_from': bill.date_from,
            'date_to': bill.date_to,
            'psof': bill.psof,
            'subscription_program': bill.subscription_program
        }):
            frappe.throw(f"""<h4>Bill dated from {bill.date_from} to {bill.date_to}
            <br>For {bill.subscription_program} already exists</h4>""")

    @frappe.whitelist()
    def create_bill(self):
        progs = frappe.db.sql("""SELECT * FROM `tabPSOF Program` WHERE parent = %s AND subscription_program = %s""",
                               (self.name, self.subscription_program), as_dict=1)

        # get data from server
        for i in progs:
            start = i.start_date
            end = i.end_date
            decoder_count = 0
            card_count = 0
            promo_count = 0
            freight_count = 0
            row = 0

            while start < end:
                doc = frappe.new_doc("PSOF Program Bill")
                doc.psof = self.name
                doc.subscription_program = self.subscription_program
                doc.date_from = start
                doc.date_to = add_days(add_months(start, +1), -1)
                doc.no_of_subs = i.no_of_subs
                doc.subscription_fee = i.subscription_fee
                doc.subscription_rate = i.subscription_rate
                doc.vat_amount = i.vat_amount
                doc.customer_name = self.customer_name
                doc.subscription_contract = i.subscription_contract
                doc.account_manager = self.account_manager
                doc.active = 1 if i.renewal == 1 or i.active == 1 else 0
                doc.currency_used = i.subscription_currency
                doc.parent_bill = i.name

                # Added on 1-29-21, recomputes data for 1st row to solve round-off error

                if row == 0:
                    if i.decoder_difference:
                        doc.decoder_rate = i.decoder_rate + i.decoder_difference
                        doc.subscription_rate = doc.subscription_rate - i.decoder_difference
                    else:
                        doc.decoder_rate = i.decoder_rate
                    if i.card_difference:
                        doc.card_rate = i.card_rate + i.card_difference
                        doc.subscription_rate = doc.subscription_rate - i.card_difference
                    else:
                        doc.card_rate = i.card_rate
                    if i.promo_difference:
                        doc.promo_rate = i.promo_rate + i.promo_difference
                        doc.subscription_rate = doc.subscription_rate - i.promo_difference
                    else:
                        doc.promo_rate = i.promo_rate
                    if i.freight_difference:
                        doc.freight_rate = i.freight_rate + i.freight_difference
                        doc.subscription_rate = doc.subscription_rate - i.freight_difference
                    else:
                        doc.freight_rate = i.freight_rate
                else:
                    if i.decoder_max_bill_count > decoder_count:
                        doc.decoder_rate = i.decoder_rate
                    else:
                        doc.subscription_rate = doc.subscription_rate + i.decoder_rate

                    if i.card_max_bill_count > card_count:
                        doc.card_rate = i.card_rate
                    else:
                        doc.subscription_rate = doc.subscription_rate + i.card_rate

                    if i.promo_max_bill_count > promo_count:
                        doc.promo_rate = i.promo_rate
                    else:
                        doc.subscription_rate = doc.subscription_rate + i.promo_rate

                    if i.freight_max_bill_count > freight_count:
                        doc.freight_rate = i.freight_rate
                    else:
                        doc.subscription_rate = doc.subscription_rate + i.freight_rate

                doc.flags.ignore_mandatory = True
                self.validate_bills(doc)
                doc.insert()
                start = add_months(start, +1)
                row += 1
                decoder_count = decoder_count + 1
                card_count = card_count + 1
                promo_count = promo_count + 1
                freight_count = freight_count + 1



        # db containing data from PSOF
        view = frappe.db.sql(
            """SELECT * FROM `tabPSOF Program Bill` WHERE psof = %s AND subscription_program = %s ORDER BY date_from;""",(self.name, self.subscription_program), as_dict=1)

        # send data to client
        for i in view:
            self.append('bill_view', {
                "active": i.active,
                "subscription_program": i.subscription_program,
                "date_from": i.date_from,
                "date_to": i.date_to,
                "no_of_subs": i.no_of_subs,
                "subscription_fee": i.subscription_fee,
                "subscription_rate": i.subscription_rate,
                "decoder_rate": i.decoder_rate,
                "card_rate": i.card_rate,
                "promo_rate": i.promo_rate,
                "freight_rate": i.freight_rate,
                "psof_program_bill": i.name,
                "vat_amount": i.vat_amount,
                "currency_used": i.currency_used
            })

    @frappe.whitelist()
    def update_bills(self):
        newbills = self.bill_view

        for i in newbills:
            doc = frappe.get_doc('PSOF Program Bill', i.psof_program_bill)
            doc.name = i.psof_program_bill
            doc.psof = self.name
            doc.subscription_program = self.subscription_program
            doc.date_from = i.date_from
            doc.date_to = i.date_to
            doc.no_of_subs = i.no_of_subs
            doc.subscription_fee = i.subscription_fee
            doc.subscription_rate = i.subscription_rate
            doc.vat_amount = i.vat_amount
            doc.decoder_rate = i.decoder_rate
            doc.card_rate = i.card_rate
            doc.promo_rate = i.promo_rate
            doc.freight_rate = i.freight_rate
            doc.flags.ignore_mandatory = True
            doc.save()

    @frappe.whitelist()
    def view_new_bill(self):
        view = frappe.db.sql (
            """SELECT * FROM `tabPSOF Program Bill` WHERE psof = %s AND subscription_program = %s ORDER BY date_from;""",
            (self.name, self.subscription_program), as_dict=1)

        # send data to client
        for i in view:
            self.append('bill_view', {
                "active": i.active,
                "subscription_program": i.subscription_program,
                "date_from": i.date_from,
                "date_to": i.date_to,
                "no_of_subs": i.no_of_subs,
                "subscription_fee": i.subscription_fee,
                "subscription_rate": i.subscription_rate,
                "decoder_rate": i.decoder_rate,
                "card_rate": i.card_rate,
                "promo_rate": i.promo_rate,
                "freight_rate": i.freight_rate,
                "psof_program_bill": i.name,
                "vat_amount": i.vat_amount,
                "currency": i.currency_used
            })


@frappe.whitelist()
def get_programs(doctype, txt, searchfield, start, page_len, filters, as_dict=False):
    programs = frappe.db.sql("""SELECT b.program_name FROM `tabPSOF Program` a, `tabSubscription Program` b, `tabPSOF` c
        WHERE a.subscription_program = b.name AND a.parent = %s """,(filters["dname"]))

    return programs


@frappe.whitelist()
def delete_generated(parent, program, psof):

    if frappe.db.exists({
        "doctype": "PSOF Program Bill",
        "subscription_program": program,
        "psof": psof
    }):
        programs = frappe.db.sql(f"""
            SELECT
                name 
            FROM 
                `tabPSOF Program Bill` 
            WHERE 
                parent_bill = '{parent}'
                AND
                subscription_program = '{program}'
                AND
                psof = '{psof}'
                """, as_dict=1)

        for program in programs:
            frappe.db.delete("PSOF Program Bill", program.name)

        return f"{len(programs)} generated bill/s has been deleted"
    else:
        return f"{program} has been removed from the list"
