// Copyright (c) 2021, ossphin and contributors
// For license information, please see license.txt

frappe.ui.form.on('Subscription Bill', {
    on_submit: function(frm) {
        frm.call('createjournal','', function(r){ })
    }
});
