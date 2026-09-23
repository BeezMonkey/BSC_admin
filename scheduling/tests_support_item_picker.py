from decimal import Decimal

from django.test import TestCase

from invoices.forms import SupportCoordinationInvoiceCreateForm
from scheduling.forms import RecurringShiftForm, ShiftForm
from scheduling.models import SupportItem


class AdminSupportItemPickerFormTests(TestCase):
    def setUp(self):
        self.weekday_item = SupportItem.objects.create(
            item_number="01_011_0107_1_1",
            name=(
                "Assistance With Self-Care Activities - Standard - "
                "Weekday Daytime"
            ),
            category="Assistance With Self-Care Activities",
            unit=SupportItem.Unit.HOUR,
            price_limit=Decimal("65.47"),
            gst_code=SupportItem.GSTCode.GST_FREE,
            is_active=True,
        )
        self.saturday_item = SupportItem.objects.create(
            item_number="01_013_0107_1_1",
            name="Assistance With Self-Care Activities - Standard - Saturday",
            category="Assistance With Self-Care Activities",
            unit=SupportItem.Unit.HOUR,
            price_limit=Decimal("92.66"),
            gst_code=SupportItem.GSTCode.GST_FREE,
            is_active=True,
        )
        self.inactive_item = SupportItem.objects.create(
            item_number="01_014_0107_1_1",
            name="Assistance With Self-Care Activities - Standard - Sunday",
            category="Assistance With Self-Care Activities",
            unit=SupportItem.Unit.HOUR,
            price_limit=Decimal("119.84"),
            gst_code=SupportItem.GSTCode.GST_FREE,
            is_active=False,
        )

    def assert_picker_contract(self, field):
        self.assertEqual(
            list(field.queryset),
            [self.weekday_item, self.saturday_item],
        )
        self.assertEqual(field.widget.attrs["data-support-item-picker"], "")

        html = field.widget.render(
            "support_item",
            self.weekday_item.pk,
        )

        self.assertIn(f'value="{self.weekday_item.pk}"', html)
        self.assertIn(
            'data-category="Assistance With Self-Care Activities"',
            html,
        )
        self.assertIn(str(self.weekday_item), html)
        self.assertNotIn(str(self.inactive_item), html)

    def test_shift_form_support_item_uses_picker_without_changing_choices(self):
        self.assert_picker_contract(ShiftForm().fields["support_item"])

    def test_recurring_shift_form_support_item_uses_picker_without_changing_choices(
        self,
    ):
        self.assert_picker_contract(RecurringShiftForm().fields["support_item"])

    def test_support_coordination_invoice_keeps_native_support_item_select(self):
        field = SupportCoordinationInvoiceCreateForm().fields["support_item"]

        self.assertNotIn("data-support-item-picker", field.widget.attrs)
