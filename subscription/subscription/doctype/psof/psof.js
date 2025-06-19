// Copyright (c) 2020, ossphin and contributors
// For license information, please see license.txt

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
function diff(period, cost) {
    return flt(cost - (flt((cost / period), 2) * period), 2)
}
function cond(dif) {
    return dif >= 0 ? "OVER" : "UNDER"
}
const update_program = function (frm) {
    frm.set_query("subscription_program", function () {
        return {
            "query": "subscription.subscription.doctype.psof.psof.get_programs",
            "filters": {
                "dname": frm.docname
            }
        };
    });
}
const truncateByDecimalPlace = (value, numDecimalPlaces) => Math.trunc(value * Math.pow(10, numDecimalPlaces)) / Math.pow(10, numDecimalPlaces)
const evaluateAllocationCond = (doc) => {
    doc.decoder_condition = cond(doc.decoder_difference)
    doc.card_condition = cond(doc.card_difference)
    doc.promo_condition = cond(doc.promo_difference)
    doc.freight_condition = cond(doc.freight_difference)
}
const computeAllocationDiff = (doc) => {
    doc.decoder_difference = diff(doc.decoder_max_bill_div, doc.decoder_calculation);
    doc.card_difference = diff(doc.card_max_bill_divisor, doc.card_calculation);
    doc.promo_difference = diff(doc.promo_max_bill_divisor, doc.promo_calculation);
    doc.freight_difference = diff(doc.freight_max_bill_divisor, doc.freight_calculation);
}
const computeAllocationTotal = (doc, from_bv = false) => {
    if (from_bv) {
        return flt(frappe.utils.sum([doc.decoder_rate, doc.card_rate, doc.promo_rate, doc.freight_rate]), 2)
    } else {
        doc.total = flt(
            frappe.utils.sum(
                [
                    doc.decoder_allocation_active === 1 ? flt(doc.decoder_rate, 2) : 0,
                    doc.card_allocation_active === 1 ? flt(doc.card_rate, 2) : 0,
                    doc.promo_allocation_active === 1 ? flt(doc.promo_rate, 2) : 0,
                    doc.freight_allocation_active === 1 ? flt(doc.freight_rate, 2) : 0,
                ]
            )
        )
    }
}
const computeTax = (taxType, doc, flat_fee) => {
    if (flat_fee === "Yes") {
        doc.no_of_subs = doc.subs_display
        console.log(doc.no_of_subs)
        doc.subscription_rate = flt((flt(doc.no_of_subs * doc.rate_per_sub)) * 1.12)
    }
    if (taxType === "Vat Inclusive") {
        doc.less_of_vat_original = (doc.subscription_fee - doc.total) / 1.12;
        doc.vat_amount = roundAccurately(roundAccurately(doc.less_of_vat_original * 0.12, 3), 2) // VAT
    } else {
        doc.less_of_vat_original = (doc.subscription_fee - doc.total)
        doc.vat_amount = 0
    }
    doc.grand_total = doc.less_of_vat_original + doc.total + doc.vat_amount;
    doc.difference_grand_total = doc.subscription_fee - doc.grand_total;
    doc.subscription_rate = doc.less_of_vat_original + doc.difference_grand_total;

    // Decimal Check
    if (hasAllDecimalPlacesAsNine(doc.less_of_vat_original / doc.rate_per_sub)) {
        doc.no_of_subs = Math.trunc((doc.less_of_vat_original) / doc.rate_per_sub) + 1;
    } else {
        doc.no_of_subs = Math.trunc((doc.less_of_vat_original) / doc.rate_per_sub);
    }


    if (!frappe.utils.sum([doc.decoder_allocation_active, doc.card_allocation_active,
    doc.promo_allocation_active, doc.freight_allocation_active])) {
        doc.flat_subs = cint(doc.subscription_rate / doc.rate_per_sub)
    }
    doc.subs_display = flat_fee === "Yes" ? doc.no_of_subs : doc.flat_subs;
}

