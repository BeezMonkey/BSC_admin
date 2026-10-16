from datetime import date, time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.template.loader import render_to_string
from django.test import RequestFactory, TestCase, override_settings
from django.templatetags.static import static
from django.urls import reverse

from accounts.models import UserProfile
from participants.models import Participant, ParticipantWorkerAssignment
from scheduling.models import Shift, SupportItem
from service_logs.models import ServiceLog
from workers.models import SupportWorker


@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    },
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class R1ShellIsolationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_user(username="b01-admin")
        UserProfile.objects.create(user=cls.admin, role=UserProfile.Role.ADMIN)
        cls.worker_user = get_user_model().objects.create_user(username="b01-worker")
        UserProfile.objects.create(
            user=cls.worker_user, role=UserProfile.Role.SUPPORT_WORKER, is_active_worker=True
        )
        cls.worker = SupportWorker.objects.create(
            user=cls.worker_user, first_name="B01", last_name="Demo Worker",
            email="b01-worker@example.invalid", status=SupportWorker.Status.ACTIVE,
        )
        cls.participant = Participant.objects.create(
            first_name="B01", last_name="Demo Participant", status=Participant.Status.ACTIVE
        )
        ParticipantWorkerAssignment.objects.create(
            participant=cls.participant, worker=cls.worker, start_date=date(2026, 1, 1)
        )
        item = SupportItem.objects.create(
            item_number="B01-TEST", name="B01 fictional support item",
            unit=SupportItem.Unit.HOUR, price_limit=Decimal("73.58"), is_active=True,
        )
        shift_fields = dict(
            participant=cls.participant, worker=cls.worker, service_date=date(2026, 10, 14),
            start_time=time(9), end_time=time(12), planned_hours=Decimal("3.00"),
            support_item=item, service_type=Shift.ServiceType.PERSONAL_CARE,
            created_by=cls.admin,
        )
        cls.shift = Shift.objects.create(**shift_fields, status=Shift.Status.CONFIRMED)
        completed = Shift.objects.create(**shift_fields, status=Shift.Status.COMPLETED)
        cls.log = ServiceLog.objects.create_from_shift(
            completed, actual_start_time=time(9), actual_end_time=time(12),
            actual_hours=Decimal("3.00"), kilometres=Decimal("25.00"),
            case_notes="Fictional B01 notes", worker_notes="Fictional worker notes",
        )

    def assert_r1_resources(self, response, shell):
        self.assertContains(response, f"r1-ui r1-{shell}")
        html = response.content.decode()
        for path in ("css/r1_tokens.css", "css/r1_shell.css"):
            self.assertContains(response, static(path), count=1)
        self.assertLess(html.index(static("css/r1_tokens.css")), html.index(static("css/r1_shell.css")))

    def test_rostered_log_opts_in_without_changing_form_contract(self):
        self.client.force_login(self.worker_user)
        response = self.client.get(reverse("worker_service_log_create", args=[self.shift.pk]))
        self.assert_r1_resources(response, "worker")
        self.assertContains(response, 'method="post" enctype="multipart/form-data"')
        for name in ("actual_start_time", "actual_end_time", "break_minutes", "kilometres", "case_notes", "worker_notes", "attachments", "csrfmiddlewaretoken"):
            self.assertContains(response, f'name="{name}"')
        self.assertContains(response, f'href="{reverse("worker_shift_detail", args=[self.shift.pk])}">Cancel</a>')
        self.assertContains(response, 'data-max-files="3"')
        self.assertContains(response, 'data-max-size="5242880"')

    def test_unscheduled_log_opts_in_and_retains_original_cancel_target(self):
        self.client.force_login(self.worker_user)
        response = self.client.get(reverse("worker_unscheduled_service_log_create"))
        self.assert_r1_resources(response, "worker")
        for name in ("participant", "service_date", "support_item", "service_type", "unscheduled_reason"):
            self.assertContains(response, f'name="{name}"')
        self.assertContains(response, f'href="{reverse("worker_log_list")}">Cancel</a>')

    def test_admin_detail_opts_in_after_its_existing_styles(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("service_log_detail", args=[self.log.pk]))
        self.assert_r1_resources(response, "admin")
        html = response.content.decode()
        self.assertLess(html.index(static("css/invoice_billing.css")), html.index(static("css/r1_tokens.css")))
        for action in ("service_log_approve", "service_log_reject"):
            self.assertContains(response, f'action="{reverse(action, args=[self.log.pk])}"')
        self.assertContains(response, reverse("service_log_pdf", args=[self.log.pk]))
        self.assertContains(response, "Fictional B01 notes")

    def test_review_actions_still_follow_existing_status(self):
        self.client.force_login(self.admin)
        self.log.status = ServiceLog.Status.APPROVED
        self.log.save(update_fields=["status"])
        response = self.client.get(reverse("service_log_detail", args=[self.log.pk]))
        self.assert_r1_resources(response, "admin")
        self.assertNotContains(response, reverse("service_log_approve", args=[self.log.pk]))
        self.assertNotContains(response, reverse("service_log_reject", args=[self.log.pk]))

    def test_worker_shell_retains_four_bottom_destinations_and_post_logout(self):
        self.client.force_login(self.worker_user)
        response = self.client.get(reverse("worker_unscheduled_service_log_create"))
        self.assertContains(response, 'aria-label="Worker quick navigation"')
        self.assertContains(response, 'class="worker-bottom-nav-link', count=4)
        self.assertContains(response, 'aria-controls="worker-mobile-drawer"')
        self.assertContains(response, f'method="post" action="{reverse("logout")}"', count=2)
        self.assertContains(response, static("js/worker_nav.js"))

    def test_base_shells_are_default_off_including_sc_and_login(self):
        request = RequestFactory().get("/")
        request.user = AnonymousUser()
        for template in ("admin_base.html", "worker_base.html", "coordinator_base.html", "accounts/login.html"):
            with self.subTest(template=template):
                html = render_to_string(template, {"request": request})
                self.assertNotIn("r1_tokens.css", html)
                self.assertNotIn("r1_shell.css", html)
                self.assertNotIn("r1-ui", html)

    def test_navigation_pages_opt_in_but_other_worker_and_admin_pages_do_not(self):
        self.client.force_login(self.worker_user)
        navigation_urls = [reverse(name) for name in
                           ("worker_dashboard", "worker_log_list", "worker_shift_list")]
        navigation_urls += [reverse("worker_shift_detail", args=[self.shift.pk]),
                            reverse("worker_service_log_detail", args=[self.log.pk])]
        for url in navigation_urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assert_r1_resources(response, "worker")
                self.assertContains(response, "r1_worker_navigation.css", count=1)
        for user, routes in (
            (self.worker_user, ("worker_document_list",)),
            (self.admin, ("admin_dashboard", "roster_planner", "invoice_placeholder")),
        ):
            self.client.force_login(user)
            for route in routes:
                with self.subTest(route=route):
                    response = self.client.get(reverse(route))
                    self.assertEqual(response.status_code, 200)
                    self.assertNotContains(response, "r1_shell.css")
                    self.assertNotContains(response, "r1-ui")

    def test_profile_opts_into_independent_support_shell(self):
        self.client.force_login(self.worker_user)
        response = self.client.get(reverse("worker_profile"))
        self.assert_r1_resources(response, "worker")
        self.assertTemplateUsed(response, "r1/worker_support_base.html")
        self.assertContains(response, "r1_worker_support.css", count=1)
        self.assertNotContains(response, "r1_worker_navigation.css")
        self.assertNotContains(response, "r1_worker_logs.css")

    def test_pilot_does_not_grant_worker_admin_detail_access(self):
        self.client.force_login(self.worker_user)
        response = self.client.get(reverse("service_log_detail", args=[self.log.pk]))
        self.assertEqual(response.status_code, 403)
