from datetime import date, time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import UserProfile
from invoices.models import Invoice, InvoiceLine
from participants.models import Participant, ParticipantWorkerAssignment
from scheduling.models import Shift, SupportItem
from service_logs.models import ServiceLog
from workers.models import SupportWorker


DEMO_PASSWORD = "InvoiceDemo456"
DEMO_USERNAMES = (
    "invoice_demo_admin",
    "invoice_demo_accountant",
    "invoice_demo_worker_1",
    "invoice_demo_worker_2",
)
DEMO_NDIS_PREFIX = "889000"
DEMO_SUPPORT_ITEM = "DEMO-INVOICE-001"
DEMO_INVOICE_PREFIX = "DEMO-INV-"


class Command(BaseCommand):
    help = "Create or rebuild invoice-focused demo data for beta trial use."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing invoice demo records before recreating them.",
        )
        parser.add_argument(
            "--password",
            default=DEMO_PASSWORD,
            help="Password for generated invoice demo accounts.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        self.verbosity = options.get("verbosity", 1)
        if options["reset"]:
            self.delete_demo_records()

        admin = self.upsert_user(
            "invoice_demo_admin",
            "invoice.demo.admin@example.com",
            options["password"],
            UserProfile.Role.ADMIN,
        )
        accountant = self.upsert_user(
            "invoice_demo_accountant",
            "invoice.demo.accountant@example.com",
            options["password"],
            UserProfile.Role.ACCOUNTANT,
        )
        worker_one_user = self.upsert_user(
            "invoice_demo_worker_1",
            "invoice.demo.worker.1@example.com",
            options["password"],
            UserProfile.Role.SUPPORT_WORKER,
            is_active_worker=True,
        )
        worker_two_user = self.upsert_user(
            "invoice_demo_worker_2",
            "invoice.demo.worker.2@example.com",
            options["password"],
            UserProfile.Role.SUPPORT_WORKER,
            is_active_worker=True,
        )

        participants = self.upsert_participants()
        worker_one = self.upsert_worker(
            worker_one_user,
            "Invoice",
            "Worker One",
            "invoice.demo.worker.1@example.com",
        )
        worker_two = self.upsert_worker(
            worker_two_user,
            "Invoice",
            "Worker Two",
            "invoice.demo.worker.2@example.com",
        )
        support_item = self.upsert_support_item()
        self.upsert_assignment(participants[0], worker_one)
        self.upsert_assignment(participants[1], worker_one)
        self.upsert_assignment(participants[2], worker_two)

        invoice_records = [
            {
                "invoice_number": "DEMO-INV-0001",
                "participant": participants[0],
                "worker": worker_one,
                "service_date": date(2026, 6, 3),
                "start_time": time(9, 0),
                "end_time": time(12, 0),
                "hours": Decimal("3.00"),
                "status": Invoice.Status.DRAFT,
                "notes": "Draft invoice example for morning personal care.",
            },
            {
                "invoice_number": "DEMO-INV-0002",
                "participant": participants[0],
                "worker": worker_two,
                "service_date": date(2026, 6, 10),
                "start_time": time(10, 0),
                "end_time": time(12, 30),
                "hours": Decimal("2.50"),
                "status": Invoice.Status.ISSUED,
                "notes": "Issued invoice example for community access support.",
            },
            {
                "invoice_number": "DEMO-INV-0003",
                "participant": participants[1],
                "worker": worker_one,
                "service_date": date(2026, 6, 17),
                "start_time": time(9, 0),
                "end_time": time(13, 0),
                "hours": Decimal("4.00"),
                "status": Invoice.Status.PAID,
                "notes": "Paid invoice example for a longer support shift.",
            },
        ]
        invoices = [
            self.upsert_invoiced_record(admin, accountant, support_item, record)
            for record in invoice_records
        ]
        approved_log = self.upsert_approved_log(
            admin,
            participants[2],
            worker_two,
            support_item,
        )

        if self.verbosity:
            self.stdout.write(self.style.SUCCESS("Invoice demo data ready."))
            self.stdout.write(f"Admin login: invoice_demo_admin / {options['password']}")
            self.stdout.write(
                f"Accountant login: invoice_demo_accountant / {options['password']}"
            )
            self.stdout.write(f"Worker login: invoice_demo_worker_1 / {options['password']}")
            self.stdout.write(f"Second worker login: invoice_demo_worker_2 / {options['password']}")
            self.stdout.write(
                "Invoices: " + ", ".join(invoice.invoice_number for invoice in invoices)
            )
            self.stdout.write(f"Approved log ready for invoicing: {approved_log}")

    def delete_demo_records(self):
        demo_participants = Participant.objects.filter(ndis_number__startswith=DEMO_NDIS_PREFIX)
        demo_workers = SupportWorker.objects.filter(user__username__in=DEMO_USERNAMES)
        Invoice.objects.filter(invoice_number__startswith=DEMO_INVOICE_PREFIX).delete()
        ServiceLog.objects.filter(participant__in=demo_participants).delete()
        Shift.objects.filter(participant__in=demo_participants).delete()
        ParticipantWorkerAssignment.objects.filter(participant__in=demo_participants).delete()
        demo_participants.delete()
        demo_workers.delete()
        SupportItem.objects.filter(item_number=DEMO_SUPPORT_ITEM).delete()
        get_user_model().objects.filter(username__in=DEMO_USERNAMES).delete()

    def upsert_user(self, username, email, password, role, is_active_worker=False):
        User = get_user_model()
        user, _ = User.objects.update_or_create(
            username=username,
            defaults={
                "email": email,
                "is_active": True,
                "is_staff": role in (UserProfile.Role.ADMIN, UserProfile.Role.SUPER_ADMIN),
                "is_superuser": False,
            },
        )
        user.set_password(password)
        user.save()
        UserProfile.objects.update_or_create(
            user=user,
            defaults={
                "role": role,
                "phone": "0400000900",
                "is_active_worker": is_active_worker,
            },
        )
        return user

    def upsert_participants(self):
        records = [
            {
                "ndis_number": "889000001",
                "first_name": "Demo",
                "last_name": "Participant One",
                "phone": "0455 101 001",
                "email": "invoice.demo.participant.1@example.com",
                "address_line_1": "11 Demo Street",
                "suburb": "Brisbane",
                "plan_manager_name": "Demo Plan Manager A",
                "plan_manager_phone": "1300 000 101",
                "plan_manager_email": "claims.demo.a@example.com",
            },
            {
                "ndis_number": "889000002",
                "first_name": "Demo",
                "last_name": "Participant Two",
                "phone": "0455 101 002",
                "email": "invoice.demo.participant.2@example.com",
                "address_line_1": "22 Trial Avenue",
                "suburb": "South Brisbane",
                "plan_manager_name": "Demo Plan Manager B",
                "plan_manager_phone": "1300 000 102",
                "plan_manager_email": "claims.demo.b@example.com",
            },
            {
                "ndis_number": "889000003",
                "first_name": "Demo",
                "last_name": "Participant Three",
                "phone": "0455 101 003",
                "email": "invoice.demo.participant.3@example.com",
                "address_line_1": "33 Sample Road",
                "suburb": "Calamvale",
                "plan_manager_name": "Demo Plan Manager C",
                "plan_manager_phone": "1300 000 103",
                "plan_manager_email": "claims.demo.c@example.com",
            },
        ]
        participants = []
        for record in records:
            participant, _ = Participant.objects.update_or_create(
                ndis_number=record["ndis_number"],
                defaults={
                    **record,
                    "preferred_name": record["first_name"],
                    "date_of_birth": date(1990, 1, 1),
                    "status": Participant.Status.ACTIVE,
                    "state": "QLD",
                    "postcode": "4000",
                    "management_type": Participant.ManagementType.PLAN_MANAGED,
                    "plan_start_date": date(2026, 6, 1),
                    "plan_end_date": date(2027, 5, 31),
                    "worker_visible_notes": "Invoice demo participant only.",
                    "address_access_instructions": "Demo data: no real visit required.",
                    "risk_safety_notes": "No real client data.",
                    "internal_notes": "Created by seed_invoice_demo_data.",
                },
            )
            participants.append(participant)
        return participants

    def upsert_worker(self, user, first_name, last_name, email):
        worker, _ = SupportWorker.objects.update_or_create(
            user=user,
            defaults={
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "phone": "0400 000 900",
                "address": "Invoice demo worker address, Brisbane QLD 4000",
                "employment_type": SupportWorker.EmploymentType.EMPLOYEE,
                "start_date": date(2026, 6, 1),
                "status": SupportWorker.Status.ACTIVE,
                "police_check_status": SupportWorker.ComplianceStatus.CURRENT,
                "police_check_expiry": date(2027, 6, 1),
                "wwcc_status": SupportWorker.ComplianceStatus.CURRENT,
                "wwcc_expiry": date(2027, 6, 1),
                "notes": "Invoice demo worker only.",
            },
        )
        return worker

    def upsert_assignment(self, participant, worker):
        return ParticipantWorkerAssignment.objects.update_or_create(
            participant=participant,
            worker=worker,
            defaults={
                "start_date": date(2026, 6, 1),
                "end_date": None,
                "is_active": True,
                "notes": "Invoice demo assignment.",
            },
        )[0]

    def upsert_support_item(self):
        support_item, _ = SupportItem.objects.update_or_create(
            item_number=DEMO_SUPPORT_ITEM,
            defaults={
                "name": "Invoice demo personal care support",
                "category": "Invoice demo",
                "unit": SupportItem.Unit.HOUR,
                "price_limit": Decimal("65.47"),
                "gst_code": SupportItem.GSTCode.GST_FREE,
                "is_active": True,
                "notes": "For invoice demo testing only.",
            },
        )
        return support_item

    def upsert_shift(self, admin, participant, worker, support_item, record):
        shift, _ = Shift.objects.update_or_create(
            participant=participant,
            worker=worker,
            service_date=record["service_date"],
            start_time=record["start_time"],
            defaults={
                "end_time": record["end_time"],
                "break_minutes": 0,
                "planned_hours": record["hours"],
                "support_item": support_item,
                "service_type": Shift.ServiceType.PERSONAL_CARE,
                "location": "Participant home",
                "address": participant.address_line_1,
                "instructions": "Invoice demo shift.",
                "admin_notes": record["notes"],
                "status": Shift.Status.COMPLETED,
                "completed_at": timezone.now(),
                "created_by": admin,
            },
        )
        return shift

    def upsert_service_log(self, shift, admin, record, status):
        service_log, _ = ServiceLog.objects.update_or_create(
            shift=shift,
            defaults={
                "participant": shift.participant,
                "worker": shift.worker,
                "support_item": shift.support_item,
                "service_date": shift.service_date,
                "actual_start_time": record["start_time"],
                "actual_end_time": record["end_time"],
                "break_minutes": 0,
                "actual_hours": record["hours"],
                "kilometres": Decimal("0.00"),
                "case_notes": record["notes"],
                "worker_notes": "Invoice demo service log.",
                "status": status,
                "reviewed_by": admin,
                "reviewed_at": timezone.now(),
                "rejection_reason": "",
            },
        )
        return service_log

    def upsert_invoiced_record(self, admin, accountant, support_item, record):
        shift = self.upsert_shift(
            admin,
            record["participant"],
            record["worker"],
            support_item,
            record,
        )
        service_log = self.upsert_service_log(
            shift,
            admin,
            record,
            ServiceLog.Status.INVOICED,
        )
        invoice, _ = Invoice.objects.update_or_create(
            invoice_number=record["invoice_number"],
            defaults={
                "participant": record["participant"],
                "period_start": record["service_date"],
                "period_end": record["service_date"],
                "status": record["status"],
                "created_by": accountant,
            },
        )
        InvoiceLine.objects.update_or_create(
            service_log=service_log,
            defaults={
                "invoice": invoice,
                "support_item_number": service_log.support_item.item_number,
                "description": service_log.support_item.name,
                "unit": service_log.support_item.unit,
                "unit_price": service_log.support_item.price_limit,
                "quantity": service_log.actual_hours,
                "gst_code": service_log.support_item.gst_code,
                "line_total": (
                    service_log.actual_hours * service_log.support_item.price_limit
                ).quantize(Decimal("0.01")),
            },
        )
        return invoice

    def upsert_approved_log(self, admin, participant, worker, support_item):
        record = {
            "participant": participant,
            "worker": worker,
            "service_date": date(2026, 6, 24),
            "start_time": time(9, 0),
            "end_time": time(11, 0),
            "hours": Decimal("2.00"),
            "notes": "Approved log waiting to become a demo invoice.",
        }
        shift = self.upsert_shift(admin, participant, worker, support_item, record)
        return self.upsert_service_log(shift, admin, record, ServiceLog.Status.APPROVED)
