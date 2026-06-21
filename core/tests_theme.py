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

    def test_invoice_settings_logo_field_is_styled(self):
        css = Path("static/css/app.css").read_text(encoding="utf-8")
        template = Path("templates/invoices/invoice_settings.html").read_text(encoding="utf-8")

        self.assertIn(".invoice-logo-field", css)
        self.assertIn(".invoice-logo-current", css)
        self.assertIn("object-fit: contain;", css)
        self.assertIn("overflow-wrap: anywhere;", css)
        self.assertIn(".checkbox-row", css)
        self.assertIn('class="field invoice-logo-field"', template)
        self.assertIn("Remove current logo", template)

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
        self.assertIn(".planner-week-toolbar", css)
        self.assertIn(".planner-scope-chips", css)
        self.assertIn(".planner-scope-chip", css)
        self.assertIn(".planner-add-shift", css)
        self.assertIn(".planner-add-shift-square", css)
        self.assertIn(".planner-shift-time", css)
        self.assertIn(".planner-shift-meta", css)
        self.assertIn("border-collapse: collapse;", css)
        self.assertIn(".planner-shift-tile-footer", css)
        self.assertIn("minmax(140px, 1fr)", css)
        self.assertIn("border-radius: 5px;", css)
        self.assertIn("margin: -1rem -1rem 1rem;", css)
        self.assertIn("@media (max-width: 1280px)", css)
        self.assertIn("grid-template-columns: repeat(3, minmax(0, 1fr));", css)
        self.assertIn(".planner-filter-bar-compact button,\n  .planner-filter-bar-compact .button", css)
        self.assertIn(".planner-filter-actions", css)
        self.assertIn("grid-template-columns: repeat(2, minmax(0, 1fr));", css)

        template = Path("templates/scheduling/roster_planner.html").read_text(encoding="utf-8")
        self.assertIn('class="planner-filter-actions"', template)

    def test_planner_copy_paste_actions_use_purple_accent(self):
        css = Path("static/css/app.css").read_text(encoding="utf-8")

        self.assertIn("--planner-copy-bg: #f3e8ff;", css)
        self.assertIn("--planner-copy-border: #d8b4fe;", css)
        self.assertIn("--planner-copy-ink: #7e22ce;", css)
        self.assertIn(".planner-paste-shift", css)
        self.assertIn(".planner-paste-shift {\n  display: inline-flex;", css)
        self.assertIn("padding: 0;\n  color: var(--planner-copy-ink);", css)
        self.assertIn(".planner-shift-action-active", css)
        self.assertIn(".planner-shift-action-active:hover,\n.planner-shift-action-active:focus", css)

    def test_planner_delete_confirmation_modal_assets_exist(self):
        css = Path("static/css/app.css").read_text(encoding="utf-8")
        script = Path("static/js/shift_modal.js").read_text(encoding="utf-8")

        self.assertIn(".shift-delete-confirm-card", css)
        self.assertIn(".shift-modal-delete-button", css)
        self.assertIn(".js-shift-delete-trigger", script)
        self.assertIn("Delete shift?", script)
        self.assertIn("data-shift-delete-confirm", script)
