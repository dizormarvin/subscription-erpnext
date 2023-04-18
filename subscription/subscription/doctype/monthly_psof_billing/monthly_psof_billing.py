# -*- coding: utf-8 -*-
# Copyright (c) 2021, ossphin and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import datetime
from frappe.model.document import Document
from erpnext.accounts.party import get_party_account, get_due_date
import math
from frappe.utils import flt
from collections import Counter
from functools import reduce
from operator import add


class MonthlyPSOFBilling(Document):
    """Monthly Billing Generation"""

    def on_trash(self):
        self.status = 'Bills Deleted'
        linked_docs = self.count_linked_doc()
        frappe.get_doc("Monthly PSOF", self.monthly_psof).db_set("billing_generated", 0)

        frappe.db.delete("Subscription Bill", {'subscription_period': self.name})
        frappe.db.delete("Subscription Bill Item", {'subscription_period': self.name})
        frappe.db.delete("Monthly PSOF Bill", {'subscription_period': self.name})

        frappe.msgprint(msg=f"""Deleting the following documents:<br>
        <b>{linked_docs['s']}</b> Subscription Bill/s<br>
        <b>{linked_docs['sb']}</b> Subscription Bill Item/s<br>
        <b>{linked_docs['mb']}</b> Monthly Billing Items/s<br>""")
        frappe.db.commit()

    def count_linked_doc(self):
        subs_bill = frappe.db.count("Subscription Bill", {'subscription_period': self.name})
        subs_bill_items = frappe.db.count("Subscription Bill Item", {'subscription_period': self.name})
        monthly_bill = frappe.db.count("Monthly PSOF Bill", {'subscription_period': self.name})
        return {"s": subs_bill, "mb": monthly_bill, "sb": subs_bill_items}

    def truncate(self, number, digits) -> float:
        stepper = 10.0 ** digits
        return math.trunc(stepper * number) / stepper

    def truncate_first(self, number, digits) -> float:
        stepper = 100.0 ** digits
        x = math.trunc(stepper * number) / stepper
        return self.truncate(x, 2)

    def autoname(self):
        self.name = self.subscription_period

    def on_cancel(self):
        frappe.db.set(self, 'status', 'Cancelled')

    def check_accounts(self, items):
        for p in items:
            if None in [
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
            ]:
                frappe.msgprint(msg=f"{p.subscription_program} has incomplete accounting details",
                                title="Incomplete Account Details",
                                indicator="red",
                                raise_exception=True)
        return True

    def on_submit(self):
        self.submit_billings()

        frappe.msgprint(
            msg='Bills successfully posted',
            title='Success',
            indicator='yellow',
            raise_exception=False
        )

    def submit_billings(self):
        bills = self.get_billings()
        for bill in bills:
            bill.submit()

    def get_billings(self):
        subscription_bill = frappe.db.get_list("Monthly PSOF Bill", {"parent": self.name}, "bill_no", pluck="bill_no")
        return [frappe.get_doc("Subscription Bill", bill_no) for bill_no in subscription_bill]

    @frappe.whitelist()
    def create_sales_invoice(self):
        bills = self.get_billings()
        
        for bill in bills:
            bill.create_invoices()

    def create_journal_entries(self):
        mpsof = frappe.db.get_list("Monthly PSOF Bill", {"parent": self.name}, as_dict=1)

        for b in mpsof:
            bill = frappe.db.get_list("Subscription Bill", b.get("bill_no"), as_dict=1)

            for i in bill:
                doc = frappe.new_doc("Journal Entry")
                doc.entry_type = "Journal Entry"
                doc.posting_date = i.bill_date
                doc.bill_no = i.name
                doc.bill_date = i.bill_date
                doc.due_date = i.due_date
                doc.reference_no = i.name
                doc.reference_date = i.bill_date
                doc.subscription_period = i.subscription_period
                doc.user_remark = "Billing Entry For " + i.name

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
                                  FROM 
                                  `tabSubscription Bill Item` i, `tabSubscription Program` p
                                  WHERE i.parent = %s
                                  AND i.subscription_program = p.name""", (i.name), as_dict=1)

                if self.check_accounts(item):
                    for d in item:
                        if d.subscription_rate >= 0:
                            doc.append('accounts', {
                                "account": d.msf_ar_account,
                                "party_type": "Customer",
                                "party": i.customer,
                                "debit": d.subscription_fee,
                                "exchange_rate": 1,
                                "debit_in_account_currency": d.subscription_rate + d.vat
                            })
                            doc.append('accounts', {
                                "account": d.msf_sales_account,
                                "credit": d.subscription_rate,
                                "exchange_rate": 1,
                                "credit_in_account_currency": d.subscription_rate
                            })
                            doc.append('accounts', {
                                "account": d.vat_account,
                                "credit": d.subscription_fee - d.subscription_rate,
                                "exchange_rate": 1,
                                "credit_in_account_currency": d.vat
                            })
                        if d.decoder_rate >= 0:
                            doc.append('accounts', {
                                "account": d.decoder_ar_account,
                                "party_type": "Customer",
                                "party": i.customer,
                                "debit": round(d.decoder_rate_vat, 2),
                                "exchange_rate": 1,
                                "debit_in_account_currency": d.decoder_rate_vat
                            })
                            doc.append('accounts', {
                                "account": d.decoder_sales_account,
                                "credit": round(d.decoder_rate, 2),
                                "exchange_rate": 1,
                                "credit_in_account_currency": d.decoder_rate
                            })
                            doc.append('accounts', {
                                "account": d.vat_account,
                                "credit": round(d.decoder_rate_vat, 2) - round(d.decoder_rate, 2),
                                "exchange_rate": 1,
                                "credit_in_account_currency": round(d.decoder_rate_vat, 2) - round(d.decoder_rate, 2)
                            })
                        if d.card_rate >= 0:
                            doc.append('accounts', {
                                "account": d.card_ar_account,
                                "party_type": "Customer",
                                "party": i.customer,
                                "debit": d.card_rate_vat,
                                "exchange_rate": 1,
                                "debit_in_account_currency": d.card_rate_vat
                            })
                            doc.append('accounts', {
                                "account": d.card_sales_account,
                                "credit": d.card_rate,
                                "exchange_rate": 1,
                                "credit_in_account_currency": d.card_rate
                            })
                            doc.append('accounts', {
                                "account": d.vat_account,
                                "credit": d.card_rate_vat - d.card_rate,
                                "exchange_rate": 1,
                                "credit_in_account_currency": d.card_rate_vat - d.card_rate
                            })
                        if d.promo_rate >= 0:
                            doc.append('accounts', {
                                "account": d.promo_ar_account,
                                "party_type": "Customer",
                                "party": i.customer,
                                "debit": d.promo_rate_vat,
                                "exchange_rate": 1,
                                "debit_in_account_currency": d.promo_rate_vat
                            })
                            doc.append('accounts', {
                                "account": d.promo_sales_account,
                                "credit": d.promo_rate,
                                "exchange_rate": 1,
                                "credit_in_account_currency": d.promo_rate
                            })
                            doc.append('accounts', {
                                "account": d.vat_account,
                                "credit": d.promo_rate_vat - d.promo_rate,
                                "exchange_rate": 1,
                                "credit_in_account_currency": d.promo_rate_vat - d.promo_rate
                            })
                        if d.freight_rate >= 0:
                            doc.append('accounts', {
                                "account": d.freight_ar_account,
                                "party_type": "Customer",
                                "party": i.customer,
                                "debit": d.freight_rate_vat,
                                "exchange_rate": 1,
                                "debit_in_account_currency": d.freight_rate_vat
                            })
                            doc.append('accounts', {
                                "account": d.freight_sales_account,
                                "credit": d.freight_rate,
                                "exchange_rate": 1,
                                "credit_in_account_currency": d.freight_rate
                            })
                            doc.append('accounts', {
                                "account": d.vat_account,
                                "credit": d.freight_rate_vat - d.freight_rate,
                                "exchange_rate": 1,
                                "credit_in_account_currency": d.freight_rate_vat - d.freight_rate
                            })

                    doc.insert()
                    doc.submit()
                    bills = frappe.get_doc("Subscription Bill", i.name)
                    bills.journal_reference = doc.name
                    bills.save()
                    bills.submit()

    @frappe.whitelist()
    def create_bills(self):
        sales_bills = frappe.db.sql("""
            SELECT 
                d.customer, 
                h.date, 
                h.subscription_period,
                h.currency, 
                p.exchange_rate, 
                p.end_date,
                d.psof, 
                d.parent,
                d.account_manager, 
                d.tax_category as tx
            FROM 
                `tabMonthly PSOF` h, 
                `tabMonthly PSOF Program Bill` d, 
                `tabSubscription Period` p
            WHERE 
                    h.name = d.parent 
                AND 
                    h.name = %s
                AND 
                    h.subscription_period = p.name
                GROUP BY 
                    d.customer, 
                    h.date, 
                    h.subscription_period, 
                    p.exchange_rate; """, self.monthly_psof, as_dict=1)

        period = frappe.get_doc("Subscription Period", self.subscription_period)

        def vat_(rate):
            if not rate:
                return 0
            return flt(rate / 1.12)

        def sum_(lists):
            return flt(sum([flt(i) for i in lists]), 2)

        def round2(rate):
            return frappe.db.sql(f"SELECT ROUND({rate}, 2)")[0][0]

        def round_convert(rate, exchange_rate=self.exchange_rate):
            return frappe.db.sql(f"SELECT ROUND({rate} * {exchange_rate}, 2)")[0][0]

        def get_difference(rate):
            if not rate:
                return 0
            return rate - vat_(rate)

        for bill in sales_bills:
            customer_ = frappe.get_doc("Customer", bill.customer)
            doc = frappe.new_doc("Subscription Bill")
            doc.customer = bill.customer
            doc.customer_name = bill.customer_name
            doc.bill_date = bill.date
            doc.subscription_period = bill.subscription_period
            doc.due_date = get_due_date(doc.bill_date, "Customer", doc.customer)
            doc.exchange_rate = self.exchange_rate
            doc.account_manager = bill.account_manager
            doc.assistant = customer_.billing_assistant
            doc.monthly_psof = bill.parent
            doc.psof = bill.psof

            sbill_items = frappe.db.get_all('Monthly PSOF Program Bill',
                                            {'parent': self.monthly_psof,
                                             'customer': bill.customer},
                                            ['subscription_fee as sfee', 'subscription_rate as srate', 'vat',
                                             'decoder_rate as drate', 'promo_rate as prate', 'freight_rate as frate',
                                             'card_rate as crate', 'subscription_program as program', 'psof'])

            totals = {
                't_msf': 0,
                't_diff': 0,
                't_vat_ex': 0,
                't_vat': 0,
                'msf': sum([i['sfee'] for i in sbill_items]),
                'decoder': sum([i['drate'] for i in sbill_items]),
                'promo': sum([i['prate'] for i in sbill_items]),
                'freight': sum([i['frate'] for i in sbill_items]),
                'card': sum([i['crate'] for i in sbill_items]),
                'php_msf': sum([round_convert(i['sfee']) for i in sbill_items]),
                'php_drate': sum([round_convert(i['drate']) for i in sbill_items]),
                'php_prate': sum([round_convert(i['prate']) for i in sbill_items]),
                'php_frate': sum([round_convert(i['frate']) for i in sbill_items]),
                'php_crate': sum([round_convert(i['crate']) for i in sbill_items]),
            }

            for p in sbill_items:
                allocations = {
                    "msf": round_convert(p.sfee),
                    "decoder_rate":  round_convert(p.drate),
                    "card_rate":  round_convert(p.crate),
                    "promo_rate":  round_convert(p.prate),
                    "freight_rate":  round_convert(p.frate),
                    "decoder_diff": get_difference(round_convert(p.drate)),
                    "card_diff": get_difference(round_convert(p.crate)),
                    "promo_diff": get_difference(round_convert(p.prate)),
                    "freight_diff": get_difference(round_convert(p.frate)),
                }
                allocations["total"] = round2(sum((flt(allocations["decoder_rate"]), flt(allocations["promo_rate"]),
                                                   flt(allocations["card_rate"]), flt(allocations["freight_rate"]))))
                allocations["vat_inc"] = round2(allocations["msf"] - allocations["total"])
                allocations["vat_ex"] = round2(vat_(allocations["vat_inc"]))
                allocations["vat"] = round2(allocations["vat_ex"] * 0.12)
                allocations["vat_ex"] = round2(allocations["vat_inc"] - allocations["vat"])
                allocations["comp_total"] = round2(sum([allocations["vat_ex"], allocations["vat"],
                                                        allocations["total"]]))
                allocations["comp_diff"] = allocations["msf"] - allocations["comp_total"]
                allocations["comp_vat_ex"] = allocations["vat_ex"] + allocations["comp_diff"]

                bill_totals = {'created_from': self.monthly_psof, 'customer': doc.customer,
                               'subscription_period': doc.subscription_period, 'bill_date': doc.bill_date,
                               "subscription_program": p.program, "subs_fee": p.sfee,
                               "subscription_fee": allocations['msf'], "subscription_rate_inc": allocations["vat_inc"],
                               "subscription_rate_ex": allocations["vat_ex"], "vat": allocations["vat"],
                               "decoder_rate": vat_(allocations["decoder_rate"]),
                               "card_rate": vat_(allocations["card_rate"]),
                               "promo_rate": vat_(allocations["promo_rate"]),
                               "freight_rate": vat_(allocations["freight_rate"]), "monthly_psof_no": doc.monthly_psof,
                               "psof_no": p.psof, 'total_alloc': vat_(allocations["total"]),
                               'total_alloc_vat': allocations["total"], "decoder_rate_vat": allocations["decoder_rate"],
                               "card_rate_vat": allocations["card_rate"], "promo_rate_vat": allocations["promo_rate"],
                               "freight_rate_vat": allocations["freight_rate"], 'card_diff': allocations["card_diff"],
                               'decoder_diff': allocations["decoder_diff"], 'freight_diff': allocations["freight_diff"],
                               'promo_diff': allocations["promo_diff"],
                               'total_diff': get_difference(allocations["total"]),
                               'computed_total': allocations["comp_total"], 'computed_diff': allocations["comp_diff"],
                               'computed_vat_ex': allocations["comp_vat_ex"], "billing_currency": "PHP",
                               "rounding_diff": [],
                               'tax_category': bill.get('tx')}

                for i in ["decoder", "card", "promo", "freight"]:
                    bill_totals["rounding_diff"].append(flt((bill_totals.get(f"{i}_rate_vat") - (bill_totals.get(f"{i}_rate_vat") / 1.12)), 2) - bill_totals.get(f"{i}_diff"))

                bill_totals["rounding_diff"] = flt(sum(bill_totals["rounding_diff"]), 2)
                doc.append('items', bill_totals)

                totals["t_msf"] += allocations["comp_total"]
                totals["t_diff"] += allocations["comp_diff"]
                totals["t_vat_ex"] += allocations["comp_vat_ex"]
                totals["t_vat"] += allocations["vat"]

            doc.flags.ignore_mandatory = True
            doc.insert()

            totals["usd_allocation"] = sum([totals['decoder'], totals['promo'], totals['freight'], totals['card']])
            totals["allocation"] = sum([totals['php_drate'], totals['php_prate'], totals['php_frate'], totals['php_crate']])
            totals["vat"] = totals["t_vat"]
            totals["vat_inc"] = totals["php_msf"] - totals["allocation"]
            totals["vat_ex"] = totals["vat_inc"] - totals["vat"]
            totals["comp_total"] = round2(sum((totals["vat_ex"], totals["vat"], totals["allocation"])))
            totals["comp_diff"] = totals["php_msf"] - totals["comp_total"]
            totals["comp_vat_ex"] = totals["vat_ex"] + totals["comp_diff"]


            _totals_usd = reduce(add, (map(Counter, [
                {"drate": i.get("drate"), "prate": i.get("prate"), "frate": i.get("frate"),
              "crate": i.get("crate")} for i in sbill_items])))

            self.append('billings', {
                'tax_category': bill.get('tx'),
                "billing_currency": "PHP",
                'customer_name': customer_.customer_name,
                'subscription_period': period.name,
                'billing_date': period.end_date,
                'currency': 'USD',
                'exchange_rate': self.exchange_rate,
                "account_manager": doc.account_manager or "",
                "assistant": doc.assistant,
                "customer": doc.customer,
                "bill_no": doc.name,
                "date": doc.bill_date,
                'total_msf': totals['msf'],
                'total_msf_vat_inc': totals['msf'] - totals["usd_allocation"],
                'total_msf_vat_ex': vat_(totals['msf'] - totals["usd_allocation"]),
                'total_vat': vat_(totals['msf'] - totals["usd_allocation"]) * 0.12,
                'total_decoder_rate': totals['decoder'],
                'total_promo_rate': totals['promo'],
                'total_freight_rate': totals['freight'],
                'total_card_rate': totals['card'],
                'usd_msf':  totals["php_msf"],
                'usd_msf_lv_inc': totals["vat_inc"],
                'usd_msf_lv_ex': totals["vat_ex"],
                'usd_vat': totals["vat"],
                'usd_decoder': totals["php_drate"],
                'usd_promo': totals["php_prate"],
                'usd_freight': totals["php_frate"],
                'usd_card': totals["php_crate"],
                'usd_decoder_ex': vat_(totals["decoder"]),
                'usd_promo_ex': vat_(totals["promo"]),
                'usd_freight_ex': vat_(totals["freight"]),
                'usd_card_ex': vat_(totals["card"]),
                'decoder_vat': get_difference(totals["php_drate"]),
                'promo_vat': get_difference(totals["php_prate"]),
                'freight_vat': get_difference(totals["php_frate"]),
                'card_vat': get_difference(totals["php_crate"]),
                'total_vat_inc': totals["allocation"],
                "computed_tamount": totals["t_msf"],
                "computed_tdiff": totals["t_diff"],
                "computed_vat_ex": totals["t_vat_ex"] + totals["t_diff"],
                "total_vat_ex": sum_(vat_(totals[i]) for i in ["decoder", "promo", "freight", "card"]),
                "total_vat_diff": totals["allocation"] - round2(vat_(totals["allocation"])),
                "t_drate_": _totals_usd.get("drate"),
                "t_prate_": _totals_usd.get("prate"),
                "t_frate_": _totals_usd.get("frate"),
                "t_crate_": _totals_usd.get("crate"),
                "t_rate_": sum(_totals_usd.values()),
                "v_drate": get_difference(_totals_usd.get("drate")),
                "v_prate": get_difference(_totals_usd.get("prate")),
                "v_frate": get_difference(_totals_usd.get("frate")),
                "v_crate": get_difference(_totals_usd.get("crate")),
                "v_rate": get_difference(sum(_totals_usd.values())),
                "x_drate": vat_(totals["php_drate"]),
                "x_prate": vat_(totals["php_prate"]),
                "x_frate": vat_(totals["php_frate"]),
                "x_crate": vat_(totals["php_crate"]),
                "x_rate": vat_(totals["allocation"]),
            })
            
        self.create_sales_invoice()

        frappe.msgprint(
            msg='Bill successfully generated',
            title='Success',
            indicator='yellow',
            raise_exception=False
        )
        self.save()
        self.db_set("generated", 1)
        frappe.db.set_value("Monthly PSOF", self.get("monthly_psof"), "billing_generated", 1)
