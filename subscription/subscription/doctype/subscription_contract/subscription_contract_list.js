frappe.listview_settings["Subscription Contract"] = {
    get_indicator: (doc) => {
        switch (doc.status) {
            case "Expired":
                return [__("Expired"), "red", "status,=,Expired"]
                break
            case "Active":
                return [__("Active"), "yellow", "status,=,Active"]
                break
            case "Inactive":
                return [__("Inactive"), "blue", "status,=,Inactive"]
                break
        };
    }
}