"""UI-only list contracts; fixtures never access a database or send mail."""
import ast
from datetime import date, datetime, time
from decimal import Decimal
from html.parser import HTMLParser
from pathlib import Path
import shutil
import subprocess
from types import SimpleNamespace
from unittest import skipUnless

from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.test import RequestFactory, SimpleTestCase
from django.urls import reverse
from django.utils.html import escape
from django.utils.text import Truncator


class ListMarkup(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.elements = []
        self.parents = []
        self.stack = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))
        self.parents.append(tuple(self.stack))
        if tag not in {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}:
            self.stack.append((tag, dict(attrs)))

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break

    def find(self, tag, **attrs):
        return [a for t, a in self.elements if t == tag and all(a.get(k) == v for k, v in attrs.items())]


class R1AdminLogListTests(SimpleTestCase):
    def context(self, **overrides):
        participant = SimpleNamespace(id=11, display_name="Fictional Participant")
        worker = SimpleNamespace(id=21, display_name="Fictional Worker")
        request = RequestFactory().get("/service-logs/?status=approved&participant=11")
        request.user = SimpleNamespace(get_username=lambda: "fictional_admin")
        request.resolver_match = SimpleNamespace(url_name="service_log_list")
        rows = []
        for pk, status in enumerate(("submitted", "approved", "invoiced", "rejected"), 1):
            rows.append(dict(
                kind="service_log", id=pk, status=status, status_label=status.title(),
                service_date=date(2026, 10, 9), participant=participant, worker=worker,
                hours=Decimal("4.00"), notes="Full case note " + "x" * 100,
                service_log=dict(source="unscheduled" if pk == 1 else "shift",
                                 submitted_at=datetime(2026, 10, 10, 9, 30)),
            ))
        rows.append(dict(kind="cancellation", id=51, status="approved", status_label="Cancellation",
                         service_date=date(2026, 10, 8), participant=participant, worker=worker,
                         hours=Decimal("2.00"), notes="Cancellation explanation " + "y" * 100))
        shift = dict(id=61, service_date=date(2026, 10, 7), start_time=time(9),
                     end_time=time(13), participant=participant)
        context = dict(
            request=request, csrf_token="fictional-list-csrf-token", status="approved", status_label="Approved", participants=[participant],
            workers=[worker], selected_participant_id="11", selected_worker_id="21",
            date_range="custom", date_range_choices=[("custom", "Custom range")],
            date_from="2026-10-01", date_to="2026-10-16", clear_filter_url="/service-logs/?status=approved",
            current_list_url=request.get_full_path(), filtered_record_count=5, filtered_hours="18.00",
            sorting=dict(links={key: f"status=approved&participant=11&sort={key}"
                                for key in ("date", "participant", "worker", "status")}),
            status_overview=[dict(label=label, count_label=count, count=number, count_unit=unit, description=description,
                                  active=label == "Approved", url=f"?status={status}")
                             for label, count, number, unit, description, status in (
                                 ("All logs", "10 records", 10, "records", "All submitted worker records", ""),
                                 ("Submitted", "3 waiting", 3, "waiting", "Waiting for admin review", "submitted"),
                                 ("Approved", "3 ready", 3, "ready", "Ready to invoice", "approved"),
                                 ("Invoiced", "2 billed", 2, "billed", "Already converted to invoices", "invoiced"),
                                 ("Rejected", "2 returned", 2, "returned", "Needs worker correction", "rejected"))],
            billing_rows=rows, has_filters=True, missing_log_count=1, missing_worker_count=1,
            missing_log_groups=[dict(worker=worker, count=1, shifts=[shift])],
        )
        page = Paginator(range(30), 10).page(2)
        context["pagination"] = dict(record_count=30, record_start=11, record_end=20,
                                     page_obj=page, page_query="status=approved&participant=11")
        context.update(overrides)
        return context

    def render(self, **overrides):
        return render_to_string("service_logs/service_log_list.html", self.context(**overrides))

    def test_list_opts_into_only_its_r1_assets_and_shell(self):
        html = self.render()
        self.assertIn('class="app-shell r1-ui r1-admin r1-admin-logs r1-admin-log-list"', html)
        assets = ["r1_tokens.css", "r1_shell.css", "r1_admin_logs.css", "r1_admin_logs_list.css"]
        positions = [html.index(static(f"css/{asset}")) for asset in assets]
        self.assertEqual(positions, sorted(positions))
        self.assertNotIn("invoice_billing.css", html)
        self.assertIn('class="r1-account"', html)
        self.assertIn('aria-label="Breadcrumb">Operations / Service Logs', html)

    def test_scroll_regions_and_active_status_are_keyboard_accessible(self):
        markup = ListMarkup(self.render())
        self.assertTrue(markup.find("div", role="region", tabindex="0", **{"aria-label": "Service logs table"}))
        self.assertTrue(markup.find("div", role="region", tabindex="0", **{"aria-label": "Service log statuses"}))
        active = markup.find("a", **{"aria-current": "page"})
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]["href"], "?status=approved")

    def test_eight_columns_billing_selection_and_secure_next_are_preserved(self):
        html = self.render()
        markup = ListMarkup(html)
        self.assertEqual(len(markup.find("th")), 8)
        self.assertEqual([a["value"] for a in markup.find("input", name="service_log_ids")], ["2"])
        self.assertEqual([a["value"] for a in markup.find("input", name="participant_cancellation_ids")], ["51"])
        self.assertTrue(markup.find("form", method="get", action=reverse("invoice_create")))
        self.assertIn(reverse("participant_cancellation_detail", args=[51]), html)
        self.assertIn('?next=/service-logs/%3Fstatus%3Dapproved%26participant%3D11', html)
        self.assertIn("participant=11&period_start=2026-10-09&period_end=2026-10-09", html)
        self.assertIn("Submitted 10/10/2026 09:30", html)
        self.assertIn("Support worker", html)
        self.assertIn("Unscheduled", html)
        self.assertIn(escape(Truncator("Full case note " + "x" * 100).chars(80)), html)
        self.assertIn("Cancellation explanation " + "y" * 100, html)

    def test_filter_values_sorting_summary_and_pagination_are_preserved(self):
        html = self.render()
        markup = ListMarkup(html)
        for name, value in (("status", "approved"), ("date_from", "2026-10-01"), ("date_to", "2026-10-16")):
            self.assertTrue(markup.find("input", name=name, value=value))
        for name in ("participant", "worker", "date_range"):
            self.assertTrue(markup.find("select", name=name))
        for value in ("11", "21", "custom"):
            self.assertTrue(any("selected" in option for option in markup.find("option", value=value)))
        for key in ("date", "participant", "worker", "status"):
            self.assertIn(f'?status=approved&amp;participant=11&amp;sort={key}', html)
        self.assertIn("5 approved records", html)
        self.assertIn("18.00 hours", html)
        self.assertIn("Showing 11-20 of 30 records", html)
        self.assertIn("status=approved&amp;participant=11&amp;page=3", html)

    def test_native_billing_checkboxes_keep_labels_and_expand_hit_targets(self):
        markup = ListMarkup(self.render())
        boxes = [(index, attrs) for index, (tag, attrs) in enumerate(markup.elements)
                 if tag == "input" and attrs.get("type") == "checkbox"]
        self.assertEqual([(attrs["name"], attrs["value"]) for _, attrs in boxes],
                         [("service_log_ids", "2"), ("participant_cancellation_ids", "51")])
        for index, attrs in boxes:
            self.assertEqual(markup.parents[index][-1],
                             ("label", {"class": "service-log-selection-target"}))
            self.assertIn("Fictional Participant, 09/10/2026" if attrs["value"] == "2"
                          else "Fictional Participant, 08/10/2026", attrs["aria-label"])
            self.assertNotIn("onclick", attrs)

    def test_scoped_filter_band_has_explicit_eight_pixel_outer_radius(self):
        stylesheet = (Path(__file__).resolve().parent.parent / "static/css/r1_admin_logs_list.css").read_text(encoding="utf-8")
        selector = ".r1-admin-log-list .service-log-filter-bar[data-service-log-filters] {"
        rule = stylesheet.split(selector, 1)[1].split("}", 1)[0]
        self.assertIn("border-radius: 8px;", rule)

    def test_all_existing_status_and_workbench_copy_remains_visible(self):
        html = self.render()
        for text in ("Service log workbench", "Review submitted support records, approve worker notes, and prepare billable logs.",
                     "Start with submitted logs, then move approved records into invoices.", "Billing action",
                     "Select approved rows to create an invoice.", "Create Invoice from Selected"):
            self.assertIn(text, html)
        for item in self.context()["status_overview"]:
            for key in ("label", "count_label", "description"):
                self.assertIn(item[key], html)

    def test_status_count_and_meaning_have_separate_presentational_elements(self):
        html = self.render()
        for item in self.context()["status_overview"]:
            self.assertInHTML(f'<strong class="service-log-status-number">{item["count"]}</strong>', html)
            self.assertInHTML(f'<span class="service-log-status-unit">{item["count_unit"]}</span>', html)
            self.assertIn(f'aria-label="{item["label"]}: {item["count_label"]}. {item["description"]}"', html)

    def test_status_metadata_uses_existing_counts_without_changing_labels(self):
        # Evaluate only the presentation assignment, never the view or its queries.
        from service_logs.models import ServiceLog
        tree = ast.parse(Path(__file__).with_name("views.py").read_text(encoding="utf-8"))
        assignment = next(node for node in ast.walk(tree) if isinstance(node, ast.Assign)
                          and any(isinstance(target, ast.Name) and target.id == "status_overview"
                                  for target in node.targets))
        expression = compile(ast.Expression(assignment.value), "status_overview", "eval")
        for total in (0, 1, 17):
            with self.subTest(total=total):
                items = eval(expression, {"ServiceLog": ServiceLog, "total_count": total,
                             "status_counts": {ServiceLog.Status.SUBMITTED: 5, ServiceLog.Status.INVOICED: 3},
                             "approved_ready_count": 7, "status": "", "status_url": lambda *args: "?status="})
                expected = [(total, "record" if total == 1 else "records"), (5, "waiting"),
                            (7, "ready"), (3, "billed"), (0, "returned")]
                self.assertEqual([(item.get("count"), item.get("count_unit")) for item in items], expected)
                self.assertEqual([item["count_label"] for item in items],
                                 [f"{number} {unit}" for number, unit in expected])

    def test_missing_panel_has_header_non_submitting_close_and_external_explanation(self):
        html = self.render()
        markup = ListMarkup(html)
        self.assertTrue(markup.find("h2", id="service-log-missing-title"))
        self.assertTrue(markup.find("button", type="button", **{"data-missing-close": None}))
        self.assertInHTML('<span class="service-log-missing-label">Missing logs</span>', html)
        self.assertInHTML('<span class="service-log-missing-counts">1 log · 1 worker</span>', html)
        explanation = "Scheduled shifts that have ended, with no service log submitted."
        self.assertLess(html.index(explanation), html.index('<details class="service-log-missing"'))
        self.assertIn(static("js/r1_admin_log_list.js"), html)
        self.assertTrue(markup.find("div", **{"class": "service-log-missing-panel",
                        "aria-labelledby": "service-log-missing-title"}))

    def test_missing_panel_preserves_multiple_worker_groups_and_shift_destinations(self):
        groups = self.context()["missing_log_groups"]
        second_shift = dict(groups[0]["shifts"][0], id=62, service_date=date(2026, 10, 8))
        groups.append(dict(worker=SimpleNamespace(display_name="Another Worker"), count=1, shifts=[second_shift]))
        html = self.render(missing_log_groups=groups, missing_worker_count=2, missing_log_count=2)
        self.assertEqual(len(ListMarkup(html).find("details", **{"class": "service-log-missing-worker"})), 2)
        for pk in (61, 62):
            self.assertIn(reverse("shift_detail", args=[pk]), html)
        self.assertIn("2 workers with 2 unsubmitted logs", html)
        self.assertIn("Earliest 08/10/2026", html)
        self.assertInHTML('<strong class="service-log-missing-participant">Fictional Participant</strong>', html)

    def test_missing_explanation_and_native_trigger_share_closed_state_bar(self):
        markup = ListMarkup(self.render())
        self.assertTrue(markup.find("div", **{"class": "service-log-missing-bar"}))
        for tag, class_name in (("p", "service-log-missing-explanation"), ("details", "service-log-missing")):
            index = next(index for index, (element_tag, attrs) in enumerate(markup.elements)
                         if element_tag == tag and attrs.get("class") == class_name)
            self.assertEqual(markup.parents[index][-1], ("div", {"class": "service-log-missing-bar"}))

    def test_compact_missing_trigger_uses_existing_decorative_chevron_only_once(self):
        markup = ListMarkup(self.render())
        chevrons = markup.find("img", **{"class": "service-log-missing-chevron"})
        self.assertEqual(len(chevrons), 1)
        self.assertEqual(chevrons[0]["src"], static("img/r1/icons/chevron.svg"))
        self.assertEqual(chevrons[0]["alt"], "")
        self.assertEqual((chevrons[0]["width"], chevrons[0]["height"]), ("20", "20"))
        index = next(index for index, (_, attrs) in enumerate(markup.elements)
                     if attrs.get("class") == "service-log-missing-chevron")
        self.assertEqual(markup.parents[index][-1][0], "summary")
        self.assertEqual(markup.parents[index][-2], ("details", {"class": "service-log-missing"}))

    def test_missing_logs_keep_native_nested_disclosures_and_all_shift_facts(self):
        html = self.render()
        markup = ListMarkup(html)
        self.assertTrue(markup.find("details", **{"class": "service-log-missing"}))
        self.assertTrue(markup.find("details", **{"class": "service-log-missing-worker"}))
        self.assertEqual(len(markup.find("summary")), 2)
        self.assertIn("1 worker with 1 unsubmitted log", html)
        self.assertIn("Scheduled shifts that have ended, with no service log submitted.", html)
        self.assertIn("Earliest 07/10/2026", html)
        self.assertIn("9:00 am &ndash; 1:00 pm", html)
        self.assertIn(reverse("shift_detail", args=[61]), html)
        self.assertIn(">Close<", html)
        self.assertIn("No unsubmitted logs in the current filters.", self.render(missing_log_count=0))

    def test_empty_states_preserve_full_explanations_and_routes(self):
        scenarios = (
            ({"status": "approved", "has_filters": True}, "No approved billing records match the current filters.",
             "Clear the filters to review approved service logs and rostered charges.", "service_log_list"),
            ({"status": "submitted", "has_filters": True}, "No service logs match the current filters.",
             "Clear the filters to review all submitted worker service records.", "service_log_list"),
            ({"status": "", "has_filters": False}, "No service logs yet.",
             "Service logs appear here after workers complete rostered shifts.", "roster_list"),
        )
        for overrides, title, help_text, route in scenarios:
            with self.subTest(title=title):
                html = self.render(billing_rows=[], **overrides)
                self.assertIn(title, html)
                self.assertIn(help_text, html)
                self.assertIn(reverse(route), html)
                self.assertIn('colspan="8"', html)


