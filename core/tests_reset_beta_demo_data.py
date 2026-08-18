from io import StringIO
from datetime import date, time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from accounts.models import UserProfile
from invoices.models import InvoiceSettings
from participants.models import Participant, ParticipantWorkerAssignment
from scheduling.models import Shift, SupportItem
from service_logs.models import ServiceLog
from workers.models import SupportWorker


class ResetBetaDemoDataCommandTests(TestCase):
    def test_dry_run_does_not_change_database(self):
        User = get_user_model()
        admin = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="admin-password",
        )
        UserProfile.objects.create(user=admin, role=UserProfile.Role.ADMIN)
        real_participant = Participant.objects.create(
            first_name="Real",
            last_name="Participant",
            ndis_number="123456789",
            status=Participant.Status.ACTIVE,
        )
        settings = InvoiceSettings.load()
        settings.next_invoice_sequence = 42
        settings.save()
        out = StringIO()

        call_command("reset_beta_demo_data", stdout=out)

        self.assertIn("Dry run only", out.getvalue())
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(Participant.objects.count(), 1)
        self.assertEqual(Participant.objects.get().id, real_participant.id)
        settings.refresh_from_db()
        self.assertEqual(settings.next_invoice_sequence, 42)

    def test_confirm_removes_legacy_demo_data_and_creates_five_by_five_trial_set(self):
        call_command("seed_beta_test_data", verbosity=0)
        call_command("seed_invoice_demo_data", verbosity=0)
        out = StringIO()

        call_command("reset_beta_demo_data", confirm=True, stdout=out, verbosity=0)

        User = get_user_model()
        self.assertIn("Beta demo data reset complete", out.getvalue())
        self.assertEqual(User.objects.filter(username__startswith="bsc_demo_worker_").count(), 5)
        self.assertEqual(Participant.objects.filter(ndis_number__startswith="777000").count(), 5)
        self.assertEqual(SupportWorker.objects.filter(email__startswith="bsc.demo.worker").count(), 5)
        self.assertEqual(ParticipantWorkerAssignment.objects.filter(is_active=True).count(), 5)
        self.assertEqual(Shift.objects.filter(status=Shift.Status.PUBLISHED).count(), 5)
        self.assertEqual(ServiceLog.objects.count(), 0)
        self.assertEqual(SupportItem.objects.filter(item_number="BETA-TEST-001").count(), 0)
        self.assertEqual(SupportItem.objects.filter(item_number="DEMO-INVOICE-001").count(), 0)
        self.assertEqual(Participant.objects.filter(ndis_number="990000001").count(), 0)
        self.assertEqual(Participant.objects.filter(ndis_number__startswith="889000").count(), 0)
        self.assertEqual(User.objects.filter(username="beta_worker").count(), 0)
        self.assertEqual(User.objects.filter(username__startswith="invoice_demo_").count(), 0)

    def test_confirm_removes_records_that_reference_legacy_demo_support_items(self):
        User = get_user_model()
        admin = User.objects.create_user(username="admin", password="admin-password")
        UserProfile.objects.create(user=admin, role=UserProfile.Role.ADMIN)
        worker_user = User.objects.create_user(username="real_worker", password="worker-password")
        worker = SupportWorker.objects.create(
            user=worker_user,
            first_name="Real",
            last_name="Worker",
            email="real.worker@example.com",
            phone="0400000000",
            status=SupportWorker.Status.ACTIVE,
        )
        participant = Participant.objects.create(
            first_name="Real",
            last_name="Participant",
            ndis_number="123456789",
            status=Participant.Status.ACTIVE,
        )
        legacy_item = SupportItem.objects.create(
            item_number="BETA-TEST-001",
            name="Legacy demo item",
            unit=SupportItem.Unit.HOUR,
            price_limit="65.47",
            gst_code=SupportItem.GSTCode.GST_FREE,
            is_active=True,
        )
        shift = Shift.objects.create(
            participant=participant,
            worker=worker,
            service_date=date(2026, 7, 1),
            start_time=time(9, 0),
            end_time=time(12, 0),
            break_minutes=0,
            planned_hours=Decimal("3.00"),
            support_item=legacy_item,
            service_type=Shift.ServiceType.PERSONAL_CARE,
            status=Shift.Status.COMPLETED,
            created_by=admin,
        )
        ServiceLog.objects.create_from_shift(
            shift,
            actual_start_time=time(9, 0),
            actual_end_time=time(12, 0),
            break_minutes=0,
            actual_hours=Decimal("3.00"),
            case_notes="Legacy demo log.",
        )

        call_command("reset_beta_demo_data", confirm=True, verbosity=0)

        self.assertFalse(Shift.objects.filter(id=shift.id).exists())
        self.assertEqual(ServiceLog.objects.count(), 0)
        self.assertFalse(SupportItem.objects.filter(item_number="BETA-TEST-001").exists())
        self.assertTrue(Participant.objects.filter(id=participant.id).exists())
        self.assertTrue(SupportWorker.objects.filter(id=worker.id).exists())
        self.assertTrue(User.objects.filter(username="admin").exists())

    def test_confirm_preserves_real_records_settings_and_official_support_items(self):
        User = get_user_model()
        admin = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="admin-password",
        )
        UserProfile.objects.create(user=admin, role=UserProfile.Role.ADMIN)
        real_participant = Participant.objects.create(
            first_name="Real",
            last_name="Participant",
            ndis_number="123456789",
            status=Participant.Status.ACTIVE,
        )
        official_item = SupportItem.objects.create(
            item_number="01_011_0107_1_1",
            name="Existing official item",
            unit=SupportItem.Unit.HOUR,
            price_limit="70.00",
            gst_code=SupportItem.GSTCode.GST_FREE,
            is_active=True,
        )
        settings = InvoiceSettings.load()
        settings.invoice_prefix = "BSC"
        settings.next_invoice_sequence = 88
        settings.save()

        call_command("reset_beta_demo_data", confirm=True, verbosity=0)

        admin.refresh_from_db()
        settings.refresh_from_db()
        self.assertTrue(admin.check_password("admin-password"))
        self.assertTrue(Participant.objects.filter(id=real_participant.id).exists())
        self.assertEqual(settings.next_invoice_sequence, 88)
        self.assertTrue(SupportItem.objects.filter(id=official_item.id).exists())
        self.assertTrue(SupportItem.objects.filter(item_number="04_104_0125_6_1").exists())
        self.assertTrue(SupportItem.objects.filter(item_number="04_799_0125_6_1").exists())
