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
    } else {
        frm.disable_save();
        program == undefined ? frappe.msgprint("Remove Empty Program") : frappe.throw(`${program} already in the Programs Table`);
    }
}
// function to get difference caused by decimal places
function diff(period, cost) {
    return flt(cost - (flt((cost  / period), 2) * period), 2)
}
// to check if computation is over or under
function cond(dif) {
    return dif >= 0 ? "OVER" : "UNDER"
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

const evaluateAllocationCond = doc => {
    doc.decoder_condition = cond(doc.decoder_difference)
    doc.card_condition = cond(doc.card_difference)
    doc.promo_condition = cond(doc.promo_difference)
    doc.freight_condition = cond(doc.freight_difference)
}

const computeAllocationDiff = doc => {
    doc.decoder_difference = diff(doc.decoder_max_bill_div, doc.decoder_calculation);
    doc.card_difference = diff(doc.card_max_bill_divisor, doc.card_calculation);
    doc.promo_difference = diff(doc.promo_max_bill_divisor, doc.promo_calculation);
    doc.freight_difference = diff(doc.freight_max_bill_divisor, doc.freight_calculation);
}

const computeAllocationTotal = (doc, from_bv=false) => {
    if (from_bv) {
        return flt(frappe.utils.sum([doc.decoder_rate, doc.card_rate, doc.promo_rate, doc.freight_rate]), 2)
    } else {
        doc.total = flt(
            frappe.utils.sum(
                [
                    doc.decoder_allocation_active === 1 ? flt(doc.decoder_rate, 2): 0,
                    doc.card_allocation_active === 1 ? flt(doc.card_rate, 2): 0,
                    doc.promo_allocation_active === 1 ? flt(doc.promo_rate, 2): 0,
                    doc.freight_allocation_active === 1 ? flt(doc.freight_rate, 2): 0,
                ]
            )
        )
    }
}

const computeTax = (taxType, doc) => {
    if (taxType === "Vat Inclusive") {
        doc.less_of_vat_original = (doc.subscription_fee -  doc.total) / 1.12;
        doc.vat_amount = roundAccurately(roundAccurately(doc.less_of_vat_original * 0.12, 3), 2) // VAT
    } else {
        doc.less_of_vat_original = (doc.subscription_fee -  doc.total)
        doc.vat_amount = 0
    }
    doc.grand_total = doc.less_of_vat_original + doc.total + doc.vat_amount;
    doc.difference_grand_total = doc.subscription_fee - doc.grand_total;
    doc.subscription_rate = doc.less_of_vat_original + doc.difference_grand_total;
    doc.no_of_subs = Math.trunc(doc.less_of_vat_original / doc.rate_per_sub); // SUBS
}
// Update Amounts
var update_amounts = function(frm, cdt, cdn) {
    let {tax_category} = frm.doc
    let cur_doc = locals[cdt][cdn];
    computeAllocationTotal(cur_doc)
    computeAllocationDiff(cur_doc)
    evaluateAllocationCond(cur_doc)
    computeTax(tax_category, cur_doc)
};

const checkContract = (contractNumber, isNew) => {
    frappe.db.get_doc("Subscription Contract", contractNumber)
        .then(contract => {
            const {tax_category, is_supersede: su, contract_number} = contract
            if (isNew === 1) {
                if (su) {
                    return tax_category === checkContract(contract_number, 0)
                }
            } else if (isNew === 0){
                return tax_category
            }
        })
}

const reCompute = frm => {
    if (!checkContract(frm.doc.subscription_contract, 1)) {
        $.each(frm.doc.programs, (ind, row) => {
            update_amounts(frm,row.doctype,row.name)
        })
        frm.dirty()
        frm.set_value('has_recomputed', 1)
        frm.save()
    }
    frm.refresh_fields()
}

const reComputeBillView = (frm, row) => {
    let total_allocation = computeAllocationTotal(row, true)
    const {tax_category} = frm.doc
    let less_vat = 0
    let diff_gt = 0
    let gt = 0
    if (tax_category === "Vat Inclusive") {
        less_vat = (row.subscription_fee - total_allocation) / 1.12
        row.vat_amount = flt(total_allocation * 0.12, 2)
    } else {
        less_vat = (row.subscription_fee -  total_allocation)
        row.vat_amount = 0
    }
    row.vat_ird = computeBillTax(tax_category, row.decoder_rate)
    row.vat_card = computeBillTax(tax_category, row.card_rate)
    row.vat_promo = computeBillTax(tax_category, row.promo_rate)
    row.vat_freight = computeBillTax(tax_category, row.freight_rate)
    gt = less_vat + computeAllocationTotal(row, true) + row.vat_amount
    diff_gt = row.subscription_fee - gt
    row.subscription_rate = less_vat + diff_gt
    frm.refresh_fields('bill_view')
}

const computeBillTax = (taxtype, allocation_amount) =>
    taxtype === "Vat Inclusive" ? flt(allocation_amount - flt(allocation_amount / 1.12)) : 0;


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

    onload: (frm) => {
        frm.set_query("subscription_contract", () => {
            return {
                query: "subscription.subscription.doctype.psof.psof.get_contracts",
                filters: {
                    docstatus: 1
                }
            }
        })
        if (frm.doc.subscription_contract && !frm.doc.has_recomputed) {
            reCompute(frm)
        }
        frm.doc.contract_currency = 'USD'
        frm.doc.subscription_program = ""
        frm.toggle_display(['generate'], false)
        frm.toggle_display(['view_bill'], false)
        cur_frm.clear_table("bill_view");
        update_program(frm);
        cur_frm.refresh_fields(frm);
    },

    onload_post_render: (frm) => {
        if (frm.doc.bill_until_renewed) {
            frm.$wrapper.find("[data-fieldname='end_date']").hide()
            frm.$wrapper.find(".data-row>[data-fieldname='subscription_program']").addClass("col-xs-4")
        } else {
            frm.$wrapper.find("[data-fieldname='bill_view']>div.grid-footer").hide()
        }
    },

    tax_category: frm => reCompute(frm),

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
        cur_frm.call('view_new_bill', function(r){})
            .then((r) => {
                $.each(frm.doc.bill_view, (i, r) => {
                    reComputeBillView(frm, locals[r.doctype][r.name])
                })
            })
        cur_frm.refresh_fields(frm);
    }
});

