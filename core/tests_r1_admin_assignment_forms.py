from datetime import date
import importlib.util

from django import forms
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.test import TestCase, override_settings
from django.urls import reverse

from core import tests_r1_admin_people_forms as form_helpers
from core import tests_r1_admin_people_lists as people_fixtures
from coordinators.forms import ParticipantCoordinatorAssignmentForm
from coordinators.models import ParticipantCoordinatorAssignment
from participants.forms import ParticipantWorkerAssignmentForm
from participants.models import ParticipantWorkerAssignment


@override_settings(STORAGES={
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
})
class R1AdminAssignmentFormTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        people_fixtures.R1AdminPeopleListTests.setUpTestData.__func__(cls)

    def setUp(self):
        self.client.force_login(self.admin)

    def routes(self):
        return [("participant_assign_worker", self.person, "worker", "Select worker"),
                ("coordinator_assign_participant", self.coordinator, "participant", "Select participant")]

    def response(self, route, person):
        response = self.client.get(reverse(route, args=[person.pk]))
        self.assertEqual(response.status_code, 200)
        return response

    def helper(self):
        self.assertIsNotNone(importlib.util.find_spec("core.templatetags.r1_forms"), "Missing presentation-only choice_hint helper")
        from core.templatetags.r1_forms import choice_hint
        return choice_hint

    def test_two_assignment_pages_reuse_content_only_r1_form_base(self):
        for route, person, _, _ in self.routes():
            response = self.response(route, person)
            self.assertTemplateUsed(response, "r1/admin_people_form_base.html")
            self.assertContains(response, 'class="r1-ui r1-people-form"', count=1)
            self.assertContains(response, static("css/r1_admin_assignment_forms.css"), count=1)
            self.assertContains(response, static("css/r1_admin_people_forms.css"), count=1)
            self.assertNotContains(response, static("css/r1_shell.css"))

    def test_exact_original_five_named_fields_and_native_dates_remain(self):
        for route, person, choice, _ in self.routes():
            response = self.response(route, person)
            tags = form_helpers.FormElements(response.content.decode()).tags
            controls = [(tag, attrs) for tag, attrs in tags if tag in ("input", "select", "textarea") and attrs.get("name") not in (None, "csrfmiddlewaretoken")]
            self.assertEqual({a["name"] for _, a in controls}, {choice, "start_date", "end_date", "is_active", "notes"})
            self.assertEqual(len(controls), 5)
            for name in ("start_date", "end_date"):
                field = next(a for _, a in controls if a["name"] == name)
                self.assertEqual(field["type"], "date")
                self.assertNotIn("disabled", field)

    def test_empty_choice_is_a_hint_not_a_valid_default(self):
        for route, person, name, hint in self.routes():
            response = self.response(route, person)
            self.assertContains(response, hint)
            parsed = people_fixtures.SelectFields(response.content.decode()).fields[name]
            self.assertEqual(sum(value == "" for value, _ in parsed), 1)
            self.assertEqual([value for value, selected in parsed if selected], [""])
            select = next(a for tag, a in form_helpers.FormElements(response.content.decode()).tags if tag == "select" and a.get("name") == name)
            self.assertIn("required", select)

    def test_rendering_does_not_mutate_original_form_field(self):
        for route, person, name, _ in self.routes():
            form = self.response(route, person).context["form"]
            self.assertEqual(form.fields[name].empty_label, "---------")
            self.assertIn("---------", str(form[name]))

    def test_hint_helper_copies_the_field_and_preserves_original_widget(self):
        hint = self.helper()
        form = ParticipantWorkerAssignmentForm(participant=self.person)
        original = form["worker"]
        before = str(original)
        shown = hint(original, "Select worker")
        self.assertIsNot(shown, original)
        self.assertIsNot(shown.field, original.field)
        self.assertIsNot(shown.field.widget, original.field.widget)
        self.assertIn("Select worker", str(shown))
        self.assertEqual(str(original), before)
        self.assertIs(form.fields["worker"], original.field)
        self.assertEqual(shown.field.required, original.field.required)
        self.assertEqual(list(shown.field.queryset.values_list("pk", flat=True)), list(original.field.queryset.values_list("pk", flat=True)))

    def test_hint_helper_keeps_bound_selection_attributes_and_escaping(self):
        hint = self.helper()
        form = ParticipantCoordinatorAssignmentForm(data={"participant": self.unassigned.pk, "start_date": "2026-10-31", "is_active": "on"}, coordinator=self.coordinator)
        field = hint(form["participant"], "Select <participant>")
        self.assertEqual(str(field.value()), str(self.unassigned.pk))
        self.assertIn("Select &lt;participant&gt;", str(field))
        self.assertEqual(field.id_for_label, form["participant"].id_for_label)
        self.assertEqual(form.fields["participant"].empty_label, "---------")
        plain = forms.Form();plain.fields["notes"] = forms.CharField()
        self.assertIs(hint(plain["notes"], "Unused"), plain["notes"])

    def test_original_active_choice_filters_are_preserved(self):
        for route, person, name, _ in self.routes():
            response = self.response(route, person)
            parsed = people_fixtures.SelectFields(response.content.decode()).fields[name]
            expected = {str(pk) for pk in response.context["form"].fields[name].queryset.values_list("pk", flat=True)} | {""}
            self.assertEqual({value for value, _ in parsed}, expected)
        response = self.response("participant_assign_worker", self.person)
        self.assertNotIn(str(self.archived_worker.pk), {v for v, _ in people_fixtures.SelectFields(response.content.decode()).fields["worker"]})

    def test_original_required_and_date_errors_render_without_saving(self):
        for route, person, name, hint in self.routes():
            counts = (ParticipantWorkerAssignment.objects.count(), ParticipantCoordinatorAssignment.objects.count())
            response = self.client.post(reverse(route, args=[person.pk]), {name: "", "start_date": "2026-10-31", "end_date": "2026-10-30", "is_active": "on"})
            self.assertEqual(response.status_code, 200)
            for message in ("This field is required.", "End date cannot be earlier than start date.", hint):
                self.assertContains(response, message)
            self.assertEqual(counts, (ParticipantWorkerAssignment.objects.count(), ParticipantCoordinatorAssignment.objects.count()))

    def test_existing_date_error_descriptions_resolve(self):
        for route, person, name, _ in self.routes():
            response = self.client.post(reverse(route, args=[person.pk]), {name: "", "start_date": "2026-10-31", "end_date": "2026-10-30", "is_active": "on"})
            tags = form_helpers.FormElements(response.content.decode()).tags
            ids = {a["id"] for _, a in tags if a.get("id")}
            self.assertIn("id_end_date_error", ids)
            for _, attrs in tags:
                if "id_end_date_error" in attrs.get("aria-describedby", "").split():
                    self.assertTrue(set(attrs["aria-describedby"].split()) <= ids)

    def test_existing_assignment_uniqueness_rule_still_rejects_invalid_form(self):
        # This existing field validation is not the deferred duplicate-submit audit.
        for route, person, name, value, message in (
            ("participant_assign_worker", self.person, "worker", self.worker.pk, "This worker already has an active assignment for this participant."),
            ("coordinator_assign_participant", self.coordinator, "participant", self.person.pk, "This participant already has an active assignment for this support coordinator."),
        ):
            response = self.client.post(reverse(route, args=[person.pk]), {name: value, "start_date": "2026-10-31", "is_active": "on"})
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, message)

    def test_original_worker_save_target_and_values_are_unchanged(self):
        response = self.client.post(reverse("participant_assign_worker", args=[self.unassigned.pk]), {"worker": self.worker.pk, "start_date": "2026-10-31", "end_date": "2027-10-30", "is_active": "on", "notes": "Fictional original save path"})
        self.assertRedirects(response, reverse("participant_detail", args=[self.unassigned.pk]))
        item = ParticipantWorkerAssignment.objects.get(participant=self.unassigned, worker=self.worker)
        self.assertEqual(item.start_date, date(2026, 10, 31))
        self.assertEqual(item.end_date, date(2027, 10, 30))
        self.assertTrue(item.is_active)
        self.assertEqual(item.notes, "Fictional original save path")

    def test_original_coordinator_save_target_and_values_are_unchanged(self):
        response = self.client.post(reverse("coordinator_assign_participant", args=[self.coordinator.pk]), {"participant": self.unassigned.pk, "start_date": "2026-10-31", "is_active": "on", "notes": "Fictional original SC path"})
        self.assertRedirects(response, reverse("coordinator_detail", args=[self.coordinator.pk]))
        item = ParticipantCoordinatorAssignment.objects.get(coordinator=self.coordinator, participant=self.unassigned)
        self.assertEqual(item.start_date, date(2026, 10, 31))
        self.assertTrue(item.is_active)
        self.assertEqual(item.notes, "Fictional original SC path")

    def test_inactive_coordinator_guard_is_not_replaced_by_ui(self):
        response = self.client.get(reverse("coordinator_assign_participant", args=[self.inactive_sc.pk]))
        self.assertRedirects(response, reverse("coordinator_detail", args=[self.inactive_sc.pk]))

    def test_non_admin_get_and_post_permissions_remain(self):
        for user in self.other_users:
            self.client.force_login(user)
            for route, person, _, _ in self.routes():
                url = reverse(route, args=[person.pk])
                self.assertEqual(self.client.get(url).status_code, 403)
                self.assertEqual(self.client.post(url, {}).status_code, 403)

    def test_current_navigation_csrf_and_return_links_remain(self):
        for route, person, _, _ in self.routes():
            response = self.response(route, person)
            nav = render_to_string("core/partials/admin_navigation_links.html", {"request": response.wsgi_request})
            self.assertContains(response, nav, count=2)
            self.assertContains(response, static("js/admin_nav.js"), count=1)
            self.assertContains(response, 'class="record-form" method="post" novalidate')
            # Assignment form plus the two unchanged desktop/mobile logout forms.
            self.assertContains(response, 'name="csrfmiddlewaretoken"', count=3)
            target = "participant_detail" if route == "participant_assign_worker" else "coordinator_detail"
            self.assertContains(response, 'href="' + reverse(target, args=[person.pk]) + '"', count=2)

    def test_assignment_styles_do_not_leak_to_accepted_people_forms_or_details(self):
        for route, person in (("participant_create", None), ("worker_edit", self.worker), ("coordinator_edit", self.coordinator), ("participant_detail", self.person), ("worker_detail", self.worker), ("coordinator_detail", self.coordinator)):
            response = self.client.get(reverse(route, args=[person.pk] if person else []))
            self.assertEqual(response.status_code, 200)
            self.assertNotContains(response, static("css/r1_admin_assignment_forms.css"))

    def test_shared_calendar_and_assignment_grid_are_used_on_both_pages(self):
        for route, person, _, _ in self.routes():
            response = self.response(route, person)
            self.assertTemplateUsed(response, "r1/partials/people_form_date.html")
            self.assertContains(response, "data-people-date-proxy", count=2)
            self.assertContains(response, 'class="form-grid participant-assignment-grid"' if route == "participant_assign_worker" else 'class="form-grid assignment-form-grid"')
            self.assertContains(response, static("js/date_time_picker.js"), count=1)
            self.assertContains(response, static("js/r1_people_form_dates.js"), count=1)
