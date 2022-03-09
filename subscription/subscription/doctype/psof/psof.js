// Copyright (c) 2020, ossphin and contributors
// For license information, please see license.txt

// PSOF

// **** CUSTOM FUNCTIONS ****
const roundAccurately = (num, decimal) => Number(Math.round(num + "e" + decimal) + "e-" + decimal)

async function validatePrograms(programList, row, frm) {
    const checker = new Set(programList);
    const {
        subscription_program: program,
        subscription_contract: contract,
        start_date: s_date,
        end_date: e_date,
        customer_name: customer,
        parent: psof
    } = row;
    if ((checker.size === programList.length) || programList.length <= 1) {
        frm.enable_save();
        // @TODO
        // await frappe.db.exist({
        //     doctype: 'PSOF Program'
        // })
    } else {
        frm.disable_save();
        program == undefined ? frappe.msgprint("Remove Empty Program") : frappe.throw(`${program} already in the Programs Table`);
    }
}

// function to get difference caused by decimal places
function diff(period, cost) {
    let allocation = roundAccurately((cost  / period), 2)
    return roundAccurately(cost - (allocation * period), 2)
}


// to check if computation is over or under
function cond(dif) {
    if(dif >= 0) {
        return "OVER"
    }
    return "UNDER"
}

var update_program = function(frm){
    frm.set_query ("subscription_program", function() {
        return {
            "query": "subscription.subscription.doctype.psof.psof.get_programs",
            "filters": {
                "dname": frm.docname
            }
        };
    });
}

const truncateByDecimalPlace = (value, numDecimalPlaces) =>
    Math.trunc(value * Math.pow(10, numDecimalPlaces)) / Math.pow(10, numDecimalPlaces)

// Update Amounts
var update_amounts = function(frm, cdt, cdn) {
    const cur_doc = locals[cdt][cdn];
    let total = 0.0;

    if(cur_doc.decoder_allocation_active === 1) {
        total += roundAccurately(cur_doc.decoder_rate, 2);
    }

    if(cur_doc.card_allocation_active === 1) {
        total += roundAccurately(cur_doc.card_rate, 2);
    }

    if(cur_doc.promo_allocation_active === 1) {
        total += roundAccurately(cur_doc.promo_rate, 2);
    }

    if(cur_doc.freight_allocation_active === 1) {
        total += roundAccurately(cur_doc.freight_rate, 2);
    }

    //Difference due to decimal places
    cur_doc.decoder_difference = diff(cur_doc.decoder_max_bill_div, cur_doc.decoder_calculation);
    cur_doc.card_difference = diff(cur_doc.card_max_bill_divisor, cur_doc.card_calculation);
    cur_doc.promo_difference = diff(cur_doc.promo_max_bill_divisor, cur_doc.promo_calculation);
    cur_doc.freight_difference = diff(cur_doc.freight_max_bill_divisor, cur_doc.freight_calculation);

    //Conditions
    cur_doc.decoder_condition = cond(cur_doc.decoder_difference)
    cur_doc.card_condition = cond(cur_doc.card_difference)
    cur_doc.promo_condition = cond(cur_doc.promo_difference)
    cur_doc.freight_condition = cond(cur_doc.freight_difference)

    // RATES COMPUTATION
    cur_doc.total = total;
    cur_doc.less_of_vat_original = (cur_doc.subscription_fee -  cur_doc.total) / 1.12;
    cur_doc.vat_amount = roundAccurately(roundAccurately(cur_doc.less_of_vat_original * 0.12, 3), 2) // VAT
    cur_doc.grand_total =  cur_doc.less_of_vat_original + cur_doc.total + cur_doc.vat_amount;
    cur_doc.no_of_subs = Math.trunc(cur_doc.less_of_vat_original / cur_doc.rate_per_sub); // SUBS
    cur_doc.difference_grand_total = cur_doc.subscription_fee - cur_doc.grand_total;
    cur_doc.subscription_rate = cur_doc.less_of_vat_original + cur_doc.difference_grand_total; // MSF Less of VAT
    frm.refresh_fields();

};

// *************************

