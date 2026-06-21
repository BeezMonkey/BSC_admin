from datetime import timedelta
from urllib.parse import urlencode

from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.dateparse import parse_date
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.decorators import admin_required, worker_required
from core.audit import write_audit_log
from core.models import AuditLog
from core.navigation import get_safe_return_url
from core.pagination import paginate_queryset
from core.sorting import apply_sorting
from participants.models import Participant
from workers.models import SupportWorker

from .forms import RecurringShiftForm, ShiftForm, SupportItemForm
from .models import Shift, SupportItem


def format_filter_date(value):
    if hasattr(value, "strftime"):
        return value.strftime("%d/%m/%Y")
    parsed_date = parse_date(value)
    if not parsed_date:
        return value
    return parsed_date.strftime("%d/%m/%Y")


def format_roster_time(value):
    return value.strftime("%I:%M %p").lstrip("0").lower()


def build_roster_filter_summary(status, participant_query, worker_query, date_from, date_to):
    status_label = dict(Shift.Status.choices).get(status)
    if not any([status_label, participant_query, worker_query, date_from, date_to]):
        return ""

    summary = f"Showing {status_label.lower()} shifts" if status_label else "Showing shifts"
    match_parts = []
    if participant_query:
        match_parts.append(f'participant "{participant_query}"')
    if worker_query:
        match_parts.append(f'worker "{worker_query}"')
    if match_parts:
        summary += f" matching {' and '.join(match_parts)}"
    if date_from and date_to:
        summary += f" from {format_filter_date(date_from)} to {format_filter_date(date_to)}"
    elif date_from:
        summary += f" from {format_filter_date(date_from)}"
    elif date_to:
        summary += f" to {format_filter_date(date_to)}"
    return f"{summary}."


def roster_quick_range(quick_filter, today=None):
    if today is None:
        today = timezone.localdate()
    if quick_filter == "today":
        return today, today
    if quick_filter == "this_week":
        week_start = today - timedelta(days=today.weekday())
        return week_start, week_start + timedelta(days=6)
    if quick_filter == "next_week":
        week_start = today - timedelta(days=today.weekday()) + timedelta(days=7)
        return week_start, week_start + timedelta(days=6)
    if quick_filter == "upcoming":
        return today, None
    return None, None


def roster_next_action(shift):
    messages = {
        Shift.Status.DRAFT: "Ready to publish",
        Shift.Status.PUBLISHED: "Awaiting worker confirmation",
        Shift.Status.CONFIRMED: "Ready for worker log",
        Shift.Status.COMPLETED: "Review service log",
        Shift.Status.CANCELLED: "No action required",
        Shift.Status.NO_SHOW: "Review follow-up",
    }
    return messages.get(shift.status, "")


def participant_address(participant):
    address_lines = [
        participant.address_line_1,
        participant.address_line_2,
        " ".join(
            part
            for part in [participant.suburb, participant.state, participant.postcode]
            if part
        ),
    ]
    return "\n".join(line for line in address_lines if line)


def filter_roster_queryset(shifts, date_from, date_to, participant_query, worker_query, status):
    if date_from:
        shifts = shifts.filter(service_date__gte=date_from)
    if date_to:
        shifts = shifts.filter(service_date__lte=date_to)
    if participant_query:
        shifts = shifts.filter(
            Q(participant__first_name__icontains=participant_query)
            | Q(participant__last_name__icontains=participant_query)
            | Q(participant__ndis_number__icontains=participant_query)
            | Q(participant__phone__icontains=participant_query)
        )
    if worker_query:
        shifts = shifts.filter(
            Q(worker__first_name__icontains=worker_query)
            | Q(worker__last_name__icontains=worker_query)
            | Q(worker__email__icontains=worker_query)
            | Q(worker__phone__icontains=worker_query)
        )
    if status:
        shifts = shifts.filter(status=status)
    return shifts


