from datetime import date, time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile
from participants.models import Participant
from scheduling.models import Shift, SupportItem
from workers.models import SupportWorker


class ShiftSchedulingTests(TestCase):
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
        self.worker_user = self.create_user_with_role("worker", UserProfile.Role.SUPPORT_WORKER)
        self.other_worker_user = self.create_user_with_role(
            "otherworker",
            UserProfile.Role.SUPPORT_WORKER,
        )
        self.create_user_with_role("accountant", UserProfile.Role.ACCOUNTANT)
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
        self.other_worker = SupportWorker.objects.create(
            user=self.other_worker_user,
            first_name="Oscar",
            last_name="Other",
            email="other@example.com",
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

    def login_admin(self):
        self.client.login(username="admin", password="test-password-123")

    def shift_payload(self, **overrides):
        data = {
            "participant": self.participant.id,
            "worker": self.worker.id,
            "service_date": "2026-06-01",
            "start_time": "09:00",
            "end_time": "11:30",
            "break_minutes": "30",
            "support_item": self.support_item.id,
            "service_type": Shift.ServiceType.PERSONAL_CARE,
            "location": "Participant home",
            "address": "10 Creek Street, Brisbane QLD 4000",
            "instructions": "Use side entrance.",
            "admin_notes": "Admin note.",
            "status": Shift.Status.DRAFT,
        }
        data.update(overrides)
        return data

    def test_admin_can_create_draft_shift_and_planned_hours_are_calculated(self):
        self.login_admin()

        response = self.client.post(reverse("shift_create"), self.shift_payload())

        shift = Shift.objects.get()
        self.assertRedirects(response, reverse("shift_detail", args=[shift.id]))
        self.assertEqual(shift.status, Shift.Status.DRAFT)
        self.assertEqual(shift.planned_hours, Decimal("2.00"))
        self.assertEqual(shift.created_by, self.admin_user)

    def test_admin_can_create_published_shift(self):
        self.login_admin()

        response = self.client.post(
            reverse("shift_create"),
            self.shift_payload(status=Shift.Status.PUBLISHED),
        )

        shift = Shift.objects.get()
        self.assertRedirects(response, reverse("shift_detail", args=[shift.id]))
        self.assertEqual(shift.status, Shift.Status.PUBLISHED)

    def test_end_time_must_be_after_start_time(self):
        self.login_admin()

        response = self.client.post(
            reverse("shift_create"),
            self.shift_payload(start_time="11:00", end_time="09:00"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "End time must be after start time")
        self.assertEqual(Shift.objects.count(), 0)

    def test_worker_overlap_is_blocked_for_active_shift_statuses(self):
        Shift.objects.create(
            participant=self.participant,
            worker=self.worker,
            service_date=date(2026, 6, 1),
            start_time=time(9, 0),
            end_time=time(11, 0),
            planned_hours=Decimal("2.00"),
            support_item=self.support_item,
            service_type=Shift.ServiceType.PERSONAL_CARE,
            status=Shift.Status.PUBLISHED,
            created_by=self.admin_user,
        )
        self.login_admin()

        response = self.client.post(
            reverse("shift_create"),
            self.shift_payload(start_time="10:00", end_time="12:00"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Worker has an overlapping active shift")
        self.assertEqual(Shift.objects.count(), 1)

    def test_admin_can_filter_roster_list(self):
        Shift.objects.create(
            participant=self.participant,
            worker=self.worker,
            service_date=date(2026, 6, 1),
            start_time=time(9, 0),
            end_time=time(11, 0),
            planned_hours=Decimal("2.00"),
            support_item=self.support_item,
            service_type=Shift.ServiceType.PERSONAL_CARE,
            status=Shift.Status.PUBLISHED,
            created_by=self.admin_user,
        )
        Shift.objects.create(
            participant=self.participant,
            worker=self.other_worker,
            service_date=date(2026, 6, 2),
            start_time=time(9, 0),
            end_time=time(10, 0),
            planned_hours=Decimal("1.00"),
            support_item=self.support_item,
            service_type=Shift.ServiceType.OTHER,
            status=Shift.Status.DRAFT,
            created_by=self.admin_user,
        )
        self.login_admin()

        response = self.client.get(
            reverse("roster_list"),
            {"worker": self.worker.id, "status": Shift.Status.PUBLISHED},
        )

        self.assertContains(response, "Wendy Worker")
        self.assertNotContains(response, "Oscar Other")

    def test_worker_can_only_see_own_non_draft_shifts(self):
        own_shift = Shift.objects.create(
            participant=self.participant,
            worker=self.worker,
            service_date=date(2026, 6, 1),
            start_time=time(9, 0),
            end_time=time(11, 0),
            planned_hours=Decimal("2.00"),
            support_item=self.support_item,
            service_type=Shift.ServiceType.PERSONAL_CARE,
            status=Shift.Status.PUBLISHED,
            created_by=self.admin_user,
        )
        Shift.objects.create(
            participant=self.participant,
            worker=self.worker,
            service_date=date(2026, 6, 2),
            start_time=time(9, 0),
            end_time=time(10, 0),
            planned_hours=Decimal("1.00"),
            support_item=self.support_item,
            service_type=Shift.ServiceType.OTHER,
            status=Shift.Status.DRAFT,
            created_by=self.admin_user,
        )
        Shift.objects.create(
            participant=self.participant,
            worker=self.other_worker,
            service_date=date(2026, 6, 1),
            start_time=time(12, 0),
            end_time=time(13, 0),
            planned_hours=Decimal("1.00"),
            support_item=self.support_item,
            service_type=Shift.ServiceType.OTHER,
            status=Shift.Status.PUBLISHED,
            created_by=self.admin_user,
        )

        self.client.login(username="worker", password="test-password-123")
        response = self.client.get(reverse("worker_shift_list"))

        self.assertContains(response, "Ava Nguyen")
        self.assertContains(response, str(own_shift.id))
        self.assertNotContains(response, "Draft")
        self.assertNotContains(response, "Oscar Other")

    def test_worker_can_view_and_confirm_own_published_shift(self):
        shift = Shift.objects.create(
            participant=self.participant,
            worker=self.worker,
            service_date=date(2026, 6, 1),
            start_time=time(9, 0),
            end_time=time(11, 0),
            planned_hours=Decimal("2.00"),
            support_item=self.support_item,
            service_type=Shift.ServiceType.PERSONAL_CARE,
            status=Shift.Status.PUBLISHED,
            created_by=self.admin_user,
        )

        self.client.login(username="worker", password="test-password-123")
        detail_response = self.client.get(reverse("worker_shift_detail", args=[shift.id]))
        confirm_response = self.client.post(reverse("worker_shift_confirm", args=[shift.id]))

        shift.refresh_from_db()
        self.assertContains(detail_response, "Confirm Shift")
        self.assertRedirects(confirm_response, reverse("worker_shift_detail", args=[shift.id]))
        self.assertEqual(shift.status, Shift.Status.CONFIRMED)
        self.assertIsNotNone(shift.confirmed_at)

    def test_worker_cannot_access_other_worker_shift(self):
        shift = Shift.objects.create(
            participant=self.participant,
            worker=self.other_worker,
            service_date=date(2026, 6, 1),
            start_time=time(9, 0),
            end_time=time(11, 0),
            planned_hours=Decimal("2.00"),
            support_item=self.support_item,
            service_type=Shift.ServiceType.PERSONAL_CARE,
            status=Shift.Status.PUBLISHED,
            created_by=self.admin_user,
        )

        self.client.login(username="worker", password="test-password-123")
        response = self.client.get(reverse("worker_shift_detail", args=[shift.id]))

        self.assertEqual(response.status_code, 404)

    def test_admin_can_cancel_shift_with_reason(self):
        shift = Shift.objects.create(
            participant=self.participant,
            worker=self.worker,
            service_date=date(2026, 6, 1),
            start_time=time(9, 0),
            end_time=time(11, 0),
            planned_hours=Decimal("2.00"),
            support_item=self.support_item,
            service_type=Shift.ServiceType.PERSONAL_CARE,
            status=Shift.Status.PUBLISHED,
            created_by=self.admin_user,
        )
        self.login_admin()

        response = self.client.post(
            reverse("shift_cancel", args=[shift.id]),
            {"cancellation_reason": "Participant unavailable."},
        )

        shift.refresh_from_db()
        self.assertRedirects(response, reverse("shift_detail", args=[shift.id]))
        self.assertEqual(shift.status, Shift.Status.CANCELLED)
        self.assertEqual(shift.cancellation_reason, "Participant unavailable.")
