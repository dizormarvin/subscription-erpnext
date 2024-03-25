# -*- coding: utf-8 -*-
# Copyright (c) 2020, ossphin and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document
from frappe.utils import flt, getdate, add_months, add_days, get_last_day, fmt_money, nowdate, format_date, get_date_str, \
    get_first_day, add_years


class PSOF(Document):

    def validate(self):
        if self.subscription_contract:
            contract = frappe.get_doc("Subscription Contract", self.subscription_contract)
            contract.db_set("is_used", 1)
        self.adjust_program_parent()
        self.calculate_total()
        self.update_program_status()

    def adjust_program_dates(self, n_end_date, n_contract):
        for program in self.get("programs"):
            frappe.db.set_value("PSOF Program", program.name, {
                "end_date": n_end_date,
                "subscription_contract": n_contract
            })

    def update_program_status(self):
        for program in self.get("programs"):
            program.set_generated()

    def adjust_program_parent(self):
        for program in self.get("programs"):
            frappe.db.set_value("PSOF Program", program.name, "parent", self.name)

    def calculate_total(self):
        self.db_set("monthly_subs_fee_total", sum(program.get("subscription_fee") for program in self.get("programs")))

    def autoname(self):
        if self.bill_until_renewed:
            prefix = "D"
            old_psof = frappe.get_doc("Subscription Contract", self.subscription_contract)
            name = old_psof.get("psof").split("-")
            self.name = f"{name[0]}-{name[1]}-{prefix}{int(name[2][1:]) + 1}" if len(name) > 2 else f"{name[0]}-{name[1]}-{prefix}{1}"

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
            # original
            start = i.supersede_date if i.renewal and not i.for_cb else i.start_date
            # start = i.supersede_date if hasattr(i, 'supersede_date') and i.renewal else other_date if not hasattr(i, 'supersede_date') and i.renewal else i.start_date
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
                doc.dummy = i.include_in_bill_expired_until_renewed
                doc.renewal = i.renewal

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

        self.update_program_status()

        # db containing data from PSOF

        view = self.alter_view()

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
        for i in self.get('bill_view'):
            if frappe.db.exists('PSOF Program Bill', i.psof_program_bill):
                doc = frappe.get_doc('PSOF Program Bill', i.psof_program_bill)
            else:
                doc = frappe.new_doc('PSOF Program Bill')
            doc.psof = self.name
            doc.update_status(i.get("active"))
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
            doc.free_view = i.free_view
            doc.flags.ignore_mandatory = True
            doc.save()

    def alter_view(self):
        if self.superseded and not self.for_cb:
            return frappe.db.sql(
                """SELECT * FROM 
                `tabPSOF Program Bill` 
                WHERE 
                subscription_program = %s 
                AND
                (psof = %s OR dummy_contract = %s) ORDER BY date_from;""",
                (self.subscription_program, self.name, self.dummy_contract), as_dict=1)
        else:
            return frappe.db.sql(
                """SELECT * FROM 
                `tabPSOF Program Bill` 
                WHERE psof = %s 
                AND
                 subscription_program = %s 
                ORDER BY date_from;""",
                (self.name, self.subscription_program), as_dict=1)

    @frappe.whitelist()
    def view_new_bill(self):
        view = self.alter_view()

        # send data to client
        for i in view:
            self.append('bill_view', {
                "active": i.get("active"),
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
                "currency": i.currency_used,
                "dummy": i.dummy,
                "renewal": i.renewal,
                "free_view": i.free_view
            })


@frappe.whitelist()
def get_programs(doctype, txt, searchfield, start, page_len, filters, as_dict=False):
    if filters.get("from_request"):
        return frappe.db.get_list("PSOF", fields=["name", "subscription_contract"],
                                  filters={"customer_name": filters.get("customer")}, order_by="creation desc", as_list=True)
    return frappe.db.get_list('PSOF Program', fields=['subscription_program', 'program_status'],
                              filters={'parent': filters.get("dname")}, order_by='subscription_program asc', as_list=True)


@frappe.whitelist()
def get_contracts(doctype, txt, searchfield, start, page_len, filters, as_dict=False):
    return frappe.db.get_list('Subscription Contract',
                              fields=['name', 'tax_category', 'sales_partner'],
                              filters={'docstatus': 1}, order_by='creation desc', as_list=True)


@frappe.whitelist()
def delete_generated(parent, program, psof):
    programs = frappe.db.get_list('PSOF Program Bill', filters={
        'subscription_program': program, 'psof': psof}, pluck="name")
    msg = ''

    if len(programs) > 0:
        for program in programs:
            frappe.db.delete("PSOF Program Bill", program)
        frappe.db.commit()
        msg = f"{len(programs)} generated bill/s has been deleted"
    else:
        msg = f"{program} has been removed from the list"

    return msg


@frappe.whitelist()
def create_dummy(contract=None, extend=None):
    original_contract = frappe.get_doc("Subscription Contract", contract)
    dummy_contract = frappe.get_doc({
        'doctype': 'Subscription Contract',
        'customer': original_contract.get("customer"),
        'contract_number': contract,
        'bill_expired': 1,
        'contract_date': nowdate(),
        "extension": extend,
        'start_date': add_years(get_date_str(get_first_day(original_contract.get("start_date"))), 1),
        'expiry_date': add_years(get_date_str(get_last_day(original_contract.get("expiry_date"))), 1)
    })

    dummy_contract.save()
    return dummy_contract.name


@frappe.whitelist()
def supersede_dummy(contract=None, cb=None):
    original_contract = frappe.get_doc("Subscription Contract", contract)
    dummy_contract = frappe.get_doc({
        'doctype': 'Subscription Contract',
        'customer': original_contract.get("customer"),
        'contract_number': contract,
        'is_supersede': 1,
        'for_cb': cb,
        'contract_date': nowdate(),
        'start_date': original_contract.get("start_date"),
        'expiry_date': original_contract.get("expiry_date")
    })

    dummy_contract.save()
    return dummy_contract.name
