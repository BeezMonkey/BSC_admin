"""B04.2 detail presentation contracts; run only with an isolated test database."""

from datetime import date
from decimal import Decimal
from html.parser import HTMLParser
from types import SimpleNamespace

from django.template.loader import render_to_string
from django.templatetags.static import static
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from django.utils.html import escape

from accounts.models import UserProfile
from invoices import tests_invoices as fixtures
from invoices.models import Invoice, InvoiceBillingAdjustment, InvoiceLine


class DetailMarkup(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.elements, self.forms, self.rows = [], [], []
        self.form = self.row = self.cell = None
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.elements.append((tag, attrs))
        if tag == "form":
            self.form = (attrs, [])
            self.forms.append(self.form)
        elif self.form is not None:
            self.form[1].append((tag, attrs))
        if tag == "tr":
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.cell = []
            self.row.append(self.cell)

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag == "form":
            self.form = None
        elif tag in ("td", "th"):
            self.cell = None
        elif tag == "tr" and self.row is not None:
            self.rows.append([" ".join("".join(cell).split()) for cell in self.row])
            self.row = self.cell = None

    def find(self, tag, **attrs):
        return [values for name, values in self.elements if name == tag
                and all(values.get(key) == value for key, value in attrs.items())]


ORIGINAL = {
    "item_number": "ORIGINAL-ITEM", "item_name": "Original support item",
    "kilometres": "48.00", "actual_start_time": "09:00", "actual_end_time": "11:00",
    "break_minutes": 0, "hours": "2.00",
}
BILLING = {
    "item_number": "SNAP-SERVICE", "item_name": "Saved billing support item",
    "kilometres": "65.00", "actual_start_time": "09:15", "actual_end_time": "11:45",
    "break_minutes": 15, "hours": "2.25",
}
REASON = "Fictional correction <reviewed> & confirmed; retain the complete explanation."


@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    },
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class R1AdminInvoiceDetailTests(TestCase):
    create_user_with_role = fixtures.InvoiceGenerationTests.create_user_with_role
    create_service_log = fixtures.InvoiceGenerationTests.create_service_log

    def setUp(self):
        fixtures.InvoiceGenerationTests.setUp(self)
        self.super_admin = self.create_user_with_role("b042-super", UserProfile.Role.SUPER_ADMIN)
        self.coordinator_user = self.create_user_with_role("b042-coord", UserProfile.Role.SUPPORT_COORDINATOR)
        self.accountant_user.is_staff = True
        self.accountant_user.save(update_fields=["is_staff"])
        self.records, self.sc_records, self.logs, self.history = {}, {}, {}, {}
        for status in Invoice.Status.values:
            invoice = Invoice.objects.create(
                participant=self.participant, created_by=self.admin_user, status=status,
                period_start=date(2026, 6, 1), period_end=date(2026, 6, 30),
            )
            self.records[status] = invoice
            self.sc_records[status] = Invoice.objects.create(
                participant=self.participant, created_by=self.admin_user, status=status,
                invoice_type=Invoice.InvoiceType.SUPPORT_COORDINATION,
                period_start=date(2026, 6, 1), period_end=date(2026, 6, 30),
            )
            log = self.create_service_log(kilometres=Decimal("48.00"))
            self.logs[status] = log
            InvoiceLine.objects.create(
                invoice=invoice, service_log=log, line_type=InvoiceLine.LineType.SERVICE,
                support_item_number="SNAP-SERVICE", description="Saved billing support item",
                unit="hour", quantity=Decimal("2.25"), unit_price=Decimal("72.10"),
                line_total=Decimal("162.23"), gst_code="P2",
            )
            InvoiceLine.objects.create(
                invoice=invoice, service_log=log, line_type=InvoiceLine.LineType.TRAVEL_NON_LABOUR,
                support_item_number="SNAP-TRAVEL", description="Saved travel & non-labour claim",
                unit="each", quantity=Decimal("17.50"), unit_price=Decimal("1.20"),
                line_total=Decimal("21.00"), gst_code="P2",
            )
            self.history[status] = InvoiceBillingAdjustment.objects.create(
                service_log=log, invoice=invoice, invoice_number=invoice.invoice_number,
                original_values=ORIGINAL.copy(), billing_values=BILLING.copy(),
                reason=REASON, created_by=self.admin_user,
            )

    def detail(self, invoice, user=None, params=None):
        self.client.force_login(user or self.admin_user)
        response = self.client.get(reverse("invoice_detail", args=[invoice.pk]), params or {})
        self.assertEqual(response.status_code, 200)
        return response

    def test_admin_and_super_admin_opt_in_for_all_four_service_states(self):
        for user in (self.admin_user, self.super_admin):
            for status, invoice in self.records.items():
                with self.subTest(role=user.userprofile.role, status=status):
                    response = self.detail(invoice, user)
                    self.assertIs(response.context.get("r1_invoice_detail"), True)
                    self.assertTemplateUsed(response, "invoices/partials/r1_invoice_detail.html")
                    self.assertContains(response, "r1-admin-invoice-detail")
                    self.assertContains(response, "r1-ui r1-admin")
                    html = response.content.decode()
                    assets = ("app.css", "admin.css", "invoice_billing.css", "r1_tokens.css",
                              "r1_shell.css", "r1_admin_invoice_detail.css")
                    positions = []
                    for asset in assets:
                        path = static(f"css/{asset}")
                        self.assertContains(response, path, count=1)
                        positions.append(html.index(path))
                    self.assertEqual(positions, sorted(positions))
                    for marker in (invoice.invoice_number, invoice.get_status_display(),
                                   self.participant.display_name, "01/06/2026 - 30/06/2026", "$183.23"):
                        self.assertContains(response, marker)

    def test_accountant_service_stays_legacy_and_admin_sc_details_opt_in(self):
        for user, records in ((self.accountant_user, self.records),
                              (self.admin_user, self.sc_records), (self.super_admin, self.sc_records)):
            for status, invoice in records.items():
                with self.subTest(role=user.userprofile.role, invoice_type=invoice.invoice_type, status=status):
                    response = self.detail(invoice, user)
                    enhanced = records is self.sc_records
                    self.assertIs(response.context.get("r1_invoice_detail"), enhanced)
                    if enhanced:
                        self.assertTemplateUsed(response, "invoices/partials/r1_invoice_detail.html")
                    else:
                        self.assertTemplateNotUsed(response, "invoices/partials/r1_invoice_detail.html")
                    for marker in ("r1-admin-invoice-detail", "r1_admin_invoice_detail.css", "r1_shell.css"):
                        if enhanced:
                            self.assertContains(response, marker)
                        else:
                            self.assertNotContains(response, marker)
                    label = "Back to SC Invoices" if records is self.sc_records else "Back to Invoices"
                    self.assertContains(response, label)
                    self.assertContains(response, static("css/invoice_billing.css"), count=1)

    def test_existing_detail_role_denials_remain_unchanged(self):
        for user, records in ((self.accountant_user, self.sc_records),
                              (self.worker_user, self.records), (self.worker_user, self.sc_records),
                              (self.coordinator_user, self.records), (self.coordinator_user, self.sc_records)):
            self.client.force_login(user)
            for status, invoice in records.items():
                with self.subTest(role=user.userprofile.role, invoice_type=invoice.invoice_type, status=status):
                    response = self.client.get(reverse("invoice_detail", args=[invoice.pk]))
                    self.assertEqual(response.status_code, 403)

    def test_saved_line_fields_and_travel_quantity_are_not_recalculated_from_logs(self):
        expected_rows = (
            ["SNAP-SERVICE", "Saved billing support item", "hour", "2.25", "$72.10", "$162.23"],
            ["SNAP-TRAVEL", "Saved travel & non-labour claim", "each", "17.50", "$1.20", "$21.00"],
        )
        for status, invoice in self.records.items():
            with self.subTest(status=status):
                response = self.detail(invoice)
                rows = DetailMarkup(response.content.decode()).rows
                for expected in expected_rows:
                    matching = [row for row in rows if expected[0] in row]
                    self.assertEqual(len(matching), 1)
                    for value in expected:
                        self.assertIn(value, matching[0])
                self.assertContains(response, "$183.23")
                self.logs[status].refresh_from_db()
                self.assertEqual(self.logs[status].kilometres, Decimal("48.00"))
                self.assertEqual(self.logs[status].actual_hours, Decimal("2.00"))
                travel = invoice.lines.get(line_type=InvoiceLine.LineType.TRAVEL_NON_LABOUR)
                self.assertEqual(travel.quantity, Decimal("17.50"))
                self.assertEqual(travel.unit_price, Decimal("1.20"))
                self.assertEqual(travel.line_total, Decimal("21.00"))

    def test_original_status_action_matrix_remains_post_with_csrf(self):
        labels = {"invoice_mark_issued": "Mark as Issued", "invoice_mark_paid": "Mark as Paid",
                  "invoice_cancel": "Cancel Invoice", "invoice_delete": "Delete Draft Invoice"}
        matrix = {"draft": {"invoice_mark_issued", "invoice_cancel", "invoice_delete"},
                  "issued": {"invoice_mark_paid", "invoice_cancel"}, "paid": set(), "cancelled": set()}
        for user in (self.admin_user, self.super_admin):
            for status, invoice in self.records.items():
                with self.subTest(role=user.userprofile.role, status=status):
                    response = self.detail(invoice, user)
                    markup = DetailMarkup(response.content.decode())
                    urls = {name: reverse(name, args=[invoice.pk]) for name in labels}
                    actions = [(attrs, children) for attrs, children in markup.forms
                               if attrs.get("action") != reverse("logout")]
                    self.assertCountEqual([attrs.get("action") for attrs, _ in actions],
                                          [urls[name] for name in matrix[status]])
                    for attrs, children in actions:
                        self.assertEqual(attrs.get("method"), "post")
                        self.assertTrue(any(tag == "input" and values.get("name") == "csrfmiddlewaretoken"
                                            and values.get("value") for tag, values in children))
                        self.assertTrue(any(tag == "button" and values.get("type") == "submit"
                                            for tag, values in children))
                    for name, label in labels.items():
                        if name in matrix[status]:
                            self.assertContains(response, label)
                        else:
                            self.assertNotContains(response, label)
                        self.assertFalse(markup.find("a", href=urls[name]))

    def test_safe_next_and_existing_csv_pdf_links_are_preserved(self):
        next_url = reverse("invoice_placeholder") + "?participant=Ava&status=issued&sort=total&direction=desc&page=2"
        for status, invoice in self.records.items():
            with self.subTest(status=status):
                response = self.detail(invoice, params={"next": next_url})
                self.assertEqual(response.context["return_url"], next_url)
                markup = DetailMarkup(response.content.decode())
                self.assertTrue(markup.find("a", href=next_url))
                self.assertContains(response, "Back to Invoices")
                for name, label in (("invoice_csv", "Download CSV"), ("invoice_pdf", "Download PDF")):
                    self.assertEqual(len(markup.find("a", href=reverse(name, args=[invoice.pk]))), 1)
                    self.assertContains(response, label)

    def test_unsafe_next_falls_back_to_the_original_invoice_list(self):
        invoice = self.records[Invoice.Status.DRAFT]
        for target in ("https://untrusted.example/invoices/", "//untrusted.example/invoices/", "javascript:alert(1)"):
            with self.subTest(next=target):
                response = self.detail(invoice, params={"next": target})
                self.assertEqual(response.context["return_url"], reverse("invoice_placeholder"))
                self.assertTrue(DetailMarkup(response.content.decode()).find("a", href=reverse("invoice_placeholder")))
                self.assertNotContains(response, f'href="{target}"')

    def test_complete_shared_history_original_billing_values_and_reason_are_preserved(self):
        for status, invoice in self.records.items():
            with self.subTest(status=status):
                response = self.detail(invoice)
                self.assertTemplateUsed(response, "invoices/billing_adjustment_history.html")
                adjustment = self.history[status]
                stamp = timezone.localtime(adjustment.created_at).strftime("%d/%m/%Y %H:%M")
                for text in ("Billing adjustments (1)", f"Log #{self.logs[status].pk}", invoice.invoice_number,
                             "admin", stamp, ORIGINAL["item_number"], ORIGINAL["item_name"],
                             BILLING["item_number"], BILLING["item_name"], "48.00", "65.00", "km",
                             "09:00 - 11:00", "09:15 - 11:45", "0 min break; 2.00 h",
                             "15 min break; 2.25 h", str(escape(REASON))):
                    self.assertContains(response, text)
                markup = DetailMarkup(response.content.decode())
                self.assertTrue(any("invoice-billing-history" in attrs.get("class", "").split()
                                    for attrs in markup.find("details")))

    def test_invoice_lines_region_is_named_and_keyboard_focusable(self):
        for status, invoice in self.records.items():
            with self.subTest(status=status):
                markup = DetailMarkup(self.detail(invoice).content.decode())
                regions = [attrs for _, attrs in markup.elements
                           if attrs.get("role") == "region" and attrs.get("aria-label") == "Invoice lines"]
                self.assertEqual(len(regions), 1)
                self.assertEqual(regions[0].get("tabindex"), "0")

    def test_parent_invoice_list_and_service_log_pages_keep_their_existing_r1_scope(self):
        self.client.force_login(self.admin_user)
        targets = (
            (reverse("invoice_placeholder"), "r1-admin-invoice-list", "r1_admin_invoice_list.css"),
            (reverse("service_log_list"), "r1-admin-log-list", "r1_admin_logs_list.css"),
            (reverse("service_log_detail", args=[self.logs[Invoice.Status.DRAFT].pk]),
             "r1-admin-log-detail", "r1_admin_log_detail.css"),
        )
        for url, marker, asset in targets:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, marker)
                self.assertContains(response, static(f"css/{asset}"), count=1)
                self.assertNotContains(response, "r1-admin-invoice-detail")
                self.assertNotContains(response, "r1_admin_invoice_detail.css")
                self.assertTemplateNotUsed(response, "invoices/partials/r1_invoice_detail.html")


class R1InvoiceDetailHistorySnapshotTests(SimpleTestCase):
    def test_deleted_invoice_snapshot_keeps_all_shared_history_content(self):
        adjustment = SimpleNamespace(
            service_log_id=42, invoice_id=None, invoice_number="DELETED-SNAPSHOT-0042",
            original_values=ORIGINAL.copy(), billing_values=BILLING.copy(), reason=REASON,
            created_by="Fictional snapshot admin", created_at=timezone.now(),
        )
        html = render_to_string("invoices/billing_adjustment_history.html", {"billing_adjustments": [adjustment]})
        stamp = timezone.localtime(adjustment.created_at).strftime("%d/%m/%Y %H:%M")
        for text in ("Billing adjustments (1)", "Log #42", "DELETED-SNAPSHOT-0042", "(invoice deleted)",
                     "Fictional snapshot admin", stamp, ORIGINAL["item_number"], ORIGINAL["item_name"],
                     BILLING["item_number"], BILLING["item_name"], "48.00", "65.00", "km",
                     "09:00 - 11:00", "09:15 - 11:45", "0 min break; 2.00 h",
                     "15 min break; 2.25 h", str(escape(REASON))):
            self.assertIn(text, html)
        self.assertIn('class="invoice-billing-history"', html)
