from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from accounts.decorators import admin_required, worker_required
from accounts.forms import AdminSetPasswordForm
from core.navigation import get_safe_return_url
from core.pagination import paginate_queryset
from core.sorting import apply_sorting
from documents.models import Document
from service_logs.models import ServiceLog

from .forms import SupportWorkerCreateForm, SupportWorkerEditForm
from .models import SupportWorker


@admin_required
def worker_list(request):
    workers = SupportWorker.objects.select_related("user")
    query = request.GET.get("q", "").strip()
    requested_status = request.GET.get("status", "").strip()
    requested_scope = request.GET.get("scope", "").strip()
    if requested_scope in {"active", "archived", "all"}:
        worker_scope = requested_scope
    elif requested_status == SupportWorker.Status.INACTIVE:
        worker_scope = "archived"
    elif requested_status == SupportWorker.Status.ACTIVE:
        worker_scope = "active"
    else:
        worker_scope = "active"
    employment_type = request.GET.get("employment_type", "").strip()
    has_filters = bool(query or employment_type)

    if worker_scope == "archived":
        workers = workers.filter(status=SupportWorker.Status.INACTIVE)
    elif worker_scope == "active":
        workers = workers.filter(status=SupportWorker.Status.ACTIVE)

    if query:
        workers = workers.filter(
            Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(email__icontains=query)
            | Q(phone__icontains=query)
        )
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
            "worker_scope": worker_scope,
            "employment_type": employment_type,
            "has_filters": has_filters,
            "employment_type_choices": SupportWorker.EmploymentType.choices,
            "current_list_url": request.get_full_path(),
        },
    )


@admin_required
def worker_create(request):
    return_url = get_safe_return_url(request, "")
    if request.method == "POST":
        form = SupportWorkerCreateForm(request.POST)
        if form.is_valid():
            worker = form.save()
            messages.success(request, "Support worker created.")
            if return_url:
                return redirect(return_url)
            return redirect(worker)
    else:
        form = SupportWorkerCreateForm()

    return render(
        request,
        "workers/worker_form.html",
        {"form": form, "title": "Add Support Worker", "return_url": return_url},
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
    documents_by_type = {}
    for document in Document.objects.filter(
        worker=worker,
        category=Document.Category.COMPLIANCE,
        required_document_type__gt="",
    ).order_by("-created_at"):
        documents_by_type.setdefault(document.required_document_type, document)
    compliance_document_items = [
        {
            "value": value,
            "label": label,
            "document": documents_by_type.get(value),
        }
        for value, label in Document.RequiredDocumentType.choices
    ]
    other_compliance_documents = Document.objects.filter(
        worker=worker,
        category=Document.Category.COMPLIANCE,
        required_document_type="",
    ).order_by("-created_at")[:5]
    recent_service_logs = ServiceLog.objects.filter(worker=worker).select_related(
        "participant",
    ).order_by("-service_date", "-submitted_at")[:5]
    return render(
        request,
        "workers/worker_detail.html",
        {
            "worker": worker,
            "readiness_items": readiness_items,
            "active_assignments": active_assignments,
            "compliance_document_items": compliance_document_items,
            "other_compliance_documents": other_compliance_documents,
            "recent_service_logs": recent_service_logs,
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


@admin_required
def worker_reset_password(request, worker_id):
    worker = get_object_or_404(SupportWorker.objects.select_related("user"), id=worker_id)
    return_url = get_safe_return_url(
        request,
        reverse("worker_detail", args=[worker.id]),
    )
    if request.method == "POST":
        form = AdminSetPasswordForm(worker.user, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Support worker password updated.")
            return redirect(return_url)
    else:
        form = AdminSetPasswordForm(worker.user)

    return render(
        request,
        "accounts/admin_password_reset_form.html",
        {
            "form": form,
            "title": "Reset Support Worker Password",
            "subject_name": worker.display_name,
            "login_username": worker.user.username,
            "return_url": return_url,
            "submit_label": "Update Password",
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
