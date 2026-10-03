from concurrent.futures import ThreadPoolExecutor
from datetime import date, time, timedelta
from decimal import Decimal
from unittest import skipUnless
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import DatabaseError, connection, connections, transaction
from django.db.models.query import QuerySet
from django.test import TestCase, TransactionTestCase, skipUnlessDBFeature
from django.urls import reverse

from accounts.models import UserProfile
from coordinators.models import CoordinationLog
from core.models import AuditLog
from invoices import views
from invoices.models import Invoice, InvoiceLine, InvoiceSettings
from invoices.tests_invoices import create_coordinator_user
from participants.models import Participant
from scheduling.models import SupportItem


class SupportCoordinationInvoiceRaceFixture:
    def setUp(self):
        super().setUp()
        self.admin = get_user_model().objects.create_user(username="sc-race-admin")
        UserProfile.objects.create(user=self.admin, role=UserProfile.Role.ADMIN)
        self.coordinator = create_coordinator_user("sc-race-coordinator")
        self.participant = Participant.objects.create(
            first_name="Ava", last_name="Nguyen", status=Participant.Status.ACTIVE,
        )
        self.support_item = SupportItem.objects.create(
            item_number="07_002_0106_8_3",
            name="Support coordination",
            unit=SupportItem.Unit.HOUR,
            price_limit=Decimal("100.00"),
            gst_code=SupportItem.GSTCode.GST_FREE,
            is_active=True,
        )
        self.settings = InvoiceSettings.load()
        self.initial_sequence = self.settings.next_invoice_sequence
        self.log = self.create_log()
        self.client.force_login(self.admin)
        self.url = reverse("support_coordination_invoice_create")

    def create_log(self, **overrides):
        values = {
            "participant": self.participant,
            "coordinator": self.coordinator,
            "service_date": date(2026, 10, 2),
            "start_time": time(9),
            "end_time": time(10, 30),
            "actual_hours": Decimal("1.50"),
            "case_notes": "Approved coordination work.",
            "status": CoordinationLog.Status.APPROVED,
        }
        values.update(overrides)
        return CoordinationLog.objects.create(**values)

    def post_invoice(self, logs=None, *, selected=True):
        data = {
            "participant": self.participant.pk,
            "period_start": "2026-10-01",
            "period_end": "2026-10-03",
            "support_item": self.support_item.pk,
        }
        if selected:
            data["coordination_log_ids"] = [log.pk for log in (logs or [self.log])]
        return self.client.post(self.url, data)

    def post_with_race(self, change, logs=None, *, selected=True):
        if selected:
            selector = views.get_selected_billable_coordination_logs

            def select_then_change(*args, **kwargs):
                result = selector(*args, **kwargs)
                change()
                return result

            name = "get_selected_billable_coordination_logs"
        else:
            selector = views.get_billable_coordination_logs

            def select_then_change(*args, **kwargs):
                # Keep the query lazy: only the POST's consumed selection changes.
                yield from list(selector(*args, **kwargs))
                change()

            name = "get_billable_coordination_logs"
        with patch.object(views, name, side_effect=select_then_change):
            return self.post_invoice(logs, selected=selected)

    def revise_log(self):
        CoordinationLog.objects.filter(pk=self.log.pk).update(
            status=CoordinationLog.Status.SUBMITTED,
            actual_hours=Decimal("2.00"),
            case_notes="Revised and resubmitted.",
            updated_at=self.log.updated_at + timedelta(seconds=1),
        )

    def invoice_log_elsewhere(self, log):
        invoice = Invoice.objects.create(
            participant=self.participant,
            period_start=log.service_date,
            period_end=log.service_date,
            invoice_type=Invoice.InvoiceType.SUPPORT_COORDINATION,
            created_by=self.admin,
        )
        InvoiceLine.objects.create_from_coordination_log(
            invoice=invoice, coordination_log=log, support_item=self.support_item,
        )
        return invoice

    def assert_no_new_invoice(self, *, existing_invoices=0):
        self.assertEqual(Invoice.objects.count(), existing_invoices)
        self.assertEqual(InvoiceLine.objects.count(), existing_invoices)
        self.assertFalse(AuditLog.objects.filter(
            action=AuditLog.Action.SUPPORT_COORDINATION_INVOICE_CREATED,
        ).exists())
        self.settings.refresh_from_db()
        self.assertEqual(
            self.settings.next_invoice_sequence,
            self.initial_sequence + existing_invoices,
        )

    def assert_race_rejected(self, response, *, existing_invoices=0):
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "no longer available for invoicing")
        self.assertFalse(response.context["coordination_logs"])
        self.assert_no_new_invoice(existing_invoices=existing_invoices)


