from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from accounts.models import UserProfile
from participants.models import Participant, ParticipantWorkerAssignment
from scheduling.models import Shift, SupportItem
from workers.models import SupportWorker


class SeedBetaTestDataCommandTests(TestCase):
    def test_seed_beta_test_data_creates_safe_trial_records(self):
        User = get_user_model()
        admin = User.objects.create_user(
            username="admin",
            email="owner@example.com",
            password="owner-password",
        )
        UserProfile.objects.create(user=admin, role=UserProfile.Role.ADMIN)

        call_command("seed_beta_test_data", password="BetaTest456")

        admin.refresh_from_db()
        self.assertEqual(admin.email, "owner@example.com")
        self.assertTrue(admin.check_password("owner-password"))

        worker_user = User.objects.get(username="beta_worker")
        self.assertTrue(worker_user.check_password("BetaTest456"))
        self.assertEqual(worker_user.userprofile.role, UserProfile.Role.SUPPORT_WORKER)
        self.assertTrue(worker_user.userprofile.is_active_worker)

        self.assertTrue(
            Participant.objects.filter(ndis_number="990000001").exists()
        )
        self.assertTrue(
            SupportWorker.objects.filter(user=worker_user, email="beta.worker@example.com").exists()
        )
        self.assertTrue(
            ParticipantWorkerAssignment.objects.filter(is_active=True).exists()
        )
        self.assertTrue(
            SupportItem.objects.filter(item_number="BETA-TEST-001").exists()
        )
        self.assertTrue(
            Shift.objects.filter(status=Shift.Status.PUBLISHED).exists()
        )

    def test_seed_beta_test_data_is_idempotent(self):
        call_command("seed_beta_test_data", password="BetaTest456")
        call_command("seed_beta_test_data", password="BetaTest456")

        self.assertEqual(Participant.objects.filter(ndis_number="990000001").count(), 1)
        self.assertEqual(SupportWorker.objects.filter(email="beta.worker@example.com").count(), 1)
        self.assertEqual(SupportItem.objects.filter(item_number="BETA-TEST-001").count(), 1)
        self.assertEqual(Shift.objects.count(), 1)
