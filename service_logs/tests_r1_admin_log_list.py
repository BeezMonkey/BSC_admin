"""UI-only list contracts; fixtures never access a database or send mail."""
from datetime import date, datetime, time
from decimal import Decimal
from html.parser import HTMLParser
from types import SimpleNamespace

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
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))

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
            status_overview=[dict(label=label, count_label=count, description=description,
                                  active=label == "Approved", url=f"?status={status}")
                             for label, count, description, status in (
                                 ("All logs", "10 records", "All submitted worker records", ""),
                                 ("Submitted", "3 waiting", "Waiting for admin review", "submitted"),
                                 ("Approved", "3 ready", "Ready to invoice", "approved"),
                                 ("Invoiced", "2 billed", "Already converted to invoices", "invoiced"),
                                 ("Rejected", "2 returned", "Needs worker correction", "rejected"))],
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

    def test_all_existing_status_and_workbench_copy_remains_visible(self):
        html = self.render()
        for text in ("Service log workbench", "Review submitted support records, approve worker notes, and prepare billable logs.",
                     "Start with submitted logs, then move approved records into invoices.", "Billing action",
                     "Select approved rows to create an invoice.", "Create Invoice from Selected"):
            self.assertIn(text, html)
        for item in self.context()["status_overview"]:
            for key in ("label", "count_label", "description"):
                self.assertIn(item[key], html)

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
        self.assertNotIn(">Close<", html)
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
