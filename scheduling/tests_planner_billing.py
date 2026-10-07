from datetime import date, time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import UserProfile
from invoices.models import Invoice, InvoiceLine
from participants.models import Participant
from scheduling.models import ParticipantCancellation, Shift, SupportItem
from service_logs.models import ServiceLog
from workers.models import SupportWorker


class PlannerBillingViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.users = {}
        for role in UserProfile.Role.values:
            user = get_user_model().objects.create_user(username=f"billing-{role}")
            UserProfile.objects.create(user=user, role=role)
            cls.users[role] = user
        cls.admin = cls.users[UserProfile.Role.ADMIN]
        cls.participant = Participant.objects.create(first_name="Ava", last_name="Nguyen")
        cls.worker = SupportWorker.objects.create(
            user=cls.users[UserProfile.Role.SUPPORT_WORKER], first_name="Wendy",
            last_name="Worker", email="billing-worker@example.com",
        )
        cls.item = SupportItem.objects.create(
            item_number="01_TEST", name="Self-care", price_limit=Decimal("73.58"),
        )
        cls.shift = Shift.objects.create(
            participant=cls.participant, worker=cls.worker, service_date=date(2026, 9, 28),
            start_time=time(9), end_time=time(12), planned_hours=Decimal("3"),
            support_item=cls.item, service_type=Shift.ServiceType.PERSONAL_CARE,
            status=Shift.Status.COMPLETED, created_by=cls.admin,
        )
        cls.log = ServiceLog.objects.create_from_shift(
            cls.shift, actual_start_time=time(9), actual_end_time=time(12, 15),
            actual_hours=Decimal("3.25"), status=ServiceLog.Status.APPROVED,
            case_notes="Private clinical notes not included in planner drawer",
        )

    def setUp(self):
        self.client.force_login(self.admin)
        self.params = {"date_from": "2026-09-28", "date_to": "2026-10-04"}

    def detail_url(self):
        return f"/roster/planner/{self.shift.pk}/billing/"

    def test_mode_is_off_by_default_and_does_not_render_billing_rows(self):
        response = self.client.get(reverse("roster_planner"), self.params)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="billing"')
        self.assertNotContains(response, 'data-planner-billing-url=')

    def test_all_views_enable_the_same_read_only_status_link(self):
        for mode in ("daily", "participant", "worker"):
            with self.subTest(mode=mode):
                response = self.client.get(reverse("roster_planner"), {
                    **self.params, "view": mode, "billing": "1",
                })
                self.assertContains(response, 'data-planner-billing-url=')
                self.assertContains(response, "Ready to invoice")
                self.assertContains(response, self.detail_url())
                self.assertContains(response, 'id="planner-billing-drawer"')

    def test_filter_only_changes_visible_shifts_and_preserves_navigation(self):
        response = self.client.get(reverse("roster_planner"), {
            **self.params, "billing": "1", "billing_status": "issued",
            "participant": self.participant.pk, "worker": self.worker.pk,
        })
        self.assertEqual(len(response.context["shifts"]), 0)
        self.assertEqual(len(response.context["planner_days"]), 7)
        for url in [response.context["next_week_url"], *response.context["mode_urls"].values()]:
            self.assertIn("billing=1", url)
            self.assertIn("billing_status=issued", url)
            self.assertIn(f"participant={self.participant.pk}", url)
            self.assertIn(f"worker={self.worker.pk}", url)

    def test_filter_does_not_change_worker_workload_totals(self):
        response = self.client.get(reverse("roster_planner"), {
            **self.params, "view": "worker", "worker": self.worker.pk,
            "billing": "1", "billing_status": "issued",
        })
        self.assertEqual(len(response.context["shifts"]), 0)
        self.assertEqual(response.context["planner_resources"][0]["hours_total"], Decimal("3"))

    def test_status_filter_is_ignored_when_billing_is_off(self):
        response = self.client.get(reverse("roster_planner"), {**self.params, "billing_status": "issued"})
        self.assertEqual(len(response.context["shifts"]), 1)

    def test_billing_filter_preserves_worker_conflict_warning(self):
        self.shift.status = Shift.Status.PUBLISHED
        self.shift.save(update_fields=["status"])
        Shift.objects.create(
            participant=self.participant, worker=self.worker,
            service_date=self.shift.service_date, start_time=time(10), end_time=time(13),
            planned_hours=Decimal("3"), support_item=self.item,
            service_type=self.shift.service_type, status=Shift.Status.PUBLISHED,
            created_by=self.admin,
        )
        response = self.client.get(reverse("roster_planner"), {
            **self.params, "view": "worker", "worker": self.worker.pk,
            "billing": "1", "billing_status": "issued",
        })
        self.assertEqual(response.context["shifts"], [])
        self.assertTrue(response.context["planner_resources"][0]["has_conflict"])

    def test_rostered_break_is_visible_without_actual_log(self):
        self.log.delete()
        self.shift.break_minutes = 15
        self.shift.save(update_fields=["break_minutes"])
        response = self.client.get(self.detail_url(), {"partial": "1"})
        self.assertContains(response, "Rostered break")
        self.assertContains(response, "15 minutes")
        self.assertNotContains(response, "<dt>Actual break</dt>")

    def test_conflicting_log_and_cancellation_do_not_assert_non_delivery(self):
        ParticipantCancellation.objects.create(
            shift=self.shift, status=ParticipantCancellation.Status.APPROVED,
            cancellation_type=ParticipantCancellation.CancellationType.SHORT_NOTICE,
            reason=ParticipantCancellation.Reason.HEALTH, details="Test conflict",
            received_at=timezone.now(), previous_shift_status=Shift.Status.CONFIRMED,
            submitted_by=self.admin,
        )
        response = self.client.get(self.detail_url(), {"partial": "1"})
        self.assertContains(response, "Conflicting service and cancellation records")
        self.assertNotContains(response, "Not delivered")

    def test_detail_partial_is_fresh_read_only_and_separates_durations(self):
        response = self.client.get(self.detail_url(), {"partial": "1"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("X-Planner-Billing"), "1")
        self.assertIn("no-store", response.headers.get("Cache-Control", ""))
        self.assertContains(response, "3.00")
        self.assertContains(response, "3.25")
        self.assertContains(response, "Not invoiced")
        self.assertNotContains(response, self.log.case_notes)
        self.assertNotContains(response, "<html")
        self.log.refresh_from_db()
        self.assertEqual(self.log.status, ServiceLog.Status.APPROVED)
        self.assertFalse(Invoice.objects.exists())

    def test_detail_has_standalone_fallback_and_rejects_post(self):
        response = self.client.get(self.detail_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<html")
        self.assertEqual(self.client.post(self.detail_url()).status_code, 405)
        self.assertEqual(self.client.get('/roster/planner/999999/billing/').status_code, 404)

    def test_only_admin_roles_can_read_detail(self):
        for role, user in self.users.items():
            self.client.force_login(user)
            expected = 200 if role in (UserProfile.Role.ADMIN, UserProfile.Role.SUPER_ADMIN) else 403
            self.assertEqual(self.client.get(self.detail_url()).status_code, expected, role)
        self.client.logout()
        self.assertEqual(self.client.get(self.detail_url()).status_code, 302)

    def test_invoice_status_is_read_from_live_invoice_and_cancellation_not_counted(self):
        invoice = Invoice.objects.create(
            participant=self.participant, period_start=self.shift.service_date,
            period_end=self.shift.service_date, created_by=self.admin,
        )
        InvoiceLine.objects.create_from_service_log(invoice, self.log)
        response = self.client.get(self.detail_url(), {"partial": "1"})
        self.assertContains(response, invoice.invoice_number)
        self.assertContains(response, "Draft")
        self.assertContains(response, "239.14")
        invoice.status = Invoice.Status.ISSUED
        invoice.save(update_fields=["status"])
        self.assertContains(self.client.get(self.detail_url(), {"partial": "1"}), "Issued")
        invoice.status = Invoice.Status.CANCELLED
        invoice.save(update_fields=["status"])
        self.assertNotContains(self.client.get(self.detail_url(), {"partial": "1"}), invoice.invoice_number)

    def test_record_text_is_escaped(self):
        self.participant.first_name = '<img src=x onerror="alert(1)">'
        self.participant.save()
        response = self.client.get(self.detail_url(), {"partial": "1"})
        self.assertNotContains(response, '<img src=x')
        self.assertContains(response, '&lt;img src=x')
