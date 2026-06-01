from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import admin_required, worker_required

from .forms import SupportWorkerCreateForm, SupportWorkerEditForm
from .models import SupportWorker


@admin_required
def worker_list(request):
    workers = SupportWorker.objects.select_related("user")
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    employment_type = request.GET.get("employment_type", "").strip()

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

    return render(
        request,
        "workers/worker_list.html",
        {
            "workers": workers,
            "query": query,
            "status": status,
            "employment_type": employment_type,
            "status_choices": SupportWorker.Status.choices,
            "employment_type_choices": SupportWorker.EmploymentType.choices,
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
        },
    )


@admin_required
def worker_edit(request, worker_id):
    worker = get_object_or_404(SupportWorker.objects.select_related("user"), id=worker_id)
    if request.method == "POST":
        form = SupportWorkerEditForm(request.POST, instance=worker)
        if form.is_valid():
            worker = form.save()
            messages.success(request, "Support worker updated.")
            return redirect(worker)
    else:
        form = SupportWorkerEditForm(instance=worker)

    return render(
        request,
        "workers/worker_form.html",
        {"form": form, "title": "Edit Support Worker", "worker": worker},
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
