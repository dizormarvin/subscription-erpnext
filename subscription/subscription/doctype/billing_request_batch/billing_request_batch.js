// Copyright (c) 2020, ossphin and contributors
// For license information, please see license.txt

frappe.ui.form.on('Billing Request Batch', {
	// refresh: function(frm) {

	// }

	refresh: function(frm) {
	if(frm.doc.docstatus === 0){
		frm.add_custom_button(__('Generate Bills'), function(){
		        cur_frm.call('generate_bills','',function(r){});
			    }, __("Utilities"));
		}
	},
	
	onload: function(frm) {
	if(frm.doc.docstatus === 0){
		cur_frm.call('get_defaults','',function(r){}
			);
		frm.refresh_fields();
		}
	}
});
