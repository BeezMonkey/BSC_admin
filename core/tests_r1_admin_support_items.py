from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.test import TestCase, override_settings
from django.urls import reverse

from core import tests_r1_admin_people_forms as form_helpers
from core import tests_r1_admin_people_lists as people_fixtures
from scheduling.models import SupportItem


@override_settings(STORAGES={
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
})
class R1AdminSupportItemsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        people_fixtures.R1AdminPeopleListTests.setUpTestData.__func__(cls)
        cls.item = SupportItem.objects.create(
            item_number="QA-NOT-REAL-ITEM", name="Fictional support item",
            category="Fictional category", unit=SupportItem.Unit.KM,
            price_limit=Decimal("100.00"), gst_code=SupportItem.GSTCode.TAXABLE,
            notes="Fictional first line.\nSecond line with <escaped> content.")

    def setUp(self):
        self.client.force_login(self.admin)

    def routes(self):
        return [("support_item_list", []), ("support_item_detail", [self.item.pk]),
                ("support_item_create", []), ("support_item_edit", [self.item.pk])]

    def get_page(self, route, args):
        response = self.client.get(reverse(route, args=args))
        self.assertEqual(response.status_code, 200)
        return response

    def test_four_pages_have_content_only_approved_styles(self):
        for route, args in self.routes():
            with self.subTest(route=route):
                response = self.get_page(route, args)
                self.assertContains(response, "r1-support-items", count=1)
                for asset in ("r1_tokens.css", "r1_admin_people_forms.css", "r1_admin_support_items.css", "form_focus.css"):
                    self.assertContains(response, static("css/" + asset), count=1)
                self.assertNotContains(response, static("css/r1_shell.css"))
                self.assertContains(response, '<div class="app-shell" data-admin-theme>')

    def test_forms_keep_eight_original_fields_and_attributes(self):
        expected = {"item_number", "name", "category", "unit", "price_limit", "gst_code", "is_active", "notes"}
        for route, args in self.routes()[2:]:
            response = self.get_page(route, args)
            self.assertContains(response, "r1-people-form", count=1)
            tags = form_helpers.FormElements(response.content.decode()).tags
            controls = [(tag, attrs) for tag, attrs in tags if tag in ("input", "select", "textarea") and attrs.get("name") in expected]
            self.assertEqual({a["name"] for _, a in controls}, expected)
            self.assertEqual(len(controls), 8)
            attrs = {a["name"]: a for _, a in controls}
            for name, length in (("item_number", "50"), ("name", "255"), ("category", "150")):
                self.assertEqual(attrs[name]["maxlength"], length)
            self.assertEqual(attrs["price_limit"]["step"], "0.01")
            self.assertEqual(attrs["is_active"]["type"], "checkbox")
            self.assertEqual(attrs["notes"]["rows"], "3")
            form = response.context["form"]
            self.assertEqual(list(form.fields["unit"].choices), list(SupportItem.Unit.choices))
            self.assertEqual(list(form.fields["gst_code"].choices), list(SupportItem.GSTCode.choices))
            self.assertContains(response, "Inactive items stay in records but cannot be selected for new shifts.")
            self.assertContains(response, "The system does not invent NDIS item numbers.")

    def test_list_keeps_filters_labels_and_inline_view_edit_targets(self):
        response = self.get_page("support_item_list", [])
        self.assertContains(response, 'class="support-item-action-row"', count=1)
        for label in ("Item number", "Name", "Category", "Unit", "Price limit", "GST", "Status", "Actions"):
            self.assertContains(response, 'data-label="' + label + '"', count=1)
        for route in ("support_item_detail", "support_item_edit"):
            self.assertContains(response, 'href="' + reverse(route, args=[self.item.pk]) + '"')
        for field in ("q", "is_active", "category"):
            self.assertContains(response, 'name="' + field + '"')
        self.assertContains(response, 'method="get"')
        filtered = self.client.get(reverse("support_item_list"), {"q": "DOES-NOT-EXIST"})
        self.assertContains(filtered, "No support items found.")
        self.assertContains(filtered, 'class="empty-cell"')

    def test_detail_keeps_all_original_values_and_actions(self):
        response = self.get_page("support_item_detail", [self.item.pk])
        self.assertContains(response, "Configuration")
        for value in ("QA-NOT-REAL-ITEM", "Fictional category", "Kilometre", "$100.00", "Taxable", "Active", "Fictional first line.", "Second line with &lt;escaped&gt; content."):
            self.assertContains(response, value)
        self.assertContains(response, "<dt>", count=7)
        for route, args in (("support_item_list", []), ("support_item_edit", [self.item.pk])):
            self.assertContains(response, 'href="' + reverse(route, args=args) + '"')

    def test_original_errors_are_rendered_under_fields_without_saving(self):
        count = SupportItem.objects.count()
        for route, args in self.routes()[2:]:
            response = self.client.post(reverse(route, args=args), {"item_number": "", "name": "", "unit": "hour", "gst_code": "gst_free", "price_limit": "-1.00"})
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "r1-support-items", count=1)
            self.assertContains(response, "Price limit cannot be negative.")
            self.assertContains(response, "This field is required.", count=2)
            self.assertEqual(SupportItem.objects.count(), count)
        self.item.refresh_from_db()
        self.assertEqual(self.item.price_limit, Decimal("100.00"))

    def test_navigation_and_form_security_markup_unchanged(self):
        for route, args in self.routes():
            response = self.get_page(route, args)
            nav = render_to_string("core/partials/admin_navigation_links.html", {"request": response.wsgi_request})
            self.assertContains(response, nav, count=2)
            self.assertContains(response, static("js/admin_nav.js"), count=1)
            self.assertContains(response, 'class="user-label"')
            self.assertContains(response, 'name="csrfmiddlewaretoken"', count=3 if route in ("support_item_create", "support_item_edit") else 2)

    def test_original_non_admin_get_and_post_permissions_remain(self):
        for user in self.other_users:
            self.client.force_login(user)
            for route, args in self.routes():
                url = reverse(route, args=args)
                self.assertEqual(self.client.get(url).status_code, 403)
                self.assertEqual(self.client.post(url, {}).status_code, 403)

    def test_support_item_css_is_not_loaded_by_other_accepted_pages(self):
        for route, args in (("participant_list", []), ("worker_detail", [self.worker.pk]), ("coordinator_edit", [self.coordinator.pk]), ("invoice_placeholder", [])):
            response = self.get_page(route, args)
            self.assertNotContains(response, static("css/r1_admin_support_items.css"))

    def test_scoped_css_keeps_action_row_and_mobile_labels(self):
        path = Path(settings.BASE_DIR) / "static/css/r1_admin_support_items.css"
        self.assertTrue(path.is_file(), "Missing support-items-only stylesheet")
        css = path.read_text(encoding="utf-8")
        for expected in (".r1-support-items", ".support-item-action-row", "flex-wrap:nowrap", "content:attr(data-label)", "select::picker(select)"):
            self.assertIn(expected, css)
        self.assertNotIn(".sidebar", css)
        self.assertNotIn(".topbar", css)
