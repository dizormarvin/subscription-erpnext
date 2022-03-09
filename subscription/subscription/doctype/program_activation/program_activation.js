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


	psof: function(frm) {
		cur_frm.call('get_programs', '', function(r){});
	},

	timeline_refresh: (frm, cdt, cdn) => {
		if (frm.doc.workflow_state == "Approved") {
			cur_frm.call('activate', '', function(r){})
			frm.refresh_fields('included_programs')
		}
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


