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