@skipUnless(shutil.which("node"), "Node is required for the isolated list interaction test")
class R1AdminLogListInteractionTests(SimpleTestCase):
    def test_expanding_worker_reclamps_panel_inside_short_viewport(self):
        script = Path(__file__).resolve().parent.parent / "static/js/r1_admin_log_list.js"
        result = subprocess.run([shutil.which("node"), "-e", r"""
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const events = [];
let panelHeight = 100;
const anchor = {left: 700, right: 900, top: 550, bottom: 594};
const trigger = {
  getBoundingClientRect: () => anchor,
  setAttribute() {}, focus() {},
};
const button = {addEventListener() {}};
const panel = {
  style: {}, setAttribute() {}, removeAttribute() {},
  querySelector: () => button, contains: () => false,
  getBoundingClientRect: () => ({width: 560, height: panelHeight}),
};
const disclosure = {
  open: true, contains: () => true,
  querySelector: (selector) => selector === ':scope > summary' ? trigger : panel,
  addEventListener: (type, callback, capture) => events.push({type, callback, capture}),
};
const document = {
  querySelector: () => ({querySelector: () => disclosure}),
  addEventListener() {},
};
const window = {
  innerWidth: 1024, innerHeight: 800,
  matchMedia: () => ({matches: false}), addEventListener() {},
};
vm.runInNewContext(fs.readFileSync(process.argv[1], 'utf8'), {document, window});
assert.equal(parseFloat(panel.style.top), 602);
assert.equal(parseFloat(panel.style.left), 340, 'Panel right edge must align with trigger right edge');
panelHeight = 464;
// Native toggle does not bubble: only capture listeners see a worker's toggle.
for (const event of events) {
  if (event.type === 'toggle' && event.capture) event.callback({target: {}});
}
assert.ok(parseFloat(panel.style.top) + panelHeight <= 788,
          'Expanded worker panel must remain inside the visible viewport');
assert.ok(parseFloat(panel.style.top) >= 12);
""", str(script)], capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
