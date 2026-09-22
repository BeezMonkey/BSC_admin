from itertools import combinations

from django.db import transaction

from core.audit import write_audit_log
from core.models import AuditLog

from .models import PlannedMultiWorkerSupport


def shift_pair_key(first_shift, second_shift):
    return tuple(sorted((first_shift.id, second_shift.id)))


@transaction.atomic
def approve_multi_worker_support(shifts, reason, notes, approved_by):
    shifts = list({shift.id: shift for shift in shifts}.values())
    if len(shifts) < 2:
        raise ValueError("Multi-worker support requires at least two shifts.")

    participant_ids = {shift.participant_id for shift in shifts}
    service_dates = {shift.service_date for shift in shifts}
    worker_ids = {shift.worker_id for shift in shifts}
    if len(participant_ids) != 1 or len(service_dates) != 1:
        raise ValueError("Selected shifts must have the same participant and date.")
    if len(worker_ids) != len(shifts):
        raise ValueError("Each selected shift must have a different worker.")

    overlap_start_time = max(shift.start_time for shift in shifts)
    overlap_end_time = min(shift.end_time for shift in shifts)
    if overlap_start_time >= overlap_end_time:
        raise ValueError("Selected shifts must share an overlapping time window.")

    selected_shift_ids = {shift.id for shift in shifts}
    related_supports = []
    for support in (
        PlannedMultiWorkerSupport.objects.filter(shifts__in=shifts)
        .distinct()
        .prefetch_related("shifts")
    ):
        support_shift_ids = {shift.id for shift in support.shifts.all()}
        if (
            support_shift_ids.issubset(selected_shift_ids)
            or selected_shift_ids.issubset(support_shift_ids)
        ):
            related_supports.append(support)
    invalidate_multi_worker_support_records(
        related_supports,
        approved_by,
        "Replaced by a new multi-worker support approval.",
    )
    support = PlannedMultiWorkerSupport.objects.create(
        participant_id=shifts[0].participant_id,
        service_date=shifts[0].service_date,
        overlap_start_time=overlap_start_time,
        overlap_end_time=overlap_end_time,
        worker_count=len(shifts),
        reason=reason,
        notes=notes,
        approved_by=approved_by,
    )
    support.shifts.add(*shifts)
    write_audit_log(
        approved_by,
        AuditLog.Action.MULTI_WORKER_SUPPORT_APPROVED,
        support,
        (
            f"Approved {support.worker_count}:1 support for "
            f"{support.participant.display_name} on {support.service_date}."
        ),
    )
    return support


def invalidate_multi_worker_supports(shifts, actor, reason):
    supports = list(
        PlannedMultiWorkerSupport.objects.filter(shifts__in=list(shifts)).distinct()
    )
    return invalidate_multi_worker_support_records(supports, actor, reason)


def invalidate_multi_worker_support_records(supports, actor, reason):
    for support in supports:
        write_audit_log(
            actor,
            AuditLog.Action.MULTI_WORKER_SUPPORT_INVALIDATED,
            support,
            (
                f"Invalidated {support.worker_count}:1 support for "
                f"{support.participant.display_name} on {support.service_date}. "
                f"{reason}"
            ),
        )
        support.delete()
    return len(supports)


@transaction.atomic
def approve_overlap_groups(primary_shift, overlap_shifts, reason, notes, approved_by):
    shifts = list(
        {shift.id: shift for shift in [primary_shift, *overlap_shifts]}.values()
    )
    boundaries = sorted(
        {boundary for shift in shifts for boundary in (shift.start_time, shift.end_time)}
    )
    active_shift_sets = set()
    shifts_by_id = {shift.id: shift for shift in shifts}
    for interval_start, interval_end in zip(boundaries, boundaries[1:]):
        active_ids = frozenset(
            shift.id
            for shift in shifts
            if shift.start_time < interval_end and shift.end_time > interval_start
        )
        if len(active_ids) >= 2 and primary_shift.id in active_ids:
            active_shift_sets.add(active_ids)

    maximal_shift_sets = [
        shift_ids
        for shift_ids in active_shift_sets
        if not any(shift_ids < other_ids for other_ids in active_shift_sets)
    ]
    supports = []
    for shift_ids in sorted(maximal_shift_sets, key=lambda ids: (min(ids), len(ids))):
        supports.append(
            approve_multi_worker_support(
                [shifts_by_id[shift_id] for shift_id in shift_ids],
                reason,
                notes,
                approved_by,
            )
        )
    return supports


def approved_shift_pairs(supports):
    pairs = set()
    support_by_shift_id = {}
    for support in supports:
        support_shifts = list(support.shifts.all())
        for shift in support_shifts:
            current_support = support_by_shift_id.get(shift.id)
            if not current_support or support.worker_count > current_support.worker_count:
                support_by_shift_id[shift.id] = support
        for first_shift, second_shift in combinations(support_shifts, 2):
            pairs.add(shift_pair_key(first_shift, second_shift))
    return pairs, support_by_shift_id
