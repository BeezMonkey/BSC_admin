from django.test import TestCase, override_settings
from django.test.html import parse_html
from django.urls import reverse

from core import tests_r1_shell
from core.tests_r1_worker_navigation import elements
from scheduling.models import Shift
from service_logs.models import ServiceLog


@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    },
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ADMIN_NOTIFICATION_EMAILS=[],
)
class R1HomeRevisionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        tests_r1_shell.R1ShellIsolationTests.setUpTestData.__func__(cls)

    def setUp(self):
        self.client.force_login(self.worker_user)

    def nodes(self, tree, css):
        return [node for node in elements(tree)
                if css in dict(node.attributes).get("class", "").split()]

    def home(self):
        response = self.client.get(reverse("worker_dashboard"))
        self.assertEqual(response.status_code, 200)
        return response, parse_html(response.content.decode())

    def test_desktop_titles_share_count_heading_without_changing_mobile_labels(self):
        response, tree = self.home()
        cards = self.nodes(tree, "action-summary-item")
        for card, title, field, query in zip(cards,
                ("Needs attention", "Ready for log", "Completed"),
                ("needs_attention_count", "ready_for_log_count", "completed_shift_count"),
                ("needs_attention", "upcoming", "completed")):
            with self.subTest(title=title):
                self.assertEqual(dict(card.attributes)["href"],
                                 reverse("worker_shift_list") + "?view=" + query)
                heading = [node for node in elements(card) if node.name == "strong"][0]
                self.assertIn(str(response.context[field]), str(heading))
                desktop = self.nodes(heading, "r1-desktop-summary-title")
                self.assertEqual(len(desktop), 1)
                self.assertIn(title, str(desktop[0]))
                self.assertEqual(len(self.nodes(card, "r1-summary-label")), 1)
        self.assertEqual(len(cards), 3)
        self.assertEqual(len(self.nodes(tree, "r1-mobile-summary-title")), 1)
        self.assertContains(response, "Go to My Shifts", count=1)

    def test_single_module_is_home_grid_child_after_quick_access_for_mobile_order(self):
        response, tree = self.home()
        home = self.nodes(tree, "worker-dashboard-page")[0]
        workspace = self.nodes(tree, "r1-home-workspace")[0]
        module = self.nodes(tree, "worker-unscheduled-service-card")
        self.assertEqual(len(module), 1)
        self.assertIn(module[0], home.children)
        self.assertNotIn(module[0], list(elements(workspace)))
        self.assertLess(home.children.index(workspace), home.children.index(module[0]))
        self.assertContains(response, reverse("worker_unscheduled_service_log_create"), count=1)

    def test_quick_access_keeps_all_four_ordered_existing_routes(self):
        response, tree = self.home()
        quick = self.nodes(tree, "r1-quick-access")[0]
        links = [dict(node.attributes)["href"] for node in elements(quick)
                 if node.name == "a"]
        self.assertEqual(links, [reverse(name) for name in
                         ("worker_shift_list", "worker_log_list", "worker_document_list", "worker_profile")])
        for description in ("View your scheduled work", "Check your service records",
                            "Manage compliance documents", "View your worker details"):
            self.assertContains(response, description)

    def test_empty_summary_keeps_original_condition_and_independent_unscheduled_entry(self):
        ServiceLog.objects.filter(worker=self.worker).delete()
        Shift.objects.filter(worker=self.worker).delete()
        response, tree = self.home()
        self.assertFalse(response.context["has_shift_actions"])
        self.assertContains(response, "No shift actions need attention.")
        self.assertEqual(self.nodes(tree, "action-summary-item"), [])
        self.assertContains(response, reverse("worker_unscheduled_service_log_create"), count=1)

    def test_names_remain_dynamic_escaped_and_other_unscheduled_entry_is_unchanged(self):
        self.worker.first_name = "Long<Worker>"
        self.worker.last_name = "Name" * 18
        self.worker.save(update_fields=["first_name", "last_name"])
        response, _ = self.home()
        self.assertContains(response, "Long&lt;Worker&gt;")
        self.assertContains(response, self.worker.last_name)
        logs = self.client.get(reverse("worker_log_list"))
        self.assertContains(logs, "worker-log-list-header")
        self.assertContains(logs, reverse("worker_unscheduled_service_log_create"), count=1)
        self.assertNotContains(logs, "worker-dashboard-page")
