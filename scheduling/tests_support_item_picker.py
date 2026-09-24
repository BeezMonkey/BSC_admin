from decimal import Decimal
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile
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
            category="Core Supports",
            unit=SupportItem.Unit.HOUR,
            price_limit=Decimal("65.47"),
            gst_code=SupportItem.GSTCode.GST_FREE,
            is_active=True,
        )
        self.saturday_item = SupportItem.objects.create(
            item_number="01_013_0107_1_1",
            name="Assistance With Self-Care Activities - Standard - Saturday",
            category="Core Supports",
            unit=SupportItem.Unit.HOUR,
            price_limit=Decimal("92.66"),
            gst_code=SupportItem.GSTCode.GST_FREE,
            is_active=True,
        )
        self.inactive_item = SupportItem.objects.create(
            item_number="01_014_0107_1_1",
            name="Assistance With Self-Care Activities - Standard - Sunday",
            category="Core Supports",
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
            'data-category="Self-care"',
            html,
        )
        self.assertIn(str(self.weekday_item), html)
        self.assertNotIn(str(self.inactive_item), html)

    def test_picker_uses_service_family_headings_without_changing_options(self):
        access_item = SupportItem.objects.create(
            item_number="04_104_0125_6_1",
            name=(
                "Access Community Social and Rec Activ - Standard - "
                "Weekday Daytime"
            ),
            category="Core Supports",
            unit=SupportItem.Unit.HOUR,
            price_limit=Decimal("73.58"),
            gst_code=SupportItem.GSTCode.GST_FREE,
            is_active=True,
        )
        travel_item = SupportItem.objects.create(
            item_number="04_799_0125_6_1",
            name="Provider travel - non-labour costs",
            category="Core Supports",
            unit=SupportItem.Unit.EACH,
            price_limit=Decimal("1.00"),
            gst_code=SupportItem.GSTCode.GST_FREE,
            is_active=True,
        )
        coordination_item = SupportItem.objects.create(
            item_number="07_002_0106_8_3",
            name="Support Coordination Level 2: Coordination of Supports",
            category="Support Coordination",
            unit=SupportItem.Unit.HOUR,
            price_limit=Decimal("100.14"),
            gst_code=SupportItem.GSTCode.GST_FREE,
            is_active=True,
        )
        other_item = SupportItem.objects.create(
            item_number="99_001_TEST",
            name="A future support item",
            category="Capacity Building",
            unit=SupportItem.Unit.HOUR,
            price_limit=Decimal("50.00"),
            gst_code=SupportItem.GSTCode.GST_FREE,
            is_active=True,
        )
        other_core_item = SupportItem.objects.create(
            item_number="99_001_CORE",
            name="A future core support item",
            category="Core Supports",
            unit=SupportItem.Unit.HOUR,
            price_limit=Decimal("50.00"),
            gst_code=SupportItem.GSTCode.GST_FREE,
            is_active=True,
        )
        uncategorized_item = SupportItem.objects.create(
            item_number="99_002_TEST",
            name="Another future support item",
            category="",
            unit=SupportItem.Unit.HOUR,
            price_limit=Decimal("50.00"),
            gst_code=SupportItem.GSTCode.GST_FREE,
            is_active=True,
        )

        html = ShiftForm().fields["support_item"].widget.render(
            "support_item",
            access_item.pk,
        )

        self.assertIn('data-category="Self-care"', html)
        self.assertIn('data-category="Community access"', html)
        self.assertIn('data-category="Provider travel"', html)
        self.assertIn('data-category="Support coordination"', html)
        self.assertIn('data-category="Capacity Building"', html)
        self.assertIn('data-category="Other core supports"', html)
        self.assertIn('data-category="Other support items"', html)
        self.assertNotIn('data-category="Core Supports"', html)
        for item in (
            self.weekday_item,
            access_item,
            travel_item,
            coordination_item,
            other_item,
            other_core_item,
            uncategorized_item,
        ):
            self.assertIn(f'value="{item.pk}"', html)
            self.assertIn(str(item), html)

    def test_shift_form_support_item_uses_picker_without_changing_choices(self):
        self.assert_picker_contract(ShiftForm().fields["support_item"])

    def test_recurring_shift_form_support_item_uses_picker_without_changing_choices(
        self,
    ):
        self.assert_picker_contract(RecurringShiftForm().fields["support_item"])

    def test_support_coordination_invoice_keeps_native_support_item_select(self):
        field = SupportCoordinationInvoiceCreateForm().fields["support_item"]

        self.assertNotIn("data-support-item-picker", field.widget.attrs)


class AdminSupportItemPickerPageTests(TestCase):
    def setUp(self):
        self.admin_user = get_user_model().objects.create_user(
            username="admin",
            password="test-password-123",
            email="admin@example.com",
        )
        UserProfile.objects.create(
            user=self.admin_user,
            role=UserProfile.Role.ADMIN,
        )
        self.client.login(username="admin", password="test-password-123")

    def assert_picker_assets(self, response):
        self.assertContains(response, "data-support-item-picker")
        self.assertContains(response, "data-support-item-picker-script")

    def test_shift_form_loads_support_item_picker_assets(self):
        self.assert_picker_assets(self.client.get(reverse("shift_create")))

    def test_roster_planner_loads_support_item_picker_assets(self):
        self.assert_picker_assets(self.client.get(reverse("roster_planner")))

    def test_recurring_shift_form_loads_support_item_picker_assets(self):
        self.assert_picker_assets(self.client.get(reverse("recurring_shift_create")))

    def test_support_coordination_invoice_does_not_load_picker_assets(self):
        response = self.client.get(reverse("support_coordination_invoice_create"))

        self.assertNotContains(response, "data-support-item-picker")
        self.assertNotContains(response, "data-support-item-picker-script")

    def test_picker_can_open_above_a_clipping_shift_modal_boundary(self):
        script = Path("static/js/support_item_picker.js").read_text(encoding="utf-8")
        styles = Path("static/css/app.css").read_text(encoding="utf-8")

        self.assertIn('closest(".shift-modal-body")', script)
        self.assertIn('classList.add("open-up")', script)
        self.assertIn(
            ".support-item-picker.open-up .support-item-picker-panel",
            styles,
        )

    def test_picker_combobox_name_includes_the_existing_field_label(self):
        script = Path("static/js/support_item_picker.js").read_text(encoding="utf-8")

        self.assertIn("select.labels", script)
        self.assertIn('"aria-labelledby"', script)
        self.assertIn('select.setAttribute("aria-hidden", "true")', script)
        self.assertIn("select.tabIndex = -1", script)

    def test_picker_uses_compact_type_without_reducing_touch_targets(self):
        styles = Path("static/css/app.css").read_text(encoding="utf-8")

        self.assertRegex(
            styles,
            r"(?s)\.support-item-picker-group\s*\{[^}]*font-size:\s*0\.7rem;",
        )
        self.assertRegex(
            styles,
            r"(?s)\.support-item-picker-option\s*\{[^}]*font-size:\s*0\.8rem;",
        )
        self.assertRegex(
            styles,
            r"(?s)\.support-item-picker-option\s*\{[^}]*min-height:\s*2\.55rem;",
        )
        self.assertRegex(
            styles,
            (
                r"(?s)@media \(max-width: 640px\).*?"
                r"\.support-item-picker-option\s*\{[^}]*"
                r"min-height:\s*2\.75rem;"
            ),
        )
