from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile


class WorkerMobileShellTests(TestCase):
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

    def test_worker_pages_include_mobile_bottom_navigation(self):
        self.create_user_with_role("worker", UserProfile.Role.SUPPORT_WORKER)
        self.client.login(username="worker", password="test-password-123")

        response = self.client.get(reverse("worker_dashboard"))

        self.assertContains(response, 'class="worker-bottom-nav"')
        self.assertContains(response, reverse("worker_dashboard"))
        self.assertContains(response, reverse("worker_shift_list"))
        self.assertContains(response, reverse("worker_log_list"))
        self.assertContains(response, reverse("worker_document_list"))

    def test_worker_mobile_nav_uses_refined_portal_icons(self):
        self.create_user_with_role("worker", UserProfile.Role.SUPPORT_WORKER)
        self.client.login(username="worker", password="test-password-123")

        response = self.client.get(reverse("worker_dashboard"))

        self.assertContains(response, "portal-nav-icon portal-nav-icon-home")
        self.assertContains(response, "portal-nav-icon portal-nav-icon-calendar")
        self.assertContains(response, "portal-nav-icon portal-nav-icon-logs")
        self.assertContains(response, "portal-nav-icon portal-nav-icon-file")

    def test_admin_pages_do_not_include_worker_mobile_bottom_navigation(self):
        self.create_user_with_role("admin", UserProfile.Role.ADMIN)
        self.client.login(username="admin", password="test-password-123")

        response = self.client.get(reverse("admin_dashboard"))

        self.assertNotContains(response, "worker-bottom-nav")
