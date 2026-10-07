"""Read-only projections of existing roster, service and invoice records.

Use with_billing_relations for lists (at most three queries), or detail=True
for drawer data (at most four). These are display states, not permission to
invoice a record; invoice creation retains its existing eligibility checks.
"""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.db.models import F, Prefetch
from django.utils import timezone

from invoices.models import Invoice, InvoiceBillingAdjustment, InvoiceLine
from service_logs.models import ServiceLog

from .models import ParticipantCancellation, Shift, SupportItem


_STATES = {
    "issued": ("Invoice issued", "info"),
    "paid": ("Invoice paid", "success"),
    "draft": ("Draft invoice", "neutral"),
    "ready": ("Ready to invoice", "success"),
    "missing": ("Missing service log", "danger"),
    "review": ("Log awaiting review", "warning"),
    "rejected": ("Log rejected", "danger"),
    "cancelreview": ("Cancellation review", "warning"),
    "nocharge": ("No charge", "neutral"),
    "cancelled": ("Cancelled", "neutral"),
    "upcoming": ("Upcoming", "neutral"),
    "not_due": ("Not due", "neutral"),
    "check": ("Check billing records", "warning"),
}
_SERVICE_TYPES = (InvoiceLine.LineType.SERVICE, InvoiceLine.LineType.CANCELLATION)
_ACTIVE_CANCELLATIONS = (
    ParticipantCancellation.Status.PENDING,
    ParticipantCancellation.Status.APPROVED,
    ParticipantCancellation.Status.WAIVED,
)


def with_billing_relations(queryset, detail=False):
    """Keep projection queries bounded without loading history on the planner."""
    lines = InvoiceLine.objects.exclude(invoice__status=Invoice.Status.CANCELLED).select_related("invoice")
    queryset = queryset.select_related("service_log", "participant_cancellation").prefetch_related(
        Prefetch("service_log__invoice_lines", queryset=lines, to_attr="_planner_billing_lines"),
        Prefetch("participant_cancellation__invoice_lines", queryset=lines, to_attr="_planner_billing_lines"),
    )
    if detail:
        # An old adjustment is not evidence for a replacement invoice, even if
        # its invoice is still active for some other source record.
        adjustments = InvoiceBillingAdjustment.objects.filter(
            invoice__lines__service_log_id=F("service_log_id"),
        ).exclude(invoice__status=Invoice.Status.CANCELLED).select_related(
            "invoice", "created_by",
        ).distinct().order_by("-created_at", "-pk")
        queryset = queryset.select_related(
            "participant", "worker", "support_item", "service_log__support_item",
            "service_log__participant", "service_log__worker", "service_log__reviewed_by",
            "participant_cancellation__submitted_by", "participant_cancellation__reviewed_by",
        ).prefetch_related(Prefetch(
            "service_log__billing_adjustments", queryset=adjustments,
            to_attr="_planner_billing_adjustments",
        ))
    return queryset


def _records(shift):
    return getattr(shift, "service_log", None), getattr(shift, "participant_cancellation", None)


def _active_lines(log, cancellation):
    lines = {}
    for record in (log, cancellation):
        if record is None:
            continue
        related = getattr(record, "_planner_billing_lines", None)
        if related is None:
            related = record.invoice_lines.exclude(
                invoice__status=Invoice.Status.CANCELLED,
            ).select_related("invoice")
        for line in related:
            lines[line.pk] = line
    return sorted(lines.values(), key=lambda line: line.pk)


def _summary_key(shift, log, cancellation, lines, now):
    active_cancellation = cancellation and cancellation.status in _ACTIVE_CANCELLATIONS
    if active_cancellation and log is not None:
        return "check"
    if lines:
        statuses = {line.invoice.status for line in lines}
        if len(statuses) != 1 or not statuses <= {
            Invoice.Status.DRAFT, Invoice.Status.ISSUED, Invoice.Status.PAID,
        }:
            return "check"
        if active_cancellation:
            if cancellation.status != ParticipantCancellation.Status.APPROVED or any(
                line.service_log_id is not None for line in lines
            ):
                return "check"
            expected_type = InvoiceLine.LineType.CANCELLATION
        else:
            if any(line.participant_cancellation_id is not None for line in lines):
                return "check"
            expected_type = InvoiceLine.LineType.SERVICE
        service_lines = [line for line in lines if line.line_type == expected_type]
        if not service_lines or any(line.unit != SupportItem.Unit.HOUR for line in service_lines):
            return "check"
        return next(iter(statuses))

    if cancellation:
        cancellation_key = {
            ParticipantCancellation.Status.PENDING: "cancelreview",
            ParticipantCancellation.Status.APPROVED: "ready",
            ParticipantCancellation.Status.WAIVED: "nocharge",
        }.get(cancellation.status)
        if cancellation_key:
            return cancellation_key
        if cancellation.status != ParticipantCancellation.Status.REJECTED:
            return "check"
    if log:
        return {
            ServiceLog.Status.SUBMITTED: "review",
            ServiceLog.Status.APPROVED: "ready",
            ServiceLog.Status.REJECTED: "rejected",
            ServiceLog.Status.INVOICED: "check",
        }.get(log.status, "check")
    if shift.status == Shift.Status.CANCELLED:
        return "cancelled"
    if shift.status == Shift.Status.DRAFT:
        return "not_due"
    if shift.status == Shift.Status.CANCELLATION_REVIEW:
        return "cancelreview"
    if shift.status not in (Shift.Status.PUBLISHED, Shift.Status.CONFIRMED):
        return "check"

    local_now = timezone.localtime(now)
    if (shift.service_date, shift.start_time) > (local_now.date(), local_now.time()):
        return "upcoming"
    if (shift.service_date, shift.end_time) > (local_now.date(), local_now.time()):
        return "not_due"
    # Match service_logs.follow_up: only ended, scheduled, published/confirmed
    # shifts without a log or active cancellation are missing service logs.
    return "missing" if shift.source == Shift.Source.SCHEDULED else "check"


