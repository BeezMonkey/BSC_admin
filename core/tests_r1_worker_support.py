from datetime import date, datetime, time
from decimal import Decimal
from html.parser import HTMLParser
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.test import TestCase, override_settings
from django.templatetags.static import static
from django.urls import reverse
from django.utils import timezone
from django.utils.html import escape

from accounts.models import UserProfile
from core.models import AuditLog
from participants.models import Participant, ParticipantWorkerAssignment
from scheduling.forms import ParticipantCancellationForm
from scheduling.models import ParticipantCancellation, Shift, SupportItem
from service_logs.models import ServiceLog
from workers.models import SupportWorker


class Elements(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.items = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.items.append((tag, dict(attrs)))


@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    },
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class WorkerSupportTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="support-ui-worker")
        UserProfile.objects.create(user=cls.user, role=UserProfile.Role.SUPPORT_WORKER,
                                   is_active_worker=True)
        cls.worker = SupportWorker.objects.create(user=cls.user, first_name="Alex", last_name="Example",
            email="support@example.invalid", phone="0400 000 000")
        cls.participant = Participant.objects.create(first_name="Mia", last_name="Example")
        cls.assignment = ParticipantWorkerAssignment.objects.create(worker=cls.worker,
            participant=cls.participant, start_date=date(2026, 1, 12))
        cls.item = SupportItem.objects.create(item_number="SUPPORT-UI-ONLY", name="Fictional support",
            price_limit=Decimal("73.58"), unit=SupportItem.Unit.HOUR)
        cls.shift = Shift.objects.create(worker=cls.worker, participant=cls.participant,
            service_date=date(2026, 10, 12), start_time=time(9), end_time=time(13),
            planned_hours=Decimal("4.00"), support_item=cls.item,
            service_type=Shift.ServiceType.COMMUNITY_ACCESS, status=Shift.Status.CONFIRMED,
            created_by=cls.user)

    def setUp(self):
        self.client.force_login(self.user)
        self.url = reverse("worker_participant_cancellation_create", args=[self.shift.pk])

    def payload(self, **overrides):
        return {"cancellation_type": "short_notice", "reason": "other",
                "received_at": "2026-10-12T08:00", "details": "Fictional participant cancellation.",
                **overrides}

    def assert_support_shell(self, response):
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "r1/worker_support_base.html")
        for resource in ("r1_tokens.css", "r1_shell.css", "r1_worker_support.css"):
            self.assertContains(response, static("css/" + resource), count=1)
        self.assertContains(response, "r1-worker-support")
        self.assertNotContains(response, "r1_worker_navigation.css")
        self.assertNotContains(response, "r1_worker_logs.css")

    def test_cancellation_uses_independent_support_shell(self):
        response = self.client.get(self.url)
        self.assert_support_shell(response)
        self.assertContains(response, "Report a cancellation for review.")
        self.assertContains(response, "support-info20.svg")

    def test_profile_uses_independent_read_only_support_shell(self):
        response = self.client.get(reverse("worker_profile"))
        self.assert_support_shell(response)
        for text in ("My Profile", "Contact details and participant assignments.", "Read-only profile",
                     "Contact details", "Employment", "support-profile-identity32.svg"):
            self.assertContains(response, text)
        self.assertNotContains(response, ">Edit<")

    def test_cancellation_preserves_important_original_text_and_values(self):
        response = self.client.get(self.url)
        for text in ("Report Participant Cancellation", self.participant.display_name, "Date",
                     "12/10/2026", "Rostered time", "9:00 am - 1:00 pm", "Service",
                     self.shift.get_service_type_display(), "Send for Review", "Cancel"):
            self.assertContains(response, text)
        self.assertContains(response, reverse("worker_shift_detail", args=[self.shift.pk]))

    def test_native_fields_labels_choices_required_and_default_are_unchanged(self):
        response = self.client.get(self.url)
        form = response.context["form"]
        self.assertEqual(set(form.fields), {"cancellation_type", "reason", "details", "received_at"})
        for field in form:
            self.assertContains(response, str(field), html=True)
            self.assertContains(response, field.label)
            self.assertContains(response, f'for="{field.id_for_label}"')
        self.assertContains(response, 'type="datetime-local"')
        self.assertIsNotNone(form.initial["received_at"])
        elements = Elements(response.content.decode()).items
        self.assertEqual(len([1 for tag, _ in elements if tag == "select"]), 2)
        self.assertEqual(len([1 for tag, _ in elements if tag == "textarea"]), 1)
        self.assertEqual(len([1 for tag, attrs in elements if tag == "form" and "action" not in attrs]), 1)
        self.assertContains(response, 'name="csrfmiddlewaretoken"')

    def test_success_preserves_all_saved_fields_audit_status_and_redirect(self):
        response = self.client.post(self.url, self.payload())
        self.assertRedirects(response, reverse("worker_shift_detail", args=[self.shift.pk]))
        cancellation = ParticipantCancellation.objects.get(shift=self.shift)
        for name in ("cancellation_type", "reason", "details"):
            self.assertEqual(getattr(cancellation, name), self.payload()[name])
        self.assertEqual(cancellation.received_at,
                         timezone.make_aware(datetime(2026, 10, 12, 8)))
        self.assertEqual(cancellation.previous_shift_status, Shift.Status.CONFIRMED)
        self.assertEqual(cancellation.submitted_by, self.user)
        self.assertEqual(cancellation.status, ParticipantCancellation.Status.PENDING)
        self.assertEqual(cancellation.claim_type, "CANC")
        self.shift.refresh_from_db()
        self.assertEqual(self.shift.status, Shift.Status.CANCELLATION_REVIEW)
        self.assertEqual(AuditLog.objects.filter(actor=self.user,
            action=AuditLog.Action.PARTICIPANT_CANCELLATION_SUBMITTED,
            object_type="ParticipantCancellation", object_id=str(cancellation.pk)).count(), 1)

    def test_duplicate_post_cannot_change_existing_report_or_add_audit(self):
        self.client.post(self.url, self.payload())
        self.assertEqual(self.client.post(self.url, self.payload(details="Duplicate")).status_code, 404)
        self.assertEqual(ParticipantCancellation.objects.count(), 1)
        self.assertEqual(ParticipantCancellation.objects.get().details, self.payload()["details"])
        self.assertEqual(AuditLog.objects.filter(
            action=AuditLog.Action.PARTICIPANT_CANCELLATION_SUBMITTED).count(), 1)

    def test_rejected_eligibility_get_and_post_stay_denied(self):
        for source, status in ((Shift.Source.UNSCHEDULED, Shift.Status.CONFIRMED),
                               (Shift.Source.SCHEDULED, Shift.Status.DRAFT),
                               (Shift.Source.SCHEDULED, Shift.Status.COMPLETED),
                               (Shift.Source.SCHEDULED, Shift.Status.CANCELLATION_REVIEW),
                               (Shift.Source.SCHEDULED, Shift.Status.CANCELLED)):
            with self.subTest(source=source, status=status):
                self.shift.source, self.shift.status = source, status
                self.shift.save(update_fields=["source", "status"])
                self.assertEqual(self.client.get(self.url).status_code, 404)
                self.assertEqual(self.client.post(self.url, self.payload()).status_code, 404)
        self.assertFalse(ParticipantCancellation.objects.exists())

    def test_existing_service_log_blocks_submission(self):
        ServiceLog.objects.create_from_shift(self.shift, actual_start_time=time(9),
            actual_end_time=time(13), actual_hours=Decimal("4"), kilometres=Decimal("0"),
            case_notes="Fictional existing log", worker_notes="")
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertEqual(self.client.post(self.url, self.payload()).status_code, 404)

    def test_invalid_errors_keep_bound_values_and_do_not_write(self):
        payload = self.payload(received_at="not-a-date", details='<script>alert("fictional")</script>')
        response = self.client.post(self.url, payload)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Enter a valid date/time.")
        for field in response.context["form"]:
            self.assertContains(response, str(field), html=True)
        self.assertContains(response, escape(payload["details"]))
        self.assertNotContains(response, payload["details"])
        self.assertFalse(ParticipantCancellation.objects.exists())
        self.assertFalse(AuditLog.objects.exists())
        self.shift.refresh_from_db()
        self.assertEqual(self.shift.status, Shift.Status.CONFIRMED)

    def test_required_and_choice_errors_are_visible(self):
        for overrides in ({"details": ""}, {"reason": "invalid"}, {"cancellation_type": "invalid"}):
            with self.subTest(overrides=overrides):
                response = self.client.post(self.url, self.payload(**overrides))
                self.assertEqual(response.status_code, 200)
                for errors in response.context["form"].errors.values():
                    for error in errors:
                        self.assertContains(response, escape(error))
        self.assertFalse(ParticipantCancellation.objects.exists())

    def test_non_field_errors_and_help_text_are_not_dropped(self):
        form = ParticipantCancellationForm(self.payload())
        form.fields["details"].help_text = "Fictional important field help."
        form.is_valid()
        form.add_error(None, "Fictional non-field explanation.")
        html = render_to_string("scheduling/participant_cancellation_form.html",
            {"form": form, "shift": self.shift}, request=self.client.get(self.url).wsgi_request)
        self.assertIn("Fictional non-field explanation.", html)
        self.assertIn("Fictional important field help.", html)

    def test_profile_dynamic_values_are_escaped_and_table_retains_all_labels(self):
        self.worker.first_name = '<b>Alex</b>'
        self.worker.phone = '<i>0400</i>'
        self.worker.email = 'long&fictional@example.invalid'
        self.worker.save()
        self.participant.first_name = '<script>Fictional</script>'
        self.participant.save()
        response = self.client.get(reverse("worker_profile"))
        for text in (self.worker.display_name, self.worker.email, self.worker.phone,
                     self.participant.display_name):
            self.assertContains(response, escape(text))
            if "<" in text:
                self.assertNotContains(response, text)
        for text in ("Email", "Phone", "Status", "Employment type", "Assigned Participants",
                     "Participant", "Start", "12/01/2026", self.worker.get_status_display(),
                     self.worker.get_employment_type_display()):
            self.assertContains(response, text)
        for label in ("Participant", "Start", "Status"):
            self.assertContains(response, f'data-label="{label}"')
        self.assertContains(response, "<table")
        self.assertContains(response, 'scope="col"', count=3)

    def test_profile_single_original_loop_filters_inactive_assignments(self):
        other = Participant.objects.create(first_name="InactiveOnly", last_name="Fictional")
        ParticipantWorkerAssignment.objects.create(worker=self.worker, participant=other,
            start_date=date(2026, 1, 1), is_active=False)
        response = self.client.get(reverse("worker_profile"))
        self.assertContains(response, self.participant.display_name, count=1)
        self.assertNotContains(response, "InactiveOnly")
        self.assertNotContains(response, "No active participants assigned.")

    def test_profile_empty_and_inactive_only_preserve_original_for_empty_semantics(self):
        self.assignment.delete()
        response = self.client.get(reverse("worker_profile"))
        self.assertContains(response, "No active participants assigned.", count=1)
        ParticipantWorkerAssignment.objects.create(worker=self.worker, participant=self.participant,
            start_date=date(2026, 1, 1), is_active=False)
        response = self.client.get(reverse("worker_profile"))
        self.assertNotContains(response, "No active participants assigned.")
        self.assertNotContains(response, self.participant.display_name)

    def test_profile_blank_phone_keeps_dash_fallback(self):
        self.worker.phone = ""
        self.worker.save(update_fields=["phone"])
        self.assertContains(self.client.get(reverse("worker_profile")), "<dd>-</dd>", html=True)

    def test_missing_profile_uses_unchanged_placeholder(self):
        user = get_user_model().objects.create_user(username="support-ui-missing")
        UserProfile.objects.create(user=user, role=UserProfile.Role.SUPPORT_WORKER,
                                   is_active_worker=True)
        self.client.force_login(user)
        response = self.client.get(reverse("worker_profile"))
        self.assertContains(response, "Your worker profile has not been set up yet.")
        self.assertTemplateUsed(response, "core/worker_placeholder.html")
        self.assertNotContains(response, "r1_worker_support.css")

    def test_navigation_keeps_four_destinations_menu_script_and_csrf_logout(self):
        for url, logout_count in ((self.url, 2), (reverse("worker_profile"), 3)):
            response = self.client.get(url)
            self.assertContains(response, 'class="worker-bottom-nav-link', count=4)
            self.assertContains(response, 'aria-controls="worker-mobile-drawer"')
            self.assertContains(response, static("js/worker_nav.js"), count=1)
            self.assertContains(response, f'method="post" action="{reverse("logout")}"', count=logout_count)
            forms = Elements(response.content.decode()).items
            self.assertEqual(sum(attrs.get("name") == "csrfmiddlewaretoken" for _, attrs in forms),
                             logout_count + int(url == self.url))

    def test_unauthenticated_and_unassigned_access_stays_guarded(self):
        self.client.logout()
        for url in (self.url, reverse("worker_profile")):
            self.assertEqual(self.client.get(url).status_code, 302)
        other = get_user_model().objects.create_user(username="support-ui-other")
        UserProfile.objects.create(user=other, role=UserProfile.Role.SUPPORT_WORKER,
                                   is_active_worker=True)
        SupportWorker.objects.create(user=other, first_name="Other", last_name="Fictional",
                                     email="other@example.invalid")
        self.client.force_login(other)
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertEqual(self.client.post(self.url, self.payload()).status_code, 404)
        self.assertNotContains(self.client.get(reverse("worker_profile")), self.worker.email)

    def test_support_css_and_assets_are_local_and_independent(self):
        css_path = Path(settings.BASE_DIR) / "static/css/r1_worker_support.css"
        self.assertTrue(css_path.is_file(), "Independent B02.3 stylesheet must exist")
        css = css_path.read_text()
        self.assertNotIn("@import", css)
        self.assertIn("pointer-events: none", css)
        self.assertIn("980px", css)
        for url in (self.url, reverse("worker_profile")):
            response = self.client.get(url)
            for tag, attrs in Elements(response.content.decode()).items:
                if tag == "img" and "r1-icon" in attrs.get("class", "").split():
                    self.assertEqual(attrs.get("alt"), "")
                    self.assertEqual(attrs.get("aria-hidden"), "true")
                    prefix = static("img/r1/icons/")
                    self.assertTrue(attrs["src"].startswith(prefix))
                    self.assertTrue((Path(settings.BASE_DIR) / "static/img/r1/icons" /
                                     attrs["src"].removeprefix(prefix)).is_file())
