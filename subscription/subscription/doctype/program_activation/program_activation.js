// Copyright (c) 2021, ossphin and contributors
// For license information, please see license.txt


var get_serials = function(frm, program){
	frm.set_query('serial_no', 'included_programs', function() {
		return {
			"query": "subscription.subscription.doctype.program_activation.program_activation.get_program_serials",
			"filters": {
				'customer': frm.doc.customer_name
			}
		}
	});
}

frappe.ui.form.on("Program Activation", {
	// refresh: function(frm) {

	// },

	onload: (frm,cdt,cdn) => {
		frm.set_query('psof', () => {
			return {
				filters: {
					customer_name: frm.doc.customer_name
				}
			}
		})

		$.each(frm.doc.included_programs, (i,d) => {
			get_serials(frm, d.program)
		})
		cur_frm.refresh_fields(frm)
	},
	
	psof: frm => {
		frm.clear_table("included_programs")

		frappe.db.get_list("PSOF Program", {
			fields: ["subscription_program", "active", "psof", "name", "customer_name"],
			filters: {
				parent : frm.doc.psof
			}
		}).then(r => {
			$.each(r, (i, r) => {
				const {subscription_program, active, psof, name, customer_name} = r
				frm.add_child("included_programs", {
					program: subscription_program,
					active: active,
					psof: psof,
					psof_program: name,
					customer_name: customer_name
				})
			})
			frm.refresh_field('included_programs');
		})
	},

	customer_name: (frm, cdt, cdn) => {
		frm.set_query('psof', () => {
			return {
				filters: {
					customer_name: frm.doc.customer_name
				}
			}
		})
	}
});


