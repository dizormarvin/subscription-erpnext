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
import time
from collections import defaultdict
from itertools import groupby
from operator import itemgetter
import json

class MonthlyPSOFBilling(Document):
    """Monthly Billing Generation"""

    def on_trash(self):
        self.status = 'Bills Deleted'
        linked_docs = self.count_linked_doc()
        frappe.get_doc("Monthly PSOF", self.monthly_psof).db_set("billing_generated", 0)

        frappe.db.delete("Subscription Bill", {'subscription_period': self.name})
        frappe.db.delete("Subscription Bill Item", {'subscription_period': self.name})
        frappe.db.delete("Monthly PSOF Bill", {'subscription_period': self.name})

        frappe.db.delete("Digital SOA", {'subscription_period': self.name})
        frappe.db.delete("Digital SOA Journal", {'subscription_period': self.name})
        frappe.db.delete("Digital SOA Payment", {'subscription_period': self.name})

        frappe.db.delete("Sales Invoice", {'subs_period': self.name})

        for items in self.get("billings"):
            frappe.db.delete("GL Entry", {'subscription_bill': items.bill_no})

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
        # sb = frappe.get_doc("Subscription Bill", {'subscription_period': self.name})
        # sb.cancel()

        frappe.db.sql("""update `tabSubscription Bill` set  docstatus=2
                                          WHERE subscription_period = %s """, (self.name))

        frappe.db.sql("""update `tabSubscription Bill Item` set  docstatus=2
                                          WHERE parent in ( select name from `tabSubscription Bill` where subscription_period= %s )""",
                      (self.name))

        linked_docs = frappe.get_all("Sales Invoice", filters={"subs_period": self.name})
        for linked_doc in linked_docs:
            linked_doc_obj = frappe.get_doc("Sales Invoice", linked_doc.name)
            linked_doc_obj.cancel()

        # si = frappe.get_doc("Sales Invoice", {'subs_period': self.name})
        # si.cancel()

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
        if self.billings:
            self.submit_billings()

            frappe.msgprint(
                msg='Bills successfully posted',
                title='Success',
                indicator='yellow',
                raise_exception=False
            )
        else:
            frappe.msgprint(
                msg='Billing should create first Before Submission',
                title='Billing Not Created',
                indicator='red',
                raise_exception=True
            )
        #
        # prepared_doc = frappe.new_doc('Prepared Report')
        # prepared_doc.docstatus = 0
        # prepared_doc.status = 'Queued'
        # prepared_doc.report_name = "Monthly Sales Generation Sales Invoice"
        # prepared_doc.ref_report_doctype = 'Monthly Sales Generation Sales Invoice'
        # prepared_doc.owner = 'Administrator'
        # prepared_doc.doctype = 'Prepared Report'
        # prepared_doc.insert()

    def after_insert(self):
        pass

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
        digitals = []
        soa_payment = []
        sales_bills = frappe.db.sql(f"""
            SELECT
                d.customer_name as customer_name,
                d.parent as parent,
                d.psof as psof,
                d.customer as customer,
                d.assistant as assistant_manager,
                d.account_manager as account_manager,
                h.subscription_period as subscription_period,
                d.tax_category as tax_category,
                ROUND(b.exchange_rate, 2) as exchange_rate,
                ROUND(date_from, 2) as date_from,
                ROUND(date_to, 2) as date_to,
                subscription_program,
                contract,
                ROUND(contract_start, 2) as contract_start,
                ROUND(contract_end, 2) as contract_end,
                ROUND(subscription_fee, 2) as subs_fee,
                
                
                
                
                
                ROUND(subscription_fee * {self.exchange_rate}, 2) as subscription_fee,
                ROUND(subscription_fee * {self.exchange_rate}, 2) - ROUND((freight_rate + card_rate + decoder_rate + promo_rate) * {self.exchange_rate}, 2) as subscription_rate_inc,
                ROUND((ROUND(subscription_fee * {self.exchange_rate}, 2) - ROUND((freight_rate + card_rate + decoder_rate + promo_rate) * {self.exchange_rate}, 2)) / 1.12, 2) as subscription_rate_ex1,
                ROUND(subscription_rate * {self.exchange_rate}, 2) as subscription_rate_ex,
                ROUND(subscription_fee * {self.exchange_rate}, 2) - ROUND((freight_rate + card_rate + decoder_rate + promo_rate) * {self.exchange_rate}, 2) - ROUND((ROUND(subscription_fee * {self.exchange_rate}, 2) - ROUND((freight_rate + card_rate + decoder_rate + promo_rate) * {self.exchange_rate}, 2)) / 1.12, 2) as vat1,
                ROUND(vat * {self.exchange_rate}, 2) as vat,
                ROUND(decoder_rate * {self.exchange_rate}, 2) as decoder_rate_vat,
                ROUND(card_rate * {self.exchange_rate}, 2) as card_rate_vat,
                ROUND(promo_rate * {self.exchange_rate}, 2) as promo_rate_vat,
                ROUND(freight_rate * {self.exchange_rate}, 2) as freight_rate_vat,
                ROUND(decoder_rate * {self.exchange_rate} / 1.12, 2) as decoder_rate,
                ROUND(card_rate * {self.exchange_rate} / 1.12, 2) as card_rate,
                ROUND(promo_rate * {self.exchange_rate} / 1.12, 2) as promo_rate,
                ROUND(freight_rate * {self.exchange_rate} / 1.12, 2) as freight_rate,
                ROUND(decoder_rate * {self.exchange_rate}, 2) - ROUND(decoder_rate * {self.exchange_rate} / 1.12, 2) as decoder_diff,
                ROUND(card_rate * {self.exchange_rate}, 2) - ROUND(card_rate * {self.exchange_rate} / 1.12, 2) as card_diff,
                ROUND(promo_rate * {self.exchange_rate}, 2) - ROUND(promo_rate * {self.exchange_rate} / 1.12, 2) as promo_diff,
                ROUND(freight_rate * {self.exchange_rate}, 2) - ROUND(freight_rate * {self.exchange_rate} / 1.12, 2) as freight_diff,
                ROUND((freight_rate + card_rate + decoder_rate + promo_rate) * {self.exchange_rate}, 2) as total_alloc_vat,
                ROUND(((freight_rate + card_rate + decoder_rate + promo_rate) * {self.exchange_rate}) / 1.12, 2) as total_alloc,
                ROUND((freight_rate + card_rate + decoder_rate + promo_rate) * {self.exchange_rate}, 2) - ROUND(((freight_rate + card_rate + decoder_rate + promo_rate) * {self.exchange_rate}) / 1.12, 2) as total_diff,
                'self.name' as created_from,
                
                
                
                round(((card_rate + freight_rate + promo_rate + decoder_rate) * {self.exchange_rate} / 1.12) * .12, 2) + round(((subscription_fee  - (card_rate + freight_rate + promo_rate + decoder_rate)) * {self.exchange_rate} / 1.12) * .12, 2) as amount_vat,
                round((subscription_fee  - (card_rate + freight_rate + promo_rate + decoder_rate)) * {self.exchange_rate} / 1.12, 2) as amount
                
                
                
                
            FROM
                `tabMonthly PSOF` h,
                `tabMonthly PSOF Program Bill` d,
                `tabSubscription Period` p,
                `tabMonthly PSOF Billing` b
            WHERE
                h.name = d.parent
                AND
                h.name = '{self.monthly_psof}'
                AND
                h.subscription_period = p.name
                and h.name = b.monthly_psof
            order by customer
            
                ;""", as_dict=1)

        consolidated_data = {}
        # Group data by customer
        for entry in sales_bills:
            customer_id = entry["customer"]
            if customer_id not in consolidated_data:
                consolidated_data[customer_id] = []
            consolidated_data[customer_id].append(entry)

        consolidated_result = []

        for customer_id, entries in consolidated_data.items():
            header = {
                "customer": customer_id,
                "customer_name": entries[0]["customer_name"],
                "tax_category": entries[0]["tax_category"],
                "contract": entries[0]["contract"],
                "subscription_period": entries[0]["subscription_period"],
                "account_manager": entries[0]["account_manager"],
                "parent": entries[0]["parent"],
                # "psof": entries[0]["psof"],
                "exchange_rate": entries[0]["exchange_rate"]
            }
            child_table = [{key: value for key, value in entry.items() if key not in header} for entry in entries]
            consolidated_result.append({"header": header, "child_table": child_table})

        # Print or do whatever you want with consolidated_result

        for item in consolidated_result:
            header = item["header"]
            childs = item["child_table"]

            customer_ = frappe.get_doc("Customer", header['customer'])
            doc = frappe.new_doc("Subscription Bill")
            doc.customer = header['customer']
            doc.customer_name = header['customer_name']
            # doc.bill_date = bill.date
            doc.bill_date = self.posting_date
            doc.subscription_period = header['subscription_period']
            doc.due_date = get_due_date(doc.bill_date, "Customer", doc.customer)
            doc.exchange_rate = header['exchange_rate']
            doc.account_manager = header['account_manager']
            doc.assistant = customer_.billing_assistant
            doc.monthly_psof = header['parent']
            # doc.psof = header['psof']
            doc.total_in_php = sum(i.get('subscription_fee') for i in childs)
            doc.total_in_usd = sum(i.get('subs_fee') for i in childs)

            for child in childs:
                # newamount = (child.get("subscription_fee") - (child.get("decoder_rate_vat") + child.get("freight_rate_vat") + child.get("promo_rate_vat") + child.get("card_rate_vat"))) / 1.12
                # newvat = ((((child.get("subscription_fee")) - ((child.get("decoder_rate_vat")) + (child.get("card_rate_vat")) + (child.get("promo_rate_vat")) + (child.get("freight_rate_vat")))) / 1.12) * .12) + (child.get("decoder_diff")) + (child.get("card_diff")) + (child.get("promo_diff")) + (child.get("freight_diff"))
                # computed_diff = flt((child.get("subscription_fee") - (newamount + child.get("decoder_rate") + child.get("freight_rate") + child.get("promo_rate") + child.get("card_rate") + newvat)))
                doc.append('items',
                        {
                            "created_from": self.monthly_psof,
                            'customer': doc.customer,
                            'subscription_period': doc.subscription_period,
                            'bill_date': doc.bill_date,
                            "subscription_program": child.get('subscription_program'),
                            "subs_fee": child.get('subs_fee'),
                            "subscription_fee": child.get('subscription_fee'),
                            "subscription_rate_inc": child.get('subscription_rate_inc'),
                            "subscription_rate_ex": child.get('subscription_rate_ex'),
                            'vat': child.get('vat'),
                            # 'exchange_rate': self.exchage_rate,
                            'exchange_rate': child.get('exchange_rate'),

                            "monthly_psof_no": doc.monthly_psof,
                            "psof_no": child.get('psof'),
                            'contract': child.get('contract'),

                            'decoder_rate_vat': child.get('decoder_rate_vat'),
                            'card_rate_vat': child.get('card_rate_vat'),
                            'promo_rate_vat': child.get('promo_rate_vat'),
                            'freight_rate_vat': child.get('freight_rate_vat'),

                            'decoder_rate': child.get('decoder_rate'),
                            'card_rate': child.get('card_rate'),
                            'promo_rate': child.get('promo_rate'),
                            'freight_rate': child.get('freight_rate'),

                            'decoder_diff': child.get('decoder_diff'),
                            'card_diff': child.get('card_diff'),
                            'promo_diff': child.get('promo_diff'),
                            'freight_diff': child.get('freight_diff'),

                            'total_alloc_vat': child.get('total_alloc_vat'),
                            'total_alloc': child.get('total_alloc'),
                            'total_diff': child.get('total_diff'),
                            'amount_vat': child.get('amount_vat'),
                            # 'computed_diff': computed_diff,

                        }
                )

            doc.flags.ignore_mandatory = True
            doc.insert()
            self.append('billings', {
                'customer': doc.customer,
                'usd_msf': sum(i.get('subscription_fee') for i in childs),
                'bill_no': doc.name,
                'date': self.posting_date,
                'exchange_rate': self.exchange_rate
            })

        self.create_sales_invoice()

        frappe.msgprint(
            msg='Bill successfully generated',
            title='Success',
            indicator='yellow',
            raise_exception=False
        )

        self.save()

        self.create_digital()
        self.db_set("generated", 1)
        frappe.db.set_value("Monthly PSOF", self.get("monthly_psof"), "billing_generated", 1)

    @frappe.whitelist()
    def create_digital(self):
        subscription_bill = frappe.db.get_list("Monthly PSOF Bill", {"parent": self.name}, "bill_no", pluck="bill_no")

        for subs_bill in subscription_bill:
            soa_bill = frappe.db.get_list('Subscription Bill', filters={'name': subs_bill}, fields=['name', 'customer', 'customer_name', 'account_manager', 'subscription_period'])

            period = frappe.get_doc("Subscription Period", self.subscription_period)

            collect = frappe.db.sql("""
                select 
                name as payment, 
                party as customer, 
                posting_date, 
                pr_no, 
                paid_amount as amount,
                mode_of_payment,
                case 
                    when mode_of_payment in ('Check', 'Check-USD') then reference_date
                    when mode_of_payment in ('Direct Deposit-USD', 'Direct Deposit') then direct_deposit_date
                    else pr_date
                end as dated
                
                from `tabPayment Entry`
                where billing_date between '{}' and '{}' and party = '{}' and docstatus = 1

           """.format(period.start_date, period.end_date, soa_bill[0].customer), as_dict=1)

            # journal = frappe.db.sql("""
            # SELECT
            #     jea.parent, je.name as journal, je.total_credit as amount, je.naming_series, je.posting_date, je.soa_remark_3, jea.party as customer
            # FROM
            #     `tabJournal Entry Account` as jea
            # LEFT JOIN
            #     `tabJournal Entry` as je ON je.name = jea.parent
            # WHERE
            #     jea.docstatus = 1 and je.naming_series in ('BILL-JV-.YYYY.-', 'BILL-JV-.YYYY.-.MM.-.####') and je.billing_date between '{}' and '{}' and jea.party = '{}'
            # """.format(period.start_date, period.end_date, soa_bill[0].customer), as_dict=1)

            journal = frappe.db.sql("""
                SELECT
                    sum(jea.debit) as debit, 
                    sum(jea.credit) as credit, 
                    jea.parent, 
                    je.name as journal, 
                    je.posting_date, 
                    je.soa_remark_3, 
                    jea.party as customer,
                    case
                        when sum(jea.debit) = 0 then -sum(jea.credit)
                        else sum(jea.debit)
                    end as amount
                FROM
                    `tabJournal Entry Account` as jea
                LEFT JOIN
                    `tabJournal Entry` as je ON je.name = jea.parent
                WHERE
                    jea.docstatus = 1 and je.naming_series in ('BILL-JV-.YYYY.-', 'BILL-JV-.YYYY.-.MM.-.####') and je.billing_date between '{}' and '{}' and jea.party = '{}' and jea.account  LIKE '%ACCTS. REC.%'
            """.format(period.start_date, period.end_date, soa_bill[0].customer), as_dict=1)

            # frappe.msgprint("<pre>{}</pre>".format(collect))

            doc_soa = frappe.new_doc("Digital SOA")
            doc_soa.billing_no = soa_bill[0].name
            doc_soa.customer_code = soa_bill[0].customer
            doc_soa.customer = soa_bill[0].customer_name,
            doc_soa.monthly_billing_generation = self.name
            doc_soa.account_manager = soa_bill[0].account_manager or "",
            doc_soa.subscription_period = soa_bill[0].subscription_period,
            doc_soa.date = soa_bill[0].bill_date,

            for pay in collect:
                if soa_bill[0].customer == pay.get('customer'):
                    # frappe.msgprint("<pre>{}</pre>".format(pay))
                    pay['subscription_period'] = soa_bill[0].subscription_period
                    doc_soa.append("payment", pay)

            for adjustment in journal:
                if soa_bill[0].customer == adjustment.get('customer'):
                    adjustment['subscription_period'] = soa_bill[0].subscription_period
                    doc_soa.append("journal", adjustment)

            doc_soa.insert()

    @frappe.whitelist()
    def test(self):
        # frappe.msgprint('test print')
        return 'test'



