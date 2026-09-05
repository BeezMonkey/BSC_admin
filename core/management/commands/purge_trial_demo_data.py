from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

from accounts.models import UserProfile
from coordinators.models import (
    CoordinationLog,
    ParticipantCoordinatorAssignment,
    SupportCoordinator,
)
from core.models import AuditLog
from documents.models import Document
from invoices.models import Invoice
from participants.models import Participant, ParticipantWorkerAssignment
from scheduling.models import Shift, SupportItem
from service_logs.models import ServiceLog
from workers.models import SupportWorker


KNOWN_DEMO_USERNAMES = (
    "beta_worker",
    "beta_accountant",
    "invoice_demo_admin",
    "invoice_demo_accountant",
    "invoice_demo_worker_1",
    "invoice_demo_worker_2",
    "bsc_demo_admin",
)
KNOWN_DEMO_NDIS_NUMBERS = ("990000001",)
KNOWN_DEMO_NDIS_PREFIXES = ("777000", "889000")
KNOWN_DEMO_SUPPORT_ITEMS = ("BETA-TEST-001", "DEMO-INVOICE-001")
KNOWN_DEMO_INVOICE_PREFIXES = ("DEMO-", "DEMO-INV-")
KNOWN_DEMO_PARTICIPANT_NOTES = (
    "Local demo participant.",
    "Second local demo participant.",
    "Created by seed_beta_test_data.",
    "Created by seed_invoice_demo_data.",
    "Created by reset_beta_demo_data.",
)
KNOWN_DEMO_WORKER_NOTES = (
    "Local demo worker.",
    "Beta test worker only.",
    "Invoice demo worker only.",
    "Beta rehearsal worker only.",
)


