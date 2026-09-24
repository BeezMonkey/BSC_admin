from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile
from scheduling.models import SupportItem
from service_logs.forms import UnscheduledServiceLogForm
from workers.models import SupportWorker


class WorkerSupportItemPickerFormTests(TestCase):
    def setUp(self):
        self.support_item = SupportItem.objects.create(
            item_number="04_104_0125_6_1",
            name=(
                "Access Community Social and Recreational Activities - "
                "Standard - Weekday Daytime"
            ),
            category="Core Supports",
            unit=SupportItem.Unit.HOUR,
            price_limit=Decimal("65.47"),
            gst_code=SupportItem.GSTCode.GST_FREE,
            is_active=True,
        )
        self.inactive_item = SupportItem.objects.create(
            item_number="04_106_0125_6_1",
            name=(
                "Access Community Social and Recreational Activities - "
                "Standard - Sunday"
            ),
            category="Core Supports",
            unit=SupportItem.Unit.HOUR,
            price_limit=Decimal("119.84"),
            gst_code=SupportItem.GSTCode.GST_FREE,
            is_active=False,
        )

    def test_unscheduled_service_support_item_uses_picker_without_changing_choices(
        self,
    ):
        field = UnscheduledServiceLogForm().fields["support_item"]

        self.assertEqual(list(field.queryset), [self.support_item])
        self.assertEqual(field.widget.attrs["data-support-item-picker"], "")

        html = field.widget.render(
            "support_item",
            self.support_item.pk,
        )

        self.assertIn(f'value="{self.support_item.pk}"', html)
        self.assertIn('data-category="Community access"', html)
        self.assertIn(str(self.support_item), html)
        self.assertNotIn(str(self.inactive_item), html)


class WorkerSupportItemPickerPageTests(TestCase):
    def setUp(self):
        self.worker_user = get_user_model().objects.create_user(
            username="worker",
            password="test-password-123",
            email="worker@example.com",
        )
        UserProfile.objects.create(
            user=self.worker_user,
            role=UserProfile.Role.SUPPORT_WORKER,
            is_active_worker=True,
        )
        SupportWorker.objects.create(
            user=self.worker_user,
            first_name="Wendy",
            last_name="Worker",
            email="worker@example.com",
            status=SupportWorker.Status.ACTIVE,
        )
        self.client.login(username="worker", password="test-password-123")

    def test_unscheduled_service_form_loads_support_item_picker_assets(self):
        response = self.client.get(reverse("worker_unscheduled_service_log_create"))

        self.assertContains(response, "data-support-item-picker")
        self.assertContains(response, "data-support-item-picker-script")
