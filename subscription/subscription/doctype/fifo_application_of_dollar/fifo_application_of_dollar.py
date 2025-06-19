# Copyright (c) 2024, ossphin and contributors
# For license information, please see license.txt

import frappe
import json
import datetime

from frappe.model.document import Document


class FifoApplicationofDollar(Document):
	pass


@frappe.whitelist()
def get_query(doctype, txt, searchfield=None, start=None, page_len=None, filters=None):
	bank_account = filters.get('bank_account')
	deferred_revenue_account = filters.get('deferred_revenue_account')
	posting_date = filters.get('posting_date')
	transaction_type = filters.get('transaction_type')
	query = ''

	if filters.get('date_from') and filters.get('date_to'):
		date = f""" and posting_date between '{filters.get('date_from')}' and '{filters.get('date_to')}'"""

	if filters.get('date_from') and not filters.get('date_to'):
		date = f""" and posting_date = '{filters.get('date_from')}' """

	if transaction_type == 'Payment Entry':
		query = frappe.db.sql(f"""
			select name from `tabPayment Entry` where paid_to = '{bank_account}' {date}
		""")

	if transaction_type == 'Disbursement':
		query = frappe.db.sql(f"""
					select name from `tabDisbursement` where paid_to = '{bank_account}' {date}
				""")

	return query


@frappe.whitelist()
def get_collection():
	return


def get_disbursement():
	return


def get_journal():
	return


@frappe.whitelist()
def create_journal_entry():
	return


@frappe.whitelist()
def reverse_journal_entry():
	return

