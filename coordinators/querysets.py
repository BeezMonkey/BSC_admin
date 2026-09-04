from participants.models import Participant

from .models import SupportCoordinator


def assigned_participants_for(coordinator):
    if coordinator is None:
        return Participant.objects.none()
    return Participant.objects.filter(
        status=Participant.Status.ACTIVE,
        coordinator_assignments__coordinator=coordinator,
        coordinator_assignments__is_active=True,
        coordinator_assignments__coordinator__status=SupportCoordinator.Status.ACTIVE,
    ).distinct()
