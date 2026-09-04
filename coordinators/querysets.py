from participants.models import Participant

from .models import CoordinationLog, SupportCoordinator


def assigned_participants_for(coordinator):
    if coordinator is None:
        return Participant.objects.none()
    return Participant.objects.filter(
        status=Participant.Status.ACTIVE,
        coordinator_assignments__coordinator=coordinator,
        coordinator_assignments__is_active=True,
        coordinator_assignments__coordinator__status=SupportCoordinator.Status.ACTIVE,
    ).distinct()


def coordination_logs_for(coordinator):
    if coordinator is None:
        return CoordinationLog.objects.none()
    return CoordinationLog.objects.filter(
        coordinator=coordinator,
        participant__in=assigned_participants_for(coordinator),
    ).select_related("participant", "coordinator")