@frappe.whitelist()
def generate_loading_bill(monthlypsof, docname):
    doc = frappe.get_doc("Monthly PSOF Billing", docname)
    # digitals = []
    # soa_payment = []
    # decimal = 2
    sales_bills = frappe.db.sql(f"""
        SELECT
            d.customer_name as customer_name,
            d.parent as parent,
            d.psof as psof,
            d.customer as customer,
            d.assistant as assistant_manager,
            d.account_manager as account_manager,
            h.subscription_period as subscription_period,
            d.tax_category as tax_category,
            ROUND(b.exchange_rate, 2) as exchange_rate,
            ROUND(date_from, 2) as date_from,
            ROUND(date_to, 2) as date_to,
            subscription_program,
            contract,
            ROUND(contract_start, 2) as contract_start,
            ROUND(contract_end, 2) as contract_end,
            ROUND(subscription_fee, 2) as subs_fee,





            ROUND(subscription_fee * {doc.exchange_rate}, 2) as subscription_fee,
            ROUND(subscription_fee * {doc.exchange_rate}, 2) - ROUND((freight_rate + card_rate + decoder_rate + promo_rate) * {doc.exchange_rate}, 2) as subscription_rate_inc,
            ROUND((ROUND(subscription_fee * {doc.exchange_rate}, 2) - ROUND((freight_rate + card_rate + decoder_rate + promo_rate) * {doc.exchange_rate}, 2)) / 1.12, 2) as subscription_rate_ex1,
            ROUND(subscription_rate * {doc.exchange_rate}, 2) as subscription_rate_ex,
            ROUND(subscription_fee * {doc.exchange_rate}, 2) - ROUND((freight_rate + card_rate + decoder_rate + promo_rate) * {doc.exchange_rate}, 2) - ROUND((ROUND(subscription_fee * {doc.exchange_rate}, 2) - ROUND((freight_rate + card_rate + decoder_rate + promo_rate) * {doc.exchange_rate}, 2)) / 1.12, 2) as vat1,
            ROUND(vat * {doc.exchange_rate}, 2) as vat,
            ROUND(decoder_rate * {doc.exchange_rate}, 2) as decoder_rate_vat,
            ROUND(card_rate * {doc.exchange_rate}, 2) as card_rate_vat,
            ROUND(promo_rate * {doc.exchange_rate}, 2) as promo_rate_vat,
            ROUND(freight_rate * {doc.exchange_rate}, 2) as freight_rate_vat,
            ROUND(decoder_rate * {doc.exchange_rate} / 1.12, 2) as decoder_rate,
            ROUND(card_rate * {doc.exchange_rate} / 1.12, 2) as card_rate,
            ROUND(promo_rate * {doc.exchange_rate} / 1.12, 2) as promo_rate,
            ROUND(freight_rate * {doc.exchange_rate} / 1.12, 2) as freight_rate,
            ROUND(decoder_rate * {doc.exchange_rate}, 2) - ROUND(decoder_rate * {doc.exchange_rate} / 1.12, 2) as decoder_diff,
            ROUND(card_rate * {doc.exchange_rate}, 2) - ROUND(card_rate * {doc.exchange_rate} / 1.12, 2) as card_diff,
            ROUND(promo_rate * {doc.exchange_rate}, 2) - ROUND(promo_rate * {doc.exchange_rate} / 1.12, 2) as promo_diff,
            ROUND(freight_rate * {doc.exchange_rate}, 2) - ROUND(freight_rate * {doc.exchange_rate} / 1.12, 2) as freight_diff,
            ROUND((freight_rate + card_rate + decoder_rate + promo_rate) * {doc.exchange_rate}, 2) as total_alloc_vat,
            ROUND(((freight_rate + card_rate + decoder_rate + promo_rate) * {doc.exchange_rate}) / 1.12, 2) as total_alloc,
            ROUND((freight_rate + card_rate + decoder_rate + promo_rate) * {doc.exchange_rate}, 2) - ROUND(((freight_rate + card_rate + decoder_rate + promo_rate) * {doc.exchange_rate}) / 1.12, 2) as total_diff,
            'self.name' as created_from,



            round(((card_rate + freight_rate + promo_rate + decoder_rate) * {doc.exchange_rate} / 1.12) * .12, 2) + round(((subscription_fee  - (card_rate + freight_rate + promo_rate + decoder_rate)) * {doc.exchange_rate} / 1.12) * .12, 2) as amount_vat,
            round((subscription_fee  - (card_rate + freight_rate + promo_rate + decoder_rate)) * {doc.exchange_rate} / 1.12, 2) as amount




        FROM
            `tabMonthly PSOF` h,
            `tabMonthly PSOF Program Bill` d,
            `tabSubscription Period` p,
            `tabMonthly PSOF Billing` b
        WHERE
            h.name = d.parent
            AND
            h.name = '{monthlypsof}'
            AND
            h.subscription_period = p.name
            and h.name = b.monthly_psof
        order by customer

            ;""", as_dict=1)

    consolidated_data = {}
    # Group data by customer
    for entry in sales_bills:
        customer_id = entry["customer"]
        if customer_id not in consolidated_data:
            consolidated_data[customer_id] = []
        consolidated_data[customer_id].append(entry)

    consolidated_result = []

    for customer_id, entries in consolidated_data.items():
        header = {
            "customer": customer_id,
            "customer_name": entries[0]["customer_name"],
            "tax_category": entries[0]["tax_category"],
            "contract": entries[0]["contract"],
            "subscription_period": entries[0]["subscription_period"],
            "account_manager": entries[0]["account_manager"],
            "parent": entries[0]["parent"],
            "psof": entries[0]["psof"],
            "exchange_rate": entries[0]["exchange_rate"]
        }
        child_table = [{key: value for key, value in entry.items() if key not in header} for entry in entries]
        consolidated_result.append({"header": header, "child_table": child_table})


    return consolidated_result

