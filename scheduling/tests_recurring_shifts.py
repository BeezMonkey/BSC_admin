from datetime import date, time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile
from participants.models import Participant
from scheduling.models import Shift, SupportItem
from workers.models import SupportWorker


class RecurringShiftTests(TestCase):
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

    def login_admin(self):
        self.client.login(username="admin", password="test-password-123")

    def login_worker(self):
        self.client.login(username="worker", password="test-password-123")

    def recurring_payload(self, **overrides):
        data = {
            "participant": self.participant.id,
            "worker": self.worker.id,
            "frequency": "weekly",
            "start_date": "2026-06-01",
            "end_date": "2026-06-22",
            "start_time": "09:00",
            "end_time": "11:00",
            "break_minutes": "0",
            "support_item": self.support_item.id,
            "service_type": Shift.ServiceType.PERSONAL_CARE,
            "location": "Participant home",
            "address": "10 Creek Street, Brisbane QLD 4000",
            "instructions": "Use side entrance.",
            "admin_notes": "Recurring draft.",
        }
        data.update(overrides)
        return data

    def test_weekly_preview_lists_generated_dates(self):
        self.login_admin()

        response = self.client.get(reverse("recurring_shift_create"), self.recurring_payload())

        self.assertContains(response, "01/06/2026")
        self.assertContains(response, "08/06/2026")
        self.assertContains(response, "15/06/2026")
        self.assertContains(response, "22/06/2026")
        self.assertContains(response, "Will create", count=4)

    def test_fortnightly_preview_skips_alternate_weeks(self):
        self.login_admin()

        response = self.client.get(
            reverse("recurring_shift_create"),
            self.recurring_payload(frequency="fortnightly"),
        )

        self.assertContains(response, "01/06/2026")
        self.assertContains(response, "15/06/2026")
        self.assertNotContains(response, "08/06/2026")
        self.assertNotContains(response, "22/06/2026")

    def test_preview_marks_worker_conflicts_as_skipped(self):
        Shift.objects.create(
            participant=self.participant,
            worker=self.worker,
            service_date=date(2026, 6, 8),
            start_time=time(10, 0),
            end_time=time(12, 0),
            break_minutes=0,
            planned_hours=Decimal("2.00"),
            support_item=self.support_item,
            service_type=Shift.ServiceType.PERSONAL_CARE,
            status=Shift.Status.PUBLISHED,
            created_by=self.admin_user,
        )
        self.login_admin()

        response = self.client.get(reverse("recurring_shift_create"), self.recurring_payload())

        self.assertContains(response, "08/06/2026")
        self.assertContains(response, "Skipped - worker conflict")

    def test_confirm_creates_only_non_conflicting_draft_shifts(self):
        Shift.objects.create(
            participant=self.participant,
            worker=self.worker,
            service_date=date(2026, 6, 8),
            start_time=time(10, 0),
            end_time=time(12, 0),
            break_minutes=0,
            planned_hours=Decimal("2.00"),
            support_item=self.support_item,
            service_type=Shift.ServiceType.PERSONAL_CARE,
            status=Shift.Status.PUBLISHED,
            created_by=self.admin_user,
        )
        self.login_admin()

        response = self.client.post(
            reverse("recurring_shift_create"),
            self.recurring_payload(confirm="1"),
        )

        self.assertRedirects(response, f"{reverse('roster_list')}?status={Shift.Status.DRAFT}")
        created_dates = list(
            Shift.objects.filter(status=Shift.Status.DRAFT)
            .order_by("service_date")
            .values_list("service_date", flat=True)
        )
        self.assertEqual(
            created_dates,
            [date(2026, 6, 1), date(2026, 6, 15), date(2026, 6, 22)],
        )

    def test_worker_cannot_access_recurring_shift_create(self):
        self.login_worker()

        response = self.client.get(reverse("recurring_shift_create"))

        self.assertEqual(response.status_code, 403)
