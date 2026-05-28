from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import admin_required

from .forms import ParticipantForm
from .models import Participant


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
    participant = get_object_or_404(Participant, id=participant_id)
    return render(
        request,
        "participants/participant_detail.html",
        {"participant": participant},
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
