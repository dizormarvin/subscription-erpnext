// Copyright (c) 2022, ossphin and contributors
// For license information, please see license.txt
/* eslint-disable */
const toggleSubsPeriod = (frappe) => {
	if (frappe.query_report.get_filter_value('subs_period')) frappe.query_report.set_filter_value('subs_period', '');
	frappe.query_report.refresh()
}

frappe.query_reports["Program Activation"] = {
	"filters": [
		{
			"fieldname": "group_by",
			"fieldtype": "Select",
			"label": "Group By",
			"options": "\nCable System\nPSOF"
		},
		{
			"fieldname": "status",
			"fieldtype": "Select",
			"label": "Doc Status",
			"options": "\nSubmitted\nDraft\nCancelled"
		},
		{
			"fieldname": "action",
			"fieldtype": "Select",
			"label": "Action",
			"options": "\nActivate\nDeactivate"
		},
		{
			"fieldname": "subs_period",
			"fieldtype": "Link",
			"label": "Subscription Period",
			"options": "Subscription Period",
			"on_change": () => {
				const subs_period = frappe.query_report.get_filter_value('subs_period');
				if (subs_period) {
					frappe.db.get_value("Subscription Period", subs_period, ["start_date", "end_date"])
						.then((r) => {
							if (r) {
								const {start_date, end_date} = r.message;
								frappe.query_report.set_filter_value('start_date', new Date(start_date));
								frappe.query_report.set_filter_value("end_date", new Date(end_date));
							}
						})
				}
			}
		},
		{
			"fieldname": "start_date",
			"fieldtype": "Date",
			"label": "Start Date",
			"on_change": () => {
				toggleSubsPeriod(frappe)
			}
		},
		{
			"fieldname": "end_date",
			"fieldtype": "Date",
			"label": "End Date",
			"on_change": () => {
				toggleSubsPeriod(frappe)
			}
		},
		{
			"fieldname": "free_view",
			"fieldtype": "Check",
			"label": "Show Only Free Viewing"
		},
		],
};
