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


DEMO_PASSWORD = "BscTest123!"


class Command(BaseCommand):
    help = "Create or update local demo data for V1 trial use."

    @transaction.atomic
    def handle(self, *args, **options):
        self.verbosity = options.get("verbosity", 1)
        admin = self.upsert_user("admin", "admin@example.com", UserProfile.Role.ADMIN)
        worker_user = self.upsert_user(
            "worker",
            "worker@example.com",
            UserProfile.Role.SUPPORT_WORKER,
            is_active_worker=True,
        )
        accountant = self.upsert_user(
            "accountant",
            "accountant@example.com",
            UserProfile.Role.ACCOUNTANT,
        )

        participant = self.upsert_participant()
        second_participant = self.upsert_second_participant()
        worker = self.upsert_worker(worker_user)
        assignment = self.upsert_assignment(participant, worker)
        second_assignment = self.upsert_second_assignment(second_participant, worker)
        support_item = self.upsert_support_item()
        shift = self.upsert_shift(admin, participant, worker, support_item)
        second_shift = self.upsert_second_shift(
            admin,
            second_participant,
            worker,
            support_item,
        )
        service_log = self.upsert_service_log(shift, admin)
        second_service_log = self.upsert_second_service_log(second_shift, admin)
        invoice = self.upsert_invoice(accountant, participant, service_log)
        second_invoice = self.upsert_second_invoice(
            accountant,
            second_participant,
            second_service_log,
        )

        if self.verbosity:
            self.stdout.write(
                self.style.SUCCESS(
                    "Demo data ready: "
                    "admin, worker, accountant, participant, worker profile, "
                    "assignment, support item, shift, service log, and invoice."
                )
            )
            self.stdout.write(f"Admin login: admin / {DEMO_PASSWORD}")
            self.stdout.write(f"Worker login: worker / {DEMO_PASSWORD}")
            self.stdout.write(f"Accountant login: accountant / {DEMO_PASSWORD}")
            self.stdout.write(f"Participant: {participant.display_name}")
            self.stdout.write(f"Second participant: {second_participant.display_name}")
            self.stdout.write(f"Worker: {worker.display_name}")
            self.stdout.write(f"Assignment: {assignment}")
            self.stdout.write(f"Second assignment: {second_assignment}")
            self.stdout.write(f"Invoice: {invoice.invoice_number}")
            self.stdout.write(f"Second invoice: {second_invoice.invoice_number}")

    def upsert_user(self, username, email, role, is_active_worker=False):
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
        user.set_password(DEMO_PASSWORD)
        user.save()
        UserProfile.objects.update_or_create(
            user=user,
            defaults={
                "role": role,
                "phone": "0400000000",
                "is_active_worker": is_active_worker,
            },
        )
        return user

    def upsert_participant(self):
        participant, _ = Participant.objects.update_or_create(
            ndis_number="430000001",
            defaults={
                "first_name": "Ava",
                "last_name": "Nguyen",
                "preferred_name": "Ava",
                "date_of_birth": date(1992, 4, 12),
                "status": Participant.Status.ACTIVE,
                "phone": "0730000001",
                "email": "ava.nguyen@example.com",
                "address_line_1": "10 Creek Street",
                "suburb": "Brisbane",
                "state": "QLD",
                "postcode": "4000",
                "emergency_contact_name": "Linh Nguyen",
                "emergency_contact_relationship": "Sister",
                "emergency_contact_phone": "0730000002",
                "management_type": Participant.ManagementType.PLAN_MANAGED,
                "plan_start_date": date(2026, 1, 1),
                "plan_end_date": date(2026, 12, 31),
                "worker_visible_notes": "Prefers morning appointments.",
                "address_access_instructions": "Use side entrance.",
                "risk_safety_notes": "No known safety alerts for demo data.",
                "internal_notes": "Local demo participant.",
            },
        )
        return participant

    def upsert_second_participant(self):
        participant, _ = Participant.objects.update_or_create(
            ndis_number="430000002",
            defaults={
                "first_name": "Ben",
                "last_name": "Taylor",
                "preferred_name": "Ben",
                "date_of_birth": date(1987, 9, 3),
                "status": Participant.Status.ACTIVE,
                "phone": "0730000003",
                "email": "ben.taylor@example.com",
                "address_line_1": "22 Garden Road",
                "suburb": "South Brisbane",
                "state": "QLD",
                "postcode": "4101",
                "emergency_contact_name": "Mia Taylor",
                "emergency_contact_relationship": "Partner",
                "emergency_contact_phone": "0730000004",
                "management_type": Participant.ManagementType.PLAN_MANAGED,
                "plan_start_date": date(2026, 2, 1),
                "plan_end_date": date(2027, 1, 31),
                "worker_visible_notes": "Enjoys community access activities.",
                "address_access_instructions": "Call on arrival.",
                "risk_safety_notes": "No known safety alerts for demo data.",
                "internal_notes": "Second local demo participant.",
            },
        )
        return participant

    def upsert_worker(self, user):
        worker, _ = SupportWorker.objects.update_or_create(
            user=user,
            defaults={
                "first_name": "Wendy",
                "last_name": "Worker",
                "email": "worker@example.com",
                "phone": "0400000001",
                "address": "20 River Street, Brisbane QLD 4000",
                "employment_type": SupportWorker.EmploymentType.EMPLOYEE,
                "status": SupportWorker.Status.ACTIVE,
                "police_check_status": SupportWorker.ComplianceStatus.CURRENT,
                "police_check_expiry": date(2027, 6, 30),
                "wwcc_status": SupportWorker.ComplianceStatus.CURRENT,
                "wwcc_expiry": date(2027, 6, 30),
                "notes": "Local demo worker.",
            },
        )
        return worker

    def upsert_assignment(self, participant, worker):
        assignment, _ = ParticipantWorkerAssignment.objects.update_or_create(
            participant=participant,
            worker=worker,
            is_active=True,
            defaults={
                "start_date": date(2026, 1, 1),
                "end_date": None,
                "notes": "Demo assignment for local trial.",
            },
        )
        return assignment

    def upsert_second_assignment(self, participant, worker):
        assignment, _ = ParticipantWorkerAssignment.objects.update_or_create(
            participant=participant,
            worker=worker,
            is_active=True,
            defaults={
                "start_date": date(2026, 2, 1),
                "end_date": None,
                "notes": "Second demo assignment for local trial.",
            },
        )
        return assignment

    def upsert_support_item(self):
        support_item, _ = SupportItem.objects.update_or_create(
            item_number="01_011_0107_1_1",
            defaults={
                "name": "Assistance with self-care activities",
                "category": "Core supports",
                "unit": SupportItem.Unit.HOUR,
                "price_limit": Decimal("65.47"),
                "gst_code": SupportItem.GSTCode.GST_FREE,
                "is_active": True,
                "notes": "Local demo support item.",
            },
        )
        return support_item

    def upsert_shift(self, admin, participant, worker, support_item):
        shift, _ = Shift.objects.update_or_create(
            participant=participant,
            worker=worker,
            service_date=date(2026, 6, 1),
            start_time=time(9, 0),
            defaults={
                "end_time": time(11, 30),
                "break_minutes": 30,
                "planned_hours": Decimal("2.00"),
                "support_item": support_item,
                "service_type": Shift.ServiceType.PERSONAL_CARE,
                "location": "Participant home",
                "address": "10 Creek Street, Brisbane QLD 4000",
                "instructions": "Use side entrance.",
                "admin_notes": "Local demo shift.",
                "status": Shift.Status.COMPLETED,
                "completed_at": timezone.now(),
                "created_by": admin,
            },
        )
        return shift

    def upsert_second_shift(self, admin, participant, worker, support_item):
        shift, _ = Shift.objects.update_or_create(
            participant=participant,
            worker=worker,
            service_date=date(2026, 6, 2),
            start_time=time(13, 0),
            defaults={
                "end_time": time(15, 0),
                "break_minutes": 0,
                "planned_hours": Decimal("2.00"),
                "support_item": support_item,
                "service_type": Shift.ServiceType.COMMUNITY_ACCESS,
                "location": "Community centre",
                "address": "50 Stanley Street, South Brisbane QLD 4101",
                "instructions": "Meet participant at front reception.",
                "admin_notes": "Second local demo shift.",
                "status": Shift.Status.COMPLETED,
                "completed_at": timezone.now(),
                "created_by": admin,
            },
        )
        return shift

    def upsert_service_log(self, shift, admin):
        service_log, _ = ServiceLog.objects.update_or_create(
            shift=shift,
            defaults={
                "participant": shift.participant,
                "worker": shift.worker,
                "support_item": shift.support_item,
                "service_date": shift.service_date,
                "actual_start_time": time(9, 0),
                "actual_end_time": time(11, 30),
                "break_minutes": 30,
                "actual_hours": Decimal("2.00"),
                "kilometres": Decimal("4.50"),
                "case_notes": "Supported participant with morning personal care routine.",
                "worker_notes": "Demo service log for local trial.",
                "status": ServiceLog.Status.INVOICED,
                "reviewed_by": admin,
                "reviewed_at": timezone.now(),
                "rejection_reason": "",
            },
        )
        return service_log

    def upsert_second_service_log(self, shift, admin):
        service_log, _ = ServiceLog.objects.update_or_create(
            shift=shift,
            defaults={
                "participant": shift.participant,
                "worker": shift.worker,
                "support_item": shift.support_item,
                "service_date": shift.service_date,
                "actual_start_time": time(13, 0),
                "actual_end_time": time(15, 0),
                "break_minutes": 0,
                "actual_hours": Decimal("2.00"),
                "kilometres": Decimal("8.00"),
                "case_notes": "Supported participant with community access activity.",
                "worker_notes": "Second demo service log for local trial.",
                "status": ServiceLog.Status.INVOICED,
                "reviewed_by": admin,
                "reviewed_at": timezone.now(),
                "rejection_reason": "",
            },
        )
        return service_log

    def upsert_invoice(self, accountant, participant, service_log):
        invoice, _ = Invoice.objects.update_or_create(
            invoice_number="DEMO-202606-0001",
            defaults={
                "participant": participant,
                "period_start": date(2026, 6, 1),
                "period_end": date(2026, 6, 30),
                "status": Invoice.Status.DRAFT,
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
                "line_total": (service_log.actual_hours * service_log.support_item.price_limit).quantize(
                    Decimal("0.01"),
                ),
            },
        )
        return invoice

    def upsert_second_invoice(self, accountant, participant, service_log):
        invoice, _ = Invoice.objects.update_or_create(
            invoice_number="DEMO-202606-0002",
            defaults={
                "participant": participant,
                "period_start": date(2026, 6, 1),
                "period_end": date(2026, 6, 30),
                "status": Invoice.Status.DRAFT,
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
                "line_total": (service_log.actual_hours * service_log.support_item.price_limit).quantize(
                    Decimal("0.01"),
                ),
            },
        )
        return invoice
