// Copyright (c) 2020, ossphin and contributors
// For license information, please see license.txt
{% include 'erpnext/selling/sales_common.js' %}

frappe.ui.form.on('Subscription Contract',  {
	onload: (frm) => {
		frm.add_custom_button("Make Dummy Contract", () => alert("hello"), 'Contract Options')
		frm.add_custom_button("Supersede Dummy Contract", () => alert("hello"), 'Contract Options')
	},

	setup: (frm) => {
		frm.doc.currency = 'USD'
	},

	start_date: frm => {
		let date = frappe.format(new Date(frm.doc.start_date), {fieldType: 'Date'})
		if (!frm.doc.bill_expired) {frm.set_value('expiry_date', frappe.format(new Date(date.getFullYear() + 1, date.getMonth(), 0), {fieldType: 'Date'}))}
	},

	contract_number: frm => {
		frm.set_query('psof', () => {
			return {
				filters: {
					subscription_contract: frm.doc.contract_number
				}
			}
		})
	},

});

