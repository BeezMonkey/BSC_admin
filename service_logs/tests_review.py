from datetime import date, datetime, time, timezone as datetime_timezone
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile
from participants.models import Participant
from scheduling.models import Shift, SupportItem
from service_logs.models import ServiceLog
from workers.models import SupportWorker


class ServiceLogReviewTests(TestCase):
    def create_user_with_role(self, username, role):
        user = get_user_model().objects.create_user(
            username=username,
            password="test-password-123",
            email=f"{username}@example.com",
        )
        UserProfile.objects.create(
            user=user,
            role=role,
            is_active_worker=role == UserProfile.Role.SUPPORT_WORKER,
        )
        return user

    def setUp(self):
        self.admin_user = self.create_user_with_role("admin", UserProfile.Role.ADMIN)
        self.worker_user = self.create_user_with_role(
            "worker",
            UserProfile.Role.SUPPORT_WORKER,
        )
        self.participant = Participant.objects.create(
            first_name="Ava",
            last_name="Nguyen",
            status=Participant.Status.ACTIVE,
            address_line_1="10 Creek Street",
            suburb="Brisbane",
            state="QLD",
            postcode="4000",
        )
        self.worker = SupportWorker.objects.create(
            user=self.worker_user,
            first_name="Wendy",
            last_name="Worker",
            email="worker@example.com",
            status=SupportWorker.Status.ACTIVE,
        )
        self.support_item = SupportItem.objects.create(
            item_number="01_011_0107_1_1",
            name="Assistance with self-care activities",
            unit=SupportItem.Unit.HOUR,
            price_limit=Decimal("65.47"),
            gst_code=SupportItem.GSTCode.GST_FREE,
            is_active=True,
        )
        self.shift = Shift.objects.create(
            participant=self.participant,
            worker=self.worker,
            service_date=date(2026, 6, 1),
            start_time=time(9, 0),
            end_time=time(11, 30),
            break_minutes=30,
            planned_hours=Decimal("2.00"),
            support_item=self.support_item,
            service_type=Shift.ServiceType.PERSONAL_CARE,
            status=Shift.Status.COMPLETED,
            created_by=self.admin_user,
        )
        self.service_log = ServiceLog.objects.create_from_shift(
            shift=self.shift,
            actual_start_time=time(9, 0),
            actual_end_time=time(11, 30),
            break_minutes=30,
            actual_hours=Decimal("2.00"),
            kilometres=Decimal("1.0"),
            case_notes="Submitted for review.",
            worker_notes="",
        )

    def login_admin(self):
        self.client.login(username="admin", password="test-password-123")

    def login_worker(self):
        self.client.login(username="worker", password="test-password-123")

    def test_admin_can_approve_submitted_service_log(self):
        self.login_admin()

        response = self.client.post(
            reverse("service_log_approve", args=[self.service_log.id]),
        )

        self.service_log.refresh_from_db()
        self.assertRedirects(
            response,
            reverse("service_log_detail", args=[self.service_log.id]),
        )
        self.assertEqual(self.service_log.status, ServiceLog.Status.APPROVED)
        self.assertEqual(self.service_log.reviewed_by, self.admin_user)
        self.assertIsNotNone(self.service_log.reviewed_at)

    def test_admin_can_reject_submitted_service_log_with_reason(self):
        self.login_admin()

        response = self.client.post(
            reverse("service_log_reject", args=[self.service_log.id]),
            {"rejection_reason": "Please clarify case notes."},
        )

        self.service_log.refresh_from_db()
        self.assertRedirects(
            response,
            reverse("service_log_detail", args=[self.service_log.id]),
        )
        self.assertEqual(self.service_log.status, ServiceLog.Status.REJECTED)
        self.assertEqual(self.service_log.rejection_reason, "Please clarify case notes.")
        self.assertEqual(self.service_log.reviewed_by, self.admin_user)
        self.assertIsNotNone(self.service_log.reviewed_at)

    def test_reject_requires_reason(self):
        self.login_admin()

        response = self.client.post(
            reverse("service_log_reject", args=[self.service_log.id]),
            {"rejection_reason": "   "},
        )

        self.service_log.refresh_from_db()
        self.assertRedirects(
            response,
            reverse("service_log_detail", args=[self.service_log.id]),
        )
        self.assertEqual(self.service_log.status, ServiceLog.Status.SUBMITTED)
        self.assertEqual(self.service_log.rejection_reason, "")

    def test_worker_can_see_rejection_reason(self):
        self.service_log.status = ServiceLog.Status.REJECTED
        self.service_log.rejection_reason = "Please clarify case notes."
        self.service_log.reviewed_by = self.admin_user
        self.service_log.save(
            update_fields=["status", "rejection_reason", "reviewed_by", "updated_at"],
        )
        self.login_worker()

        response = self.client.get(
            reverse("worker_service_log_detail", args=[self.service_log.id]),
        )

        self.assertContains(response, "Rejected")
        self.assertContains(response, "Please clarify case notes.")

    def test_worker_cannot_approve_service_log(self):
        self.login_worker()

        response = self.client.post(
            reverse("service_log_approve", args=[self.service_log.id]),
        )

        self.service_log.refresh_from_db()
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.service_log.status, ServiceLog.Status.SUBMITTED)

    def test_admin_can_filter_service_logs_by_status(self):
        self.service_log.status = ServiceLog.Status.APPROVED
        self.service_log.save(update_fields=["status", "updated_at"])
        other_shift = Shift.objects.create(
            participant=self.participant,
            worker=self.worker,
            service_date=date(2026, 6, 2),
            start_time=time(12, 0),
            end_time=time(13, 0),
            break_minutes=0,
            planned_hours=Decimal("1.00"),
            support_item=self.support_item,
            service_type=Shift.ServiceType.PERSONAL_CARE,
            status=Shift.Status.COMPLETED,
            created_by=self.admin_user,
        )
        ServiceLog.objects.create_from_shift(
            shift=other_shift,
            actual_start_time=time(12, 0),
            actual_end_time=time(13, 0),
            break_minutes=0,
            actual_hours=Decimal("1.00"),
            kilometres=Decimal("0.0"),
            case_notes="Submitted log.",
            worker_notes="",
        )
        self.login_admin()

        response = self.client.get(
            reverse("service_log_list"),
            {"status": ServiceLog.Status.APPROVED},
        )

        self.assertContains(response, "Submitted for review.")
        self.assertNotContains(response, "Submitted log.")

    def test_service_log_list_renders_status_specific_class(self):
        self.service_log.status = ServiceLog.Status.APPROVED
        self.service_log.save(update_fields=["status", "updated_at"])
        self.login_admin()

        response = self.client.get(reverse("service_log_list"))

        self.assertContains(response, 'class="status-pill status-approved"')

    def test_service_log_list_displays_australian_date_format(self):
        self.service_log.status = ServiceLog.Status.APPROVED
        self.service_log.save(update_fields=["status", "updated_at"])
        self.login_admin()

        response = self.client.get(reverse("service_log_list"))

        self.assertContains(response, ">01/06/2026</a>")
        self.assertNotContains(response, ">June 1, 2026</a>")

    def test_service_log_detail_displays_australian_date_format(self):
        self.login_admin()

        response = self.client.get(reverse("service_log_detail", args=[self.service_log.id]))

        self.assertContains(response, "01/06/2026 |")
        self.assertNotContains(response, "June 1, 2026 |")

    def test_service_log_detail_displays_australian_datetime_format(self):
        self.service_log.reviewed_by = self.admin_user
        self.service_log.reviewed_at = datetime(2026, 6, 3, 23, 30, tzinfo=datetime_timezone.utc)
        self.service_log.submitted_at = datetime(2026, 6, 3, 22, 15, tzinfo=datetime_timezone.utc)
        self.service_log.save(update_fields=["reviewed_by", "reviewed_at", "submitted_at", "updated_at"])
        self.login_admin()

        response = self.client.get(reverse("service_log_detail", args=[self.service_log.id]))

        self.assertContains(response, "<dt>Reviewed at</dt><dd>04/06/2026 09:30</dd>", html=True)
        self.assertContains(response, "<dt>Submitted</dt><dd>04/06/2026 08:15</dd>", html=True)
        self.assertNotContains(response, "June 4, 2026")

    def test_service_log_list_shows_status_filter_summary(self):
        self.service_log.status = ServiceLog.Status.APPROVED
        self.service_log.save(update_fields=["status", "updated_at"])
        self.login_admin()

        response = self.client.get(
            reverse("service_log_list"),
            {"status": ServiceLog.Status.APPROVED},
        )

        self.assertContains(response, "Showing approved service logs.")
        self.assertContains(response, reverse("service_log_list"))

    def test_service_log_list_is_paginated_and_preserves_filters(self):
        self.service_log.status = ServiceLog.Status.APPROVED
        self.service_log.save(update_fields=["status", "updated_at"])
        for index in range(2, 26):
            shift = Shift.objects.create(
                participant=self.participant,
                worker=self.worker,
                service_date=date(2026, 6, index),
                start_time=time(9, 0),
                end_time=time(10, 0),
                break_minutes=0,
                planned_hours=Decimal("1.00"),
                support_item=self.support_item,
                service_type=Shift.ServiceType.PERSONAL_CARE,
                status=Shift.Status.COMPLETED,
                created_by=self.admin_user,
            )
            service_log = ServiceLog.objects.create_from_shift(
                shift=shift,
                actual_start_time=time(9, 0),
                actual_end_time=time(10, 0),
                break_minutes=0,
                actual_hours=Decimal("1.00"),
                kilometres=Decimal("0.0"),
                case_notes=f"Approved log {index}",
                worker_notes="",
            )
            service_log.status = ServiceLog.Status.APPROVED
            service_log.save(update_fields=["status", "updated_at"])
        submitted_shift = Shift.objects.create(
            participant=self.participant,
            worker=self.worker,
            service_date=date(2026, 6, 26),
            start_time=time(9, 0),
            end_time=time(10, 0),
            break_minutes=0,
            planned_hours=Decimal("1.00"),
            support_item=self.support_item,
            service_type=Shift.ServiceType.PERSONAL_CARE,
            status=Shift.Status.COMPLETED,
            created_by=self.admin_user,
        )
        ServiceLog.objects.create_from_shift(
            shift=submitted_shift,
            actual_start_time=time(9, 0),
            actual_end_time=time(10, 0),
            break_minutes=0,
            actual_hours=Decimal("1.00"),
            kilometres=Decimal("0.0"),
            case_notes="Submitted log outside filter.",
            worker_notes="",
        )
        self.login_admin()

        response = self.client.get(
            reverse("service_log_list"),
            {"status": ServiceLog.Status.APPROVED},
        )

        self.assertEqual(response.context["service_logs"].paginator.count, 25)
        self.assertEqual(len(response.context["service_logs"]), 20)
        self.assertContains(response, "Showing 1-20 of 25 records")
        self.assertContains(response, "?status=approved&amp;page=2")
        self.assertNotContains(response, "Submitted log outside filter.")

    def test_service_log_list_can_sort_by_date_and_preserve_filters(self):
        self.service_log.status = ServiceLog.Status.APPROVED
        self.service_log.save(update_fields=["status", "updated_at"])
        later_shift = Shift.objects.create(
            participant=self.participant,
            worker=self.worker,
            service_date=date(2026, 6, 3),
            start_time=time(9, 0),
            end_time=time(10, 0),
            break_minutes=0,
            planned_hours=Decimal("1.00"),
            support_item=self.support_item,
            service_type=Shift.ServiceType.PERSONAL_CARE,
            status=Shift.Status.COMPLETED,
            created_by=self.admin_user,
        )
        later_log = ServiceLog.objects.create_from_shift(
            shift=later_shift,
            actual_start_time=time(9, 0),
            actual_end_time=time(10, 0),
            break_minutes=0,
            actual_hours=Decimal("1.00"),
            kilometres=Decimal("0.0"),
            case_notes="Later approved log.",
            worker_notes="",
        )
        later_log.status = ServiceLog.Status.APPROVED
        later_log.save(update_fields=["status", "updated_at"])
        self.login_admin()

        response = self.client.get(
            reverse("service_log_list"),
            {"status": ServiceLog.Status.APPROVED, "sort": "date", "direction": "asc"},
        )
        content = response.content.decode()

        self.assertLess(content.index("01/06/2026"), content.index("03/06/2026"))
        self.assertContains(response, "?status=approved&amp;sort=date&amp;direction=desc")

    def test_service_log_list_distinguishes_empty_filter_results(self):
        self.login_admin()

        response = self.client.get(
            reverse("service_log_list"),
            {"status": ServiceLog.Status.APPROVED},
        )

        self.assertContains(response, "No service logs match the current filters.")
        self.assertContains(response, "Clear filters")
        self.assertNotContains(response, "Service logs appear here after workers complete")

    def test_admin_service_log_list_has_explicit_view_action(self):
        self.login_admin()

        response = self.client.get(reverse("service_log_list"))

        self.assertContains(response, "Actions")
        self.assertContains(response, reverse("service_log_detail", args=[self.service_log.id]))
        self.assertContains(response, "View")

    def test_service_log_list_uses_dense_table_structure(self):
        self.service_log.status = ServiceLog.Status.APPROVED
        self.service_log.save(update_fields=["status", "updated_at"])
        self.login_admin()

        response = self.client.get(reverse("service_log_list"))

        self.assertContains(response, 'class="service-log-table"')
        self.assertContains(response, 'class="notes-cell"')
        self.assertContains(response, 'name="service_log_ids"')
        self.assertContains(response, "Create Invoice")

    def test_service_log_list_uses_readability_table_classes(self):
        self.service_log.status = ServiceLog.Status.APPROVED
        self.service_log.save(update_fields=["status", "updated_at"])
        self.login_admin()

        response = self.client.get(reverse("service_log_list"))

        self.assertContains(response, 'class="card table-card service-log-table-card"')
        self.assertContains(response, 'class="service-log-date-cell"')
        self.assertContains(response, 'class="service-log-person-cell"')
        self.assertContains(response, 'class="service-log-status-cell"')
        self.assertContains(response, 'class="service-log-hours-cell"')
        self.assertContains(response, 'class="actions service-log-actions-cell"')

    def test_service_log_detail_back_link_preserves_list_state(self):
        self.service_log.status = ServiceLog.Status.APPROVED
        self.service_log.save(update_fields=["status", "updated_at"])
        list_path = f"{reverse('service_log_list')}?status=approved&sort=date&direction=desc&page=2"
        self.login_admin()

        list_response = self.client.get(list_path)
        detail_response = self.client.get(
            reverse("service_log_detail", args=[self.service_log.id]),
            {"next": list_path},
        )

        self.assertContains(
            list_response,
            f"{reverse('service_log_detail', args=[self.service_log.id])}?next=",
        )
        self.assertContains(detail_response, f'href="{list_path.replace("&", "&amp;")}"')
