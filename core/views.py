from django.shortcuts import get_object_or_404, render

from accounts.decorators import admin_required, worker_required
from invoices.models import Invoice
from participants.models import Participant, ParticipantWorkerAssignment
from scheduling.models import Shift
from service_logs.models import ServiceLog

from .models import AuditLog


def count_label(count, singular, plural=None):
    label = singular if count == 1 else (plural or f"{singular}s")
    return f"{count} {label}"


def checklist_count_label(count, singular, plural=None):
    if count == 0:
        return f"No {plural or f'{singular}s'} yet"
    return count_label(count, singular, plural)


@admin_required
def admin_dashboard(request):
    draft_shift_count = Shift.objects.filter(status=Shift.Status.DRAFT).count()
    submitted_log_count = ServiceLog.objects.filter(
        status=ServiceLog.Status.SUBMITTED,
    ).count()
    approved_log_count = ServiceLog.objects.filter(
        status=ServiceLog.Status.APPROVED,
        invoice_line__isnull=True,
    ).count()
    draft_invoice_count = Invoice.objects.filter(status=Invoice.Status.DRAFT).count()
    issued_invoice_count = Invoice.objects.filter(status=Invoice.Status.ISSUED).count()
    operations_summary = {
        "draft_shift_label": count_label(draft_shift_count, "draft shift"),
        "submitted_log_label": count_label(submitted_log_count, "submitted log"),
        "approved_log_label": count_label(approved_log_count, "approved log"),
        "draft_invoice_label": count_label(draft_invoice_count, "draft invoice"),
        "issued_invoice_label": count_label(issued_invoice_count, "issued invoice"),
        "has_actions": any(
            [
                draft_shift_count,
                submitted_log_count,
                approved_log_count,
                draft_invoice_count,
                issued_invoice_count,
            ]
        ),
    }
    workflow_checklist = [
        {
            "label": "Add participant",
            "detail": checklist_count_label(Participant.objects.count(), "participant"),
            "description": "Create the client record before scheduling support.",
            "url_name": "participant_create",
        },
        {
            "label": "Assign worker",
            "detail": checklist_count_label(
                ParticipantWorkerAssignment.objects.filter(is_active=True).count(),
                "active assignment",
            ),
            "description": "Connect participants with the workers who can support them.",
            "url_name": "participant_list",
        },
        {
            "label": "Create roster shift",
            "detail": checklist_count_label(Shift.objects.count(), "shift"),
            "description": "Add one-off or recurring shifts for confirmed services.",
            "url_name": "shift_create",
        },
        {
            "label": "Worker submits service log",
            "detail": checklist_count_label(
                Shift.objects.filter(status=Shift.Status.CONFIRMED).count(),
                "confirmed shift",
            ),
            "description": "Track shifts that are ready for worker notes.",
            "url_name": "roster_list",
            "query": f"status={Shift.Status.CONFIRMED}",
        },
        {
            "label": "Approve service log",
            "detail": checklist_count_label(submitted_log_count, "submitted log"),
            "description": "Review notes, hours, and support details before billing.",
            "url_name": "service_log_list",
            "query": f"status={ServiceLog.Status.SUBMITTED}",
        },
        {
            "label": "Create invoice",
            "detail": checklist_count_label(approved_log_count, "approved log"),
            "description": "Convert approved, uninvoiced logs into participant invoices.",
            "url_name": "invoice_create",
        },
    ]
    return render(
        request,
        "core/admin_dashboard.html",
        {
            "operations_summary": operations_summary,
            "workflow_checklist": workflow_checklist,
        },
    )


@worker_required
def worker_dashboard(request):
    worker = getattr(request.user, "supportworker", None)
    if worker is None:
        shift_counts = {
            "needs_attention_count": 0,
            "ready_for_log_count": 0,
            "completed_shift_count": 0,
        }
    else:
        worker_shifts = Shift.objects.filter(worker=worker)
        shift_counts = {
            "needs_attention_count": worker_shifts.filter(status=Shift.Status.PUBLISHED).count(),
            "ready_for_log_count": worker_shifts.filter(status=Shift.Status.CONFIRMED).count(),
            "completed_shift_count": worker_shifts.filter(
                status__in=[
                    Shift.Status.COMPLETED,
                    Shift.Status.CANCELLED,
                    Shift.Status.NO_SHOW,
                ]
            ).count(),
        }
    shift_counts["has_shift_actions"] = any(
        [
            shift_counts["needs_attention_count"],
            shift_counts["ready_for_log_count"],
            shift_counts["completed_shift_count"],
        ]
    )

    return render(request, "core/worker_dashboard.html", shift_counts)


@admin_required
def audit_log_list(request):
    audit_logs = AuditLog.objects.select_related("actor")
    return render(request, "core/audit_log_list.html", {"audit_logs": audit_logs})


@admin_required
def audit_log_detail(request, audit_log_id):
    audit_log = get_object_or_404(AuditLog.objects.select_related("actor"), id=audit_log_id)
    return render(request, "core/audit_log_detail.html", {"audit_log": audit_log})

# Create your views here.