frappe.ui.form.on("PSOF Program Bill View", {
    subscription_fee: (frm,cdt, cdn) => reComputeBillView(frm, locals[cdt][cdn]),
    subscription_rate: (frm,cdt, cdn) => reComputeBillView(frm, locals[cdt][cdn]),
    decoder_rate: (frm,cdt, cdn) => reComputeBillView(frm, locals[cdt][cdn]),
    card_rate: (frm,cdt, cdn) => reComputeBillView(frm, locals[cdt][cdn]),
    promo_rate: (frm,cdt, cdn) => reComputeBillView(frm, locals[cdt][cdn]),
    freight_rate: (frm,cdt, cdn) => reComputeBillView(frm, locals[cdt][cdn]),
    form_render: (frm,cdt, cdn) => reComputeBillView(frm, locals[cdt][cdn]),
    bill_view_add: (frm, cdt, cdn) => {
        const row = locals[cdt][cdn]
        if (frm.doc.bill_until_renewed && frm.doc.bill_view.length >= 1) {
            $.each(frm.doc.bill_view, (i, r) => {
                if (r.idx + 1 == row.idx) {
                    row.active = r.active
                    row.card_rate = r.card_rate
                    row.decoder_rate = r.decoder_rate
                    row.freight_rate = r.freight_rate
                    row.no_of_subs = r.no_of_subs
                    row.promo_rate = r.promo_rate
                    row.subscription_fee = r.subscription_fee
                    row.subscription_program = r.subscription_program
                    row.subscription_rate = r.subscription_rate
                    row.vat_amount = r.vat_amount
                    row.vat_card = r.vat_card
                    row.vat_freight = r.vat_freight
                    row.vat_ird = r.vat_ird
                    row.vat_promo = r.vat_promo
                    row.date_from = frappe.datetime.add_months(r.date_from, 1)
                    row.date_to = frappe.datetime.add_months(r.date_to, 1)
                    console.log(r, row)
                }
            })

            frm.refresh_field("bill_view")
        }
    }
});


frappe.ui.form.on("PSOF Program", {
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
        const row = locals[cdt][cdn];
        let date = new Date(frm.doc.start_date);
        let firstDay = frappe.format(new Date(date.getFullYear(), date.getMonth(), 1), {fieldType: 'Date'});
        row.subscription_contract = frm.doc.subscription_contract;
        row.subscription_currency = frm.doc.contract_currency;
        row.customer_name = frm.doc.customer_name;

        frappe.db.get_value('PSOF', row.parent, ['expiry_date', 'customer_name']).then(r => {
            let {customer_name} = r.message;
            row.start_date = firstDay;
            row.end_date = frappe.format(new Date(date.getFullYear() + 1, date.getMonth(), 0), {fieldType: 'Date'});
            row.customer_name = customer_name
            row.program_status = "<b>Status: Inactive</b> "

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