@admin_required
def roster_list(request):
    shifts = Shift.objects.select_related("participant", "worker", "support_item")
    date_from = request.GET.get("date_from", "").strip()
    date_to = request.GET.get("date_to", "").strip()
    participant_query = request.GET.get("participant", "").strip()
    worker_query = request.GET.get("worker", "").strip()
    status = request.GET.get("status", "").strip()
    quick_filter = request.GET.get("quick", "").strip()
    today = parse_date(request.GET.get("today", "")) or timezone.localdate()
    quick_date_from, quick_date_to = roster_quick_range(quick_filter, today)
    if quick_date_from and not date_from:
        date_from = quick_date_from.isoformat()
    if quick_date_to and not date_to:
        date_to = quick_date_to.isoformat()
    has_filters = bool(
        date_from or date_to or participant_query or worker_query or status or quick_filter
    )

    shifts = filter_roster_queryset(
        shifts,
        date_from,
        date_to,
        participant_query,
        worker_query,
        status,
    )
    draft_publish_count = shifts.count() if status == Shift.Status.DRAFT else 0
    filter_summary = build_roster_filter_summary(
        status,
        participant_query,
        worker_query,
        date_from,
        date_to,
    )
    shifts, sorting = apply_sorting(
        request,
        shifts,
        {
            "date": ("service_date", "start_time"),
            "participant": ("participant__last_name", "participant__first_name", "service_date"),
            "worker": ("worker__last_name", "worker__first_name", "service_date"),
            "status": ("status", "service_date"),
        },
    )
    shifts, pagination = paginate_queryset(request, shifts)
    for shift in shifts:
        shift.next_action = roster_next_action(shift)

    quick_filters = [
        {
            "label": "Today",
            "value": "today",
            "date_from": today.isoformat(),
            "date_to": today.isoformat(),
        },
        {
            "label": "This week",
            "value": "this_week",
            "date_from": (today - timedelta(days=today.weekday())).isoformat(),
            "date_to": (today - timedelta(days=today.weekday()) + timedelta(days=6)).isoformat(),
        },
        {
            "label": "Next week",
            "value": "next_week",
            "date_from": (
                today - timedelta(days=today.weekday()) + timedelta(days=7)
            ).isoformat(),
            "date_to": (
                today - timedelta(days=today.weekday()) + timedelta(days=13)
            ).isoformat(),
        },
        {
            "label": "All upcoming",
            "value": "upcoming",
            "date_from": today.isoformat(),
            "date_to": "",
        },
    ]

    return render(
        request,
        "scheduling/roster_list.html",
        {
            "shifts": shifts,
            "pagination": pagination,
            "sorting": sorting,
            "date_from": date_from,
            "date_to": date_to,
            "participant_query": participant_query,
            "worker_query": worker_query,
            "status": status,
            "has_filters": has_filters,
            "status_choices": Shift.Status.choices,
            "filter_summary": filter_summary,
            "current_list_url": request.get_full_path(),
            "quick_filter": quick_filter,
            "quick_filters": quick_filters,
            "show_bulk_publish": status == Shift.Status.DRAFT,
            "draft_publish_count": draft_publish_count,
        },
    )


