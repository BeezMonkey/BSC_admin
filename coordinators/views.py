from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.decorators import admin_required, coordinator_required
from accounts.forms import AdminSetPasswordForm
from core.audit import write_audit_log
from core.models import AuditLog
from core.navigation import get_safe_return_url
from core.pagination import paginate_queryset
from core.sorting import apply_sorting
from participants.models import Participant

from .forms import (
    CoordinationLogCorrectionForm,
    CoordinationLogEditForm,
    CoordinationLogForm,
    ParticipantCoordinatorAssignmentForm,
    SupportCoordinatorCreateForm,
    SupportCoordinatorEditForm,
)
from .log_revisions import (
    log_snapshot,
    record_log_change,
    revision_is_current,
    revision_token,
)
from .models import CoordinationLog, CoordinationLogChange, SupportCoordinator
from .querysets import assigned_participants_for, coordination_logs_for


def get_current_coordinator(user):
    return getattr(user, "supportcoordinator", None)


@coordinator_required
def coordinator_dashboard(request):
    coordinator = get_current_coordinator(request.user)
    assigned_participant_count = assigned_participants_for(coordinator).count()
    return render(
        request,
        "coordinators/sc_dashboard.html",
        {"assigned_participant_count": assigned_participant_count},
    )


@coordinator_required
def coordinator_account(request):
    coordinator = get_current_coordinator(request.user)
    return render(
        request,
        "coordinators/sc_account.html",
        {"coordinator": coordinator},
    )


@coordinator_required
def coordinator_participant_list(request):
    coordinator = get_current_coordinator(request.user)
    participants = Participant.objects.none()
    if coordinator:
        participants = assigned_participants_for(coordinator)
    return render(
        request,
        "coordinators/sc_participant_list.html",
        {"participants": participants},
    )


@coordinator_required
def coordinator_participant_detail(request, participant_id):
    coordinator = get_current_coordinator(request.user)
    participant = get_object_or_404(
        assigned_participants_for(coordinator),
        id=participant_id,
    )
    return render(
        request,
        "coordinators/sc_participant_detail.html",
        {"participant": participant},
    )


@coordinator_required
def coordinator_log_list(request):
    coordinator = get_current_coordinator(request.user)
    logs = coordination_logs_for(coordinator).prefetch_related("invoice_lines")
    return render(
        request,
        "coordinators/sc_coordination_log_list.html",
        {"logs": logs},
    )


@coordinator_required
def coordinator_log_detail(request, log_id):
    coordinator = get_current_coordinator(request.user)
    log = get_object_or_404(
        coordination_logs_for(coordinator),
        id=log_id,
    )
    return render(
        request,
        "coordinators/sc_coordination_log_detail.html",
        {"log": log, "changes": log.changes.select_related("actor")},
    )


@coordinator_required
@transaction.atomic
def coordinator_log_edit(request, log_id):
    coordinator = get_current_coordinator(request.user)
    logs = coordination_logs_for(coordinator)
    if request.method == "POST":
        logs = logs.select_related(None).select_for_update()
    log = get_object_or_404(logs, pk=log_id)
    if not log.can_coordinator_edit:
        return HttpResponseForbidden("This log is read-only. Contact Admin for a correction.")
    before = log_snapshot(log)
    form = CoordinationLogEditForm(
        request.POST if request.method == "POST" else None,
        instance=log, coordinator=coordinator,
    )
    status = 200
    if request.method == "POST":
        if not revision_is_current(log, request.POST.get("revision_token", "")):
            form.add_error(
                None,
                "This log has changed. Reload the latest version before editing.",
            )
            status = 409
        elif form.is_valid():
            log = form.save(commit=False)
            log.status = CoordinationLog.Status.SUBMITTED
            log.reviewed_by = None
            log.reviewed_at = None
            log.rejection_reason = ""
            log.submitted_at = timezone.now()
            log.save()
            record_log_change(
                log, request.user, CoordinationLogChange.Kind.REVISION, before,
                reason=form.cleaned_data["revision_reason"],
            )
            messages.success(request, "Changes submitted for admin review.")
            return redirect("coordinator_log_detail", log_id=log.pk)
    token = request.POST.get("revision_token", "") if status == 409 else revision_token(log)
    return render(
        request,
        "coordinators/sc_coordination_log_form.html",
        {
            "form": form, "log": log, "editing": True,
            "revision_token": token, "stale_record": status == 409,
        },
        status=status,
    )


@coordinator_required
def coordinator_log_create(request):
    coordinator = get_current_coordinator(request.user)
    if request.method == "POST":
        form = CoordinationLogForm(request.POST, coordinator=coordinator)
        if form.is_valid():
            log = form.save(commit=False)
            log.coordinator = coordinator
            log.status = CoordinationLog.Status.SUBMITTED
            log.save()
            write_audit_log(
                request.user,
                AuditLog.Action.COORDINATION_LOG_SUBMITTED,
                log,
                f"Submitted coordination log {log.id}.",
            )
            messages.success(
                request,
                "Coordination log submitted for admin review.",
            )
            return redirect("coordinator_log_detail", log_id=log.id)
    else:
        form = CoordinationLogForm(coordinator=coordinator)

    return render(
        request,
        "coordinators/sc_coordination_log_form.html",
        {"form": form},
    )


