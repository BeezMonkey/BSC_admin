from pathlib import Path

from django.test import SimpleTestCase


class ThemeTokenTests(SimpleTestCase):
    def test_theme_uses_light_admin_palette_tokens(self):
        css = Path("static/css/app.css").read_text(encoding="utf-8")

        self.assertIn("--ink: #1f2937;", css)
        self.assertIn("--surface: #f7f9fb;", css)
        self.assertIn("--brand: #128b7e;", css)
        self.assertIn("--sidebar: #ffffff;", css)
        self.assertIn("--sidebar-text: #263445;", css)
        self.assertIn("--sidebar-active: #e7f5f3;", css)
        self.assertIn("--sidebar-active-text: #0f766e;", css)

    def test_theme_uses_lighter_typography_and_spacing_tokens(self):
        css = Path("static/css/app.css").read_text(encoding="utf-8")

        self.assertIn("--shadow: 0 1px 2px rgba(15, 23, 42, 0.035);", css)
        self.assertIn("--weight-action: 600;", css)
        self.assertIn("--weight-heading: 650;", css)
        self.assertIn("--weight-label: 650;", css)
        self.assertIn("font-weight: var(--weight-action);", css)
        self.assertIn("font-weight: var(--weight-heading);", css)

    def test_admin_sidebar_groups_real_v1_modules(self):
        template = Path("templates/admin_base.html").read_text(encoding="utf-8")

        self.assertIn('class="sidebar-section-label">Operations</span>', template)
        self.assertIn('class="sidebar-section-label">Business</span>', template)
        self.assertIn('class="sidebar-section-label">Compliance</span>', template)
        self.assertIn(">Dashboard</a>", template)
        self.assertIn(">Participants</a>", template)
        self.assertIn(">Support Workers</a>", template)
        self.assertIn(">Roster</a>", template)
        self.assertIn("url_name == 'roster_planner'", template)
        self.assertIn(">Service Logs</a>", template)
        self.assertIn(">Invoices</a>", template)
        self.assertIn(">Documents</a>", template)
        self.assertIn(">Support Items</a>", template)
        self.assertIn(">Audit Logs</a>", template)
        self.assertNotIn(">CRM</a>", template)
        self.assertNotIn(">Forms</a>", template)

    def test_roster_operational_polish_classes_are_styled(self):
        css = Path("static/css/app.css").read_text(encoding="utf-8")

        self.assertIn(".quick-filter-row", css)
        self.assertIn(".quick-filter-row .button.active", css)
        self.assertIn(".roster-bulk-action-card", css)
        self.assertIn(".roster-table .roster-next-action-cell", css)
        self.assertIn(".planner-scroll-frame", css)
        self.assertIn(".planner-add-shift", css)
        self.assertIn(".planner-shift-time", css)
        self.assertIn(".planner-shift-meta", css)
        self.assertIn("border-collapse: collapse;", css)
        self.assertIn(".planner-shift-tile-footer", css)
        self.assertIn("minmax(150px, 1fr)", css)