@admin_required
def roster_planner(request):
    today = timezone.localdate()
    default_date_from = today - timedelta(days=today.weekday())
    default_date_to = default_date_from + timedelta(days=6)
    view_mode = request.GET.get("view", "participant").strip()
    if view_mode not in {"participant", "worker"}:
        view_mode = "participant"
    is_worker_view = view_mode == "worker"
    date_from = request.GET.get("date_from", "").strip() or default_date_from.isoformat()
    date_to = request.GET.get("date_to", "").strip() or default_date_to.isoformat()
    display_date_from = parse_date(date_from)
    display_date_to = parse_date(date_to)
    participant_id = request.GET.get("participant", "").strip()
    worker_id = request.GET.get("worker", "").strip()
    selected_participant = None
    selected_worker = None
    planner_day_count = 0
    planner_span_label = "Custom range"
    planner_range_label = ""
    planner_scope_modifier = "custom"

    shifts = Shift.objects.select_related("participant", "worker", "support_item")
    shifts = filter_roster_queryset(shifts, date_from, date_to, "", "", "")
    if participant_id:
        selected_participant = get_object_or_404(Participant, id=participant_id)
        shifts = shifts.filter(participant=selected_participant)
    if worker_id:
        selected_worker = get_object_or_404(SupportWorker, id=worker_id)
        shifts = shifts.filter(worker=selected_worker)
    shifts = list(shifts.order_by("service_date", "start_time", "participant__last_name"))
    for shift in shifts:
        shift.display_time = (
            f"{format_roster_time(shift.start_time)} - {format_roster_time(shift.end_time)}"
        )
        shift.can_delete_from_planner = shift.status in (
            Shift.Status.DRAFT,
            Shift.Status.PUBLISHED,
        )
        shift.can_edit_from_planner = shift.status not in (
            Shift.Status.COMPLETED,
            Shift.Status.CANCELLED,
        )
        copy_shift_params = {
            "view": view_mode,
            "participant": shift.participant_id,
            "worker": shift.worker_id,
            "service_date": shift.service_date.isoformat(),
            "start_time": shift.start_time.strftime("%H:%M"),
            "end_time": shift.end_time.strftime("%H:%M"),
            "break_minutes": shift.break_minutes,
            "support_item": shift.support_item_id,
            "service_type": shift.service_type,
            "location": shift.location,
            "address": shift.address,
            "instructions": shift.instructions,
            "admin_notes": shift.admin_notes,
            "status": Shift.Status.DRAFT,
            "next": request.get_full_path(),
        }
        shift.copy_shift_url = (
            f"{reverse('shift_create')}?"
            f"{urlencode({key: value for key, value in copy_shift_params.items() if value != '' and value is not None})}"
        )
    planner_days = []
    if display_date_from and display_date_to and display_date_from <= display_date_to:
        planner_day_count = (display_date_to - display_date_from).days + 1
        planner_range_label = (
            f"{display_date_from.strftime('%d/%m/%Y')} - {display_date_to.strftime('%d/%m/%Y')}"
        )
        if planner_day_count == 7:
            planner_span_label = "1 week"
            planner_scope_modifier = "one-week"
        elif planner_day_count > 7:
            planner_span_label = (
                f"{planner_day_count // 7} weeks"
                if planner_day_count % 7 == 0
                else f"{planner_day_count} days"
            )
            planner_scope_modifier = "multi-week"
        else:
            planner_span_label = "1 day" if planner_day_count == 1 else f"{planner_day_count} days"
            planner_scope_modifier = "short-range"

        def planner_url_for(start_date, end_date):
            params = {
                "view": view_mode,
                "participant": selected_participant.id if selected_participant else "",
                "worker": selected_worker.id if selected_worker else "",
                "date_from": start_date.isoformat(),
                "date_to": end_date.isoformat(),
            }
            return (
                f"{reverse('roster_planner')}?"
                f"{urlencode({key: value for key, value in params.items() if value})}"
            )

        previous_week_url = planner_url_for(
            display_date_from - timedelta(days=7),
            display_date_to - timedelta(days=7),
        )
        next_week_url = planner_url_for(
            display_date_from + timedelta(days=7),
            display_date_to + timedelta(days=7),
        )
        today_url = planner_url_for(default_date_from, default_date_to)

        current_date = display_date_from
        while current_date <= display_date_to:
            add_shift_params = {
                "view": view_mode,
                "participant": selected_participant.id if selected_participant else "",
                "worker": selected_worker.id if selected_worker else "",
                "service_date": current_date.isoformat(),
                "from_planner": "1",
                "next": request.get_full_path(),
            }
            planner_days.append(
                {
                    "date": current_date,
                    "is_weekend": current_date.weekday() >= 5,
                    "shifts": [shift for shift in shifts if shift.service_date == current_date],
                    "add_shift_url": (
                        f"{reverse('shift_create')}?"
                        f"{urlencode({key: value for key, value in add_shift_params.items() if value})}"
                    ),
                }
            )
            current_date += timedelta(days=1)

    return render(
        request,
        "scheduling/roster_planner.html",
        {
            "date_from": date_from,
            "date_to": date_to,
            "display_date_from": display_date_from,
            "display_date_to": display_date_to,
            "participants": Participant.objects.filter(status=Participant.Status.ACTIVE).order_by(
                "last_name",
                "first_name",
            ),
            "workers": SupportWorker.objects.filter(status=SupportWorker.Status.ACTIVE).order_by(
                "last_name",
                "first_name",
            ),
            "selected_participant": selected_participant,
            "selected_worker": selected_worker,
            "view_mode": view_mode,
            "is_worker_view": is_worker_view,
            "primary_filter_label": "Worker focus" if is_worker_view else "Participant focus",
            "secondary_filter_label": "Participant filter" if is_worker_view else "Worker filter",
            "shifts": shifts,
            "planner_days": planner_days,
            "planner_day_count": planner_day_count,
            "planner_span_label": planner_span_label,
            "planner_range_label": planner_range_label,
            "planner_scope_modifier": planner_scope_modifier,
            "previous_week_url": previous_week_url if planner_days else "",
            "next_week_url": next_week_url if planner_days else "",
            "today_url": today_url if planner_days else "",
            "current_planner_url": request.get_full_path(),
        },
    )


