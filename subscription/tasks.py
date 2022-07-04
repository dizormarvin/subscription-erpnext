import frappe
from frappe.utils import nowdate


def all():
    expired_contracts = frappe.db.sql(f"""
    SELECT
        name
    FROM
        `tabSubscription Contract`
    WHERE
        expiry_date IS NOT NULL
        AND
        expiry_date <= '{nowdate()}'""")

    for contract in expired_contracts:
        doc = frappe.get_doc("Subscription Contract", contract[0])
        doc.db_set("status", "Expired")