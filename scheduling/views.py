from datetime import timedelta

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.decorators import admin_required, worker_required
from core.audit import write_audit_log
from core.models import AuditLog

from .forms import RecurringShiftForm, ShiftForm, SupportItemForm
from .models import Shift, SupportItem


@admin_required
def roster_list(request):
    shifts = Shift.objects.select_related("participant", "worker", "support_item")
    date_from = request.GET.get("date_from", "").strip()
    date_to = request.GET.get("date_to", "").strip()
    participant_id = request.GET.get("participant", "").strip()
    worker_id = request.GET.get("worker", "").strip()
    status = request.GET.get("status", "").strip()

    if date_from:
        shifts = shifts.filter(service_date__gte=date_from)
    if date_to:
        shifts = shifts.filter(service_date__lte=date_to)
    if participant_id:
        shifts = shifts.filter(participant_id=participant_id)
    if worker_id:
        shifts = shifts.filter(worker_id=worker_id)
    if status:
        shifts = shifts.filter(status=status)

    return render(
        request,
        "scheduling/roster_list.html",
        {
            "shifts": shifts,
            "date_from": date_from,
            "date_to": date_to,
            "participant_id": participant_id,
            "worker_id": worker_id,
            "status": status,
            "status_choices": Shift.Status.choices,
        },
    )


@worker_required
def worker_shift_list(request):
    worker = getattr(request.user, "supportworker", None)
    shifts = Shift.objects.none()
    if worker:
        shifts = Shift.objects.filter(
            worker=worker,
            status__in=Shift.WORKER_VISIBLE_STATUSES,
        ).select_related("participant", "support_item")

    return render(
        request,
        "scheduling/worker_shift_list.html",
        {"shifts": shifts},
    )


@admin_required
def shift_create(request):
    if request.method == "POST":
        form = ShiftForm(request.POST, created_by=request.user)
        if form.is_valid():
            shift = form.save()
            messages.success(request, "Shift created.")
            return redirect(shift)
    else:
        initial = {
            key: request.GET[key]
            for key in ("participant", "worker")
            if request.GET.get(key)
        }
        form = ShiftForm(created_by=request.user, initial=initial)

    return render(
        request,
        "scheduling/shift_form.html",
        {"form": form, "title": "New Shift"},
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
            return redirect("roster_list")
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
        },
    )


@admin_required
def shift_edit(request, shift_id):
    shift = get_object_or_404(Shift, id=shift_id)
    if shift.status in [Shift.Status.COMPLETED, Shift.Status.CANCELLED]:
        messages.error(request, "Completed or cancelled shifts cannot be edited.")
        return redirect(shift)
    if request.method == "POST":
        form = ShiftForm(request.POST, instance=shift, created_by=request.user)
        if form.is_valid():
            shift = form.save()
            messages.success(request, "Shift updated.")
            return redirect(shift)
    else:
        form = ShiftForm(instance=shift, created_by=request.user)

    return render(
        request,
        "scheduling/shift_form.html",
        {"form": form, "title": "Edit Shift", "shift": shift},
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