const update_amounts = (frm, cdt, cdn) => {
    let { tax_category, flat_fee } = frm.doc
    let cur_doc = locals[cdt][cdn];
    computeAllocationTotal(cur_doc)
    computeAllocationDiff(cur_doc)
    evaluateAllocationCond(cur_doc)
    computeTax(tax_category, cur_doc, flat_fee)
    console.log(frm)
    frm.refresh_fields();
};
const checkContract = (contractNumber, isNew) => {
    if (!contractNumber) {
        return
    }
    frappe.db.get_doc("Subscription Contract", contractNumber)
        .then(contract => {
            const { tax_category, is_supersede: su, contract_number } = contract
            if (isNew === 1) {
                if (su) {
                    return tax_category === checkContract(contract_number, 0)
                }
            } else if (isNew === 0) {
                return tax_category
            }
        })
}
const reCompute = (frm) => {
    if (!checkContract(frm.doc.subscription_contract, 1)) {
        $.each(frm.doc.programs, (ind, row) => {
            update_amounts(frm, row.doctype, row.name)
        })
        frm.dirty()
        frm.set_value('has_recomputed', 1)
        frm.save()
    }
    frm.refresh_fields()
}
const reComputeBillView = (frm, row) => {
    let total_allocation = computeAllocationTotal(row, true)
    if(row.subscription_fee <= total_allocation){
        frappe.msgprint("Subscription Fee must be higher than Total Allocation")
        return
    }
    const { tax_category } = frm.doc
    let less_vat = 0
    let diff_gt = 0
    let gt = 0
    if (tax_category === "Vat Inclusive") {
        less_vat = (row.subscription_fee - total_allocation) / 1.12
        row.vat_amount = flt(less_vat * 0.12, 2)
    } else {
        less_vat = (row.subscription_fee - total_allocation)
        row.vat_amount = 0
    }
    row.vat_ird = computeBillTax(tax_category, row.decoder_rate)
    row.vat_card = computeBillTax(tax_category, row.card_rate)
    row.vat_promo = computeBillTax(tax_category, row.promo_rate)
    row.vat_freight = computeBillTax(tax_category, row.freight_rate)
    gt = less_vat + computeAllocationTotal(row, true) + row.vat_amount
    diff_gt = gt - row.subscription_fee

    //ORIGINAL
    //row.subscription_rate = less_vat + diff_gt
    row.subscription_rate = less_vat - diff_gt

    // Marvin: Getting rate_per_sub for current generated/view bill
    const current_rate_per_sub = frm.doc.programs.find(item => item.subscription_program === frm.doc.subscription_program)?.rate_per_sub;
    console.log(current_rate_per_sub)
    let new_rate_per_sub = Math.trunc(row.subscription_rate / current_rate_per_sub)
    console.log('new rate per sub', new_rate_per_sub)
    // Decimal Check
    if (hasAllDecimalPlacesAsNine(row.subscription_rate / current_rate_per_sub)) {
        row.no_of_subs = Math.trunc(row.subscription_rate / current_rate_per_sub) + 1;
    } else {
        row.no_of_subs = Math.trunc(row.subscription_rate / current_rate_per_sub);
    }
    // row.no_of_subs = new_rate_per_sub

    frm.refresh_fields('bill_view')
}
const computeBillTax = (taxtype, allocation_amount) => taxtype === "Vat Inclusive" ? flt(allocation_amount - flt(allocation_amount / 1.12)) : 0;

const flatFeeToggler = (doc) => {
    const ns = frappe.meta.get_docfield("PSOF Program", "subs_display", doc.doc.name)
    const sf = frappe.meta.get_docfield("PSOF Program", "subscription_fee", doc.doc.name)
    // switch (doc.doc.flat_fee) {
    //     case "Yes":
    //         ns.read_only = 0;
    //         sf.read_only = 1;
    //         break;
    //     case "No":
    //         ns.read_only = 1;
    //         sf.read_only = 0;
    //         break;
    // }
}


