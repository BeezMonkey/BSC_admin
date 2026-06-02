from django.shortcuts import get_object_or_404, render

from accounts.decorators import admin_required, worker_required
from invoices.models import Invoice
from scheduling.models import Shift
from service_logs.models import ServiceLog

from .models import AuditLog


def count_label(count, singular, plural=None):
    label = singular if count == 1 else (plural or f"{singular}s")
    return f"{count} {label}"


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
    return render(
        request,
        "core/admin_dashboard.html",
        {"operations_summary": operations_summary},
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
