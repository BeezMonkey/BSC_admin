"""Shared billing eligibility; existing participant wrappers keep their contract."""
from service_logs.models import ServiceLog
from scheduling.models import ParticipantCancellation


def billable_logs_in_period(period_start, period_end):
    return ServiceLog.objects.filter(
        service_date__gte=period_start,
        service_date__lte=period_end,
        status=ServiceLog.Status.APPROVED,
        invoice_lines__isnull=True,
    ).select_related('participant', 'worker', 'support_item')


def get_billable_logs(participant, period_start, period_end):
    return billable_logs_in_period(period_start, period_end).filter(participant=participant)


def billable_cancellations_in_period(period_start, period_end):
    return ParticipantCancellation.objects.filter(
        shift__service_date__gte=period_start,
        shift__service_date__lte=period_end,
        status=ParticipantCancellation.Status.APPROVED,
        invoice_lines__isnull=True,
    ).select_related(
        'shift', 'shift__participant', 'shift__worker', 'shift__support_item',
    ).order_by('shift__service_date', 'shift__start_time', 'id')


def get_billable_cancellations(participant, period_start, period_end):
    return billable_cancellations_in_period(period_start, period_end).filter(shift__participant=participant)
