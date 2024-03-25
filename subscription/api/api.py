import frappe
import json


@frappe.whitelist()
def get_test_api():
    return frappe.db.get_list("Test Doc")
