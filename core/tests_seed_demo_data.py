from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from accounts.models import UserProfile
from invoices.models import Invoice, InvoiceLine
from participants.models import Participant, ParticipantWorkerAssignment
from scheduling.models import Shift, SupportItem
from service_logs.models import ServiceLog
from workers.models import SupportWorker


class SeedDemoDataCommandTests(TestCase):
    def run_command(self):
        call_command("seed_demo_data", verbosity=0)

    def test_seed_demo_data_creates_demo_accounts_and_business_records(self):
        self.run_command()

        User = get_user_model()
        admin = User.objects.get(username="admin")
        worker_user = User.objects.get(username="worker")
        accountant = User.objects.get(username="accountant")

        self.assertTrue(admin.check_password("BscTest123!"))
        self.assertTrue(worker_user.check_password("BscTest123!"))
        self.assertTrue(accountant.check_password("BscTest123!"))
        self.assertEqual(admin.userprofile.role, UserProfile.Role.ADMIN)
        self.assertEqual(worker_user.userprofile.role, UserProfile.Role.SUPPORT_WORKER)
        self.assertEqual(accountant.userprofile.role, UserProfile.Role.ACCOUNTANT)

        participant = Participant.objects.get(ndis_number="430000001")
        worker = SupportWorker.objects.get(user=worker_user)
        assignment = ParticipantWorkerAssignment.objects.get(
            participant=participant,
            worker=worker,
            is_active=True,
        )
        support_item = SupportItem.objects.get(item_number="01_011_0107_1_1")
        shift = Shift.objects.get(participant=participant, worker=worker)
        service_log = ServiceLog.objects.get(shift=shift)
        invoice = Invoice.objects.get(participant=participant)
        invoice_line = InvoiceLine.objects.get(invoice=invoice, service_log=service_log)

        self.assertEqual(worker.email, "worker@example.com")
        self.assertEqual(assignment.notes, "Demo assignment for local trial.")
        self.assertEqual(support_item.name, "Assistance with self-care activities")
        self.assertEqual(shift.status, Shift.Status.COMPLETED)
        self.assertEqual(service_log.status, ServiceLog.Status.INVOICED)
        self.assertEqual(invoice_line.support_item_number, support_item.item_number)

    def test_seed_demo_data_is_idempotent_for_stable_records(self):
        self.run_command()
        self.run_command()

        User = get_user_model()
        self.assertEqual(User.objects.filter(username="admin").count(), 1)
        self.assertEqual(User.objects.filter(username="worker").count(), 1)
        self.assertEqual(User.objects.filter(username="accountant").count(), 1)
        self.assertEqual(Participant.objects.filter(ndis_number="430000001").count(), 1)
        self.assertEqual(SupportWorker.objects.filter(email="worker@example.com").count(), 1)
        self.assertEqual(SupportItem.objects.filter(item_number="01_011_0107_1_1").count(), 1)
        self.assertEqual(Shift.objects.count(), 1)
        self.assertEqual(ServiceLog.objects.count(), 1)
        self.assertEqual(Invoice.objects.count(), 1)
        self.assertEqual(InvoiceLine.objects.count(), 1)
