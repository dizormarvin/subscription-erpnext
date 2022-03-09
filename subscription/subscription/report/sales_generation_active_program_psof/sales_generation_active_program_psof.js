frappe.query_reports["Sales Generation Active Program PSOF"] = {
    "filters": [
        {
            "fieldname":"period",
            "label": __("Previous Period"),
            "fieldtype": "Link",
            "options": "Subscription Period",
            "reqd" : 1
            //"default": frappe.defaults.get_user_default("company")
        },
        {
            "fieldname":"periodcurrent",
            "label": __("Current Period"),
            "fieldtype": "Link",
            "options": "Subscription Period",
            "reqd" : 1
            //"default": frappe.defaults.get_user_default("company")
        },
              /*
        {
            "fieldname":"date_from",
            "label": __("Created Date"),
            "fieldtype": "Date",
	    "default": get_today()
        },

                {
            "fieldname":"project",
            "label": __("Project"),
            "fieldtype": "Link",
            "options": "Project"
        },
          */
    ]
}
