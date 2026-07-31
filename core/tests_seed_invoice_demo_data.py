from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from accounts.models import UserProfile
from invoices.models import Invoice, InvoiceLine, InvoiceSettings
from participants.models import Participant, ParticipantWorkerAssignment
from scheduling.models import Shift, SupportItem
from service_logs.models import ServiceLog
from workers.models import SupportWorker


class SeedInvoiceDemoDataCommandTests(TestCase):
    def test_seed_invoice_demo_data_creates_invoice_trial_records(self):
        settings = InvoiceSettings.load()
        settings.next_invoice_sequence = 99
        settings.save()

        call_command("seed_invoice_demo_data", verbosity=0)

        self.assertEqual(
            Participant.objects.filter(ndis_number__startswith="889000").count(),
            3,
        )
        self.assertEqual(
            SupportWorker.objects.filter(email__startswith="invoice.demo.worker").count(),
            2,
        )
        self.assertEqual(
            SupportItem.objects.filter(item_number="DEMO-INVOICE-001").count(),
            1,
        )
        self.assertEqual(ParticipantWorkerAssignment.objects.count(), 3)
        self.assertEqual(Shift.objects.count(), 4)
        self.assertEqual(
            ServiceLog.objects.filter(status=ServiceLog.Status.INVOICED).count(),
            3,
        )
        self.assertEqual(
            ServiceLog.objects.filter(
                status=ServiceLog.Status.APPROVED,
                invoice_lines__isnull=True,
            ).count(),
            1,
        )
        self.assertEqual(Invoice.objects.filter(invoice_number__startswith="DEMO-INV-").count(), 3)
        self.assertEqual(Invoice.objects.filter(status=Invoice.Status.DRAFT).count(), 1)
        self.assertEqual(Invoice.objects.filter(status=Invoice.Status.ISSUED).count(), 1)
        self.assertEqual(Invoice.objects.filter(status=Invoice.Status.PAID).count(), 1)
        self.assertEqual(InvoiceLine.objects.count(), 3)
        settings.refresh_from_db()
        self.assertEqual(settings.next_invoice_sequence, 99)

    def test_seed_invoice_demo_data_is_idempotent(self):
        call_command("seed_invoice_demo_data", verbosity=0)
        call_command("seed_invoice_demo_data", verbosity=0)

        User = get_user_model()
        self.assertEqual(User.objects.filter(username__startswith="invoice_demo_").count(), 4)
        self.assertEqual(Participant.objects.filter(ndis_number__startswith="889000").count(), 3)
        self.assertEqual(
            SupportWorker.objects.filter(email__startswith="invoice.demo.worker").count(),
            2,
        )
        self.assertEqual(Shift.objects.count(), 4)
        self.assertEqual(ServiceLog.objects.count(), 4)
        self.assertEqual(Invoice.objects.filter(invoice_number__startswith="DEMO-INV-").count(), 3)
        self.assertEqual(InvoiceLine.objects.count(), 3)

    def test_seed_invoice_demo_data_preserves_existing_travel_lines(self):
        call_command("seed_invoice_demo_data", verbosity=0)
        service_log = ServiceLog.objects.filter(
            status=ServiceLog.Status.INVOICED
        ).order_by("id")[0]
        invoice = Invoice.objects.get(lines__service_log=service_log)
        travel_item = SupportItem.objects.create(
            item_number="04_799_0125_6_1",
            name="Provider travel - non-labour costs",
            unit=SupportItem.Unit.EACH,
            price_limit=Decimal("1.00"),
            gst_code=SupportItem.GSTCode.GST_FREE,
        )
        InvoiceLine.objects.create_travel_claim_from_service_log(
            invoice=invoice,
            service_log=service_log,
            support_item=travel_item,
            amount=Decimal("12.00"),
        )

        call_command("seed_invoice_demo_data", verbosity=0)

        self.assertEqual(InvoiceLine.objects.filter(service_log=service_log).count(), 2)

    def test_seed_invoice_demo_data_reset_preserves_non_demo_records(self):
        User = get_user_model()
        real_user = User.objects.create_user(
            username="real_admin",
            email="real.admin@example.com",
            password="real-password",
        )
        UserProfile.objects.create(user=real_user, role=UserProfile.Role.ADMIN)
        real_participant = Participant.objects.create(
            first_name="Real",
            last_name="Participant",
            ndis_number="123456789",
            status=Participant.Status.ACTIVE,
        )
        call_command("seed_invoice_demo_data", verbosity=0)

        call_command("seed_invoice_demo_data", reset=True, verbosity=0)

        self.assertTrue(Participant.objects.filter(id=real_participant.id).exists())
        self.assertTrue(User.objects.filter(id=real_user.id).exists())
        self.assertEqual(Participant.objects.filter(ndis_number__startswith="889000").count(), 3)
        self.assertEqual(Invoice.objects.filter(invoice_number__startswith="DEMO-INV-").count(), 3)