@worker_required
def worker_shift_list(request):
    worker = getattr(request.user, "supportworker", None)
    shifts = Shift.objects.none()
    selected_view = request.GET.get("view", "all").strip()
    valid_views = {"all", "needs_attention", "upcoming", "completed"}
    if selected_view not in valid_views:
        selected_view = "all"
    shift_groups = {
        "needs_attention": [],
        "upcoming": [],
        "completed": [],
    }
    if worker:
        shifts = Shift.objects.filter(
            worker=worker,
            status__in=Shift.WORKER_VISIBLE_STATUSES,
        ).select_related("participant", "support_item")
        for shift in shifts:
            if shift.status == Shift.Status.PUBLISHED:
                shift_groups["needs_attention"].append(shift)
            elif shift.status == Shift.Status.CONFIRMED:
                shift_groups["upcoming"].append(shift)
            else:
                shift_groups["completed"].append(shift)
    visible_shift_groups = {
        key: value if selected_view in ["all", key] else []
        for key, value in shift_groups.items()
    }

    return render(
        request,
        "scheduling/worker_shift_list.html",
        {
            "shifts": shifts,
            "shift_groups": shift_groups,
            "visible_shift_groups": visible_shift_groups,
            "selected_view": selected_view,
            "needs_attention_count": len(shift_groups["needs_attention"]),
            "upcoming_count": len(shift_groups["upcoming"]),
            "completed_count": len(shift_groups["completed"]),
        },
    )


@admin_required
def shift_create(request):
    return_url = get_safe_return_url(request, "")
    is_modal = request.GET.get("modal") == "1" or request.POST.get("modal") == "1"
    modal_context = {"is_modal": is_modal}
    if request.method == "POST":
        form = ShiftForm(request.POST, created_by=request.user)
        if form.is_valid():
            shift = form.save()
            if is_modal:
                return JsonResponse({"ok": True})
            messages.success(request, "Shift created.")
            if return_url:
                return redirect(return_url)
            return redirect(shift)
        if is_modal:
            service_date = form["service_date"].value()
            modal_date_label = format_filter_date(service_date) if service_date else ""
            return render(
                request,
                "scheduling/partials/shift_form_modal.html",
                {
                    "form": form,
                    "title": "New Shift",
                    "modal_title": (
                        f"New Shift on {modal_date_label}" if modal_date_label else "New Shift"
                    ),
                    "return_url": return_url,
                    "form_action": f"{reverse('shift_create')}?modal=1",
                    **modal_context,
                },
                status=400,
            )
    else:
        initial = {
            key: request.GET[key]
            for key in (
                "participant",
                "worker",
                "service_date",
                "start_time",
                "end_time",
                "break_minutes",
                "support_item",
                "service_type",
                "location",
                "address",
                "instructions",
                "admin_notes",
                "status",
            )
            if request.GET.get(key)
        }
        if request.GET.get("from_planner") and request.GET.get("participant"):
            participant = get_object_or_404(Participant, id=request.GET["participant"])
            initial.setdefault("status", Shift.Status.DRAFT)
            initial.setdefault("location", "Participant home")
            initial.setdefault("address", participant_address(participant))
        form = ShiftForm(created_by=request.user, initial=initial)

    if is_modal:
        service_date = form["service_date"].value()
        modal_date_label = format_filter_date(service_date) if service_date else ""
        return render(
            request,
            "scheduling/partials/shift_form_modal.html",
            {
                "form": form,
                "title": "New Shift",
                "modal_title": (
                    f"New Shift on {modal_date_label}" if modal_date_label else "New Shift"
                ),
                "return_url": return_url,
                "form_action": request.get_full_path(),
                **modal_context,
            },
        )

    return render(
        request,
        "scheduling/shift_form.html",
        {"form": form, "title": "New Shift", "return_url": return_url, **modal_context},
    )


