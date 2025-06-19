frappe.listview_settings["Program Activation Request"] = {
    add_fields: ["workflow_state"],
    get_indicator: (doc) => {
        let color =
            doc.workflow_state === 'Rejected' ? 'red' :
                doc.workflow_state === "For Acct Manager Approval" ? "green" :
                doc.workflow_state === "For Billing & Collection Approval" ? "green" :
                    doc.workflow_state === "For Sales Coordinator Approval" ? "green" :
                         doc.workflow_state === "For AVP Network Approval" ? "green" :
                             doc.workflow_state === "Draft Request" ? "green" :
                                 doc.workflow_state === "EMD Approval" ? "green" :
                doc.workflow_state === 'Sent to Technical' ? 'yellow' :
                doc.workflow_state === "Fulfilled" ? "blue" : "black";
        return [__(doc.workflow_state), color, `status,=,${doc.workflow_state}`]
    }

}