import csv
from datetime import time
from decimal import Decimal
from io import StringIO
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from invoices.models import Invoice, InvoiceBillingAdjustment, InvoiceLine
from invoices import tests_billing_adjustments as fixtures
from service_logs.models import ServiceLog


class BillingDrawerTests(TestCase):
    setUp = fixtures.BillingAdjustmentTests.setUp
    create_user_with_role = fixtures.BillingAdjustmentTests.create_user_with_role
    create_service_log = fixtures.BillingAdjustmentTests.create_service_log
    create_travel_support_item = fixtures.BillingAdjustmentTests.create_travel_support_item
    prepare = fixtures.BillingAdjustmentTests.prepare
    submit = fixtures.BillingAdjustmentTests.submit

    def payload(self, log, **changes):
        changes.setdefault("source_version", log.updated_at.isoformat())
        return fixtures.BillingAdjustmentTests.payload(self, log, **changes)

    def correction(self, **kwargs):
        return dict(correct_time="on", actual_start_time="09:00", actual_end_time="10:45",
                    break_minutes="0", reason="incorrect_time", **kwargs)

    def test_time_correction_updates_log_and_invoice_but_not_roster(self):
        log, _ = self.prepare("25")
        response = self.submit(log, **self.correction())
        self.assertEqual(response.status_code, 302)
        log.refresh_from_db()
        self.assertEqual(log.actual_end_time, time(10, 45))
        self.assertEqual(log.actual_hours, Decimal("1.75"))
        self.assertEqual(log.shift.end_time, time(11))
        self.assertEqual(log.kilometres, Decimal("25"))
        line = InvoiceLine.objects.get()
        self.assertEqual(line.quantity, Decimal("1.75"))
        self.assertEqual(line.line_total, Decimal("114.57"))
        history = InvoiceBillingAdjustment.objects.get()
        self.assertEqual(history.original_values["actual_end_time"], "11:00:00")
        self.assertEqual(history.billing_values["actual_end_time"], "10:45:00")
        self.assertEqual(history.original_values["hours"], "2.00")
        self.assertEqual(history.created_by, self.admin_user)

    def test_invalid_or_incomplete_time_corrections_are_rejected(self):
        log, _ = self.prepare()
        for invalid in ({"actual_end_time": "08:00"}, {"actual_end_time": ""},
                        {"break_minutes": "105"}, {"break_minutes": "-1"},
                        {"reason": ""}):
            data = self.correction()
            data.update(invalid)
            with self.subTest(invalid=invalid):
                self.assertEqual(self.submit(log, **data).status_code, 200)
                self.assertFalse(Invoice.objects.exists())
                log.refresh_from_db()
                self.assertEqual(log.actual_hours, Decimal("2.00"))

    def test_time_correction_is_opt_in_and_legacy_hours_preserved(self):
        log, _ = self.prepare()
        ServiceLog.objects.filter(pk=log.pk).update(actual_hours=Decimal("2.25"))
        response = self.submit(log, actual_end_time="10:45", break_minutes="0")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(InvoiceLine.objects.get().quantity, Decimal("2.25"))
        self.assertFalse(InvoiceBillingAdjustment.objects.exists())

    def test_accountant_cannot_forge_time_correction(self):
        log, _ = self.prepare()
        self.client.force_login(self.accountant_user)
        self.assertEqual(self.submit(log, **self.correction()).status_code, 403)
        self.assertFalse(Invoice.objects.exists())

    def test_history_failure_rolls_back_time_changes(self):
        log, _ = self.prepare()
        with patch("invoices.billing.InvoiceBillingAdjustment.objects.create", side_effect=RuntimeError("audit")):
            with self.assertRaises(RuntimeError):
                self.submit(log, **self.correction())
        log.refresh_from_db()
        self.assertEqual(log.actual_end_time, time(11))
        self.assertEqual(log.status, ServiceLog.Status.APPROVED)
        self.assertFalse(Invoice.objects.exists())

    def test_stale_source_version_does_not_overwrite_newer_log(self):
        log, _ = self.prepare()
        response = self.submit(log, **self.correction(source_version="2000-01-01T00:00:00+00:00"))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Invoice.objects.exists())

    def test_missing_or_blank_source_version_rejects_time_correction(self):
        log, _ = self.prepare()
        for value in (None, ""):
            data = self.payload(log, **self.correction())
            if value is None:
                data.pop(f"adjustment-{log.pk}-source_version")
            else:
                data[f"adjustment-{log.pk}-source_version"] = value
            response = self.client.post(reverse("invoice_create"), data)
            self.assertEqual(response.status_code, 200)
            self.assertFalse(Invoice.objects.exists())

    def test_corrected_time_and_audit_survive_draft_deletion(self):
        log, _ = self.prepare()
        self.submit(log, **self.correction())
        invoice = Invoice.objects.get()
        self.client.post(reverse("invoice_delete", args=[invoice.pk]))
        log.refresh_from_db()
        self.assertEqual(log.actual_hours, Decimal("1.75"))
        self.assertEqual(log.status, ServiceLog.Status.APPROVED)
        self.assertIsNone(InvoiceBillingAdjustment.objects.get().invoice_id)
        self.submit(log)
        self.assertEqual(InvoiceLine.objects.get().quantity, Decimal("1.75"))

    def test_time_item_km_and_claim_corrections_are_applied_together(self):
        log, item = self.prepare("25")
        changes = self.correction(support_item=item.pk, kilometres="30")
        changes["reason"] = "multiple"
        response = self.submit(log, claim="20", **changes)
        self.assertEqual(response.status_code, 302)
        log.refresh_from_db()
        self.assertEqual(log.actual_hours, Decimal("1.75"))
        self.assertEqual(log.kilometres, Decimal("25"))
        self.assertNotEqual(log.support_item_id, item.pk)
        self.assertEqual(Invoice.objects.get().total_amount, Decimal("142.50"))
        history = InvoiceBillingAdjustment.objects.get()
        self.assertEqual(history.billing_values["kilometres"], "30")

    def test_time_correction_and_audit_survive_invoice_cancellation(self):
        log, _ = self.prepare()
        self.submit(log, **self.correction())
        invoice = Invoice.objects.get()
        self.client.post(reverse("invoice_cancel", args=[invoice.pk]))
        log.refresh_from_db()
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, Invoice.Status.CANCELLED)
        self.assertEqual(log.status, ServiceLog.Status.APPROVED)
        self.assertEqual(log.actual_hours, Decimal("1.75"))
        self.assertEqual(InvoiceBillingAdjustment.objects.get().invoice_id, invoice.pk)

    def test_unchanged_km_without_drawer_submission_retains_manual_claim(self):
        log, _ = self.prepare("25")
        self.assertEqual(self.submit(log, claim="20").status_code, 302)
        self.assertEqual(Invoice.objects.get().total_amount, Decimal("150.94"))
        self.assertFalse(InvoiceBillingAdjustment.objects.exists())

    def test_both_previews_have_drawer_rate_and_single_claim_input(self):
        log, _ = self.prepare("25")
        for selected in (True, False):
            data = self.payload(log)
            if not selected:
                data.pop("service_log_ids")
            response = self.client.get(reverse("invoice_create"), data)
            self.assertContains(response, 'data-billing-open')
            self.assertContains(response, 'class="lucide lucide-sliders-horizontal"', count=1)
            self.assertContains(response, f'aria-label="Adjust log {log.pk}"')
            self.assertContains(response, 'title="Adjust billing details"')
            self.assertContains(response, 'data-billing-drawer')
            self.assertContains(response, 'Rate / hr')
            self.assertContains(response, f'name="travel-{log.pk}-amount"', count=1)
            self.assertContains(response, f'name="adjustment-{log.pk}-kilometres"', count=1)

    def test_preview_preserves_configured_travel_price_including_zero(self):
        log, _ = self.prepare("25")
        from scheduling.models import SupportItem
        from invoices.views import TRAVEL_SUPPORT_ITEM_NUMBER

        travel = SupportItem.objects.get(item_number=TRAVEL_SUPPORT_ITEM_NUMBER)
        for price in (Decimal("0.00"), Decimal("1.25")):
            travel.price_limit = price
            travel.save(update_fields=["price_limit"])
            response = self.client.get(reverse("invoice_create"), self.payload(log))
            self.assertEqual(response.context["travel_unit_price"], price)

    def test_accountant_zero_km_keeps_claim_input_hidden(self):
        log, _ = self.prepare()
        self.client.force_login(self.accountant_user)
        response = self.client.get(reverse("invoice_create"), self.payload(log))
        self.assertNotContains(response, f'name="travel-{log.pk}-amount"')
        self.assertContains(response, "No travel recorded")

    def test_corrected_hours_use_existing_csv_and_pdf_exports(self):
        log, _ = self.prepare()
        self.submit(log, **self.correction())
        invoice = Invoice.objects.get()
        csv_response = self.client.get(reverse("invoice_csv", args=[invoice.pk]))
        rows = list(csv.DictReader(StringIO(csv_response.content.decode("utf-8"))))
        self.assertEqual(rows[0]["quantity"], "1.75")
        self.assertEqual(rows[0]["line_total"], "114.57")
        pdf_response = self.client.get(reverse("invoice_pdf", args=[invoice.pk]))
        self.assertEqual(pdf_response["Content-Type"], "application/pdf")
        self.assertTrue(pdf_response.content.startswith(b"%PDF"))
        self.assertIn(b"$114.57", pdf_response.content)
