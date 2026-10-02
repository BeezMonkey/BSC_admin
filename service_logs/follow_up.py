from django.db.models import Q
from django.utils import timezone

from scheduling.models import ParticipantCancellation, Shift


def missing_log_summary(shifts):
    local_now = timezone.localtime()
    missing_shifts = (
        shifts.filter(
            source=Shift.Source.SCHEDULED,
            status__in=(Shift.Status.PUBLISHED, Shift.Status.CONFIRMED),
            service_log__isnull=True,
        )
        .filter(
            Q(service_date__lt=local_now.date())
            | Q(service_date=local_now.date(), end_time__lte=local_now.time())
        )
        .exclude(
            participant_cancellation__status__in=(
                ParticipantCancellation.Status.PENDING,
                ParticipantCancellation.Status.APPROVED,
                ParticipantCancellation.Status.WAIVED,
            ),
        )
        .select_related("worker", "participant")
        .order_by(
            "worker__last_name", "worker__first_name", "worker_id",
            "service_date", "start_time", "id",
        )
    )
    groups = {}
    count = 0
    for shift in missing_shifts:
        group = groups.setdefault(
            shift.worker_id,
            {"worker": shift.worker, "shifts": [], "count": 0},
        )
        group["shifts"].append(shift)
        group["count"] += 1
        count += 1
    return {
        "missing_log_groups": list(groups.values()),
        "missing_log_count": count,
        "missing_worker_count": len(groups),
    }