@admin_required
def coordination_log_list(request):
    logs = CoordinationLog.objects.select_related(
        "participant", "coordinator"
    ).prefetch_related("invoice_lines")
    status = request.GET.get("status", "").strip()
    has_filters = bool(status)
    if status:
        logs = logs.filter(status=status)

    return render(
        request,
        "coordinators/coordination_log_list.html",
        {
            "logs": logs,
            "status": status,
            "has_filters": has_filters,
            "status_choices": CoordinationLog.Status.choices,
            "current_list_url": request.get_full_path(),
        },
    )


@admin_required
def coordination_log_detail(request, log_id):
    log = get_object_or_404(
        CoordinationLog.objects.select_related(
            "participant",
            "coordinator",
            "reviewed_by",
        ),
        id=log_id,
    )
    return render(
        request,
        "coordinators/coordination_log_detail.html",
        {
            "log": log,
            "revision_token": revision_token(log),
            "changes": log.changes.select_related("actor"),
            "invoice_locked": not log.can_coordinator_edit,
            "return_url": get_safe_return_url(
                request,
                reverse("coordination_log_list"),
            ),
        },
    )


def review_coordination_log(request, log_id, *, approve):
    with transaction.atomic():
        log = get_object_or_404(CoordinationLog.objects.select_for_update(), pk=log_id)
        if log.status != CoordinationLog.Status.SUBMITTED or log.invoice_lines.exists():
            messages.warning(request, "Coordination log has already been reviewed.")
        elif not revision_is_current(log, request.POST.get("revision_token", "")):
            messages.warning(
                request,
                "Coordination log has changed. Review the latest record before making a decision.",
            )
        else:
            reason = "" if approve else request.POST.get("rejection_reason", "").strip()
            if not approve and not reason:
                messages.error(request, "Rejection reason is required.")
            else:
                before = log_snapshot(log)
                log.status = (
                    CoordinationLog.Status.APPROVED if approve
                    else CoordinationLog.Status.REJECTED
                )
                log.reviewed_by = request.user
                log.reviewed_at = timezone.now()
                log.rejection_reason = reason
                log.save(update_fields=[
                    "status", "reviewed_by", "reviewed_at", "rejection_reason", "updated_at",
                ])
                kind = (
                    CoordinationLogChange.Kind.APPROVAL if approve
                    else CoordinationLogChange.Kind.REJECTION
                )
                record_log_change(log, request.user, kind, before, reason=reason)
                messages.success(
                    request,
                    "Coordination log approved." if approve else "Coordination log rejected.",
                )
    return redirect("coordination_log_detail", log_id=log_id)


@admin_required
@require_POST
def coordination_log_approve(request, log_id):
    return review_coordination_log(request, log_id, approve=True)


@admin_required
@require_POST
def coordination_log_reject(request, log_id):
    return review_coordination_log(request, log_id, approve=False)


@admin_required
@transaction.atomic
def coordination_log_correction(request, log_id):
    logs = CoordinationLog.objects.all()
    if request.method == "POST":
        logs = logs.select_for_update()
    log = get_object_or_404(logs, pk=log_id)
    if log.can_coordinator_edit:
        return HttpResponseForbidden(
            "Corrections are for invoiced logs. Uninvoiced logs can be revised by their coordinator."
        )
    form = CoordinationLogCorrectionForm(request.POST if request.method == "POST" else None)
    status = 200
    if request.method == "POST":
        if not revision_is_current(log, request.POST.get("revision_token", "")):
            form.add_error(None, "This log has changed. Reload before recording a correction.")
            status = 409
        elif form.is_valid():
            before = log_snapshot(log)
            log.save(update_fields=["updated_at"])
            record_log_change(
                log, request.user, form.cleaned_data["kind"], before,
                reason=form.cleaned_data["reason"], details=form.cleaned_data["details"],
            )
            messages.success(
                request, "Correction recorded. Original log and invoice values are unchanged."
            )
            return redirect("coordination_log_detail", log_id=log.pk)
    token = request.POST.get("revision_token", "") if status == 409 else revision_token(log)
    return render(
        request,
        "coordinators/coordination_log_correction.html",
        {
            "log": log, "form": form,
            "invoice_lines": log.invoice_lines.select_related("invoice"),
            "revision_token": token, "stale_record": status == 409,
        },
        status=status,
    )


