from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import admin_required

from .forms import ParticipantForm, ParticipantWorkerAssignmentForm
from .models import Participant, ParticipantWorkerAssignment


@admin_required
def participant_list(request):
    participants = Participant.objects.all()
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()

    if query:
        participants = participants.filter(
            Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(preferred_name__icontains=query)
            | Q(ndis_number__icontains=query)
        )
    if status:
        participants = participants.filter(status=status)

    return render(
        request,
        "participants/participant_list.html",
        {
            "participants": participants,
            "query": query,
            "status": status,
            "status_choices": Participant.Status.choices,
        },
    )


@admin_required
def participant_create(request):
    if request.method == "POST":
        form = ParticipantForm(request.POST)
        if form.is_valid():
            participant = form.save()
            messages.success(request, "Participant created.")
            return redirect(participant)
    else:
        form = ParticipantForm()

    return render(
        request,
        "participants/participant_form.html",
        {"form": form, "title": "Add Participant"},
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
        },
    )


@admin_required
def participant_edit(request, participant_id):
    participant = get_object_or_404(Participant, id=participant_id)
    if request.method == "POST":
        form = ParticipantForm(request.POST, instance=participant)
        if form.is_valid():
            participant = form.save()
            messages.success(request, "Participant updated.")
            return redirect(participant)
    else:
        form = ParticipantForm(instance=participant)

    return render(
        request,
        "participants/participant_form.html",
        {"form": form, "title": "Edit Participant", "participant": participant},
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
