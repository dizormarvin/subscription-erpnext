from frappe import _


def get_data():
    return {
        "fieldname": "program_activation_request",
        "non_standard_fieldnames": {
            "Material Request": "parent_program_activation"
        },
        "transactions": [
            {
                "label": _("Material Request"),
                "items": ["Material Request"],
            },
        ]
    }
