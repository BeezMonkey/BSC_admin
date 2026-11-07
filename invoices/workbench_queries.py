"""Read-only period queries. Query count does not depend on participant count."""
from datetime import date, timedelta
from decimal import Decimal
from urllib.parse import urlencode

from django.db.models import Count, Min, Prefetch, Q
from django.urls import reverse
from django.utils import timezone

from participants.models import Participant
from scheduling.models import ParticipantCancellation, Shift
from service_logs.follow_up import missing_log_summary
from service_logs.models import ServiceLog

from .billing import service_total
from .workbench_actions import billing_catalog, source_fingerprint
from .models import Invoice, InvoiceLine
from .selectors import billable_cancellations_in_period, billable_logs_in_period


def _log_row(log):
    shift = log.shift
    return {
        'log': log, 'shift': shift,
        'unscheduled': log.source == ServiceLog.Source.UNSCHEDULED,
        'hours_differ': log.actual_hours != shift.planned_hours,
        'time_window_differ': (log.actual_start_time, log.actual_end_time) != (shift.start_time, shift.end_time),
        'break_differ': log.break_minutes != shift.break_minutes,
        'hours_difference': log.actual_hours - shift.planned_hours,
    }


def _delivery(participant):
    if participant.management_type != Participant.ManagementType.PLAN_MANAGED:
        return 'Manual handling'
    return participant.plan_manager_email.strip() or 'PM email missing'


