// Copyright (c) 2022, ossphin and contributors
// For license information, please see license.txt


frappe.ui.form.on('Program Activation Request', {
    onload: (frm) => {
        if (!frm.doc.docstatus)
            frm.set_value("user", frappe.session.user)
    },
    
    customer: (frm) => {
        frm.set_query ("psof", () => {
            return {
                query: "subscription.subscription.doctype.psof.psof.get_programs",
                filters: {
                    customer: frm.doc.customer,
                    from_request: 1
                }
            }
        });
    },

    psof: (frm) => {
		frm.clear_table("programs")
		frm.call("load_psof_programs")
		frm.refresh_field('programs')
	},
});



frappe.ui.form.on('Program Activation Request Item', {
    before_programs_remove: (frm, cdt, cdn) => {
        const row = locals[cdt][cdn]

        if (row.from_package) {
            frappe.throw(`Cannot remove ${row.program} because it belongs to package ${row.package_name}`)
        }
    },

    action: (frm, cdt, cdn) => {
        const row = locals[cdt][cdn]
        row.request_date = row.request_date ? row.request_date:frappe.datetime.get_today();
        row.remarks = `${row.program} from PSOF: ${row.psof} request to ${row.action} on ${row.request_date}`
        frm.refresh_field('programs')
    }
})