def recurring_shift_preview(form):
    if not form.is_valid():
        return []

    data = form.cleaned_data
    step_days = 7 if data["frequency"] == RecurringShiftForm.FREQUENCY_WEEKLY else 14
    preview = []
    service_date = data["start_date"]
    while service_date <= data["end_date"]:
        conflict = Shift.objects.filter(
            worker=data["worker"],
            service_date=service_date,
            status__in=Shift.ACTIVE_CONFLICT_STATUSES,
            start_time__lt=data["end_time"],
            end_time__gt=data["start_time"],
        ).exists()
        preview.append(
            {
                "service_date": service_date,
                "has_conflict": conflict,
                "status": "Skipped - worker conflict" if conflict else "Will create",
            }
        )
        service_date += timedelta(days=step_days)
    return preview


@admin_required
def recurring_shift_create(request):
    if request.method == "POST":
        form = RecurringShiftForm(request.POST)
        preview = recurring_shift_preview(form)
        if form.is_valid():
            created_count = 0
            skipped_count = 0
            data = form.cleaned_data
            for item in preview:
                if item["has_conflict"]:
                    skipped_count += 1
                    continue
                Shift.objects.create(
                    participant=data["participant"],
                    worker=data["worker"],
                    service_date=item["service_date"],
                    start_time=data["start_time"],
                    end_time=data["end_time"],
                    break_minutes=data["break_minutes"],
                    planned_hours=data["planned_hours"],
                    support_item=data["support_item"],
                    service_type=data["service_type"],
                    location=data["location"],
                    address=data["address"],
                    instructions=data["instructions"],
                    admin_notes=data["admin_notes"],
                    status=Shift.Status.DRAFT,
                    created_by=request.user,
                )
                created_count += 1
            messages.success(
                request,
                f"Recurring shifts created: {created_count}; skipped: {skipped_count}.",
            )
            return redirect(f"{reverse('roster_list')}?status={Shift.Status.DRAFT}")
    else:
        form = RecurringShiftForm(request.GET or None)
        preview = recurring_shift_preview(form)

    return render(
        request,
        "scheduling/recurring_shift_form.html",
        {"form": form, "preview": preview},
    )


@admin_required
def shift_detail(request, shift_id):
    shift = get_object_or_404(
        Shift.objects.select_related("participant", "worker", "support_item", "created_by"),
        id=shift_id,
    )
    service_log = getattr(shift, "service_log", None)
    workflow_messages = {
        Shift.Status.DRAFT: {
            "label": "Draft shift",
            "next_step": "Next step: publish this shift so the worker can see it.",
        },
        Shift.Status.PUBLISHED: {
            "label": "Published shift",
            "next_step": "Next step: wait for worker confirmation or follow up with the worker.",
        },
        Shift.Status.CONFIRMED: {
            "label": "Confirmed shift",
            "next_step": "Next step: worker completes the service log after the shift.",
        },
        Shift.Status.COMPLETED: {
            "label": "Completed shift",
            "next_step": "Next step: review the submitted service log.",
        },
        Shift.Status.CANCELLED: {
            "label": "Cancelled shift",
            "next_step": "No further shift action is required unless it needs to be recreated.",
        },
        Shift.Status.NO_SHOW: {
            "label": "No-show shift",
            "next_step": "Next step: review notes and decide any follow-up action.",
        },
    }
    return render(
        request,
        "scheduling/shift_detail.html",
        {
            "shift": shift,
            "service_log": service_log,
            "workflow_status": workflow_messages.get(shift.status),
            "return_url": get_safe_return_url(request, reverse("roster_list")),
        },
    )


