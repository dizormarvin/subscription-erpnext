// Copyright (c) 2021, ossphin and contributors
// For license information, please see license.txt

frappe.ui.form.on('Monthly PSOF Billing', {
	refresh: function(frm) {
		if (frm.doc.status === 'Bills Generated' || frm.doc.status === 'Submitted') {
			frm.clear_custom_buttons();
		}
		if (!frm.doc.__islocal && !frm.doc.generated){
			frm.add_custom_button(__("Create Billings"), function() {
				if(!frm.doc.posting_date){
					frappe.throw(__('Select Posting Date First'))
				}
				else if(frm.doc.exchange_rate == 0){
					frappe.throw(__('Add Exchage Rate'))
				}
				else{
					cur_frm.call('create_bills', function(r){});
					cur_frm.refresh_fields(frm);
				}
			});
		}

		// TEST LOADING SCREEN
		if(frappe.session.user == 'Administrator'){
			frm.add_custom_button(__('Generate Data'), function() {
				// simulateProgress(frm.doc.monthly_psof);
				generate_bills(frm)
				// cur_frm.call('test', (r)=>{
				// 	console.log(r)
				// }).then((e) => {
				// 	console.log(e.message)
				// })
				// frm.save();
			});
		}
		// TEST LOADING SCREEN
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

function generate_bills(frm){
	frappe.call({
					method: 'subscription.subscription.doctype.monthly_psof_billing.monthly_psof_billing.generate_loading_bill',
					args: {
						monthlypsof: frm.doc.monthly_psof,
						docname: frm.doc.name
					},
					freeze: true,
					callback: (r) => {
						var progress = 0
						r.message.forEach((bill)=>{
							frappe.call({
								method: 'subscription.subscription.doctype.monthly_psof_billing.monthly_psof_billing.g_bill',
								args: {
									bill: bill
								},
								freeze: true,
								callback: (b) => {
									var bill_data = b.message
									var row = frappe.model.add_child(frm.doc, 'billings', 'billings');
									row.customer_name = bill_data.customer
									frm.refresh_fields('billings')

									progress++
									frappe.show_progress('Generating Bill', progress, r.message.length, 'Please wait');
									console.log(bill_data)
									if(progress == r.message.length){
										frappe.show_alert({
											message:__('Generation finished'),
											indicator:'green'
										}, 10);
									}
								},
								error: (b) => {
									console.log(b)
								}
							})

							// frm.call('test', (r)=>{
							// 	console.log(r)
							// }).then((e) => {
							// 	console.log(e.message)
							// 	progress++
							// 	frappe.show_progress('Generating Bill', progress, r.message.length, 'Please wait');
							// 	// console.log(bill_data)
							// 	if(progress == r.message.length){
							// 		frappe.show_alert({
							// 			message:__('Generation finished'),
							// 			indicator:'green'
							// 		}, 10);
							// 	}
							// })

						})

					},
					error: (r) => {
						// on error
						console.log('error')
					}

				})
}

