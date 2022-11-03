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
	onload: (frm,cdt,cdn) => {
		frm.set_query('activation_req', () => {
			return {
				filters: {
					workflow_state: 'Sent to Technical'
				}
			}
		})
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

	activation_req: (frm) => {
		frm.clear_table("included_programs")
		frm.call("load_req")
		frm.refresh_fields()
		frm.refresh_field('included_programs')
	},

	psof: frm => {
		frm.clear_table("included_programs")
		frm.call("load_psof_programs")
		frm.refresh_field('included_programs')
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


