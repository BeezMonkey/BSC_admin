from datetime import date, datetime, time, timezone as datetime_timezone
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from accounts.models import UserProfile
from core.models import AuditLog
from invoices.models import Invoice
from participants.models import Participant
from scheduling.models import ParticipantCancellation, Shift, SupportItem
from service_logs.models import ServiceLog
from workers.models import SupportWorker


NOW = datetime(2026, 10, 2, 8, 0, tzinfo=datetime_timezone.utc)


class ServiceLogFollowUpTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_user(username="follow-up-admin")
        UserProfile.objects.create(user=cls.admin, role=UserProfile.Role.ADMIN)
        cls.worker_user = get_user_model().objects.create_user(username="follow-up-worker")
        UserProfile.objects.create(
            user=cls.worker_user,
            role=UserProfile.Role.SUPPORT_WORKER,
            is_active_worker=True,
        )
        cls.worker = SupportWorker.objects.create(
            user=cls.worker_user, first_name="Alex", last_name="Able",
            email="alex@example.com",
        )
        other_user = get_user_model().objects.create_user(username="follow-up-other")
        cls.other_worker = SupportWorker.objects.create(
            user=other_user, first_name="Blair", last_name="Baker",
            email="blair@example.com", status=SupportWorker.Status.INACTIVE,
        )
        cls.participant = Participant.objects.create(first_name="Demo", last_name="One")
        cls.other_participant = Participant.objects.create(first_name="Demo", last_name="Two")
        cls.item = SupportItem.objects.create(
            item_number="01_011_0107_1_1", name="Personal care",
            unit=SupportItem.Unit.HOUR, price_limit=Decimal("65.00"),
        )

    def setUp(self):
        self.client.force_login(self.admin)
        clock = patch("django.utils.timezone.now", return_value=NOW)
        clock.start()
        self.addCleanup(clock.stop)

    def shift(self, **overrides):
        values = {
            "participant": self.participant, "worker": self.worker,
            "service_date": date(2026, 10, 1), "start_time": time(9),
            "end_time": time(12), "planned_hours": Decimal("3.00"),
            "support_item": self.item, "service_type": Shift.ServiceType.PERSONAL_CARE,
            "status": Shift.Status.CONFIRMED, "created_by": self.admin,
        }
        values.update(overrides)
        return Shift.objects.create(**values)

    def log(self, shift=None, status=ServiceLog.Status.APPROVED, **shift_values):
        shift = shift or self.shift(status=Shift.Status.COMPLETED, **shift_values)
        return ServiceLog.objects.create_from_shift(
            shift, actual_start_time=shift.start_time, actual_end_time=shift.end_time,
            actual_hours=shift.planned_hours, case_notes="Demo completed service.",
            status=status,
        )

    def cancellation(self, shift=None, status=ParticipantCancellation.Status.APPROVED):
        return ParticipantCancellation.objects.create(
            shift=shift or self.shift(status=Shift.Status.CANCELLED),
            cancellation_type=ParticipantCancellation.CancellationType.SHORT_NOTICE,
            reason=ParticipantCancellation.Reason.HEALTH,
            details="Private cancellation details", received_at=NOW,
            previous_shift_status=Shift.Status.CONFIRMED, submitted_by=self.worker_user,
            status=status,
        )

    def page(self, **params):
        response = self.client.get(reverse("service_log_list"), params)
        self.assertEqual(response.status_code, 200)
        return response

    def missing_ids(self, response):
        return [
            shift.id
            for group in response.context["missing_log_groups"]
            for shift in group["shifts"]
        ]

    def test_worker_filter_scopes_logs_and_approved_cancellations(self):
        keep_log = self.log()
        self.log(worker=self.other_worker)
        self.log(participant=self.other_participant)
        self.log(service_date=date(2026, 9, 30))
        keep_cancel = self.cancellation()
        self.cancellation(self.shift(worker=self.other_worker, status=Shift.Status.CANCELLED))
        response = self.page(
            worker=self.worker.id, participant=self.participant.id, status="approved",
            date_range="custom", date_from="2026-10-01", date_to="2026-10-01",
        )
        self.assertEqual(
            {(row["kind"], row["id"]) for row in response.context["billing_rows"]},
            {("service_log", keep_log.id), ("cancellation", keep_cancel.id)},
        )
        self.assertEqual(response.context["filtered_record_count"], 2)
        self.assertEqual(response.context["filtered_hours"], "6")

    def test_inactive_workers_remain_available_for_history(self):
        old_log = self.log(worker=self.other_worker)
        response = self.page(worker=self.other_worker.id)
        self.assertEqual(list(response.context["service_logs"]), [old_log])
        self.assertIn(self.other_worker, response.context["workers"])
        self.assertEqual(response.context["selected_worker_id"], str(self.other_worker.id))

    def test_invalid_worker_does_not_broaden_any_query(self):
        self.log()
        self.cancellation()
        self.shift()
        for value in ("99999", "invalid", "-1", "999999999999999999999999"):
            with self.subTest(value=value):
                response = self.page(worker=value, status="approved")
                self.assertEqual(response.context["filtered_record_count"], 0)
                self.assertEqual(response.context.get("missing_log_count"), 0)
                self.assertTrue(response.context["has_filters"])

    def test_status_sort_pagination_and_return_links_keep_worker_filter(self):
        for _ in range(21):
            self.log()
        response = self.page(worker=self.worker.id, status="approved", sort="date", page=2)
        for card in response.context["status_overview"]:
            self.assertIn(f"worker={self.worker.id}", card["url"])
        self.assertIn(f"worker={self.worker.id}", response.context["sorting"]["links"]["date"])
        self.assertIn(f"worker={self.worker.id}", response.context["pagination"]["page_query"])
        self.assertIn(f"worker={self.worker.id}", response.context["current_list_url"])
        self.assertEqual(response.context["clear_filter_url"], "/service-logs/?status=approved")

    def test_only_ended_scheduled_shifts_with_no_log_are_missing(self):
        past = self.shift(status=Shift.Status.PUBLISHED)
        ended = self.shift(service_date=date(2026, 10, 2), end_time=time(17, 59))
        boundary = self.shift(service_date=date(2026, 10, 2), end_time=time(18))
        self.shift(service_date=date(2026, 10, 2), end_time=time(18, 1))
        self.shift(service_date=date(2026, 10, 3))
        self.shift(source=Shift.Source.UNSCHEDULED)
        for status in (
            Shift.Status.DRAFT, Shift.Status.CANCELLED, Shift.Status.NO_SHOW,
            Shift.Status.CANCELLATION_REVIEW, Shift.Status.COMPLETED,
        ):
            self.shift(status=status)
        response = self.page()
        self.assertEqual(response.context.get("missing_log_count"), 3)
        self.assertCountEqual(self.missing_ids(response), [past.id, ended.id, boundary.id])

    def test_end_boundary_uses_brisbane_date_not_utc_date(self):
        previous_evening = self.shift(service_date=date(2026, 10, 1), end_time=time(23))
        after_midnight = self.shift(service_date=date(2026, 10, 2), start_time=time(0), end_time=time(0, 10))
        self.shift(service_date=date(2026, 10, 2), start_time=time(0), end_time=time(0, 20))
        with patch("django.utils.timezone.now", return_value=datetime(2026, 10, 1, 14, 15, tzinfo=datetime_timezone.utc)):
            response = self.page()
        self.assertCountEqual(self.missing_ids(response), [previous_evening.id, after_midnight.id])

    def test_any_existing_log_excludes_shift_including_rejected(self):
        for status, _ in ServiceLog.Status.choices:
            self.log(self.shift(), status=status)
        response = self.page()
        self.assertEqual(response.context.get("missing_log_count"), 0)
        self.assertContains(response, "No unsubmitted logs in the current filters.")

    def test_active_cancellation_reports_are_excluded_but_rejected_can_return(self):
        for status in (
            ParticipantCancellation.Status.PENDING, ParticipantCancellation.Status.APPROVED,
            ParticipantCancellation.Status.WAIVED,
        ):
            self.cancellation(self.shift(), status=status)
        restored = self.shift()
        self.cancellation(restored, status=ParticipantCancellation.Status.REJECTED)
        response = self.page()
        self.assertEqual(response.context.get("missing_log_count"), 1)
        self.assertEqual(self.missing_ids(response), [restored.id])

    def test_missing_scope_uses_worker_participant_and_inclusive_service_dates(self):
        first = self.shift(service_date=date(2026, 9, 28))
        last = self.shift(service_date=date(2026, 9, 30))
        self.shift(service_date=date(2026, 9, 27))
        self.shift(service_date=date(2026, 10, 1))
        self.shift(service_date=date(2026, 9, 29), worker=self.other_worker)
        self.shift(service_date=date(2026, 9, 29), participant=self.other_participant)
        response = self.page(
            worker=self.worker.id, participant=self.participant.id,
            date_range="custom", date_from="2026-09-28", date_to="2026-09-30",
            status="approved",
        )
        self.assertEqual(response.context.get("missing_log_count"), 2)
        self.assertEqual(self.missing_ids(response), [first.id, last.id])
        self.assertEqual(response.context["filtered_record_count"], 0)
        self.assertEqual(response.context["filtered_hours"], "0")

    def test_missing_groups_ignore_main_table_status_and_pagination(self):
        for _ in range(23):
            self.shift()
        self.shift(worker=self.other_worker)
        for status in ("", "submitted", "approved", "invoiced", "rejected"):
            with self.subTest(status=status):
                response = self.page(status=status, page=2)
                self.assertEqual(response.context.get("missing_log_count"), 24)
                self.assertEqual(response.context["missing_worker_count"], 2)
                self.assertEqual([group["count"] for group in response.context["missing_log_groups"]], [23, 1])

    def test_missing_summary_is_read_only_and_outside_invoice_form(self):
        shift = self.shift()
        before = list(Shift.objects.values())
        audits = AuditLog.objects.count()
        response = self.page(status="approved")
        self.assertEqual(list(Shift.objects.values()), before)
        self.assertEqual(ServiceLog.objects.count(), 0)
        self.assertEqual(Invoice.objects.count(), 0)
        self.assertEqual(AuditLog.objects.count(), audits)
        self.assertContains(response, reverse("shift_detail", args=[shift.id]))
        self.assertNotContains(response, 'name="service_log_ids"')
        self.assertNotContains(response, 'name="participant_cancellation_ids"')
        html = response.content.decode()
        self.assertLess(html.index('class="service-log-missing'), html.index('action="/invoices/new/"'))

    def test_groups_and_shifts_are_sorted_without_per_shift_queries(self):
        later = self.shift(service_date=date(2026, 10, 1), start_time=time(11))
        earlier = self.shift(service_date=date(2026, 9, 28))
        middle = self.shift(service_date=date(2026, 10, 1), start_time=time(9))
        self.shift(worker=self.other_worker)
        with CaptureQueriesContext(connection) as small:
            response = self.page()
        self.assertEqual(self.missing_ids(response)[:3], [earlier.id, middle.id, later.id])
        for _ in range(25):
            self.shift()
        with CaptureQueriesContext(connection) as large:
            self.page()
        self.assertLessEqual(len(large), len(small) + 1)

    def test_real_worker_submission_removes_missing_reminder(self):
        shift = self.shift()
        self.assertEqual(self.page().context.get("missing_log_count"), 1)
        self.client.force_login(self.worker_user)
        response = self.client.post(
            reverse("worker_service_log_create", args=[shift.id]),
            {
                "actual_start_time": "09:00", "actual_end_time": "12:00",
                "break_minutes": "0", "kilometres": "0",
                "case_notes": "Completed the scheduled support.", "worker_notes": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.client.force_login(self.admin)
        response = self.page()
        self.assertEqual(response.context.get("missing_log_count"), 0)
        self.assertEqual(response.context["filtered_record_count"], 1)

    def test_worker_cannot_access_admin_follow_up(self):
        self.client.force_login(self.worker_user)
        response = self.client.get(reverse("service_log_list"))
        self.assertNotEqual(response.status_code, 200)
