// Copyright (c) 2023, ossphin and contributors
// For license information, please see license.txt
/* eslint-disable */
const d = new Date();
const monthNames = ["January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
];
let years = Array.from({length: d.getUTCFullYear() - 2019 + 3}, (v, i) => i + 2019);

frappe.query_reports["Billing vs Sales"] = {
    tree: true,
    parent_field: 'parent',
    name_field: 'child',
    filters: [
        {
            fieldname: 'bill_month',
            label: __('Billing Month'),
            fieldtype: 'Select',
            options: monthNames.join('\n'),
			default: monthNames[d.getMonth() - 1],
			reqd: true,
        },
        {
            fieldname: 'sales_month',
            label: __('Sales Month'),
            fieldtype: 'Select',
            options: monthNames.join('\n'),
			default: monthNames[d.getMonth()],
			reqd: true,
        },
        {
            fieldname: 'year',
            label: __('Year'),
            fieldtype: 'Select',
            options: years.join('\n'),
			default: years[years.length -1],
			reqd: true,
        },
        {
            fieldname: 'psof_no',
            label: __('PSOF No'),
            fieldtype: 'Link',
            options: 'PSOF',
        },
        {
            fieldname: 'customer',
            label: __('Cable System'),
            fieldtype: 'Link',
            options: 'Customer',
        },
        {
            fieldname: 'has_variance',
            label: __('Has Variance'),
            fieldtype: 'Check',
            default: 0
        },
    ]
};
