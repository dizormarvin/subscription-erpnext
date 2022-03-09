// Copyright (c) 2021, ossphin and contributors
// For license information, please see license.txt

function updateTotal(frm) {
        let subsFee = 0
        let subsRate = 0
        let dRate = 0
        let pRate = 0
        let cRate = 0
        let fRate = 0
	    frm.doc.bills.forEach(e => {
            subsFee += Number.parseFloat(e.subscription_fee)
            subsRate += Number.parseFloat(e.subscription_rate)
            dRate += Number.parseFloat(e.decoder_rate)
            pRate += Number.parseFloat(e.promo_rate)
            cRate += Number.parseFloat(e.card_rate)
            fRate += Number.parseFloat(e.freight_rate)
        })
        frm.set_value('total_subs_fee', subsFee)
        frm.set_value('total_subs_rate', subsRate)
        frm.set_value('total_decoder_rate', dRate)
        frm.set_value('total_promo_rate', pRate)
        frm.set_value('total_card_rate', cRate)
        frm.set_value('total_freight_rate', fRate)
}

frappe.ui.form.on('Monthly PSOF', {
	refresh: function(frm) {
		frm.add_custom_button(__("Get Items"), function() {
            cur_frm.call('get_items', (r) => {
        })
            cur_frm.refresh_fields(frm);
		});
	},
    setup: (frm) => {
       frm.set_value('currency', "USD")
    },

    validate: (frm) => updateTotal(frm),

	get_items: function(frm){
        cur_frm.call('get_items', (r) => {})
        setTimeout(()=> {
            updateTotal(frm)
        }, 1300)
    },
});

frappe.ui.form.on('Monthly PSOF Program Bill', {
    bills_add: (frm) => updateTotal(frm),
    bills_remove: (frm) => updateTotal(frm),
})
