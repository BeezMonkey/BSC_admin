from django.shortcuts import get_object_or_404, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from accounts.decorators import admin_required

from .models import Shift
from .planner_billing import billing_detail, with_billing_relations


BILLING_STATUS_CHOICES = (
    ("all", "All billing statuses"),
    ("attention", "Needs attention"),
    ("ready", "Ready to invoice"),
    ("draft", "Draft invoice"),
    ("issued", "Issued"),
    ("paid", "Paid"),
    ("nocharge", "Charge waived"),
)
ATTENTION_STATUSES = {"missing", "review", "rejected", "cancelreview", "check"}


@never_cache
@admin_required
@require_GET
def planner_billing_detail(request, shift_id):
    shift = get_object_or_404(with_billing_relations(Shift.objects.all(), detail=True), pk=shift_id)
    context = {"billing": billing_detail(shift)}
    partial = request.GET.get("partial") == "1"
    template = (
        "scheduling/partials/planner_billing_content.html" if partial
        else "scheduling/planner_billing_detail.html"
    )
    response = render(request, template, context)
    if partial:
        response["X-Planner-Billing"] = "1"
    return response
