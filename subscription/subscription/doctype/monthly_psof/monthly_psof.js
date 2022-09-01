// Copyright (c) 2021, ossphin and contributors
// For license information, please see license.txt

const rateTotal = (rateName) => frappe.utils.sum(frm.doc.bills.map(e => e[rateName]))

function updateTotal(frm) {
    if (!frm.is_new() && frm.doc.bills.length > 0) {
        frm.set_value('total_subs_fee', rateTotal("subscription_fee"))
        frm.set_value('total_subs_rate', rateTotal("subscription_rate"))
        frm.set_value('total_decoder_rate', rateTotal("decoder_rate"))
        frm.set_value('total_promo_rate', rateTotal("promo_rate"))
        frm.set_value('total_card_rate', rateTotal("card_rate"))
        frm.set_value('total_freight_rate', rateTotal("freight_rate"))
        frm.refresh_fields();
    }
}

frappe.ui.form.on('Monthly PSOF', {
    refresh: (frm) => {
        if (!frm.is_new() && !frm.doc.is_generated) {
            frm.trigger("get_items_btn");
        } else if (frm.doc.docstatus === 1 && !frm.doc.bills_created) {
            frm.trigger("generate_bills_btn")
        } else {
            frm.trigger("clear_custom_buttons")
        }
    },

    generate_bills_btn: (frm) => {
        frm.add_custom_button(__("Generate Bills"), () => {
            frm.call('generate_monthly_bills')
            frm.refresh_fields();
        });
    },

    get_items_btn: (frm) => {
        frm.add_custom_button(__("Get Items"), () => {
            frm.call('get_items')
            frm.refresh_fields();
        });
    },

    setup: (frm) => frm.set_value('currency', "USD"),
    validate: (frm) => updateTotal(frm),
});

frappe.ui.form.on('Monthly PSOF Program Bill', {
    bills_add: (frm) => updateTotal(frm),
    bills_remove: (frm) => updateTotal(frm),
})