frappe.ui.form.on('PSOF', {
    validate: (frm, cdt, cdn) => {
        const cur_doc = locals[cdt][cdn];
        const program_list = [];
        const bill_generated = [];
        if (cur_doc.programs) {
            const subs = cur_doc.programs
                .map(program => program.subscription_fee)
                .reduce((total, value) => total + value, 0);
            frm.set_value('monthly_subs_fee_total', subs);

            for (let i = 0; i < cur_doc.programs.length; i++) {
                program_list.push(cur_doc.programs[i].subscription_program)
                bill_generated.push(cur_doc.programs[i].bill_generated)
            };
            let checker = new Set(program_list)
            if (program_list.length !== checker.size) {
                frappe.throw(__('Duplicate Entries Found\nCheck programs and remove duplicates'));
                cur_frm.refresh_fields(frm);
            }
            console.log(bill_generated)
            if (bill_generated.includes(0)) {
                frappe.msgprint(__('Kindly generate all programs'));
            }
        }
    },
    subscription_contract(frm) {
        frappe.db.get_value('Customer', frm.doc.customer_name, ['customer_primary_address', 'primary_address']).then(r => {
            frm.set_value('address_title', r.message.customer_primary_address)
            frm.set_value('cable_system_address', r.message.primary_address)
        })
    },

    address_title(frm) {
        frappe.db.get_value('Address', frm.doc.address_title, ['address_line1', 'address_line2', 'city', 'country']).then(a => {
            var r = a.message
            frm.set_value('cable_system_address', r.address_line1 + '<br>' + (r.address_line2 ? r.address_line2 + '<br>' : '') + r.city + "<br>" + r.country + '<br>');

        })
        // erpnext.utils.get_address_display(frm, cable_system_address, address_title)
    },

    // customer_name(frm) {
    //     frappe.db.get_value('Customer', frm.doc.customer_name, 'customer_primary_address').then(r => {
    //         console.log(r.message.customer_primary_address)
    //     })
    // },

    refresh: (frm) => {
        if (!frm.doc.__unsaved) {
            const cur_programs = frm.doc.programs.map((e) => e.subscription_program).filter((z) => z)
            if (cur_programs.length > 0 && cur_programs) {

                // frm.set_query("subscription_program", "programs", () => {
                //     return {
                //         filters: {
                //             name: ["not in", cur_programs]
                //         }
                //     }
                // })

                console.log(cur_programs)
            }
            flatFeeToggler(frm)
        }
        frm.set_query("subscription_contract", () => {
            return {
                query: "subscription.subscription.doctype.psof.psof.get_contracts",
                filters: {
                    docstatus: 1
                }
            }
        })
        // frm.fields_dict['subscription_contract'].get_query = function(doc, cdt, cdn) {
        //     return {
        //         filters: [
        //             // Add your filter conditions here
        //             ['docstatus', '=', 1]
        //         ],
        //         order_by: "creation DESC"
        //     };
        // };

        if (frm.doc.subscription_contract && !frm.doc.has_recomputed) {
            reCompute(frm)
        }
        frm.doc.contract_currency = 'USD'
        frm.toggle_display(['generate'], false)
        frm.toggle_display(['view_bill'], false)
        update_program(frm);
        frm.set_value('subscription_program', '')
        frm.clear_table('bill_view');


    },
    // onload_post_render: (frm) => {
    //     if (frm.doc.bill_until_renewed) {
    //         frm.$wrapper.find("[data-fieldname='end_date']").hide()
    //         frm.$wrapper.find(".data-row>[data-fieldname='subscription_program']").addClass("col-xs-4")
    //     } else {
    //         frm.$wrapper.find("[data-fieldname='bill_view']>div.grid-footer").hide()
    //     }
    // },

    tax_category: frm => reCompute(frm),
    programs: (frm) => {
        update_program(frm);
        cur_frm.refresh_fields(frm);
    },
    before_save: (frm) => {
        // cur_frm.call('create_bill', function (r){});
        cur_frm.call('update_bills', function (r) { });
        cur_frm.refresh_fields();
    },
    after_save: (frm) => {
        cur_frm.clear_table("bill_view");
        cur_frm.refresh_fields(frm)
    },
    subscription_program: (frm, cdt, cdn) => {
        const cur_doc = locals[cdt][cdn];
        const program_list = [];

        if (cur_doc.subscription_program && !(frm.doc.__unsaved && frm.doc.__islocal)) {
            frappe.db.get_value('PSOF Program Bill', {
                "subscription_program": cur_doc.subscription_program,
                "psof": cur_doc.name
            },
                ['subscription_program', 'psof', 'parent'])
                .then(r => {
                    let program = r.message
                    if ($.isEmptyObject(program)) {
                        frm.toggle_display(['generate'], true)
                        frm.toggle_display(['view_bill'], false)
                    } else {
                        frm.toggle_display(['generate'], false)
                        frm.toggle_display(['view_bill'], true)
                    }
                    cur_frm.refresh_fields(frm)
                })

        } else {
            frm.toggle_display(['generate'], false)
            frm.toggle_display(['view_bill'], false)
        }

        if (cur_doc.programs) {
            for (let i = 0; i < cur_doc.programs.length; i++) {
                program_list.push(cur_doc.programs[i].subscription_program)
            };
            let p = program_list.includes(cur_doc.subscription_program)
            if (!p) {
                if (cur_doc.subscription_program === '') {
                    return
                }
                else {
                    frappe.throw(__(cur_doc.subscription_program + ' not in the list of programs'))
                }
            }
        } else if (!frm.doc.__unsaved && !cur_doc.programs) {
            frappe.throw(__("Add a program first"))
        }
        cur_frm.clear_table("bill_view");
        cur_frm.refresh_fields(frm);
    },

    generate(frm, cdt, cdn) {
        const cur_doc = locals[cdt][cdn];
        const programs = frm.doc.programs
        const program_list = [];
        frm.toggle_display(['generate'], false)
        frm.toggle_display(['view_bill'], true)

        if (cur_doc.programs) {
            for (let i = 0; i < cur_doc.programs.length; i++) {
                program_list.push(cur_doc.programs[i].subscription_program)
            };
            if (program_list.includes(cur_doc.subscription_program)) {
                for (let program of programs) {
                    if (frm.doc.subscription_program === program.subscription_program) {
                        program.bill_generated = 1

                        setTimeout(() => {
                            frm.save()
                        }, "2000")
                        // console.log(program.doctype)
                        // frappe.model.set_value(program.doctype, program.docname, "bill_generated", 1);

                        // frm.fields_dict['programs'].grid.get_field('subscription_program').read_only = 1;
                    }
                }
                if (cur_doc.subscription_program === undefined) { }
                // else {
                //     frappe.throw(__(cur_doc.subscription_program + ' not in the list of programs'))
                // }
            }
        } else {
            frappe.throw(__("Add a program first"))
        }

        cur_frm.clear_table("bill_view");

        if (frappe.boot.sitename === 'test-v13.cableboss.net') {
            // FOR TEST SITE TESTING OF SCRIPT
            cur_frm.call('create_bill', function (r) { });
        } else {
            // ORGINAL
            // cur_frm.call('create_bill', function (r) { });
            cur_frm.call('create_bill', function (r) { });

        }

        cur_frm.refresh_fields(frm);
    },
    view_bill: (frm) => {
        cur_frm.clear_table("bill_view");
        cur_frm.call('view_new_bill', function (r) { })
        cur_frm.refresh_fields(frm);
    },
    flat_fee: (frm) => {
        if (in_list(["Yes", "No"], frm.doc.flat_fee)) {
            frappe.confirm(`You are setting the Flat Fee to ${frm.doc.flat_fee}, this cannot be changed. Are you sure you want to proceed?`,
                () => frm.save(),
                () => frm.refresh())
        }
    },
});

