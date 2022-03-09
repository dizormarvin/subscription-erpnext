from __future__ import unicode_literals
from frappe import _


def get_data():

        return [
                {
                        "label": _("Contracts"),
                        "icon": "icon-file",
                        "items": [
                                {
                                        "type": "doctype",
                                        "name": "Subscription Contract",
                                        "label": _("Subscription Contract"),
                                },
                                {
                                        "type": "doctype",
                                        "name": "PSOF",
                                        "label": _("PSOF"),
                                },
                                {
                                        "type": "doctype",
                                        "name": "Monthly PSOF",
                                        "label": _("Monthly PSOF"),
                                },
                                {
                                        "type": "doctype",
                                        "name": "PSOF Program",
                                        "label": _("PSOF Program"),
                                },
                                {
                                        "type": "doctype",
                                        "name": "Customer",
                                        "label": _("Customer"),
                                },
                                {
                                        "type": "doctype",
                                        "name": "Item",
                                        "label": _("Item"),
                                },
                                {
                                        "type": "doctype",
                                        "name": "Monthly PSOF Billing",
                                        "label": _("Monthly Billing"),
                                },
                                {
                                        "type": "doctype",
                                        "name": "Program Activation",
                                        "label": _("Program Activation / Deactivation"),
                                },
                        ]
                },
                {
                        "label": _("Settings"),
                        "icon": "icon-file",
                        "items": [
                                {
                                        "type": "doctype",
                                        "name": "Subscription Period",
                                        "label": _("Subscription Period"),
                                },
                                {
                                        "type": "doctype",
                                        "name": "Subscription Setup",
                                        "label": _("Subscription Setup"),
                                },
                                {
                                        "type": "doctype",
                                        "name": "Subscription Program",
                                        "label": _("Subscription Program"),
                                },
                        ]
                }
        ]
