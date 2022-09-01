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