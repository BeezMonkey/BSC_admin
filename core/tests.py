from django.contrib.auth import get_user_model
from django.test import TestCase
from django.templatetags.static import static
from django.urls import reverse

from accounts.models import UserProfile
from workers.models import SupportWorker


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

        for name in ("home-active", "shifts", "logs", "documents"):
            with self.subTest(icon=name):
                self.assertContains(
                    response,
                    f'<img class="r1-icon" src="{static(f"img/r1/icons/{name}.svg")}" '
                    'alt="" aria-hidden="true">',
                    count=1,
                    html=True,
                )

    def test_untouched_worker_pages_retain_legacy_portal_icons(self):
        user = self.create_user_with_role("worker", UserProfile.Role.SUPPORT_WORKER)
        SupportWorker.objects.create(
            user=user, first_name="Fictional", last_name="Worker", email=user.email,
        )
        self.client.login(username="worker", password="test-password-123")

        for route in ("worker_document_list",):
            with self.subTest(route=route):
                response = self.client.get(reverse(route))
                self.assertEqual(response.status_code, 200)
                for name in ("home", "calendar", "logs", "file"):
                    self.assertContains(response, f"portal-nav-icon portal-nav-icon-{name}")
                self.assertNotContains(response, "r1_worker_navigation.css")

    def test_profile_uses_support_icons_without_changing_mobile_destinations(self):
        user = self.create_user_with_role("worker", UserProfile.Role.SUPPORT_WORKER)
        SupportWorker.objects.create(
            user=user, first_name="Fictional", last_name="Worker", email=user.email,
        )
        self.client.login(username="worker", password="test-password-123")
        response = self.client.get(reverse("worker_profile"))
        for name in ("support-home", "support-shifts", "support-logs", "support-documents"):
            self.assertContains(response, static(f"img/r1/icons/{name}.svg"))
        for route in ("worker_dashboard", "worker_shift_list", "worker_log_list", "worker_document_list"):
            self.assertContains(response, reverse(route))
        self.assertContains(response, static("css/r1_worker_support.css"))
        self.assertNotContains(response, "r1_worker_navigation.css")

    def test_admin_pages_do_not_include_worker_mobile_bottom_navigation(self):
        self.create_user_with_role("admin", UserProfile.Role.ADMIN)
        self.client.login(username="admin", password="test-password-123")

        response = self.client.get(reverse("admin_dashboard"))

        self.assertNotContains(response, "worker-bottom-nav")
