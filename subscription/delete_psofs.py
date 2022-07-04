
import frappe



psof_list = frappe.db.get_list("PSOF", filters={"modified": ["<=", '2022-05-18 15:22:16.600373']}, pluck='name')

for psof in psof_list:
    frappe.db.delete("PSOF", {"name": psof})
    frappe.db.delete("PSOF Program", {"parent": psof})
    frappe.db.delete("PSOF Program Bill", {"psof": psof})
    frappe.db.delete("Program Activation", {"psof": psof})

for table in ("Program Activation", "Program Activation Item", "Monthly PSOF", "Monthly PSOF Bill", "Monthly PSOF Billing",
              "Subscription Bill", "Subscription Bill Item", "Journal Entry", "Journal Entry Account"):
    frappe.db.delete(table)

frappe.db.commit()