@frappe.whitelist()
def g_bill(bill):
    bill_data = json.loads(bill)
    header = bill_data["header"]
    childs = bill_data["child_table"]

    # customer_ = frappe.get_doc("Customer", header['customer'])
    # doc = frappe.new_doc("Subscription Bill")
    # doc.customer = header['customer']
    # doc.customer_name = header['customer_name']
    # # doc.bill_date = bill.date
    # doc.bill_date = self.posting_date
    # doc.subscription_period = header['subscription_period']
    # doc.due_date = get_due_date(doc.bill_date, "Customer", doc.customer)
    # doc.exchange_rate = header['exchange_rate']
    # doc.account_manager = header['account_manager']
    # doc.assistant = customer_.billing_assistant
    # doc.monthly_psof = header['parent']
    # doc.psof = header['psof']
    # doc.total_in_php = sum(i.get('subscription_fee') for i in childs)
    # doc.total_in_usd = sum(i.get('subs_fee') for i in childs)
    #
    # for child in childs:
    #     # newamount = (child.get("subscription_fee") - (child.get("decoder_rate_vat") + child.get("freight_rate_vat") + child.get("promo_rate_vat") + child.get("card_rate_vat"))) / 1.12
    #     # newvat = ((((child.get("subscription_fee")) - ((child.get("decoder_rate_vat")) + (child.get("card_rate_vat")) + (child.get("promo_rate_vat")) + (child.get("freight_rate_vat")))) / 1.12) * .12) + (child.get("decoder_diff")) + (child.get("card_diff")) + (child.get("promo_diff")) + (child.get("freight_diff"))
    #     # computed_diff = flt((child.get("subscription_fee") - (newamount + child.get("decoder_rate") + child.get("freight_rate") + child.get("promo_rate") + child.get("card_rate") + newvat)))
    #     doc.append('items',
    #                {
    #                    "created_from": self.monthly_psof,
    #                    'customer': doc.customer,
    #                    'subscription_period': doc.subscription_period,
    #                    'bill_date': doc.bill_date,
    #                    "subscription_program": child.get('subscription_program'),
    #                    "subs_fee": child.get('subs_fee'),
    #                    "subscription_fee": child.get('subscription_fee'),
    #                    "subscription_rate_inc": child.get('subscription_rate_inc'),
    #                    "subscription_rate_ex": child.get('subscription_rate_ex'),
    #                    'vat': child.get('vat'),
    #                    # 'exchange_rate': self.exchage_rate,
    #                    'exchange_rate': child.get('exchange_rate'),
    #
    #                    "monthly_psof_no": doc.monthly_psof,
    #                    "psof_no": header['psof'],
    #                    'contract': child.get('contract'),
    #
    #                    'decoder_rate_vat': child.get('decoder_rate_vat'),
    #                    'card_rate_vat': child.get('card_rate_vat'),
    #                    'promo_rate_vat': child.get('promo_rate_vat'),
    #                    'freight_rate_vat': child.get('freight_rate_vat'),
    #
    #                    'decoder_rate': child.get('decoder_rate'),
    #                    'card_rate': child.get('card_rate'),
    #                    'promo_rate': child.get('promo_rate'),
    #                    'freight_rate': child.get('freight_rate'),
    #
    #                    'decoder_diff': child.get('decoder_diff'),
    #                    'card_diff': child.get('card_diff'),
    #                    'promo_diff': child.get('promo_diff'),
    #                    'freight_diff': child.get('freight_diff'),
    #
    #                    'total_alloc_vat': child.get('total_alloc_vat'),
    #                    'total_alloc': child.get('total_alloc'),
    #                    'total_diff': child.get('total_diff'),
    #                    'amount_vat': child.get('amount_vat'),
    #                    # 'computed_diff': computed_diff,
    #
    #                }
    #                )
    #
    #     doc.flags.ignore_mandatory = True
    #     doc.insert()
    #     self.append('billings', {
    #         'customer': doc.customer,
    #         'usd_msf': sum(i.get('subscription_fee') for i in childs),
    #         'bill_no': doc.name,
    #         'date': self.posting_date,
    #         'exchange_rate': self.exchange_rate
    #     })
    #
    # self.create_sales_invoice()
    #
    # frappe.msgprint(
    #     msg='Bill successfully generated',
    #     title='Success',
    #     indicator='yellow',
    #     raise_exception=False
    # )
    #
    # self.save()
    #
    # self.create_digital()
    # self.db_set("generated", 1)
    # frappe.db.set_value("Monthly PSOF", self.get("monthly_psof"), "billing_generated", 1)
    
    return header

# for print out
@frappe.whitelist()
def get_sub_bill(bill_no):
    sub_bill = frappe.db.sql(f"""
    	select *
        from `tabSubscription Bill Item`
        where parent = '{bill_no}'
    	""", as_dict=1)

    return sub_bill