@admin_required
def shift_edit(request, shift_id):
    shift = get_object_or_404(Shift, id=shift_id)
    return_url = get_safe_return_url(
        request,
        reverse("shift_detail", args=[shift.id]),
    )
    is_modal = request.GET.get("modal") == "1" or request.POST.get("modal") == "1"
    if shift.status in [Shift.Status.COMPLETED, Shift.Status.CANCELLED]:
        messages.error(request, "Completed or cancelled shifts cannot be edited.")
        return redirect(shift)
    if request.method == "POST":
        form = ShiftForm(request.POST, instance=shift, created_by=request.user)
        if form.is_valid():
            shift = form.save()
            if is_modal:
                return JsonResponse({"ok": True})
            messages.success(request, "Shift updated.")
            return redirect(return_url)
        if is_modal:
            service_date = form["service_date"].value()
            modal_date_label = format_filter_date(service_date) if service_date else ""
            return render(
                request,
                "scheduling/partials/shift_form_modal.html",
                {
                    "form": form,
                    "title": "Edit Shift",
                    "modal_title": (
                        f"Edit Shift on {modal_date_label}" if modal_date_label else "Edit Shift"
                    ),
                    "modal_subtitle": "Update this rostered service without leaving the planner.",
                    "submit_label": "Save Shift",
                    "return_url": return_url,
                    "form_action": f"{reverse('shift_edit', args=[shift.id])}?modal=1",
                    "is_modal": True,
                },
                status=400,
            )
    else:
        form = ShiftForm(instance=shift, created_by=request.user)

    if is_modal:
        service_date = form["service_date"].value()
        modal_date_label = format_filter_date(service_date) if service_date else ""
        return render(
            request,
            "scheduling/partials/shift_form_modal.html",
            {
                "form": form,
                "title": "Edit Shift",
                "modal_title": (
                    f"Edit Shift on {modal_date_label}" if modal_date_label else "Edit Shift"
                ),
                "modal_subtitle": "Update this rostered service without leaving the planner.",
                "submit_label": "Save Shift",
                "return_url": return_url,
                "form_action": request.get_full_path(),
                "is_modal": True,
            },
        )

    return render(
        request,
        "scheduling/shift_form.html",
        {
            "form": form,
            "title": "Edit Shift",
            "shift": shift,
            "return_url": return_url,
        },
    )


@admin_required
@require_POST
def shift_publish(request, shift_id):
    shift = get_object_or_404(Shift, id=shift_id)
    if shift.status == Shift.Status.DRAFT:
        shift.status = Shift.Status.PUBLISHED
        shift.save(update_fields=["status", "updated_at"])
        messages.success(request, "Shift published.")
    return redirect(shift)


@admin_required
@require_POST
def shift_bulk_publish(request):
    date_from = request.POST.get("date_from", "").strip()
    date_to = request.POST.get("date_to", "").strip()
    participant_query = request.POST.get("participant", "").strip()
    worker_query = request.POST.get("worker", "").strip()
    shifts = filter_roster_queryset(
        Shift.objects.all(),
        date_from,
        date_to,
        participant_query,
        worker_query,
        Shift.Status.DRAFT,
    )
    published_count = shifts.update(status=Shift.Status.PUBLISHED, updated_at=timezone.now())
    if published_count:
        messages.success(request, f"Published {published_count} draft shift(s).")
    else:
        messages.info(request, "No draft shifts matched the current filters.")
    redirect_params = {
        "date_from": date_from,
        "date_to": date_to,
        "participant": participant_query,
        "worker": worker_query,
        "status": Shift.Status.PUBLISHED,
    }
    redirect_query = urlencode({key: value for key, value in redirect_params.items() if value})
    return redirect(f"{reverse('roster_list')}?{redirect_query}")


