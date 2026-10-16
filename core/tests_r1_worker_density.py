"""Desktop-only presentation contracts; browser checks cover rendered sizes."""

from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

from core.tests_r1_hover_corners import css_rules


SHELL = "html body .app-shell.r1-worker.r1-ui"
DESKTOP = "(min-width: 981px)"


class R1WorkerDensityTests(SimpleTestCase):
    def setUp(self):
        self.root = Path(settings.BASE_DIR)
        path = self.root / "static/css/r1_worker_density.css"
        self.source = path.read_text(encoding="utf-8") if path.exists() else ""
        self.rules = list(css_rules(self.source))

    def declarations(self, selector, media=DESKTOP):
        matches = [d for query, target, d in self.rules
                   if query == media and target == selector]
        self.assertTrue(matches, f"Missing density rule: {media} {selector}")
        return {k: v for d in matches for k, v in d.items()}

    def test_three_r1_entry_points_load_density_once_after_page_styles(self):
        for template, owner in (
            ("r1/worker_navigation_base.html", "r1_worker_navigation.css"),
            ("r1/worker_support_base.html", "r1_worker_support.css"),
            ("service_logs/worker_service_log_form.html", "r1_worker_logs.css"),
        ):
            with self.subTest(template=template):
                text = (self.root / "templates" / template).read_text(encoding="utf-8")
                self.assertEqual(text.count("css/r1_worker_density.css"), 1)
                self.assertLess(text.index(owner), text.index("r1_worker_density.css"))
        self.assertNotIn("r1_worker_density.css", (self.root / "templates/worker_base.html")
                         .read_text(encoding="utf-8"))

    def test_desktop_heading_uses_approved_24_pixel_size(self):
        self.assertEqual(self.declarations(SHELL + " h1"),
                         {"font-size": "24px", "line-height": "32px"})

    def test_subtitles_include_the_existing_nested_log_header_markup(self):
        self.assertEqual(self.declarations(
            SHELL + " .worker-log-form-header p, " + SHELL + " .r1-support-heading > p",
        ), {"font-size": "14px", "line-height": "20px"})

    def test_only_view_log_nowrap_rule_can_apply_to_mobile(self):
        self.assertTrue(self.rules)
        for media, selector, declarations in self.rules:
            self.assertTrue(selector.startswith(SHELL))
            if media != DESKTOP:
                self.assertEqual(media, "")
                self.assertEqual(selector, SHELL + " .r1-log-view")
                self.assertEqual(declarations, {"white-space": "nowrap",
                                                "overflow-wrap": "normal"})

    def test_controls_keep_native_field_types_and_minute_popup_sizes(self):
        matches = [(s, d) for m, s, d in self.rules if m == DESKTOP
                   and "height" in d and "input:not" in s]
        self.assertEqual(len(matches), 1)
        selector, declarations = matches[0]
        self.assertIn("select:not([data-cancellation-hour])", selector)
        self.assertIn(":not([data-cancellation-minute])", selector)
        self.assertIn(":not([data-cancellation-period])", selector)
        self.assertEqual(declarations["height"], "40px")
        self.assertEqual(declarations["min-height"], "40px")
        self.assertEqual(declarations["font-size"], "14px")
        self.assertNotIn("appearance", self.source)

    def test_rows_shrink_but_allow_long_content_to_grow(self):
        self.assertEqual(self.declarations(SHELL + " .r1-shift-table td"),
                         {"height": "64px"})
        self.assertNotIn("max-height", self.source)
        self.assertNotIn("text-overflow", self.source)

    def test_view_log_has_dedicated_action_space_without_shrinking(self):
        self.assertEqual(self.declarations(SHELL + " .r1-log-view"),
                         {"width": "max-content", "min-width": "80px", "flex-shrink": "0"})
        for column, width in ((4, "128px"), (5, "112px")):
            self.assertEqual(self.declarations(SHELL + f" .r1-log-table th:nth-child({column})"),
                             {"width": width})

    def test_override_changes_only_approved_dimension_properties(self):
        allowed = {"font-size", "line-height", "font-weight", "padding", "height",
                   "min-height", "width", "min-width", "gap", "white-space",
                   "overflow-wrap", "flex-shrink"}
        self.assertTrue(self.rules)
        for _, _, declarations in self.rules:
            self.assertLessEqual(set(declarations), allowed)
