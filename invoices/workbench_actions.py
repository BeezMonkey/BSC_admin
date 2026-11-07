"""Explicit, signed weekly previews over the existing billing transaction."""
import hashlib
import json
import uuid
from decimal import Decimal

from django.core import signing
from django.db import transaction
from django.db.models import Q

from accounts.permissions import ADMIN_ROLES, has_role
from django.core.exceptions import PermissionDenied
from core.models import AuditLog
from scheduling.models import ParticipantCancellation, Shift, SupportItem
from service_logs.models import ServiceLog

from .billing import (BillingRecordsChanged, build_service_billing_row,
                      create_service_invoice, service_total, valid_billing_rows)
from .models import Invoice
from .forms import InvoiceCreateForm
from .selectors import get_billable_cancellations, get_billable_logs

TRAVEL_ITEM = '04_799_0125_6_1'
SALT = 'invoices.weekly.preview.v1'
MAX_AGE = 8 * 60 * 60


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def billing_catalog():
    return list(SupportItem.objects.filter(is_active=True).filter(
        Q(unit=SupportItem.Unit.HOUR) | Q(item_number=TRAVEL_ITEM)
    ).order_by('pk').values('pk', 'item_number', 'name', 'unit', 'price_limit', 'gst_code'))


def _sources(participant, start, end):
    logs = list(get_billable_logs(participant, start, end).order_by('pk'))
    cancellations = list(get_billable_cancellations(participant, start, end).order_by('pk'))
    return logs, cancellations


def source_fingerprint(logs, cancellations, *, catalog=None):
    # Include copied log values and rostered cancellation values, even if a bulk
    # update omitted auto_now. An unchanged preview must mean unchanged billing.
    originals = {log.support_item_id: log.support_item for log in logs}
    originals.update({c.shift.support_item_id: c.shift.support_item for c in cancellations})
    return _digest({
        'logs': [[log.pk, log.updated_at, log.shift_id, log.participant_id, log.service_date,
                  log.actual_start_time, log.actual_end_time, log.break_minutes,
                  log.actual_hours, log.support_item_id, log.kilometres] for log in logs],
        'cancellations': [[c.pk, c.updated_at, c.shift_id, c.shift.participant_id,
                           c.shift.service_date, c.shift.planned_hours,
                           c.shift.support_item_id] for c in cancellations],
        'catalog': billing_catalog() if catalog is None else catalog,
        # Keep-original remains legal for inactive/non-hour historical items.
        # Their actual billed values must also be protected from silent changes.
        'original_items': [[key, item.item_number, item.name, item.unit,
                            item.price_limit, item.gst_code, item.is_active]
                           for key, item in sorted(originals.items())],
    })


def _scope(actor, session_key, participant, start, end):
    return {'actor': actor.pk, 'session': _digest(session_key), 'participant': participant.pk,
            'start': start.isoformat(), 'end': end.isoformat()}


def build_preview(*, actor, session_key, participant, start, end, data=None, tokens=None):
    logs, cancellations = _sources(participant, start, end)
    dates = [log.service_date for log in logs] + [c.shift.service_date for c in cancellations]
    if not dates:
        raise BillingRecordsChanged('No approved unbilled sources remain. Refresh the workbench.')
    rows = [build_service_billing_row(log, data, can_adjust=True) for log in logs]
    rows.extend({'service_log': None, 'participant_cancellation': c, 'travel_form': None,
                 'billing_hours': c.shift.planned_hours,
                 'billing_unit_price': c.shift.support_item.price_limit,
                 'billing_line_total': service_total(c.shift.planned_hours, c.shift.support_item.price_limit)}
                for c in cancellations)
    rows.sort(key=lambda row: (row['service_log'].service_date if row['service_log'] else
                               row['participant_cancellation'].shift.service_date,
                               row['service_log'].pk if row['service_log'] else row['participant_cancellation'].pk))
    if tokens is None:
        payload = {**_scope(actor, session_key, participant, start, end),
                   'logs': [log.pk for log in logs], 'cancellations': [c.pk for c in cancellations],
                   'fingerprint': source_fingerprint(logs, cancellations)}
        tokens = {mode: signing.dumps({**payload, 'mode': mode, 'intent': uuid.uuid4().hex},
                                     salt=SALT, compress=True) for mode in ('workbench', 'actual')}
    travel = SupportItem.objects.filter(item_number=TRAVEL_ITEM, is_active=True).first()
    price = travel.price_limit if travel else Decimal('0.00')
    total = sum((row['billing_line_total'] for row in rows), Decimal('0.00'))
    for row in rows:
        if row['travel_form'] is not None and data is not None and row['travel_form'].is_valid():
            total += service_total(row['travel_form'].cleaned_data['amount'], price)
    return {'participant': participant, 'logs': logs, 'cancellations': cancellations, 'rows': rows,
            'actual_start': min(dates), 'actual_end': max(dates), 'tokens': tokens,
            'travel_unit_price': price, 'travel_available': travel is not None, 'total': total,
            'period_mode': data.get('period_mode', 'workbench') if data is not None else 'workbench'}


