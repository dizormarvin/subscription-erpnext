// Copyright (c) 2016, ossphin and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["BILLING LAST MONTH VS SALES THIS MONTH"] = {
	"filters": [
		{
			fieldname: 'sales_this_month',
			label: __('Sales This Month'),
			fieldtype: 'Link',
			options: 'Monthly PSOF',
		},
		{
			fieldname: 'billing_last_month',
			label: __('Billing Last Month'),
			fieldtype: 'Link',
			options: 'Monthly PSOF Billing',
		}
	]
};