@admin_required
@require_POST
def shift_cancel(request, shift_id):
    shift = get_object_or_404(Shift, id=shift_id)
    shift.status = Shift.Status.CANCELLED
    shift.cancellation_reason = request.POST.get("cancellation_reason", "")
    shift.save(update_fields=["status", "cancellation_reason", "updated_at"])
    write_audit_log(
        request.user,
        AuditLog.Action.SHIFT_CANCELLED,
        shift,
        f"Cancelled shift {shift.id}.",
    )
    messages.success(request, "Shift cancelled.")
    return redirect(shift)


@admin_required
@require_POST
def shift_delete(request, shift_id):
    shift = get_object_or_404(Shift, id=shift_id)
    return_url = get_safe_return_url(request, reverse("roster_planner"))
    if shift.status not in (Shift.Status.DRAFT, Shift.Status.PUBLISHED):
        messages.error(request, "Only draft or published shifts can be deleted.")
        return redirect(shift)

    shift.delete()
    messages.success(request, "Shift deleted.")
    return redirect(return_url)


@worker_required
def worker_shift_detail(request, shift_id):
    worker = getattr(request.user, "supportworker", None)
    shift = get_object_or_404(
        Shift.objects.select_related("participant", "support_item"),
        id=shift_id,
        worker=worker,
        status__in=Shift.WORKER_VISIBLE_STATUSES,
    )
    return render(request, "scheduling/worker_shift_detail.html", {"shift": shift})


@worker_required
@require_POST
def worker_shift_confirm(request, shift_id):
    worker = getattr(request.user, "supportworker", None)
    shift = get_object_or_404(
        Shift,
        id=shift_id,
        worker=worker,
        status=Shift.Status.PUBLISHED,
    )
    shift.status = Shift.Status.CONFIRMED
    shift.confirmed_at = timezone.now()
    shift.save(update_fields=["status", "confirmed_at", "updated_at"])
    messages.success(request, "Shift confirmed.")
    return redirect("worker_shift_detail", shift_id=shift.id)


@admin_required
def support_item_list(request):
    support_items = SupportItem.objects.all()
    query = request.GET.get("q", "").strip()
    is_active = request.GET.get("is_active", "").strip()
    category = request.GET.get("category", "").strip()

    if query:
        support_items = support_items.filter(
            Q(item_number__icontains=query)
            | Q(name__icontains=query)
            | Q(category__icontains=query)
        )
    if is_active == "active":
        support_items = support_items.filter(is_active=True)
    elif is_active == "inactive":
        support_items = support_items.filter(is_active=False)
    if category:
        support_items = support_items.filter(category=category)

    categories = (
        SupportItem.objects.exclude(category="")
        .order_by("category")
        .values_list("category", flat=True)
        .distinct()
    )

    return render(
        request,
        "scheduling/support_item_list.html",
        {
            "support_items": support_items,
            "query": query,
            "is_active": is_active,
            "category": category,
            "categories": categories,
        },
    )


@admin_required
def support_item_create(request):
    if request.method == "POST":
        form = SupportItemForm(request.POST)
        if form.is_valid():
            support_item = form.save()
            messages.success(request, "Support item created.")
            return redirect(support_item)
    else:
        form = SupportItemForm()

    return render(
        request,
        "scheduling/support_item_form.html",
        {"form": form, "title": "Add Support Item"},
    )


@admin_required
def support_item_detail(request, support_item_id):
    support_item = get_object_or_404(SupportItem, id=support_item_id)
    return render(
        request,
        "scheduling/support_item_detail.html",
        {"support_item": support_item},
    )


@admin_required
def support_item_edit(request, support_item_id):
    support_item = get_object_or_404(SupportItem, id=support_item_id)
    if request.method == "POST":
        form = SupportItemForm(request.POST, instance=support_item)
        if form.is_valid():
            support_item = form.save()
            messages.success(request, "Support item updated.")
            return redirect(support_item)
    else:
        form = SupportItemForm(instance=support_item)

    return render(
        request,
        "scheduling/support_item_form.html",
        {
            "form": form,
            "title": "Edit Support Item",
            "support_item": support_item,
        },
    )
