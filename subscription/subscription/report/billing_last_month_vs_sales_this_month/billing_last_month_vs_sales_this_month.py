# Copyright (c) 2013, ossphin and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from  frappe import _


def execute(filters=None):
	if filters:
		return get_columns(), get_data(filters)
	else:
		return get_columns(), []


def get_data(filters):
	current_bill = get_bill(filters['sales_this_month'])

	data = []
	data.append(['PB000006', filters['sales_this_month']])
	data.append([1, 2])
	data.append([3, 4])
	frappe.msgprint(str(get_bill(filters['sales_this_month'])))
	return get_bill(filters['sales_this_month'])


def get_bill(bill_no):
	doc = frappe.get_doc('Monthly PSOF', bill_no)
	billing = {'monthly_psof_bill_no': bill_no, 'data': []}
	subs_bill = doc.get('billings')

	for bill in subs_bill:
		subs_doc = frappe.get_doc('Subscription Bill', bill.bill_no)
		subs_item = subs_doc.get('items')
		billing['data'].append({
			'system': bill.customer,
			'bill_no': bill.bill_no,
			'bill_date': bill.date,
			'bill_data': [
				{
					'program': item.subscription_program,
					'psof': item.psof_no,
					'm_psof': item.monthly_psof_no,
					'subs': item.no_of_subs,
					'msf': item.subscription_fee,
					'msf_less_vat': item.subscription_rate,
					'vat': item.vat,
					'ird': item.decoder_rate,
					'card': item.card_rate,
					'promo': item.promo_rate,
					'freight': item.freight_rate
				}
				for item in subs_item]
		})
	return billing


def get_columns():
	return [
		f"Billing Last Month:Link/Monthly PSOF Billing:350",
		f"Sales This Month:Link/Monthly PSOF Billing:350"
	]