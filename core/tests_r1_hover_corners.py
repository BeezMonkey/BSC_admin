"""Structural CSS contracts; browser behavior is verified separately."""

from pathlib import Path
import re

from django.conf import settings
from django.test import SimpleTestCase


DESKTOP = "(min-width: 981px)"
SHELL = ".app-shell.r1-worker-navigation"
SUMMARY = SHELL + " .worker-dashboard-page .action-summary-item"
TABLE = SHELL + " .worker-shift-page .r1-shift-table"


def css_rules(source):
    """Read the stylesheet's flat rules and single-level media blocks."""
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.S)
    media_pattern = r"@media\s+([^{}]+)\{((?:[^{}]|\{[^{}]*\})*)\}"

    def rules(body, media):
        for match in re.finditer(r"([^{}]+)\{([^{}]*)\}", body):
            selector = " ".join(match[1].split())
            declarations = dict(
                (name.strip(), value.strip())
                for declaration in match[2].split(";") if declaration.strip()
                for name, value in [declaration.split(":", 1)]
            )
            yield media, selector, declarations

    yield from rules(re.sub(media_pattern, "", source), "")
    for match in re.finditer(media_pattern, source):
        yield from rules(match[2], " ".join(match[1].split()))


class R1HoverCornersTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.rules = list(css_rules(
            (Path(settings.BASE_DIR) / "static/css/r1_worker_navigation.css")
            .read_text(encoding="utf-8")
        ))

    def declarations(self, media, selector):
        matches = [declarations for query, target, declarations in self.rules
                   if query == media and target == selector]
        self.assertTrue(matches, f"Missing CSS rule: {media} {selector}")
        return {key: value for declarations in matches
                for key, value in declarations.items()}

    def test_each_status_has_matching_desktop_hover_and_keyboard_feedback(self):
        for status, token in (("needs-attention", "warning"),
                              ("ready-for-log", "accent"), ("completed", "success")):
            with self.subTest(status=status):
                selector = SUMMARY + f".{status}:is(:hover, :focus-visible)"
                self.assertEqual(self.declarations(DESKTOP, selector), {
                    "border-color": f"var(--r1-{token})",
                    "background": (
                        f"color-mix(in srgb, var(--r1-{token}) 5%, var(--r1-surface))"
                    ),
                })
                self.assertEqual(
                    self.declarations(DESKTOP, SUMMARY + f".{status}")["color"],
                    f"var(--r1-{token})",
                )
        self.assertEqual(self.declarations(DESKTOP, SUMMARY + " strong")["color"],
                         "inherit")

    def test_desktop_transitions_only_border_and_background_without_resizing(self):
        declarations = self.declarations(DESKTOP, SUMMARY)
        self.assertEqual(declarations.get("transition"),
                         "border-color 150ms, background-color 150ms")
        self.assertEqual(declarations["border"], "1px solid var(--r1-border)")
        self.assertEqual(declarations["padding"], "16px 20px")
        self.assertEqual(declarations["min-height"], "134px")

    def test_reduced_motion_disables_only_desktop_summary_transitions(self):
        self.assertEqual(self.declarations(
            DESKTOP + " and (prefers-reduced-motion: reduce)", SUMMARY,
        ), {"transition": "none"})

    def test_table_and_only_outer_cells_have_eight_pixel_corners(self):
        expected = {
            TABLE: {"border-radius": "8px"},
            TABLE + " thead th:first-child": {"border-top-left-radius": "8px"},
            TABLE + " thead th:last-child": {"border-top-right-radius": "8px"},
            TABLE + " tbody:last-child > .shift-list-item:last-child > td:first-child": {
                "border-bottom-left-radius": "8px",
            },
            TABLE + " tbody:last-child > .shift-list-item:last-child > td:last-child": {
                "border-bottom-right-radius": "8px",
            },
        }
        for selector, declarations in expected.items():
            with self.subTest(selector=selector):
                self.assertEqual(self.declarations(DESKTOP, selector), declarations)
        for media, selector, declarations in self.rules:
            if TABLE in selector and any("radius" in key for key in declarations):
                self.assertEqual(media, DESKTOP)
                self.assertIn(selector, expected, "Internal table rows must stay square")

    def test_feedback_keeps_focus_outline_and_table_actions_unclipped(self):
        for media, selector, declarations in self.rules:
            if SUMMARY in selector:
                self.assertFalse(any(key.startswith("outline") for key in declarations))
                self.assertNotIn("box-shadow", declarations)
                self.assertNotIn("transform", declarations)
                if ":hover" in selector or ":focus-visible" in selector:
                    self.assertEqual(media, DESKTOP)
                    self.assertLessEqual(set(declarations), {"border-color", "background"})
            if TABLE in selector:
                self.assertFalse(any(key.startswith("overflow") for key in declarations))
                self.assertNotIn("clip-path", declarations)
        self.assertEqual(self.declarations("", SHELL + " .r1-navigation-table")
                         ["border-collapse"], "separate")

    def test_existing_mobile_summary_and_table_presentation_is_retained(self):
        mobile = "(max-width: 980px)"
        summary = self.declarations(mobile, SHELL + " .action-summary-item")
        self.assertEqual(summary["border-radius"], "12px")
        self.assertEqual(summary["padding"], "16px")
        self.assertEqual(summary["background"], "var(--r1-accent-soft)")
        self.assertNotIn("transition", summary)
        self.assertEqual(self.declarations(mobile, SHELL + " .r1-navigation-table"),
                         {"display": "block", "background": "transparent"})
