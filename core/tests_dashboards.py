from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile
from workers.models import SupportWorker


class DashboardPolishTests(TestCase):
    def test_admin_dashboard_lists_current_v1_modules(self):
        user = User.objects.create_user(username="admin", password="pass")
        UserProfile.objects.create(user=user, role=UserProfile.Role.ADMIN)

        self.client.login(username="admin", password="pass")
        response = self.client.get(reverse("admin_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Participants")
        self.assertContains(response, "Support Workers")
        self.assertContains(response, "Roster")
        self.assertContains(response, "Service Logs")
        self.assertContains(response, "Invoices")
        self.assertContains(response, "Documents")
        self.assertContains(response, "Audit Logs")
        self.assertNotContains(response, "will be added")

    def test_worker_dashboard_lists_current_worker_tools(self):
        user = User.objects.create_user(username="worker", password="pass")
        UserProfile.objects.create(
            user=user,
            role=UserProfile.Role.SUPPORT_WORKER,
            is_active_worker=True,
        )
        SupportWorker.objects.create(
            user=user,
            first_name="Wendy",
            last_name="Worker",
            email="worker@example.com",
        )

        self.client.login(username="worker", password="pass")
        response = self.client.get(reverse("worker_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "My Shifts")
        self.assertContains(response, "My Logs")
        self.assertContains(response, "My Documents")
        self.assertContains(response, "Profile")
        self.assertNotContains(response, "will appear here")
