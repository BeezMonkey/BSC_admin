from datetime import date, time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import UserProfile
from documents.models import Document
from invoices.models import Invoice
from participants.models import Participant, ParticipantWorkerAssignment
from scheduling.management.commands.seed_ndis_support_items_2026_27 import (
    SUPPORT_ITEMS,
)
from scheduling.models import Shift, SupportItem
from service_logs.models import ServiceLog
from workers.models import SupportWorker


DEFAULT_PASSWORD = "BetaTest456"
DEMO_WORKER_PREFIX = "bsc_demo_worker_"
DEMO_ADMIN_USERNAME = "bsc_demo_admin"
DEMO_NDIS_PREFIX = "777000"
LEGACY_USERNAMES = (
    "beta_worker",
    "beta_accountant",
    "invoice_demo_admin",
    "invoice_demo_accountant",
    "invoice_demo_worker_1",
    "invoice_demo_worker_2",
)
LEGACY_NDIS_NUMBERS = ("990000001",)
LEGACY_NDIS_PREFIXES = ("889000",)
LEGACY_SUPPORT_ITEMS = ("BETA-TEST-001", "DEMO-INVOICE-001")
LEGACY_INVOICE_PREFIXES = ("DEMO-INV-",)


PARTICIPANT_RECORDS = (
    {
        "number": 1,
        "first_name": "Demo",
        "last_name": "Participant One",
        "suburb": "Brisbane",
        "plan_manager_name": "Demo Plan Manager A",
        "plan_manager_email": "claims.demo.a@example.com",
    },
    {
        "number": 2,
        "first_name": "Demo",
        "last_name": "Participant Two",
        "suburb": "South Brisbane",
        "plan_manager_name": "Demo Plan Manager B",
        "plan_manager_email": "claims.demo.b@example.com",
    },
    {
        "number": 3,
        "first_name": "Demo",
        "last_name": "Participant Three",
        "suburb": "Calamvale",
        "plan_manager_name": "Demo Plan Manager C",
        "plan_manager_email": "claims.demo.c@example.com",
    },
    {
        "number": 4,
        "first_name": "Demo",
        "last_name": "Participant Four",
        "suburb": "Sunnybank",
        "plan_manager_name": "Demo Plan Manager D",
        "plan_manager_email": "claims.demo.d@example.com",
    },
    {
        "number": 5,
        "first_name": "Demo",
        "last_name": "Participant Five",
        "suburb": "Logan",
        "plan_manager_name": "Demo Plan Manager E",
        "plan_manager_email": "claims.demo.e@example.com",
    },
)


