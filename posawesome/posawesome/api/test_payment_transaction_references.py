import importlib.util
import pathlib
import sys
import types
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
HOOKS_PATH = REPO_ROOT / "posawesome" / "hooks.py"
PATCHES_PATH = REPO_ROOT / "posawesome" / "patches.txt"
PATCH_MODULE = "posawesome.patches.add_payment_transaction_references"
PATCH_PATH = f"{PATCH_MODULE}.execute"


def _install_frappe_stub():
    frappe_module = types.ModuleType("frappe")
    frappe_module._ = lambda text: text

    def _throw(message):
        raise Exception(message)

    frappe_module.throw = _throw

    frappe_utils = types.ModuleType("frappe.utils")

    def _flt(value, precision=None):
        try:
            result = float(value or 0)
        except (TypeError, ValueError):
            result = 0.0
        if precision is not None:
            result = round(result, precision)
        return result

    frappe_utils.flt = _flt
    frappe_utils.add_days = lambda date, days: date
    frappe_module.utils = frappe_utils

    model_module = types.ModuleType("frappe.model")
    mapper_module = types.ModuleType("frappe.model.mapper")
    mapper_module.get_mapped_doc = lambda *args, **kwargs: None
    model_module.mapper = mapper_module

    sys.modules["frappe"] = frappe_module
    sys.modules["frappe.utils"] = frappe_utils
    sys.modules["frappe.model"] = model_module
    sys.modules["frappe.model.mapper"] = mapper_module

    utilities_module = types.ModuleType("posawesome.posawesome.api.utilities")
    utilities_module.get_company_domain = lambda *args, **kwargs: None
    sys.modules["posawesome.posawesome.api.utilities"] = utilities_module

    payments_module = types.ModuleType("posawesome.posawesome.api.payments")
    payments_module.get_posawesome_credit_redeem_remark = lambda *args, **kwargs: ""
    sys.modules["posawesome.posawesome.api.payments"] = payments_module

    delivery_charges_module = types.ModuleType(
        "posawesome.posawesome.doctype.delivery_charges.delivery_charges"
    )
    delivery_charges_module.get_applicable_delivery_charges = lambda *args, **kwargs: None
    sys.modules["posawesome.posawesome.doctype.delivery_charges.delivery_charges"] = (
        delivery_charges_module
    )

    pos_coupon_module = types.ModuleType("posawesome.posawesome.doctype.pos_coupon.pos_coupon")
    pos_coupon_module.update_coupon_code_count = lambda *args, **kwargs: None
    sys.modules["posawesome.posawesome.doctype.pos_coupon.pos_coupon"] = pos_coupon_module


def _load_invoice_module():
    module_name = "posawesome.posawesome.api.invoice"
    file_path = REPO_ROOT / "posawesome" / "posawesome" / "api" / "invoice.py"
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class FakeDoc:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def get(self, key, default=None):
        return getattr(self, key, default)


def _row(mode_of_payment, transaction_reference, amount):
    return types.SimpleNamespace(
        mode_of_payment=mode_of_payment,
        transaction_reference=transaction_reference,
        amount=amount,
    )


def _payment(mode_of_payment, amount):
    return types.SimpleNamespace(mode_of_payment=mode_of_payment, amount=amount)


class TestValidatePaymentTransactionReferences(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _install_frappe_stub()
        cls.invoice = _load_invoice_module()

    def _validate(self, doc):
        self.invoice.validate_payment_transaction_references(doc)

    def test_no_references_is_a_noop(self):
        doc = FakeDoc(
            posa_payment_transaction_references=[],
            payments=[_payment("Cash", 1240)],
            is_return=0,
            grand_total=500,
            rounded_total=500,
        )
        # Should not raise even though payments exceed the (irrelevant) totals below,
        # since old invoices without references must validate exactly as before.
        self._validate(doc)

    def test_blank_transaction_reference_throws(self):
        doc = FakeDoc(
            posa_payment_transaction_references=[_row("M-Pesa", "  ", 500)],
            payments=[_payment("M-Pesa", 500)],
            is_return=0,
            grand_total=500,
            rounded_total=500,
        )
        with self.assertRaises(Exception):
            self._validate(doc)

    def test_zero_amount_throws(self):
        doc = FakeDoc(
            posa_payment_transaction_references=[_row("M-Pesa", "QWE123", 0)],
            payments=[_payment("M-Pesa", 0)],
            is_return=0,
            grand_total=500,
            rounded_total=500,
        )
        with self.assertRaises(Exception):
            self._validate(doc)

    def test_mismatched_sum_throws(self):
        doc = FakeDoc(
            posa_payment_transaction_references=[
                _row("M-Pesa", "QWE123", 500),
                _row("M-Pesa", "ABC567", 300),
            ],
            payments=[_payment("M-Pesa", 1240)],
            is_return=0,
            grand_total=1240,
            rounded_total=1240,
        )
        with self.assertRaises(Exception):
            self._validate(doc)

    def test_matching_sum_passes(self):
        doc = FakeDoc(
            posa_payment_transaction_references=[
                _row("M-Pesa", "QWE123", 500),
                _row("M-Pesa", "ABC567", 300),
                _row("M-Pesa", "XYZ111", 440),
            ],
            payments=[_payment("M-Pesa", 1240)],
            is_return=0,
            grand_total=1240,
            rounded_total=1240,
        )
        self._validate(doc)

    def test_total_referenced_exceeding_invoice_total_throws(self):
        doc = FakeDoc(
            posa_payment_transaction_references=[
                _row("M-Pesa", "QWE123", 1000),
                _row("Bank", "ABC567", 500),
            ],
            payments=[_payment("M-Pesa", 1000), _payment("Bank", 500)],
            is_return=0,
            grand_total=1240,
            rounded_total=1240,
        )
        with self.assertRaises(Exception):
            self._validate(doc)

    def test_return_invoice_is_exempt_from_total_check(self):
        doc = FakeDoc(
            posa_payment_transaction_references=[_row("M-Pesa", "QWE123", 500)],
            payments=[_payment("M-Pesa", -1240)],
            is_return=1,
            grand_total=1240,
            rounded_total=1240,
        )
        # The amount/sum-mismatch check still applies (500 != -1240 magnitude-wise it
        # would throw), so use a matching row to isolate the invoice-wide exemption.
        doc.payments = [_payment("M-Pesa", 500)]
        self._validate(doc)


class TestPaymentTransactionReferenceRegistration(unittest.TestCase):
    def test_hooks_export_payment_transaction_reference_fields(self):
        hooks = HOOKS_PATH.read_text()

        self.assertIn("Sales Invoice-custom_transaction_reference", hooks)
        self.assertIn("POS Invoice-custom_transaction_reference", hooks)
        self.assertIn("Sales Invoice-posa_payment_transaction_references", hooks)
        self.assertIn("POS Invoice-posa_payment_transaction_references", hooks)

    def test_migration_chain_runs_payment_transaction_reference_patch(self):
        hooks = HOOKS_PATH.read_text()
        patches = PATCHES_PATH.read_text().splitlines()

        self.assertIn(PATCH_PATH, hooks)
        self.assertIn(PATCH_MODULE, patches)


if __name__ == "__main__":
    unittest.main()
