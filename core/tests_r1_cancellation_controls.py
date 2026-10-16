"""Presentation and payload contracts for the cancellation-only enhancement."""
from pathlib import Path
import re
import shutil
import subprocess
from unittest import skipUnless

from django.conf import settings
from django.test import SimpleTestCase, TestCase
from django.templatetags.static import static
from django.urls import reverse

from core import tests_r1_worker_support as support_fixture
from scheduling.forms import ParticipantCancellationForm
from scheduling.models import ParticipantCancellation


class CancellationControlsTests(TestCase):
    setUpTestData = classmethod(support_fixture.WorkerSupportTests.setUpTestData.__func__)
    setUp = support_fixture.WorkerSupportTests.setUp
    payload = support_fixture.WorkerSupportTests.payload

    def test_empty_captions_preserve_required_and_all_real_choices(self):
        form = ParticipantCancellationForm()
        for name, caption in (("cancellation_type", "Select cancellation type"),
                              ("reason", "Select a reason")):
            field = form.fields[name]
            self.assertTrue(field.required)
            choices = list(field.choices)
            self.assertEqual(choices[0], ("", caption))
            self.assertEqual(choices[1:], list(ParticipantCancellation._meta.get_field(name).choices))
            self.assertIn(f'<option value="" selected>{caption}</option>', str(form[name]))
        empty = ParticipantCancellationForm(self.payload(cancellation_type="", reason=""))
        self.assertFalse(empty.is_valid())
        self.assertEqual(empty.errors.as_data()["reason"][0].code, "required")
        self.assertEqual(empty.errors.as_data()["cancellation_type"][0].code, "required")

    def test_native_fallback_and_stable_enhancement_hooks(self):
        response = self.client.get(self.url)
        html = response.content.decode()
        elements = support_fixture.Elements(html).items
        native = [a for t, a in elements if t == "input" and a.get("name") == "received_at"]
        self.assertEqual(len(native), 1)
        self.assertEqual(native[0]["type"], "datetime-local")
        self.assertIn("required", native[0])
        self.assertNotIn("hidden", native[0])
        self.assertContains(response, str(response.context["form"]["received_at"]), html=True)
        for suffix in ("", "-trigger", "-popover", "-apply", "-cancel", "-clear"):
            self.assertIn("data-cancellation-datetime" + suffix, html)
        for tag, attrs in elements:
            if tag == "button" and any(k.startswith("data-cancellation-") for k in attrs):
                self.assertEqual(attrs.get("type"), "button")
        self.assertContains(response, static("js/r1_cancellation_controls.js"), count=1)
        self.assertContains(response, static("js/date_time_picker.js"), count=1)
        profile = self.client.get(reverse("worker_profile"))
        self.assertNotContains(profile, "r1_cancellation_controls.js")

    def test_bound_values_and_arbitrary_minutes_keep_native_payload(self):
        for value in ("2026-10-12T00:57", "2026-10-12T12:59", "2026-10-12T23:01"):
            with self.subTest(value=value):
                response = self.client.post(self.url, self.payload(received_at=value, details=""))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, f'value="{value}"')
                form = response.context["form"]
                self.assertEqual(form["received_at"].value(), value)
                local = form.cleaned_data["received_at"]
                self.assertEqual(local.strftime("%Y-%m-%dT%H:%M"), value)
                self.assertIn("details", form.errors)
        self.assertFalse(ParticipantCancellation.objects.exists())

    def test_styled_choices_remain_required_native_selects_with_all_options(self):
        response = self.client.get(self.url)
        elements = support_fixture.Elements(response.content.decode()).items
        for name in ("cancellation_type", "reason"):
            with self.subTest(name=name):
                selects = [attrs for tag, attrs in elements
                           if tag == "select" and attrs.get("name") == name]
                self.assertEqual(len(selects), 1)
                self.assertEqual(selects[0]["id"], "id_" + name)
                self.assertIn("required", selects[0])
                for attr in ("hidden", "disabled", "multiple", "role", "tabindex"):
                    self.assertNotIn(attr, selects[0])
                self.assertContains(response, str(response.context["form"][name]), html=True)

    def test_scoped_focus_contract(self):
        path = Path(settings.BASE_DIR) / "static/css/r1_cancellation_controls.css"
        self.assertTrue(path.exists(), "Cancellation-only stylesheet must exist")
        css = path.read_text()
        self.assertNotIn("@import", css)
        for token in (".r1-cancellation", "outline: 3px solid", "outline-offset: 0",
                      "box-shadow: none", "var(--r1-blue-soft)", ":disabled",
                      "var(--r1-danger)", "font-size: 14px", "font-size: 16px"):
            self.assertIn(token, css)
        self.assertContains(self.client.get(self.url), static("css/r1_cancellation_controls.css"))


