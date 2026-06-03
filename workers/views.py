from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from accounts.decorators import admin_required, worker_required
from core.navigation import get_safe_return_url
from core.pagination import paginate_queryset
from core.sorting import apply_sorting

from .forms import SupportWorkerCreateForm, SupportWorkerEditForm
from .models import SupportWorker


@admin_required
def worker_list(request):
    workers = SupportWorker.objects.select_related("user")
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    employment_type = request.GET.get("employment_type", "").strip()
    has_filters = bool(query or status or employment_type)

    if query:
        workers = workers.filter(
            Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(email__icontains=query)
            | Q(phone__icontains=query)
        )
    if status:
        workers = workers.filter(status=status)
    if employment_type:
        workers = workers.filter(employment_type=employment_type)
    workers, sorting = apply_sorting(
        request,
        workers,
        {
            "name": ("last_name", "first_name"),
            "status": ("status", "last_name", "first_name"),
            "employment_type": ("employment_type", "last_name", "first_name"),
        },
    )
    workers, pagination = paginate_queryset(request, workers)

    return render(
        request,
        "workers/worker_list.html",
        {
            "workers": workers,
            "pagination": pagination,
            "sorting": sorting,
            "query": query,
            "status": status,
            "employment_type": employment_type,
            "has_filters": has_filters,
            "status_choices": SupportWorker.Status.choices,
            "employment_type_choices": SupportWorker.EmploymentType.choices,
            "current_list_url": request.get_full_path(),
        },
    )


@admin_required
def worker_create(request):
    if request.method == "POST":
        form = SupportWorkerCreateForm(request.POST)
        if form.is_valid():
            worker = form.save()
            messages.success(request, "Support worker created.")
            return redirect(worker)
    else:
        form = SupportWorkerCreateForm()

    return render(
        request,
        "workers/worker_form.html",
        {"form": form, "title": "Add Support Worker"},
    )


@admin_required
def worker_detail(request, worker_id):
    worker = get_object_or_404(
        SupportWorker.objects.select_related("user").prefetch_related(
            "participant_assignments__participant"
        ),
        id=worker_id,
    )
    active_assignments = [
        assignment
        for assignment in worker.participant_assignments.all()
        if assignment.is_active
    ]
    readiness_items = [
        {
            "label": "Worker active",
            "missing_label": "Needs active worker status",
            "is_ready": worker.status == SupportWorker.Status.ACTIVE,
        },
        {
            "label": "Police check current",
            "missing_label": "Needs police check current",
            "is_ready": worker.police_check_status == SupportWorker.ComplianceStatus.CURRENT,
        },
        {
            "label": "WWCC / Blue Card current",
            "missing_label": "Needs WWCC / Blue Card current",
            "is_ready": worker.wwcc_status == SupportWorker.ComplianceStatus.CURRENT,
        },
        {
            "label": "Has active participant assignment",
            "missing_label": "Needs active participant assignment",
            "is_ready": bool(active_assignments),
        },
    ]
    return render(
        request,
        "workers/worker_detail.html",
        {
            "worker": worker,
            "readiness_items": readiness_items,
            "active_assignments": active_assignments,
            "return_url": get_safe_return_url(request, reverse("worker_list")),
        },
    )


@admin_required
def worker_edit(request, worker_id):
    worker = get_object_or_404(SupportWorker.objects.select_related("user"), id=worker_id)
    return_url = get_safe_return_url(
        request,
        reverse("worker_detail", args=[worker.id]),
    )
    if request.method == "POST":
        form = SupportWorkerEditForm(request.POST, instance=worker)
        if form.is_valid():
            worker = form.save()
            messages.success(request, "Support worker updated.")
            return redirect(return_url)
    else:
        form = SupportWorkerEditForm(instance=worker)

    return render(
        request,
        "workers/worker_form.html",
        {
            "form": form,
            "title": "Edit Support Worker",
            "worker": worker,
            "return_url": return_url,
        },
    )


@worker_required
def worker_profile(request):
    worker = (
        SupportWorker.objects.filter(user=request.user)
        .prefetch_related("participant_assignments__participant")
        .first()
    )
    if worker is None:
        return render(
            request,
            "core/worker_placeholder.html",
            {
                "title": "My Profile",
                "message": "Your worker profile has not been set up yet.",
            },
        )

    return render(
        request,
        "workers/worker_profile.html",
        {"worker": worker},
    )