class Command(BaseCommand):
    help = "Safely preview or reset beta demo records for end-to-end trial workflows."

    def add_arguments(self, parser):
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Actually delete known beta/demo records and rebuild the 5-by-5 trial set.",
        )
        parser.add_argument(
            "--password",
            default=DEFAULT_PASSWORD,
            help="Password for generated beta worker accounts.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        plan = self.build_reset_plan()

        if not options["confirm"]:
            self.write_plan(plan)
            self.stdout.write(
                self.style.WARNING("Dry run only. Re-run with --confirm to apply.")
            )
            return

        self.delete_demo_records(plan)
        admin = self.get_created_by_user(options["password"])
        self.upsert_official_support_items()
        support_item = SupportItem.objects.get(item_number="01_011_0107_1_1")
        participants = self.create_participants()
        workers = self.create_workers(options["password"])
        for index, participant in enumerate(participants):
            worker = workers[index]
            self.create_assignment(participant, worker)
            self.create_shift(admin, participant, worker, support_item, index)

        self.stdout.write(self.style.SUCCESS("Beta demo data reset complete."))
        self.stdout.write(f"Worker password: {options['password']}")
        for worker_user in get_user_model().objects.filter(
            username__startswith=DEMO_WORKER_PREFIX,
        ).order_by("username"):
            self.stdout.write(f"Worker login: {worker_user.username} / {options['password']}")

    def build_reset_plan(self):
        demo_users = self.demo_users()
        demo_participants = self.demo_participants()
        demo_workers = self.demo_workers(demo_users)
        demo_shifts = self.demo_shifts(demo_participants, demo_workers)
        demo_logs = self.demo_logs(demo_participants, demo_workers, demo_shifts)
        demo_invoices = self.demo_invoices(demo_participants)
        return {
            "users": demo_users,
            "participants": demo_participants,
            "workers": demo_workers,
            "assignments": ParticipantWorkerAssignment.objects.filter(
                participant__in=demo_participants,
            )
            | ParticipantWorkerAssignment.objects.filter(worker__in=demo_workers),
            "shifts": demo_shifts,
            "service_logs": demo_logs,
            "invoices": demo_invoices,
            "documents": self.demo_documents(
                demo_users,
                demo_participants,
                demo_workers,
                demo_invoices,
                demo_logs,
            ),
            "support_items": SupportItem.objects.filter(item_number__in=LEGACY_SUPPORT_ITEMS),
        }

    def write_plan(self, plan):
        self.stdout.write("Beta demo reset preview:")
        for label, queryset in plan.items():
            self.stdout.write(f"- {label}: {queryset.count()}")
        self.stdout.write("- create participants: 5")
        self.stdout.write("- create support workers: 5")
        self.stdout.write("- create active assignments: 5")
        self.stdout.write("- create published shifts: 5")

    def delete_demo_records(self, plan):
        plan["documents"].delete()
        plan["invoices"].delete()
        plan["service_logs"].delete()
        plan["shifts"].delete()
        plan["assignments"].delete()
        plan["participants"].delete()
        plan["workers"].delete()
        plan["support_items"].delete()
        plan["users"].delete()

    def demo_users(self):
        User = get_user_model()
        return User.objects.filter(username__in=LEGACY_USERNAMES) | User.objects.filter(
            username__startswith=DEMO_WORKER_PREFIX,
        ) | User.objects.filter(username=DEMO_ADMIN_USERNAME)

    def demo_participants(self):
        queryset = Participant.objects.filter(ndis_number__startswith=DEMO_NDIS_PREFIX)
        for ndis_number in LEGACY_NDIS_NUMBERS:
            queryset = queryset | Participant.objects.filter(ndis_number=ndis_number)
        for prefix in LEGACY_NDIS_PREFIXES:
            queryset = queryset | Participant.objects.filter(ndis_number__startswith=prefix)
        return queryset

    def demo_workers(self, demo_users):
        return SupportWorker.objects.filter(user__in=demo_users) | SupportWorker.objects.filter(
            email__startswith="bsc.demo.worker",
        )

    def demo_shifts(self, demo_participants, demo_workers):
        return Shift.objects.filter(participant__in=demo_participants) | Shift.objects.filter(
            worker__in=demo_workers,
        )

    def demo_logs(self, demo_participants, demo_workers, demo_shifts):
        return (
            ServiceLog.objects.filter(participant__in=demo_participants)
            | ServiceLog.objects.filter(worker__in=demo_workers)
            | ServiceLog.objects.filter(shift__in=demo_shifts)
        )

    def demo_invoices(self, demo_participants):
        queryset = Invoice.objects.filter(participant__in=demo_participants)
        for prefix in LEGACY_INVOICE_PREFIXES:
            queryset = queryset | Invoice.objects.filter(invoice_number__startswith=prefix)
        return queryset

    def demo_documents(
        self,
        demo_users,
        demo_participants,
        demo_workers,
        demo_invoices,
        demo_logs,
    ):
        return (
            Document.objects.filter(uploaded_by__in=demo_users)
            | Document.objects.filter(participant__in=demo_participants)
            | Document.objects.filter(worker__in=demo_workers)
            | Document.objects.filter(invoice__in=demo_invoices)
            | Document.objects.filter(service_log__in=demo_logs)
        )

    def get_created_by_user(self, password):
        admin_profile = UserProfile.objects.filter(
            role__in=(UserProfile.Role.ADMIN, UserProfile.Role.SUPER_ADMIN),
            user__is_active=True,
        ).select_related("user").first()
        if admin_profile:
            return admin_profile.user

        User = get_user_model()
        user, _ = User.objects.update_or_create(
            username=DEMO_ADMIN_USERNAME,
            defaults={
                "email": "bsc.demo.admin@example.com",
                "is_active": True,
                "is_staff": True,
                "is_superuser": False,
            },
        )
        user.set_password(password)
        user.save()
        UserProfile.objects.update_or_create(
            user=user,
            defaults={"role": UserProfile.Role.ADMIN, "is_active_worker": False},
        )
        return user

    def upsert_official_support_items(self):
        for item_data in SUPPORT_ITEMS:
            SupportItem.objects.update_or_create(
                item_number=item_data["item_number"],
                defaults=item_data,
            )

    def create_participants(self):
        participants = []
        for record in PARTICIPANT_RECORDS:
            number = record["number"]
            participant, _ = Participant.objects.update_or_create(
                ndis_number=f"{DEMO_NDIS_PREFIX}{number:03d}",
                defaults={
                    "first_name": record["first_name"],
                    "last_name": record["last_name"],
                    "preferred_name": f"Demo {number}",
                    "date_of_birth": date(1990, number, 1),
                    "status": Participant.Status.ACTIVE,
                    "phone": f"0455 70{number:02d} 00{number}",
                    "email": f"bsc.demo.participant.{number}@example.com",
                    "address_line_1": f"{number} Demo Street",
                    "suburb": record["suburb"],
                    "state": "QLD",
                    "postcode": "4000",
                    "emergency_contact_name": f"Demo Contact {number}",
                    "emergency_contact_relationship": "Family",
                    "emergency_contact_phone": f"0455 80{number:02d} 00{number}",
                    "management_type": Participant.ManagementType.PLAN_MANAGED,
                    "plan_start_date": date(2026, 8, 1),
                    "plan_end_date": date(2027, 7, 31),
                    "plan_manager_name": record["plan_manager_name"],
                    "plan_manager_email": record["plan_manager_email"],
                    "plan_manager_phone": f"1300 000 10{number}",
                    "support_coordinator_name": f"Demo Coordinator {number}",
                    "support_coordinator_email": f"coordinator.demo.{number}@example.com",
                    "worker_visible_notes": "Beta rehearsal participant only.",
                    "address_access_instructions": "Demo data: no real visit required.",
                    "risk_safety_notes": "No real client data.",
                    "internal_notes": "Created by reset_beta_demo_data.",
                },
            )
            participants.append(participant)
        return participants

    def create_workers(self, password):
        workers = []
        User = get_user_model()
        for index in range(1, 6):
            user, _ = User.objects.update_or_create(
                username=f"{DEMO_WORKER_PREFIX}{index}",
                defaults={
                    "email": f"bsc.demo.worker.{index}@example.com",
                    "is_active": True,
                    "is_staff": False,
                    "is_superuser": False,
                },
            )
            user.set_password(password)
            user.save()
            UserProfile.objects.update_or_create(
                user=user,
                defaults={
                    "role": UserProfile.Role.SUPPORT_WORKER,
                    "phone": f"0400 20{index:02d} 00{index}",
                    "is_active_worker": True,
                },
            )
            worker, _ = SupportWorker.objects.update_or_create(
                user=user,
                defaults={
                    "first_name": "Demo",
                    "last_name": f"Worker {index}",
                    "email": f"bsc.demo.worker.{index}@example.com",
                    "phone": f"0400 30{index:02d} 00{index}",
                    "address": f"{index} Worker Street, Brisbane QLD 4000",
                    "employment_type": SupportWorker.EmploymentType.EMPLOYEE,
                    "start_date": date(2026, 8, 1),
                    "status": SupportWorker.Status.ACTIVE,
                    "police_check_status": SupportWorker.ComplianceStatus.CURRENT,
                    "police_check_expiry": date(2027, 8, 1),
                    "wwcc_status": SupportWorker.ComplianceStatus.CURRENT,
                    "wwcc_expiry": date(2027, 8, 1),
                    "notes": "Beta rehearsal worker only.",
                },
            )
            workers.append(worker)
        return workers

    def create_assignment(self, participant, worker):
        return ParticipantWorkerAssignment.objects.update_or_create(
            participant=participant,
            worker=worker,
            defaults={
                "start_date": date(2026, 8, 1),
                "end_date": None,
                "is_active": True,
                "notes": "Beta rehearsal assignment.",
            },
        )[0]

    def create_shift(self, admin, participant, worker, support_item, index):
        start_date = date(2026, 8, 24)
        service_date = date.fromordinal(start_date.toordinal() + index)
        shift, _ = Shift.objects.update_or_create(
            participant=participant,
            worker=worker,
            service_date=service_date,
            start_time=time(9, 0),
            defaults={
                "end_time": time(12, 0),
                "break_minutes": 0,
                "planned_hours": Decimal("3.00"),
                "support_item": support_item,
                "service_type": Shift.ServiceType.PERSONAL_CARE,
                "location": "Participant home",
                "address": f"{participant.address_line_1}, {participant.suburb} QLD {participant.postcode}",
                "instructions": "Beta rehearsal shift. Complete and submit a service log.",
                "admin_notes": "Created by reset_beta_demo_data.",
                "status": Shift.Status.PUBLISHED,
                "created_by": admin,
            },
        )
        return shift