def _read_token(token, actor, session_key, participant, start, end, mode):
    try:
        payload = signing.loads(token, salt=SALT, max_age=MAX_AGE)
    except signing.BadSignature as exc:
        raise BillingRecordsChanged('This preview has expired or changed. Refresh the preview.') from exc
    expected = {**_scope(actor, session_key, participant, start, end), 'mode': mode}
    if any(payload.get(key) != value for key, value in expected.items()):
        raise BillingRecordsChanged('The participant or billing period changed. Refresh the preview.')
    return payload


def _recover(payload, actor):
    # A durable marker on the existing creation audit also covers a lost response
    # before SessionMiddleware persisted its bounded result cache.
    marker = f'[weekly-intent:{payload["intent"]}]'
    audit = AuditLog.objects.filter(actor=actor, action=AuditLog.Action.INVOICE_CREATED,
                                    object_type='Invoice', summary__endswith=marker).first()
    if audit:
        invoice = Invoice.objects.filter(pk=audit.object_id, participant_id=payload['participant']).first()
        if invoice is None or invoice.status == Invoice.Status.CANCELLED:
            raise BillingRecordsChanged('This request already created an invoice that was removed. Refresh before creating another draft.')
        return invoice
    return None


@transaction.atomic
def create_weekly_draft(*, actor, session_key, participant, start, end, data, results=None):
    if not has_role(actor, ADMIN_ROLES):
        raise PermissionDenied
    payload = _read_token(data.get('preview_token', ''), actor, session_key, participant,
                          start, end, data.get('period_mode', 'workbench'))
    cached_id = (results or {}).get(_digest_token(data.get('preview_token', '')))
    if cached_id:
        cached = Invoice.objects.filter(pk=cached_id, created_by=actor, participant=participant).first()
        if cached is None or cached.status == Invoice.Status.CANCELLED:
            raise BillingRecordsChanged('This request already created an invoice that was removed. Refresh before creating another draft.')
        return cached
    recovered = _recover(payload, actor)
    if recovered:
        return recovered
    # Stable lock order shared with review services. Explicit signed IDs are the
    # only sources ever passed to the original invoice creation service.
    shift_ids = list(ServiceLog.objects.filter(pk__in=payload['logs']).values_list('shift_id', flat=True))
    shift_ids += list(ParticipantCancellation.objects.filter(pk__in=payload['cancellations']).values_list('shift_id', flat=True))
    list(Shift.objects.select_for_update().filter(pk__in=shift_ids).order_by('pk'))
    list(ServiceLog.objects.select_for_update().filter(pk__in=payload['logs']).order_by('pk'))
    list(ParticipantCancellation.objects.select_for_update().filter(pk__in=payload['cancellations']).order_by('pk'))
    # Lock the complete signed active catalog, including any newly selected item.
    list(SupportItem.objects.select_for_update().order_by('pk'))
    recovered = _recover(payload, actor)
    if recovered:
        return recovered
    logs, cancellations = _sources(participant, start, end)
    if ([log.pk for log in logs] != payload['logs'] or [c.pk for c in cancellations] != payload['cancellations']
            or source_fingerprint(logs, cancellations) != payload['fingerprint']):
        raise BillingRecordsChanged('Sources or billing rates changed since this preview. Refresh the preview before creating a draft.')
    rows = [build_service_billing_row(log, data, can_adjust=True) for log in logs]
    if not valid_billing_rows(rows):
        raise InvalidBillingDetails('Check the highlighted billing details. Your inputs have been retained.')
    dates = [log.service_date for log in logs] + [c.shift.service_date for c in cancellations]
    invoice_start, invoice_end = (min(dates), max(dates)) if payload['mode'] == 'actual' else (start, end)
    form = InvoiceCreateForm(data={
        'participant': participant, 'period_start': invoice_start, 'period_end': invoice_end,
    })
    if not form.is_valid():
        raise InvalidBillingDetails('Check the invoice participant and dates.')
    invoice = create_service_invoice(actor=actor, form_data=form.cleaned_data,
        logs=logs, cancellations=cancellations, data=data, can_adjust=True, travel_item_number=TRAVEL_ITEM)
    audit = AuditLog.objects.get(actor=actor, action=AuditLog.Action.INVOICE_CREATED,
                                 object_type='Invoice', object_id=str(invoice.pk))
    audit.summary += f' [weekly-intent:{payload["intent"]}]'
    audit.save(update_fields=['summary'])
    return invoice


class InvalidBillingDetails(ValueError):
    pass


def _digest_token(token):
    return hashlib.sha256(token.encode()).hexdigest()