@admin_required
def coordinator_list(request):
    coordinators = SupportCoordinator.objects.select_related("user").annotate(
        active_assignment_count=Count(
            "participant_assignments",
            filter=Q(
                participant_assignments__is_active=True,
                participant_assignments__participant__status=Participant.Status.ACTIVE,
            ),
            distinct=True,
        ),
    )
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    has_filters = bool(query or status)

    if query:
        coordinators = coordinators.filter(
            Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(email__icontains=query)
            | Q(phone__icontains=query)
        )
    if status:
        coordinators = coordinators.filter(status=status)

    coordinators, sorting = apply_sorting(
        request,
        coordinators,
        {
            "name": ("last_name", "first_name"),
            "status": ("status", "last_name", "first_name"),
        },
        default_sort="name",
    )
    coordinators, pagination = paginate_queryset(request, coordinators)

    return render(
        request,
        "coordinators/coordinator_list.html",
        {
            "coordinators": coordinators,
            "pagination": pagination,
            "sorting": sorting,
            "query": query,
            "status": status,
            "has_filters": has_filters,
            "status_choices": SupportCoordinator.Status.choices,
            "current_list_url": request.get_full_path(),
        },
    )


@admin_required
def coordinator_create(request):
    return_url = get_safe_return_url(request, "")
    if request.method == "POST":
        form = SupportCoordinatorCreateForm(request.POST)
        if form.is_valid():
            coordinator = form.save()
            write_audit_log(
                request.user,
                AuditLog.Action.SUPPORT_COORDINATOR_CREATED,
                coordinator,
                f"Created support coordinator {coordinator.id}.",
            )
            messages.success(request, "Support coordinator created.")
            if return_url:
                return redirect(return_url)
            return redirect(coordinator)
    else:
        form = SupportCoordinatorCreateForm()

    return render(
        request,
        "coordinators/coordinator_form.html",
        {
            "form": form,
            "title": "Add Support Coordinator",
            "return_url": return_url,
        },
    )


@admin_required
def coordinator_detail(request, coordinator_id):
    coordinator = get_object_or_404(
        SupportCoordinator.objects.select_related("user").prefetch_related(
            "participant_assignments__participant",
        ),
        id=coordinator_id,
    )
    assignments = coordinator.participant_assignments.all()

    return render(
        request,
        "coordinators/coordinator_detail.html",
        {
            "coordinator": coordinator,
            "assignments": assignments,
            "return_url": get_safe_return_url(
                request,
                reverse("coordinator_list"),
            ),
        },
    )


@admin_required
def coordinator_edit(request, coordinator_id):
    coordinator = get_object_or_404(
        SupportCoordinator.objects.select_related("user"),
        id=coordinator_id,
    )
    return_url = get_safe_return_url(
        request,
        reverse("coordinator_detail", args=[coordinator.id]),
    )
    if request.method == "POST":
        form = SupportCoordinatorEditForm(request.POST, instance=coordinator)
        if form.is_valid():
            coordinator = form.save()
            write_audit_log(
                request.user,
                AuditLog.Action.SUPPORT_COORDINATOR_UPDATED,
                coordinator,
                f"Updated support coordinator {coordinator.id}.",
            )
            messages.success(request, "Support coordinator updated.")
            return redirect(return_url)
    else:
        form = SupportCoordinatorEditForm(instance=coordinator)

    return render(
        request,
        "coordinators/coordinator_form.html",
        {
            "form": form,
            "title": "Edit Support Coordinator",
            "coordinator": coordinator,
            "return_url": return_url,
        },
    )


@admin_required
def coordinator_reset_password(request, coordinator_id):
    coordinator = get_object_or_404(
        SupportCoordinator.objects.select_related("user"),
        id=coordinator_id,
    )
    return_url = get_safe_return_url(
        request,
        reverse("coordinator_detail", args=[coordinator.id]),
    )
    if request.method == "POST":
        form = AdminSetPasswordForm(coordinator.user, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Support coordinator password updated.")
            return redirect(return_url)
    else:
        form = AdminSetPasswordForm(coordinator.user)

    return render(
        request,
        "accounts/admin_password_reset_form.html",
        {
            "form": form,
            "title": "Reset Support Coordinator Password",
            "subject_name": coordinator.display_name,
            "login_username": coordinator.user.username,
            "return_url": return_url,
            "submit_label": "Update Password",
        },
    )


@admin_required
def coordinator_assign_participant(request, coordinator_id):
    coordinator = get_object_or_404(SupportCoordinator, id=coordinator_id)
    if coordinator.status != SupportCoordinator.Status.ACTIVE:
        messages.error(
            request,
            "Inactive support coordinators cannot receive new active participant assignments.",
        )
        return redirect(coordinator)

    if request.method == "POST":
        form = ParticipantCoordinatorAssignmentForm(
            request.POST,
            coordinator=coordinator,
        )
        if form.is_valid():
            assignment = form.save()
            write_audit_log(
                request.user,
                AuditLog.Action.PARTICIPANT_COORDINATOR_ASSIGNED,
                assignment,
                (
                    f"Assigned participant {assignment.participant_id} "
                    f"to support coordinator {assignment.coordinator_id}."
                ),
            )
            messages.success(
                request,
                "Participant assigned to support coordinator.",
            )
            return redirect(coordinator)
    else:
        form = ParticipantCoordinatorAssignmentForm(coordinator=coordinator)

    return render(
        request,
        "coordinators/coordinator_assignment_form.html",
        {
            "form": form,
            "coordinator": coordinator,
        },
    )