class Command(BaseCommand):
    help = "Preview or purge known demo/test records before a real trial starts."

    def add_arguments(self, parser):
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Actually delete known demo/test records.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        plan = self.build_purge_plan()

        if not options["confirm"]:
            self.write_plan(plan)
            self.stdout.write(
                self.style.WARNING("Dry run only. Re-run with --confirm to apply.")
            )
            return

        self.delete_records(plan)
        self.stdout.write(self.style.SUCCESS("Trial demo data purged."))

    def build_purge_plan(self):
        initial_demo_users = self.demo_users()
        demo_participants = self.demo_participants()
        demo_workers = self.demo_workers(initial_demo_users)
        demo_coordinators = self.demo_coordinators(initial_demo_users)
        demo_user_ids = set(initial_demo_users.values_list("pk", flat=True))
        demo_user_ids.update(demo_workers.values_list("user_id", flat=True))
        demo_user_ids.update(demo_coordinators.values_list("user_id", flat=True))
        demo_users = get_user_model().objects.filter(pk__in=demo_user_ids).exclude(
            username="admin",
        )
        demo_support_items = self.demo_support_items()
        demo_worker_assignments = (
            ParticipantWorkerAssignment.objects.filter(participant__in=demo_participants)
            | ParticipantWorkerAssignment.objects.filter(worker__in=demo_workers)
        ).distinct()
        demo_coordinator_assignments = (
            ParticipantCoordinatorAssignment.objects.filter(
                participant__in=demo_participants,
            )
            | ParticipantCoordinatorAssignment.objects.filter(
                coordinator__in=demo_coordinators,
            )
        ).distinct()
        demo_shifts = self.demo_shifts(
            demo_participants,
            demo_workers,
            demo_support_items,
        )
        demo_service_logs = self.demo_service_logs(
            demo_participants,
            demo_workers,
            demo_shifts,
            demo_support_items,
        )
        demo_coordination_logs = self.demo_coordination_logs(
            demo_participants,
            demo_coordinators,
        )
        demo_invoices = self.demo_invoices(
            demo_participants,
            demo_service_logs,
            demo_coordination_logs,
        )
        demo_documents = self.demo_documents(
            demo_users,
            demo_participants,
            demo_workers,
            demo_invoices,
            demo_service_logs,
        )
        demo_audit_logs = self.demo_audit_logs(
            demo_users,
            {
                "Participant": demo_participants,
                "SupportWorker": demo_workers,
                "SupportCoordinator": demo_coordinators,
                "ParticipantWorkerAssignment": demo_worker_assignments,
                "ParticipantCoordinatorAssignment": demo_coordinator_assignments,
                "Shift": demo_shifts,
                "ServiceLog": demo_service_logs,
                "CoordinationLog": demo_coordination_logs,
                "Invoice": demo_invoices,
                "Document": demo_documents,
            },
        )
        return {
            "documents": demo_documents,
            "invoices": demo_invoices,
            "service_logs": demo_service_logs,
            "coordination_logs": demo_coordination_logs,
            "shifts": demo_shifts,
            "worker_assignments": demo_worker_assignments,
            "coordinator_assignments": demo_coordinator_assignments,
            "participants": demo_participants,
            "support_workers": demo_workers,
            "support_coordinators": demo_coordinators,
            "support_items": demo_support_items,
            "users": demo_users,
            "audit_logs": demo_audit_logs,
        }

    def write_plan(self, plan):
        self.stdout.write("Trial demo purge preview:")
        for label, queryset in plan.items():
            self.stdout.write(f"- {label}: {queryset.count()}")

    def delete_records(self, plan):
        self.delete_document_files(plan["documents"])
        plan["documents"].delete()
        plan["invoices"].delete()
        plan["service_logs"].delete()
        plan["coordination_logs"].delete()
        plan["shifts"].delete()
        plan["worker_assignments"].delete()
        plan["coordinator_assignments"].delete()
        plan["participants"].delete()
        plan["support_workers"].delete()
        plan["support_coordinators"].delete()
        plan["support_items"].delete()
        plan["audit_logs"].delete()
        self.delete_demo_user_profiles(plan["users"])
        plan["users"].delete()

    def delete_document_files(self, documents):
        for document in documents:
            if document.file:
                document.file.delete(save=False)

    def delete_demo_user_profiles(self, users):
        UserProfile.objects.filter(user__in=users).delete()

    def demo_users(self):
        User = get_user_model()
        return (
            User.objects.filter(username__in=KNOWN_DEMO_USERNAMES)
            | User.objects.filter(username__startswith="bsc_demo_")
            | User.objects.filter(username__startswith="invoice_demo_")
            | User.objects.filter(username__startswith="beta_")
            | User.objects.filter(email__contains=".demo.")
            | User.objects.filter(email__startswith="beta.")
        ).exclude(username="admin").distinct()

    def demo_participants(self):
        queryset = Participant.objects.filter(ndis_number__in=KNOWN_DEMO_NDIS_NUMBERS)
        for prefix in KNOWN_DEMO_NDIS_PREFIXES:
            queryset = queryset | Participant.objects.filter(
                ndis_number__startswith=prefix,
            )
        queryset = (
            queryset
            | Participant.objects.filter(email__contains=".demo.")
            | Participant.objects.filter(email__startswith="beta.")
            | Participant.objects.filter(internal_notes__in=KNOWN_DEMO_PARTICIPANT_NOTES)
        )
        return queryset.distinct()

    def demo_workers(self, demo_users):
        return (
            SupportWorker.objects.filter(user__in=demo_users)
            | SupportWorker.objects.filter(email__contains=".demo.")
            | SupportWorker.objects.filter(email__startswith="beta.")
            | SupportWorker.objects.filter(notes__in=KNOWN_DEMO_WORKER_NOTES)
        ).distinct()

    def demo_coordinators(self, demo_users):
        return (
            SupportCoordinator.objects.filter(user__in=demo_users)
            | SupportCoordinator.objects.filter(email__contains=".demo.")
            | SupportCoordinator.objects.filter(email__startswith="beta.")
        ).distinct()

    def demo_support_items(self):
        queryset = SupportItem.objects.filter(item_number__in=KNOWN_DEMO_SUPPORT_ITEMS)
        queryset = (
            queryset
            | SupportItem.objects.filter(item_number__startswith="BETA-")
            | SupportItem.objects.filter(item_number__startswith="DEMO-")
        )
        return queryset.distinct()

    def demo_shifts(self, demo_participants, demo_workers, demo_support_items):
        return (
            Shift.objects.filter(participant__in=demo_participants)
            | Shift.objects.filter(worker__in=demo_workers)
            | Shift.objects.filter(support_item__in=demo_support_items)
        ).distinct()

    def demo_service_logs(
        self,
        demo_participants,
        demo_workers,
        demo_shifts,
        demo_support_items,
    ):
        return (
            ServiceLog.objects.filter(participant__in=demo_participants)
            | ServiceLog.objects.filter(worker__in=demo_workers)
            | ServiceLog.objects.filter(shift__in=demo_shifts)
            | ServiceLog.objects.filter(support_item__in=demo_support_items)
        ).distinct()

    def demo_coordination_logs(self, demo_participants, demo_coordinators):
        return (
            CoordinationLog.objects.filter(participant__in=demo_participants)
            | CoordinationLog.objects.filter(coordinator__in=demo_coordinators)
        ).distinct()

    def demo_invoices(
        self,
        demo_participants,
        demo_service_logs,
        demo_coordination_logs,
    ):
        queryset = Invoice.objects.filter(participant__in=demo_participants)
        queryset = queryset | Invoice.objects.filter(lines__service_log__in=demo_service_logs)
        queryset = queryset | Invoice.objects.filter(
            lines__coordination_log__in=demo_coordination_logs,
        )
        for prefix in KNOWN_DEMO_INVOICE_PREFIXES:
            queryset = queryset | Invoice.objects.filter(invoice_number__startswith=prefix)
        return queryset.distinct()

    def demo_documents(
        self,
        demo_users,
        demo_participants,
        demo_workers,
        demo_invoices,
        demo_service_logs,
    ):
        return (
            Document.objects.filter(uploaded_by__in=demo_users)
            | Document.objects.filter(participant__in=demo_participants)
            | Document.objects.filter(worker__in=demo_workers)
            | Document.objects.filter(invoice__in=demo_invoices)
            | Document.objects.filter(service_log__in=demo_service_logs)
        ).distinct()

    def demo_audit_logs(self, demo_users, querysets_by_type):
        query = Q(actor__in=demo_users)
        for object_type, queryset in querysets_by_type.items():
            object_ids = [str(pk) for pk in queryset.values_list("pk", flat=True)]
            if object_ids:
                query |= Q(object_type=object_type, object_id__in=object_ids)
        return AuditLog.objects.filter(query).distinct()
