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
			else if (frm.doc.revised) {
				return {
					filters: {
						subscription_contract: frm.doc.reference_contract,
					}
				}
			}
		});

		if (frm.doc.docstatus === 1) {
			if (frm.doc.status === "Expired") {
				frm.add_custom_button("Make Dummy Contract", () => {
					console.log(frm.doc.contract_number)
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
			// ossphinc04112023 create new contract then inactive
			if (frm.doc.status === "Expired" && frm.doc.bill_expired != 1) {
				frm.add_custom_button("Renew Contract", () => {
					var revised_expired = 0
					amend_contract(frm, revised_expired);
				}, 'Contract Options')
			}
			if (frm.doc.status === "Active") {
				frm.add_custom_button("Amend Contract", () => {
					var revised_expired = 0
					amend_contract(frm, revised_expired);
				}, 'Contract Options')
			}
			if (frm.doc.status === "Expired" && frm.doc.bill_expired != 1) {
				frm.add_custom_button("Amend Expired Contract", () => {
					var revised_expired = 1
					amend_contract(frm, revised_expired);
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

	refresh: (frm) => {
		let contract_number_list = []

		if (frm.doc.contract_number){
			let contract_number = frm.doc.contract_number.split("-")

			frappe.db.get_list('Subscription Contract', {
				fields: ['psof'],
				filters: {
					contract_number: ['like', '%' + contract_number.join('%') + '%']
				}
			}).then(records => {
				records.forEach(e =>{
					if(e.psof){
						contract_number_list.push(e.psof)
					}
				})
			})
		}

		frm.set_query('psof', () => {
			return {
				filters: {
					subscription_contract: frm.doc.contract_number,
					name: ['not in', contract_number_list]
				}
			}
		})
	},
});
function amend_contract(frm, revised_expired){
	frappe.call({
		method: "subscription.subscription.doctype.psof.psof.create_new_contract",
		args: {
			contract: frm.doc.name,
			revised_expired: revised_expired
		},
		callback: (r) => {
			if (r) {
				frappe.set_route("Form", "Subscription Contract", r.message)
			}
		}
	})
}
