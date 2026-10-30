from datetime import date
from html.parser import HTMLParser
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.test import TestCase, override_settings
from django.urls import reverse

from core import tests_r1_admin_people_lists as people_fixtures
from documents.models import Document


class DetailElements(HTMLParser):
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
class R1AdminPeopleDetailTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        people_fixtures.R1AdminPeopleListTests.setUpTestData.__func__(cls)
        cls.person.preferred_name = "Mia"
        cls.person.worker_visible_notes = "Fictional complete support note\n" + "LongUnbrokenNote" * 20
        cls.person.address_access_instructions = "Use the main entrance."
        cls.person.risk_safety_notes = "Original safety note."
        cls.person.internal_notes = "Internal Admin note, not an eligibility decision."
        cls.person.save()
        cls.coordinator.notes = "Full coordinator note\n" + "LongCoordinatorNote" * 20
        cls.coordinator.save()

    def setUp(self):
        self.client.force_login(self.admin)

    def routes(self):
        return [("participant_detail", self.person), ("worker_detail", self.worker),
                ("coordinator_detail", self.coordinator)]

    def get_detail(self, route, person):
        response = self.client.get(reverse(route, args=[person.pk]))
        self.assertEqual(response.status_code, 200)
        return response

    def test_three_details_opt_into_content_only_base_and_styles(self):
        for route, person in self.routes():
            with self.subTest(route=route):
                response = self.get_detail(route, person)
                self.assertTemplateUsed(response, "r1/admin_people_detail_base.html")
                head = response.content.decode().split("</head>", 1)[0]
                self.assertEqual(head.count(static("css/r1_tokens.css")), 1)
                self.assertContains(response, static("css/r1_admin_people_details.css"), count=1)
                self.assertContains(response, 'class="r1-ui r1-people-detail ')
                self.assertNotContains(response, static("css/r1_shell.css"))
                self.assertContains(response, '<div class="app-shell" data-admin-theme>')

    def test_existing_navigation_and_global_header_stay_unchanged(self):
        for route, person in self.routes():
            with self.subTest(route=route):
                response = self.get_detail(route, person)
                navigation = render_to_string("core/partials/admin_navigation_links.html",
                                              {"request": response.wsgi_request})
                self.assertContains(response, navigation, count=2, html=False)
                self.assertContains(response, 'class="user-label"')
                self.assertContains(response, 'class="button secondary topbar-logout"')
                self.assertContains(response, static("js/admin_nav.js"), count=1)
                self.assertNotContains(response, "r1-account-name")

    def test_participant_has_compact_original_three_checks(self):
        response = self.get_detail("participant_detail", self.person)
        self.assertContains(response, 'id="record-checks"')
        values = [a["data-existing-result"] for _, a in DetailElements(response.content.decode()).tags
                  if "data-existing-result" in a]
        self.assertEqual(values, [str(x["is_ready"]).lower() for x in response.context["readiness_items"]])
        self.assertEqual(len(values), 3)
        self.assertNotContains(response, 'id="record-checks" open')
        self.assertContains(response, "3 checks recorded")

    def test_participant_unmet_checks_open_without_new_date_rules(self):
        response = self.get_detail("participant_detail", self.unassigned)
        self.assertContains(response, 'id="record-checks" open')
        self.person.plan_start_date, self.person.plan_end_date = date(2020, 1, 1), date(2020, 2, 1)
        self.person.save()
        response = self.get_detail("participant_detail", self.person)
        self.assertTrue(response.context["readiness_items"][1]["is_ready"])
        self.assertNotContains(response, "Expired")

    def test_participant_profile_notes_and_original_relationship_forms_remain(self):
        response = self.get_detail("participant_detail", self.person)
        for label in ("Preferred name", "Date of birth", "Phone", "Email", "Address", "Management type",
                      "Plan period", "Plan manager", "Support coordinator", "Worker visible notes",
                      "Address access instructions", "Risk/safety notes", "Internal notes"):
            self.assertContains(response, "<dt>" + label + "</dt>", html=True)
        for value in (self.person.worker_visible_notes, self.person.internal_notes,
                      self.person.address_access_instructions, self.person.risk_safety_notes):
            self.assertContains(response, value)
        self.assertContains(response, 'id="assigned-workers"')
        self.assertContains(response, 'name="end_date"')
        assignment = self.person.worker_assignments.get()
        self.assertContains(response, reverse("assignment_end", args=[assignment.pk]))
        self.assertContains(response, reverse("participant_document_files", args=[self.person.pk]))
        self.assertContains(response, "data-document-upload-open")

    def test_participant_assignment_and_shift_entries_are_not_duplicated(self):
        response = self.get_detail("participant_detail", self.person)
        self.assertContains(response, reverse("participant_assign_worker", args=[self.person.pk]), count=1)
        self.assertContains(response, reverse("shift_create") + "?participant=" + str(self.person.pk), count=1)
        self.assertContains(response, "Add assignment")
        empty = self.get_detail("participant_detail", self.unassigned)
        self.assertContains(empty, "Assign Worker")
        self.assertContains(empty, "No workers assigned.")

    def test_archive_restore_keep_original_direct_post_buttons_and_conditions(self):
        for status, route, label, absent in (("active", "participant_archive", "Archive", "Restore"),
                                             ("archived", "participant_restore", "Restore", "Archive")):
            with self.subTest(status=status):
                self.person.status = status
                self.person.save()
                response = self.get_detail("participant_detail", self.person)
                self.assertContains(response, reverse(route, args=[self.person.pk]))
                self.assertContains(response, ">" + label + "</button>")
                self.assertNotContains(response, ">" + absent + "</button>")
                self.assertNotContains(response, "data-more-toggle")

    def test_worker_contact_and_login_are_separate_preserved_groups(self):
        response = self.get_detail("worker_detail", self.worker)
        self.assertContains(response, "worker-contact-fields")
        self.assertContains(response, "worker-login-fields")
        html = response.content.decode()
        self.assertLess(html.index("<dt>Email</dt>"), html.index("<dt>Phone</dt>"))
        self.assertLess(html.index("<dt>Phone</dt>"), html.index("<dt>Address</dt>"))
        self.assertLess(html.index("worker-login-fields"), html.index("Reset Password"))
        self.assertContains(response, self.worker.user.username)
        self.assertContains(response, reverse("worker_reset_password", args=[self.worker.pk]), count=1)

    def test_worker_keeps_four_checks_and_document_status_independent(self):
        Document.objects.create(title="Fictional approved police PDF", category="compliance", worker=self.worker,
                                required_document_type="police_check", review_status="approved",
                                expiry_date=date(2027, 10, 12), file="fictional-unused.pdf", uploaded_by=self.admin)
        response = self.get_detail("worker_detail", self.worker)
        values = [a["data-existing-result"] for _, a in DetailElements(response.content.decode()).tags
                  if "data-existing-result" in a]
        self.assertEqual(values, [str(x["is_ready"]).lower() for x in response.context["readiness_items"]])
        self.assertEqual(len(values), 4)
        self.assertFalse(response.context["readiness_items"][1]["is_ready"])
        self.assertContains(response, "Approved")
        self.assertContains(response, "12/10/2027")
        self.assertNotContains(response, "worker-record-status")

    def test_worker_fourth_check_alone_can_open_summary(self):
        self.worker.police_check_status = "current"
        self.worker.wwcc_status = "current"
        self.worker.save()
        self.worker.participant_assignments.all().delete()
        response = self.get_detail("worker_detail", self.worker)
        self.assertContains(response, 'id="record-checks" open')
        values = [a["data-existing-result"] for _, a in DetailElements(response.content.decode()).tags
                  if "data-existing-result" in a]
        self.assertEqual(values, ["true", "true", "true", "false"])
        self.assertContains(response, "Needs active participant assignment")

    def test_worker_all_four_existing_checks_can_collapse(self):
        self.worker.police_check_status = "current"
        self.worker.wwcc_status = "current"
        self.worker.save()
        response = self.get_detail("worker_detail", self.worker)
        self.assertContains(response, "4 checks recorded")
        self.assertNotContains(response, 'id="record-checks" open')

    def test_worker_has_balanced_middle_full_tables_and_no_duplicate_person_list(self):
        response = self.get_detail("worker_detail", self.worker)
        for label in ("worker-middle", "worker-contact", "worker-employment", "compliance-documents", "assigned-participants"):
            self.assertContains(response, label)
        self.assertContains(response, "Assigned Participants")
        self.assertContains(response, "Recent Service Logs")
        self.assertNotContains(response, "Current participants")
        self.assertContains(response, reverse("shift_create") + "?worker=" + str(self.worker.pk), count=1)
        self.assertContains(response, reverse("worker_edit", args=[self.worker.pk]), count=1)
        for value in ("Police Check", "NDIS Worker Screening Check", "First Aid Certificate", "CPR Certificate",
                      "Working With Children Check", "Driver Licence", "All worker files"):
            self.assertContains(response, value)

    def test_coordinator_keeps_six_fields_full_notes_and_single_assignment_entry(self):
        response = self.get_detail("coordinator_detail", self.coordinator)
        for value in ("sc-information", "sc-contact-fields", "sc-account-fields", "sc-notes-fields", "Participant Assignments"):
            self.assertContains(response, value)
        for label in ("Email", "Login username", "Phone", "Status", "Login enabled", "Notes"):
            self.assertContains(response, "<dt>" + label + "</dt>", html=True)
        self.assertContains(response, self.coordinator.notes)
        self.assertContains(response, reverse("coordinator_assign_participant", args=[self.coordinator.pk]), count=1)
        self.assertContains(response, reverse("coordinator_reset_password", args=[self.coordinator.pk]), count=1)
        for value in ("Current participants", "Record checks", "Archive", "Create Shift", "View all files"):
            self.assertNotContains(response, value)

    def test_detail_tables_have_original_mobile_field_labels(self):
        for route, person, labels in (("participant_detail", self.person, ["Worker", "Start", "End", "Status", "Notes", "Actions"]),
                                      ("worker_detail", self.worker, ["Participant", "Start", "End", "Status", "Document", "Expiry", "Actions"]),
                                      ("coordinator_detail", self.coordinator, ["Participant", "Start", "End", "Status", "Notes"])):
            with self.subTest(route=route):
                response = self.get_detail(route, person)
                for label in labels:
                    self.assertContains(response, 'data-label="' + label + '"')

    def test_non_admin_roles_still_cannot_open_details(self):
        for user in self.other_users:
            self.client.force_login(user)
            for route, person in self.routes():
                with self.subTest(user=user.username, route=route):
                    self.assertEqual(self.client.get(reverse(route, args=[person.pk])).status_code, 403)

    def test_unrelated_list_and_form_routes_do_not_load_detail_css(self):
        for route in ("participant_list", "worker_list", "coordinator_list", "participant_create", "worker_create", "coordinator_create"):
            with self.subTest(route=route):
                response = self.client.get(reverse(route))
                self.assertEqual(response.status_code, 200)
                self.assertNotContains(response, static("css/r1_admin_people_details.css"))

    def test_content_css_keeps_grid_alignment_and_never_targets_navigation(self):
        path = Path(settings.BASE_DIR) / "static/css/r1_admin_people_details.css"
        self.assertTrue(path.is_file())
        css = path.read_text()
        for value in ('"contact compliance" "employment compliance"', "worker-contact-fields", "worker-login-fields",
                      "width: 25%", "text-align: center", "text-align: left", "@media(max-width: 760px)"):
            self.assertIn(value, css)
        for value in (".sidebar", ".admin-mobile", ".topbar", ".r1-account", ".sidebar-link"):
            self.assertNotIn(value, css)
