from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile
from scheduling.models import SupportItem


class SupportItemManagementTests(TestCase):
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
        self.create_user_with_role("admin", UserProfile.Role.ADMIN)
        self.create_user_with_role("worker", UserProfile.Role.SUPPORT_WORKER)
        self.create_user_with_role("accountant", UserProfile.Role.ACCOUNTANT)

    def login_admin(self):
        self.client.login(username="admin", password="test-password-123")

    def support_item_payload(self, **overrides):
        data = {
            "item_number": "01_011_0107_1_1",
            "name": "Assistance with self-care activities",
            "category": "Core Supports",
            "unit": SupportItem.Unit.HOUR,
            "price_limit": "65.47",
            "gst_code": SupportItem.GSTCode.GST_FREE,
            "is_active": "on",
            "notes": "Admin verified item.",
        }
        data.update(overrides)
        return data

    def test_admin_can_create_support_item(self):
        self.login_admin()

        response = self.client.post(
            reverse("support_item_create"),
            self.support_item_payload(),
        )

        item = SupportItem.objects.get(item_number="01_011_0107_1_1")
        self.assertRedirects(response, reverse("support_item_detail", args=[item.id]))
        self.assertEqual(item.name, "Assistance with self-care activities")
        self.assertEqual(item.price_limit, Decimal("65.47"))

    def test_item_number_is_required_and_unique(self):
        SupportItem.objects.create(
            item_number="01_011_0107_1_1",
            name="Existing item",
            unit=SupportItem.Unit.HOUR,
            price_limit=Decimal("10.00"),
            gst_code=SupportItem.GSTCode.GST_FREE,
        )
        self.login_admin()

        missing_response = self.client.post(
            reverse("support_item_create"),
            self.support_item_payload(item_number=""),
        )
        duplicate_response = self.client.post(
            reverse("support_item_create"),
            self.support_item_payload(),
        )

        self.assertContains(missing_response, "This field is required")
        self.assertContains(duplicate_response, "Support item with this item number already exists")
        self.assertEqual(SupportItem.objects.count(), 1)

    def test_price_limit_cannot_be_negative(self):
        self.login_admin()

        response = self.client.post(
            reverse("support_item_create"),
            self.support_item_payload(price_limit="-1.00"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Price limit cannot be negative")
        self.assertEqual(SupportItem.objects.count(), 0)

    def test_admin_can_search_and_filter_support_items(self):
        SupportItem.objects.create(
            item_number="ACTIVE-1",
            name="Community access",
            category="Core Supports",
            unit=SupportItem.Unit.HOUR,
            price_limit=Decimal("70.00"),
            gst_code=SupportItem.GSTCode.GST_FREE,
            is_active=True,
        )
        SupportItem.objects.create(
            item_number="INACTIVE-1",
            name="Transport",
            category="Transport",
            unit=SupportItem.Unit.KM,
            price_limit=Decimal("1.00"),
            gst_code=SupportItem.GSTCode.GST_FREE,
            is_active=False,
        )
        self.login_admin()

        response = self.client.get(
            reverse("support_item_list"),
            {"q": "Community", "is_active": "active", "category": "Core Supports"},
        )

        self.assertContains(response, "Community access")
        self.assertNotContains(response, "INACTIVE-1")

    def test_admin_can_view_support_item_detail(self):
        item = SupportItem.objects.create(
            item_number="ACTIVE-1",
            name="Community access",
            category="Core Supports",
            unit=SupportItem.Unit.HOUR,
            price_limit=Decimal("70.00"),
            gst_code=SupportItem.GSTCode.GST_FREE,
            is_active=True,
        )
        self.login_admin()

        response = self.client.get(reverse("support_item_detail", args=[item.id]))

        self.assertContains(response, "Community access")
        self.assertContains(response, "ACTIVE-1")
        self.assertContains(response, "GST-free")

    def test_admin_can_edit_support_item(self):
        item = SupportItem.objects.create(
            item_number="ACTIVE-1",
            name="Community access",
            category="Core Supports",
            unit=SupportItem.Unit.HOUR,
            price_limit=Decimal("70.00"),
            gst_code=SupportItem.GSTCode.GST_FREE,
            is_active=True,
        )
        self.login_admin()

        response = self.client.post(
            reverse("support_item_edit", args=[item.id]),
            self.support_item_payload(
                item_number="ACTIVE-1",
                name="Updated community access",
                price_limit="72.50",
                is_active="",
            ),
        )

        item.refresh_from_db()
        self.assertRedirects(response, reverse("support_item_detail", args=[item.id]))
        self.assertEqual(item.name, "Updated community access")
        self.assertFalse(item.is_active)

    def test_active_items_helper_returns_active_items_only(self):
        active = SupportItem.objects.create(
            item_number="ACTIVE-1",
            name="Community access",
            unit=SupportItem.Unit.HOUR,
            price_limit=Decimal("70.00"),
            gst_code=SupportItem.GSTCode.GST_FREE,
            is_active=True,
        )
        SupportItem.objects.create(
            item_number="INACTIVE-1",
            name="Inactive item",
            unit=SupportItem.Unit.EACH,
            price_limit=Decimal("10.00"),
            gst_code=SupportItem.GSTCode.GST_FREE,
            is_active=False,
        )

        self.assertEqual(list(SupportItem.active_items()), [active])

    def test_worker_and_accountant_cannot_access_support_item_pages(self):
        item = SupportItem.objects.create(
            item_number="ACTIVE-1",
            name="Community access",
            unit=SupportItem.Unit.HOUR,
            price_limit=Decimal("70.00"),
            gst_code=SupportItem.GSTCode.GST_FREE,
            is_active=True,
        )
        protected_urls = [
            reverse("support_item_list"),
            reverse("support_item_create"),
            reverse("support_item_detail", args=[item.id]),
            reverse("support_item_edit", args=[item.id]),
        ]

        for username in ["worker", "accountant"]:
            self.client.login(username=username, password="test-password-123")
            for url in protected_urls:
                with self.subTest(username=username, url=url):
                    response = self.client.get(url)
                    self.assertEqual(response.status_code, 403)
            self.client.logout()
