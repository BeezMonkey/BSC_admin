from django.contrib import messages
from django.db.models import Count, Prefetch, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from accounts.decorators import admin_required
from core.navigation import get_safe_return_url
from core.pagination import paginate_queryset
from core.sorting import apply_sorting

from .forms import ParticipantForm, ParticipantWorkerAssignmentForm
from .models import Participant, ParticipantWorkerAssignment


@admin_required
def participant_list(request):
    participants_base = Participant.objects.annotate(
        active_worker_count=Count(
            "worker_assignments",
            filter=Q(worker_assignments__is_active=True),
            distinct=True,
        ),
    ).order_by("last_name", "first_name", "id")
    total_count = participants_base.count()
    active_count = participants_base.filter(status=Participant.Status.ACTIVE).count()
    inactive_count = participants_base.filter(status=Participant.Status.INACTIVE).count()
    archived_count = participants_base.filter(status=Participant.Status.ARCHIVED).count()
    needs_assignment_count = participants_base.filter(
        status=Participant.Status.ACTIVE,
        active_worker_count=0,
    ).count()
    participants = participants_base.prefetch_related(
        Prefetch(
            "worker_assignments",
            queryset=ParticipantWorkerAssignment.objects.filter(is_active=True)
            .select_related("worker")
            .order_by("worker__last_name", "worker__first_name"),
            to_attr="active_worker_assignments",
        ),
    )
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    assignment = request.GET.get("assignment", "").strip()
    has_filters = bool(query or status or assignment)

    if query:
        participants = participants.filter(
            Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(preferred_name__icontains=query)
            | Q(ndis_number__icontains=query)
            | Q(phone__icontains=query)
            | Q(email__icontains=query)
        )
    if status:
        participants = participants.filter(status=status)
    if assignment == "assigned":
        participants = participants.filter(active_worker_count__gt=0)
    elif assignment == "unassigned":
        participants = participants.filter(active_worker_count=0)
    participant_overview = [
        {
            "label": "All participants",
            "count_label": f"{total_count} record{'s' if total_count != 1 else ''}",
            "description": "Full participant list",
            "url": reverse("participant_list"),
            "active": not status and not assignment,
        },
        {
            "label": "Active",
            "count_label": f"{active_count} active",
            "description": "Currently receiving support",
            "url": f"{reverse('participant_list')}?status={Participant.Status.ACTIVE}",
            "active": status == Participant.Status.ACTIVE and not assignment,
        },
        {
            "label": "Needs assignment",
            "count_label": f"{needs_assignment_count} without workers",
            "description": "Active participants without workers",
            "url": f"{reverse('participant_list')}?status={Participant.Status.ACTIVE}&assignment=unassigned",
            "active": status == Participant.Status.ACTIVE and assignment == "unassigned",
        },
        {
            "label": "Inactive",
            "count_label": f"{inactive_count} inactive",
            "description": "Not currently active",
            "url": f"{reverse('participant_list')}?status={Participant.Status.INACTIVE}",
            "active": status == Participant.Status.INACTIVE and not assignment,
        },
        {
            "label": "Archived",
            "count_label": f"{archived_count} archived",
            "description": "Historical participant records",
            "url": f"{reverse('participant_list')}?status={Participant.Status.ARCHIVED}",
            "active": status == Participant.Status.ARCHIVED and not assignment,
        },
    ]
    participants, sorting = apply_sorting(
        request,
        participants,
        {
            "name": ("last_name", "first_name"),
            "status": ("status", "last_name", "first_name"),
        },
    )
    participants, pagination = paginate_queryset(request, participants)

    return render(
        request,
        "participants/participant_list.html",
        {
            "participants": participants,
            "pagination": pagination,
            "sorting": sorting,
            "query": query,
            "status": status,
            "assignment": assignment,
            "has_filters": has_filters,
            "status_choices": Participant.Status.choices,
            "participant_overview": participant_overview,
            "current_list_url": request.get_full_path(),
        },
    )


@admin_required
def participant_create(request):
    return_url = get_safe_return_url(request, "")
    if request.method == "POST":
        form = ParticipantForm(request.POST)
        if form.is_valid():
            participant = form.save()
            messages.success(request, "Participant created.")
            if return_url:
                return redirect(return_url)
            return redirect(participant)
    else:
        form = ParticipantForm()

    return render(
        request,
        "participants/participant_form.html",
        {"form": form, "title": "Add Participant", "return_url": return_url},
    )


@admin_required
def participant_detail(request, participant_id):
    participant = get_object_or_404(
        Participant.objects.prefetch_related("worker_assignments__worker"),
        id=participant_id,
    )
    active_assignments = [
        assignment
        for assignment in participant.worker_assignments.all()
        if assignment.is_active
    ]
    readiness_items = [
        {
            "label": "NDIS number recorded",
            "missing_label": "Needs NDIS number",
            "is_ready": bool(participant.ndis_number),
        },
        {
            "label": "Plan dates recorded",
            "missing_label": "Needs plan dates",
            "is_ready": bool(participant.plan_start_date and participant.plan_end_date),
        },
        {
            "label": "Active worker assigned",
            "missing_label": "Needs active worker assignment",
            "is_ready": bool(active_assignments),
        },
    ]
    return render(
        request,
        "participants/participant_detail.html",
        {
            "participant": participant,
            "readiness_items": readiness_items,
            "active_assignments": active_assignments,
            "return_url": get_safe_return_url(request, reverse("participant_list")),
        },
    )


@admin_required
def participant_edit(request, participant_id):
    participant = get_object_or_404(Participant, id=participant_id)
    return_url = get_safe_return_url(
        request,
        reverse("participant_detail", args=[participant.id]),
    )
    if request.method == "POST":
        form = ParticipantForm(request.POST, instance=participant)
        if form.is_valid():
            participant = form.save()
            messages.success(request, "Participant updated.")
            return redirect(return_url)
    else:
        form = ParticipantForm(instance=participant)

    return render(
        request,
        "participants/participant_form.html",
        {
            "form": form,
            "title": "Edit Participant",
            "participant": participant,
            "return_url": return_url,
        },
    )


@admin_required
@require_POST
def participant_archive(request, participant_id):
    participant = get_object_or_404(Participant, id=participant_id)
    participant.status = Participant.Status.ARCHIVED
    participant.save(update_fields=["status", "updated_at"])
    messages.success(request, "Participant archived.")
    return redirect(participant)


@admin_required
def participant_assign_worker(request, participant_id):
    participant = get_object_or_404(Participant, id=participant_id)
    if request.method == "POST":
        form = ParticipantWorkerAssignmentForm(request.POST, participant=participant)
        if form.is_valid():
            form.save()
            messages.success(request, "Worker assigned.")
            return redirect(participant)
    else:
        form = ParticipantWorkerAssignmentForm(participant=participant)

    return render(
        request,
        "participants/assignment_form.html",
        {"form": form, "participant": participant},
    )


@admin_required
@require_POST
def assignment_end(request, assignment_id):
    assignment = get_object_or_404(ParticipantWorkerAssignment, id=assignment_id)
    end_date = request.POST.get("end_date") or None
    assignment.end_date = end_date
    assignment.is_active = False
    assignment.save(update_fields=["end_date", "is_active", "updated_at"])
    messages.success(request, "Assignment ended.")
    return redirect(assignment.participant)
