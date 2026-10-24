from datetime import date
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.template.defaultfilters import truncatechars
from django.test import TestCase, override_settings
from django.test.html import parse_html
from django.templatetags.static import static
from django.urls import reverse

from core import tests_r1_shell
from documents.models import Document
from scheduling.models import Shift
from service_logs.models import ServiceLog
from workers.models import SupportWorker


def elements(node):
    if not isinstance(node, str):
        yield node
        for child in node.children:
            yield from elements(child)


@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    },
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ADMIN_NOTIFICATION_EMAILS=[],
)
class R1WorkerNavigationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        tests_r1_shell.R1ShellIsolationTests.setUpTestData.__func__(cls)

    def setUp(self):
        self.client.force_login(self.worker_user)

    def routes(self):
        return [reverse(name) for name in
                ("worker_dashboard", "worker_shift_list", "worker_log_list")] + [
                    reverse("worker_shift_detail", args=[self.shift.pk]),
                    reverse("worker_service_log_detail", args=[self.log.pk]),
                ]

    def page(self, response):
        self.assertEqual(response.status_code, 200)
        return parse_html(response.content.decode())

    def nodes(self, tree, name=None, css=None):
        return [node for node in elements(tree)
                if (name is None or node.name == name)
                and (css is None or css in dict(node.attributes).get("class", "").split())]

    def test_five_pages_load_scoped_styles_once_after_existing_foundations(self):
        for url in self.routes():
            with self.subTest(url=url):
                response = self.client.get(url)
                tree = self.page(response)
                styles = [dict(node.attributes).get("href") for node in self.nodes(tree, "link")]
                expected = [static("css/" + name) for name in
                            ("r1_tokens.css", "r1_shell.css", "r1_worker_navigation.css")]
                for path in expected:
                    self.assertEqual(styles.count(path), 1)
                self.assertEqual(sorted(expected, key=styles.index), expected)
                self.assertContains(response, "r1-worker-navigation")
                self.assertNotContains(response, "r1_worker_logs.css")

    def test_other_pages_do_not_load_navigation_styles(self):
        response = self.client.get(reverse("worker_document_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "r1_worker_navigation.css", count=1)
        for user, urls in (
            (self.worker_user, [reverse(name) for name in
             ("worker_profile", "worker_unscheduled_service_log_create")]
             + [reverse("worker_service_log_create", args=[self.shift.pk]),
                reverse("worker_participant_cancellation_create", args=[self.shift.pk])]),
            (self.admin, [reverse(name) for name in
             ("admin_dashboard", "roster_planner", "invoice_placeholder", "service_log_list")]),
        ):
            self.client.force_login(user)
            for url in urls:
                with self.subTest(url=url):
                    response = self.client.get(url)
                    self.assertEqual(response.status_code, 200)
                    self.assertNotContains(response, "r1_worker_navigation.css")

    def test_shell_keeps_four_bottom_links_menu_profile_and_post_logout(self):
        for url in self.routes():
            with self.subTest(url=url):
                tree = self.page(self.client.get(url))
                bottom = self.nodes(tree, "nav", "worker-bottom-nav")[0]
                links = self.nodes(bottom, "a")
                self.assertEqual([dict(node.attributes)["href"] for node in links],
                                 [reverse(name) for name in ("worker_dashboard", "worker_shift_list",
                                  "worker_log_list", "worker_document_list")])
                self.assertEqual(sum(dict(node.attributes).get("aria-current") == "page"
                                     for node in links), 1)
                drawer = self.nodes(tree, "aside", "worker-mobile-drawer")[0]
                self.assertIn(reverse("worker_profile"), str(drawer))
                self.assertIn('aria-controls="worker-mobile-drawer"', str(tree))
                forms = [node for node in self.nodes(tree, "form")
                         if dict(node.attributes).get("action") == reverse("logout")]
                self.assertEqual(len(forms), 2)
                for form in forms:
                    self.assertEqual(dict(form.attributes)["method"], "post")
                    self.assertIn("csrfmiddlewaretoken", str(form))

    def test_lists_are_semantic_tables_with_headers_and_single_actions(self):
        for route, label in (("worker_shift_list", "My Shifts"), ("worker_log_list", "My Logs")):
            response = self.client.get(reverse(route))
            tree = self.page(response)
            tables = self.nodes(tree, "table", "r1-navigation-table")
            self.assertEqual(len(tables), 1)
            self.assertEqual(dict(tables[0].attributes)["aria-label"], label)
            headers = self.nodes(tables[0], "th")
            self.assertGreaterEqual(len(headers), 5)
            self.assertTrue(all(dict(node.attributes).get("scope") == "col" for node in headers))
        self.assertContains(self.client.get(reverse("worker_shift_list")),
                            reverse("worker_service_log_create", args=[self.shift.pk]), count=1)

    def test_shift_list_and_detail_keep_distinct_status_actions(self):
        for status in ("published", "confirmed", "completed", "cancellation_review", "cancelled"):
            with self.subTest(status=status):
                self.shift.status = status
                self.shift.save(update_fields=["status"])
                confirm = reverse("worker_shift_confirm", args=[self.shift.pk])
                complete = reverse("worker_service_log_create", args=[self.shift.pk])
                cancellation = reverse("worker_participant_cancellation_create", args=[self.shift.pk])
                for detail in (False, True):
                    response = self.client.get(reverse("worker_shift_detail", args=[self.shift.pk])
                                               if detail else reverse("worker_shift_list"))
                    tree = self.page(response)
                    html = response.content.decode()
                    self.assertEqual(html.count(confirm), int(status == "published"))
                    self.assertEqual(html.count(complete), int(status in
                                     (("published", "confirmed") if detail else ("confirmed",))))
                    self.assertEqual(html.count(cancellation), int(detail and status in
                                     ("published", "confirmed")))
                    if status == "published":
                        form = [node for node in self.nodes(tree, "form")
                                if dict(node.attributes).get("action") == confirm][0]
                        self.assertEqual(dict(form.attributes)["method"], "post")
                        self.assertIn("csrfmiddlewaretoken", str(form))
                    if detail and status == "cancellation_review":
                        self.assertContains(response, "Cancellation awaiting admin review")
                        self.assertContains(response, "No further action is needed for this shift.")
                    if detail and status == "completed":
                        self.assertNotContains(response, reverse("worker_service_log_detail", args=[self.log.pk]))

    def test_home_counts_and_links_keep_original_empty_condition(self):
        response = self.client.get(reverse("worker_dashboard"))
        for field in ("needs_attention_count", "ready_for_log_count", "completed_shift_count"):
            self.assertIn(str(response.context[field]), response.content.decode())
        for query in ("needs_attention", "upcoming", "completed"):
            self.assertContains(response, reverse("worker_shift_list") + "?view=" + query)
        for name in ("worker_shift_list", "worker_log_list", "worker_document_list",
                     "worker_profile", "worker_unscheduled_service_log_create"):
            self.assertContains(response, reverse(name))
        ServiceLog.objects.filter(worker=self.worker).delete()
        Shift.objects.filter(worker=self.worker).delete()
        response = self.client.get(reverse("worker_dashboard"))
        self.assertFalse(response.context["has_shift_actions"])
        self.assertContains(response, "No shift actions need attention.")
        self.assertNotContains(response, "?view=needs_attention")

    def test_cancellation_review_counts_and_status_based_upcoming_are_preserved(self):
        self.shift.status = "cancellation_review"
        self.shift.save(update_fields=["status"])
        home = self.client.get(reverse("worker_dashboard"))
        listing = self.client.get(reverse("worker_shift_list"))
        self.assertEqual(home.context["completed_shift_count"], 1)
        self.assertEqual(listing.context["completed_count"], 2)
        self.shift.status = "confirmed"
        self.shift.service_date = date(2000, 1, 1)
        self.shift.save(update_fields=["status", "service_date"])
        response = self.client.get(reverse("worker_shift_list"), {"view": "upcoming"})
        self.assertContains(response, "01/01/2000")
        self.assertEqual(response.context["upcoming_count"], 1)

    def test_filters_group_order_invalid_filter_and_empty_selected_group(self):
        response = self.client.get(reverse("worker_shift_list"), {"view": "invalid"})
        self.assertEqual(response.context["selected_view"], "all")
        tree = self.page(response)
        active = [node for node in self.nodes(tree, "a", "filter-active")]
        self.assertEqual(len(active), 1)
        self.assertEqual(dict(active[0].attributes)["aria-current"], "page")
        response = self.client.get(reverse("worker_shift_list"), {"view": "needs_attention"})
        self.assertNotContains(response, "No shifts found.")
        self.assertNotContains(response, reverse("worker_shift_detail", args=[self.shift.pk]))
        response = self.client.get(reverse("worker_shift_list"))
        self.assertLess(response.content.decode().index("Upcoming</h2>"),
                        response.content.decode().index("Completed</h2>"))

    def test_log_summary_truncation_all_statuses_and_unscheduled_source(self):
        self.log.case_notes = "Fictional case notes " * 12
        self.log.source = "unscheduled"
        for status, _ in ServiceLog.Status.choices:
            with self.subTest(status=status):
                self.log.status = status
                self.log.save(update_fields=["case_notes", "source", "status"])
                response = self.client.get(reverse("worker_log_list"))
                self.assertContains(response, truncatechars(self.log.case_notes, 80))
                self.assertNotContains(response, self.log.case_notes)
                self.assertContains(response, self.log.get_status_display())
                self.assertContains(response, "Unscheduled")
                self.assertContains(response, reverse("worker_service_log_detail", args=[self.log.pk]), count=1)

    def test_log_detail_keeps_every_original_value_notes_reasons_and_document_status(self):
        self.log.source = "unscheduled"
        self.log.unscheduled_reason = "Fictional urgent request"
        self.log.rejection_reason = "Fictional clarification required"
        self.log.case_notes = "Case notes " + "x" * 200 + "\nSecond line"
        self.log.worker_notes = "Worker notes " + "y" * 200
        self.log.save()
        document = Document.objects.create(title="Fictional attachment", file="fictional.pdf",
            original_filename="FictionalEvidence.pdf", service_log=self.log,
            uploaded_by=self.worker_user, review_status="pending_review", worker=self.worker)
        response = self.client.get(reverse("worker_service_log_detail", args=[self.log.pk]))
        for value in (self.log.case_notes, self.log.worker_notes, self.log.unscheduled_reason,
                      self.log.rejection_reason, self.log.get_source_display(),
                      str(self.log.actual_hours), str(self.log.kilometres),
                      "Actual time", "Actual hours", "Kilometres", "Date", "Status",
                      document.filename, document.get_review_status_display()):
            self.assertContains(response, value)
        self.assertContains(response, reverse("worker_document_detail", args=[document.pk]))

    def test_empty_markers_and_shift_fields_are_not_removed(self):
        self.shift.location = ""
        self.shift.instructions = "Long instruction " + "z" * 180
        self.shift.save(update_fields=["location", "instructions"])
        response = self.client.get(reverse("worker_shift_detail", args=[self.shift.pk]))
        for label in ("Date", "Time", "Status", "Source", "Address", "Instructions", "Service"):
            self.assertContains(response, label)
        self.assertContains(response, self.shift.instructions)
        self.assertContains(response, "<dd>-</dd>", html=True)
        self.log.worker_notes = ""
        self.log.rejection_reason = ""
        self.log.save(update_fields=["worker_notes", "rejection_reason"])
        response = self.client.get(reverse("worker_service_log_detail", args=[self.log.pk]))
        self.assertContains(response, "<dd>-</dd>", count=2, html=True)
        self.assertContains(response, "No attachments.")

    def test_navigation_icons_reference_existing_local_assets_and_are_decorative(self):
        for url in self.routes():
            tree = self.page(self.client.get(url))
            for node in self.nodes(tree, "img", "r1-icon"):
                attrs = dict(node.attributes)
                self.assertEqual(attrs["alt"], "")
                self.assertEqual(attrs["aria-hidden"], "true")
                prefix = static("img/r1/icons/")
                self.assertTrue(attrs["src"].startswith(prefix))
                self.assertTrue((Path(settings.BASE_DIR) / "static/img/r1/icons" /
                                 attrs["src"].removeprefix(prefix)).is_file())

    def test_other_worker_cannot_open_shift_or_log(self):
        other_user = get_user_model().objects.create_user(username="other-worker")
        other = SupportWorker.objects.create(user=other_user, first_name="Other", last_name="Worker",
            email="other@example.invalid", status=SupportWorker.Status.ACTIVE)
        self.shift.worker = other
        self.shift.save(update_fields=["worker"])
        self.log.worker = other
        self.log.save(update_fields=["worker"])
        for name, pk in (("worker_shift_detail", self.shift.pk),
                         ("worker_service_log_detail", self.log.pk)):
            self.assertEqual(self.client.get(reverse(name, args=[pk])).status_code, 404)
        self.assertNotContains(self.client.get(reverse("worker_shift_list")),
                               reverse("worker_shift_detail", args=[self.shift.pk]))
        self.assertNotContains(self.client.get(reverse("worker_log_list")),
                               reverse("worker_service_log_detail", args=[self.log.pk]))

    def test_shift_action_guidance_uses_approved_decorative_icon_only_when_actionable(self):
        for status in ("published", "confirmed", "completed", "cancellation_review"):
            with self.subTest(status=status):
                self.shift.status = status
                self.shift.save(update_fields=["status"])
                tree = self.page(self.client.get(reverse("worker_shift_detail", args=[self.shift.pk])))
                actions = self.nodes(tree, css="worker-detail-actions")[0]
                icons = self.nodes(actions, "img", "r1-icon")
                self.assertEqual(len(icons), int(status in ("published", "confirmed")))
                for icon in icons:
                    attrs = dict(icon.attributes)
                    self.assertEqual(attrs["src"], static("img/r1/icons/logs-active.svg"))
                    self.assertEqual(attrs["alt"], "")
                    self.assertEqual(attrs["aria-hidden"], "true")
