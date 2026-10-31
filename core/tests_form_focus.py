from html.parser import HTMLParser
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase, override_settings


class Stylesheets(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.links = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "link" and attrs.get("rel") == "stylesheet":
            self.links.append(attrs["href"])


@override_settings(STORAGES={
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
})
class FormFocusTests(SimpleTestCase):
    def test_all_page_families_load_one_shared_focus_policy_last(self):
        request = RequestFactory().get("/")
        request.user = AnonymousUser()
        for template in ("admin_base.html", "worker_base.html", "coordinator_base.html",
                         "r1/admin_people_form_base.html", "r1/coordinator_log_base.html",
                         "r1/worker_documents_base.html", "accounts/login.html"):
            with self.subTest(template=template):
                links = Stylesheets(render_to_string(template, request=request)).links
                self.assertEqual(sum("/css/form_focus.css" in href for href in links), 1)
                self.assertTrue(links[-1].endswith("/css/form_focus.css"))

    def css(self):
        path = Path(settings.BASE_DIR) / "static/css/form_focus.css"
        self.assertTrue(path.exists(), "Shared focus stylesheet is missing")
        return path.read_text(encoding="utf-8")

    def test_policy_uses_approved_invoice_focus_tokens(self):
        css = self.css()
        self.assertIn("--control-focus-border: #315bcb", css)
        self.assertIn("--control-focus-ring: #eaf1ff", css)
        self.assertIn("outline: 3px solid", css)
        self.assertIn("outline-offset: 0", css)
        self.assertIn("box-shadow: none", css)

    def test_policy_covers_existing_custom_control_triggers(self):
        css = self.css()
        for selector in ("[data-picker-trigger]", ".support-item-picker-trigger",
                         "[data-cancellation-datetime-trigger]", '[aria-expanded="true"]',
                         "select:open", ":focus-visible"):
            self.assertIn(selector, css)

    def test_explicit_errors_and_disabled_states_have_separate_priority(self):
        css = self.css()
        for selector in ('[aria-invalid="true"]', ".has-error", ".field-error",
                         ".errorlist", ":not(:disabled)", ':not([aria-disabled="true"])'):
            self.assertIn(selector, css)
        self.assertNotIn(":invalid", css, "Do not invent errors for empty required fields")

    def test_forced_colors_keeps_a_visible_focus_indicator(self):
        css = self.css()
        self.assertIn("forced-colors: active", css)
        self.assertIn("Highlight", css)
