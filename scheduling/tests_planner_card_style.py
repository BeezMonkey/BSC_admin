import re

from django.conf import settings
from django.test import SimpleTestCase


class PlannerCardStyleTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.css = (settings.BASE_DIR / "static/css/holiday_reminders.css").read_text(
            encoding="utf-8"
        )

    def test_time_matches_compact_name_size(self):
        for selector, size in (
            ("planner-shift-time", "0.72rem"),
            ("planner-shift-primary", "0.72rem"),
            ("planner-shift-meta", "0.72rem"),
        ):
            with self.subTest(selector=selector):
                self.assertRegex(
                    self.css, rf"\.{selector} \{{[^}}]*font-size: {re.escape(size)};"
                )

    def test_time_uses_semibold_weight(self):
        self.assertRegex(
            self.css, r"\.planner-shift-time \{[^}]*font-weight: 600;"
        )

    def test_only_text_spacing_is_tightened(self):
        self.assertIn(".planner-shift-copy { display: grid; gap: 0.25rem; }", self.css)
        for selector in ("planner-shift-time", "planner-shift-primary", "planner-shift-meta"):
            with self.subTest(selector=selector):
                self.assertRegex(self.css, rf"\.{selector} \{{[^}}]*line-height: 1\.3;")
        self.assertRegex(self.css, r"\.planner-shift-tile \{[^}]*gap: 0\.6rem;")
        self.assertRegex(
            self.css, r"\.planner-shift-tile-footer \{[^}]*padding-top: 0\.45rem; gap: 0\.4rem;"
        )

    def test_status_wrap_is_scoped_to_planner_cards(self):
        for declaration in (
            "font-size: 0.69rem;",
            "min-width: 0;",
            "max-width: 100%;",
            "white-space: normal;",
            "overflow-wrap: anywhere;",
            "line-height: 1.25;",
        ):
            with self.subTest(declaration=declaration):
                self.assertRegex(
                    self.css,
                    rf"\.planner-shift-tile \.status-pill \{{[^}}]*{re.escape(declaration)}",
                )

    def test_time_segments_and_action_targets_are_preserved(self):
        self.assertIn(".planner-time-part { white-space: nowrap; }", self.css)
        self.assertNotRegex(self.css, r"\.planner-shift-action(?:\s|:)")

    def test_bottom_padding_compensates_for_icon_target_whitespace(self):
        self.assertRegex(
            self.css,
            r"\.planner-shift-tile \{[^}]*padding: 0\.65rem 0\.55rem 0\.3rem;",
        )

    def test_all_planner_views_reserve_width_for_four_action_targets(self):
        self.assertRegex(
            self.css,
            r"\.planner-date-grid \{[^}]*grid-template-columns: repeat\(7, minmax\(10rem, 1fr\)\);[^}]*min-width: 70rem;",
        )
        self.assertRegex(
            self.css,
            r"\.planner-resource-grid \{[^}]*--planner-resource-day-width: 10rem;",
        )
