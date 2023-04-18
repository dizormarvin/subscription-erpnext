# Copyright (c) 2023, ossphin and contributors
# For license information, please see license.txt

import frappe
import pandas as pd
from frappe.query_builder import DocType
from frappe import _

_cols = ['psof', 'subscription_program', 'parent', 'subscription_fee', 'customer_name']


def execute(filters=None):
    report_filter = process_filters(filters)
    process_data(report_filter)
    columns, data = get_report_cols(), [
        {
            'parent': 123,
            'parent_field': None,
            'is_group': True,
            'has_value': True,
            'billing': 0,
            'sales': 0,
            'indent': 0,
            'b_rate': 1,
            's_rate': 1
        },
        {
            'parent': 3,
            'parent_field': 123,
            'is_group': True,
            'has_value': True,
            'billing': 0,
            'sales': 0,
            'indent': 1,
            'b_rate': 1,
            's_rate': 1
        },
        {
            'parent': 2,
            'parent_field': 3,
            'is_group': True,
            'has_value': True,
            'billing': 0,
            'sales': 0,
            'indent': 2,
            'b_rate': 1,
            's_rate': 1
        }
    ]
    return columns, data


def process_data(filters=None):
    s_data = get_doc_data("Monthly PSOF Program Bill", filters)
    sales_data = process_df(s_data)
    # bills_data = process_df(get_doc_data("Subscription Bill Item", filters))


def process_df(doc_data):
    df_dict = {}
    df = pd.DataFrame(doc_data)
    grouped_df = df.groupby(["customer_name", "psof"])

    for groups, content in grouped_df:
        if df_dict.get(groups[0]):
            df_dict[groups[0]][groups[1]] = content.to_dict('records')
        else:
            df_dict[groups[0]] = content.to_dict('records')

    return df_dict




def get_report_cols():
    return [
        {
            "fieldname": "parent",
            "label": _('Systems\'s Name / Program'),
            "fieldtype": "Data",
            "width": 350,
        },
        {
            "fieldname": "billing",
            "label": _('Billing'),
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "fieldname": "sales",
            "label": _('Sales'),
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "fieldname": "b_rate",
            "label": _('Billing Rate'),
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "fieldname": "s_rate",
            "label": _('Sales Rate'),
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "fieldname": "variance",
            "label": _('Variance'),
            "fieldtype": "Data",
            "width": 150,
        },
    ]


def get_doc_data(doct, filters):
    doc = DocType(doct)
    cols = _cols.copy()
    mo = "s_month"

    if doct == 'Subscription Bill Item':
        cols[0] = (doc.psof_no).as_("psof")
        mo = "b_month"

    q = (
        frappe.qb.from_(doc)
        .select(*cols)
        .where(doc.date_from[filters.get(mo).get("s"):filters.get(mo).get("e")])
    )

    result = q.run(as_dict=True)

    return result


def process_filters(filters=None):
    _filter = {}
    if filters:
        for k, v in filters.items():
            if k == 'sales_month':
                _filter['s_month'] = get_start_end_day(filters.get("year"), v)
            if k == 'bill_month':
                _filter['b_month'] = get_start_end_day(filters.get("year"), v)
            if k == 'psof_no':
                _filter['psof'] = v
            if k == 'customer':
                _filter['customer'] = v
        _filter['variance'] = bool(filters.get("has_variance"))
        return _filter

    return None


def get_start_end_day(year, month):
    from frappe.utils import formatdate
    from time import strptime
    from frappe.utils import get_first_day, get_last_day
    date = formatdate(f'{year}-{strptime(month, "%B").tm_mon}')
    return {
        "s": get_first_day(date),
        "e": get_last_day(date)
    }