class SupportCoordinationInvoiceRaceTests(
    SupportCoordinationInvoiceRaceFixture, TestCase,
):
    def release_with_competing_release(self, after_release):
        invoice = self.invoice_log_elsewhere(self.log)
        self.log.status = CoordinationLog.Status.INVOICED
        self.log.save()
        fetch_all = QuerySet._fetch_all
        raced = []

        def release_between_selection_and_lock(queryset):
            fresh = queryset._result_cache is None
            result = fetch_all(queryset)
            related = queryset.query.select_related
            selects_coordination_logs = (
                isinstance(related, dict) and "coordination_log" in related
            ) or queryset.query.values_select == ("coordination_log_id",)
            if fresh and not raced and queryset.model is InvoiceLine and selects_coordination_logs:
                raced.append(True)
                views.release_invoice_source_logs(invoice)
                after_release()
            return result

        with patch.object(QuerySet, "_fetch_all", release_between_selection_and_lock):
            views.release_invoice_source_logs(invoice)
        self.assertTrue(raced)

    def test_competing_release_cannot_approve_sc_revision(self):
        self.release_with_competing_release(self.revise_log)
        self.log.refresh_from_db()
        self.assertEqual(self.log.status, CoordinationLog.Status.SUBMITTED)
        self.assertEqual(self.log.actual_hours, Decimal("2.00"))

    def test_competing_release_cannot_release_log_from_new_invoice(self):
        new_invoices = []

        def reinvoice():
            self.log.refresh_from_db()
            new_invoices.append(self.invoice_log_elsewhere(self.log))
            self.log.status = CoordinationLog.Status.INVOICED
            self.log.save()

        self.release_with_competing_release(reinvoice)
        self.log.refresh_from_db()
        self.assertEqual(self.log.status, CoordinationLog.Status.INVOICED)
        self.assertEqual(self.log.invoice_lines.get().invoice_id, new_invoices[0].pk)

    def test_resubmission_after_selected_logs_are_loaded_aborts_invoice(self):
        response = self.post_with_race(self.revise_log)

        self.assert_race_rejected(response)
        self.log.refresh_from_db()
        self.assertEqual(self.log.status, CoordinationLog.Status.SUBMITTED)
        self.assertEqual(self.log.actual_hours, Decimal("2.00"))

    def test_approved_log_with_changed_timestamp_aborts_invoice(self):
        response = self.post_with_race(lambda: CoordinationLog.objects.filter(
            pk=self.log.pk,
        ).update(
            actual_hours=Decimal("2.00"),
            updated_at=self.log.updated_at + timedelta(seconds=1),
        ))

        self.assert_race_rejected(response)
        self.log.refresh_from_db()
        self.assertEqual(self.log.status, CoordinationLog.Status.APPROVED)

    def test_status_is_rechecked_even_without_timestamp_change(self):
        response = self.post_with_race(lambda: CoordinationLog.objects.filter(
            pk=self.log.pk,
        ).update(status=CoordinationLog.Status.SUBMITTED))

        self.assert_race_rejected(response)
        self.log.refresh_from_db()
        self.assertEqual(self.log.status, CoordinationLog.Status.SUBMITTED)

    def test_invoice_link_is_rechecked_even_when_log_still_approved(self):
        self.client.raise_request_exception = False
        response = self.post_with_race(lambda: self.invoice_log_elsewhere(self.log))

        self.assert_race_rejected(response, existing_invoices=1)
        self.assertEqual(InvoiceLine.objects.get().coordination_log_id, self.log.pk)
        self.log.refresh_from_db()
        self.assertEqual(self.log.status, CoordinationLog.Status.APPROVED)

    def test_participant_is_rechecked_even_without_timestamp_change(self):
        other_participant = Participant.objects.create(
            first_name="Ben", last_name="Taylor", status=Participant.Status.ACTIVE,
        )
        response = self.post_with_race(lambda: CoordinationLog.objects.filter(
            pk=self.log.pk,
        ).update(participant=other_participant))

        self.assert_race_rejected(response)

    def test_date_before_invoice_period_aborts_invoice(self):
        response = self.post_with_race(lambda: CoordinationLog.objects.filter(
            pk=self.log.pk,
        ).update(service_date=date(2026, 9, 30)))

        self.assert_race_rejected(response)

    def test_date_after_invoice_period_aborts_invoice(self):
        response = self.post_with_race(lambda: CoordinationLog.objects.filter(
            pk=self.log.pk,
        ).update(service_date=date(2026, 10, 4)))

        self.assert_race_rejected(response)

    def test_deleted_log_aborts_invoice_cleanly(self):
        self.client.raise_request_exception = False
        response = self.post_with_race(lambda: CoordinationLog.objects.filter(
            pk=self.log.pk,
        ).delete())

        self.assert_race_rejected(response)

    def test_one_revised_log_aborts_entire_selected_batch(self):
        unchanged = self.create_log(service_date=date(2026, 10, 1))
        original_updated_at = unchanged.updated_at
        response = self.post_with_race(self.revise_log, [unchanged, self.log])

        self.assert_race_rejected(response)
        unchanged.refresh_from_db()
        self.assertEqual(unchanged.status, CoordinationLog.Status.APPROVED)
        self.assertEqual(unchanged.updated_at, original_updated_at)

    def test_one_linked_log_aborts_entire_selected_batch_cleanly(self):
        unchanged = self.create_log(service_date=date(2026, 10, 1))
        original_updated_at = unchanged.updated_at
        self.client.raise_request_exception = False
        response = self.post_with_race(
            lambda: self.invoice_log_elsewhere(self.log), [unchanged, self.log],
        )

        self.assert_race_rejected(response, existing_invoices=1)
        unchanged.refresh_from_db()
        self.assertEqual(unchanged.status, CoordinationLog.Status.APPROVED)
        self.assertEqual(unchanged.updated_at, original_updated_at)
        self.assertFalse(unchanged.invoice_lines.exists())

    def test_period_selection_race_aborts_entire_invoice(self):
        unchanged = self.create_log(service_date=date(2026, 10, 1))
        response = self.post_with_race(self.revise_log, selected=False)

        self.assert_race_rejected(response)
        unchanged.refresh_from_db()
        self.assertEqual(unchanged.status, CoordinationLog.Status.APPROVED)

    def test_all_candidates_locked_by_pk_in_transaction_before_invoice_create(self):
        earlier_log = self.create_log(service_date=date(2026, 10, 1))
        atomic_depth = len(connection.atomic_blocks)
        locked_batches = []
        fetch_all = QuerySet._fetch_all
        create_invoice = Invoice.objects.create
        joined_lock_query = CoordinationLog.objects.select_related(
            "participant", "coordinator",
        ).select_for_update()

        def observe_fetch(queryset):
            locking = (
                queryset.model is CoordinationLog
                and queryset.query.select_for_update
                and queryset._result_cache is None
            )
            if locking:
                self.assertTrue(connection.in_atomic_block)
                self.assertGreater(len(connection.atomic_blocks), atomic_depth)
                self.assertEqual(queryset.query.order_by, ("pk",))
                self.assertFalse(queryset.query.select_related)
            result = fetch_all(queryset)
            if locking:
                locked_batches.append([log.pk for log in queryset._result_cache])
            return result

        def create_after_locks(**kwargs):
            self.assertEqual(locked_batches, [[self.log.pk, earlier_log.pk]])
            return create_invoice(**kwargs)

        with (
            patch.object(
                CoordinationLog.objects, "select_for_update",
                return_value=joined_lock_query,
            ),
            patch.object(QuerySet, "_fetch_all", observe_fetch),
            patch.object(Invoice.objects, "create", side_effect=create_after_locks),
        ):
            response = self.post_invoice([earlier_log, self.log])

        invoice = Invoice.objects.get()
        self.assertRedirects(response, invoice.get_absolute_url())
        self.assertEqual(invoice.lines.count(), 2)
        self.assertEqual(invoice.total_amount, Decimal("300.00"))

    def test_invoice_snapshots_refetched_objects_not_initial_instances(self):
        selector = views.get_selected_billable_coordination_logs

        def stale_in_memory_quantity(*args, **kwargs):
            logs, error = selector(*args, **kwargs)
            logs[0].actual_hours = Decimal("99.00")
            return logs, error

        with patch.object(
            views, "get_selected_billable_coordination_logs",
            side_effect=stale_in_memory_quantity,
        ):
            response = self.post_invoice()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(InvoiceLine.objects.get().quantity, Decimal("1.50"))

    def test_later_line_failure_rolls_back_invoice_lines_statuses_and_sequence(self):
        second_log = self.create_log(service_date=date(2026, 10, 3))
        create_line = InvoiceLine.objects.create_from_coordination_log
        created_lines = []

        def fail_second_line(**kwargs):
            if created_lines:
                raise RuntimeError("Simulated second line failure")
            line = create_line(**kwargs)
            created_lines.append(line.pk)
            return line

        with patch.object(
            InvoiceLine.objects, "create_from_coordination_log",
            side_effect=fail_second_line,
        ):
            with self.assertRaisesMessage(RuntimeError, "Simulated second line failure"):
                self.post_invoice([self.log, second_log])

        self.assertEqual(len(created_lines), 1)
        self.assert_no_new_invoice()
        for log in (self.log, second_log):
            original_updated_at = log.updated_at
            log.refresh_from_db()
            self.assertEqual(log.status, CoordinationLog.Status.APPROVED)
            self.assertEqual(log.updated_at, original_updated_at)

    def test_unchanged_period_selection_creates_invoice(self):
        response = self.post_invoice(selected=False)

        invoice = Invoice.objects.get()
        self.assertRedirects(response, invoice.get_absolute_url())
        self.assertEqual(invoice.invoice_type, Invoice.InvoiceType.SUPPORT_COORDINATION)
        self.assertEqual(invoice.total_amount, Decimal("150.00"))
        self.log.refresh_from_db()
        self.assertEqual(self.log.status, CoordinationLog.Status.INVOICED)


