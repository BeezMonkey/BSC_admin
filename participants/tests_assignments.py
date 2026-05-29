from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile
from participants.models import Participant, ParticipantWorkerAssignment
from workers.models import SupportWorker


class ParticipantWorkerAssignmentTests(TestCase):
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
        self.accountant_user = self.create_user_with_role(
            "accountant",
            UserProfile.Role.ACCOUNTANT,
        )
        self.participant = Participant.objects.create(
            first_name="Ava",
            last_name="Nguyen",
            ndis_number="100000001",
            status=Participant.Status.ACTIVE,
        )
        self.worker = SupportWorker.objects.create(
            user=self.worker_user,
            first_name="Wendy",
            last_name="Worker",
            email="worker@example.com",
            status=SupportWorker.Status.ACTIVE,
        )

    def login_admin(self):
        self.client.login(username="admin", password="test-password-123")

    def assignment_payload(self, **overrides):
        data = {
            "worker": self.worker.id,
            "start_date": "2026-05-01",
            "end_date": "",
            "is_active": "on",
            "notes": "Primary worker.",
        }
        data.update(overrides)
        return data

    def test_admin_can_create_assignment_from_participant(self):
        self.login_admin()

        response = self.client.post(
            reverse("participant_assign_worker", args=[self.participant.id]),
            self.assignment_payload(),
        )

        assignment = ParticipantWorkerAssignment.objects.get()
        self.assertRedirects(response, reverse("participant_detail", args=[self.participant.id]))
        self.assertEqual(assignment.participant, self.participant)
        self.assertEqual(assignment.worker, self.worker)
        self.assertTrue(assignment.is_active)

    def test_duplicate_active_assignment_is_rejected(self):
        ParticipantWorkerAssignment.objects.create(
            participant=self.participant,
            worker=self.worker,
            start_date=date(2026, 5, 1),
            is_active=True,
        )
        self.login_admin()

        response = self.client.post(
            reverse("participant_assign_worker", args=[self.participant.id]),
            self.assignment_payload(),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This worker already has an active assignment")
        self.assertEqual(ParticipantWorkerAssignment.objects.count(), 1)

    def test_end_date_cannot_be_before_start_date(self):
        self.login_admin()

        response = self.client.post(
            reverse("participant_assign_worker", args=[self.participant.id]),
            self.assignment_payload(start_date="2026-06-01", end_date="2026-05-01"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "End date cannot be earlier than start date")
        self.assertEqual(ParticipantWorkerAssignment.objects.count(), 0)

    def test_admin_can_end_assignment_without_deleting_it(self):
        assignment = ParticipantWorkerAssignment.objects.create(
            participant=self.participant,
            worker=self.worker,
            start_date=date(2026, 5, 1),
            is_active=True,
        )
        self.login_admin()

        response = self.client.post(
            reverse("assignment_end", args=[assignment.id]),
            {"end_date": "2026-06-01"},
        )

        assignment.refresh_from_db()
        self.assertRedirects(response, reverse("participant_detail", args=[self.participant.id]))
        self.assertFalse(assignment.is_active)
        self.assertEqual(assignment.end_date, date(2026, 6, 1))
        self.assertEqual(ParticipantWorkerAssignment.objects.count(), 1)

    def test_participant_detail_displays_assigned_worker(self):
        ParticipantWorkerAssignment.objects.create(
            participant=self.participant,
            worker=self.worker,
            start_date=date(2026, 5, 1),
            is_active=True,
        )
        self.login_admin()

        response = self.client.get(reverse("participant_detail", args=[self.participant.id]))

        self.assertContains(response, "Assigned Workers")
        self.assertContains(response, "Wendy Worker")

    def test_worker_detail_displays_assigned_participant(self):
        ParticipantWorkerAssignment.objects.create(
            participant=self.participant,
            worker=self.worker,
            start_date=date(2026, 5, 1),
            is_active=True,
        )
        self.login_admin()

        response = self.client.get(reverse("worker_detail", args=[self.worker.id]))

        self.assertContains(response, "Assigned Participants")
        self.assertContains(response, "Ava Nguyen")

    def test_worker_profile_displays_own_assigned_participants(self):
        ParticipantWorkerAssignment.objects.create(
            participant=self.participant,
            worker=self.worker,
            start_date=date(2026, 5, 1),
            is_active=True,
        )

        self.client.login(username="worker", password="test-password-123")
        response = self.client.get(reverse("worker_profile"))

        self.assertContains(response, "Assigned Participants")
        self.assertContains(response, "Ava Nguyen")

    def test_worker_and_accountant_cannot_manage_assignments(self):
        assignment = ParticipantWorkerAssignment.objects.create(
            participant=self.participant,
            worker=self.worker,
            start_date=date(2026, 5, 1),
            is_active=True,
        )
        urls = [
            reverse("participant_assign_worker", args=[self.participant.id]),
            reverse("assignment_end", args=[assignment.id]),
        ]

        for username in ["worker", "accountant"]:
            self.client.login(username=username, password="test-password-123")
            for url in urls:
                with self.subTest(username=username, url=url):
                    response = self.client.get(url)
                    self.assertEqual(response.status_code, 403)
            self.client.logout()
