from pathlib import Path

from django.test import SimpleTestCase


class ThemeTokenTests(SimpleTestCase):
    def test_theme_uses_soft_healthcare_palette_tokens(self):
        css = Path("static/css/app.css").read_text(encoding="utf-8")

        self.assertIn("--ink: #102033;", css)
        self.assertIn("--surface: #f6f8fb;", css)
        self.assertIn("--brand: #16877d;", css)
        self.assertIn("--sidebar: #1f4f4a;", css)
        self.assertIn("--sidebar-text: #e8f3f1;", css)
        self.assertIn("--sidebar-active: #dff3ef;", css)
        self.assertIn("--sidebar-active-text: #0f5f58;", css)

    def test_theme_uses_lighter_typography_and_spacing_tokens(self):
        css = Path("static/css/app.css").read_text(encoding="utf-8")

        self.assertIn("--shadow: 0 6px 18px rgba(16, 32, 51, 0.035);", css)
        self.assertIn("--weight-action: 600;", css)
        self.assertIn("--weight-heading: 700;", css)
        self.assertIn("--weight-label: 650;", css)
        self.assertIn("font-weight: var(--weight-action);", css)
        self.assertIn("font-weight: var(--weight-heading);", css)

    def test_roster_operational_polish_classes_are_styled(self):
        css = Path("static/css/app.css").read_text(encoding="utf-8")

        self.assertIn(".quick-filter-row", css)
        self.assertIn(".quick-filter-row .button.active", css)
        self.assertIn(".roster-bulk-action-card", css)
        self.assertIn(".roster-table .roster-next-action-cell", css)
