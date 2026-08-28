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
        self.assertIn(".invoice-logo-placeholder", css)
        self.assertIn("overflow-wrap: anywhere;", css)
        self.assertIn(".checkbox-row", css)
        self.assertIn('class="field invoice-logo-field"', template)
        self.assertIn('class="invoice-logo-placeholder"', template)
        self.assertIn("Remove current logo", template)
        self.assertNotIn('alt="Current logo"', template)

    def test_invoice_create_table_and_filter_polish_assets_exist(self):
        css = Path("static/css/app.css").read_text(encoding="utf-8")
        template = Path("templates/invoices/invoice_form.html").read_text(encoding="utf-8")

        self.assertIn(".invoice-preview-filter", css)
        self.assertIn(".invoice-preview-table", css)
        self.assertIn(".invoice-preview-empty-state", css)
        self.assertIn(".invoice-preview-table th", css)
        self.assertIn(".invoice-preview-table td", css)
        self.assertIn(".invoice-preview-hours-cell", css)
        self.assertIn(".invoice-preview-table .status-pill", css)
        self.assertIn("font-weight: 400;", css)
        self.assertIn("border-bottom: 1px solid #e3ebf2;", css)
        self.assertIn('class="invoice-preview-empty-state empty-state"', template)
        self.assertIn('class="invoice-preview-hours-cell"', template)

    def test_admin_filter_and_table_system_polish_assets_exist(self):
        css = Path("static/css/app.css").read_text(encoding="utf-8")

        self.assertIn(".filter-bar label", css)
        self.assertIn(".filter-bar input,\n.filter-bar select", css)
        self.assertIn(".filter-bar > button,\n.filter-bar > .button", css)
        self.assertIn("height: 2.38rem;", css)
        self.assertIn("border-color: #d6e1eb;", css)
        self.assertIn(".table-card th,\n.table-card td", css)
        self.assertIn("border-bottom: 1px solid #e3ebf2;", css)
        self.assertIn(".table-card td", css)
        self.assertIn("font-weight: 400;", css)
        self.assertIn(".numeric-cell", css)
        self.assertIn("text-align: right;", css)
        self.assertIn("font-variant-numeric: tabular-nums;", css)
        self.assertIn("td.actions", css)
        self.assertIn("justify-content: flex-end;", css)

    def test_admin_numeric_table_cells_use_alignment_hooks(self):
        invoice_list = Path("templates/invoices/invoice_list.html").read_text(encoding="utf-8")
        service_logs = Path("templates/service_logs/service_log_list.html").read_text(encoding="utf-8")
        support_items = Path("templates/scheduling/support_item_list.html").read_text(encoding="utf-8")

        self.assertIn('class="numeric-cell"', invoice_list)
        self.assertIn('class="service-log-hours-cell numeric-cell"', service_logs)
        self.assertIn('class="numeric-cell"', support_items)

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

    def test_worker_responsive_navigation_assets_exist(self):
        css = Path("static/css/app.css").read_text(encoding="utf-8")
        script = Path("static/js/worker_nav.js").read_text(encoding="utf-8")

        self.assertIn(".worker-mobile-menu-button", css)
        self.assertIn(".worker-mobile-menu-icon", css)
        self.assertIn("width: 2.35rem;", css)
        self.assertIn("border-radius: 10px;", css)
        self.assertIn("box-shadow: 0 1px 2px rgba(15, 23, 42, 0.08);", css)
        self.assertIn(".worker-mobile-menu-icon {\n    width: 1rem;", css)
        self.assertIn(".worker-mobile-drawer", css)
        self.assertIn(".worker-mobile-drawer-backdrop", css)
        self.assertIn(".worker-nav-open", css)
        self.assertIn("@media (max-width: 980px)", css)
        self.assertIn("overflow-x: visible;", css)
        self.assertIn("worker-mobile-menu-button", script)
        self.assertIn("worker-nav-open", script)
        self.assertIn("Escape", script)

        template = Path("templates/worker_base.html").read_text(encoding="utf-8")
        self.assertIn('class="worker-mobile-menu-icon"', template)

    def test_worker_mobile_content_polish_assets_exist(self):
        css = Path("static/css/app.css").read_text(encoding="utf-8")

        self.assertIn(".worker-dashboard-page", css)
        self.assertIn(".worker-priority-panel", css)
        self.assertIn(".worker-tool-grid", css)
        self.assertIn(".worker-tool-card", css)
        self.assertIn(".worker-shift-page", css)
        self.assertIn(".shift-list-actions", css)
        self.assertIn(".worker-shift-page .shift-list-item", css)

    def test_worker_shift_mobile_density_assets_exist(self):
        css = Path("static/css/app.css").read_text(encoding="utf-8")

        self.assertIn(".worker-shift-toolbar", css)
        self.assertIn(".worker-shift-page .shift-summary", css)
        self.assertIn(".shift-summary > span", css)
        self.assertIn(".worker-shift-page .shift-summary > span", css)
        self.assertIn(".shift-summary-attention", css)
        self.assertIn(".shift-summary-upcoming", css)
        self.assertIn(".shift-summary-completed", css)
        self.assertIn(".shift-summary-count", css)
        self.assertIn(".worker-shift-page .shift-filter-nav", css)
        self.assertIn(".shift-list-item-top", css)
        self.assertIn(".shift-list-status-row", css)
        self.assertIn(".shift-list-primary-action", css)
        self.assertIn(".shift-list-view-action", css)
        self.assertIn("justify-content: space-between;", css)
        self.assertIn("grid-template-columns: repeat(2, minmax(0, 1fr));", css)

    def test_worker_shift_mobile_flow_polish_assets_exist(self):
        css = Path("static/css/app.css").read_text(encoding="utf-8")

        self.assertIn(".shift-list-secondary-action", css)
        self.assertIn("overflow-wrap: anywhere;", css)
        self.assertIn("@media (max-width: 380px)", css)
        self.assertIn("@media (max-width: 340px)", css)
        self.assertIn("grid-template-columns: 1fr;", css)
        self.assertIn("touch-action: manipulation;", css)

    def test_worker_service_log_mobile_form_assets_exist(self):
        css = Path("static/css/app.css").read_text(encoding="utf-8")

        self.assertIn(".worker-service-log-form-page", css)
        self.assertIn(".worker-log-shift-summary", css)
        self.assertIn(".worker-log-field-grid", css)
        self.assertIn(".worker-log-notes-grid", css)
        self.assertIn(".worker-log-form-actions", css)
        self.assertIn(".worker-service-log-form-page textarea", css)
        self.assertIn(".worker-service-log-form-page .field", css)
        self.assertIn(".worker-service-log-form-page input", css)
        self.assertIn("max-inline-size: 100%;", css)

    def test_worker_service_log_time_inputs_are_ios_contained(self):
        css = Path("static/css/app.css").read_text(encoding="utf-8")

        self.assertIn('.worker-service-log-form-page input[type="time"]', css)
        self.assertIn("display: block;", css)
        self.assertIn("box-sizing: border-box;", css)
        self.assertIn("max-width: 100%;", css)

    def test_worker_service_log_time_inputs_have_ios_safari_override(self):
        css = Path("static/css/app.css").read_text(encoding="utf-8")

        self.assertIn("@supports (-webkit-touch-callout: none)", css)
        self.assertIn('.worker-service-log-form-page input[type="time"]', css)
        self.assertIn("-webkit-appearance: none;", css)
        self.assertIn("width: -webkit-fill-available;", css)
        self.assertIn("max-width: -webkit-fill-available;", css)

    def test_worker_detail_mobile_polish_assets_exist(self):
        css = Path("static/css/app.css").read_text(encoding="utf-8")

        self.assertIn(".worker-shift-detail-page", css)
        self.assertIn(".worker-detail-header", css)
        self.assertIn(".worker-detail-actions", css)
        self.assertIn(".worker-primary-action", css)
        self.assertIn(".worker-bottom-actions", css)
        self.assertIn("padding-bottom: max(1rem, env(safe-area-inset-bottom));", css)
