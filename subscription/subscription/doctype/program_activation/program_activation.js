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

// OSSPHINC CUSTOM MATERIAL REQUEST
frappe.ui.form.on("Program Activation", {
	onload: (frm,cdt,cdn) => {

		let activation_req_list = []

		frappe.db.get_list('Program Activation', {
			fields: ['activation_req'],
			filters: {
				workflow_state: ['in',['Technical Assistant', 'For Approval', 'Approved']],
			}
		}).then(records => {
			if(records.length > 0){
				records.forEach(e =>{
					//console.log(e.activation_req)
					activation_req_list.push(e.activation_req)
				})

			}

			frm.set_query('activation_req', () => {
				return {
					filters: {
						name: ['not in', activation_req_list],
						workflow_state: 'Sent to Technical'
					}
				}
			})

		})


		//original
		// frm.set_query('activation_req', () => {
		// 	return {
		// 		filters: {
		// 			workflow_state: 'Sent to Technical'
		//
		// 		}
		// 	}
		// })
		
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

	// validate: (frm) =>{
	// 	frm.clear_table("included_programs")
	// 	frm.call("load_req")
	// 	frm.call("load_psof_programs")
	// 	frm.refresh_field('included_programs')
	// },

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


// frappe.ui.form.on('Program Activation', {
// 	refresh(frm) {
// 		// your code here
// 	},
//
// 	onload: function(frm) {
//     frm.set_query('activation_req', function() {
//       return {
//         query: function() {
//           return frappe.db.get_list('Program Activation Request', {
//             fields: ['customer', 'workflow_state'],
//             filters: [
//               // Add your filters for Sales Invoice here (if any)
//               ['workflow_state', '=', 'Pending'],
//               ['workflow_state', '=', ''],
//             ],
//             fields: ['customer']
//           });
//         }
//       };
//     });
//   }
//
// })

//
// frappe.ui.form.on('Sales Invoice', {
//     refresh: function(frm) {
//         // Your custom logic here when the form is refreshed
//
//         // Example: Fetching a Sales Invoice document
//         frappe.call({
//             method: 'frappe.client.get',
//             args: {
//                 doctype: 'Sales Invoice',
//                 name: frm.doc.name
//             },
//             callback: function(response) {
//                 var salesInvoiceDoc = response.message;
//
//                 // Now you can access the fields of the Sales Invoice document
//                 if (salesInvoiceDoc) {
//                     console.log('Sales Invoice Total Amount:', salesInvoiceDoc.total);
//                 }
//             }
//         });
//     },
//
//     // Other events and functions can be defined here
// });




