from datetime import date
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless
from unittest.mock import patch

from django.db import connection, connections
from django.test import TestCase, TransactionTestCase
from django.urls import reverse

from invoices import models
from invoices.models import Invoice, InvoiceLine
from invoices import tests_invoices as fixtures
from scheduling.models import SupportItem
from service_logs.models import ServiceLog


class BillingAdjustmentTests(TestCase):
    setUp = fixtures.InvoiceGenerationTests.setUp
    create_user_with_role = fixtures.InvoiceGenerationTests.create_user_with_role
    create_service_log = fixtures.InvoiceGenerationTests.create_service_log
    create_travel_support_item = fixtures.InvoiceGenerationTests.create_travel_support_item

    def prepare(self, km="0.00"):
        self.client.force_login(self.admin_user)
        log = self.create_service_log(kilometres=Decimal(km))
        item = SupportItem.objects.create(
            item_number="04_104_0125_6_1", name="Access Community Social and Rec Actv",
            unit=SupportItem.Unit.HOUR, price_limit=Decimal("70.00"), is_active=True,
        )
        self.create_travel_support_item()
        return log, item

    def payload(self, log, **changes):
        result = {
            "participant": log.participant_id, "period_start": "2026-06-01",
            "period_end": "2026-06-30", "service_log_ids": [log.id],
        }
        result.update({f"adjustment-{log.id}-{key}": value for key, value in changes.items()})
        return result

    def submit(self, log, claim=None, **changes):
        data = self.payload(log, **changes)
        if claim is not None:
            data[f"travel-{log.id}-amount"] = claim
        return self.client.post(reverse("invoice_create"), data)

    def test_admin_can_change_whole_service_item_without_changing_log(self):
        log, item = self.prepare()
        response = self.submit(log, support_item=item.pk, reason="service_changed")
        self.assertEqual(response.status_code, 302)
        line = InvoiceLine.objects.get()
        self.assertEqual(line.support_item_number, item.item_number)
        self.assertEqual(line.unit_price, Decimal("70.00"))
        self.assertEqual(line.quantity, Decimal("2.00"))
        self.assertEqual(line.line_total, Decimal("140.00"))
        log.refresh_from_db()
        self.assertEqual(log.support_item_id, self.support_item.id)
        self.assertEqual(log.shift.support_item_id, self.support_item.id)
        self.assertEqual(log.status, ServiceLog.Status.INVOICED)
        history = models.InvoiceBillingAdjustment.objects.get()
        self.assertEqual(history.original_values["item_number"], self.support_item.item_number)
        self.assertEqual(history.billing_values["item_number"], item.item_number)
        self.assertEqual(history.created_by, self.admin_user)

    def test_missing_km_can_be_confirmed_without_converting_km_into_money(self):
        log, item = self.prepare()
        response = self.submit(log, claim="15.50", support_item=item.pk, kilometres="20", reason="missing_km")
        self.assertEqual(response.status_code, 302)
        travel = InvoiceLine.objects.get(line_type=InvoiceLine.LineType.TRAVEL_NON_LABOUR)
        self.assertEqual(travel.quantity, Decimal("15.50"))
        self.assertEqual(travel.line_total, Decimal("15.50"))
        log.refresh_from_db()
        self.assertEqual(log.kilometres, Decimal("0.00"))
        history = models.InvoiceBillingAdjustment.objects.get()
        self.assertEqual(Decimal(history.billing_values["kilometres"]), Decimal("20"))

    def test_item_change_and_optional_empty_km_does_not_add_travel(self):
        log, item = self.prepare()
        self.submit(log, support_item=item.pk, kilometres="", reason="service_changed")
        self.assertEqual(InvoiceLine.objects.count(), 1)

    def test_legacy_admin_and_accountant_claims_are_unchanged(self):
        log, _ = self.prepare("48")
        self.client.force_login(self.accountant_user)
        response = self.submit(log, claim="35")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Invoice.objects.get().total_amount, Decimal("165.94"))

    def test_change_requires_reason_and_other_requires_details(self):
        log, item = self.prepare()
        for fields in ({"support_item": item.pk}, {"kilometres": "20"}, {"support_item": item.pk, "reason": "other"}):
            with self.subTest(fields=fields):
                response = self.submit(log, **fields)
                self.assertEqual(response.status_code, 200)
                self.assertFalse(Invoice.objects.exists())

    def test_other_reason_is_saved_with_details(self):
        log, item = self.prepare()
        self.submit(log, support_item=item.pk, reason="other", reason_details="Participant requested a community visit.")
        history = models.InvoiceBillingAdjustment.objects.get()
        self.assertIn("Participant requested", history.reason)

    def test_accountant_cannot_forge_adjustments(self):
        log, item = self.prepare("12")
        self.client.force_login(self.accountant_user)
        response = self.submit(log, support_item=item.pk, kilometres="20", reason="service_changed")
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Invoice.objects.exists())

    def test_inactive_and_non_hourly_items_are_rejected(self):
        log, item = self.prepare()
        for changes in ({"is_active": False}, {"is_active": True, "unit": SupportItem.Unit.EACH}):
            for name, value in changes.items():
                setattr(item, name, value)
            item.save()
            response = self.submit(log, support_item=item.pk, reason="service_changed")
            self.assertEqual(response.status_code, 200)
            self.assertFalse(Invoice.objects.exists())

    def test_invalid_km_and_unconfirmed_travel_are_rejected(self):
        log, _ = self.prepare()
        for km in ("-1", "abc", "0", ""):
            response = self.submit(log, claim="20", kilometres=km, reason="missing_km")
            self.assertEqual(response.status_code, 200)
            self.assertFalse(Invoice.objects.exists())

    def test_explicit_zero_km_does_not_allow_positive_claim(self):
        log, _ = self.prepare("48")
        response = self.submit(log, claim="20", kilometres="0", reason="corrected_km")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Invoice.objects.exists())
        self.assertContains(response, "Enter confirmed kilometres before adding a travel claim.")

    def test_noop_form_needs_no_reason_and_preserves_existing_claim(self):
        log, _ = self.prepare("48")
        response = self.submit(log, claim="30", support_item="", kilometres="48", reason="")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Invoice.objects.get().total_amount, Decimal("160.94"))
        self.assertFalse(models.InvoiceBillingAdjustment.objects.exists())

    def test_adjustment_history_survives_draft_deletion_and_is_not_reused(self):
        log, item = self.prepare()
        self.submit(log, support_item=item.pk, kilometres="20", reason="service_changed")
        invoice = Invoice.objects.get()
        number = invoice.invoice_number
        self.client.post(reverse("invoice_delete", args=[invoice.pk]))
        history = models.InvoiceBillingAdjustment.objects.get()
        self.assertIsNone(history.invoice_id)
        self.assertEqual(history.invoice_number, number)
        log.refresh_from_db()
        self.assertEqual(log.status, ServiceLog.Status.APPROVED)
        response = self.client.get(reverse("service_log_detail", args=[log.pk]))
        self.assertContains(response, number)
        self.submit(log)
        self.assertEqual(InvoiceLine.objects.get().support_item_number, self.support_item.item_number)

    def test_cancel_keeps_history_and_releases_original_log(self):
        log, item = self.prepare()
        self.submit(log, support_item=item.pk, reason="service_changed")
        invoice = Invoice.objects.get()
        self.client.post(reverse("invoice_cancel", args=[invoice.pk]))
        self.assertEqual(models.InvoiceBillingAdjustment.objects.count(), 1)
        log.refresh_from_db()
        self.assertEqual(log.status, ServiceLog.Status.APPROVED)
        self.assertEqual(log.support_item_id, self.support_item.pk)

    def test_duplicate_submission_does_not_create_second_invoice(self):
        log, item = self.prepare()
        self.submit(log, support_item=item.pk, reason="service_changed")
        response = self.submit(log, support_item=item.pk, reason="service_changed")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Invoice.objects.count(), 1)

    def test_empty_km_retains_recorded_km_and_manual_claim(self):
        log, item = self.prepare("48")
        response = self.submit(log, claim="25", support_item=item.pk, kilometres="", reason="service_changed")
        self.assertEqual(response.status_code, 302)
        history = models.InvoiceBillingAdjustment.objects.get()
        self.assertEqual(Decimal(history.billing_values["kilometres"]), Decimal("48"))
        self.assertEqual(Invoice.objects.get().total_amount, Decimal("165.00"))

    def test_posted_hours_and_rate_cannot_override_server_values(self):
        log, item = self.prepare()
        response = self.submit(log, support_item=item.pk, reason="service_changed", hours="99", unit_price="1")
        self.assertEqual(response.status_code, 302)
        line = InvoiceLine.objects.get()
        self.assertEqual(line.quantity, Decimal("2.00"))
        self.assertEqual(line.unit_price, Decimal("70.00"))

    def test_history_failure_rolls_back_invoice_lines_and_log_status(self):
        log, item = self.prepare()
        with patch("invoices.billing.InvoiceBillingAdjustment.objects.create", side_effect=RuntimeError("Test audit failure")):
            with self.assertRaises(RuntimeError):
                self.submit(log, claim="10", support_item=item.pk, kilometres="20", reason="service_changed")
        self.assertFalse(Invoice.objects.exists())
        self.assertFalse(InvoiceLine.objects.exists())
        self.assertFalse(models.InvoiceBillingAdjustment.objects.exists())
        log.refresh_from_db()
        self.assertEqual(log.status, ServiceLog.Status.APPROVED)

    def test_source_status_is_rechecked_inside_transaction(self):
        from invoices.billing import BillingRecordsChanged, create_service_invoice

        log, item = self.prepare()
        ServiceLog.objects.filter(pk=log.pk).update(status=ServiceLog.Status.REJECTED)
        with self.assertRaises(BillingRecordsChanged):
            create_service_invoice(
                actor=self.admin_user,
                form_data={"participant": log.participant, "period_start": log.service_date, "period_end": log.service_date},
                logs=[log], cancellations=[], data=self.payload(log, support_item=item.pk, reason="service_changed"),
                can_adjust=True, travel_item_number="04_799_0125_6_1",
            )
        self.assertFalse(Invoice.objects.exists())

    def test_invoice_keeps_preview_order_when_logs_were_created_out_of_date_order(self):
        self.client.force_login(self.accountant_user)
        later = self.create_service_log(service_date=date(2026, 6, 20))
        earlier = self.create_service_log(service_date=date(2026, 6, 1))
        data = self.payload(later)
        data["service_log_ids"] = [later.pk, earlier.pk]
        response = self.client.post(reverse("invoice_create"), data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(list(InvoiceLine.objects.order_by("pk").values_list("service_log_id", flat=True)), [earlier.pk, later.pk])

    def test_admin_preview_exposes_adjustment_but_accountant_does_not(self):
        log, _ = self.prepare()
        url = reverse("invoice_create")
        response = self.client.get(url, self.payload(log))
        self.assertContains(response, f'name="adjustment-{log.pk}-support_item"')
        self.assertContains(response, f'name="adjustment-{log.pk}-kilometres"')
        self.client.force_login(self.accountant_user)
        response = self.client.get(url, self.payload(log))
        self.assertNotContains(response, f'name="adjustment-{log.pk}-support_item"')


@skipUnless(connection.vendor == "postgresql", "Requires PostgreSQL row locks")
class BillingAdjustmentPostgresTests(TransactionTestCase):
    setUp = fixtures.InvoiceGenerationTests.setUp
    create_user_with_role = fixtures.InvoiceGenerationTests.create_user_with_role
    create_service_log = fixtures.InvoiceGenerationTests.create_service_log

    def test_competing_overlapping_selections_create_only_one_invoice(self):
        from invoices.billing import BillingRecordsChanged, create_service_invoice

        first = self.create_service_log()
        second = self.create_service_log(service_date=date(2026, 6, 2))
        models.InvoiceSettings.load()
        barrier = Barrier(2)

        def submit(logs):
            try:
                with connections["default"].cursor() as cursor:
                    cursor.execute("SET lock_timeout = '5s'")
                barrier.wait(timeout=10)
                try:
                    return create_service_invoice(
                        actor=self.admin_user,
                        form_data={"participant": self.participant, "period_start": date(2026, 6, 1), "period_end": date(2026, 6, 30)},
                        logs=logs, cancellations=[], data={}, can_adjust=True,
                        travel_item_number="04_799_0125_6_1",
                    ).pk
                except BillingRecordsChanged:
                    return None
            finally:
                connections["default"].close()

        with ThreadPoolExecutor(max_workers=2) as executor:
            attempts = [executor.submit(submit, logs) for logs in ([first, second], [second, first])]
            results = [attempt.result(timeout=20) for attempt in attempts]
        self.assertEqual(sum(result is not None for result in results), 1)
        self.assertEqual(Invoice.objects.count(), 1)
        self.assertEqual(InvoiceLine.objects.count(), 2)
