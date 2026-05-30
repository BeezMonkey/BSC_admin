import csv
from datetime import date, time
from decimal import Decimal
from io import StringIO

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile
from invoices.models import Invoice, InvoiceLine
from participants.models import Participant
from scheduling.models import Shift, SupportItem
from service_logs.models import ServiceLog
from workers.models import SupportWorker


class InvoiceExportTests(TestCase):
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
        self.accountant_user = self.create_user_with_role(
            "accountant",
            UserProfile.Role.ACCOUNTANT,
        )
        self.admin_user = self.create_user_with_role("admin", UserProfile.Role.ADMIN)
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
        self.service_log = self.create_invoiced_service_log()
        self.invoice = Invoice.objects.create(
            participant=self.participant,
            period_start=date(2026, 6, 1),
            period_end=date(2026, 6, 30),
            created_by=self.accountant_user,
        )
        InvoiceLine.objects.create_from_service_log(
            invoice=self.invoice,
            service_log=self.service_log,
        )

    def create_invoiced_service_log(self):
        shift = Shift.objects.create(
            participant=self.participant,
            worker=self.worker,
            service_date=date(2026, 6, 1),
            start_time=time(9, 0),
            end_time=time(11, 0),
            break_minutes=0,
            planned_hours=Decimal("2.00"),
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
            actual_hours=Decimal("2.00"),
            kilometres=Decimal("0.0"),
            case_notes="Invoice export log.",
            worker_notes="",
        )
        service_log.status = ServiceLog.Status.INVOICED
        service_log.save(update_fields=["status", "updated_at"])
        return service_log

    def login_accountant(self):
        self.client.login(username="accountant", password="test-password-123")

    def login_worker(self):
        self.client.login(username="worker", password="test-password-123")

    def test_finance_user_can_download_invoice_csv(self):
        self.login_accountant()

        response = self.client.get(reverse("invoice_csv", args=[self.invoice.id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("attachment;", response["Content-Disposition"])
        rows = list(csv.DictReader(StringIO(response.content.decode("utf-8"))))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["invoice_number"], self.invoice.invoice_number)
        self.assertEqual(rows[0]["participant"], "Ava Nguyen")
        self.assertEqual(rows[0]["support_item_number"], "01_011_0107_1_1")
        self.assertEqual(rows[0]["quantity"], "2.00")
        self.assertEqual(rows[0]["unit_price"], "65.47")
        self.assertEqual(rows[0]["line_total"], "130.94")

    def test_finance_user_can_download_invoice_pdf(self):
        self.login_accountant()

        response = self.client.get(reverse("invoice_pdf", args=[self.invoice.id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("attachment;", response["Content-Disposition"])
        self.assertTrue(response.content.startswith(b"%PDF"))
        self.assertIn(self.invoice.invoice_number.encode("latin-1"), response.content)

    def test_finance_user_can_mark_invoice_issued(self):
        self.login_accountant()

        response = self.client.post(reverse("invoice_mark_issued", args=[self.invoice.id]))

        self.invoice.refresh_from_db()
        self.assertRedirects(response, reverse("invoice_detail", args=[self.invoice.id]))
        self.assertEqual(self.invoice.status, Invoice.Status.ISSUED)

    def test_finance_user_can_mark_invoice_paid(self):
        self.invoice.status = Invoice.Status.ISSUED
        self.invoice.save(update_fields=["status", "updated_at"])
        self.login_accountant()

        response = self.client.post(reverse("invoice_mark_paid", args=[self.invoice.id]))

        self.invoice.refresh_from_db()
        self.assertRedirects(response, reverse("invoice_detail", args=[self.invoice.id]))
        self.assertEqual(self.invoice.status, Invoice.Status.PAID)

    def test_finance_user_can_cancel_draft_invoice(self):
        self.login_accountant()

        response = self.client.post(reverse("invoice_cancel", args=[self.invoice.id]))

        self.invoice.refresh_from_db()
        self.assertRedirects(response, reverse("invoice_detail", args=[self.invoice.id]))
        self.assertEqual(self.invoice.status, Invoice.Status.CANCELLED)

    def test_worker_cannot_download_invoice_csv(self):
        self.login_worker()

        response = self.client.get(reverse("invoice_csv", args=[self.invoice.id]))

        self.assertEqual(response.status_code, 403)