@skipUnless(connection.vendor == "postgresql", "Requires PostgreSQL row locks")
class SupportCoordinationInvoicePostgresLockTests(
    SupportCoordinationInvoiceRaceFixture, TransactionTestCase,
):
    @skipUnlessDBFeature("has_select_for_update", "has_select_for_update_nowait")
    def test_invoice_lock_blocks_revision_until_snapshot_is_created(self):
        create_invoice = Invoice.objects.create

        def attempt_revision():
            try:
                with transaction.atomic():
                    log = CoordinationLog.objects.select_for_update(nowait=True).get(
                        pk=self.log.pk,
                    )
                    log.status = CoordinationLog.Status.SUBMITTED
                    log.save(update_fields=["status", "updated_at"])
                return None
            except DatabaseError as error:
                cause = error.__cause__
                return getattr(cause, "sqlstate", None) or getattr(cause, "pgcode", None)
            finally:
                connections["default"].close()

        def create_with_contending_revision(**kwargs):
            # A separate connection must see a real lock conflict, not a test mock.
            with ThreadPoolExecutor(max_workers=1) as executor:
                sqlstate = executor.submit(attempt_revision).result(timeout=10)
            self.assertEqual(sqlstate, "55P03")  # PostgreSQL lock_not_available.
            return create_invoice(**kwargs)

        with patch.object(
            Invoice.objects, "create", side_effect=create_with_contending_revision,
        ):
            response = self.post_invoice()

        invoice = Invoice.objects.get()
        self.assertRedirects(response, invoice.get_absolute_url())
        self.assertEqual(invoice.lines.get().quantity, Decimal("1.50"))
        self.log.refresh_from_db()
        self.assertEqual(self.log.status, CoordinationLog.Status.INVOICED)
