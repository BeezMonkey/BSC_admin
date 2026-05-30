from django.contrib import messages
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.decorators import admin_required, worker_required
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
    return render(
        request,
        "service_logs/service_log_list.html",
        {"service_logs": service_logs},
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
        {"service_log": service_log},
    )


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
