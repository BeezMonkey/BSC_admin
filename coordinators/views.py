from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from accounts.decorators import admin_required, coordinator_required
from core.navigation import get_safe_return_url
from core.pagination import paginate_queryset
from core.sorting import apply_sorting

from .forms import (
    ParticipantCoordinatorAssignmentForm,
    SupportCoordinatorCreateForm,
    SupportCoordinatorEditForm,
)
from .models import SupportCoordinator


@coordinator_required
def coordinator_dashboard(request):
    return render(request, "coordinators/sc_dashboard.html")


@admin_required
def coordinator_list(request):
    coordinators = SupportCoordinator.objects.select_related("user").annotate(
        active_assignment_count=Count(
            "participant_assignments",
            filter=Q(participant_assignments__is_active=True),
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
def coordinator_assign_participant(request, coordinator_id):
    coordinator = get_object_or_404(SupportCoordinator, id=coordinator_id)
    if request.method == "POST":
        form = ParticipantCoordinatorAssignmentForm(
            request.POST,
            coordinator=coordinator,
        )
        if form.is_valid():
            form.save()
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
