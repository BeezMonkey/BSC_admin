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
