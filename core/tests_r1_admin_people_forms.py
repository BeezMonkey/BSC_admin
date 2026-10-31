from html.parser import HTMLParser
from pathlib import Path

from django.conf import settings
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.test import TestCase, override_settings
from django.urls import reverse

from core import tests_r1_admin_people_lists as people_fixtures
from participants.forms import ParticipantForm


class FormElements(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.tags = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


@override_settings(STORAGES={
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
})
class R1AdminPeopleFormTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        people_fixtures.R1AdminPeopleListTests.setUpTestData.__func__(cls)

    def setUp(self):
        self.client.force_login(self.admin)

    def routes(self):
        return [("participant_create", None), ("participant_edit", self.person),
                ("worker_create", None), ("worker_edit", self.worker),
                ("coordinator_create", None), ("coordinator_edit", self.coordinator)]

    def get_form(self, route, person=None):
        response = self.client.get(reverse(route, args=[person.pk] if person else []))
        self.assertEqual(response.status_code, 200)
        return response

    def test_six_forms_use_content_only_r1_base(self):
        for route, person in self.routes():
            with self.subTest(route=route):
                response = self.get_form(route, person)
                self.assertTemplateUsed(response, "r1/admin_people_form_base.html")
                self.assertContains(response, 'class="r1-ui r1-people-form"', count=1)
                self.assertContains(response, static("css/r1_admin_people_forms.css"), count=1)
                self.assertContains(response, static("css/r1_tokens.css"), count=1)
                self.assertNotContains(response, static("css/r1_shell.css"))
                self.assertContains(response, '<div class="app-shell" data-admin-theme>')

    def test_every_original_bound_field_is_present_exactly_once(self):
        for route, person in self.routes():
            with self.subTest(route=route):
                response = self.get_form(route, person)
                tags = FormElements(response.content.decode()).tags
                names = [a.get("name") for t, a in tags if t in ("input", "select", "textarea")]
                for name in response.context["form"].fields:
                    self.assertEqual(names.count(name), 1, name)

    def test_navigation_global_header_and_original_scripts_unchanged(self):
        for route, person in self.routes():
            response = self.get_form(route, person)
            navigation = render_to_string("core/partials/admin_navigation_links.html", {"request": response.wsgi_request})
            self.assertContains(response, navigation, count=2)
            self.assertContains(response, static("js/admin_nav.js"), count=1)
            self.assertContains(response, 'class="user-label"')
            self.assertContains(response, 'class="button secondary topbar-logout"')

    def test_original_named_dates_keep_native_type_and_use_approved_calendar(self):
        for route, person in self.routes():
            response = self.get_form(route, person)
            form = response.context["form"]
            dates = [name for name in form.fields if getattr(form.fields[name].widget, "input_type", None) == "date"]
            tags = FormElements(response.content.decode()).tags
            for name in dates:
                inputs = [a for t, a in tags if t == "input" and a.get("name") == name]
                self.assertEqual(inputs[0]["type"], "date")
                self.assertNotIn("disabled", inputs[0])
            if dates:
                self.assertTemplateUsed(response, "r1/partials/people_form_date.html")
                self.assertContains(response, "data-people-date-proxy", count=len(dates))
                self.assertContains(response, static("js/date_time_picker.js"), count=1)
            self.assertContains(response, static("js/r1_people_form_dates.js"), count=1)

    def test_participant_keeps_compact_groups_and_sc_name_modifier(self):
        for route, person in self.routes()[:2]:
            response = self.get_form(route, person)
            self.assertContains(response, 'class="locality-row field-wide"')
            self.assertContains(response, 'class="field field-wide coordinator-name-field"')
            self.assertContains(response, '<span>Address</span>', html=True)
            self.assertContains(response, 'name="plan_manager_email"')
            self.assertContains(response, 'name="support_coordinator_phone"')

    def test_empty_optional_address_is_collapsed_and_original_field_retained(self):
        response = self.get_form("participant_create")
        tags = FormElements(response.content.decode()).tags
        optional = [a for t, a in tags if t == "details" and "data-optional-address" in a]
        self.assertEqual(len(optional), 1)
        self.assertNotIn("open", optional[0])
        self.assertContains(response, 'name="address_line_2"', count=1)
        self.assertContains(response, "Address line 2 (optional)")

    def test_existing_address_line2_is_visible_without_data_merge(self):
        self.person.address_line_2 = "Fictional Unit 4"
        self.person.save()
        response = self.get_form("participant_edit", self.person)
        optional = [a for t, a in FormElements(response.content.decode()).tags if t == "details" and "data-optional-address" in a]
        self.assertTrue(optional)
        self.assertIn("open", optional[0])
        self.assertContains(response, 'value="Fictional Unit 4"')
        self.person.refresh_from_db()
        self.assertEqual(self.person.address_line_2, "Fictional Unit 4")

    def test_invalid_address_line2_opens_and_displays_original_error(self):
        form = ParticipantForm(data={"first_name": "Mia", "last_name": "Parker", "status": "active", "address_line_2": "x" * 256})
        self.assertFalse(form.is_valid())
        self.assertIn("address_line_2", form.errors)
        html = render_to_string("participants/participant_form.html", {"form": form, "title": "Add Participant"})
        optional = [a for t, a in FormElements(html).tags if t == "details" and "data-optional-address" in a]
        self.assertTrue(optional)
        self.assertIn("open", optional[0])
        self.assertIn(str(form.errors["address_line_2"][0]), html)

    def test_original_postcode_plan_and_required_errors_remain(self):
        response = self.client.post(reverse("participant_create"), {"first_name": "", "last_name": "", "status": "active", "postcode": "123", "plan_start_date": "2027-10-12", "plan_end_date": "2026-10-12"})
        self.assertEqual(response.status_code, 200)
        for text in ("This field is required.", "Enter a 4-digit Australian postcode.", "Plan end date cannot be earlier than plan start date."):
            self.assertContains(response, text)
        self.assertContains(response, 'aria-invalid="true"')

    def test_validation_descriptions_resolve_to_actual_error_elements(self):
        response = self.client.post(reverse("participant_create"), {"first_name": "", "last_name": "", "status": "active", "postcode": "123", "plan_start_date": "2027-10-12", "plan_end_date": "2026-10-12"})
        tags = FormElements(response.content.decode()).tags
        ids = {a["id"] for _, a in tags if a.get("id")}
        for _, attrs in tags:
            for target in attrs.get("aria-describedby", "").split():
                self.assertIn(target, ids)

    def test_edit_forms_do_not_add_username_or_password_controls(self):
        for route, person in self.routes():
            if not route.endswith("_edit") or route.startswith("participant"):
                continue
            response = self.get_form(route, person)
            for name in ("username", "password1", "password2"):
                self.assertNotContains(response, 'name="' + name + '"')

    def test_worker_account_archive_instructions_and_checkbox_preserved(self):
        response = self.get_form("worker_edit", self.worker)
        for text in ("Login access controls whether this worker can sign in to the worker portal.",
                     "Turn this off to stop this worker signing in. Their worker record and history are kept.",
                     "Set Worker status to Inactive to archive this worker.",
                     "Archived workers are removed from new scheduling and assignment choices. Existing shifts, service logs, invoices, and documents are kept."):
            self.assertContains(response, text)
        self.assertContains(response, 'name="account_active"')

    def test_original_return_targets_and_post_forms_remain(self):
        for route, person in self.routes():
            response = self.get_form(route, person)
            self.assertContains(response, 'class="record-form" method="post" novalidate')
            self.assertContains(response, '<button type="submit">Save</button>', count=1)
            self.assertContains(response, 'name="csrfmiddlewaretoken"')

    def test_non_admin_roles_still_denied_on_all_six_forms(self):
        for user in self.other_users:
            self.client.force_login(user)
            for route, person in self.routes():
                response = self.client.get(reverse(route, args=[person.pk] if person else []))
                self.assertEqual(response.status_code, 403, (user.username, route))

    def test_unrelated_details_do_not_import_form_styles(self):
        for route, person in [("participant_detail", self.person), ("worker_detail", self.worker), ("coordinator_detail", self.coordinator)]:
            response = self.get_form(route, person)
            self.assertNotContains(response, static("css/r1_admin_people_forms.css"))

    def test_scoped_assets_preserve_mobile_calendar_fallback_and_half_width(self):
        css = Path(settings.BASE_DIR) / "static/css/r1_admin_people_forms.css"
        script = Path(settings.BASE_DIR) / "static/js/r1_people_form_dates.js"
        self.assertTrue(css.is_file())
        self.assertTrue(script.is_file())
        text = css.read_text(encoding="utf-8")
        self.assertIn(".r1-people-form", text)
        self.assertIn("coordinator-name-field", text)
        self.assertIn("max-width:calc((100% - 24px) / 2)", text)
        adapter = script.read_text(encoding="utf-8")
        self.assertIn(".r1-people-form .record-form", adapter)
        self.assertIn('(min-width: 761px) and (hover: hover) and (pointer: fine)', adapter)
        self.assertIn('native.tabIndex = desktop.matches ? -1 : 0', adapter)
