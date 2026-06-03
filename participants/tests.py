from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile
from workers.models import SupportWorker

from .models import Participant, ParticipantWorkerAssignment


class ParticipantManagementTests(TestCase):
    def create_user_with_role(self, username, role):
        user = get_user_model().objects.create_user(
            username=username,
            password="test-password-123",
        )
        UserProfile.objects.create(user=user, role=role)
        return user

    def setUp(self):
        self.create_user_with_role("admin", UserProfile.Role.ADMIN)
        self.create_user_with_role("worker", UserProfile.Role.SUPPORT_WORKER)
        self.create_user_with_role("accountant", UserProfile.Role.ACCOUNTANT)

    def login_admin(self):
        self.client.login(username="admin", password="test-password-123")

    def participant_payload(self, **overrides):
        data = {
            "first_name": "Ava",
            "last_name": "Nguyen",
            "preferred_name": "Ava",
            "date_of_birth": "1990-01-15",
            "ndis_number": "123456789",
            "status": Participant.Status.ACTIVE,
            "phone": "0400000000",
            "email": "ava@example.com",
            "address_line_1": "10 Creek Street",
            "address_line_2": "",
            "suburb": "Brisbane",
            "state": "QLD",
            "postcode": "4000",
            "emergency_contact_name": "Mia Nguyen",
            "emergency_contact_relationship": "Sister",
            "emergency_contact_phone": "0411111111",
            "emergency_contact_email": "mia@example.com",
            "plan_start_date": "2026-01-01",
            "plan_end_date": "2026-12-31",
            "management_type": Participant.ManagementType.PLAN_MANAGED,
            "plan_manager_name": "Plan Manager Co",
            "plan_manager_email": "pm@example.com",
            "plan_manager_phone": "0730000000",
            "support_coordinator_name": "Sam Lee",
            "support_coordinator_email": "sam@example.com",
            "support_coordinator_phone": "0731111111",
            "worker_visible_notes": "Use side entrance.",
            "address_access_instructions": "Gate code 1234.",
            "risk_safety_notes": "Dog in backyard.",
            "internal_notes": "Admin-only note.",
        }
        data.update(overrides)
        return data

    def test_admin_can_create_participant(self):
        self.login_admin()

        response = self.client.post(reverse("participant_create"), self.participant_payload())

        participant = Participant.objects.get(ndis_number="123456789")
        self.assertRedirects(response, reverse("participant_detail", args=[participant.id]))
        self.assertEqual(participant.first_name, "Ava")
        self.assertEqual(participant.management_type, Participant.ManagementType.PLAN_MANAGED)

    def test_first_and_last_name_are_required(self):
        self.login_admin()

        response = self.client.post(
            reverse("participant_create"),
            self.participant_payload(first_name="", last_name=""),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This field is required")
        self.assertEqual(Participant.objects.count(), 0)

    def test_ndis_number_must_be_unique_when_supplied(self):
        Participant.objects.create(
            first_name="Existing",
            last_name="Participant",
            ndis_number="123456789",
            status=Participant.Status.ACTIVE,
        )
        self.login_admin()

        response = self.client.post(reverse("participant_create"), self.participant_payload())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Participant with this NDIS number already exists")
        self.assertEqual(Participant.objects.count(), 1)

    def test_plan_end_date_cannot_be_before_start_date(self):
        self.login_admin()

        response = self.client.post(
            reverse("participant_create"),
            self.participant_payload(
                plan_start_date="2026-12-31",
                plan_end_date="2026-01-01",
            ),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Plan end date cannot be earlier than plan start date")
        self.assertEqual(Participant.objects.count(), 0)

    def test_postcode_must_be_four_digits_when_supplied(self):
        self.login_admin()

        response = self.client.post(
            reverse("participant_create"),
            self.participant_payload(postcode="400"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Enter a 4-digit Australian postcode")
        self.assertEqual(Participant.objects.count(), 0)

    def test_admin_can_search_and_filter_participant_list(self):
        Participant.objects.create(
            first_name="Ava",
            last_name="Nguyen",
            preferred_name="Ava",
            ndis_number="111111111",
            status=Participant.Status.ACTIVE,
        )
        Participant.objects.create(
            first_name="Ben",
            last_name="Taylor",
            preferred_name="Ben",
            ndis_number="222222222",
            status=Participant.Status.ARCHIVED,
        )
        self.login_admin()

        response = self.client.get(reverse("participant_list"), {"q": "Ava", "status": "active"})

        self.assertContains(response, "Ava Nguyen")
        self.assertNotContains(response, "Ben Taylor")

    def test_participant_list_is_paginated_and_preserves_filters(self):
        for index in range(25):
            Participant.objects.create(
                first_name=f"Active{index:02d}",
                last_name="Participant",
                ndis_number=f"5000000{index:02d}",
                status=Participant.Status.ACTIVE,
            )
        Participant.objects.create(
            first_name="Archived",
            last_name="Participant",
            ndis_number="599999999",
            status=Participant.Status.ARCHIVED,
        )
        self.login_admin()

        response = self.client.get(
            reverse("participant_list"),
            {"q": "Active", "status": Participant.Status.ACTIVE},
        )

        self.assertEqual(response.context["participants"].paginator.count, 25)
        self.assertEqual(len(response.context["participants"]), 20)
        self.assertContains(response, "Showing 1-20 of 25 records")
        self.assertContains(response, "?q=Active&amp;status=active&amp;page=2")
        self.assertNotContains(response, "Archived Participant")

    def test_admin_can_view_participant_detail(self):
        participant = Participant.objects.create(
            first_name="Ava",
            last_name="Nguyen",
            preferred_name="Ava",
            ndis_number="111111111",
            status=Participant.Status.ACTIVE,
            plan_start_date=date(2026, 1, 1),
            plan_end_date=date(2026, 12, 31),
        )
        self.login_admin()

        response = self.client.get(reverse("participant_detail", args=[participant.id]))

        self.assertContains(response, "Ava Nguyen")
        self.assertContains(response, "111111111")
        self.assertContains(response, "Roster")
        self.assertContains(response, "Service Logs")

    def test_participant_detail_shows_readiness_and_next_steps(self):
        participant = Participant.objects.create(
            first_name="Ava",
            last_name="Nguyen",
            status=Participant.Status.ACTIVE,
            plan_start_date=date(2026, 1, 1),
            plan_end_date=date(2026, 12, 31),
        )
        user = get_user_model().objects.create_user(
            username="assignedworker",
            email="assignedworker@example.com",
            password="test-password-123",
        )
        worker = SupportWorker.objects.create(
            user=user,
            first_name="Wendy",
            last_name="Worker",
            email="assignedworker@example.com",
        )
        ParticipantWorkerAssignment.objects.create(
            participant=participant,
            worker=worker,
            start_date=date(2026, 1, 1),
        )
        self.login_admin()

        response = self.client.get(reverse("participant_detail", args=[participant.id]))

        self.assertContains(response, "Readiness")
        self.assertContains(response, "Needs NDIS number")
        self.assertContains(response, "Active worker assigned")
        self.assertContains(response, "Next steps")
        self.assertContains(response, "Upload Document")
        self.assertContains(response, "Create Shift")

    def test_admin_can_edit_participant(self):
        participant = Participant.objects.create(
            first_name="Ava",
            last_name="Nguyen",
            ndis_number="111111111",
            status=Participant.Status.ACTIVE,
        )
        self.login_admin()

        response = self.client.post(
            reverse("participant_edit", args=[participant.id]),
            self.participant_payload(
                first_name="Avery",
                ndis_number="111111111",
                email="avery@example.com",
            ),
        )

        participant.refresh_from_db()
        self.assertRedirects(response, reverse("participant_detail", args=[participant.id]))
        self.assertEqual(participant.first_name, "Avery")
        self.assertEqual(participant.email, "avery@example.com")

    def test_admin_can_archive_participant_without_deleting_it(self):
        participant = Participant.objects.create(
            first_name="Ava",
            last_name="Nguyen",
            ndis_number="111111111",
            status=Participant.Status.ACTIVE,
        )
        self.login_admin()

        response = self.client.post(reverse("participant_archive", args=[participant.id]))

        participant.refresh_from_db()
        self.assertRedirects(response, reverse("participant_detail", args=[participant.id]))
        self.assertEqual(participant.status, Participant.Status.ARCHIVED)
        self.assertEqual(Participant.objects.count(), 1)

    def test_worker_and_accountant_cannot_access_participant_pages(self):
        participant = Participant.objects.create(
            first_name="Ava",
            last_name="Nguyen",
            status=Participant.Status.ACTIVE,
        )
        protected_urls = [
            reverse("participant_list"),
            reverse("participant_create"),
            reverse("participant_detail", args=[participant.id]),
            reverse("participant_edit", args=[participant.id]),
            reverse("participant_archive", args=[participant.id]),
        ]

        for username in ["worker", "accountant"]:
            self.client.login(username=username, password="test-password-123")
            for url in protected_urls:
                with self.subTest(username=username, url=url):
                    response = self.client.get(url)
                    self.assertEqual(response.status_code, 403)
            self.client.logout()
