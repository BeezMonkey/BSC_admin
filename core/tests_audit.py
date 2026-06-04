from datetime import date, datetime, time
from decimal import Decimal
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import UserProfile
from core.models import AuditLog
from documents.models import Document
from invoices.models import Invoice
from participants.models import Participant
from scheduling.models import Shift, SupportItem
from service_logs.models import ServiceLog
from workers.models import SupportWorker


class AuditLogTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.media_dir = TemporaryDirectory()
        cls.override = override_settings(MEDIA_ROOT=cls.media_dir.name)
        cls.override.enable()

    @classmethod
    def tearDownClass(cls):
        cls.override.disable()
        cls.media_dir.cleanup()
        super().tearDownClass()

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
        self.worker_user = self.create_user_with_role(
            "worker",
            UserProfile.Role.SUPPORT_WORKER,
        )
        self.accountant_user = self.create_user_with_role(
            "accountant",
            UserProfile.Role.ACCOUNTANT,
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

    def login_admin(self):
        self.client.login(username="admin", password="test-password-123")

    def login_worker(self):
        self.client.login(username="worker", password="test-password-123")

    def login_accountant(self):
        self.client.login(username="accountant", password="test-password-123")

    def create_shift(self, **overrides):
        data = {
            "participant": self.participant,
            "worker": self.worker,
            "service_date": date(2026, 6, 1),
            "start_time": time(9, 0),
            "end_time": time(11, 0),
            "break_minutes": 0,
            "planned_hours": Decimal("2.00"),
            "support_item": self.support_item,
            "service_type": Shift.ServiceType.PERSONAL_CARE,
            "status": Shift.Status.PUBLISHED,
            "created_by": self.admin_user,
        }
        data.update(overrides)
        return Shift.objects.create(**data)

    def create_service_log(self, status=ServiceLog.Status.SUBMITTED):
        shift = self.create_shift(status=Shift.Status.COMPLETED)
        service_log = ServiceLog.objects.create_from_shift(
            shift=shift,
            actual_start_time=time(9, 0),
            actual_end_time=time(11, 0),
            break_minutes=0,
            actual_hours=Decimal("2.00"),
            kilometres=Decimal("0.0"),
            case_notes="Audit test log.",
            worker_notes="",
        )
        service_log.status = status
        service_log.save(update_fields=["status", "updated_at"])
        return service_log

    def create_invoice(self, status=Invoice.Status.DRAFT):
        invoice = Invoice.objects.create(
            participant=self.participant,
            period_start=date(2026, 6, 1),
            period_end=date(2026, 6, 30),
            status=status,
            created_by=self.accountant_user,
        )
        return invoice

    def assert_audit(self, action, object_type, object_id, actor):
        audit_log = AuditLog.objects.get(action=action)
        self.assertEqual(audit_log.object_type, object_type)
        self.assertEqual(audit_log.object_id, str(object_id))
        self.assertEqual(audit_log.actor, actor)
        self.assertNotEqual(audit_log.summary, "")
        return audit_log

    def test_service_log_approve_writes_audit_log(self):
        service_log = self.create_service_log()
        self.login_admin()

        self.client.post(reverse("service_log_approve", args=[service_log.id]))

        self.assert_audit(
            AuditLog.Action.SERVICE_LOG_APPROVED,
            "ServiceLog",
            service_log.id,
            self.admin_user,
        )

    def test_service_log_reject_writes_audit_log(self):
        service_log = self.create_service_log()
        self.login_admin()

        self.client.post(
            reverse("service_log_reject", args=[service_log.id]),
            {"rejection_reason": "Needs clarification."},
        )

        self.assert_audit(
            AuditLog.Action.SERVICE_LOG_REJECTED,
            "ServiceLog",
            service_log.id,
            self.admin_user,
        )

    def test_shift_cancel_writes_audit_log(self):
        shift = self.create_shift()
        self.login_admin()

        self.client.post(
            reverse("shift_cancel", args=[shift.id]),
            {"cancellation_reason": "Participant unavailable."},
        )

        self.assert_audit(
            AuditLog.Action.SHIFT_CANCELLED,
            "Shift",
            shift.id,
            self.admin_user,
        )

    def test_invoice_create_writes_audit_log(self):
        self.create_service_log(status=ServiceLog.Status.APPROVED)
        self.login_accountant()

        self.client.post(
            reverse("invoice_create"),
            {
                "participant": self.participant.id,
                "period_start": "2026-06-01",
                "period_end": "2026-06-30",
            },
        )

        invoice = Invoice.objects.get()
        self.assert_audit(
            AuditLog.Action.INVOICE_CREATED,
            "Invoice",
            invoice.id,
            self.accountant_user,
        )

    def test_invoice_status_changes_write_audit_logs(self):
        invoice = self.create_invoice()
        self.login_accountant()

        self.client.post(reverse("invoice_mark_issued", args=[invoice.id]))
        self.client.post(reverse("invoice_mark_paid", args=[invoice.id]))

        self.assert_audit(
            AuditLog.Action.INVOICE_MARKED_ISSUED,
            "Invoice",
            invoice.id,
            self.accountant_user,
        )
        self.assert_audit(
            AuditLog.Action.INVOICE_MARKED_PAID,
            "Invoice",
            invoice.id,
            self.accountant_user,
        )

    def test_invoice_cancel_writes_audit_log(self):
        invoice = self.create_invoice()
        self.login_accountant()

        self.client.post(reverse("invoice_cancel", args=[invoice.id]))

        self.assert_audit(
            AuditLog.Action.INVOICE_CANCELLED,
            "Invoice",
            invoice.id,
            self.accountant_user,
        )

    def test_document_upload_and_download_write_audit_logs(self):
        self.login_admin()

        response = self.client.post(
            reverse("document_create"),
            {
                "title": "Audit document",
                "category": Document.Category.GENERAL,
                "participant": self.participant.id,
                "worker": "",
                "invoice": "",
                "service_log": "",
                "notes": "",
                "file": SimpleUploadedFile("audit.pdf", b"file-content"),
            },
        )
        document = Document.objects.get()
        self.client.get(reverse("document_download", args=[document.id]))

        self.assertRedirects(response, reverse("document_detail", args=[document.id]))
        self.assert_audit(
            AuditLog.Action.DOCUMENT_UPLOADED,
            "Document",
            document.id,
            self.admin_user,
        )
        self.assert_audit(
            AuditLog.Action.DOCUMENT_DOWNLOADED,
            "Document",
            document.id,
            self.admin_user,
        )

    def test_admin_can_view_audit_log_list_and_detail(self):
        audit_log = AuditLog.objects.create(
            actor=self.admin_user,
            action=AuditLog.Action.SHIFT_CANCELLED,
            object_type="Shift",
            object_id="123",
            summary="Cancelled shift 123.",
        )
        AuditLog.objects.filter(id=audit_log.id).update(
            created_at=timezone.make_aware(datetime(2026, 6, 4, 9, 30)),
        )
        self.login_admin()

        list_response = self.client.get(reverse("audit_log_list"))
        detail_response = self.client.get(reverse("audit_log_detail", args=[audit_log.id]))

        self.assertContains(list_response, ">04/06/2026 09:30</a>")
        self.assertNotContains(list_response, "June 4, 2026")
        self.assertContains(detail_response, "04/06/2026 09:30")
        self.assertNotContains(detail_response, "June 4, 2026")
        self.assertContains(list_response, "Cancelled shift 123.")
        self.assertContains(detail_response, "Shift")
        self.assertContains(detail_response, "123")

    def test_worker_cannot_view_audit_logs(self):
        self.login_worker()

        response = self.client.get(reverse("audit_log_list"))

        self.assertEqual(response.status_code, 403)