frappe.ui.form.on("PSOF Program Bill View", {
    subscription_fee: (frm, cdt, cdn) => reComputeBillView(frm, locals[cdt][cdn]),
    subscription_rate: (frm, cdt, cdn) => reComputeBillView(frm, locals[cdt][cdn]),
    decoder_rate: (frm, cdt, cdn) => reComputeBillView(frm, locals[cdt][cdn]),
    card_rate: (frm, cdt, cdn) => reComputeBillView(frm, locals[cdt][cdn]),
    promo_rate: (frm, cdt, cdn) => reComputeBillView(frm, locals[cdt][cdn]),
    freight_rate: (frm, cdt, cdn) => reComputeBillView(frm, locals[cdt][cdn]),
    // form_render: (frm, cdt, cdn) => reComputeBillView(frm, locals[cdt][cdn]),
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
                    row.free_view = r.free_view
                }
            })
            frm.refresh_field("bill_view")
        }
    },

    bill_generated: (frm, cdt, cdn) => {
        console.log('yes')
        let row = locals[cdt][cdn]
        // const sam = frappe.meta.get_docfield("PSOF Program Bill View", "bill_generated", row.name)
        console.log(row.idx)
        // console.log(sam)
        // ns.read_only = 0;
        // frm.fields_dict['programs'].grid.get_field('subscription_program').read_only = 1;
    }
});


