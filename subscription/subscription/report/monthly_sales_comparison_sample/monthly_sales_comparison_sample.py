# Copyright (c) 2023, ossphin and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import add_months, getdate, nowdate, flt
import pandas as pd


def execute(filters=None):
    if not (filters.get('mpsof_1') and filters.get('mpsof_2')):
        return [], []

    columns = _get_columns(filters=filters)
    data = _get_data(filters, columns)
    pd_df = pd.DataFrame(data)

    data.append({
        'parent_customer': 'Total',
        'm1_fee': pd_df['m1_fee'].sum() or 0,
        'm2_fee': pd_df['m2_fee'].sum() or 0,
        'variance': pd_df['variance'].sum() or 0
    })

    [d.update({'variance': flt(d.get('m1_fee') - d.get('m2_fee'))}) for d in data if d.get('indent') == 2]

    return columns, data


def _get_columns(filters=None):
    m1 = filters.get("mpsof_1")
    m2 = filters.get("mpsof_2")

    columns = [
        {
            "fieldname": "parent_customer",
            "label": _('Cable System/Program Name'),
            "fieldtype": "Link",
            "options": 'Subscription',
            "width": 350,
        },
        {
            "fieldname": "m1_psof",
            "label": _(f'{m1} PSOF'),
            "fieldtype": "Link",
            "options": 'PSOF',
            "width": 120,
        },
        {
            "fieldname": "m2_psof",
            "label": _(f'{m2} PSOF'),
            "fieldtype": "Link",
            "options": 'PSOF',
            "width": 120,
        },
        {
            "fieldname": "m1_fee",
            "label": _(f'{m1}'),
            "fieldtype": "Currency",
            "width": 120,
        },
        {
            "fieldname": "m2_fee",
            "label": _(f'{m2}'),
            "fieldtype": "Currency",
            "width": 100,
        },
        {
            "fieldname": "variance",
            "label": _(f'Variance'),
            "fieldtype": "Currency",
            "width": 100,
        }
    ]

    return columns


def _get_data(filters=None, columns=None):
    mpsof, mp1, mp2 = [frappe.qb.DocType('Monthly PSOF Program Bill'), filters.get('mpsof_1'), filters.get('mpsof_2')]
    result = []

    parent_program = (
        frappe.qb.from_(mpsof)
        .select(mpsof.customer_name.as_('customer')).distinct()
        .where(mpsof.parent.isin([mp1, mp2]))
    ).run(as_dict=True)

    for parent in parent_program:
        p_data = {
            'parent': 1,
            'parent_customer': parent.customer,
            'child_program': None,
            'm1_psof': None,
            'm2_psof': None,
            'm1_fee': mpsof_total(mp1, parent.get('customer')),
            'm2_fee': mpsof_total(mp2, parent.get('customer')),
            'variance': 0,
            'indent': 0,
            'has_value': False,
        }
        p_data['variance'] = flt(p_data.get('m1_fee') - p_data.get('m2_fee'))

        c_data = []

        for i, f in enumerate((mp1, mp2)):
            prefix = 'm1_' if not i else 'm2_'

            q = (
                frappe.qb.from_(mpsof)
                .select(
                    (mpsof.subscription_program).as_(prefix + 'program'),
                    (mpsof.psof).as_(prefix + 'psof'),
                    (mpsof.subscription_fee).as_(prefix + 'fee')
                )
            )

            for k, v in filters.items():
                if k in ('mpsof_1', 'mpsof_2', 'has_variance'):
                    continue
                elif k == 'date_from':
                    q = q.where(mpsof[k] >= v)
                elif k == 'date_to':
                    q = q.where(mpsof[k] <= v)
                else:
                    q = q.where(mpsof[k] == v)

            q = q.where((mpsof.parent == f) & (mpsof.customer_name == parent.get('customer'))).run(as_dict=1)

            c_data.append(q)

        n_data = []
        if not len(c_data[0]) and not len(c_data[1]):
            p_data.clear()
            continue
        elif len(c_data[0]) and len(c_data[1]):
            for i1 in c_data[0]:
                for i2 in c_data[1]:
                    if i2.get("m2_psof") == i1.get("m1_psof") and i2.get("m2_program") == i1.get("m1_program"):
                        i1.update(i2)
                        c_data[1].remove(i2)
                        i1.update({
                            'parent_customer': i1.get('m1_program'),
                            'child_program': parent.customer,
                            'indent': 2,
                        })
            if len(c_data[1]):
                for i2 in c_data[1]:
                    x = i2
                    x.update({
                        'parent_customer': i2.get('m2_program'),
                        'child_program': parent.customer,
                        'indent': 2
                    })
                    c_data[0].append(i2)
                    c_data[1].remove(i2)

            n_data = c_data[0]
        elif len(c_data[0]):
            n_data = c_data[0]
            p_data['m2_fee'] = 0
            p_data['variance'] = p_data.get('m1_fee') - 0
        elif len(c_data[1]):
            n_data = c_data[1]
            p_data['m1_fee'] = 0
            p_data['variance'] = 0 - p_data.get('m2_fee')
        result.append(p_data)

        for i in n_data:
            if i.get("m2_psof") == i.get("m1_psof") and i.get("m2_program") == i.get("m1_program"):
                i.update({
                    'variance': flt(i.get('m1_fee') or 0 - i.get('m2_fee') or 0) + 500,
                })
            i.update({
                'parent_customer': i.get('m1_program') or i.get('m2_program'),
                'child_program': parent.customer,
                'indent': 2,
                'm1_fee': i.get('m1_fee') or 0,
                'm2_fee': i.get('m2_fee') or 0,
                'variance': flt(i.get('m1_fee') or 0 - i.get('m2_fee') or 0),
            })

        if filters.get('has_variance'):
            n_data = [res for res in n_data if flt(res['variance'])]

        result += n_data

    return result


def mpsof_total(mpsof, customer=None):
    f = {"parent": mpsof}

    if customer:
        f["customer_name"] = customer

    result = flt(frappe.db.get_value("Monthly PSOF Program Bill", f, "sum(subscription_fee)"))

    return result or 0
