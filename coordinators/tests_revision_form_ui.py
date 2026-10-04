from datetime import date, time
from decimal import Decimal
from html.parser import HTMLParser

from django.template.loader import render_to_string
from django.templatetags.static import static
from django.test import TestCase, override_settings
from django.urls import reverse

from .forms import CoordinationLogEditForm
from .models import CoordinationLog, ParticipantCoordinatorAssignment
from .tests import create_coordinator, create_participant


class RevisionDetailsParser(HTMLParser):
    def __init__(self, markup):
        super().__init__()
        self.containers = []
        self.feed(markup)

    def handle_starttag(self, tag, attrs):
        if dict(attrs).get("id") == "sc-revision-details":
            self.containers.append((tag, dict(attrs)))


@override_settings(STORAGES={
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
})
class CoordinationLogRevisionFormUITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.sc = create_coordinator("revision-form-ui")
        cls.participant = create_participant()
        ParticipantCoordinatorAssignment.objects.create(
            participant=cls.participant, coordinator=cls.sc, start_date=date(2026, 1, 1),
        )
        cls.log = CoordinationLog.objects.create(
            participant=cls.participant, coordinator=cls.sc,
            service_date=date(2026, 10, 1), start_time=time(9), end_time=time(10),
            actual_hours=Decimal("1.00"), case_notes="Original case note.",
        )

    def setUp(self):
        self.client.force_login(self.sc.user)
        self.edit_url = reverse("coordinator_log_edit", args=[self.log.pk])

    def assert_details_visible(self, markup, expected):
        containers = RevisionDetailsParser(markup).containers
        self.assertEqual(len(containers), 1)
        tag, attrs = containers[0]
        self.assertEqual(tag, "div")
        self.assertEqual("hidden" not in attrs, expected)
        self.assertNotIn("Add details", markup)

    def render_initial(self, **initial):
        form = CoordinationLogEditForm(
            coordinator=self.sc, instance=self.log, initial=initial,
        )
        return render_to_string("coordinators/sc_coordination_log_form.html", {
            "form": form, "editing": True, "log": self.log,
        })

    def post_edit(self, **overrides):
        token = self.client.get(self.edit_url).context["revision_token"]
        data = {
            "participant": self.participant.pk, "service_date": "2026-10-01",
            "duration_hours": "1", "duration_minutes": "0", "coordination_type": "general",
            "case_notes": "Revised case note.", "coordinator_notes": "",
            "revision_reason": "update_notes", "revision_details": "",
            "revision_token": token,
        }
        data.update(overrides)
        return self.client.post(self.edit_url, data)

    def test_edit_starts_with_hidden_details_and_unframed_revision(self):
        response = self.client.get(self.edit_url)
        self.assert_details_visible(response.content.decode(), False)
        self.assertTrue(response.context["form"].fields["revision_details"].disabled)
        self.assertContains(response, 'name="revision_details"')
        self.assertContains(response, 'class="card form-section"', count=2)
        self.assertContains(response, 'class="sc-log-revision"')
        self.assertContains(response, 'class="record-form sc-log-form" method="post" novalidate')
        self.assertContains(response, static("css/portal.css"))
        self.assertContains(response, static("css/sc_log_revision.css"))
        self.assertContains(response, static("js/sc_log_revision.js"))

    def test_preset_details_are_hidden_on_render(self):
        for reason in ("appointment_changed", "correct_time", "update_notes", "admin_feedback"):
            with self.subTest(reason=reason):
                markup = self.render_initial(revision_reason=reason)
                self.assert_details_visible(markup, False)

    def test_other_shows_details_on_render_with_required_label(self):
        markup = self.render_initial(revision_reason="other")
        self.assert_details_visible(markup, True)
        self.assertIn("Additional details (required)", markup)

    def test_details_visibility_is_rendered_without_javascript(self):
        for reason in ("", "appointment_changed", "correct_time", "update_notes", "admin_feedback", "other"):
            with self.subTest(reason=reason):
                required = reason == "other"
                markup = self.render_initial(revision_reason=reason)
                self.assert_details_visible(markup, required)

    def test_other_details_remain_escaped_on_render(self):
        markup = self.render_initial(
            revision_reason="other", revision_details="Retained <details> & context.",
        )
        self.assert_details_visible(markup, True)
        self.assertIn("Retained &lt;details&gt; &amp; context.", markup)

    def test_other_validation_error_stays_open_and_retains_edits(self):
        response = self.post_edit(revision_reason="other")
        self.assertEqual(response.status_code, 200)
        self.assertIn("revision_details", response.context["form"].errors)
        self.assert_details_visible(response.content.decode(), True)
        self.assertContains(response, "Additional details (required)")
        self.assertContains(response, "Revised case note.")
        self.assertContains(response, '<option value="other" selected>Other</option>', html=True)

    def test_other_details_error_stays_visible_and_retains_text(self):
        details = "x" * 2001
        response = self.post_edit(revision_reason="other", revision_details=details)
        self.assertEqual(response.status_code, 200)
        self.assertIn("revision_details", response.context["form"].errors)
        self.assert_details_visible(response.content.decode(), True)
        self.assertContains(response, details)
        self.assertContains(response, "Additional details (required)")

    def test_unrelated_errors_keep_preset_details_hidden_and_discarded(self):
        response = self.post_edit(case_notes="", revision_details="Stale hidden explanation.")
        self.assertEqual(response.status_code, 200)
        self.assertIn("case_notes", response.context["form"].errors)
        self.assert_details_visible(response.content.decode(), False)
        self.assertNotContains(response, "Stale hidden explanation.")

    def test_create_form_has_no_revision_ui_or_assets(self):
        response = self.client.get(reverse("coordinator_log_create"))
        self.assertEqual(response.status_code, 200)
        for value in ("revision_reason", "revision_details", "sc-log-revision", "sc_log_revision"):
            self.assertNotContains(response, value)
        self.assertContains(response, 'class="card form-section"', count=2)
        self.assertContains(response, static("css/portal.css"))
        self.assertContains(response, 'class="record-form sc-log-form" method="post" novalidate')