class CancellationNativeSelectStylesTests(SimpleTestCase):
    scope = ".app-shell.r1-worker-support .r1-cancellation"
    target = scope + " :is(#id_cancellation_type, #id_reason)"

    def test_only_choice_wrapper_chevrons_point_down_at_all_sizes(self):
        css = (Path(settings.BASE_DIR) / "static/css/r1_cancellation_controls.css").read_text()
        selector = self.scope + " .r1-native-select:has(> :is(#id_cancellation_type, #id_reason)) > .r1-icon"
        before_supports = css.split("@supports", 1)[0]
        self.assertIn(selector + " { transform: rotate(90deg); }", before_supports)

    def test_base_select_is_desktop_only_scoped_and_keeps_native_checkmarks(self):
        css = (Path(settings.BASE_DIR) / "static/css/r1_cancellation_controls.css").read_text()
        guard = re.search(
            r"@supports \(appearance: base-select\) and selector\(select::picker\(select\)\) \{"
            r"\s*@media \(min-width: 701px\) and \(hover: hover\) and \(pointer: fine\) \{", css)
        self.assertIsNotNone(guard, "Custom native pickers require both support and desktop pointer gates")
        rules = dict(re.findall(r"([^{}]+)\{([^{}]*)\}", css[guard.end():]))
        rules = {selector.strip(): body for selector, body in rules.items()}
        for selector in rules:
            for line in selector.splitlines():
                self.assertTrue(line.strip().startswith(self.target), line)
        appearance = self.target + ",\n    " + self.target + "::picker(select)"
        self.assertIn("appearance: base-select;", rules[appearance])
        self.assertEqual(css.count("appearance: base-select;"), 1)
        self.assertIn("display: none;", rules[self.target + "::picker-icon"])
        popup = rules[self.target + "::picker(select)"]
        for declaration in ("background: var(--r1-surface);", "border: 1px solid var(--r1-border);",
                            "border-radius: 8px;", "margin-block: 6px;", "padding: 4px;", "box-shadow:"):
            self.assertIn(declaration, popup)
        option = rules[self.target + " option"]
        for declaration in ("min-height: 44px;", "height: auto;", "padding: 8px 12px;",
                            "font-size: 16px;", "line-height: 24px;", "font-weight: 400;",
                            "white-space: normal;", "overflow-wrap: anywhere;"):
            self.assertIn(declaration, option)
        empty = rules[self.target + ' option[value=""]']
        self.assertIn("font-size: 14px;", empty)
        self.assertNotRegex(empty, r"display:\s*none|visibility:\s*hidden")
        states = rules[self.target + " option:is(:hover, :focus, :checked)"]
        self.assertIn("background: var(--r1-blue-soft);", states)
        self.assertIn("color: var(--r1-accent);", states)
        self.assertEqual(rules[self.target + " option::checkmark"].strip(), "color: var(--r1-accent);")


class CancellationDateTimeValuesTests(SimpleTestCase):
    @skipUnless(shutil.which("node"), "Node is unavailable; run the datetime value checks on a Node-enabled host")
    def test_local_wall_time_display_and_composition_without_rounding(self):
        path = Path(settings.BASE_DIR) / "static/js/r1_cancellation_controls.js"
        self.assertTrue(path.exists(), "Cancellation-only enhancement must exist")
        node = shutil.which("node")
        self.assertIsNotNone(node, "Node is needed for the focused datetime value checks")
        source = path.read_text()
        assertions = """
        const assert = require('node:assert/strict');
        assert.equal(formatDateTime('2026-10-12T00:57'), '12/10/2026 12:57 AM');
        assert.equal(formatDateTime('2026-10-12T12:59'), '12/10/2026 12:59 PM');
        assert.equal(formatDateTime('2026-10-12T13:01'), '12/10/2026 01:01 PM');
        assert.equal(formatDateTime(''), 'Select date and time');
        assert.equal(composeDateTime('2026-10-12', '12', '57', 'AM'), '2026-10-12T00:57');
        assert.equal(composeDateTime('2026-10-12', '12', '59', 'PM'), '2026-10-12T12:59');
        assert.equal(composeDateTime('2026-10-12', '1', '01', 'PM'), '2026-10-12T13:01');
        assert.equal(composeDateTime('', '1', '01', 'AM'), '');
        """
        instrumented = source.rsplit("})();", 1)[0] + assertions + "})();"
        result = subprocess.run([node, "-e", "global.document={querySelectorAll:()=>[]};" +
                                 instrumented], capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
