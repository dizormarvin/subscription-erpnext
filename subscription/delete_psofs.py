import frappe



psof_list = frappe.db.get_list("PSOF", pluck='name')

for psof in psof_list:
    frappe.db.delete("PSOF", {"name": psof})
    frappe.db.delete("PSOF Program", {"parent": psof})
    frappe.db.delete("PSOF Program Bill", {"psof": psof})
    frappe.db.delete("PSOF Program Bill View", {"parent": psof})
    frappe.db.delete("Program Activation", {"psof": psof})

for table in ("Subscription Contract", "Program Activation", "Program Activation Item", "Monthly PSOF", "Monthly PSOF Bill", "Monthly PSOF Billing",
              "Subscription Bill", "PSOF Program Bill View", "Subscription Bill Item", "Journal Entry", "Journal Entry Account"):
    frappe.db.delete(table)

frappe.db.commit()