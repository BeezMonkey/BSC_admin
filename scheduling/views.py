from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import admin_required, worker_required

from .forms import SupportItemForm
from .models import SupportItem


@admin_required
def roster_list(request):
    return render(
        request,
        "core/admin_placeholder.html",
        {"title": "Roster", "message": "Scheduling starts in Phase 6."},
    )


@worker_required
def worker_shift_list(request):
    return render(
        request,
        "core/worker_placeholder.html",
        {"title": "My Shifts", "message": "Worker shifts start in Phase 6."},
    )


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
