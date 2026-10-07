from datetime import date, datetime, time, timezone as datetime_timezone
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext

from invoices.models import Invoice, InvoiceBillingAdjustment, InvoiceLine
from participants.models import Participant
from scheduling.models import ParticipantCancellation, Shift, SupportItem
from scheduling.planner_billing import billing_detail, billing_summary, with_billing_relations
from service_logs.models import ServiceLog
from workers.models import SupportWorker


NOW = datetime(2026, 10, 2, 8, tzinfo=datetime_timezone.utc)


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class PlannerBillingDataTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_user(username="projection-admin")
        worker_user = get_user_model().objects.create_user(username="projection-worker")
        cls.worker = SupportWorker.objects.create(
            user=worker_user, first_name="Demo", last_name="Worker",
            email="projection@example.com",
        )
        cls.participant = Participant.objects.create(first_name="Demo", last_name="Person")
        cls.item = SupportItem.objects.create(
            item_number="01_011_0107_1_1", name="Original service",
            unit=SupportItem.Unit.HOUR, price_limit=Decimal("65.00"),
        )

    def shift(self, **overrides):
        values = {
            "participant": self.participant, "worker": self.worker,
            "service_date": date(2026, 10, 1), "start_time": time(9),
            "end_time": time(12), "planned_hours": Decimal("2.50"),
            "break_minutes": 30, "support_item": self.item,
            "service_type": Shift.ServiceType.PERSONAL_CARE,
            "status": Shift.Status.CONFIRMED, "created_by": self.admin,
        }
        values.update(overrides)
        return Shift.objects.create(**values)

    def log(self, shift=None, **overrides):
        values = {
            "actual_start_time": time(9), "actual_end_time": time(12, 10),
            "break_minutes": 30, "actual_hours": Decimal("2.67"),
            "kilometres": Decimal("12.00"), "case_notes": "Original notes",
            "status": ServiceLog.Status.APPROVED,
        }
        values.update(overrides)
        return ServiceLog.objects.create_from_shift(shift or self.shift(), **values)

    def cancellation(self, shift, status=ParticipantCancellation.Status.PENDING):
        return ParticipantCancellation.objects.create(
            shift=shift, cancellation_type=ParticipantCancellation.CancellationType.SHORT_NOTICE,
            reason=ParticipantCancellation.Reason.HEALTH, details="Original report",
            received_at=NOW, previous_shift_status=Shift.Status.CONFIRMED,
            submitted_by=self.admin, status=status,
        )

    def invoice(self, status=Invoice.Status.ISSUED):
        return Invoice.objects.create(
            invoice_number=f"PROJECTION-{Invoice.objects.count() + 1}",
            participant=self.participant, period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 31), created_by=self.admin, status=status,
        )

    def line(self, invoice, log=None, cancellation=None, **overrides):
        values = {
            "invoice": invoice, "service_log": log,
            "participant_cancellation": cancellation,
            "line_type": InvoiceLine.LineType.CANCELLATION if cancellation else InvoiceLine.LineType.SERVICE,
            "support_item_number": "SNAPSHOT-ITEM", "description": "Billed service snapshot",
            "unit": "hour", "unit_price": Decimal("70.00"),
            "quantity": Decimal("2.67"), "line_total": Decimal("186.90"),
            "gst_code": "gst_free",
        }
        values.update(overrides)
        return InvoiceLine.objects.create(**values)

    def adjustment(self, log, invoice, km="20.00"):
        return InvoiceBillingAdjustment.objects.create(
            service_log=log, invoice=invoice, invoice_number=invoice.invoice_number,
            original_values={"kilometres": "12.00"}, billing_values={"kilometres": km},
            reason="Confirmed distance", created_by=self.admin,
        )

    def projected(self, shift, detail=False):
        return with_billing_relations(Shift.objects.filter(pk=shift.pk), detail=detail).get()

    def summary(self, shift):
        result = billing_summary(self.projected(shift), now=NOW)
        self.assertEqual(set(result), {"key", "label", "tone"})
        self.assertTrue(result["label"])
        self.assertTrue(result["tone"])
        return result["key"]

    def detail(self, shift):
        return billing_detail(self.projected(shift, detail=True), now=NOW)

    def test_missing_only_for_ended_published_or_confirmed_scheduled_shifts(self):
        for status in (Shift.Status.PUBLISHED, Shift.Status.CONFIRMED):
            with self.subTest(status=status):
                self.assertEqual(self.summary(self.shift(status=status)), "missing")
        for status, expected in (
            (Shift.Status.DRAFT, "not_due"), (Shift.Status.CANCELLED, "cancelled"),
            (Shift.Status.COMPLETED, "check"), (Shift.Status.NO_SHOW, "check"),
            (Shift.Status.CANCELLATION_REVIEW, "cancelreview"),
        ):
            with self.subTest(status=status):
                self.assertEqual(self.summary(self.shift(status=status)), expected)
        self.assertEqual(self.summary(self.shift(source=Shift.Source.UNSCHEDULED)), "check")

    def test_future_and_in_progress_shifts_are_not_missing(self):
        for values, expected in (
            ({"service_date": date(2026, 10, 3)}, "upcoming"),
            ({"service_date": date(2026, 10, 2), "start_time": time(19), "end_time": time(20)}, "upcoming"),
            ({"service_date": date(2026, 10, 2), "end_time": time(18, 1)}, "not_due"),
            ({"service_date": date(2026, 10, 2), "end_time": time(18)}, "missing"),
        ):
            with self.subTest(values=values):
                self.assertEqual(self.summary(self.shift(**values)), expected)

    def test_missing_boundary_uses_local_date_and_default_clock(self):
        shift = self.shift(service_date=date(2026, 10, 2), start_time=time(0), end_time=time(0, 10))
        instant = datetime(2026, 10, 1, 14, 15, tzinfo=datetime_timezone.utc)
        self.assertEqual(billing_summary(self.projected(shift), now=instant)["key"], "missing")
        with patch("django.utils.timezone.now", return_value=instant):
            self.assertEqual(billing_summary(self.projected(shift))["key"], "missing")

    def test_log_statuses_and_orphaned_invoiced_log(self):
        for status, expected in (
            (ServiceLog.Status.SUBMITTED, "review"), (ServiceLog.Status.APPROVED, "ready"),
            (ServiceLog.Status.REJECTED, "rejected"), (ServiceLog.Status.INVOICED, "check"),
        ):
            with self.subTest(status=status):
                log = self.log(status=status)
                self.assertEqual(self.summary(log.shift), expected)
                self.assertEqual(self.detail(log.shift)["actual_hours"], log.actual_hours)

    def test_cancellation_states_override_missing_and_suppress_actual_hours(self):
        for status, expected in (
            (ParticipantCancellation.Status.PENDING, "cancelreview"),
            (ParticipantCancellation.Status.APPROVED, "ready"),
            (ParticipantCancellation.Status.WAIVED, "nocharge"),
        ):
            with self.subTest(status=status):
                shift = self.shift()
                cancellation = self.cancellation(shift, status)
                self.assertEqual(self.summary(shift), expected)
                detail = self.detail(shift)
                self.assertEqual(detail["cancellation"], cancellation)
                self.assertIsNone(detail["actual_hours"])
                self.assertIsNone(detail["difference_minutes"])
                self.assertIsNone(detail["log"])

    def test_active_cancellation_with_any_service_log_requires_check(self):
        for cancellation_status in (
            ParticipantCancellation.Status.PENDING,
            ParticipantCancellation.Status.APPROVED,
            ParticipantCancellation.Status.WAIVED,
        ):
            for log_status, _ in ServiceLog.Status.choices:
                with self.subTest(cancellation=cancellation_status, log=log_status):
                    log = self.log(status=log_status)
                    cancellation = self.cancellation(log.shift, cancellation_status)
                    self.assertEqual(self.summary(log.shift), "check")
                    detail = self.detail(log.shift)
                    self.assertEqual(detail["summary"]["key"], "check")
                    self.assertEqual(detail["cancellation"], cancellation)
                    self.assertEqual(detail["log"], log)
                    self.assertIsNone(detail["actual_hours"])
                    self.assertIsNone(detail["difference_minutes"])

    def test_invoiced_cancellation_with_unbilled_service_log_requires_check(self):
        for status in (Invoice.Status.DRAFT, Invoice.Status.ISSUED, Invoice.Status.PAID):
            with self.subTest(status=status):
                log = self.log()
                cancellation = self.cancellation(log.shift, ParticipantCancellation.Status.APPROVED)
                line = self.line(self.invoice(status), cancellation=cancellation)
                self.assertEqual(self.summary(log.shift), "check")
                detail = self.detail(log.shift)
                self.assertEqual(detail["summary"]["key"], "check")
                self.assertEqual(detail["invoices"][0]["lines"], [line])
                self.assertIsNone(detail["actual_hours"])
                self.assertIsNone(detail["difference_minutes"])

    def test_rejected_cancellation_does_not_conflict_with_any_service_log_status(self):
        for log_status, expected in (
            (ServiceLog.Status.SUBMITTED, "review"),
            (ServiceLog.Status.APPROVED, "ready"),
            (ServiceLog.Status.REJECTED, "rejected"),
            (ServiceLog.Status.INVOICED, "check"),
        ):
            with self.subTest(status=log_status):
                log = self.log(status=log_status)
                cancellation = self.cancellation(log.shift, ParticipantCancellation.Status.REJECTED)
                self.assertEqual(self.summary(log.shift), expected)
                detail = self.detail(log.shift)
                self.assertEqual(detail["cancellation"], cancellation)
                self.assertEqual(detail["actual_hours"], log.actual_hours)
                self.assertEqual(detail["difference_minutes"], 10)
                self.line(self.invoice(), log)
                self.assertEqual(self.summary(log.shift), "issued")

    def test_rejected_cancellation_falls_back_to_service_and_remains_visible(self):
        shift = self.shift()
        cancellation = self.cancellation(shift, ParticipantCancellation.Status.REJECTED)
        self.assertEqual(self.summary(shift), "missing")
        log = self.log(shift)
        self.assertEqual(self.summary(shift), "ready")
        detail = self.detail(shift)
        self.assertEqual(detail["cancellation"], cancellation)
        self.assertEqual(detail["actual_hours"], log.actual_hours)

    def test_all_active_invoice_statuses_override_invoiced_log_status(self):
        for status in (Invoice.Status.DRAFT, Invoice.Status.ISSUED, Invoice.Status.PAID):
            with self.subTest(status=status):
                log = self.log(status=ServiceLog.Status.INVOICED)
                self.line(self.invoice(status), log)
                self.assertEqual(self.summary(log.shift), status)

    def test_cancelled_invoice_does_not_make_orphaned_invoiced_log_ready(self):
        log = self.log(status=ServiceLog.Status.INVOICED)
        self.line(self.invoice(Invoice.Status.CANCELLED), log)
        self.assertEqual(self.summary(log.shift), "check")
        self.assertEqual(self.detail(log.shift)["invoices"], [])
        log.status = ServiceLog.Status.APPROVED
        log.save(update_fields=["status"])
        self.assertEqual(self.summary(log.shift), "ready")

    def test_approved_cancellation_invoice_uses_cancellation_line_snapshot(self):
        shift = self.shift(status=Shift.Status.CANCELLED)
        cancellation = self.cancellation(shift, ParticipantCancellation.Status.APPROVED)
        invoice = self.invoice()
        line = self.line(invoice, cancellation=cancellation, quantity=Decimal("2.00"), line_total=Decimal("140.00"))
        detail = self.detail(shift)
        self.assertEqual(detail["summary"]["key"], "issued")
        self.assertIsNone(detail["actual_hours"])
        self.assertEqual(detail["invoices"][0]["service_lines"], [line])
        self.assertEqual(detail["invoices"][0]["quantity"], Decimal("2.00"))

    def test_detail_schema_snapshots_and_shift_only_totals(self):
        log = self.log()
        invoice = self.invoice()
        service = self.line(invoice, log)
        travel = self.line(
            invoice, log, line_type=InvoiceLine.LineType.TRAVEL_NON_LABOUR,
            unit="each", quantity=Decimal("15.50"), unit_price=Decimal("1.00"),
            line_total=Decimal("15.50"),
        )
        self.line(invoice, self.log(), quantity=Decimal("9.00"), line_total=Decimal("630.00"))
        SupportItem.objects.filter(pk=self.item.pk).update(price_limit=Decimal("999.00"))
        detail = self.detail(log.shift)
        self.assertEqual(set(detail), {
            "shift", "summary", "log", "cancellation", "invoices", "rostered_hours",
            "actual_hours", "difference_minutes", "adjustments", "original_km",
            "confirmed_km", "confirmed_km_conflict",
        })
        row = detail["invoices"][0]
        self.assertEqual(set(row), {
            "invoice", "lines", "service_lines", "travel_lines", "quantity",
            "quantity_state", "total", "confirmed_km",
        })
        self.assertEqual(row["invoice"].invoice_number, invoice.invoice_number)
        self.assertEqual(row["invoice"].get_absolute_url(), invoice.get_absolute_url())
        self.assertEqual(row["lines"], [service, travel])
        self.assertEqual(row["service_lines"], [service])
        self.assertEqual(row["travel_lines"], [travel])
        self.assertEqual(row["quantity"], Decimal("2.67"))
        self.assertEqual(row["quantity_state"], "hour")
        self.assertEqual(row["total"], Decimal("202.40"))
        self.assertEqual(row["service_lines"][0].unit_price, Decimal("70.00"))
        self.assertEqual(detail["rostered_hours"], Decimal("2.50"))
        self.assertEqual(detail["actual_hours"], Decimal("2.67"))
        self.assertEqual(detail["difference_minutes"], 10)
        self.assertEqual(detail["log"].break_minutes, 30)
        self.assertEqual(detail["shift"].break_minutes, 30)

    def test_difference_minutes_rounds_stored_hours_and_can_be_negative(self):
        log = self.log(actual_hours=Decimal("2.33"))
        self.assertEqual(self.detail(log.shift)["difference_minutes"], -10)

    def test_non_hour_service_quantity_is_not_presented_as_hours(self):
        log = self.log()
        self.line(self.invoice(), log, unit="each")
        detail = self.detail(log.shift)
        self.assertEqual(detail["summary"]["key"], "check")
        row = detail["invoices"][0]
        self.assertIsNone(row["quantity"])
        self.assertEqual(row["quantity_state"], "non_hour")

    def test_non_hour_cancellation_invoice_requires_review_without_inventing_hours(self):
        shift = self.shift(status=Shift.Status.CANCELLED)
        cancellation = self.cancellation(shift, ParticipantCancellation.Status.APPROVED)
        self.line(self.invoice(), cancellation=cancellation, unit="each")
        detail = self.detail(shift)
        self.assertEqual(detail["summary"]["key"], "check")
        self.assertIsNone(detail["invoices"][0]["quantity"])
        self.assertIsNone(detail["actual_hours"])

    def test_travel_only_invoice_is_explicitly_missing_service_quantity(self):
        log = self.log()
        self.line(self.invoice(), log, line_type=InvoiceLine.LineType.TRAVEL_NON_LABOUR, unit="hour")
        detail = self.detail(log.shift)
        self.assertEqual(detail["summary"]["key"], "check")
        self.assertIsNone(detail["invoices"][0]["quantity"])
        self.assertEqual(detail["invoices"][0]["quantity_state"], "missing")

    def test_split_invoices_are_all_retained_and_mixed_statuses_need_check(self):
        log = self.log()
        service_invoice, travel_invoice = self.invoice(), self.invoice(Invoice.Status.DRAFT)
        self.line(service_invoice, log)
        self.line(travel_invoice, log, line_type=InvoiceLine.LineType.TRAVEL_NON_LABOUR, unit="each")
        detail = self.detail(log.shift)
        self.assertEqual(detail["summary"]["key"], "check")
        self.assertEqual([row["invoice"] for row in detail["invoices"]], [service_invoice, travel_invoice])
        travel_invoice.status = Invoice.Status.ISSUED
        travel_invoice.save(update_fields=["status"])
        self.assertEqual(self.summary(log.shift), "issued")

    def test_active_cancellation_and_service_invoices_require_check(self):
        log = self.log()
        cancellation = self.cancellation(log.shift, ParticipantCancellation.Status.APPROVED)
        invoice = self.invoice()
        self.line(invoice, log)
        self.line(invoice, cancellation=cancellation)
        self.assertEqual(self.summary(log.shift), "check")
        self.assertEqual(len(self.detail(log.shift)["invoices"][0]["service_lines"]), 2)

    def test_adjustments_only_for_this_log_and_its_active_linked_invoices(self):
        log = self.log()
        active = self.invoice()
        self.line(active, log)
        keep = self.adjustment(log, active)
        self.adjustment(log, self.invoice(Invoice.Status.CANCELLED), "90")
        self.adjustment(log, self.invoice(), "91")
        deleted = self.invoice(Invoice.Status.DRAFT)
        self.adjustment(log, deleted, "92")
        deleted.delete()
        self.adjustment(self.log(), active, "93")
        detail = self.detail(log.shift)
        self.assertEqual(detail["adjustments"], [keep])
        self.assertEqual(detail["original_km"], Decimal("12.00"))
        self.assertEqual(detail["confirmed_km"], Decimal("20.00"))
        self.assertEqual(detail["invoices"][0]["confirmed_km"], Decimal("20.00"))
        self.assertEqual(detail["invoices"][0]["total"], Decimal("186.90"))
        self.assertEqual(detail["log"].kilometres, Decimal("12.00"))

    def test_no_adjustment_means_no_confirmed_km_not_invented_confirmation(self):
        log = self.log()
        self.line(self.invoice(), log)
        detail = self.detail(log.shift)
        self.assertIsNone(detail["confirmed_km"])
        self.assertEqual(detail["original_km"], Decimal("12.00"))

    def test_latest_adjustment_per_invoice_and_conflicting_confirmed_km(self):
        log = self.log()
        first, second = self.invoice(), self.invoice()
        self.line(first, log)
        self.line(second, log, line_type=InvoiceLine.LineType.TRAVEL_NON_LABOUR)
        self.adjustment(log, first, "19")
        self.adjustment(log, first, "20")
        self.adjustment(log, second, "21")
        detail = self.detail(log.shift)
        self.assertEqual([row["confirmed_km"] for row in detail["invoices"]], [Decimal("20"), Decimal("21")])
        self.assertIsNone(detail["confirmed_km"])
        self.assertTrue(detail["confirmed_km_conflict"])

    def test_malformed_adjusted_km_is_not_exposed_as_a_numeric_value(self):
        for km in (None, "bad", "NaN", "Infinity", "-1", {}):
            with self.subTest(km=km):
                log = self.log()
                invoice = self.invoice()
                self.line(invoice, log)
                self.adjustment(log, invoice, km)
                self.assertIsNone(self.detail(log.shift)["confirmed_km"])

    def test_cancelled_or_deleted_draft_history_does_not_leak_into_rebilling(self):
        for deleted in (False, True):
            with self.subTest(deleted=deleted):
                log = self.log(status=ServiceLog.Status.INVOICED)
                old = self.invoice(Invoice.Status.DRAFT)
                self.line(old, log)
                self.adjustment(log, old, "88")
                if deleted:
                    old.delete()
                else:
                    old.lines.all().delete()
                    old.status = Invoice.Status.CANCELLED
                    old.save(update_fields=["status"])
                ServiceLog.objects.filter(pk=log.pk).update(status=ServiceLog.Status.APPROVED)
                self.assertEqual(self.summary(log.shift), "ready")
                self.assertEqual(self.detail(log.shift)["adjustments"], [])
                new = self.invoice()
                self.line(new, log)
                detail = self.detail(log.shift)
                self.assertEqual(detail["summary"]["key"], "issued")
                self.assertEqual([row["invoice"] for row in detail["invoices"]], [new])
                self.assertIsNone(detail["confirmed_km"])

    def test_summary_queries_are_bounded_and_do_not_fetch_adjustments(self):
        for _ in range(12):
            log = self.log()
            invoice = self.invoice()
            self.line(invoice, log)
            self.adjustment(log, invoice)
            self.cancellation(log.shift, ParticipantCancellation.Status.REJECTED)
        with CaptureQueriesContext(connection) as queries:
            summaries = [billing_summary(shift, now=NOW) for shift in with_billing_relations(Shift.objects.all())]
        self.assertEqual(len(summaries), 12)
        self.assertLessEqual(len(queries), 3)
        self.assertFalse(any("invoices_invoicebillingadjustment" in query["sql"].lower() for query in queries))

    def test_detail_queries_are_bounded_and_related_display_records_are_loaded(self):
        for _ in range(8):
            log = self.log()
            invoice = self.invoice()
            self.line(invoice, log)
            self.adjustment(log, invoice)
            self.cancellation(log.shift, ParticipantCancellation.Status.REJECTED)
        with CaptureQueriesContext(connection) as queries:
            for shift in with_billing_relations(Shift.objects.all(), detail=True):
                detail = billing_detail(shift, now=NOW)
                str(detail["shift"].participant)
                str(detail["shift"].worker)
                str(detail["shift"].support_item)
                str(detail["log"].support_item)
                str(detail["log"].worker)
                str(detail["log"].participant)
                for adjustment in detail["adjustments"]:
                    str(adjustment.created_by)
                    str(adjustment.invoice)
        self.assertLessEqual(len(queries), 4)

    def test_projection_is_read_only_and_plain_instances_are_supported(self):
        log = self.log()
        invoice = self.invoice()
        self.line(invoice, log)
        self.adjustment(log, invoice)
        original = ServiceLog.objects.values().get(pk=log.pk)
        with CaptureQueriesContext(connection) as queries:
            detail = billing_detail(Shift.objects.get(pk=log.shift_id), now=NOW)
        self.assertEqual(detail["summary"]["key"], "issued")
        self.assertTrue(all(query["sql"].lstrip().upper().startswith("SELECT") for query in queries))
        self.assertEqual(ServiceLog.objects.values().get(pk=log.pk), original)
