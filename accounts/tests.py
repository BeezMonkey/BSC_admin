from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import UserProfile


class RoleRoutingTests(TestCase):
    def create_user_with_role(self, username, role):
        user = get_user_model().objects.create_user(
            username=username,
            password="test-password-123",
        )
        UserProfile.objects.create(user=user, role=role)
        return user

    def test_super_admin_redirects_to_admin_dashboard(self):
        self.create_user_with_role("owner", UserProfile.Role.SUPER_ADMIN)

        self.client.login(username="owner", password="test-password-123")
        response = self.client.get(reverse("role_redirect"))

        self.assertRedirects(response, reverse("admin_dashboard"))

    def test_admin_redirects_to_admin_dashboard(self):
        self.create_user_with_role("admin", UserProfile.Role.ADMIN)

        self.client.login(username="admin", password="test-password-123")
        response = self.client.get(reverse("role_redirect"))

        self.assertRedirects(response, reverse("admin_dashboard"))

    def test_support_worker_redirects_to_worker_dashboard(self):
        self.create_user_with_role("worker", UserProfile.Role.SUPPORT_WORKER)

        self.client.login(username="worker", password="test-password-123")
        response = self.client.get(reverse("role_redirect"))

        self.assertRedirects(response, reverse("worker_dashboard"))

    def test_accountant_redirects_to_invoice_placeholder(self):
        self.create_user_with_role("accountant", UserProfile.Role.ACCOUNTANT)

        self.client.login(username="accountant", password="test-password-123")
        response = self.client.get(reverse("role_redirect"))

        self.assertRedirects(response, reverse("invoice_placeholder"))

    def test_worker_cannot_access_admin_dashboard(self):
        self.create_user_with_role("worker", UserProfile.Role.SUPPORT_WORKER)

        self.client.login(username="worker", password="test-password-123")
        response = self.client.get(reverse("admin_dashboard"))

        self.assertEqual(response.status_code, 403)

    def test_admin_cannot_access_worker_dashboard(self):
        self.create_user_with_role("admin", UserProfile.Role.ADMIN)

        self.client.login(username="admin", password="test-password-123")
        response = self.client.get(reverse("worker_dashboard"))

        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_user_redirects_to_login(self):
        response = self.client.get(reverse("admin_dashboard"))

        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('admin_dashboard')}",
        )


class RoleAccessTests(TestCase):
    def create_user_with_role(self, username, role):
        user = get_user_model().objects.create_user(
            username=username,
            password="test-password-123",
        )
        UserProfile.objects.create(user=user, role=role)
        return user

    def assert_role_can_access(self, username, url_name):
        self.client.login(username=username, password="test-password-123")
        response = self.client.get(reverse(url_name))
        self.assertEqual(response.status_code, 200)
        self.client.logout()

    def assert_role_is_forbidden(self, username, url_name):
        self.client.login(username=username, password="test-password-123")
        response = self.client.get(reverse(url_name))
        self.assertEqual(response.status_code, 403)
        self.client.logout()

    def setUp(self):
        self.create_user_with_role("super", UserProfile.Role.SUPER_ADMIN)
        self.create_user_with_role("admin", UserProfile.Role.ADMIN)
        self.create_user_with_role("worker", UserProfile.Role.SUPPORT_WORKER)
        self.create_user_with_role("accountant", UserProfile.Role.ACCOUNTANT)

    def test_admin_operation_pages_allow_admins_only(self):
        admin_pages = [
            "participant_list",
            "worker_list",
            "roster_list",
            "service_log_list",
            "document_list",
        ]

        for url_name in admin_pages:
            with self.subTest(url_name=url_name):
                self.assert_role_can_access("super", url_name)
                self.assert_role_can_access("admin", url_name)
                self.assert_role_is_forbidden("worker", url_name)
                self.assert_role_is_forbidden("accountant", url_name)

    def test_worker_pages_allow_support_workers_only(self):
        worker_pages = [
            "worker_dashboard",
            "worker_shift_list",
            "worker_log_list",
            "worker_profile",
        ]

        for url_name in worker_pages:
            with self.subTest(url_name=url_name):
                self.assert_role_can_access("worker", url_name)
                self.assert_role_is_forbidden("super", url_name)
                self.assert_role_is_forbidden("admin", url_name)
                self.assert_role_is_forbidden("accountant", url_name)

    def test_finance_pages_allow_admins_and_accountant(self):
        finance_pages = [
            "invoice_placeholder",
            "exports_placeholder",
        ]

        for url_name in finance_pages:
            with self.subTest(url_name=url_name):
                self.assert_role_can_access("super", url_name)
                self.assert_role_can_access("admin", url_name)
                self.assert_role_can_access("accountant", url_name)
                self.assert_role_is_forbidden("worker", url_name)

    def test_user_without_profile_cannot_access_protected_pages(self):
        get_user_model().objects.create_user(
            username="missing-profile",
            password="test-password-123",
        )

        self.client.login(username="missing-profile", password="test-password-123")
        response = self.client.get(reverse("admin_dashboard"))

        self.assertEqual(response.status_code, 403)
