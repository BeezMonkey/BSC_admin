from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from html import escape
from urllib.parse import parse_qs, urlsplit

from django.conf import settings
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from accounts.models import UserProfile
from coordinators.models import ParticipantCoordinatorAssignment, SupportCoordinator
from participants.models import Participant, ParticipantWorkerAssignment
from workers.models import SupportWorker


class SelectFields(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.fields = {}
        self.links = []
        self.current = None
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and "href" in attrs:
            self.links.append(attrs["href"])
        if tag == "select":
            self.current = attrs["name"]
            self.fields[self.current] = []
        elif tag == "option" and self.current:
            self.fields[self.current].append((attrs.get("value", ""), "selected" in attrs))

    def handle_endtag(self, tag):
        if tag == "select":
            self.current = None


@override_settings(STORAGES={
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
})
class R1AdminPeopleListTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        cls.admin = users.objects.create_user(username="b091-admin")
        UserProfile.objects.create(user=cls.admin, role="admin")
        cls.other_users = []
        for role in ("support_worker", "support_coordinator", "accountant"):
            user = users.objects.create_user(username="b091-" + role)
            UserProfile.objects.create(user=user, role=role)
            cls.other_users.append(user)
        cls.worker = SupportWorker.objects.create(
            user=cls.other_users[0], first_name="Amelia", last_name="Reed",
            email="b091-worker@example.invalid", phone="0491 570 006",
        )
        archived_user = users.objects.create_user(username="b091-archived-worker")
        cls.archived_worker = SupportWorker.objects.create(
            user=archived_user, first_name="Zoe", last_name="West",
            email="b091-archived@example.invalid", status="inactive", employment_type="subcontractor",
        )
        cls.coordinator = SupportCoordinator.objects.create(
            user=cls.other_users[1], first_name="Jordan", last_name="Ellis",
            email="b091-sc@example.invalid", phone="0491 570 007",
        )
        inactive_user = users.objects.create_user(username="b091-inactive-sc")
        cls.inactive_sc = SupportCoordinator.objects.create(
            user=inactive_user, first_name="Casey", last_name="Morgan",
            email="b091-inactive-sc@example.invalid", status="inactive",
        )
        cls.person = Participant.objects.create(
            first_name="Mia", last_name="Parker", ndis_number="QA-B091-001",
            email="b091-participant@example.invalid", phone="0491 570 008",
            management_type="plan_managed", plan_start_date=date(2026, 8, 1),
            plan_end_date=date(2027, 7, 31), support_coordinator_name="Jordan Ellis",
        )
        cls.unassigned = Participant.objects.create(first_name="Zoe", last_name="West", ndis_number="QA-B091-002")
        Participant.objects.create(first_name="Ava", last_name="Chen", status="inactive", ndis_number="QA-B091-003")
        Participant.objects.create(first_name="Noah", last_name="Lee", status="archived", ndis_number="QA-B091-004")
        ParticipantWorkerAssignment.objects.create(participant=cls.person, worker=cls.worker, start_date=date(2026, 8, 1))
        ParticipantCoordinatorAssignment.objects.create(participant=cls.person, coordinator=cls.coordinator, start_date=date(2026, 8, 1))

    def setUp(self):
        self.client.force_login(self.admin)

    def test_only_three_lists_load_the_route_local_shell_in_order(self):
        for route, crumb in (("participant_list", "Operations / Participants"),
                             ("worker_list", "Operations / Support Workers"),
                             ("coordinator_list", "Coordination / Support Coordinators")):
            with self.subTest(route=route):
                response = self.client.get(reverse(route))
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, "r1/admin_people_list_base.html")
                self.assertContains(response, "r1-ui r1-admin r1-admin-people-lists", count=1)
                self.assertContains(response, crumb, count=1)
                html = response.content.decode()
                paths = [static("css/" + path) for path in ("admin.css", "r1_tokens.css", "r1_shell.css", "r1_admin_people_lists.css")]
                self.assertEqual([html.index(path) for path in paths], sorted(html.index(path) for path in paths))
                for path in paths:
                    self.assertContains(response, path, count=1)

    def test_participant_overview_counts_and_original_filter_links_remain(self):
        response = self.client.get(reverse("participant_list"))
        self.assertEqual([item["count_label"] for item in response.context["participant_overview"]],
                         ["4 records", "2 active", "1 without workers", "1 inactive", "1 archived"])
        self.assertContains(response, reverse("participant_list") + "?status=active&amp;assignment=unassigned")
        for value in ("Mia Parker", "QA-B091-001", "b091-participant@example.invalid", "Plan managed", "01/08/2026", "31/07/2027", "1 active worker", "Jordan Ellis"):
            self.assertContains(response, value)

    def test_participant_filters_keep_original_native_names_values_and_results(self):
        response = self.client.get(reverse("participant_list"), {"status": "active", "assignment": "unassigned", "q": "Zoe"})
        self.assertEqual([p.pk for p in response.context["participants"]], [self.unassigned.pk])
        fields = SelectFields(response.content.decode()).fields
        self.assertEqual(fields["status"], [("", False), ("active", True), ("inactive", False), ("archived", False)])
        self.assertEqual(fields["assignment"], [("", False), ("assigned", False), ("unassigned", True)])
        self.assertContains(response, 'name="q" value="Zoe"')
        self.assertContains(response, 'method="get"')

    def test_workers_scope_employment_type_and_selected_option_remain(self):
        response = self.client.get(reverse("worker_list"), {"scope": "archived", "employment_type": "subcontractor"})
        self.assertEqual([w.pk for w in response.context["workers"]], [self.archived_worker.pk])
        self.assertContains(response, 'name="scope" value="archived"')
        self.assertEqual(SelectFields(response.content.decode()).fields["employment_type"], [("", False), ("employee", False), ("subcontractor", True)])
        for scope in ("active", "archived", "all"):
            self.assertContains(response, reverse("worker_list") + "?scope=" + scope)

    def test_coordinator_status_and_active_assignment_count_remain(self):
        response = self.client.get(reverse("coordinator_list"))
        self.assertEqual({c.pk: c.active_assignment_count for c in response.context["coordinators"]}, {self.coordinator.pk: 1, self.inactive_sc.pk: 0})
        inactive = self.client.get(reverse("coordinator_list"), {"status": "inactive"})
        self.assertEqual([c.pk for c in inactive.context["coordinators"]], [self.inactive_sc.pk])
        self.assertEqual(SelectFields(inactive.content.decode()).fields["status"], [("", False), ("active", False), ("inactive", True)])

    def test_all_table_columns_have_mobile_labels_and_original_sort_anchors(self):
        expected = {
            "participant_list": (["Participant", "Contact", "Status", "Plan", "Assigned Workers", "Coordinator", "Actions"], ["name", "status"]),
            "worker_list": (["Name", "Email", "Phone", "Type", "Status", "Actions"], ["name", "employment_type", "status"]),
            "coordinator_list": (["Name", "Email", "Phone", "Status", "Active Assignments", "Actions"], ["name", "status"]),
        }
        for route, (labels, sorts) in expected.items():
            with self.subTest(route=route):
                response = self.client.get(reverse(route))
                for label in labels:
                    self.assertContains(response, 'data-label="' + label + '"')
                for sort in sorts:
                    self.assertContains(response, escape(response.context["sorting"]["links"][sort], quote=True))

    def test_original_add_view_edit_return_and_post_logout_targets_remain(self):
        for route, prefix, obj, create in (
            ("participant_list", "participant", self.person, "participant_create"),
            ("worker_list", "worker", self.worker, "worker_create"),
            ("coordinator_list", "coordinator", self.coordinator, "coordinator_create"),
        ):
            with self.subTest(route=route):
                url = reverse(route)
                response = self.client.get(url)
                links = [urlsplit(href) for href in SelectFields(response.content.decode()).links]
                for target in [reverse(create), reverse(prefix + "_detail", args=[obj.pk]), reverse(prefix + "_edit", args=[obj.pk])]:
                    self.assertTrue(any(link.path == target and parse_qs(link.query).get("next") == [url] for link in links), target)
                self.assertContains(response, 'method="post" action="' + reverse("logout") + '"', count=2)
                self.assertContains(response, 'name="csrfmiddlewaretoken"', count=2)
                self.assertContains(response, 'aria-controls="admin-mobile-drawer"')

    def test_sort_and_pagination_keep_original_query_parameters(self):
        for i in range(22):
            Participant.objects.create(first_name="Fixture", last_name=f"Extra{i:02}", ndis_number=f"QA-B091-EXTRA-{i:02}")
        response = self.client.get(reverse("participant_list"), {"q": "Fixture", "sort": "name", "direction": "desc", "page": 2})
        self.assertEqual([p.last_name for p in response.context["participants"]], ["Extra01", "Extra00"])
        self.assertContains(response, "q=Fixture&amp;sort=name&amp;direction=desc&amp;page=1")
        self.assertContains(response, "q=Fixture&amp;sort=name&amp;direction=asc")

    def test_no_matching_records_keeps_each_original_empty_state_and_reset(self):
        for route, noun in (("participant_list", "participants"), ("worker_list", "support workers"), ("coordinator_list", "support coordinators")):
            with self.subTest(route=route):
                response = self.client.get(reverse(route), {"q": "FICTIONAL-NO-MATCH"})
                self.assertContains(response, "No " + noun + " match the current filters.")
                self.assertContains(response, 'href="' + reverse(route) + '">Clear filters</a>')

    def test_other_roles_and_anonymous_users_keep_original_access_boundaries(self):
        for user in self.other_users:
            self.client.force_login(user)
            for route in ("participant_list", "worker_list", "coordinator_list"):
                with self.subTest(user=user.username, route=route):
                    self.assertEqual(self.client.get(reverse(route)).status_code, 403)
        self.client.logout()
        for route in ("participant_list", "worker_list", "coordinator_list"):
            self.assertEqual(self.client.get(reverse(route)).status_code, 302)

    def test_unrelated_details_forms_and_base_shell_do_not_load_people_assets(self):
        for url in [reverse("participant_detail", args=[self.person.pk]), reverse("worker_detail", args=[self.worker.pk]), reverse("coordinator_detail", args=[self.coordinator.pk]), reverse("participant_create"), reverse("worker_create"), reverse("coordinator_create"), reverse("admin_dashboard")]:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertNotContains(response, "r1_admin_people_lists.css")
                self.assertNotContains(response, "r1-admin-people-lists")
        request = RequestFactory().get("/")
        request.user = self.admin
        self.assertNotIn("r1_admin_people_lists.css", render_to_string("admin_base.html", request=request))

    def test_local_css_retains_accepted_card_controls_picker_and_mobile_sort_rules(self):
        css_path = Path(settings.BASE_DIR) / "static/css/r1_admin_people_lists.css"
        self.assertTrue(css_path.is_file())
        css = css_path.read_text(encoding="utf-8")
        for rule in ["min-height: 96px", "min-height: 88px", "gap: 4px", "padding: 12px", "height: 40px", "height: 44px", "appearance: base-select", "select::picker(select)", "select option", "th:has(.sort-link)", "content:attr(data-label)"]:
            self.assertIn(rule, css)
        self.assertNotIn(".r1-admin-people-proposal", css)
        self.assertNotIn("!important", css)

    def test_mobile_select_matches_accepted_native_invoice_fallback(self):
        css = (Path(settings.BASE_DIR) / "static/css/r1_admin_people_lists.css").read_text(encoding="utf-8")
        self.assertIn("/* Match accepted native Invoice select fallback on touch screens. */", css)
        fallback = css.split("/* Match accepted native Invoice select fallback on touch screens. */", 1)[1]
        self.assertIn("@media (max-width: 760px)", fallback)
        self.assertIn("appearance: auto", fallback)
        self.assertIn("line-height: normal", fallback)
        self.assertIn("padding: 10px 8px", fallback)
        self.assertIn("label:has(select)::after { display: none; }", fallback)

    def test_actions_reserve_space_and_prevent_desktop_and_mobile_button_wrapping(self):
        css = (Path(settings.BASE_DIR) / "static/css/r1_admin_people_lists.css").read_text(encoding="utf-8")
        marker = "/* Keep original View/Edit controls on one row at every list breakpoint. */"
        self.assertIn(marker, css)
        actions = css.split(marker, 1)[1]
        self.assertIn(".table-card td.actions { white-space: nowrap; }", actions)
        self.assertIn(".table-card td.actions .button { flex: 0 0 auto; white-space: nowrap; }", actions)
        self.assertIn("@media (min-width: 761px)", actions)
        self.assertIn("width: 168px", actions)
        self.assertIn("@media (max-width: 760px)", actions)
        self.assertIn(".table-card td.actions { flex-wrap: nowrap; }", actions)
