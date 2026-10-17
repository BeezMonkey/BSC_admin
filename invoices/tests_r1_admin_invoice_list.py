"""B04.1 presentation activation and existing invoice-list contracts."""

from datetime import date, time
from decimal import Decimal
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlsplit

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.templatetags.static import static
from django.urls import reverse

from accounts.models import UserProfile
from invoices.models import Invoice, InvoiceLine
from participants.models import Participant
from scheduling.models import Shift, SupportItem
from service_logs.models import ServiceLog
from workers.models import SupportWorker


class InvoiceListMarkup(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.elements = []
        self.forms = []
        self.links = []
        self.current_form = None
        self.current_link = None
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.elements.append((tag, attrs))
        if tag == "form":
            self.current_form = (attrs, [])
            self.forms.append(self.current_form)
        elif self.current_form is not None:
            self.current_form[1].append((tag, attrs))
        if tag == "a":
            self.current_link = (attrs, [])
            self.links.append(self.current_link)

    def handle_endtag(self, tag):
        if tag == "form":
            self.current_form = None
        elif tag == "a":
            self.current_link = None

    def handle_data(self, data):
        if self.current_link is not None:
            self.current_link[1].append(data)

    def find(self, tag, **attrs):
        return [attributes for name, attributes in self.elements
                if name == tag and all(attributes.get(key) == value
                                       for key, value in attrs.items())]


@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    },
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class R1AdminInvoiceListTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        for name, role in (
            ("admin", UserProfile.Role.ADMIN),
            ("super_admin", UserProfile.Role.SUPER_ADMIN),
            ("accountant", UserProfile.Role.ACCOUNTANT),
            ("worker_user", UserProfile.Role.SUPPORT_WORKER),
            ("coordinator", UserProfile.Role.SUPPORT_COORDINATOR),
        ):
            user = get_user_model().objects.create_user(
                username=f"b041-{name}", is_staff=name == "accountant",
            )
            UserProfile.objects.create(
                user=user, role=role,
                is_active_worker=role == UserProfile.Role.SUPPORT_WORKER,
            )
            setattr(cls, name, user)
        cls.participant = Participant.objects.create(
            first_name="Alexandria" * 6, last_name="Longparticipantname" * 4,
            status=Participant.Status.ACTIVE,
        )
        cls.records = {}
        for status in Invoice.Status.values:
            cls.records[status] = Invoice.objects.create(
                participant=cls.participant, created_by=cls.admin, status=status,
                period_start=date(2026, 10, 1), period_end=date(2026, 10, 31),
            )
        cls.sc_invoice = Invoice.objects.create(
            participant=cls.participant, created_by=cls.admin,
            invoice_type=Invoice.InvoiceType.SUPPORT_COORDINATION,
            period_start=date(2026, 10, 1), period_end=date(2026, 10, 31),
        )
        worker = SupportWorker.objects.create(
            user=cls.worker_user, first_name="B041", last_name="Fictional Worker",
            email="b041-worker@example.invalid", status=SupportWorker.Status.ACTIVE,
        )
        item = SupportItem.objects.create(
            item_number="B041-TEST", name="Fictional invoice-list support item",
            unit=SupportItem.Unit.HOUR, price_limit=Decimal("65.47"), is_active=True,
        )
        shift = Shift.objects.create(
            participant=cls.participant, worker=worker, created_by=cls.admin,
            service_date=date(2026, 10, 1), start_time=time(9), end_time=time(11),
            planned_hours=Decimal("2.00"), support_item=item,
            service_type=Shift.ServiceType.PERSONAL_CARE, status=Shift.Status.COMPLETED,
        )
        log = ServiceLog.objects.create_from_shift(
            shift, actual_start_time=time(9), actual_end_time=time(11),
            actual_hours=Decimal("2.00"), kilometres=Decimal("0.00"),
            case_notes="Fictional B04.1 list fixture", worker_notes="",
        )
        InvoiceLine.objects.create_from_service_log(cls.records[Invoice.Status.DRAFT], log)

    def get_list(self, user=None, params=None, route="invoice_placeholder"):
        self.client.force_login(user or self.admin)
        response = self.client.get(reverse(route), params or {})
        self.assertEqual(response.status_code, 200)
        return response

    def markup(self, response):
        return InvoiceListMarkup(response.content.decode())

    def test_admin_and_super_admin_activate_only_invoice_list_assets(self):
        for user in (self.admin, self.super_admin):
            with self.subTest(role=user.userprofile.role):
                response = self.get_list(user)
                self.assertIs(response.context.get("r1_invoice_list"), True)
                shell = [attrs for attrs in self.markup(response).find("div")
                         if "data-admin-theme" in attrs]
                self.assertTrue(any(
                    {"app-shell", "r1-ui", "r1-admin", "r1-admin-invoice-list"}
                    <= set(element.get("class", "").split()) for element in shell
                ))
                assets = ("app.css", "admin.css", "r1_tokens.css", "r1_shell.css",
                          "r1_admin_invoice_list.css")
                html = response.content.decode()
                positions = []
                for asset in assets:
                    path = static(f"css/{asset}")
                    self.assertContains(response, path, count=1)
                    positions.append(html.index(path))
                self.assertEqual(positions, sorted(positions))
                self.assertNotContains(response, "r1_admin_logs")
                self.assertNotContains(response, "r1_worker_navigation")

    def test_accountant_and_sc_lists_keep_presentation_off(self):
        for user, route in (
            (self.accountant, "invoice_placeholder"),
            (self.admin, "support_coordination_invoice_list"),
            (self.super_admin, "support_coordination_invoice_list"),
        ):
            with self.subTest(role=user.userprofile.role, route=route):
                response = self.get_list(user, route=route)
                self.assertIs(response.context.get("r1_invoice_list"), False)
                for marker in ("r1-ui", "r1-admin-invoice-list", "r1_tokens.css",
                               "r1_shell.css", "r1_admin_invoice_list.css"):
                    self.assertNotContains(response, marker)
                self.assertContains(response, static("css/admin.css"), count=1)
                if route == "support_coordination_invoice_list":
                    self.assertContains(response, "SC Invoices")
                    self.assertContains(response, "Manage support coordination invoices.")
                    self.assertContains(response, "Create SC Invoice")
                    self.assertContains(response, "All SC invoices")
                    self.assertContains(response, self.sc_invoice.invoice_number)
                    self.assertNotContains(response, self.records[Invoice.Status.DRAFT].invoice_number)
                else:
                    self.assertContains(response, "Invoice Settings")
                    self.assertNotContains(response, self.sc_invoice.invoice_number)

    def test_other_invoice_pages_do_not_activate_list_presentation(self):
        self.client.force_login(self.admin)
        urls = [reverse(name) for name in
                ("invoice_create", "invoice_settings", "exports_placeholder")]
        urls.append(reverse("invoice_detail", args=[self.records[Invoice.Status.DRAFT].pk]))
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertNotContains(response, "r1-admin-invoice-list")
                self.assertNotContains(response, "r1_admin_invoice_list.css")
                if url == reverse("invoice_detail", args=[self.records[Invoice.Status.DRAFT].pk]):
                    self.assertContains(response, "r1_admin_invoice_detail.css")
                elif url != reverse("invoice_create"):
                    self.assertNotContains(response, "r1_shell.css")

    def test_existing_role_boundaries_are_unchanged(self):
        for user, routes in (
            (self.accountant, ("support_coordination_invoice_list",)),
            (self.worker_user, ("invoice_placeholder", "support_coordination_invoice_list")),
            (self.coordinator, ("invoice_placeholder", "support_coordination_invoice_list")),
        ):
            self.client.force_login(user)
            for route in routes:
                with self.subTest(role=user.userprofile.role, route=route):
                    self.assertEqual(self.client.get(reverse(route)).status_code, 403)

    def test_complete_workbench_copy_counts_and_status_links_are_preserved(self):
        response = self.get_list(params={"status": "issued", "participant": "Missing"})
        for text in (
            "Invoices", "Manage service invoices.", "Invoice Settings", "Create Invoice",
            "Billing workbench",
            "Move draft invoices into issue, then close the loop when payment is received.",
            "All invoices", "4 records", "Full billing history",
            "Draft", "1 draft", "Ready to review before issuing",
            "Issued", "1 awaiting payment", "Sent invoices not marked paid",
            "Paid", "1 paid", "Completed billing records",
            "Cancelled", "1 cancelled", "Removed from active billing",
            "Billing filters", "Search invoice number, participant, status, or period.",
        ):
            self.assertContains(response, text)
        cards = [attrs for attrs in self.markup(response).find("a")
                 if "invoice-status-card" in attrs.get("class", "").split()]
        base = reverse("invoice_placeholder")
        self.assertEqual([card["href"] for card in cards],
                         [base] + [f"{base}?status={status}" for status in Invoice.Status.values])
        self.assertEqual([card["href"] for card in cards
                          if "active" in card.get("class", "").split()], [f"{base}?status=issued"])

    def test_rows_retain_labels_all_statuses_amounts_long_names_and_actions(self):
        response = self.get_list()
        markup = self.markup(response)
        self.assertEqual(len(markup.find("th")), 6)
        for text in ("Invoice", "Participant", "Period", "Status", "Total", "Actions",
                     "Created by b041-admin", "Service", "Billing period", "Invoice total",
                     "01/10/2026 - 31/10/2026", self.participant.display_name):
            self.assertContains(response, text)
        self.assertContains(response, "$130.94", count=1)
        self.assertContains(response, "$0.00", count=3)
        self.assertEqual(sum("".join(text).strip() == "View" for _, text in markup.links), 4)
        self.assertNotContains(response, self.sc_invoice.invoice_number)
        self.assertTrue(markup.find("th", **{"class": "numeric-cell"}))
        for status, invoice in self.records.items():
            self.assertContains(response, invoice.invoice_number)
            self.assertContains(response, f"status-{status}")
            self.assertContains(response, invoice.get_status_display())
            links = [a for a in markup.find("a")
                     if urlsplit(a.get("href", "")).path == reverse("invoice_detail", args=[invoice.pk])]
            self.assertEqual(len(links), 2)
        delete_forms = [(attrs, children) for attrs, children in markup.forms
                        if attrs.get("action") == reverse(
                            "invoice_delete", args=[self.records[Invoice.Status.DRAFT].pk])]
        self.assertEqual(len(delete_forms), 1)
        attrs, children = delete_forms[0]
        self.assertEqual(attrs.get("method"), "post")
        self.assertIn("inline-form", attrs.get("class", "").split())
        self.assertTrue(any(tag == "input" and a.get("name") == "csrfmiddlewaretoken"
                            for tag, a in children))
        self.assertContains(response, "Delete", count=1)
        for status in (Invoice.Status.ISSUED, Invoice.Status.PAID, Invoice.Status.CANCELLED):
            self.assertFalse(markup.find("form", action=reverse(
                "invoice_delete", args=[self.records[status].pk])))

    def test_get_filters_overlap_summary_sort_links_and_next_preserve_contract(self):
        params = {"q": "BSC-", "participant": "Alexandria", "status": "draft",
                  "period_from": "2026-10-15", "period_to": "2026-10-15",
                  "sort": "total", "direction": "desc", "page": "2"}
        response = self.get_list(params=params)
        self.assertEqual(list(response.context["invoices"]), [self.records[Invoice.Status.DRAFT]])
        markup = self.markup(response)
        filters = [(attrs, children) for attrs, children in markup.forms
                   if attrs.get("method") == "get"]
        self.assertEqual(len(filters), 1)
        for name, kind in (("q", "search"), ("participant", "search"),
                           ("period_from", "date"), ("period_to", "date")):
            self.assertTrue(any(tag == "input" and attrs.get("name") == name
                                and attrs.get("type") == kind and attrs.get("value") == params[name]
                                for tag, attrs in filters[0][1]))
        self.assertTrue(markup.find("select", name="status"))
        self.assertTrue(any("selected" in option for option in markup.find("option", value="draft")))
        for value, label in Invoice.Status.choices:
            self.assertTrue(markup.find("option", value=value))
            self.assertContains(response, label)
        for text in ("All statuses", "From", "To", "Search", "Reset", "Clear filter",
                     "Showing draft invoices matching &quot;BSC-&quot; for Alexandria from 15/10/2026 to 15/10/2026."):
            self.assertContains(response, text)
        for label in ("Reset", "Clear filter"):
            self.assertTrue(any(
                "".join(text).strip() == label and attrs.get("href") == reverse("invoice_placeholder")
                for attrs, text in markup.links
            ))
        sorts = [a for a in markup.find("a") if "sort-link" in a.get("class", "").split()]
        self.assertEqual(len(sorts), 5)
        expected_filters = {key: [value] for key, value in params.items()
                            if key not in {"sort", "direction", "page"}}
        self.assertEqual({parse_qs(urlsplit(a["href"]).query)["sort"][0] for a in sorts},
                         {"invoice", "participant", "period", "status", "total"})
        for link in sorts:
            query = parse_qs(urlsplit(link["href"]).query)
            self.assertEqual(query, {**expected_filters, "sort": query["sort"], "direction": ["asc"]})
        detail_links = [a for a in markup.find("a") if urlsplit(a.get("href", "")).path
                        == reverse("invoice_detail", args=[self.records[Invoice.Status.DRAFT].pk])]
        self.assertEqual(len(detail_links), 2)
        for link in detail_links:
            self.assertEqual(parse_qs(urlsplit(link["href"]).query),
                             {"next": [response.wsgi_request.get_full_path()]})

    def test_total_sort_is_numeric_in_both_directions(self):
        for direction, expected in (("asc", [self.records[Invoice.Status.ISSUED],
                                            self.records[Invoice.Status.DRAFT]]),
                                    ("desc", [self.records[Invoice.Status.DRAFT],
                                              self.records[Invoice.Status.ISSUED]])):
            with self.subTest(direction=direction):
                response = self.get_list(params={"sort": "total", "direction": direction})
                records = list(response.context["invoices"])
                pair = [invoice for invoice in records if invoice.pk in {i.pk for i in expected}]
                self.assertEqual(pair, expected)
                links = [a["href"] for a in self.markup(response).find("a")
                         if "sort-link" in a.get("class", "").split()]
                total = next(parse_qs(urlsplit(link).query) for link in links
                             if parse_qs(urlsplit(link).query).get("sort") == ["total"])
                self.assertEqual(total["direction"], ["desc" if direction == "asc" else "asc"])

    def test_pagination_keeps_all_filters_and_sorting_at_twenty_records(self):
        for _ in range(24):
            Invoice.objects.create(
                participant=self.participant, created_by=self.admin,
                period_start=date(2026, 10, 1), period_end=date(2026, 10, 31),
            )
        params = {"q": "BSC-", "participant": "Alexandria", "status": "draft",
                  "period_from": "2026-10-15", "period_to": "2026-10-15",
                  "sort": "invoice", "direction": "asc"}
        for page, count, summary in (("1", 20, "Showing 1-20 of 25 records"),
                                     ("2", 5, "Showing 21-25 of 25 records")):
            with self.subTest(page=page):
                response = self.get_list(params={**params, "page": page})
                self.assertEqual(response.context["invoices"].paginator.count, 25)
                self.assertEqual(len(response.context["invoices"]), count)
                self.assertContains(response, summary)
                target_page = "2" if page == "1" else "1"
                self.assertTrue(any(
                    parse_qs(urlsplit(a.get("href", "")).query)
                    == {**{key: [value] for key, value in params.items()}, "page": [target_page]}
                    for a in self.markup(response).find("a")
                ))

    def test_filtered_and_unfiltered_empty_states_keep_existing_copy(self):
        filtered = self.get_list(params={"participant": "Missing"})
        for text in ("No invoices match the current filters.",
                     "Clear the filters to review all billing records.", "Clear filters", "Showing 0 records"):
            self.assertContains(filtered, text)
        self.assertNotContains(filtered, "Create an invoice or adjust the filters")
        Invoice.objects.filter(invoice_type=Invoice.InvoiceType.SERVICE).delete()
        unfiltered = self.get_list()
        for text in ("No invoices found.", "Create an invoice or adjust the filters to review billing records.",
                     "Create Invoice", "Showing 0 records"):
            self.assertContains(unfiltered, text)
        self.assertNotContains(unfiltered, "No invoices match the current filters.")

    def test_default_order_and_logout_post_contract_are_preserved(self):
        response = self.get_list()
        self.assertEqual(list(response.context["invoices"]),
                         list(Invoice.objects.filter(invoice_type=Invoice.InvoiceType.SERVICE)
                              .order_by("-created_at")))
        logout_forms = [(attrs, children) for attrs, children in self.markup(response).forms
                        if attrs.get("action") == reverse("logout")]
        self.assertEqual(len(logout_forms), 2)
        for attrs, children in logout_forms:
            self.assertEqual(attrs.get("method"), "post")
            self.assertTrue(any(tag == "input" and a.get("name") == "csrfmiddlewaretoken"
                                for tag, a in children))
        self.assertContains(response, static("js/admin_nav.js"), count=1)

    def test_admin_filter_hook_retains_native_named_get_controls(self):
        params = {"q": "BSC-", "participant": "Alexandria", "status": "draft",
                  "period_from": "2026-10-01", "period_to": "2026-10-31"}
        for user in (self.admin, self.super_admin):
            with self.subTest(role=user.userprofile.role):
                response = self.get_list(user, params=params)
                forms = [(attrs, children) for attrs, children in self.markup(response).forms
                         if "data-invoice-filters" in attrs]
                self.assertEqual(len(forms), 1)
                attrs, children = forms[0]
                self.assertEqual(attrs.get("method"), "get")
                self.assertCountEqual(
                    [attrs["name"] for tag, attrs in children
                     if tag in ("input", "select", "textarea") and "name" in attrs],
                    list(params),
                )
                for name, kind in (("q", "search"), ("participant", "search"),
                                   ("period_from", "date"), ("period_to", "date")):
                    fields = [attrs for tag, attrs in children
                              if tag == "input" and attrs.get("name") == name]
                    self.assertEqual(len(fields), 1)
                    self.assertEqual(fields[0].get("type"), kind)
                    self.assertEqual(fields[0].get("value"), params[name])
                    self.assertNotIn("disabled", fields[0])
                    self.assertNotIn("hidden", fields[0])
                self.assertEqual(sum(tag == "select" and attrs.get("name") == "status"
                                     for tag, attrs in children), 1)
                self.assertTrue(any("selected" in option for option in
                                    self.markup(response).find("option", value="draft")))

    def test_admin_filter_dates_use_partial_and_unnamed_proxies_with_native_fallback(self):
        for user in (self.admin, self.super_admin):
            with self.subTest(role=user.userprofile.role):
                response = self.get_list(user, params={"period_from": "2026-10-01",
                                                      "period_to": "2026-10-31"})
                self.assertTemplateUsed(response, "invoices/partials/filter_date.html")
                markup = self.markup(response)
                roots = [attrs for _, attrs in markup.elements if "data-invoice-date" in attrs]
                self.assertEqual(len(roots), 2)
                proxies = [attrs for tag, attrs in markup.elements
                           if tag == "input" and "data-invoice-date-proxy" in attrs]
                self.assertEqual(len(proxies), 2)
                for proxy in proxies:
                    self.assertEqual(proxy.get("type"), "hidden")
                    self.assertNotIn("name", proxy)
                for name, value in (("period_from", "2026-10-01"), ("period_to", "2026-10-31")):
                    native = markup.find("input", type="date", name=name, value=value)
                    self.assertEqual(len(native), 1)
                    self.assertNotIn("hidden", native[0])
                    self.assertNotIn("disabled", native[0])
                triggers = [attrs for tag, attrs in markup.elements
                            if tag == "button" and "data-picker-trigger" in attrs]
                panels = [attrs for _, attrs in markup.elements if "data-picker-popover" in attrs]
                self.assertEqual(len(triggers), 2)
                self.assertEqual(len(panels), 2)
                for trigger in triggers:
                    self.assertEqual(trigger.get("type"), "button")
                    self.assertIn("hidden", trigger)
                    self.assertEqual(trigger.get("aria-expanded"), "false")
                for panel in panels:
                    self.assertIn("hidden", panel)

    def test_admin_filter_scripts_load_once_with_shared_picker_before_adapter(self):
        for user in (self.admin, self.super_admin):
            with self.subTest(role=user.userprofile.role):
                response = self.get_list(user)
                scripts = self.markup(response).find("script")
                positions = []
                for asset in ("js/date_time_picker.js", "js/r1_admin_invoice_filters.js"):
                    path = static(asset)
                    matches = [(index, attrs) for index, attrs in enumerate(scripts)
                               if attrs.get("src") == path]
                    self.assertEqual(len(matches), 1, f"Expected one script for {asset}")
                    index, attrs = matches[0]
                    positions.append(index)
                    self.assertIn("defer", attrs)
                    self.assertNotIn("async", attrs)
                self.assertLess(positions[0], positions[1])

    def test_accountant_and_sc_lists_have_no_filter_enhancement(self):
        for user, route in (
            (self.accountant, "invoice_placeholder"),
            (self.admin, "support_coordination_invoice_list"),
            (self.super_admin, "support_coordination_invoice_list"),
        ):
            with self.subTest(role=user.userprofile.role, route=route):
                response = self.get_list(user, route=route, params={"status": "draft",
                    "period_from": "2026-10-01", "period_to": "2026-10-31"})
                for marker in ("data-invoice-filters", "data-invoice-date", "data-invoice-date-proxy",
                               "r1_admin_invoice_filters.js", "date_time_picker.js"):
                    self.assertNotContains(response, marker)
                self.assertTemplateNotUsed(response, "invoices/partials/filter_date.html")
                markup = self.markup(response)
                self.assertEqual(len(markup.find("select", name="status")), 1)
                for name, value in (("period_from", "2026-10-01"), ("period_to", "2026-10-31")):
                    self.assertEqual(len(markup.find("input", type="date", name=name, value=value)), 1)

    def test_other_invoice_pages_have_no_filter_enhancement(self):
        for user in (self.admin, self.super_admin):
            self.client.force_login(user)
            urls = [reverse(name) for name in ("invoice_create", "invoice_settings", "exports_placeholder",
                                               "support_coordination_invoice_create")]
            urls.extend(reverse("invoice_detail", args=[invoice.pk]) for invoice in
                        (self.records[Invoice.Status.DRAFT], self.sc_invoice))
            for url in urls:
                with self.subTest(role=user.userprofile.role, url=url):
                    response = self.client.get(url)
                    self.assertEqual(response.status_code, 200)
                    for marker in ("data-invoice-filters", "data-invoice-date", "data-invoice-date-proxy",
                                   "r1_admin_invoice_filters.js", "date_time_picker.js"):
                        if url == reverse("invoice_create") and marker in (
                            "data-invoice-date", "data-invoice-date-proxy", "date_time_picker.js"
                        ):
                            continue
                        self.assertNotContains(response, marker)
                    self.assertTemplateNotUsed(response, "invoices/partials/filter_date.html")
