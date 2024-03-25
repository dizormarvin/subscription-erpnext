// Copyright (c) 2020, ossphin and contributors
// For license information, please see license.txt
{% include 'erpnext/selling/sales_common.js' %}

frappe.ui.form.on('Subscription Contract',  {
	validate: function(frm) {
        if (frm.doc.start_date >= frm.doc.expiry_date) {
            frappe.msgprint(__('Start Date should be less than or equal to Expiry Date.'));
            frappe.validated = false;
        }
    },

	onload: (frm) => {
		if (frm.is_new()) {
			frm.set_value('status', 'Active')
        }

		frm.set_query('psof', () => {
			if (frm.doc.bill_expired) {
				return {
					filters: {
						subscription_contract: frm.doc.contract_number,
					}
				}
			} else if (frm.doc.is_supersede) {
				return {
					filters: {
						subscription_contract: frm.doc.contract_number,
						bill_until_renewed: 1
					}
				}
			}
		});

		if (frm.doc.docstatus === 1) {
			if (frm.doc.status === "Expired") {
				frm.add_custom_button("Make Dummy Contract", () => {
					frappe.call({
						method: "subscription.subscription.doctype.psof.psof.create_dummy",
						args: {
							contract: frm.doc.name
						},
						callback: (r) => {
							if (r) {
								frappe.set_route("Form", "Subscription Contract", r.message)
							}
						}
					})
				}, 'Contract Options')
			}

			if (frm.doc.bill_expired === 1 && frm.doc.status === "Active") {
				/*
				frm.add_custom_button("Supersede Dummy Contract", () => {
					frappe.call({
						method: "subscription.subscription.doctype.psof.psof.supersede_dummy",
						args: {
							contract: frm.doc.name
						},
						callback: (r) => {
							if (r) {
								frappe.set_route("Form", "Subscription Contract", r.message)
							}
						}
					})
				}, 'Contract Options')
				*/

				frm.add_custom_button("Supersede Dummy Contract - Cableboss", () => {
					frappe.call({
						method: "subscription.subscription.doctype.psof.psof.supersede_dummy",
						args: {
							contract: frm.doc.name,
							cb: 1
						},
						callback: (r) => {
							if (r) {
								frappe.set_route("Form", "Subscription Contract", r.message)
							}
						}
					})
				}, 'Contract Options')

			} else if (frm.doc.bill_expired === 1 && frm.doc.status === "Expired") {
				frm.add_custom_button("Extend Dummy Contract", () => {
					frappe.call({
						method: "subscription.subscription.doctype.psof.psof.create_dummy",
						args: {
							contract: frm.doc.name,
							extend: 1
						},
						callback: (r) => {
							if (r) {
								frappe.set_route("Form", "Subscription Contract", r.message)
							}
						}
					})
				}, 'Contract Options')
			}
		}
	},

	setup: (frm) => {
		frm.doc.currency = 'USD'
	},

	start_date: frm => {
		let date = frappe.format(new Date(cur_frm.doc.start_date), {fieldType: 'Date'})
		//console.log(formattedDate)
		if (!cur_frm.doc.bill_expired) {cur_frm.set_value('expiry_date', frappe.format(new Date(date.getFullYear() + 1, date.getMonth(), 0), {fieldType: 'Date'}))}
	},

	contract_number: (frm) => {
		frm.set_query('psof', () => {
			return {
				filters: {
					subscription_contract: frm.doc.contract_number
				}
			}
		})
	},
});

