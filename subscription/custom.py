import pandas as pd
import frappe
import os


def run():
    df = pd.read_excel('/home/erpnext/frappe-bench/sites/v13.cableboss.net/private/files/CB-OMI CLIENTSe58ef0.xls')
    cx = frappe.db.get_list("Customer", ['name', 'customer_name'])

    # pd_cx = df[['cable system name', 'Island', 'region', 'province', 'city_municipality']]
    pd_cx = df[['cable system name', "Type of Service", "Type of System", "Signatory", "Withholding Tax Rate"]]
    pd_cx.dropna(inplace=True)
    pd_cx.drop_duplicates(subset="cable system name", inplace=True)

    for i_pd, r in pd_cx.iterrows():
        for i in cx:
            if i.get("customer_name") == r["cable system name"]:
                frappe.db.set_value("Customer", i.get("name"), {
                    "witholding_tax_rate": r["Withholding Tax Rate"] * 100
                })

    frappe.db.commit()


def update_accounts():
    df = pd.read_excel('/home/erpnext/frappe-bench/sites/v13.cableboss.net/private/files/Account2.xls')
    for i_pd, r in df.iterrows():
        n = r["Account Name"].split(" - ")
        n = " - ".join(n[:2])

        if bool(frappe.db.exists("Account", {"account_number": r["Account Number"]})):
            doc = frappe.get_doc("Account", frappe.db.get_value("Account", {"account_number": r["Account Number"]}))
            new_doc = doc.as_dict().copy()
            try:
                doc.delete(True)
            except Exception as e:
                continue

            frappe.db.commit()
            new_name = r["ID"].split(" - ")
            new_name = ' '.join(new_name[:3])
            new_doc["name"] = new_name
            new_doc["account_name"] = n
            s = frappe.get_doc(new_doc)
            s.insert()
        else:
            d = frappe.get_doc({
                "doctype": "Account",
                "account_number": r["Account Number"],
                "parent_account": r["Parent Account"],
                "account_name": n,
            })
            d.insert()

    frappe.db.commit()


def update_all_accounts():
    x = frappe.db.get_all("Account", pluck="name")
    for i in x:
        if " - OMI - CB" in i:
            doc = frappe.get_doc("Account", i)
            new_doc = doc.as_dict().copy()
            try:
                doc.delete(True)
            except Exception as e:
                continue

            frappe.db.commit()
            new_doc["account_name"] = new_doc.get("account_name").replace(" - OMI - CB", '')
            new_doc["account_name"] = new_doc.get("account_name").replace(" - OMI", '')
            new_doc["account_name"] = new_doc.get("account_name").replace(" - CB", '')
            new_doc["name"] = ' - '.join([new_doc.get("account_number"), new_doc["account_name"]])
            d = frappe.get_doc(new_doc)
            d.insert()

    frappe.db.commit()

