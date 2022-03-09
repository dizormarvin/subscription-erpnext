// Copyright (c) 2020, ossphin and contributors
// For license information, please see license.txt
{% include 'erpnext/selling/sales_common.js' %}

frappe.ui.form.on('Subscription Contract',  {
//	 refresh: function(frm) {
//
//	 },
	setup: (frm) => {
		frm.doc.currency = 'USD'
	},
	
	refresh: function(frm) {
	if(frm.doc.docstatus === 1){
		frm.add_custom_button(__('Billing Request'), function(){
		        frappe.msgprint(frm.doc.email);
			    }, __("Create"));

		frm.add_custom_button(__('Contract Renewal'), function(){
			cur_frm.call('renew_contract','',function(r){}
				);
                            }, __("Create"));

	}
	if(frm.doc.docstatus === 0) {
                frm.add_custom_button(__('Get Items'), function(){
                        cur_frm.call('get_items','',function(r){}
				);
                            }, __("Utilities"));
		}
	}
});

// Update Amounts
var update_amounts = function(frm, cdt, cdn) {
	var cur_doc = locals[cdt][cdn];
	var total = 0;
	total = total + cur_doc.subscription_fee;

	if (cur_doc.decoder_allocation_active === 1) {
		total = total - cur_doc.decoder_rate;
		} 

	if (cur_doc.card_allocation_active) { 
                total = total - cur_doc.card_rate;
                } 

        if (cur_doc.promo_allocation_active) { 
                total = total - cur_doc.promo_rate;
                } 

        if (cur_doc.freight_allocation_active) { 
                total = total - cur_doc.freight_rate;
                } 

	cur_doc.subscription_rate = total;
	cur_doc.no_of_subs = Math.round((cur_doc.subscription_rate/1.12)/cur_doc.rate_per_sub);
        frm.refresh_fields();
}

//Items  Functions
frappe.ui.form.on("Subscription Contract Items", {
//Active Checkbox
	decoder_allocation_active: function(frm, cdt, cdn) {
		var cur_doc = locals[cdt][cdn];
		if (cur_doc.decoder_allocation_active === 1){}
		else{
			cur_doc.decoder_max_bill_count = 0;
		} 

		update_amounts(frm, cdt, cdn);
		frm.refresh_fields();
	},
        promo_allocation_active: function(frm, cdt, cdn) {
                var cur_doc = locals[cdt][cdn];
                if (cur_doc.promo_allocation_active === 1){}
                else{
                        cur_doc.promo_max_bill_count = 0;
                } 

                update_amounts(frm, cdt, cdn);
                frm.refresh_fields();
        },
        freight_allocation_active: function(frm, cdt, cdn) {
                var cur_doc = locals[cdt][cdn];
                if (cur_doc.freight_allocation_active === 1){}
                else{
                        cur_doc.freight_max_bill_count = 0;
                } 

                update_amounts(frm, cdt, cdn);
                frm.refresh_fields();
        },
        card_allocation_active: function(frm, cdt, cdn) {
                var cur_doc = locals[cdt][cdn];
                if (cur_doc.card_allocation_active === 1){}
                else{
                        cur_doc.card_max_bill_count = 0;
                } 

                update_amounts(frm, cdt, cdn);
                frm.refresh_fields();
        },

//Rates
	subscription_fee: function(frm, cdt, cdn) {
        	var cur_doc = locals[cdt][cdn];
        	update_amounts(frm, cdt, cdn);
	},
	decoder_rate: function(frm, cdt, cdn) {
        	var cur_doc = locals[cdt][cdn];
		update_amounts(frm, cdt, cdn);
	},
	promo_rate: function(frm, cdt, cdn) {
        	var cur_doc = locals[cdt][cdn];
		update_amounts(frm, cdt, cdn);
	},
	freight_rate: function(frm, cdt, cdn) {
        	var cur_doc = locals[cdt][cdn];
   		update_amounts(frm, cdt, cdn);
	},
	card_rate: function(frm, cdt, cdn) {
        	var cur_doc = locals[cdt][cdn];
   		update_amounts(frm, cdt, cdn);
	},

/*  Decoder */
	decoder_calculation: function(frm, cdt, cdn) {
        	var cur_doc = locals[cdt][cdn];
		cur_doc.decoder_rate = cur_doc.decoder_calculation/cur_doc.decoder_max_bill_divisor;
   		update_amounts(frm, cdt, cdn);
	},

	decoder_max_bill_div: function(frm, cdt, cdn) {
        	var cur_doc = locals[cdt][cdn];
   		cur_doc.decoder_rate = cur_doc.decoder_calculation/cur_doc.decoder_max_bill_div;
		update_amounts(frm, cdt, cdn);
        	frm.refresh_fields();
	},

/*  Card */
	card_calculation: function(frm, cdt, cdn) {
        	var cur_doc = locals[cdt][cdn];
   		cur_doc.card_rate = cur_doc.card_calculation/cur_doc.card_max_bill_divisor;
		update_amounts(frm, cdt, cdn);
        	frm.refresh_fields();
	},

	card_max_bill_divisor: function(frm, cdt, cdn) {
        	var cur_doc = locals[cdt][cdn];
   		cur_doc.card_rate = cur_doc.card_calculation/cur_doc.card_max_bill_divisor;
        	update_amounts(frm, cdt, cdn);
		frm.refresh_fields();
	},

/*  Promo */
	promo_calculation: function(frm, cdt, cdn) {
        	var cur_doc = locals[cdt][cdn];
   		cur_doc.promo_rate = cur_doc.promo_calculation/cur_doc.promo_max_bill_divisor;
        	update_amounts(frm, cdt, cdn);
		frm.refresh_fields();
	},

	promo_max_bill_divisor: function(frm, cdt, cdn) {
        	var cur_doc = locals[cdt][cdn];
   		cur_doc.promo_rate = cur_doc.promo_calculation/cur_doc.promo_max_bill_divisor;
        	update_amounts(frm, cdt, cdn);
		frm.refresh_fields();
	},
/* Freight */
	freight_calculation: function(frm, cdt, cdn) {
        	var cur_doc = locals[cdt][cdn];
   		cur_doc.freight_rate = cur_doc.freight_calculation/cur_doc.freight_max_bill_divisor;
        	update_amounts(frm, cdt, cdn);
		frm.refresh_fields();
	},

	freight_max_bill_divisor: function(frm, cdt, cdn) {
        	var cur_doc = locals[cdt][cdn];
   		cur_doc.freight_rate = cur_doc.freight_calculation/cur_doc.freight_max_bill_divisor;
		update_amounts(frm, cdt, cdn);
        	frm.refresh_fields();
	},
});