frappe.ui.form.on('PSOF', {

    validate: function(frm, cdt, cdn) {
        const cur_doc = locals[cdt][cdn];
        const program_list = [];

        if(cur_doc.programs) {
            const subs = cur_doc.programs
                .map(program => program.subscription_fee)
                .reduce((total, value) => total + value, 0);
            frm.set_value('monthly_subs_fee_total', subs);
            
            for (let i = 0; i < cur_doc.programs.length; i++) {
                program_list.push(cur_doc.programs[i].subscription_program)
            };
            let checker = new Set(program_list)
            if(program_list.length !== checker.size) {
                frappe.throw(__('Duplicate Entries Found\nCheck programs and remove duplicates'));
                cur_frm.refresh_fields(frm);
            }
        }
    },

    onload: (frm, cdt, cdn) => {
        const cur_doc = locals[cdt][cdn]
        let today = new Date()
        frm.doc.contract_currency = 'USD'
        frm.doc.subscription_program = ""
        frm.toggle_display(['generate'], false)
        frm.toggle_display(['view_bill'], false)
        cur_frm.clear_table("bill_view");
        update_program(frm);
        cur_frm.refresh_fields(frm);
    },

    programs: function(frm) {
        update_program(frm);
        cur_frm.refresh_fields(frm);
    },

    before_save: function(frm) {
        // cur_frm.call('create_bill', function (r){});
        cur_frm.call('update_bills', function (r){});
        cur_frm.refresh_fields();
    },

    after_save: function (frm) {
        cur_frm.clear_table("bill_view");
        cur_frm.refresh_fields(frm)
    },

    subscription_program: function(frm, cdt, cdn) {
        const cur_doc = locals[cdt][cdn];
        const program_list = [];

        if(cur_doc.subscription_program) {
            frappe.db.get_value('PSOF Program Bill', {
                    "subscription_program": cur_doc.subscription_program,
                    "psof": cur_doc.name },
                ['subscription_program', 'psof', 'parent'])
                .then(r => {
                    let program = r.message
                    if($.isEmptyObject(program)) {
                        frm.toggle_display(['generate'], true )
                        frm.toggle_display(['view_bill'], false )
                    } else {
                        frm.toggle_display(['generate'], false)
                        frm.toggle_display(['view_bill'], true)
                    }
                    cur_frm.refresh_fields(frm)
                })

        } else {
            frm.toggle_display(['generate'], false )
            frm.toggle_display(['view_bill'], false )
        }


        if(cur_doc.programs) {
            for (let i = 0; i < cur_doc.programs.length; i++) {
                program_list.push(cur_doc.programs[i].subscription_program)
            };
            let p = program_list.includes(cur_doc.subscription_program)

            if(!p) {
                if (cur_doc.subscription_program === undefined ) {}
                else {
                    frappe.throw(__(cur_doc.subscription_program + ' not in the list of programs'))
                }
            }
        } else {
            frappe.throw(__("Add a program first"))
        }
        cur_frm.clear_table("bill_view");
        cur_frm.refresh_fields(frm);
    },

    generate(frm,cdt,cdn) {
        const cur_doc = locals[cdt][cdn];
        const programs = frm.doc.programs
        const program_list = [];
        frm.toggle_display(['generate'], false )
        frm.toggle_display(['view_bill'], true )

        if(cur_doc.programs) {
            for (let i = 0; i < cur_doc.programs.length; i++) {
                program_list.push(cur_doc.programs[i].subscription_program)
            };
            if(program_list.includes(cur_doc.subscription_program)) {
                for (let program of programs) {
                    if (frm.doc.subscription_program === program.subscription_program) {
                        program.bill_generated = 1
                    }
                }
                if (cur_doc.subscription_program === undefined ) {}
                // else {
                //     frappe.throw(__(cur_doc.subscription_program + ' not in the list of programs'))
                // }
            }
        } else {
            frappe.throw(__("Add a program first"))
        }

        cur_frm.clear_table("bill_view");
        cur_frm.call('create_bill', function(r){});
        cur_frm.refresh_fields(frm);
    },

    view_bill: function (frm) {
        cur_frm.clear_table("bill_view");
        cur_frm.call('view_new_bill', function(r){});
        cur_frm.refresh_fields(frm);

    }
});
frappe.ui.form.on("PSOF Program Bill View", {

    subscription_fee: function (frm,cdt, cdn) {
        var cur_doc = locals[cdt][cdn]
        var total = cur_doc.subscription_fee

        if(cur_doc.decoder_rate){
            total = total - cur_doc.decoder_rate
        }
        if(cur_doc.card_rate){
            total = total - cur_doc.card_rate
        }
        if(cur_doc.promo_rate){
            total = total - cur_doc.promo_rate
        }
        if(cur_doc.freigh_rate){
            total = total - cur_doc.freight_rate
        }
        cur_doc.subscription_rate = truncateByDecimalPlace((total / 1.12), 2)
        cur_frm.refresh_fields(frm.doc.bill_view);
    }
});
frappe.ui.form.on("PSOF Program", {
        start_date: (frm, cdt, cdn) => {
            let row = locals[cdt][cdn]
            let date = frappe.format(new Date(row.start_date), {fieldType: 'Date'})
            row.end_date = frappe.format(new Date(date.getFullYear() + 1, date.getMonth(), 0), {fieldType: 'Date'})
            frm.refresh_field('programs')
        },

        before_programs_remove: (frm, cdt, cdn) => {
            var cur_doc = locals[cdt][cdn];
            frappe.confirm(`Are you sure you want to delete ${cur_doc.subscription_program}?`,
                () => {
                frappe.call({
                    method: "subscription.subscription.doctype.psof.psof.delete_generated",
                    args: {'parent': cur_doc.name, 'program': cur_doc.subscription_program, 'psof': frm.doc.name },
                    callback: r => {
                        frappe.msgprint(r);
                        frm.save();
                        frm.refresh();
                    }
                })
                }, () => frm.reload_doc()
            );

            frappe.db.get_value('Program Activation Item', {
                "program": cur_doc.subscription_program, "psof_program": cur_doc.name, "psof": cur_doc.parent
                }, ['program', 'psof_program', 'psof', 'parent'])
            .then(r => {
                let program = r.message
                if (program.program === cur_doc.subscription_program && program.psof_program === cur_doc.name && program.psof === cur_doc.parent) {
                    frm.disable_save()
                    frappe.msgprint({
                        title: __(`${cur_doc.subscription_program} cannot be removed`),
                        message: __(`Program is linked with Activation Module ${program.parent}, click Undo or reload doccument`),
                        primary_action:{
                            'label': 'Undo',
                            action(values) {
                                frm.enable_save();
                                frm.reload_doc();
                            }
                        },
                        indicator: 'red'
                    });
                }
            })

        frm.refresh_fields();
    },

    programs_remove: (frm, cdt, cdn) => {
            let row = locals[cdt][cdn];
            frm.enable_save();
            cur_frm.clear_table("bill_view");
            cur_frm.refresh_fields(frm);
},

    subscription_program: (frm, cdt, cdn) => {
    let row = locals[cdt][cdn]
    const programList = frm.doc.programs.map(val => val['subscription_program']);
    validatePrograms(programList, row, frm)
},

    programs_add: (frm, cdt, cdn) => {
    const cur_doc = locals[cdt][cdn];
    let date = new Date();
    let firstDay = frappe.format(new Date(date.getFullYear(), date.getMonth()), {fieldType: 'Date'});
    cur_doc.subscription_contract = frm.doc.subscription_contract;
    cur_doc.subscription_currency = frm.doc.contract_currency;
    cur_doc.customer_name = frm.doc.customer_name;

    frappe.db.get_value('PSOF', cur_doc.parent, ['expiry_date', 'customer_name']).then(r => {
        let values = r.message;
        cur_doc.start_date = firstDay;
        cur_doc.end_date = frappe.format(new Date(date.getFullYear() + 1, date.getMonth(), 0), {fieldType: 'Date'});
        cur_doc.customer_name = values.customer_name
        cur_doc.program_status = "<b>Status:</b> "

    });
    frm.refresh_fields();
},

    //Active Checkbox
    decoder_allocation_active: function(frm, cdt, cdn) {
    if(cur_doc.decoder_allocation_active === 1) {
    } else {
        cur_doc.decoder_max_bill_count = 0;
    }
    update_amounts(frm, cdt, cdn);
    frm.refresh_fields ();
},

promo_allocation_active: function (frm, cdt, cdn) {
    var cur_doc = locals[cdt][cdn];
    if(cur_doc.promo_allocation_active === 1) {
    } else {
        cur_doc.promo_max_bill_count = 0;
    }
    update_amounts(frm, cdt, cdn);
    frm.refresh_fields();
},

freight_allocation_active: function (frm, cdt, cdn) {
    var cur_doc = locals[cdt][cdn];
    if(cur_doc.freight_allocation_active === 1) {
    } else {
        cur_doc.freight_max_bill_count = 0;
    }
    update_amounts(frm, cdt, cdn);
    frm.refresh_fields();
},

card_allocation_active: function (frm, cdt, cdn) {
    var cur_doc = locals[cdt][cdn];
    if(cur_doc.card_allocation_active === 1) {
    } else {
        cur_doc.card_max_bill_count = 0;
    }
    update_amounts(frm, cdt, cdn);
    frm.refresh_fields();
},

renewal: function(frm, cdt, cdn) {
    const cur_doc = locals[cdt][cdn];
    if(cur_doc.renewal === 1) {
        cur_doc.active = 1
        cur_doc.program_status = "<b>Status:</b> Activated by Renewal"
    } else if(cur_doc.renewal === 0) {
        cur_doc.active = 0
        cur_doc.program_status = "<b>Status:</b> "
    }
    update_amounts(frm, cdt, cdn);
    frm.refresh_fields();
},

//Rates
subscription_fee: function(frm, cdt, cdn) {
    update_amounts(frm, cdt, cdn);
},
decoder_rate: function(frm, cdt, cdn) {
    update_amounts(frm, cdt, cdn);
},
promo_rate: function(frm, cdt, cdn) {
    update_amounts(frm, cdt, cdn);
},
freight_rate: function(frm, cdt, cdn) {
    update_amounts(frm, cdt, cdn);
},
card_rate: function(frm, cdt, cdn) {
    update_amounts(frm, cdt, cdn);
},
decoder_difference: function(frm, cdt, cdn) {
    update_amounts(frm, cdt, cdn);
},

/*  Decoder */
decoder_calculation: function(frm, cdt, cdn) {
    var cur_doc = locals[cdt][cdn];
    cur_doc.decoder_rate = cur_doc.decoder_calculation / cur_doc.decoder_max_bill_div;
    cur_doc.decoder_rate = truncateByDecimalPlace(cur_doc.decoder_rate, 2)
    update_amounts(frm, cdt, cdn);
    frm.refresh_fields();
},

decoder_max_bill_div: function (frm, cdt, cdn) {
    var cur_doc = locals[cdt][cdn];
    cur_doc.decoder_rate = cur_doc.decoder_calculation / cur_doc.decoder_max_bill_div;
    update_amounts(frm, cdt, cdn);
    frm.refresh_fields();
},

/*  Card */
card_calculation: function(frm, cdt, cdn) {
    var cur_doc = locals[cdt][cdn];
    cur_doc.card_rate = cur_doc.card_calculation / cur_doc.card_max_bill_divisor;
    cur_doc.card_rate = truncateByDecimalPlace(cur_doc.card_rate, 2)
    update_amounts(frm, cdt, cdn);
    frm.refresh_fields();
},

card_max_bill_divisor: function(frm, cdt, cdn) {
    var cur_doc = locals[cdt][cdn];
    cur_doc.card_rate = cur_doc.card_calculation / cur_doc.card_max_bill_divisor;
    update_amounts(frm, cdt, cdn);
    frm.refresh_fields();
},

/*  Promo */
promo_calculation: function(frm, cdt, cdn) {
    var cur_doc = locals[cdt][cdn];
    cur_doc.promo_rate = cur_doc.promo_calculation / cur_doc.promo_max_bill_divisor;
    cur_doc.promo_rate = truncateByDecimalPlace(cur_doc.promo_rate, 2)
    update_amounts(frm, cdt, cdn);
    frm.refresh_fields();
},

promo_max_bill_divisor: function(frm, cdt, cdn) {
    var cur_doc = locals[cdt][cdn];
    cur_doc.promo_rate = cur_doc.promo_calculation / cur_doc.promo_max_bill_divisor;
    update_amounts(frm, cdt, cdn);
    frm.refresh_fields();
},
/* Freight */
freight_calculation: function(frm, cdt, cdn) {
    var cur_doc = locals[cdt][cdn];
    cur_doc.freight_rate = cur_doc.freight_calculation / cur_doc.freight_max_bill_divisor;
    cur_doc.freight_rate = truncateByDecimalPlace(cur_doc.freight_rate, 2)
    update_amounts(frm, cdt, cdn);
    frm.refresh_fields();
},

freight_max_bill_divisor: function(frm, cdt, cdn) {
    var cur_doc = locals[cdt][cdn];
    cur_doc.freight_rate = cur_doc.freight_calculation / cur_doc.freight_max_bill_divisor;
    update_amounts(frm, cdt, cdn);
    frm.refresh_fields();
}
});
