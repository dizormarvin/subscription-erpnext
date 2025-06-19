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
        expiry_date <= '{nowdate()}'
        AND
        docstatus = 1
        AND
        renewed = 0""")

    for contract in expired_contracts:
        doc = frappe.get_doc("Subscription Contract", contract[0])
        if doc.get("status") != "Expired":
            doc.db_set("status", "Expired")

# OSS MARVIN START
#     active_contracts = frappe.db.sql(f"""
#         SELECT
#             name
#         FROM
#             `tabSubscription Contract`
#         WHERE
#             expiry_date IS NOT NULL
#             AND
#             expiry_date >= '{nowdate()}'
#             AND
#             renewed = 0""")
#
#     for contract in active_contracts:
#         doc = frappe.get_doc("Subscription Contract", contract[0])
#         if doc.get("status") == "Expired":
#             doc.db_set("status", "Active")
# OSS MARVIN END

# OSS INACTIVE TO ACTIVE

    inactive_contracts = frappe.db.sql(f""" SELECT
        sc.name as name
        
        FROM
        `tabSubscription Contract` sc
        
        
        left join (
        select contract_number, is_supersede from `tabSubscription Contract`
        )sc2 on sc2.contract_number = sc.name
        
        WHERE
        sc.expiry_date IS NOT NULL
        AND
        sc.expiry_date > '{nowdate()}'
        and sc.status = 'Inactive'
        and sc2.contract_number is null
        
    """)
    for contract in inactive_contracts:
        doc = frappe.get_doc("Subscription Contract", contract[0])
        if doc.get("status") != "Expired":
            doc.db_set("status", "Active")
