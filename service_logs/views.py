from django.contrib import messages
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.decorators import admin_required, worker_required
from core.audit import write_audit_log
from core.models import AuditLog
from core.navigation import get_safe_return_url
from core.pagination import paginate_queryset
from core.sorting import apply_sorting
from scheduling.models import Shift

from .forms import ServiceLogForm
from .models import ServiceLog


@admin_required
def service_log_list(request):
    service_logs = ServiceLog.objects.select_related(
        "shift",
        "participant",
        "worker",
        "support_item",
    )
    status = request.GET.get("status", "").strip()
    has_filters = bool(status)
    if status:
        service_logs = service_logs.filter(status=status)
    status_label = dict(ServiceLog.Status.choices).get(status)
    filter_summary = f"Showing {status_label.lower()} service logs." if status_label else ""
    service_logs, sorting = apply_sorting(
        request,
        service_logs,
        {
            "date": ("service_date", "id"),
            "participant": ("participant__last_name", "participant__first_name", "service_date"),
            "worker": ("worker__last_name", "worker__first_name", "service_date"),
            "status": ("status", "service_date"),
        },
    )
    service_logs, pagination = paginate_queryset(request, service_logs)
    return render(
        request,
        "service_logs/service_log_list.html",
        {
            "service_logs": service_logs,
            "pagination": pagination,
            "sorting": sorting,
            "status": status,
            "has_filters": has_filters,
            "status_choices": ServiceLog.Status.choices,
            "filter_summary": filter_summary,
            "current_list_url": request.get_full_path(),
        },
    )


@admin_required
def service_log_detail(request, service_log_id):
    service_log = get_object_or_404(
        ServiceLog.objects.select_related(
            "shift",
            "participant",
            "worker",
            "support_item",
        ),
        id=service_log_id,
    )
    return render(
        request,
        "service_logs/service_log_detail.html",
        {
            "service_log": service_log,
            "return_url": get_safe_return_url(request, reverse("service_log_list")),
        },
    )


@admin_required
@require_POST
def service_log_approve(request, service_log_id):
    service_log = get_object_or_404(
        ServiceLog,
        id=service_log_id,
        status=ServiceLog.Status.SUBMITTED,
    )
    service_log.status = ServiceLog.Status.APPROVED
    service_log.reviewed_by = request.user
    service_log.reviewed_at = timezone.now()
    service_log.rejection_reason = ""
    service_log.save(
        update_fields=[
            "status",
            "reviewed_by",
            "reviewed_at",
            "rejection_reason",
            "updated_at",
        ],
    )
    write_audit_log(
        request.user,
        AuditLog.Action.SERVICE_LOG_APPROVED,
        service_log,
        f"Approved service log {service_log.id}.",
    )
    messages.success(request, "Service log approved.")
    return redirect("service_log_detail", service_log_id=service_log.id)


@admin_required
@require_POST
def service_log_reject(request, service_log_id):
    service_log = get_object_or_404(
        ServiceLog,
        id=service_log_id,
        status=ServiceLog.Status.SUBMITTED,
    )
    rejection_reason = request.POST.get("rejection_reason", "").strip()
    if not rejection_reason:
        messages.error(request, "Rejection reason is required.")
        return redirect("service_log_detail", service_log_id=service_log.id)

    service_log.status = ServiceLog.Status.REJECTED
    service_log.reviewed_by = request.user
    service_log.reviewed_at = timezone.now()
    service_log.rejection_reason = rejection_reason
    service_log.save(
        update_fields=[
            "status",
            "reviewed_by",
            "reviewed_at",
            "rejection_reason",
            "updated_at",
        ],
    )
    write_audit_log(
        request.user,
        AuditLog.Action.SERVICE_LOG_REJECTED,
        service_log,
        f"Rejected service log {service_log.id}.",
    )
    messages.success(request, "Service log rejected.")
    return redirect("service_log_detail", service_log_id=service_log.id)


@worker_required
def worker_log_list(request):
    worker = getattr(request.user, "supportworker", None)
    service_logs = ServiceLog.objects.none()
    if worker:
        service_logs = ServiceLog.objects.filter(worker=worker).select_related(
            "shift",
            "participant",
            "support_item",
        )

    return render(
        request,
        "service_logs/worker_log_list.html",
        {"service_logs": service_logs},
    )


@worker_required
def worker_service_log_detail(request, service_log_id):
    worker = getattr(request.user, "supportworker", None)
    service_log = get_object_or_404(
        ServiceLog.objects.select_related("shift", "participant", "support_item"),
        id=service_log_id,
        worker=worker,
    )
    return render(
        request,
        "service_logs/worker_service_log_detail.html",
        {"service_log": service_log},
    )


@worker_required
def worker_service_log_create(request, shift_id):
    worker = getattr(request.user, "supportworker", None)
    shift = get_object_or_404(
        Shift.objects.select_related("participant", "worker", "support_item"),
        id=shift_id,
        worker=worker,
        status__in=[Shift.Status.PUBLISHED, Shift.Status.CONFIRMED],
    )
    if hasattr(shift, "service_log"):
        raise Http404("Service log already exists for this shift.")

    initial = {
        "actual_start_time": shift.start_time.strftime("%H:%M"),
        "actual_end_time": shift.end_time.strftime("%H:%M"),
        "break_minutes": shift.break_minutes,
    }
    if request.method == "POST":
        form = ServiceLogForm(request.POST)
        if form.is_valid():
            service_log = ServiceLog.objects.create_from_shift(
                shift=shift,
                actual_start_time=form.cleaned_data["actual_start_time"],
                actual_end_time=form.cleaned_data["actual_end_time"],
                break_minutes=form.cleaned_data["break_minutes"],
                actual_hours=form.cleaned_data["actual_hours"],
                kilometres=form.cleaned_data["kilometres"],
                case_notes=form.cleaned_data["case_notes"],
                worker_notes=form.cleaned_data["worker_notes"],
            )
            shift.status = Shift.Status.COMPLETED
            shift.completed_at = timezone.now()
            shift.save(update_fields=["status", "completed_at", "updated_at"])
            messages.success(request, "Service log submitted.")
            return redirect("worker_service_log_detail", service_log_id=service_log.id)
    else:
        form = ServiceLogForm(initial=initial)

    return render(
        request,
        "service_logs/worker_service_log_form.html",
        {"form": form, "shift": shift},
    )
