from django.shortcuts import get_object_or_404, render

from accounts.decorators import admin_required, worker_required
from invoices.models import Invoice
from scheduling.models import Shift
from service_logs.models import ServiceLog

from .models import AuditLog


@admin_required
def admin_dashboard(request):
    operations_summary = {
        "draft_shift_count": Shift.objects.filter(status=Shift.Status.DRAFT).count(),
        "submitted_log_count": ServiceLog.objects.filter(
            status=ServiceLog.Status.SUBMITTED,
        ).count(),
        "approved_log_count": ServiceLog.objects.filter(
            status=ServiceLog.Status.APPROVED,
            invoice_line__isnull=True,
        ).count(),
        "draft_invoice_count": Invoice.objects.filter(status=Invoice.Status.DRAFT).count(),
        "issued_invoice_count": Invoice.objects.filter(status=Invoice.Status.ISSUED).count(),
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
