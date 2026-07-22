import csv
from datetime import date, time
from decimal import Decimal
from io import StringIO
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import UserProfile
from invoices.models import Invoice, InvoiceLine, InvoiceSettings
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
        self.assertEqual(rows[0]["period_start"], "01/06/2026")
        self.assertEqual(rows[0]["period_end"], "30/06/2026")
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

    def test_invoice_pdf_uses_clear_download_filename(self):
        self.login_accountant()

        response = self.client.get(reverse("invoice_pdf", args=[self.invoice.id]))

        invoice_date = timezone.localtime(self.invoice.created_at).strftime("%y%m%d")
        invoice_sequence = self.invoice.invoice_number.rsplit("-", 1)[-1]
        self.assertIn(
            f'filename="Invoice_{invoice_date}_{invoice_sequence}_Ava_Nguyen.pdf"',
            response["Content-Disposition"],
        )

    def test_invoice_pdf_formats_amounts_to_two_decimal_places(self):
        self.login_accountant()

        response = self.client.get(reverse("invoice_pdf", args=[self.invoice.id]))

        content = response.content.decode("latin-1")
        self.assertIn("Period: 01/06/2026 to 30/06/2026", content)
        self.assertNotIn("Period: 2026-06-01 to 2026-06-30", content)
        self.assertIn("2.00", content)
        self.assertIn("$65.47", content)
        self.assertIn("$130.94", content)
        self.assertIn("Invoice Total", content)
        self.assertNotIn("130.940000000000", content)

    def test_invoice_pdf_uses_invoice_settings_profile_and_payment_details(self):
        settings = InvoiceSettings.load()
        settings.business_name = "Brisbane Star Care"
        settings.abn = "36 601 940 023"
        settings.phone = "0455 555 555"
        settings.email = "billing@example.com"
        settings.address = "1 Care Street\nBrisbane QLD 4000"
        settings.bank_name = "BSC Bank"
        settings.account_name = "Brisbane Star Care Pty Ltd"
        settings.bsb = "123-456"
        settings.account_number = "987654321"
        settings.save()
        self.login_accountant()

        response = self.client.get(reverse("invoice_pdf", args=[self.invoice.id]))

        content = response.content.decode("latin-1")
        self.assertIn("Brisbane Star Care", content)
        self.assertIn("ABN: 36 601 940 023", content)
        self.assertIn("Phone: 0455 555 555", content)
        self.assertIn("Email: billing@example.com", content)
        self.assertIn("1 Care Street", content)
        self.assertIn("Brisbane QLD 4000", content)
        self.assertIn("Payment Details", content)
        self.assertIn("Bank", content)
        self.assertIn("BSC Bank", content)
        self.assertIn("Account name", content)
        self.assertIn("Brisbane Star Care Pty Ltd", content)
        self.assertIn("BSB", content)
        self.assertIn("123-456", content)
        self.assertIn("Account number", content)
        self.assertIn("987654321", content)

    def test_invoice_pdf_uses_structured_invoice_sections(self):
        self.participant.ndis_number = "431211998"
        self.participant.phone = "0416 017 469"
        self.participant.email = "jules@example.com"
        self.participant.plan_manager_name = "My Autonomy Plan Management"
        self.participant.plan_manager_phone = "1300 603 389"
        self.participant.plan_manager_email = "invoices@myautonomy.com.au"
        self.participant.save()
        self.login_accountant()

        response = self.client.get(reverse("invoice_pdf", args=[self.invoice.id]))

        content = response.content.decode("latin-1")
        self.assertIn("TAX INVOICE", content)
        self.assertIn("Invoice No.: #", content)
        self.assertIn("Invoice Date:", content)
        self.assertIn("PARTICIPANT INFORMATION", content)
        self.assertIn("NDIS NUMBER: 431211998", content)
        self.assertIn("Phone: 0416 017 469", content)
        self.assertIn("Email: jules@example.com", content)
        self.assertIn("SENT TO", content)
        self.assertIn("Name: My Autonomy Plan Management", content)
        self.assertIn("Phone: 1300 603 389", content)
        self.assertIn("Email: invoices@myautonomy.com.au", content)
        self.assertIn("Item", content)
        self.assertIn("Description", content)
        self.assertIn("Qty", content)
        self.assertIn("Rate", content)
        self.assertIn("Amount", content)
        self.assertIn("Invoice Total", content)
        self.assertIn("/Helvetica-Bold", content)
        self.assertIn("/F2", content)

    def test_invoice_pdf_header_uses_alignment_helpers(self):
        view_source = Path("invoices/views.py").read_text(encoding="utf-8")

        self.assertIn("INVOICE_STATIC_LOGO_PATH", view_source)
        self.assertIn("def pdf_image", view_source)
        self.assertIn("def load_pdf_image", view_source)
        self.assertIn("static/img/bsc-logo.png", view_source)
        self.assertIn("logo_image", view_source)
        self.assertIn("if logo_image:", view_source)
        self.assertIn("else:", view_source)
        self.assertIn("logo_width", view_source)
        self.assertIn("logo_height", view_source)
        self.assertIn("logo_y", view_source)
        self.assertIn("invoice_detail_y", view_source)
        self.assertIn("def pdf_right_text", view_source)
        self.assertNotIn("pdf_right_text(\"TAX INVOICE\"", view_source)
        self.assertIn("invoice_detail_x", view_source)
        self.assertIn("pdf_text(\"TAX INVOICE\", invoice_detail_x", view_source)
        self.assertIn("logo_area_width", view_source)
        self.assertIn("detail_line_gap", view_source)
        self.assertIn("participant_section_top", view_source)
        self.assertIn("sent_to_x", view_source)
        self.assertIn("def next_invoice_section_y", view_source)
        self.assertIn("line_items_top = next_invoice_section_y", view_source)
        self.assertNotIn("page_left,\n                292,", view_source)
        self.assertIn("business_info_y", view_source)
        self.assertNotIn('participant_line.startswith(("NDIS NUMBER:", "Phone:", "Email:", "Address:"))', view_source)
        self.assertNotIn('sent_to_line.startswith(("Phone:", "Email:"))', view_source)

    def test_invoice_pdf_line_items_use_table_columns(self):
        view_source = Path("invoices/views.py").read_text(encoding="utf-8")

        self.assertIn("item_col_x", view_source)
        self.assertIn("description_col_x", view_source)
        self.assertIn("qty_col_right", view_source)
        self.assertIn("rate_col_right", view_source)
        self.assertIn("amount_col_right", view_source)
        self.assertIn('pdf_right_text("Qty"', view_source)
        self.assertIn('pdf_right_text("Rate"', view_source)
        self.assertIn('pdf_right_text("Amount"', view_source)
        self.assertIn('pdf_right_text(f"{line.quantity:.2f}"', view_source)
        self.assertIn('pdf_right_text(f"${format_money(line.unit_price)}"', view_source)
        self.assertIn('pdf_right_text(f"${format_money(line.line_total)}"', view_source)
        self.assertIn('pdf_right_text(f"${format_money(invoice.total_amount)}"', view_source)
        self.assertNotIn('f"{line.quantity:.2f} x ${format_money(line.unit_price)}', view_source)

    def test_invoice_pdf_payment_details_use_two_column_layout(self):
        view_source = Path("invoices/views.py").read_text(encoding="utf-8")

        self.assertIn("payment_label_x", view_source)
        self.assertIn("payment_value_x", view_source)
        self.assertIn("payment_details_top", view_source)
        self.assertIn("payment_detail_rows", view_source)
        self.assertIn('pdf_text(label, payment_label_x', view_source)
        self.assertIn('pdf_text(value, payment_value_x', view_source)
        self.assertNotIn('append_if_present(payment_lines, "Bank"', view_source)

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
        self.service_log.refresh_from_db()
        self.assertRedirects(response, reverse("invoice_detail", args=[self.invoice.id]))
        self.assertEqual(self.invoice.status, Invoice.Status.CANCELLED)
        self.assertEqual(self.service_log.status, ServiceLog.Status.APPROVED)
        self.assertFalse(InvoiceLine.objects.filter(service_log=self.service_log).exists())

    def test_finance_user_can_cancel_issued_invoice_and_release_logs(self):
        self.invoice.status = Invoice.Status.ISSUED
        self.invoice.save(update_fields=["status", "updated_at"])
        self.login_accountant()

        response = self.client.post(reverse("invoice_cancel", args=[self.invoice.id]))

        self.invoice.refresh_from_db()
        self.service_log.refresh_from_db()
        self.assertRedirects(response, reverse("invoice_detail", args=[self.invoice.id]))
        self.assertEqual(self.invoice.status, Invoice.Status.CANCELLED)
        self.assertEqual(self.service_log.status, ServiceLog.Status.APPROVED)
        self.assertFalse(InvoiceLine.objects.filter(service_log=self.service_log).exists())

    def test_worker_cannot_download_invoice_csv(self):
        self.login_worker()

        response = self.client.get(reverse("invoice_csv", args=[self.invoice.id]))

        self.assertEqual(response.status_code, 403)
