from datetime import date, time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.template.loader import get_template
from django.urls import reverse

from accounts.models import UserProfile
from invoices.models import Invoice, InvoiceLine
from scheduling.models import SupportItem

from .forms import CoordinationLogEditForm, CoordinationLogForm
from .models import CoordinationLog, ParticipantCoordinatorAssignment
from .tests import create_coordinator, create_participant


@override_settings(STORAGES={
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
})
class CoordinationLogDurationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.sc = create_coordinator("duration-sc")
        cls.participant = create_participant()
        ParticipantCoordinatorAssignment.objects.create(
            participant=cls.participant, coordinator=cls.sc, start_date=date(2026, 1, 1),
        )
        cls.admin = get_user_model().objects.create_user(username="duration-admin")
        UserProfile.objects.create(user=cls.admin, role=UserProfile.Role.ADMIN)
        cls.log = CoordinationLog.objects.create(
            participant=cls.participant, coordinator=cls.sc, service_date=date(2026, 10, 1),
            start_time=time(9), end_time=time(10, 30), break_minutes=10,
            actual_hours=Decimal("1.33"), case_notes="Original case note.",
            coordinator_notes="Legacy follow-up note.",
        )

    def setUp(self):
        self.client.force_login(self.sc.user)
        self.create_url = reverse("coordinator_log_create")
        self.edit_url = reverse("coordinator_log_edit", args=[self.log.pk])

    def data(self, **overrides):
        data = {
            "participant": self.participant.pk, "service_date": "2026-10-01",
            "duration_hours": "1", "duration_minutes": "20",
            "coordination_type": "general", "case_notes": "Original case note.",
            "revision_reason": "correct_time",
        }
        data.update(overrides)
        return data

    def post_edit(self, **overrides):
        token = self.client.get(self.edit_url).context["revision_token"]
        return self.client.post(self.edit_url, self.data(revision_token=token, **overrides))

    def test_forms_use_duration_parts_and_only_a_date_picker(self):
        for url in (self.create_url, self.edit_url):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertContains(response, "Service duration")
                self.assertContains(response, 'name="duration_hours"')
                self.assertContains(response, 'name="duration_minutes"')
                self.assertContains(response, 'data-date-time-picker="date"', count=1)
                self.assertNotContains(response, 'data-date-time-picker="time"')
                for field in ("start_time", "end_time", "break_minutes", "actual_hours"):
                    self.assertNotIn(field, response.context["form"].fields)
                    self.assertNotContains(response, f'name="{field}"')

    def test_participant_prompt_is_readable_and_selection_stays_required(self):
        for url in (self.create_url, self.edit_url):
            with self.subTest(url=url):
                response = self.client.get(url)
                field = response.context["form"].fields["participant"]
                self.assertEqual(field.empty_label, "Select participant")
                self.assertTrue(field.required)
                self.assertContains(response, "Select participant")
        form = CoordinationLogForm(self.data(participant=""), coordinator=self.sc)
        self.assertFalse(form.is_valid())
        self.assertIn("participant", form.errors)

    def test_duration_input_enhancement_is_loaded_on_create_and_edit(self):
        for url in (self.create_url, self.edit_url):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertContains(response, 'src="/static/js/sc_log_form.js" defer', count=1)

    def test_coordination_type_appearance_preserves_choices_and_preselection(self):
        create_form = self.client.get(self.create_url).context["form"]
        self.assertEqual(create_form["coordination_type"].value(), CoordinationLog.CoordinationType.GENERAL)
        self.assertEqual(
            list(create_form.fields["coordination_type"].choices),
            list(CoordinationLog.CoordinationType.choices),
        )
        self.log.coordination_type = CoordinationLog.CoordinationType.PROVIDER_CONTACT
        self.log.save(update_fields=["coordination_type"])
        edit_form = self.client.get(self.edit_url).context["form"]
        self.assertEqual(edit_form["coordination_type"].value(), CoordinationLog.CoordinationType.PROVIDER_CONTACT)
        self.assertTrue(edit_form.fields["participant"].disabled)

    def test_anchored_calendar_is_sc_only(self):
        for url in (self.create_url, self.edit_url):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertContains(response, 'class="record-form sc-log-form"', count=1)
                self.assertContains(response, 'src="/static/js/sc_date_picker.js" defer', count=1)
        for name in (
            "service_logs/worker_service_log_form.html", "scheduling/shift_form.html",
            "scheduling/roster_planner.html", "scheduling/partials/date_time_picker_field.html",
        ):
            with self.subTest(template=name):
                source = get_template(name).template.source
                self.assertNotIn("sc-log-form", source)
                self.assertNotIn("sc_date_picker.js", source)

    def test_duration_converts_to_decimal_invoice_hours_without_clock_values(self):
        for hours, minutes, expected in ((0, 1, "0.02"), (0, 30, "0.50"), (1, 15, "1.25"), (1, 20, "1.33"), (24, 0, "24.00")):
            with self.subTest(hours=hours, minutes=minutes):
                form = CoordinationLogForm(
                    self.data(duration_hours=str(hours), duration_minutes=str(minutes)), coordinator=self.sc,
                )
                self.assertTrue(form.is_valid(), form.errors)
                log = form.save(commit=False)
                log.coordinator = self.sc
                log.save()
                log.refresh_from_db()
                self.assertEqual(log.actual_hours, Decimal(expected))
                self.assertIsNone(log.start_time)
                self.assertIsNone(log.end_time)
                self.assertEqual(log.break_minutes, 0)
                self.assertEqual(log.duration_parts, (hours, minutes))

    def test_missing_fractional_and_out_of_range_duration_is_rejected(self):
        cases = (
            {"duration_hours": "", "duration_minutes": ""},
            {"duration_hours": "0", "duration_minutes": "0"},
            {"duration_hours": "-1"}, {"duration_minutes": "-1"},
            {"duration_hours": "1.5"}, {"duration_minutes": "2.5"},
            {"duration_hours": "25"}, {"duration_minutes": "60"},
            {"duration_hours": "24", "duration_minutes": "1"},
            {"duration_hours": "NaN"}, {"duration_minutes": "Infinity"},
        )
        for overrides in cases:
            with self.subTest(overrides=overrides):
                form = CoordinationLogForm(self.data(**overrides), coordinator=self.sc)
                self.assertFalse(form.is_valid())
                self.assertTrue(set(form.errors) & {"duration_hours", "duration_minutes"})

    def test_create_ignores_forged_decimal_hours_and_clock_fields(self):
        response = self.client.post(self.create_url, self.data(
            duration_hours="0", duration_minutes="30", actual_hours="99.99",
            start_time="09:00", end_time="22:00", break_minutes="60",
        ))
        self.assertEqual(response.status_code, 302)
        log = CoordinationLog.objects.exclude(pk=self.log.pk).get()
        self.assertEqual(log.actual_hours, Decimal("0.50"))
        self.assertIsNone(log.start_time)
        self.assertIsNone(log.end_time)
        self.assertEqual(log.break_minutes, 0)

    def test_legacy_edit_prefills_duration_from_actual_hours_not_clock_span(self):
        form = CoordinationLogEditForm(instance=self.log, coordinator=self.sc)
        self.assertIn("duration_hours", form.fields)
        self.assertEqual(form["duration_hours"].value(), 1)
        self.assertEqual(form["duration_minutes"].value(), 20)
        response = self.post_edit()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No changes to submit.")
        self.assertFalse(self.log.changes.exists())

    def test_note_only_edit_preserves_legacy_decimal_quantity_and_times(self):
        self.log.actual_hours = Decimal("1.01")
        self.log.save(update_fields=["actual_hours"])
        response = self.post_edit(duration_minutes="1", case_notes="Updated case note.")
        self.assertEqual(response.status_code, 302)
        self.log.refresh_from_db()
        self.assertEqual(self.log.actual_hours, Decimal("1.01"))
        self.assertEqual(self.log.start_time, time(9))
        self.assertEqual(self.log.end_time, time(10, 30))
        self.assertEqual(self.log.break_minutes, 10)
        self.assertEqual(self.log.coordinator_notes, "Legacy follow-up note.")

    def test_duration_only_edit_resubmits_and_records_before_after(self):
        self.log.status = CoordinationLog.Status.APPROVED
        self.log.reviewed_by = self.admin
        self.log.save()
        response = self.post_edit(duration_hours="2", duration_minutes="15", actual_hours="77")
        self.assertEqual(response.status_code, 302)
        self.log.refresh_from_db()
        self.assertEqual(self.log.actual_hours, Decimal("2.25"))
        self.assertEqual(self.log.status, CoordinationLog.Status.SUBMITTED)
        self.assertIsNone(self.log.reviewed_by)
        change = self.log.changes.get()
        self.assertEqual(change.before["actual_hours"], "1.33")
        self.assertEqual(change.after["actual_hours"], "2.25")
        for field in ("start_time", "end_time", "break_minutes", "coordinator_notes"):
            self.assertEqual(change.before[field], change.after[field])

    def test_invalid_duration_keeps_other_form_values_and_does_not_save(self):
        response = self.post_edit(duration_minutes="60", case_notes="Unsaved note.")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Unsaved note.")
        self.assertIn("duration_minutes", response.context["form"].fields)
        self.assertEqual(response.context["form"]["duration_minutes"].value(), "60")
        self.log.refresh_from_db()
        self.assertEqual(self.log.actual_hours, Decimal("1.33"))
        self.assertEqual(self.log.case_notes, "Original case note.")
        self.assertFalse(self.log.changes.exists())

    def test_duration_only_logs_display_without_empty_clock_details(self):
        response = self.client.post(self.create_url, self.data(duration_hours="0", duration_minutes="30"))
        self.assertEqual(response.status_code, 302)
        log = CoordinationLog.objects.exclude(pk=self.log.pk).get()
        for user, route in ((self.sc.user, "coordinator_log_detail"), (self.admin, "coordination_log_detail")):
            with self.subTest(route=route):
                self.client.force_login(user)
                response = self.client.get(reverse(route, args=[log.pk]))
                self.assertContains(response, "Service duration")
                self.assertContains(response, "30m")
                self.assertNotContains(response, "Previously recorded time")
                self.assertNotContains(response, "Recorded break")

    def test_legacy_times_still_visible_as_previously_recorded(self):
        for user, route in ((self.sc.user, "coordinator_log_detail"), (self.admin, "coordination_log_detail")):
            with self.subTest(route=route):
                self.client.force_login(user)
                response = self.client.get(reverse(route, args=[self.log.pk]))
                self.assertContains(response, "Previously recorded time")
                self.assertContains(response, "Recorded break")
                self.assertContains(response, "1h 20m")

    def test_invoice_uses_converted_duration_and_locked_log_stays_read_only(self):
        response = self.client.post(self.create_url, self.data(duration_hours="0", duration_minutes="30"))
        self.assertEqual(response.status_code, 302)
        log = CoordinationLog.objects.exclude(pk=self.log.pk).get()
        log.status = CoordinationLog.Status.APPROVED
        log.save(update_fields=["status"])
        item = SupportItem.objects.create(
            item_number="07_002_0106_8_3", name="Coordination", unit=SupportItem.Unit.HOUR,
            price_limit=Decimal("100.00"), is_active=True,
        )
        invoice = Invoice.objects.create(
            participant=self.participant, period_start=log.service_date, period_end=log.service_date,
            created_by=self.admin, invoice_type=Invoice.InvoiceType.SUPPORT_COORDINATION,
        )
        line = InvoiceLine.objects.create_from_coordination_log(invoice, log, item)
        self.assertEqual(line.quantity, Decimal("0.50"))
        self.assertEqual(line.line_total, Decimal("50.00"))
        edit_url = reverse("coordinator_log_edit", args=[log.pk])
        self.assertEqual(self.client.get(edit_url).status_code, 403)
        self.assertEqual(self.client.post(edit_url, self.data(duration_hours="9")).status_code, 403)
