frappe.query_reports["PSOF Bill View"] = {
    "filters": [
		{
			"fieldname":"name",
			"label":"PSOF Number",
			"fieldtype":"Link",
			"options":"PSOF"
		},
	],
    get_datatable_options(options) {
        options.columns.forEach(function(column, i) {
            if(column.id == "subscription_fee") {
                column.editable = true
            }
            });
        return Object.assign(options, {
        checkboxColumn: true,
        events: {
            onCheckRow: function (data) {
                console.log("click");
            },
        }
        });
    }
};