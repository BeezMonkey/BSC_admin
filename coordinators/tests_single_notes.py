from datetime import date, time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import UserProfile

from .models import CoordinationLog, CoordinationLogChange, ParticipantCoordinatorAssignment
from .tests import create_coordinator, create_participant


@override_settings(STORAGES={
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
})
class CoordinationLogSingleNotesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.sc = create_coordinator("single-notes-sc")
        cls.participant = create_participant()
        ParticipantCoordinatorAssignment.objects.create(
            participant=cls.participant, coordinator=cls.sc, start_date=date(2026, 1, 1),
        )
        cls.admin = get_user_model().objects.create_user(username="single-notes-admin")
        UserProfile.objects.create(user=cls.admin, role=UserProfile.Role.ADMIN)
        cls.log = CoordinationLog.objects.create(
            participant=cls.participant, coordinator=cls.sc,
            service_date=date(2026, 10, 1), start_time=time(9), end_time=time(10),
            actual_hours=Decimal("1.00"), case_notes="Original case note.",
            coordinator_notes="Legacy follow-up <note>.",
        )

    def setUp(self):
        self.client.force_login(self.sc.user)
        self.create_url = reverse("coordinator_log_create")
        self.edit_url = reverse("coordinator_log_edit", args=[self.log.pk])

    def payload(self, **overrides):
        data = {
            "participant": self.participant.pk, "service_date": "2026-10-01",
            "duration_hours": "1", "duration_minutes": "0", "coordination_type": "general",
            "case_notes": "Updated work, outcome and follow-up.",
            "revision_reason": "update_notes",
        }
        data.update(overrides)
        return data

    def edit(self, **overrides):
        token = self.client.get(self.edit_url).context["revision_token"]
        return self.client.post(self.edit_url, self.payload(revision_token=token, **overrides))

    def test_create_and_edit_have_one_required_notes_input_with_placeholder(self):
        for url in (self.create_url, self.edit_url):
            with self.subTest(url=url):
                response = self.client.get(url)
                form = response.context["form"]
                self.assertNotIn("coordinator_notes", form.fields)
                self.assertTrue(form.fields["case_notes"].required)
                self.assertContains(response, 'name="case_notes"', count=1)
                self.assertNotContains(response, 'name="coordinator_notes"')
                self.assertEqual(
                    form.fields["case_notes"].widget.attrs.get("placeholder"),
                    "Record the work completed, outcome, and any follow-up.",
                )

    def test_placeholder_does_not_prefill_or_save_blank_notes(self):
        response = self.client.get(self.create_url)
        self.assertFalse(response.context["form"]["case_notes"].value())
        count = CoordinationLog.objects.count()
        for url in (self.create_url, self.edit_url):
            with self.subTest(url=url):
                data = self.payload(case_notes="   ")
                if url == self.edit_url:
                    data["revision_token"] = self.client.get(url).context["revision_token"]
                response = self.client.post(url, data)
                self.assertEqual(response.status_code, 200)
                self.assertIn("case_notes", response.context["form"].errors)
        self.assertEqual(CoordinationLog.objects.count(), count)
        self.log.refresh_from_db()
        self.assertEqual(self.log.case_notes, "Original case note.")
        self.assertFalse(self.log.changes.exists())

    def test_create_ignores_retired_notes_field(self):
        response = self.client.post(self.create_url, self.payload(coordinator_notes="Forged notes"))
        self.assertEqual(response.status_code, 302)
        created = CoordinationLog.objects.exclude(pk=self.log.pk).get()
        self.assertEqual(created.coordinator_notes, "")
        self.assertEqual(created.case_notes, "Updated work, outcome and follow-up.")

    def test_edits_preserve_legacy_notes_even_when_posted(self):
        for index, extra in enumerate(({}, {"coordinator_notes": ""}, {"coordinator_notes": "Forged notes"})):
            with self.subTest(extra=extra):
                response = self.edit(case_notes=f"Changed case note {index}.", **extra)
                self.assertEqual(response.status_code, 302)
                self.log.refresh_from_db()
                self.assertEqual(self.log.coordinator_notes, "Legacy follow-up <note>.")
                change = self.log.changes.first()
                self.assertEqual(change.before["coordinator_notes"], self.log.coordinator_notes)
                self.assertEqual(change.after["coordinator_notes"], self.log.coordinator_notes)
                self.assertNotIn("coordinator_notes", [item["key"] for item in change.content_changes])

    def test_no_change_with_legacy_notes_does_not_create_revision(self):
        for extra in ({}, {"coordinator_notes": ""}, {"coordinator_notes": "Forged notes"}):
            with self.subTest(extra=extra):
                response = self.edit(case_notes="Original case note.", **extra)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "No changes to submit.")
        self.assertFalse(self.log.changes.exists())
        self.log.refresh_from_db()
        self.assertEqual(self.log.coordinator_notes, "Legacy follow-up <note>.")

    def test_nonempty_legacy_notes_remain_visible_to_sc_and_admin(self):
        for user, route in ((self.sc.user, "coordinator_log_detail"), (self.admin, "coordination_log_detail")):
            with self.subTest(route=route):
                self.client.force_login(user)
                response = self.client.get(reverse(route, args=[self.log.pk]))
                self.assertContains(response, "Legacy follow-up &lt;note&gt;.")
                self.assertNotContains(response, "Legacy follow-up <note>.")

    def test_empty_legacy_notes_section_is_omitted_from_details(self):
        self.log.coordinator_notes = ""
        self.log.save(update_fields=["coordinator_notes"])
        for user, route, label in (
            (self.sc.user, "coordinator_log_detail", "Coordinator Notes"),
            (self.admin, "coordination_log_detail", "Coordinator notes"),
        ):
            with self.subTest(route=route):
                self.client.force_login(user)
                response = self.client.get(reverse(route, args=[self.log.pk]))
                self.assertNotContains(response, label)
                self.assertNotContains(response, "No coordinator notes provided.")

    def test_old_coordinator_notes_history_remains_readable(self):
        change = CoordinationLogChange.objects.create(
            log=self.log, actor=self.sc.user, kind=CoordinationLogChange.Kind.REVISION,
            reason="Update notes", before={"coordinator_notes": "Earlier legacy note."},
            after={"coordinator_notes": "Later legacy note."},
        )
        for user, route in ((self.sc.user, "coordinator_log_detail"), (self.admin, "coordination_log_detail")):
            with self.subTest(route=route):
                self.client.force_login(user)
                response = self.client.get(reverse(route, args=[self.log.pk]))
                self.assertContains(response, "Earlier legacy note.")
                self.assertContains(response, "Later legacy note.")
        change.refresh_from_db()
        self.assertEqual(change.before, {"coordinator_notes": "Earlier legacy note."})
        self.assertEqual(change.after, {"coordinator_notes": "Later legacy note."})
