frappe.listview_settings['Program Activation'] = {
    add_fields: ["workflow_state"],
    get_indicator: function(doc) {
        let color =
            doc.workflow_state === 'Rejected' ? 'red' :
            doc.workflow_state === 'For Approval' ? 'green' :
            doc.workflow_state === 'Technical Assistant' ? 'orange' :
            doc.workflow_state === 'Pending' ? 'orange' :
            doc.workflow_state === 'Approved' ? 'blue' : 'black';

        return [__(doc.workflow_state), color, `status,=,${doc.workflow_state}`];
    }
};
