"""B04.3 preview contracts. Execute only through the isolated test harness."""

from datetime import date
from decimal import Decimal
from html.parser import HTMLParser
from urllib.parse import urlsplit

from django.test import TestCase, override_settings
from django.templatetags.static import static
from django.urls import reverse
from django.utils import timezone
from django.utils.html import escape

from accounts.models import UserProfile
from invoices import tests_cancellations as cancellation_fixtures
from invoices import tests_invoices as fixtures
from invoices.forms import TravelClaimForm
from invoices.models import Invoice, InvoiceBillingAdjustment, InvoiceLine
from service_logs.models import ServiceLog


class PreviewMarkup(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.elements, self.forms, self.rows = [], [], []
        self.form = self.row = None
        self.nested_forms = False
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        node = (tag, attrs)
        self.elements.append(node)
        if tag == "form":
            self.nested_forms |= self.form is not None
            self.form = (attrs, [])
            self.forms.append(self.form)
        elif self.form is not None:
            self.form[1].append(node)
        if tag == "tr":
            self.row = (attrs, [])
            self.rows.append(self.row)
        elif self.row is not None:
            self.row[1].append(node)

    def handle_endtag(self, tag):
        if tag == "form":
            self.form = None
        elif tag == "tr":
            self.row = None

    def find(self, tag, **attrs):
        return [values for name, values in self.elements if name == tag
                and all(values.get(key) == value for key, value in attrs.items())]

    def marked(self, name):
        return [attrs for _, attrs in self.elements if name in attrs]


@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    },
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class R1AdminInvoiceCreateTests(TestCase):
    create_user_with_role = fixtures.InvoiceGenerationTests.create_user_with_role
    create_service_log = fixtures.InvoiceGenerationTests.create_service_log
    create_travel_support_item = fixtures.InvoiceGenerationTests.create_travel_support_item
    create_cancellation_for_participant = (
        cancellation_fixtures.ParticipantCancellationInvoiceTests.create_cancellation_for_participant
    )

    def setUp(self):
        fixtures.InvoiceGenerationTests.setUp(self)
        self.super_admin = self.create_user_with_role("b043-super", UserProfile.Role.SUPER_ADMIN)
        self.coordinator_user = self.create_user_with_role("b043-coord", UserProfile.Role.SUPPORT_COORDINATOR)
        self.accountant_user.is_staff = True
        self.accountant_user.save(update_fields=["is_staff"])
        self.zero_log = self.create_service_log(service_date=date(2026, 6, 1), kilometres=Decimal("0.00"))
        self.km_log = self.create_service_log(service_date=date(2026, 6, 2), kilometres=Decimal("25.00"))
        self.other_log = self.create_service_log(participant=self.other_participant, service_date=date(2026, 6, 3))
        self.cancellation = self.create_cancellation_for_participant(self.participant, date(2026, 6, 4))
        self.travel_item = self.create_travel_support_item()
        self.history_reason = "Fictional correction <reviewed> & retained in full."
        self.zero_log.case_notes = "Fictional original notes.\nSecond line remains visible."
        self.zero_log.save(update_fields=["case_notes", "updated_at"])
        self.history = InvoiceBillingAdjustment.objects.create(
            service_log=self.zero_log, invoice=None, invoice_number="B043-DELETED-SNAPSHOT",
            original_values={"item_number": "B043-ORIGINAL", "item_name": "Original fictional item",
                "kilometres": "0.00", "actual_start_time": "09:00", "actual_end_time": "11:00",
                "break_minutes": 0, "hours": "2.00"},
            billing_values={"item_number": "B043-BILLING", "item_name": "Billing fictional item",
                "kilometres": "12.50", "actual_start_time": "09:15", "actual_end_time": "11:00",
                "break_minutes": 15, "hours": "1.50"},
            reason=self.history_reason, created_by=self.admin_user,
        )

    def period(self):
        return {"participant": str(self.participant.pk), "period_start": "2026-06-01", "period_end": "2026-06-30"}

    def preview(self, data=None, user=None):
        self.client.force_login(user or self.admin_user)
        response = self.client.get(reverse("invoice_create"), data or {})
        self.assertEqual(response.status_code, 200)
        return response

    def markup(self, response):
        return PreviewMarkup(response.content.decode())

    def invoice_forms(self, markup):
        return [(attrs, children) for attrs, children in markup.forms
                if attrs.get("method") == "post" and attrs.get("action") != reverse("logout")]

    def values(self, children, name):
        return [attrs.get("value", "") for tag, attrs in children
                if tag in ("input", "select", "textarea") and attrs.get("name") == name]

    def assert_form_contract(self, form, participant, logs, cancellations):
        attrs, children = form
        self.assertIn(attrs.get("action", ""), ("", reverse("invoice_create")))
        self.assertEqual(self.values(children, "participant"), [str(participant.pk)])
        self.assertEqual(len(self.values(children, "period_start")), 1)
        self.assertEqual(len(self.values(children, "period_end")), 1)
        self.assertCountEqual(self.values(children, "service_log_ids"), [str(log.pk) for log in logs])
        self.assertCountEqual(self.values(children, "participant_cancellation_ids"), [str(c.pk) for c in cancellations])
        self.assertTrue(any(tag == "input" and a.get("name") == "csrfmiddlewaretoken" and a.get("value")
                            for tag, a in children))
        self.assertEqual(sum(tag == "th" for tag, _ in children), 9)
        self.assertTrue(any(tag == "button" and a.get("type") == "submit" for tag, a in children))

    def test_admin_and_super_admin_activate_only_the_authorized_preview_variants(self):
        variants = ({}, self.period(), {"service_log_ids": [self.zero_log.pk]},
                    {"service_log_ids": [self.zero_log.pk, self.other_log.pk]},
                    {"service_log_ids": [self.zero_log.pk], "participant_cancellation_ids": [self.cancellation.pk]},
                    {"participant_cancellation_ids": [self.cancellation.pk]})
        for user in (self.admin_user, self.super_admin):
            for data in variants:
                with self.subTest(role=user.userprofile.role, data=data):
                    response = self.preview(data, user)
                    self.assertIs(response.context.get("r1_invoice_create"), True)
                    self.assertContains(response, "r1-admin-invoice-create")
                    self.assertContains(response, "r1-ui r1-admin")
                    self.assertContains(response, static("css/r1_admin_invoice_create.css"), count=1)

    def test_accountant_preview_remains_legacy_without_new_date_markup_or_assets(self):
        for data in ({}, self.period(), {"service_log_ids": [self.zero_log.pk, self.km_log.pk]}):
            with self.subTest(data=data):
                response = self.preview(data, self.accountant_user)
                self.assertIs(response.context.get("r1_invoice_create"), False)
                for marker in ("r1-admin-invoice-create", "r1_admin_invoice_create.css", "r1_admin_invoice_create.js",
                               "date_time_picker.js"):
                    self.assertNotContains(response, marker)
                self.assertTemplateNotUsed(response, "invoices/partials/create_date.html")
                self.assertContains(response, "Create Invoice")
                self.assertContains(response, "Select approved service logs for one participant and period.")
                markup = self.markup(response)
                self.assertEqual(len(markup.find("input", type="date", name="period_start")), 1)
                self.assertEqual(len(markup.find("input", type="date", name="period_end")), 1)
                self.assertNotContains(response, "data-billing-fields")

    def test_other_pages_keep_their_existing_scope_and_nonfinance_roles_are_denied(self):
        invoice = Invoice.objects.create(participant=self.participant, created_by=self.admin_user,
            period_start=date(2026, 6, 1), period_end=date(2026, 6, 30))
        self.client.force_login(self.admin_user)
        urls = [reverse(name) for name in ("invoice_placeholder", "invoice_settings",
                "support_coordination_invoice_list", "support_coordination_invoice_create", "service_log_list")]
        urls.extend((reverse("invoice_detail", args=[invoice.pk]),
                     reverse("service_log_detail", args=[self.zero_log.pk])))
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                for marker in ("r1-admin-invoice-create", "r1_admin_invoice_create.css", "r1_admin_invoice_create.js"):
                    self.assertNotContains(response, marker)
                self.assertTemplateNotUsed(response, "invoices/partials/create_date.html")
        for user in (self.worker_user, self.coordinator_user):
            self.client.force_login(user)
            self.assertEqual(self.client.get(reverse("invoice_create")).status_code, 403)

    def test_short_claim_help_is_scoped_to_r1_and_retains_the_full_description(self):
        data = {"service_log_ids": [self.km_log.pk]}
        for user in (self.admin_user, self.super_admin):
            response = self.preview(data, user)
            self.assertContains(response, 'class="invoice-claim-help-inline">Approved amount</span>', count=1)
            self.assertContains(response, 'class="invoice-claim-help-full">Admin-approved amount</span>', count=1)
            self.assertContains(response, 'title="Admin-approved amount"', count=1)
            self.assertEqual(len(self.markup(response).find("input", name=f"travel-{self.km_log.pk}-amount")), 1)
        response = self.preview(data, self.accountant_user)
        self.assertNotContains(response, "invoice-claim-help-inline")
        self.assertNotContains(response, "invoice-claim-help-full")
        self.assertContains(response, "Admin-approved amount")

    def test_drawer_time_enhancement_is_scoped_and_keeps_native_post_controls(self):
        asset = static("js/r1_invoice_adjustment_time.js")
        for user in (self.admin_user, self.super_admin):
            response = self.preview({"service_log_ids": [self.km_log.pk]}, user)
            markup = self.markup(response)
            self.assertContains(response, asset, count=1)
            for part in ("actual_start_time", "actual_end_time"):
                name = f"adjustment-{self.km_log.pk}-{part}"
                self.assertEqual(len(markup.find("input", type="time", name=name)), 1)
                self.assertEqual(sum(attrs.get("name") == name for _, attrs in markup.elements), 1)
            self.assertNotContains(response, "data-r1-time-panel")
        response = self.preview({"service_log_ids": [self.km_log.pk]}, self.accountant_user)
        self.assertNotContains(response, asset)

    def test_scoped_assets_load_once_after_existing_billing_assets(self):
        for user in (self.admin_user, self.super_admin):
            with self.subTest(role=user.userprofile.role):
                response = self.preview(self.period(), user)
                markup = self.markup(response)
                positions = []
                for name in ("app.css", "admin.css", "invoice_billing.css", "r1_tokens.css",
                             "r1_shell.css", "r1_admin_invoice_create.css"):
                    matches = [i for i, attrs in enumerate(markup.find("link"))
                               if urlsplit(attrs.get("href", "")).path == static("css/" + name)]
                    self.assertEqual(len(matches), 1, name)
                    positions.append(matches[0])
                self.assertEqual(positions, sorted(positions))
                scripts = markup.find("script")
                positions = {}
                for name in ("support_item_picker.js", "invoice_billing.js", "date_time_picker.js",
                             "r1_admin_invoice_create.js"):
                    matches = [(i, attrs) for i, attrs in enumerate(scripts)
                               if urlsplit(attrs.get("src", "")).path == static("js/" + name)]
                    self.assertEqual(len(matches), 1, name)
                    i, attrs = matches[0]
                    positions[name] = i
                    self.assertIn("defer", attrs)
                    self.assertNotIn("async", attrs)
                self.assertLess(positions["support_item_picker.js"], positions["invoice_billing.js"])
                self.assertLess(positions["date_time_picker.js"], positions["r1_admin_invoice_create.js"])

    def test_bound_date_partial_preserves_real_widgets_required_values_and_unnamed_proxies(self):
        for user in (self.admin_user, self.super_admin):
            with self.subTest(role=user.userprofile.role):
                response = self.preview(self.period(), user)
                self.assertTemplateUsed(response, "invoices/partials/create_date.html")
                form = response.context["form"]
                markup = self.markup(response)
                filters = [children for attrs, children in markup.forms if attrs.get("method") == "get"]
                self.assertEqual(len(filters), 1)
                self.assertCountEqual([a["name"] for tag, a in filters[0]
                                      if tag in ("input", "select", "textarea") and "name" in a],
                                     ["participant", "period_start", "period_end"])
                for name in ("period_start", "period_end"):
                    expected = PreviewMarkup(str(form[name].as_widget())).find("input")[0]
                    native = markup.find("input", type="date", name=name)
                    self.assertEqual(len(native), 1)
                    for key, value in expected.items():
                        self.assertEqual(native[0].get(key), value)
                    self.assertIn("required", native[0])
                    self.assertNotIn("hidden", native[0])
                    self.assertNotIn("disabled", native[0])
                proxies = [a for tag, a in filters[0] if tag == "input" and a.get("type") == "hidden" and "name" not in a]
                self.assertEqual(len(proxies), 2)
                triggers = [a for tag, a in filters[0] if tag == "button" and "data-picker-trigger" in a]
                self.assertEqual(len(triggers), 2)
                for trigger in triggers:
                    self.assertEqual(trigger.get("type"), "button")
                    self.assertIn("hidden", trigger)

    def test_initial_and_invalid_filters_keep_copy_native_fields_and_bound_errors(self):
        initial = self.preview()
        for text in ("Create Invoice", "Select approved service logs for one participant and period.",
                     "Participant", "Period start", "Period end", "Preview Logs", "Approved Billing Records",
                     "No approved logs found", "Choose another participant or date range, or approve submitted service logs before creating an invoice."):
            self.assertContains(initial, text)
        self.assertEqual(self.invoice_forms(self.markup(initial)), [])
        variants = ({"participant": str(self.participant.pk), "period_start": "2026-06-01"},
                    {**self.period(), "period_start": "not-a-date"},
                    {**self.period(), "period_start": "2026-06-30", "period_end": "2026-06-01"})
        for data in variants:
            with self.subTest(data=data):
                response = self.preview(data)
                form = response.context["form"]
                self.assertTrue(form.is_bound)
                self.assertTrue(form.errors)
                markup = self.markup(response)
                for name in ("period_start", "period_end"):
                    expected = PreviewMarkup(str(form[name].as_widget())).find("input")[0]
                    actual = markup.find("input", type="date", name=name)
                    self.assertEqual(len(actual), 1)
                    for key, value in expected.items():
                        self.assertEqual(actual[0].get(key), value)
                    for error in form[name].errors:
                        self.assertContains(response, escape(error))
                    trigger = markup.find("button", **{"aria-controls": f"id_{name}-calendar"})[0]
                    self.assertIn(f"id_{name}-client-error", trigger.get("aria-describedby", "").split())
                    if form[name].errors:
                        self.assertEqual(trigger.get("aria-invalid"), "true")
                        self.assertIn(f"id_{name}_error", trigger.get("aria-describedby", "").split())
                self.assertEqual(self.invoice_forms(markup), [])
        self.assertFalse(Invoice.objects.exists())
        self.assertEqual(ServiceLog.objects.filter(status=ServiceLog.Status.APPROVED).count(), 3)

    def test_filter_preview_keeps_only_approved_uninvoiced_rows_and_nine_columns(self):
        submitted = self.create_service_log(service_date=date(2026, 6, 5), status=ServiceLog.Status.SUBMITTED)
        billed = self.create_service_log(service_date=date(2026, 6, 6))
        invoice = Invoice.objects.create(participant=self.participant, created_by=self.admin_user,
            period_start=date(2026, 6, 1), period_end=date(2026, 6, 30))
        InvoiceLine.objects.create_from_service_log(invoice, billed)
        response = self.preview(self.period())
        self.assertEqual({log.pk for log in response.context["service_logs"]}, {self.zero_log.pk, self.km_log.pk})
        self.assertEqual({c.pk for c in response.context["participant_cancellations"]}, {self.cancellation.pk})
        markup = self.markup(response)
        forms = self.invoice_forms(markup)
        self.assertEqual(len(forms), 1)
        self.assert_form_contract(forms[0], self.participant, [], [])
        self.assertEqual({a["data-log-id"] for a in markup.marked("data-billing-row")},
                         {str(self.zero_log.pk), str(self.km_log.pk)})
        for log in (submitted, billed, self.other_log):
            self.assertNotContains(response, f'data-log-id="{log.pk}"')
        for label in ("Date", "Worker", "Support item", "Rate / hr", "Hours", "Travel km", "Travel claim", "Line total", "Actions"):
            self.assertContains(response, label)

    def test_single_participant_selection_preserves_repeated_hidden_ids_in_get_and_post(self):
        logs = [self.zero_log, self.km_log]
        response = self.preview({"service_log_ids": [log.pk for log in logs]})
        markup = self.markup(response)
        self.assertFalse(markup.nested_forms)
        filters = [children for attrs, children in markup.forms if attrs.get("method") == "get"]
        self.assertEqual(len(filters), 1)
        self.assertCountEqual(self.values(filters[0], "service_log_ids"), [str(log.pk) for log in logs])
        forms = self.invoice_forms(markup)
        self.assertEqual(len(forms), 1)
        self.assert_form_contract(forms[0], self.participant, logs, [])
        self.assertEqual(self.values(forms[0][1], "period_start"), ["2026-06-01"])
        self.assertEqual(self.values(forms[0][1], "period_end"), ["2026-06-02"])

    def test_grouped_preview_keeps_one_csrf_post_and_own_real_controls_per_participant(self):
        response = self.preview({"service_log_ids": [self.zero_log.pk, self.km_log.pk, self.other_log.pk]})
        markup = self.markup(response)
        self.assertFalse(markup.nested_forms)
        forms = self.invoice_forms(markup)
        self.assertEqual(len(forms), 2)
        expected = {str(self.participant.pk): (self.participant, [self.zero_log, self.km_log]),
                    str(self.other_participant.pk): (self.other_participant, [self.other_log])}
        for form in forms:
            participant, logs = expected[self.values(form[1], "participant")[0]]
            self.assert_form_contract(form, participant, logs, [])
            owned_ids = {str(log.pk) for log in logs}
            for tag, attrs in form[1]:
                name = attrs.get("name", "")
                if tag in ("input", "select", "textarea") and name.startswith(("adjustment-", "travel-")):
                    self.assertIn(name.split("-", 2)[1], owned_ids)
            for log in logs:
                self.assertEqual(self.values(form[1], f"adjustment-{log.pk}-source_version"), [log.updated_at.isoformat()])
                self.assertEqual(len(self.values(form[1], f"travel-{log.pk}-amount")), 1)

    def test_mixed_selection_preserves_service_and_cancellation_rows_and_hidden_ids(self):
        response = self.preview({"service_log_ids": [self.zero_log.pk],
                                 "participant_cancellation_ids": [self.cancellation.pk]})
        markup = self.markup(response)
        forms = self.invoice_forms(markup)
        self.assertEqual(len(forms), 1)
        self.assert_form_contract(forms[0], self.participant, [self.zero_log], [self.cancellation])
        filters = [children for attrs, children in markup.forms if attrs.get("method") == "get"][0]
        self.assertEqual(self.values(filters, "participant_cancellation_ids"), [str(self.cancellation.pk)])
        rows = [(a, children) for a, children in markup.rows if "data-invoice-row" in a]
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(sum(tag == "td" for tag, _ in children) == 9 for _, children in rows))
        self.assertContains(response, "Approved rostered charge")
        self.assertContains(response, "No travel claim")
        self.assertEqual(self.values(forms[0][1], "period_end"), ["2026-06-04"])

    def test_cancellation_only_preview_has_no_service_adjustments_or_travel_controls(self):
        response = self.preview({"participant_cancellation_ids": [self.cancellation.pk]})
        markup = self.markup(response)
        forms = self.invoice_forms(markup)
        self.assertEqual(len(forms), 1)
        self.assert_form_contract(forms[0], self.participant, [], [self.cancellation])
        rows = [(a, children) for a, children in markup.rows if "data-invoice-row" in a]
        self.assertEqual(len(rows), 1)
        self.assertNotIn("data-billing-row", rows[0][0])
        self.assertEqual(Decimal(rows[0][0]["data-hours"]), self.cancellation.shift.planned_hours)
        self.assertEqual(Decimal(rows[0][0]["data-price"]), self.support_item.price_limit)
        self.assertFalse(any(a.get("name", "").startswith(("adjustment-", "travel-")) for _, a in forms[0][1]))
        self.assertContains(response, "No travel claim")
        self.assertContains(response, "$65.47")

    def test_row_data_source_versions_reasons_time_and_claim_controls_are_not_cloned(self):
        response = self.preview({"service_log_ids": [self.km_log.pk]})
        markup = self.markup(response)
        rows = markup.marked("data-billing-row")
        self.assertEqual(len(rows), 1)
        attrs = rows[0]
        expected = {"data-log-id": str(self.km_log.pk), "data-original-item": str(self.support_item.pk),
                    "data-original-code": self.support_item.item_number,
                    "data-original-name": self.support_item.name, "data-service-date": "02/06/2026",
                    "data-original-start": "09:00", "data-original-end": "11:00", "data-original-break": "0",
                    "data-billing-errors": "false"}
        for name, value in expected.items():
            self.assertEqual(attrs.get(name), value)
        for name, value in (("data-hours", "2.00"), ("data-original-hours", "2.00"),
                            ("data-original-km", "25.00"), ("data-price", "65.47"), ("data-original-price", "65.47")):
            self.assertEqual(Decimal(attrs[name]), Decimal(value))
        children = self.invoice_forms(markup)[0][1]
        for name in ("source_version", "correct_time", "actual_start_time", "actual_end_time", "break_minutes",
                     "support_item", "kilometres", "reason", "reason_details"):
            self.assertEqual(len(self.values(children, f"adjustment-{self.km_log.pk}-{name}")), 1, name)
        self.assertEqual(self.values(children, f"adjustment-{self.km_log.pk}-source_version"), [self.km_log.updated_at.isoformat()])
        self.assertEqual(len(self.values(children, f"travel-{self.km_log.pk}-amount")), 1)
        row_form = response.context["selected_invoice_groups"][0]["invoice_rows"][0]["adjustment_form"]
        for value, _ in row_form.fields["reason"].choices:
            self.assertTrue(markup.find("option", value=value))

    def test_existing_drawer_time_discard_and_real_control_hooks_remain_available(self):
        response = self.preview({"service_log_ids": [self.zero_log.pk]})
        markup = self.markup(response)
        self.assertTemplateUsed(response, "invoices/invoice_adjustment_drawer.html")
        for marker in ("data-billing-drawer", "data-billing-discard", "data-drawer-body", "data-drawer-close",
                       "data-drawer-cancel", "data-drawer-apply", "data-discard-keep", "data-discard-confirm",
                       "data-billing-fields", "data-billing-time-fields", "data-billing-time-summary",
                       "data-billing-edit-time", "data-billing-restore-time", "data-billing-time-error",
                       "data-billing-claim-home", "data-billing-claim-field", "data-billing-drawer-claim",
                       "data-billing-claim-empty", "data-billing-claim-error", "data-billing-reason"):
            self.assertEqual(len(markup.marked(marker)), 1, marker)
        for marker, title in (("data-billing-drawer", "invoice-drawer-title"),
                              ("data-billing-discard", "invoice-discard-title")):
            self.assertTrue(any(marker in a and a.get("aria-labelledby") == title for a in markup.find("dialog")))
        for text in ("Adjust billing details", "Correct service time", "Originally submitted", "Apply changes",
                     "Discard unapplied changes?", "Keep editing", "Discard changes", "Original values retained",
                     "Changes are saved when the invoice is created."):
            self.assertContains(response, text)

    def test_original_notes_full_history_and_deleted_snapshot_remain_in_preview(self):
        response = self.preview({"service_log_ids": [self.zero_log.pk]})
        self.assertTemplateUsed(response, "invoices/billing_adjustment_history.html")
        for text in ("Original log notes &amp; adjustment history", "Fictional original notes.",
                     "Second line remains visible.", "Billing adjustments (1)", f"Log #{self.zero_log.pk}",
                     "B043-DELETED-SNAPSHOT", "(invoice deleted)", "B043-ORIGINAL", "Original fictional item",
                     "B043-BILLING", "Billing fictional item", "0.00", "12.50", "09:00 - 11:00",
                     "09:15 - 11:00", "0 min break; 2.00 h", "15 min break; 1.50 h",
                     str(escape(self.history_reason)), timezone.localtime(self.history.created_at).strftime("%d/%m/%Y %H:%M")):
            self.assertContains(response, text)

    def test_invalid_adjustment_posts_retain_bound_values_errors_and_source_versions(self):
        self.client.force_login(self.admin_user)
        prefix = f"adjustment-{self.km_log.pk}-"
        variants = (({"kilometres": "30", "reason": ""}, "reason"),
                    ({"correct_time": "on", "actual_start_time": "09:00", "actual_end_time": "08:00",
                      "break_minutes": "0", "reason": "incorrect_time"}, "actual_end_time"),
                    ({"source_version": "2000-01-01T00:00:00+00:00"}, "__all__"))
        for changes, error_field in variants:
            with self.subTest(changes=changes):
                data = {**self.period(), "service_log_ids": [self.km_log.pk],
                        prefix + "source_version": self.km_log.updated_at.isoformat(),
                        f"travel-{self.km_log.pk}-amount": "0.00"}
                data.update({prefix + name: value for name, value in changes.items()})
                response = self.client.post(reverse("invoice_create"), data)
                self.assertEqual(response.status_code, 200)
                row = response.context["invoice_rows"][0]
                self.assertIn(error_field, row["adjustment_form"].errors)
                markup = self.markup(response)
                self.assertEqual(len(markup.find("input", name=prefix + "source_version")), 1)
                self.assertEqual(markup.find("input", name=prefix + "source_version")[0].get("value"), data[prefix + "source_version"])
                self.assertEqual(markup.marked("data-billing-row")[0].get("data-billing-errors"), "true")
                for errors in row["adjustment_form"].errors.values():
                    for error in errors:
                        self.assertContains(response, escape(error))
                self.assertFalse(Invoice.objects.exists())
                self.km_log.refresh_from_db()
                self.assertEqual(self.km_log.actual_hours, Decimal("2.00"))
                self.assertEqual(self.km_log.kilometres, Decimal("25.00"))

    def test_zero_travel_rate_and_role_specific_claim_visibility_contracts_are_retained(self):
        self.travel_item.price_limit = Decimal("0.00")
        self.travel_item.save(update_fields=["price_limit"])
        response = self.preview({"service_log_ids": [self.zero_log.pk, self.km_log.pk]})
        self.assertEqual(response.context["travel_unit_price"], Decimal("0.00"))
        self.assertEqual(Decimal(self.markup(response).marked("data-billing-drawer")[0]["data-travel-price"]), Decimal("0.00"))
        for log in (self.zero_log, self.km_log):
            self.assertEqual(len(self.markup(response).find("input", name=f"travel-{log.pk}-amount")), 1)
            for amount in ("", "0", "0.00"):
                claim = TravelClaimForm(data={f"travel-{log.pk}-amount": amount},
                    prefix=f"travel-{log.pk}", service_log=log, confirmed_kilometres=log.kilometres)
                self.assertTrue(claim.is_valid())
                self.assertEqual(claim.cleaned_data["amount"], Decimal("0.00"))
        legacy = self.preview({"service_log_ids": [self.zero_log.pk, self.km_log.pk]}, self.accountant_user)
        self.assertFalse(self.markup(legacy).find("input", name=f"travel-{self.zero_log.pk}-amount"))
        self.assertEqual(len(self.markup(legacy).find("input", name=f"travel-{self.km_log.pk}-amount")), 1)
        self.assertContains(legacy, "No travel recorded")

