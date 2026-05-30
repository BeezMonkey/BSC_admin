from datetime import date, time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile
from invoices.models import Invoice, InvoiceLine
from participants.models import Participant
from scheduling.models import Shift, SupportItem
from service_logs.models import ServiceLog
from workers.models import SupportWorker


class InvoiceGenerationTests(TestCase):
    def create_user_with_role(self, username, role):
        user = get_user_model().objects.create_user(
            username=username,
            password="test-password-123",
            email=f"{username}@example.com",
        )
        UserProfile.objects.create(
            user=user,
            role=role,
            is_active_worker=role == UserProfile.Role.SUPPORT_WORKER,
        )
        return user

    def setUp(self):
        self.admin_user = self.create_user_with_role("admin", UserProfile.Role.ADMIN)
        self.accountant_user = self.create_user_with_role(
            "accountant",
            UserProfile.Role.ACCOUNTANT,
        )
        self.worker_user = self.create_user_with_role(
            "worker",
            UserProfile.Role.SUPPORT_WORKER,
        )
        self.participant = Participant.objects.create(
            first_name="Ava",
            last_name="Nguyen",
            status=Participant.Status.ACTIVE,
            address_line_1="10 Creek Street",
            suburb="Brisbane",
            state="QLD",
            postcode="4000",
        )
        self.other_participant = Participant.objects.create(
            first_name="Ben",
            last_name="Taylor",
            status=Participant.Status.ACTIVE,
            address_line_1="20 River Street",
            suburb="Brisbane",
            state="QLD",
            postcode="4000",
        )
        self.worker = SupportWorker.objects.create(
            user=self.worker_user,
            first_name="Wendy",
            last_name="Worker",
            email="worker@example.com",
            status=SupportWorker.Status.ACTIVE,
        )
        self.support_item = SupportItem.objects.create(
            item_number="01_011_0107_1_1",
            name="Assistance with self-care activities",
            unit=SupportItem.Unit.HOUR,
            price_limit=Decimal("65.47"),
            gst_code=SupportItem.GSTCode.GST_FREE,
            is_active=True,
        )

    def create_service_log(self, **overrides):
        participant = overrides.pop("participant", self.participant)
        service_date = overrides.pop("service_date", date(2026, 6, 1))
        status = overrides.pop("status", ServiceLog.Status.APPROVED)
        actual_hours = overrides.pop("actual_hours", Decimal("2.00"))
        shift = Shift.objects.create(
            participant=participant,
            worker=self.worker,
            service_date=service_date,
            start_time=time(9, 0),
            end_time=time(11, 0),
            break_minutes=0,
            planned_hours=actual_hours,
            support_item=self.support_item,
            service_type=Shift.ServiceType.PERSONAL_CARE,
            status=Shift.Status.COMPLETED,
            created_by=self.admin_user,
        )
        service_log = ServiceLog.objects.create_from_shift(
            shift=shift,
            actual_start_time=time(9, 0),
            actual_end_time=time(11, 0),
            break_minutes=0,
            actual_hours=actual_hours,
            kilometres=Decimal("0.0"),
            case_notes=f"Log for {participant.display_name}",
            worker_notes="",
        )
        service_log.status = status
        service_log.save(update_fields=["status", "updated_at"])
        return service_log

    def login_accountant(self):
        self.client.login(username="accountant", password="test-password-123")

    def login_worker(self):
        self.client.login(username="worker", password="test-password-123")

    def create_payload(self, **overrides):
        data = {
            "participant": self.participant.id,
            "period_start": "2026-06-01",
            "period_end": "2026-06-30",
        }
        data.update(overrides)
        return data

    def test_finance_user_can_preview_approved_uninvoiced_logs(self):
        self.create_service_log()
        self.create_service_log(status=ServiceLog.Status.SUBMITTED)
        self.create_service_log(participant=self.other_participant)
        self.login_accountant()

        response = self.client.get(reverse("invoice_create"), self.create_payload())

        self.assertContains(response, "Log for Ava Nguyen", count=1)
        self.assertNotContains(response, "Log for Ben Taylor")
        self.assertContains(response, "Create Invoice")

    def test_finance_user_can_create_invoice_from_approved_logs(self):
        first_log = self.create_service_log(actual_hours=Decimal("2.00"))
        second_log = self.create_service_log(
            service_date=date(2026, 6, 2),
            actual_hours=Decimal("1.50"),
        )
        self.login_accountant()

        response = self.client.post(reverse("invoice_create"), self.create_payload())

        invoice = Invoice.objects.get()
        self.assertRedirects(response, reverse("invoice_detail", args=[invoice.id]))
        self.assertEqual(invoice.participant, self.participant)
        self.assertEqual(invoice.created_by, self.accountant_user)
        self.assertEqual(invoice.lines.count(), 2)
        self.assertEqual(invoice.total_amount, Decimal("229.15"))
        first_log.refresh_from_db()
        second_log.refresh_from_db()
        self.assertEqual(first_log.status, ServiceLog.Status.INVOICED)
        self.assertEqual(second_log.status, ServiceLog.Status.INVOICED)

    def test_invoice_line_preserves_support_item_values(self):
        service_log = self.create_service_log(actual_hours=Decimal("2.00"))
        self.login_accountant()

        self.client.post(reverse("invoice_create"), self.create_payload())

        line = InvoiceLine.objects.get(service_log=service_log)
        self.assertEqual(line.support_item_number, "01_011_0107_1_1")
        self.assertEqual(line.description, "Assistance with self-care activities")
        self.assertEqual(line.unit, SupportItem.Unit.HOUR)
        self.assertEqual(line.unit_price, Decimal("65.47"))
        self.assertEqual(line.quantity, Decimal("2.00"))
        self.assertEqual(line.line_total, Decimal("130.94"))

    def test_already_invoiced_logs_are_excluded(self):
        service_log = self.create_service_log()
        invoice = Invoice.objects.create(
            participant=self.participant,
            period_start=date(2026, 6, 1),
            period_end=date(2026, 6, 30),
            created_by=self.accountant_user,
        )
        InvoiceLine.objects.create_from_service_log(invoice=invoice, service_log=service_log)
        service_log.status = ServiceLog.Status.INVOICED
        service_log.save(update_fields=["status", "updated_at"])
        self.login_accountant()

        response = self.client.get(reverse("invoice_create"), self.create_payload())

        self.assertNotContains(response, "Log for Ava Nguyen")
        self.assertContains(response, "No approved logs found")

    def test_worker_cannot_access_invoice_generation(self):
        self.login_worker()

        response = self.client.get(reverse("invoice_create"))

        self.assertEqual(response.status_code, 403)
