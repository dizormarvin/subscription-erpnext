# Copyright (c) 2022, ossphin and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import formatdate, get_datetime
from pypika import functions as fn


def execute(filters=None):
    columns, data = get_columns(filters), process_data(get_data(filters))
    return columns, data


def process_data(data):
    for row in data:
        for i in row:
            if i == "status":
                row[i] = "Submitted" if row[i] == 1 else "Pending" if row[i] == 0 else "Cancelled"
    return data


def get_data(filters=None):
    PA = frappe.qb.DocType("Program Activation")
    PAI = frappe.qb.DocType("Program Activation Item")
    PFB = frappe.qb.DocType("PSOF Program Bill")

    if filters.get("free_view"):
        query = (frappe.qb.from_(PA)
                 .left_join(PAI)
                 .on(PAI.parent == PA.name)
                 .left_join(PFB)
                 .on(PFB.parent_bill == PAI.psof_program)
                 .select(PA.name, (PA.docstatus).as_("status"), PA.customer, PAI.psof, PAI.program,
                         PAI.action, PAI.req_date, (PAI.date_activation_de_activation).as_("confirm_date"),
                         PAI.ird_model, PAI.decoder_serial, (PAI.ird_serial).as_("ird_id"), (PAI.cam_no).as_("cam"),
                         fn.Concat(PFB.date_from, ' / ', PFB.date_to).as_("free_view"))
                 .where(PFB.free_view == 1))
    else:
        query = (frappe.qb.from_(PA)
                 .left_join(PAI)
                 .on(PAI.parent == PA.name)
                 .select(PA.name, (PA.docstatus).as_("status"), PA.customer, PAI.psof, PAI.program,
                         PAI.action, PAI.req_date,
                         (PAI.date_activation_de_activation).as_("confirm_date"),
                         PAI.ird_model, PAI.decoder_serial, (PAI.ird_serial).as_("ird_id"), (PAI.cam_no).as_("cam")))

    if filters.get("group_by"):
        query = query.groupby(PA.customer, PAI.psof, PAI.program)

    if filters.get("status"):
        status = 1 if filters.get("status") == "Submitted" else 0 if filters.get("status") == "Draft" else 2
        query = query.where(PA.docstatus == status)

    if filters.get("action"):
        query = query.where(PAI.action == filters.get("action"))

    if filters.get("subs_period") or (filters.get("start_date") or filters.get("end_date")):
        start_date = get_datetime(filters.get("start_date"))
        end_date = get_datetime(filters.get("end_date"))

        if filters.get("start_date") and filters.get("end_date"):
            query = query.where(PAI.date_activation_de_activation[start_date: end_date])
        elif filters.get("start_date") and not (filters.get("end_date") and filters.get("subs_period")):
            query = query.where(PAI.date_activation_de_activation >= start_date)
        elif filters.get("end_date") and not (filters.get("start_date") and filters.get("subs_period")):
            query = query.where(PAI.date_activation_de_activation <= end_date)

    return query.run(as_dict=1)


def get_columns(filters):
    cols = [
        {
            "fieldname": "name",
            "fieldtype": "Link",
            "label": "ID",
            "options": "Program Activation",
            "width": 250
        },
        {
            "fieldname": "status",
            "fieldtype": "Data",
            "label": "Status",
            "width": 100
        },
        {
            "fieldname": "customer",
            "fieldtype": "Data",
            "label": "Cable System Name",
            "width": 200
        },
        {
            "fieldname": "psof",
            "fieldtype": "Link",
            "label": "PSOF",
            "options": "PSOF",
            "width": 100
        },
        {
            "fieldname": "program",
            "fieldtype": "Link",
            "label": "Subscription Program",
            "options": "Subscription Program",
            "width": 230
        },
        {
            "fieldname": "action",
            "fieldtype": "Select",
            "label": "Action",
            "options": "Activate\nDeactivate",
            "width": 150
        },
        {
            "fieldname": "confirm_date",
            "fieldtype": "Date",
            "label": "Confirmation Date",
            "width": 100
        },
        {
            "fieldname": "req_date",
            "fieldtype": "Date",
            "label": "Request Date",
            "width": 100
        },
        {
            "fieldname": "ird_model",
            "fieldtype": "Data",
            "label": "IRD Model",
            "width": 150
        },
        {
            "fieldname": "decoder_serial",
            "fieldtype": "Data",
            "label": "Decoder Serial",
            "width": 150
        },
        {
            "fieldname": "ird_id",
            "fieldtype": "Data",
            "label": "IRD ID",
            "width": 150
        },
        {
            "fieldname": "cam",
            "fieldtype": "Data",
            "label": "CAM",
            "width": 150
        },
    ]

    if filters.get("free_view"):
        cols.append({
            "fieldname": "free_view",
            "fieldtype": "Data",
            "label": "Free View",
            "width": 300
        })

    return cols
