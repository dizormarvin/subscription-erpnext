frappe.query_reports["Subscription Contract"] = {
    "filters": [
        {
            "fieldname":"company",
            "label": __("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "default": frappe.defaults.get_user_default("company")
        },
        
        {
            "fieldname":"contract_number",
            "label": __("Contract Series#"),
			"fieldtype": "Link",
			"options": "Subscription Contract",
			"reqd": 1
	   // "default": get_today()
        }


        /*
                {
            "fieldname":"project",
            "label": __("Invoice Date From"),
            "fieldtype": "Date",
            "options": "Project"
        },
        */
    ]
}
