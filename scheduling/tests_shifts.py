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

    def create_shift(self, **overrides):
        data = {
            "participant": self.participant,
            "worker": self.worker,
            "service_date": date(2026, 6, 1),
            "start_time": time(9, 0),
            "end_time": time(11, 0),
            "planned_hours": Decimal("2.00"),
            "support_item": self.support_item,
            "service_type": Shift.ServiceType.PERSONAL_CARE,
            "status": Shift.Status.PUBLISHED,
            "created_by": self.admin_user,
        }
        data.update(overrides)
        return Shift.objects.create(**data)

    def test_admin_can_create_draft_shift_and_planned_hours_are_calculated(self):
        self.login_admin()

        response = self.client.post(reverse("shift_create"), self.shift_payload())

        shift = Shift.objects.get()
        self.assertRedirects(response, reverse("shift_detail", args=[shift.id]))
        self.assertEqual(shift.status, Shift.Status.DRAFT)
        self.assertEqual(shift.planned_hours, Decimal("2.00"))
        self.assertEqual(shift.created_by, self.admin_user)

    def test_shift_detail_shows_workflow_status_panel(self):
        shift = Shift.objects.create(
            participant=self.participant,
            worker=self.worker,
            service_date=date(2026, 6, 1),
            start_time=time(9, 0),
            end_time=time(11, 0),
            planned_hours=Decimal("2.00"),
            support_item=self.support_item,
            service_type=Shift.ServiceType.PERSONAL_CARE,
            status=Shift.Status.DRAFT,
            created_by=self.admin_user,
        )
        self.login_admin()

        response = self.client.get(reverse("shift_detail", args=[shift.id]))

        self.assertContains(response, "Workflow Status")
        self.assertContains(response, "Draft shift")
        self.assertContains(response, "Next step: publish this shift")
        self.assertContains(response, "Publish")
        self.assertContains(response, "Edit Shift")

    def test_shift_create_prefills_participant_and_worker_from_shortcut(self):
        self.login_admin()

        response = self.client.get(
            reverse("shift_create"),
            {"participant": self.participant.id, "worker": self.worker.id},
        )

        self.assertContains(
            response,
            f'<option value="{self.participant.id}" selected>{self.participant.display_name}</option>',
            html=True,
        )
        self.assertContains(
            response,
            f'<option value="{self.worker.id}" selected>{self.worker.display_name}</option>',
            html=True,
        )

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
            {"worker": "Wendy", "status": Shift.Status.PUBLISHED},
        )

        self.assertContains(response, "Wendy Worker")
        self.assertNotContains(response, "<td>Oscar Other</td>", html=True)

    def test_roster_worker_filter_uses_worker_name_search(self):
        self.create_shift(status=Shift.Status.PUBLISHED)
        self.login_admin()

        response = self.client.get(
            reverse("roster_list"),
            {"worker": "Wendy"},
        )

        self.assertContains(response, 'name="worker"')
        self.assertContains(response, 'placeholder="Worker name"')
        self.assertNotContains(response, 'placeholder="Worker ID"')

    def test_roster_can_filter_by_participant_and_worker_name(self):
        ben = Participant.objects.create(
            first_name="Ben",
            last_name="Taylor",
            status=Participant.Status.ACTIVE,
            address_line_1="20 Creek Street",
            suburb="Brisbane",
            state="QLD",
            postcode="4000",
        )
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
            participant=ben,
            worker=self.other_worker,
            service_date=date(2026, 6, 2),
            start_time=time(9, 0),
            end_time=time(10, 0),
            planned_hours=Decimal("1.00"),
            support_item=self.support_item,
            service_type=Shift.ServiceType.OTHER,
            status=Shift.Status.PUBLISHED,
            created_by=self.admin_user,
        )
        self.login_admin()

        response = self.client.get(
            reverse("roster_list"),
            {"participant": "Ava", "worker": "Wendy"},
        )

        self.assertContains(response, "Ava Nguyen")
        self.assertContains(response, "Wendy Worker")
        self.assertNotContains(response, "<td>Ben Taylor</td>", html=True)
        self.assertNotContains(response, "<td>Oscar Other</td>", html=True)
        self.assertContains(response, "Showing shifts for participant Ava for worker Wendy.")
        self.assertContains(response, 'placeholder="Participant name"')
        self.assertContains(response, 'placeholder="Worker name"')

    def test_roster_list_shows_status_filter_summary(self):
        self.create_shift(status=Shift.Status.DRAFT)
        self.login_admin()

        response = self.client.get(
            reverse("roster_list"),
            {"status": Shift.Status.DRAFT},
        )

        self.assertContains(response, "Showing draft shifts.")
        self.assertContains(response, reverse("roster_list"))

    def test_roster_list_shows_multi_filter_summary(self):
        self.create_shift(status=Shift.Status.PUBLISHED)
        self.login_admin()

        response = self.client.get(
            reverse("roster_list"),
            {
                "date_from": "2026-06-01",
                "date_to": "2026-06-30",
                "worker": "Wendy",
                "status": Shift.Status.PUBLISHED,
            },
        )

        self.assertContains(
            response,
            "Showing published shifts for worker Wendy from June 1, 2026 to June 30, 2026.",
        )

    def test_worker_can_only_see_own_non_draft_shifts(self):
        own_shift = self.create_shift()
        self.create_shift(
            service_date=date(2026, 6, 2),
            start_time=time(9, 0),
            end_time=time(10, 0),
            planned_hours=Decimal("1.00"),
            service_type=Shift.ServiceType.OTHER,
            status=Shift.Status.DRAFT,
        )
        self.create_shift(
            worker=self.other_worker,
            service_date=date(2026, 6, 1),
            start_time=time(12, 0),
            end_time=time(13, 0),
            planned_hours=Decimal("1.00"),
            service_type=Shift.ServiceType.OTHER,
            status=Shift.Status.PUBLISHED,
        )

        self.client.login(username="worker", password="test-password-123")
        response = self.client.get(reverse("worker_shift_list"))

        self.assertContains(response, "Ava Nguyen")
        self.assertContains(response, str(own_shift.id))
        self.assertNotContains(response, "Draft")
        self.assertNotContains(response, "Oscar Other")

    def test_worker_shift_list_groups_and_highlights_shift_statuses(self):
        completed_shift = self.create_shift(
            service_date=date(2026, 5, 21),
            status=Shift.Status.COMPLETED,
        )
        published_shift = self.create_shift(
            service_date=date(2026, 6, 4),
            status=Shift.Status.PUBLISHED,
        )
        confirmed_shift = self.create_shift(
            service_date=date(2026, 6, 5),
            status=Shift.Status.CONFIRMED,
        )
        self.client.login(username="worker", password="test-password-123")

        response = self.client.get(reverse("worker_shift_list"))
        content = response.content.decode()

        self.assertContains(response, "1 needs attention")
        self.assertContains(response, "1 upcoming")
        self.assertContains(response, "1 completed")
        self.assertContains(response, "Needs attention")
        self.assertContains(response, "Upcoming")
        self.assertContains(response, "Completed")
        self.assertContains(response, "status-pill status-published")
        self.assertContains(response, "status-pill status-confirmed")
        self.assertContains(response, "status-pill status-completed")
        self.assertLess(
            content.index(f"#{published_shift.id}"),
            content.index(f"#{completed_shift.id}"),
        )
        self.assertLess(
            content.index(f"#{confirmed_shift.id}"),
            content.index(f"#{completed_shift.id}"),
        )

    def test_worker_shift_list_shows_status_quick_actions(self):
        published_shift = self.create_shift(
            service_date=date(2026, 6, 4),
            status=Shift.Status.PUBLISHED,
        )
        confirmed_shift = self.create_shift(
            service_date=date(2026, 6, 5),
            status=Shift.Status.CONFIRMED,
        )
        completed_shift = self.create_shift(
            service_date=date(2026, 6, 6),
            status=Shift.Status.COMPLETED,
        )
        self.client.login(username="worker", password="test-password-123")

        response = self.client.get(reverse("worker_shift_list"))
        content = response.content.decode()

        self.assertContains(response, reverse("worker_shift_confirm", args=[published_shift.id]))
        self.assertContains(response, "Confirm")
        self.assertContains(
            response,
            reverse("worker_service_log_create", args=[confirmed_shift.id]),
        )
        self.assertContains(response, "Complete Log")
        completed_section = content[content.index(f"#{completed_shift.id}") :]
        self.assertNotIn("Confirm", completed_section)
        self.assertNotIn("Complete Log", completed_section)

    def test_worker_shift_list_can_filter_by_shift_group(self):
        published_shift = self.create_shift(
            service_date=date(2026, 6, 4),
            status=Shift.Status.PUBLISHED,
        )
        confirmed_shift = self.create_shift(
            service_date=date(2026, 6, 5),
            status=Shift.Status.CONFIRMED,
        )
        completed_shift = self.create_shift(
            service_date=date(2026, 6, 6),
            status=Shift.Status.COMPLETED,
        )
        self.client.login(username="worker", password="test-password-123")

        response = self.client.get(
            reverse("worker_shift_list"),
            {"view": "needs_attention"},
        )

        self.assertContains(response, f"#{published_shift.id}")
        self.assertNotContains(response, f"#{confirmed_shift.id}")
        self.assertNotContains(response, f"#{completed_shift.id}")
        self.assertContains(response, "filter-active")
        self.assertContains(response, "Needs attention")
        self.assertNotContains(response, "Upcoming</h2>")
        self.assertNotContains(response, "Completed</h2>")

    def test_worker_shift_list_shows_filter_navigation(self):
        self.create_shift(status=Shift.Status.PUBLISHED)
        self.client.login(username="worker", password="test-password-123")

        response = self.client.get(reverse("worker_shift_list"))

        self.assertContains(response, '?view=all')
        self.assertContains(response, '?view=needs_attention')
        self.assertContains(response, '?view=upcoming')
        self.assertContains(response, '?view=completed')

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
