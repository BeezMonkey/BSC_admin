from datetime import date, time
from decimal import Decimal
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from accounts.models import UserProfile
from coordinators.models import (
    CoordinationLog,
    ParticipantCoordinatorAssignment,
    SupportCoordinator,
)
from core.models import AuditLog
from documents.models import Document
from invoices.models import Invoice, InvoiceLine, InvoiceSettings
from participants.models import Participant, ParticipantWorkerAssignment
from scheduling.models import Shift, SupportItem
from service_logs.models import ServiceLog
from workers.models import SupportWorker


class PurgeTrialDemoDataCommandTests(TestCase):
    def setUp(self):
        self.User = get_user_model()

    def test_dry_run_reports_counts_without_deleting_records(self):
        call_command("seed_beta_test_data", verbosity=0)
        out = StringIO()

        call_command("purge_trial_demo_data", stdout=out)

        self.assertIn("Trial demo purge preview", out.getvalue())
        self.assertIn("Dry run only", out.getvalue())
        self.assertTrue(self.User.objects.filter(username="beta_worker").exists())
        self.assertTrue(Participant.objects.filter(ndis_number="990000001").exists())

    def test_confirm_removes_demo_records_without_rebuilding_seed_data(self):
        call_command("seed_beta_test_data", verbosity=0)
        call_command("seed_invoice_demo_data", verbosity=0)
        self.create_support_coordination_demo_record()
        out = StringIO()

        call_command("purge_trial_demo_data", confirm=True, stdout=out, verbosity=0)

        self.assertIn("Trial demo data purged", out.getvalue())
        self.assertFalse(self.User.objects.filter(username="beta_worker").exists())
        self.assertFalse(self.User.objects.filter(username__startswith="invoice_demo_").exists())
        self.assertFalse(self.User.objects.filter(username="bsc_demo_coordinator_1").exists())
        self.assertFalse(Participant.objects.filter(ndis_number="990000001").exists())
        self.assertFalse(Participant.objects.filter(ndis_number__startswith="889000").exists())
        self.assertFalse(SupportWorker.objects.filter(email__startswith="invoice.demo.worker").exists())
        self.assertFalse(SupportCoordinator.objects.filter(email__startswith="bsc.demo.coordinator").exists())
        self.assertFalse(Shift.objects.exists())
        self.assertFalse(ServiceLog.objects.exists())
        self.assertFalse(CoordinationLog.objects.exists())
        self.assertFalse(Invoice.objects.exists())
        self.assertFalse(Document.objects.exists())
        self.assertFalse(AuditLog.objects.exists())
        self.assertFalse(SupportItem.objects.filter(item_number="BETA-TEST-001").exists())
        self.assertFalse(SupportItem.objects.filter(item_number="DEMO-INVOICE-001").exists())
        self.assertEqual(self.User.objects.filter(username__startswith="bsc_demo_worker_").count(), 0)

    def test_confirm_preserves_real_records_admin_settings_and_official_support_items(self):
        admin = self.User.objects.create_user(
            username="admin",
            email="owner@example.com",
            password="admin-password",
        )
        UserProfile.objects.create(user=admin, role=UserProfile.Role.ADMIN)
        real_worker_user = self.User.objects.create_user(
            username="real_worker",
            email="real.worker@bsc.com",
            password="worker-password",
        )
        UserProfile.objects.create(
            user=real_worker_user,
            role=UserProfile.Role.SUPPORT_WORKER,
            is_active_worker=True,
        )
        real_coordinator_user = self.User.objects.create_user(
            username="real_sc",
            email="real.sc@bsc.com",
            password="coordinator-password",
        )
        UserProfile.objects.create(
            user=real_coordinator_user,
            role=UserProfile.Role.SUPPORT_COORDINATOR,
        )
        real_participant = Participant.objects.create(
            first_name="Real",
            last_name="Participant",
            ndis_number="123456789",
            email="real.participant@example.com",
            status=Participant.Status.ACTIVE,
        )
        real_worker = SupportWorker.objects.create(
            user=real_worker_user,
            first_name="Real",
            last_name="Worker",
            email="real.worker@bsc.com",
            status=SupportWorker.Status.ACTIVE,
        )
        real_coordinator = SupportCoordinator.objects.create(
            user=real_coordinator_user,
            first_name="Real",
            last_name="Coordinator",
            email="real.sc@bsc.com",
            status=SupportCoordinator.Status.ACTIVE,
        )
        ParticipantWorkerAssignment.objects.create(
            participant=real_participant,
            worker=real_worker,
            start_date=date(2026, 9, 1),
        )
        ParticipantCoordinatorAssignment.objects.create(
            participant=real_participant,
            coordinator=real_coordinator,
            start_date=date(2026, 9, 1),
        )
        official_item = SupportItem.objects.create(
            item_number="01_011_0107_1_1",
            name="Official item",
            unit=SupportItem.Unit.HOUR,
            price_limit=Decimal("73.58"),
            gst_code=SupportItem.GSTCode.GST_FREE,
            is_active=True,
        )
        settings = InvoiceSettings.load()
        settings.invoice_prefix = "BSC"
        settings.next_invoice_sequence = 88
        settings.save()
        call_command("seed_beta_test_data", verbosity=0)

        call_command("purge_trial_demo_data", confirm=True, verbosity=0)

        admin.refresh_from_db()
        settings.refresh_from_db()
        self.assertTrue(admin.check_password("admin-password"))
        self.assertTrue(Participant.objects.filter(id=real_participant.id).exists())
        self.assertTrue(SupportWorker.objects.filter(id=real_worker.id).exists())
        self.assertTrue(SupportCoordinator.objects.filter(id=real_coordinator.id).exists())
        self.assertTrue(SupportItem.objects.filter(id=official_item.id).exists())
        self.assertEqual(settings.next_invoice_sequence, 88)
        self.assertEqual(settings.invoice_prefix, "BSC")

    def create_support_coordination_demo_record(self):
        admin = self.User.objects.create_user(
            username="bsc_demo_sc_admin",
            email="bsc.demo.sc.admin@example.com",
            password="demo-password",
        )
        UserProfile.objects.create(user=admin, role=UserProfile.Role.ADMIN)
        coordinator_user = self.User.objects.create_user(
            username="bsc_demo_coordinator_1",
            email="bsc.demo.coordinator.1@example.com",
            password="demo-password",
        )
        UserProfile.objects.create(
            user=coordinator_user,
            role=UserProfile.Role.SUPPORT_COORDINATOR,
        )
        participant = Participant.objects.create(
            first_name="Demo",
            last_name="SC Participant",
            ndis_number="777000901",
            email="bsc.demo.sc.participant@example.com",
            status=Participant.Status.ACTIVE,
        )
        coordinator = SupportCoordinator.objects.create(
            user=coordinator_user,
            first_name="Demo",
            last_name="Coordinator",
            email="bsc.demo.coordinator.1@example.com",
            status=SupportCoordinator.Status.ACTIVE,
        )
        ParticipantCoordinatorAssignment.objects.create(
            participant=participant,
            coordinator=coordinator,
            start_date=date(2026, 9, 1),
        )
        support_item = SupportItem.objects.create(
            item_number="DEMO-SC-001",
            name="Demo support coordination",
            unit=SupportItem.Unit.HOUR,
            price_limit=Decimal("100.00"),
            gst_code=SupportItem.GSTCode.GST_FREE,
            is_active=True,
        )
        coordination_log = CoordinationLog.objects.create(
            participant=participant,
            coordinator=coordinator,
            service_date=date(2026, 9, 2),
            start_time=time(10, 0),
            end_time=time(11, 0),
            actual_hours=Decimal("1.00"),
            coordination_type=CoordinationLog.CoordinationType.GENERAL,
            case_notes="Demo SC work.",
            status=CoordinationLog.Status.INVOICED,
            reviewed_by=admin,
        )
        invoice = Invoice.objects.create(
            invoice_number="DEMO-SC-INV-0001",
            invoice_type=Invoice.InvoiceType.SUPPORT_COORDINATION,
            participant=participant,
            period_start=date(2026, 9, 2),
            period_end=date(2026, 9, 2),
            created_by=admin,
        )
        InvoiceLine.objects.create_from_coordination_log(
            invoice=invoice,
            coordination_log=coordination_log,
            support_item=support_item,
        )
        Document.objects.create(
            title="Demo SC attachment",
            file="documents/demo-sc.pdf",
            original_filename="demo-sc.pdf",
            participant=participant,
            invoice=invoice,
            uploaded_by=coordinator_user,
        )
        AuditLog.objects.create(
            actor=coordinator_user,
            action=AuditLog.Action.COORDINATION_LOG_SUBMITTED,
            object_type="CoordinationLog",
            object_id=str(coordination_log.id),
            summary="Submitted demo coordination log.",
        )
