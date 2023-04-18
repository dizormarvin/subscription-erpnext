// Copyright (c) 2023, ossphin and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Monthly Sales Comparison"] = {
	tree: true,
	parent_field: "parent_customer",
	name_field: "child_program",
    "filters": [
		{fieldname: 'mpsof_1', label: __('Monthly Sales'), fieldtype: 'Link', options: 'Monthly PSOF', reqd: true, default: '02-2023-02'},
		{fieldname: 'mpsof_2', label: __('Against Monthly Sales'), fieldtype: 'Link', options: 'Monthly PSOF', reqd: true, default: '02-2023-01'},
		{fieldname: 'customer_name', label: __('Cable System'), fieldtype: 'Link', options: 'Customer'},
		{fieldname: 'subscription_program', label: __('Subscription Program'), fieldtype: 'Link', options: 'Subscription Program'},
		{fieldname: 'psof', label: __('PSOF'), fieldtype: 'Link', options: 'PSOF'},
		{fieldname: 'has_variance', label: __('Has Variance'), fieldtype: 'Check'},
		{fieldname: 'date_from', label: __('From Date'), fieldtype: 'Date'},
		{fieldname: 'date_to', label: __('To Date'), fieldtype: 'Date'},
    ]
};
