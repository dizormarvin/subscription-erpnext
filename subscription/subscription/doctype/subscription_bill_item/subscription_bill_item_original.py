# Copyright (c) 2022, ossphin and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt
from erpnext.controllers.accounts_controller import get_taxes_and_charges


class SubscriptionBillItem(Document):
    def get_subs_rate(self):
        if self.get("tax_category") == "Vat Inclusive":
            newamount = (self.subscription_fee - (self.decoder_rate_vat + self.freight_rate_vat + self.promo_rate_vat + self.card_rate_vat)) / 1.12
            newvat = ((((self.subscription_fee) - ((self.decoder_rate_vat) + (self.card_rate_vat) + (self.promo_rate_vat) + (self.freight_rate_vat))) / 1.12) * .12) + (self.decoder_diff) + (self.card_diff) + (self.promo_diff) + (self.freight_diff)

            return flt(newamount + (self.subscription_fee - (newamount + self.decoder_rate + self.freight_rate + self.promo_rate + self.card_rate + newvat)))
            # return self.subscription_rate_ex - self.computed_diff
        return self.get("subscription_rate_inc")

    def create_invoice(self):
        invoice = frappe.get_doc({
            "doctype": "Sales Invoice",
            "customer": self.get("customer"),
            "due_date": self.get("bill_date"),
            "posting_date": self.get("bill_date"),
            "set_posting_time" : "1",
            "m_psof": self.get("created_from"),
            "date_from": self.get("date_from"),
            "date_to": self.get("date_to"),
            "subs_period": self.get("subscription_period"),
            "psof": self.get("psof_no"),
            "subs_contract": self.get("contract"),
            "contract_start": self.get("contract_start"),
            "contract_end": self.get("contract_end"),
            "subscription_bill": self.get("parent"),
            "debit_to": "11070005 - ACCTS. REC. - TRADE (ND) - CB",
            "currency": "PHP",
            "tax_category": self.get("tax_category"),
            "disable_rounded_total": 1
        })

        # invoice.append("items", {
        # 	"item_name": self.get("subscription_program"),
        # 	"qty": 1,
        # 	"description": self.get("subscription_program"),
        # 	"uom": "Nos",
        # 	"conversion_factor": 1,
        # 	"rate": self.get_subs_rate(),
        # 	# ossphinc 04282023
        # 	"price_list_rate": self.get_subs_rate(),
        # 	"base_price_list_rate": self.get_subs_rate(),
        # 	"discount_amount": self.get("rounding_diff"),
        # 	# ossphinc 04282023
        # 	'income_account': frappe.get_doc("Subscription Program",
        # 									 self.get("subscription_program")).get_sales_account()
        # })
        #
        # invoice.save()
        invoice.append("items", {
            "item_name": self.get("subscription_program"),
            "item_code": self.get("subscription_program"),
            "qty": 1,
            "description": self.get("subscription_program"),
            "uom": "Nos",
            "conversion_factor": 1,
            "rate": self.get_subs_rate(),
            #ossphinc 04282023
            "price_list_rate": self.get_subs_rate(),
            "base_price_list_rate": self.get_subs_rate(),
            "discount_amount": self.get("rounding_diff"),
            #ossphinc 04282023
            'income_account': frappe.get_doc("Subscription Program", self.get("subscription_program")).get_sales_account()
        })

        if self.get("tax_category") == "Vat Inclusive":
            taxes = get_taxes_and_charges("Sales Taxes and Charges Template", "VAT Inclusive")[0]
            taxes["charge_type"] = "Actual"
            taxes["tax_amount"] = flt(self.get("amount_vat"), 2)
            # taxes["tax_amount"] = flt(self.get("vat") + self.get("total_diff"), 2)
            invoice.append("taxes", taxes)
            invoice.save()

        try:
            for rate in ("decoder", "card", "promo", "freight"):
                if self.get(f"{rate}_rate") > 0:
                    invoice.append("items", self.add_invoice_item(rate))

            invoice.save()
            invoice.db_set("conversion_rate", self.exchange_rate)
            self.db_set("sales_invoice", invoice.get("name"))
        except Exception as e:
            frappe.throw(f"{e}")

    def add_invoice_item(self, rate):
        program = frappe.get_doc("Subscription Program", self.get("subscription_program"))

        for accounts in program.get("accounting_defaults"):
            if rate in accounts.get("item_group").lower():
                rate_ = self.get(f"{rate}_rate") if self.get("tax_category") == "Vat Inclusive" else self.get(
                    f"{rate}_rate_vat")
                return {
                    "item_name": accounts.get("item_name"),
                    "qty": 1,
                    "description": accounts.get("item_name"),
                    "uom": accounts.get("uom"),
                    "conversion_factor": 1,
                    "rate": rate_,
                    'income_account': accounts.get("sales_account"),
                    'cost_center': 'Main - CB'
                }
