# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from frappe import _


def get_data():
    return [
        {
            "module_name": "Subscription",
            "category": "Modules",
            "label": _("Subscription"),
            "color": "#FFF5A7",
            "reverse": 1,
            "icon": "octicon octicon-calendar",
            "type": "module",
            "description": "Subscription Contracts, Packages and more."
        }
    ]
