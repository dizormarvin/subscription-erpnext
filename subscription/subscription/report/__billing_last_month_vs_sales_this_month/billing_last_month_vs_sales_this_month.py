# Copyright (c) 2013, ossphin and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from  frappe import _
from frappe.utils import add_months, getdate, nowdate, flt


def execute(filters):
	data = get_data(filters)
	columns = get_columns()
	columns = add_col(columns, filters)
	return columns, data


def add_col(cols, filters):
	new_col = cols
	bill_month = 'Billing'
	sales_month = 'Sales'

	if filters.get("sub_period"):
		start = frappe.db.get_value("Subscription Period", filters.get("sub_period"), ['start_date'])
		bill_month = f'{format(getdate(add_months(start, -1)), "%B")} {bill_month}'
		sales_month = f'{format(getdate(start), "%B")} {sales_month}'

	new_col.append({
		"fieldname": "bill_last",
		"label": _(f'{bill_month}'),
		"fieldtype": "Currency",
		"width": 120,
	})

	new_col.append({
		"fieldname": "sales_now",
		"label": _(f'{sales_month}'),
		"fieldtype": "Currency",
		"width": 120,
	})

	new_col.append({
		"fieldname": "variance",
		"label": _('Variance'),
		"fieldtype": "Currency",
		"width": 100,
	})

	return new_col


def get_columns():
	return [
		{
			"fieldname": "customer",
			"label": _("System Name/Program Name"),
			"fieldtype": "data",
			"width": 300,
		},
		{
			"fieldname": "billing_no",
			"label": _("Monthly Billing"),
			"fieldtype": "Link",
			"options": "Monthly PSOF Billing",
			"width": 130,
		},
		{
			"fieldname": "sales_no",
			"label": _("Monthly Sales"),
			"fieldtype": "Link",
			"options": "Monthly PSOF",
			"width": 130,
		}]


def get_data(filters):
	monthly_sales = get_sales_data(filters)
	customer_data = compare_billing_sales(monthly_sales, filters)
	return customer_data


def compare_billing_sales(sales, filters):
	parent_customers = get_parent_customer(sales)
	customer_data = populate_customer_data(parent_customers, sales, filters)

	return customer_data


def get_parent_customer(sales):
	x = [{
		"customer": sale.get("customer_name"),
		"parent_customer": None,
		"indent": 0,
		"has_value": False,
		"sales_now": 0
	}
		for sale in sales]
	return [dict(t) for t in {tuple(d.items()) for d in x}]


def populate_customer_data(parent_customers, sales, filters):
	customer_data = []

	for customer in parent_customers:
		cur_cd = customer.copy()
		cur_cd["sales_now"] = sum([sale.get("subscription_fee") for sale in sales if customer.get("customer") == sale.get("customer_name")])
		cur_cd["bill_last"] = sum([get_billing_data(sale).get("subs_fee") for sale in sales if customer.get("customer") == sale.get("customer_name")])
		cur_cd["variance"] = flt(cur_cd.get("bill_last") - cur_cd.get("sales_now"))

		if filters.get('has_variance') and not cur_cd.get('variance'):
			continue

		customer_data.append(cur_cd)

		for sale in sales:
			if customer.get("customer") == sale.get("customer_name"):
				bill_data = get_billing_data(sale)

				customer_data.append({
					'customer': sale.get("subscription_program"),
					'parent_customer': customer.get("customer"),
					'indent': 1,
					'has_value': True,
					'sales_no': sale.get("parent"),
					'sales_now': sale.get('subscription_fee'),
					'bill_last': bill_data.get('subs_fee'),
					'billing_no': bill_data.get('parent'),
					'variance': flt(sale.get('subscription_fee') - bill_data.get('subs_fee'))
				})

	return customer_data


def get_sales_data(filters):
	sales_filter = ["WHERE MP.docstatus = 1"]

	if filters.get("sub_period"):
		sales_filter.append(f"MP.subscription_period = '{filters.get('sub_period')}'")
	if filters.get("mpsof"):
		sales_filter.append(f"MP.name = '{filters.get('mpsof')}'")
	if filters.get("customer"):
		sales_filter.append(f"MPPB.customer = '{filters.get('customer')}'")
	if filters.get("program"):
		sales_filter.append(f"MPPB.subscription_program = '{filters.get('program')}'")

	sales = frappe.db.sql(
		f"""SELECT
				MPPB.customer,
				MPPB.customer_name,
				MP.subscription_period,
				MPPB.psof,
				MPPB.parent,
				MPPB.subscription_program,
				MPPB.psof_program_bill,
				MPPB.date_from,
				MPPB.date_to,
				MPPB.subscription_fee
			FROM `tabMonthly PSOF` as MP
			LEFT JOIN `tabMonthly PSOF Program Bill` as MPPB on MPPB.parent = MP.name
				{' AND '.join(sales_filter)}
			GROUP BY
				MP.name, MPPB.customer, MPPB.subscription_program;""", as_dict=1
	)
	return sales


def get_billing_data(sales):
	bill_data = {
		'parent': None,
		'subs_fee': 0
	}

	def date_between(target, start, end):
		from frappe.utils import add_months
		return add_months(end, -1) >= target >= add_months(start, -1)

	bill = frappe.db.get_value("Subscription Bill Item", {
		"customer_name": sales.get("customer_name"),
		"subscription_program": sales.get("subscription_program"),
		"docstatus": ['!=', 2],
		"monthly_psof_no": sales.get("parent"),
	}, ["customer_name", "parent", "subs_fee", "customer", "bill_date"], as_dict=1)

	bill_data['parent'] = bill.get('parent')
	bill_data['subs_fee'] = bill.get('subs_fee')

	return bill_data


def valid_sales_billing_data(sale, bill):
	return (sales.get("date_from") >= bill.get("bill_date") >= sales.get("date_to")) and (
			bill.get("customer") == sale.get("customer") and bill.get("subscription_program") == sale.get("subscription_program"))