def build_weekly_workbench(period_start, period_end):
    shifts_qs = Shift.objects.filter(service_date__range=(period_start, period_end))
    # This is the existing canonical missing-log rule, including cancellation exclusions.
    missing = missing_log_summary(shifts_qs)
    missing_ids = {shift.pk for group in missing['missing_log_groups'] for shift in group['shifts']}
    shifts = list(shifts_qs.select_related('participant', 'worker', 'support_item', 'service_log'))
    logs = list(ServiceLog.objects.filter(service_date__range=(period_start, period_end)).select_related(
        'participant', 'worker', 'support_item', 'shift', 'shift__support_item',
        'shift__participant', 'shift__worker',
    ).order_by('service_date', 'actual_start_time', 'id'))
    cancellations = list(ParticipantCancellation.objects.filter(
        shift__service_date__range=(period_start, period_end),
    ).select_related('shift', 'shift__participant', 'shift__worker', 'shift__support_item'))
    billable_logs = list(billable_logs_in_period(period_start, period_end))
    billable_cancellations = list(billable_cancellations_in_period(period_start, period_end))
    source_period = (
        Q(lines__service_log__service_date__range=(period_start, period_end))
        | Q(lines__participant_cancellation__shift__service_date__range=(period_start, period_end))
    )
    # Prefetch all saved lines, so totals and actual coverage include the whole invoice.
    invoices = list(Invoice.objects.filter(source_period, invoice_type=Invoice.InvoiceType.SERVICE)
        .distinct().select_related('participant').prefetch_related(Prefetch('lines', queryset=
            InvoiceLine.objects.select_related('service_log', 'participant_cancellation__shift'))))
    log_rows = [_log_row(log) for log in logs]
    logs_by_shift = {row['shift'].pk: row for row in log_rows}
    cancellations_by_shift = {row.shift_id: row for row in cancellations}
    local_now = timezone.localtime()
    roster_rows = []
    for shift in shifts:
        comparison = logs_by_shift.get(shift.pk)
        cancellation = cancellations_by_shift.get(shift.pk)
        log = comparison['log'] if comparison else None
        if cancellation and cancellation.status != ParticipantCancellation.Status.REJECTED:
            status = 'Cancellation · ' + cancellation.get_status_display()
        elif log:
            status = log.get_status_display()
        elif shift.pk in missing_ids:
            status = 'Missing'
        elif (shift.source == Shift.Source.SCHEDULED
                and shift.status in (Shift.Status.PUBLISHED, Shift.Status.CONFIRMED)
                and not hasattr(shift, 'service_log')
                and (shift.service_date > local_now.date() or (
                    shift.service_date == local_now.date() and shift.end_time > local_now.time()))):
            status = 'Upcoming'
        elif hasattr(shift, 'service_log'):
            status = 'Log outside period'
        else:
            status = shift.get_status_display()
        roster_rows.append({'shift': shift, 'log': log, 'comparison': comparison,
                            'cancellation': cancellation, 'status': status,
                            'unscheduled': shift.source == Shift.Source.UNSCHEDULED})
    shift_ids = {shift.pk for shift in shifts}
    for row in log_rows:
        if row['shift'].pk not in shift_ids:
            roster_rows.append({'shift': row['shift'], 'log': row['log'], 'comparison': row,
                                'status': row['log'].get_status_display(), 'unscheduled': row['unscheduled']})

    groups = {}
    def group_for(participant):
        return groups.setdefault(participant.pk, {
            'participant': participant, 'approved_log_count': 0, 'approved_cancellation_count': 0,
            'missing_count': 0, 'pending_count': 0, 'rejected_count': 0,
            'service_estimate': Decimal('0.00'), 'hours': Decimal('0.00'),
            'kilometres': Decimal('0.00'), 'source_dates': [], 'invoice_count': 0,
            'delivery': _delivery(participant), 'upcoming_count': 0,
            '_logs': [], '_cancellations': [],
        })
    for shift in shifts:
        row = group_for(shift.participant)
        row['missing_count'] += int(shift.pk in missing_ids)
    for roster_row in roster_rows:
        if roster_row['status'] == 'Upcoming':
            group_for(roster_row['shift'].participant)['upcoming_count'] += 1
    for log in logs:
        row = group_for(log.participant)
        row['pending_count'] += int(log.status == ServiceLog.Status.SUBMITTED)
        row['rejected_count'] += int(log.status == ServiceLog.Status.REJECTED)
    for cancellation in cancellations:
        row = group_for(cancellation.shift.participant)
        row['pending_count'] += int(cancellation.status == ParticipantCancellation.Status.PENDING)
    for log in billable_logs:
        row = group_for(log.participant)
        row['approved_log_count'] += 1
        row['service_estimate'] += service_total(log.actual_hours, log.support_item.price_limit)
        row['hours'] += log.actual_hours
        row['kilometres'] += log.kilometres
        row['source_dates'].append(log.service_date)
        row['_logs'].append(log)
    for cancellation in billable_cancellations:
        shift = cancellation.shift
        row = group_for(shift.participant)
        row['approved_cancellation_count'] += 1
        row['service_estimate'] += service_total(shift.planned_hours, shift.support_item.price_limit)
        row['hours'] += shift.planned_hours
        row['source_dates'].append(shift.service_date)
        row['_cancellations'].append(cancellation)
    invoice_rows = []
    for invoice in invoices:
        group_for(invoice.participant)['invoice_count'] += 1
        lines = list(invoice.lines.all())
        dates = [line.service_log.service_date if line.service_log_id
                 else line.participant_cancellation.shift.service_date
                 for line in lines if line.service_log_id or line.participant_cancellation_id]
        invoice_rows.append({'invoice': invoice, 'delivery': _delivery(invoice.participant),
                             'total': sum((line.line_total for line in lines), Decimal('0.00')),
                             'source_start': min(dates) if dates else None,
                             'source_end': max(dates) if dates else None})
    catalog = billing_catalog()
    for row in groups.values():
        row['source_key'] = source_fingerprint(sorted(row.pop('_logs'), key=lambda obj: obj.pk),
            sorted(row.pop('_cancellations'), key=lambda obj: obj.pk), catalog=catalog)
        row['billable_count'] = row['approved_log_count'] + row['approved_cancellation_count']
        row['blocker_count'] = row['missing_count'] + row['pending_count'] + row['rejected_count']
        if row['billable_count']:
            row['readiness'] = 'Partial' if row['blocker_count'] else 'Additional' if row['invoice_count'] else 'Ready'
        elif row['blocker_count']:
            row['readiness'] = 'Waiting'
        elif row['upcoming_count'] and not row['invoice_count']:
            row['readiness'] = 'Upcoming'
        else:
            row['readiness'] = 'No unbilled sources'
        row['actual_start'] = min(row['source_dates']) if row['source_dates'] else None
        row['actual_end'] = max(row['source_dates']) if row['source_dates'] else None
    earlier = {'logs': {'count': 0, 'first': None}, 'cancellations': {'count': 0, 'first': None}}
    if period_start > date.min:
        earlier_end = period_start - timedelta(days=1)
        earlier['logs'] = billable_logs_in_period(date.min, earlier_end).aggregate(count=Count('pk'), first=Min('service_date'))
        earlier['cancellations'] = billable_cancellations_in_period(date.min, earlier_end).aggregate(count=Count('pk'), first=Min('shift__service_date'))
    earlier_dates = [row['first'] for row in earlier.values() if row['first']]
    earlier_url = ''
    if earlier_dates:
        first = min(earlier_dates)
        earlier_url = reverse('weekly_billing') + '?' + urlencode({'period': 'custom', 'start': first.isoformat(), 'end': (period_start - timedelta(days=1)).isoformat()})
    return {
        **missing, 'roster_rows': roster_rows, 'log_rows': log_rows,
        'submitted_rows': [row for row in log_rows if row['log'].status == ServiceLog.Status.SUBMITTED],
        'cancellations': cancellations,
        'pending_cancellation_count': sum(row.status == ParticipantCancellation.Status.PENDING for row in cancellations),
        'participant_rows': sorted(groups.values(), key=lambda row: (row['participant'].last_name, row['participant'].first_name)),
        'invoice_rows': invoice_rows,
        'earlier_unbilled_count': sum(row['count'] for row in earlier.values()), 'earlier_url': earlier_url,
    }
