// Copyright (c) 2020, ossphin and contributors
// For license information, please see license.txt

frappe.ui.form.on('Subscription Program', {
    refresh: function(frm) {
        ['decoder', 'card', "program"].map((e) => {
            frm.fields_dict['packaged_programs'].grid.get_field(e).get_query = (doc, cdt, cdn) => {
                const row = locals[cdt][cdn];
                if (e === "program") return {
                    filters: {
                        item_group: "CHANNELS",
                    }
                }
                return {
                    filters: {
                        item_group: e === "card" ? "SMART CARD" : e.toUpperCase(),
                        name: ["like", `%${row.program}%`]
                    }
                }
            }
        })
    },

    validate: (frm) => {
        const {is_package, program_name} = frm.doc;

        if (is_package) {
            const psof = frappe.db.exists("PSOF Program", {"subscription_program" : program_name})
            console.log(psof)
        }
    }
});