def billing_summary(shift, now=None):
    """Return exactly {key, label, tone}; never fetch adjustment history."""
    log, cancellation = _records(shift)
    key = _summary_key(shift, log, cancellation, _active_lines(log, cancellation), now)
    label, tone = _STATES[key]
    return {"key": key, "label": label, "tone": tone}


def _confirmed_km(adjustment):
    values = adjustment.billing_values
    if not isinstance(values, dict):
        return None
    try:
        value = Decimal(str(values.get("kilometres")))
    except (InvalidOperation, ValueError, TypeError):
        return None
    return value if value.is_finite() and value >= 0 else None


def billing_detail(shift, now=None):
    """Return template context with source objects and active invoice snapshots.

    invoices is ordered by invoice PK; each entry has invoice, lines,
    service_lines (SERVICE/CANCELLATION), travel_lines, quantity, quantity_state,
    total and confirmed_km. quantity is Decimal hours only when every service
    line is hourly; otherwise None with state 'missing' or 'non_hour'. total
    sums only this shift's stored line_total values, never the whole invoice.

    actual_hours and rounded difference_minutes are None for active
    cancellations. adjustments contains newest-first source-log adjustments
    for currently linked active invoices only. confirmed_km is None without
    valid evidence or if those invoices disagree (confirmed_km_conflict=True).
    original_km always comes from the unchanged log, or is None without a log.
    """
    log, cancellation = _records(shift)
    lines = _active_lines(log, cancellation)
    groups = {}
    for line in lines:
        groups.setdefault(line.invoice_id, []).append(line)

    adjustments = []
    if log and groups:
        related = getattr(log, "_planner_billing_adjustments", None)
        if related is None:
            related = log.billing_adjustments.filter(
                invoice_id__in=groups, invoice__lines__service_log_id=log.pk,
            ).select_related("invoice", "created_by").distinct().order_by("-created_at", "-pk")
        adjustments = [adjustment for adjustment in related if adjustment.invoice_id in groups]

    latest = {}
    for adjustment in adjustments:
        if adjustment.invoice_id not in latest:
            latest[adjustment.invoice_id] = _confirmed_km(adjustment)

    invoices = []
    for invoice_id, invoice_lines in sorted(groups.items()):
        service_lines = [line for line in invoice_lines if line.line_type in _SERVICE_TYPES]
        quantity_state = "missing"
        quantity = None
        if service_lines:
            quantity_state = "non_hour"
            if all(line.unit == SupportItem.Unit.HOUR for line in service_lines):
                quantity_state = "hour"
                quantity = sum((line.quantity for line in service_lines), Decimal("0.00"))
        invoices.append({
            "invoice": invoice_lines[0].invoice,
            "lines": invoice_lines,
            "service_lines": service_lines,
            "travel_lines": [line for line in invoice_lines if line.line_type == InvoiceLine.LineType.TRAVEL_NON_LABOUR],
            "quantity": quantity,
            "quantity_state": quantity_state,
            "total": sum((line.line_total for line in invoice_lines), Decimal("0.00")),
            "confirmed_km": latest.get(invoice_id),
        })

    active_cancellation = cancellation and cancellation.status in _ACTIVE_CANCELLATIONS
    actual_hours = log.actual_hours if log and not active_cancellation else None
    difference_minutes = None
    if actual_hours is not None:
        difference_minutes = int(((actual_hours - shift.planned_hours) * 60).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP,
        ))
    confirmations = {value for value in latest.values() if value is not None}
    key = _summary_key(shift, log, cancellation, lines, now)
    label, tone = _STATES[key]
    return {
        "shift": shift,
        "summary": {"key": key, "label": label, "tone": tone},
        "log": log,
        "cancellation": cancellation,
        "invoices": invoices,
        "rostered_hours": shift.planned_hours,
        "actual_hours": actual_hours,
        "difference_minutes": difference_minutes,
        "adjustments": adjustments,
        "original_km": log.kilometres if log else None,
        "confirmed_km": next(iter(confirmations)) if len(confirmations) == 1 else None,
        "confirmed_km_conflict": len(confirmations) > 1,
    }