frappe.ui.form.on("PSOF Program", {
    before_programs_remove: (frm, cdt, cdn) => {
        let row = locals[cdt][cdn];
        if (row.subscription_program) {
            frappe.confirm(`Are you sure you want to delete ${row.subscription_program}?`,
                () => {
                    frappe.call({
                        method: "subscription.subscription.doctype.psof.psof.delete_generated",
                        args: { 'parent': row.name, 'program': row.subscription_program, 'psof': frm.doc.name },
                        callback: r => {
                            if (r) {
                                frappe.msgprint(r.message)
                            }
                        },
                    })
                    //deleted row
                    setTimeout(() => {
                        frm.save()
                    }, "1500")

                },
                () => frm.reload_doc()
            );

        }

        frappe.db.get_value('Program Activation Item', {
            "program": row.subscription_program, "psof_program": row.name, "psof": row.parent
        }, ['program', 'psof_program', 'psof', 'parent'])
            .then(r => {
                let program = r.message
                if (program.program === row.subscription_program && program.psof_program === row.name && program.psof === row.parent) {
                    frm.disable_save()
                    frappe.msgprint({
                        title: __(`${row.subscription_program} cannot be removed`),
                        message: __(`Program is linked with Activation Module ${program.parent}, click Undo or reload doccument`),
                        primary_action: {
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
        let firstDay = frappe.format(new Date(date.getFullYear(), date.getMonth(), 1), { fieldType: 'Date' });
        row.subscription_contract = frm.doc.subscription_contract;
        row.subscription_currency = frm.doc.contract_currency;
        row.customer_name = frm.doc.customer_name;

        frappe.db.get_value('PSOF', row.parent, ['expiry_date', 'customer_name']).then(r => {
            let { customer_name } = r.message;
            row.start_date = firstDay;
            row.end_date = frappe.format(new Date(date.getFullYear() + 1, date.getMonth(), 0), { fieldType: 'Date' });
            row.customer_name = customer_name
            row.program_status = "<b>Status: Inactive</b> "

        });
        frm.refresh_fields();
    },
    //Active Checkbox
    decoder_allocation_active: (frm, cdt, cdn) => {
        var cur_doc = locals[cdt][cdn];
        if (cur_doc.decoder_allocation_active === 1) {
        } else {
            cur_doc.decoder_max_bill_count = 0;
        }
        update_amounts(frm, cdt, cdn);
        frm.refresh_fields();
    },
    promo_allocation_active: (frm, cdt, cdn) => {
        var cur_doc = locals[cdt][cdn];
        if (cur_doc.promo_allocation_active === 1) {
        } else {
            cur_doc.promo_max_bill_count = 0;
        }
        update_amounts(frm, cdt, cdn);
        frm.refresh_fields();
    },
    freight_allocation_active: (frm, cdt, cdn) => {
        var cur_doc = locals[cdt][cdn];
        if (cur_doc.freight_allocation_active === 1) {
        } else {
            cur_doc.freight_max_bill_count = 0;
        }
        update_amounts(frm, cdt, cdn);
        frm.refresh_fields();
    },
    card_allocation_active: (frm, cdt, cdn) => {
        var cur_doc = locals[cdt][cdn];
        if (cur_doc.card_allocation_active === 1) {
        } else {
            cur_doc.card_max_bill_count = 0;
        }
        update_amounts(frm, cdt, cdn);
        frm.refresh_fields();
    },
    renewal: (frm, cdt, cdn) => {
        const cur_doc = locals[cdt][cdn];
        if (cur_doc.renewal === 1) {
            cur_doc.active = 1
            cur_doc.program_status = "<b>Status:</b> Activated by Renewal"
        } else if (cur_doc.renewal === 0) {
            cur_doc.active = 0
            cur_doc.program_status = "<b>Status:</b> "
        }
        update_amounts(frm, cdt, cdn);
    },
    //Rates
    subscription_fee: (frm, cdt, cdn) => update_amounts(frm, cdt, cdn),
    no_of_subs: (frm, cdt, cdn) => update_amounts(frm, cdt, cdn),
    subs_display: (frm, cdt, cdn) => update_amounts(frm, cdt, cdn),
    decoder_rate: (frm, cdt, cdn) => update_amounts(frm, cdt, cdn),
    promo_rate: (frm, cdt, cdn) => update_amounts(frm, cdt, cdn),
    freight_rate: (frm, cdt, cdn) => update_amounts(frm, cdt, cdn),
    card_rate: (frm, cdt, cdn) => update_amounts(frm, cdt, cdn),
    decoder_difference: (frm, cdt, cdn) => update_amounts(frm, cdt, cdn),

    decoder_calculation: (frm, cdt, cdn) => {
        var cur_doc = locals[cdt][cdn];
        cur_doc.decoder_rate = cur_doc.decoder_calculation / cur_doc.decoder_max_bill_div;
        cur_doc.decoder_rate = truncateByDecimalPlace(cur_doc.decoder_rate, 2)
        update_amounts(frm, cdt, cdn);
        frm.refresh_fields();
    },
    card_calculation: (frm, cdt, cdn) => {
        var cur_doc = locals[cdt][cdn];
        cur_doc.card_rate = cur_doc.card_calculation / cur_doc.card_max_bill_divisor;
        cur_doc.card_rate = truncateByDecimalPlace(cur_doc.card_rate, 2)
        update_amounts(frm, cdt, cdn);
        frm.refresh_fields();
    },
    promo_calculation: (frm, cdt, cdn) => {
        var cur_doc = locals[cdt][cdn];
        cur_doc.promo_rate = cur_doc.promo_calculation / cur_doc.promo_max_bill_divisor;
        cur_doc.promo_rate = truncateByDecimalPlace(cur_doc.promo_rate, 2)
        update_amounts(frm, cdt, cdn);
        frm.refresh_fields();
    },
    freight_calculation: (frm, cdt, cdn) => {
        var cur_doc = locals[cdt][cdn];
        cur_doc.freight_rate = cur_doc.freight_calculation / cur_doc.freight_max_bill_divisor;
        cur_doc.freight_rate = truncateByDecimalPlace(cur_doc.freight_rate, 2)
        update_amounts(frm, cdt, cdn);
        frm.refresh_fields();
    },

    decoder_max_bill_div: (frm, cdt, cdn) => {
        var cur_doc = locals[cdt][cdn];
        cur_doc.decoder_rate = cur_doc.decoder_calculation / cur_doc.decoder_max_bill_div;
        update_amounts(frm, cdt, cdn);
        frm.refresh_fields();
    },
    card_max_bill_divisor: (frm, cdt, cdn) => {
        var cur_doc = locals[cdt][cdn];
        cur_doc.card_rate = cur_doc.card_calculation / cur_doc.card_max_bill_divisor;
        update_amounts(frm, cdt, cdn);
        frm.refresh_fields();
    },
    promo_max_bill_divisor: (frm, cdt, cdn) => {
        var cur_doc = locals[cdt][cdn];
        cur_doc.promo_rate = cur_doc.promo_calculation / cur_doc.promo_max_bill_divisor;
        update_amounts(frm, cdt, cdn);
        frm.refresh_fields();
    },
    freight_max_bill_divisor: (frm, cdt, cdn) => {
        var cur_doc = locals[cdt][cdn];
        cur_doc.freight_rate = cur_doc.freight_calculation / cur_doc.freight_max_bill_divisor;
        update_amounts(frm, cdt, cdn);
        frm.refresh_fields();
    }
});


// frappe.ui.form.on('PSOF Program', {
//     subscription_program: function(frm, cdt, cdn) {
//         var child = locals[cdt][cdn];
//         frappe.model.set_value(cdt, cdn, 'renewal', frm.doc.renewal);
//
//     }
// });

function hasAllDecimalPlacesAsNine(no_of_subs) {
    // Convert number to string
    let strNumber = no_of_subs.toString();

    // Check if the decimal part consists entirely of '9's using regular expression
    let decimalPart = strNumber.split('.')[1]; // Splitting at the decimal point and taking the part after it
    if (!decimalPart) return false; // If there's no decimal part, return false
    return /^99[5-9]/.test(decimalPart);
}