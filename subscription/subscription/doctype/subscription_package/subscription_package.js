// Copyright (c) 2020, ossphin and contributors
// For license information, please see license.txt

frappe.ui.form.on('Subscription Package', {
	// refresh: function(frm) {

	// }
});

frappe.ui.form.on("Subscription Package Item", "rate", function(frm, cdt, cdn) {

   var table = frm.doc.packages;
   var total = 0;
   for(var i in table) {
	if (table[i].active == 1)
	{
       		total = total + table[i].rate;
        }
  }

        frm.set_value("total",total); 
});

frappe.ui.form.on("Subscription Package Item", "active", function(frm, cdt, cdn) {

   var table = frm.doc.packages;
   var total = 0;
   for(var i in table) {
        if (table[i].active == 1)
        {
                total = total + table[i].rate;
        }
  }

        frm.set_value("total",total); 
});
