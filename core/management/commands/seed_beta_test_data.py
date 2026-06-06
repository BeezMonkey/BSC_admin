from datetime import date, time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import UserProfile
from participants.models import Participant, ParticipantWorkerAssignment
from scheduling.models import Shift, SupportItem
from workers.models import SupportWorker


DEFAULT_PASSWORD = "BetaTest456"


class Command(BaseCommand):
    help = "Create safe beta test records without changing the owner admin account."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            default=DEFAULT_PASSWORD,
            help="Password for generated beta worker and accountant accounts.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        password = options["password"]
        worker_user = self.upsert_user(
            username="beta_worker",
            email="beta.worker@example.com",
            password=password,
            role=UserProfile.Role.SUPPORT_WORKER,
            is_active_worker=True,
        )
        accountant = self.upsert_user(
            username="beta_accountant",
            email="beta.accountant@example.com",
            password=password,
            role=UserProfile.Role.ACCOUNTANT,
        )
        participant = self.upsert_participant()
        worker = self.upsert_worker(worker_user)
        assignment = self.upsert_assignment(participant, worker)
        support_item = self.upsert_support_item()
        shift = self.upsert_shift(accountant, participant, worker, support_item)

        self.stdout.write(self.style.SUCCESS("Beta test data ready."))
        self.stdout.write(f"Worker login: beta_worker / {password}")
        self.stdout.write(f"Accountant login: beta_accountant / {password}")
        self.stdout.write(f"Participant: {participant.display_name}")
        self.stdout.write(f"Worker: {worker.display_name}")
        self.stdout.write(f"Assignment: {assignment}")
        self.stdout.write(f"Shift: {shift}")

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
                "phone": "0400000100",
                "is_active_worker": is_active_worker,
            },
        )
        return user

    def upsert_participant(self):
        participant, _ = Participant.objects.update_or_create(
            ndis_number="990000001",
            defaults={
                "first_name": "Beta",
                "last_name": "Participant",
                "preferred_name": "Beta",
                "date_of_birth": date(1990, 6, 1),
                "status": Participant.Status.ACTIVE,
                "phone": "0400000200",
                "email": "beta.participant@example.com",
                "address_line_1": "10 Test Street",
                "suburb": "Brisbane",
                "state": "QLD",
                "postcode": "4000",
                "emergency_contact_name": "Beta Contact",
                "emergency_contact_relationship": "Friend",
                "emergency_contact_phone": "0400000201",
                "management_type": Participant.ManagementType.PLAN_MANAGED,
                "plan_start_date": date(2026, 6, 1),
                "plan_end_date": date(2027, 5, 31),
                "plan_manager_name": "Beta Plan Manager",
                "plan_manager_email": "beta.plan.manager@example.com",
                "support_coordinator_name": "Beta Coordinator",
                "support_coordinator_email": "beta.coordinator@example.com",
                "worker_visible_notes": "Beta test participant only.",
                "address_access_instructions": "Use front entrance.",
                "risk_safety_notes": "No real client data.",
                "internal_notes": "Created by seed_beta_test_data.",
            },
        )
        return participant

    def upsert_worker(self, user):
        worker, _ = SupportWorker.objects.update_or_create(
            user=user,
            defaults={
                "first_name": "Beta",
                "last_name": "Worker",
                "email": "beta.worker@example.com",
                "phone": "0400000300",
                "address": "20 Test Avenue, Brisbane QLD 4000",
                "employment_type": SupportWorker.EmploymentType.EMPLOYEE,
                "start_date": date(2026, 6, 1),
                "status": SupportWorker.Status.ACTIVE,
                "police_check_status": SupportWorker.ComplianceStatus.CURRENT,
                "police_check_expiry": date(2027, 6, 1),
                "wwcc_status": SupportWorker.ComplianceStatus.CURRENT,
                "wwcc_expiry": date(2027, 6, 1),
                "notes": "Beta test worker only.",
            },
        )
        return worker

    def upsert_assignment(self, participant, worker):
        assignment, _ = ParticipantWorkerAssignment.objects.update_or_create(
            participant=participant,
            worker=worker,
            defaults={
                "start_date": date(2026, 6, 1),
                "end_date": None,
                "is_active": True,
                "notes": "Beta test assignment.",
            },
        )
        return assignment

    def upsert_support_item(self):
        support_item, _ = SupportItem.objects.update_or_create(
            item_number="BETA-TEST-001",
            defaults={
                "name": "Beta test personal care support",
                "category": "Beta testing",
                "unit": SupportItem.Unit.HOUR,
                "price_limit": Decimal("65.47"),
                "gst_code": SupportItem.GSTCode.GST_FREE,
                "is_active": True,
                "notes": "For beta workflow testing only.",
            },
        )
        return support_item

    def upsert_shift(self, created_by, participant, worker, support_item):
        shift, _ = Shift.objects.update_or_create(
            participant=participant,
            worker=worker,
            service_date=date(2026, 6, 8),
            start_time=time(9, 0),
            defaults={
                "end_time": time(11, 0),
                "break_minutes": 0,
                "planned_hours": Decimal("2.00"),
                "support_item": support_item,
                "service_type": Shift.ServiceType.PERSONAL_CARE,
                "location": "Participant home",
                "address": "10 Test Street, Brisbane QLD 4000",
                "instructions": "Use front entrance.",
                "admin_notes": "Beta test shift.",
                "status": Shift.Status.PUBLISHED,
                "created_by": created_by,
            },
        )
        return shift
