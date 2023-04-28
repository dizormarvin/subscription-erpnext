// Copyright (c) 2016, ossphin and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["BILLING LAST MONTH VS SALES THIS MONTH"] = {
	tree: true,
	parent_field: "parent_customer",
	name_field: "customer",
	"filters": [
		{
			fieldname: 'mpsof',
			label: __('Sales This Month'),
			fieldtype: 'Link',
			options: 'Monthly PSOF',
		},
		{
			fieldname: 'customer',
			label: __('Cable System'),
			fieldtype: 'Link',
			options: 'Customer',
		},
		{
			fieldname: 'program',
			label: __('Subscription Program'),
			fieldtype: 'Link',
			options: 'Subscription Program',
		},
		{
			fieldname: 'psof',
			label: __('PSOF No'),
			fieldtype: 'Link',
			options: 'PSOF',
		},
		{
			fieldname: 'sub_period',
			label: __('Subscription Period'),
			fieldtype: 'Link',
			options: 'Subscription Period'
		},
		{
			fieldname: 'has_variance',
			label: __('Has Variance'),
			fieldtype: 'Check',
			default: 0
		},
	]
};
