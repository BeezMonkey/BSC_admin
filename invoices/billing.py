from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction

from core.audit import write_audit_log
from core.models import AuditLog
from scheduling.models import ParticipantCancellation, SupportItem
from scheduling.widgets import support_item_picker_group
from service_logs.models import ServiceLog

from .forms import BillingAdjustmentForm, TravelClaimForm
from .models import Invoice, InvoiceBillingAdjustment, InvoiceLine


class BillingRecordsChanged(ValueError):
    pass


def service_total(hours, rate):
    return (hours * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def build_service_billing_row(log, data=None, *, can_adjust=False):
    adjustment = None
    item, kilometres = log.support_item, log.kilometres
    if can_adjust:
        adjustment = BillingAdjustmentForm(data=data, prefix=f"adjustment-{log.pk}", service_log=log)
        if data is not None:
            adjustment.is_valid()
        item, kilometres = adjustment.effective_item, adjustment.effective_kilometres
    return {
        "service_log": log, "participant_cancellation": None,
        "adjustment_form": adjustment,
        "travel_form": TravelClaimForm(
            data=data, prefix=f"travel-{log.pk}", service_log=log,
            confirmed_kilometres=kilometres if can_adjust else None,
        ),
        "billing_item": item, "billing_unit_price": item.price_limit,
        "billing_line_total": service_total(log.actual_hours, item.price_limit),
        "effective_kilometres": kilometres,
        "original_item_group": support_item_picker_group(log.support_item),
        "billing_item_group": support_item_picker_group(item),
    }


def valid_billing_rows(rows):
    valid = True
    for row in rows:
        if row["adjustment_form"] is not None and not row["adjustment_form"].is_valid():
            valid = False
        if not row["travel_form"].is_valid():
            valid = False
    return valid


def billing_snapshot(log, item, kilometres):
    return {
        "item_number": item.item_number, "item_name": item.name,
        "unit_price": str(item.price_limit), "hours": str(log.actual_hours),
        "kilometres": str(kilometres),
        "service_total": str(service_total(log.actual_hours, item.price_limit)),
    }


@transaction.atomic
def create_service_invoice(*, actor, form_data, logs, cancellations, data, can_adjust, travel_item_number):
    # Lock only source rows, in a stable order, then check eligibility again.
    locked_logs = list(ServiceLog.objects.select_for_update(of=("self",)).filter(
        pk__in=[log.pk for log in logs],
    ).select_related("support_item").order_by("pk"))
    locked_cancellations = list(ParticipantCancellation.objects.select_for_update(of=("self",)).filter(
        pk__in=[row.pk for row in cancellations],
    ).select_related("shift__support_item").order_by("pk"))
    if len(locked_logs) != len(logs) or len(locked_cancellations) != len(cancellations):
        raise BillingRecordsChanged("Selected billing records have changed. Refresh the preview.")
    # Acquisition order avoids deadlocks; invoice lines retain the existing preview order.
    log_order = {log.pk: index for index, log in enumerate(logs)}
    cancellation_order = {row.pk: index for index, row in enumerate(cancellations)}
    locked_logs.sort(key=lambda log: log_order[log.pk])
    locked_cancellations.sort(key=lambda row: cancellation_order[row.pk])
    for log in locked_logs:
        if (log.status != ServiceLog.Status.APPROVED or log.invoice_lines.exists()
                or log.participant_id != form_data["participant"].pk
                or not form_data["period_start"] <= log.service_date <= form_data["period_end"]):
            raise BillingRecordsChanged("Selected service logs are no longer available for invoicing.")
    for cancellation in locked_cancellations:
        if (cancellation.status != ParticipantCancellation.Status.APPROVED or cancellation.invoice_lines.exists()
                or cancellation.shift.participant_id != form_data["participant"].pk
                or not form_data["period_start"] <= cancellation.shift.service_date <= form_data["period_end"]):
            raise BillingRecordsChanged("Selected cancellation charges are no longer available for invoicing.")
    rows = [build_service_billing_row(log, data, can_adjust=can_adjust) for log in locked_logs]
    if not valid_billing_rows(rows):
        raise BillingRecordsChanged("Billing details have changed. Review the preview and try again.")
    claims = {row["service_log"].pk: row["travel_form"].cleaned_data["amount"] for row in rows}
    travel_item = None
    if any(claims.values()):
        travel_item = SupportItem.objects.filter(item_number=travel_item_number, is_active=True).first()
        if travel_item is None:
            raise BillingRecordsChanged(
                "The active Provider travel - non-labour support item is required before travel claims can be invoiced."
            )
    invoice = Invoice.objects.create(
        participant=form_data["participant"], period_start=form_data["period_start"],
        period_end=form_data["period_end"], created_by=actor,
    )
    for row in rows:
        log, item = row["service_log"], row["billing_item"]
        InvoiceLine.objects.create_from_service_log(invoice, log, billing_support_item=item)
        amount = claims[log.pk]
        travel_line = None
        if amount:
            travel_line = InvoiceLine.objects.create_travel_claim_from_service_log(
                invoice, log, travel_item, amount,
            )
        adjustment = row["adjustment_form"]
        if adjustment is not None and adjustment.is_adjusted:
            billed = billing_snapshot(log, item, row["effective_kilometres"])
            billed.update(travel_claim_amount=str(amount), travel_line_total=str(travel_line.line_total if travel_line else Decimal("0.00")))
            InvoiceBillingAdjustment.objects.create(
                service_log=log, invoice=invoice, invoice_number=invoice.invoice_number,
                original_values=billing_snapshot(log, log.support_item, log.kilometres),
                billing_values=billed, reason=adjustment.reason_text, created_by=actor,
            )
        log.status = ServiceLog.Status.INVOICED
        log.save(update_fields=["status", "updated_at"])
    for cancellation in locked_cancellations:
        InvoiceLine.objects.create_from_participant_cancellation(invoice, cancellation)
    write_audit_log(actor, AuditLog.Action.INVOICE_CREATED, invoice, f"Created invoice {invoice.invoice_number}.")
    return invoice
