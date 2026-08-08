import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field


FIELDS_BY_DOCTYPE = {
    "Sales Invoice": {
        "fieldname": "custom_transaction_reference",
        "label": "Transaction Reference",
        "fieldtype": "Data",
        "insert_after": "gift_card_redemptions",
    },
    "POS Invoice": {
        "fieldname": "custom_transaction_reference",
        "label": "Transaction Reference",
        "fieldtype": "Data",
        "insert_after": "gift_card_redemptions",
    },
}

TABLE_FIELDS_BY_DOCTYPE = {
    "Sales Invoice": {
        "fieldname": "posa_payment_transaction_references",
        "label": "Payment Transaction References",
        "fieldtype": "Table",
        "options": "POS Payment Transaction Reference",
        "insert_after": "custom_transaction_reference",
    },
    "POS Invoice": {
        "fieldname": "posa_payment_transaction_references",
        "label": "Payment Transaction References",
        "fieldtype": "Table",
        "options": "POS Payment Transaction Reference",
        "insert_after": "custom_transaction_reference",
    },
}


def _sync_field(doctype, field):
    custom_field_name = f"{doctype}-{field['fieldname']}"
    if not frappe.db.exists("Custom Field", custom_field_name):
        create_custom_field(doctype, field)
    else:
        frappe.db.set_value(
            "Custom Field",
            custom_field_name,
            {
                "label": field["label"],
                "fieldtype": field["fieldtype"],
                "options": field.get("options"),
                "insert_after": field["insert_after"],
            },
            update_modified=False,
        )
    frappe.clear_cache(doctype=doctype)


def execute():
    for doctype, field in FIELDS_BY_DOCTYPE.items():
        _sync_field(doctype, field)

    for doctype, field in TABLE_FIELDS_BY_DOCTYPE.items():
        _sync_field(doctype, field)
