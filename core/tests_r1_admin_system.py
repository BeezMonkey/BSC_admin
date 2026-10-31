from pathlib import Path

from django.conf import settings
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.test import TestCase, override_settings
from django.urls import reverse

from core import tests_r1_admin_people_forms as form_helpers
from core import tests_r1_admin_people_lists as people_fixtures
from core.models import AuditLog
from invoices.forms import InvoiceSettingsForm
from invoices.models import InvoiceSettings


@override_settings(STORAGES={
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
})
class R1AdminSystemPagesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        people_fixtures.R1AdminPeopleListTests.setUpTestData.__func__(cls)
        cls.profile = InvoiceSettings.objects.create(
            business_name="Fictional Care Example Only", abn="QA-NOT-REAL",
            phone="0400 000 000", email="fictional@example.invalid",
            address="12 Fictional Example Street\nWest End QLD 4101",
            bank_name="Fictional Example Bank", account_name="Fictional account only",
            bsb="QA-000-000", account_number="QA-NOT-REAL-0001",
            invoice_prefix="DEMO", next_invoice_sequence=42, accent_colour="#315bcb",
            logo="invoice_settings/logos/fictional-logo.png",
        )
        cls.event = AuditLog.objects.create(
            actor=cls.admin, action=AuditLog.Action.COORDINATION_LOG_APPROVED,
            object_type="FictionalObject", object_id="QA-ONLY-1",
            summary="Fictional first line.\nSecond line with <escaped> content.",
        )

    def setUp(self):
        self.client.force_login(self.admin)

    def routes(self):
        return [("invoice_settings", []), ("audit_log_list", []),
                ("audit_log_detail", [self.event.pk])]

    def get_page(self, route, args):
        response = self.client.get(reverse(route, args=args))
        self.assertEqual(response.status_code, 200)
        return response

    def test_three_pages_have_content_only_approved_styles(self):
        for route, args in self.routes():
            with self.subTest(route=route):
                response = self.get_page(route, args)
                self.assertContains(response, "r1-admin-system", count=1)
                for asset in ("r1_tokens.css", "r1_admin_people_forms.css", "r1_admin_system.css", "form_focus.css"):
                    self.assertContains(response, static("css/" + asset), count=1)
                self.assertNotContains(response, static("css/r1_shell.css"))
                self.assertContains(response, '<div class="app-shell" data-admin-theme>')

    def test_settings_keeps_original_fields_attributes_and_three_groups(self):
        response = self.get_page("invoice_settings", [])
        expected = set(InvoiceSettingsForm.Meta.fields) | {"remove_logo"}
        controls = [(tag, attrs) for tag, attrs in form_helpers.FormElements(response.content.decode()).tags
                    if tag in ("input", "select", "textarea") and attrs.get("name") in expected]
        self.assertEqual(len(controls), 14)
        self.assertEqual({a["name"] for _, a in controls}, expected)
        attrs = {a["name"]: a for _, a in controls}
        for name, length in (("business_name", "120"), ("abn", "30"), ("invoice_prefix", "12"), ("accent_colour", "7")):
            self.assertEqual(attrs[name]["maxlength"], length)
        self.assertEqual(attrs["next_invoice_sequence"]["min"], "0")
        self.assertEqual(attrs["accent_colour"]["type"], "text")
        self.assertEqual(attrs["logo"]["type"], "file")
        self.assertEqual(attrs["remove_logo"]["type"], "checkbox")
        self.assertEqual(attrs["address"]["rows"], "3")
        for title in ("Business Profile", "Invoice Numbering", "Payment Details"):
            self.assertContains(response, title)
        for value in ("fictional-logo.png", "Remove current logo", "Save Settings", "future invoice PDFs."):
            self.assertContains(response, value)
        self.assertContains(response, 'class="form-grid numbering-grid"', count=1)
        self.assertContains(response, "r1-people-form", count=1)

    def test_settings_original_no_logo_branch_is_retained(self):
        InvoiceSettings.objects.filter(pk=self.profile.pk).update(logo="")
        response = self.get_page("invoice_settings", [])
        self.assertContains(response, "No logo uploaded yet.")
        self.assertContains(response, 'name="logo"', count=1)
        self.assertNotContains(response, 'name="remove_logo"')
        self.assertContains(response, "r1-admin-system", count=1)

    def test_settings_original_errors_are_rendered_without_saving(self):
        before = InvoiceSettings.objects.values().get(pk=self.profile.pk)
        data = {name: getattr(self.profile, name) for name in InvoiceSettingsForm.Meta.fields if name != "logo"}
        data.update(business_name="", invoice_prefix="", email="invalid-address",
                    next_invoice_sequence="-1", accent_colour="#GGGGGG")
        response = self.client.post(reverse("invoice_settings"), data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "r1-admin-system", count=1)
        self.assertEqual(set(response.context["form"].errors), {
            "business_name", "email", "invoice_prefix", "next_invoice_sequence", "accent_colour"})
        for message in ("Enter a valid email address.", "Ensure this value is greater than or equal to 0.",
                        "Enter a valid hex colour, for example #6f2c80."):
            self.assertContains(response, message)
        self.assertEqual(InvoiceSettings.objects.values().get(pk=self.profile.pk), before)
        self.assertEqual(AuditLog.objects.count(), 1)

    def test_audit_list_keeps_original_columns_time_link_and_empty_state(self):
        response = self.get_page("audit_log_list", [])
        for label in ("Time", "Actor", "Action", "Object", "Summary"):
            self.assertContains(response, 'data-label="' + label + '"', count=1)
        self.assertContains(response, 'href="' + reverse("audit_log_detail", args=[self.event.pk]) + '"')
        self.assertContains(response, "Coordination log approved")
        self.assertContains(response, "FictionalObject QA-ONLY-1")
        self.assertNotContains(response, 'name="q"')
        AuditLog.objects.all().delete()
        empty = self.get_page("audit_log_list", [])
        self.assertContains(empty, "No audit logs yet.")
        self.assertContains(empty, "Key business actions will appear here as the system is used.")
        self.assertContains(empty, 'class="audit-empty"', count=1)

    def test_audit_detail_keeps_original_values_system_fallback_and_back_link(self):
        response = self.get_page("audit_log_detail", [self.event.pk])
        self.assertContains(response, "<dt>", count=5)
        for value in ("b091-admin", "coordination_log_approved", "FictionalObject", "QA-ONLY-1",
                      "Fictional first line.", "Second line with &lt;escaped&gt; content."):
            self.assertContains(response, value)
        self.assertContains(response, 'href="' + reverse("audit_log_list") + '"')
        self.assertContains(response, 'class="card detail-card"', count=1)
        AuditLog.objects.filter(pk=self.event.pk).update(actor=None)
        system = self.get_page("audit_log_detail", [self.event.pk])
        self.assertContains(system, "<dd>System</dd>")

    def test_navigation_links_and_form_security_are_unchanged(self):
        for route, args in self.routes():
            response = self.get_page(route, args)
            nav = render_to_string("core/partials/admin_navigation_links.html", {"request": response.wsgi_request})
            self.assertContains(response, nav, count=2)
            self.assertContains(response, static("js/admin_nav.js"), count=1)
            self.assertContains(response, 'class="user-label"')
            self.assertContains(response, 'name="csrfmiddlewaretoken"', count=3 if route == "invoice_settings" else 2)
        response = self.get_page("invoice_settings", [])
        self.assertContains(response, 'method="post" enctype="multipart/form-data" novalidate')
        self.assertContains(response, 'href="' + reverse("invoice_placeholder") + '"')

    def test_original_non_admin_get_post_permissions_and_anonymous_login_remain(self):
        for user in self.other_users:
            self.client.force_login(user)
            for route, args in self.routes():
                url = reverse(route, args=args)
                self.assertEqual(self.client.get(url).status_code, 403)
                self.assertEqual(self.client.post(url, {}).status_code, 403)
        self.client.logout()
        for route, args in self.routes():
            self.assertEqual(self.client.get(reverse(route, args=args)).status_code, 302)

    def test_system_css_is_not_loaded_by_other_accepted_pages(self):
        for route, args in (("support_item_list", []), ("participant_list", []),
                            ("worker_detail", [self.worker.pk]), ("invoice_placeholder", [])):
            response = self.get_page(route, args)
            self.assertNotContains(response, static("css/r1_admin_system.css"))

    def test_scoped_css_keeps_mobile_values_file_button_and_unframed_detail(self):
        path = Path(settings.BASE_DIR) / "static/css/r1_admin_system.css"
        self.assertTrue(path.is_file(), "Missing system-pages-only stylesheet")
        css = path.read_text(encoding="utf-8")
        for value in (".r1-admin-system", "content:attr(data-label)", "min-width:0", "max-width:100%",
                      "::file-selector-button", ".detail-list", "numbering-grid",
                      ".numbering-grid .field>span:first-child"):
            self.assertIn(value, css)
        self.assertNotIn(".sidebar", css)
        self.assertNotIn(".topbar", css)
        self.assertNotIn(":root", css)
