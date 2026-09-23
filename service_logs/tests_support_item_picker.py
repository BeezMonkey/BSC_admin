from decimal import Decimal

from django.test import TestCase

from scheduling.models import SupportItem
from service_logs.forms import UnscheduledServiceLogForm


class WorkerSupportItemPickerFormTests(TestCase):
    def setUp(self):
        self.support_item = SupportItem.objects.create(
            item_number="04_104_0125_6_1",
            name=(
                "Access Community Social and Recreational Activities - "
                "Standard - Weekday Daytime"
            ),
            category="Community Access",
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
            category="Community Access",
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
        self.assertIn('data-category="Community Access"', html)
        self.assertIn(str(self.support_item), html)
        self.assertNotIn(str(self.inactive_item), html)
