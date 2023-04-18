// Copyright (c) 2021, ossphin and contributors
// For license information, please see license.txt

frappe.ui.form.on('Monthly PSOF Billing', {
	refresh: function(frm) {
		if (frm.doc.status === 'Bills Generated' || frm.doc.status === 'Submitted') {
			frm.clear_custom_buttons();
		}

		if (!frm.doc.__islocal && !frm.doc.generated){
			frm.add_custom_button(__("Create Billings"), function() {
				cur_frm.call('create_bills', function(r){});
				cur_frm.refresh_fields(frm);
			});
		}
	},

	onload(frm) {
		frm.set_query('monthly_psof', () => {
			return {
				filters: {
					docstatus: 1,
					billing_generated: 0
				}
			}
		})
	}
});
