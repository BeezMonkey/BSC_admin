"""Canonical participant-cancellation review transitions."""

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

from accounts.permissions import ADMIN_ROLES, has_role
from core.audit import write_audit_log
from core.models import AuditLog

from .models import ParticipantCancellation, Shift


class CancellationReviewConflict(ValueError):
    """The source no longer exists or is no longer awaiting review."""


@transaction.atomic
def review_participant_cancellation(*, actor, cancellation_id, decision, admin_note=""):
    """Review a pending cancellation and its shift in one audited transaction.

    PermissionDenied denies non-admin callers; ValueError rejects invalid input;
    CancellationReviewConflict rejects missing or already-reviewed sources.
    """
    if not getattr(actor, "is_authenticated", False) or not has_role(actor, ADMIN_ROLES):
        raise PermissionDenied
    decisions = {
        "approve": (
            ParticipantCancellation.Status.APPROVED,
            AuditLog.Action.PARTICIPANT_CANCELLATION_APPROVED,
            "Cancellation approved for charging.",
        ),
        "waive": (
            ParticipantCancellation.Status.WAIVED,
            AuditLog.Action.PARTICIPANT_CANCELLATION_WAIVED,
            "Cancellation recorded and charge waived.",
        ),
        "reject": (
            ParticipantCancellation.Status.REJECTED,
            AuditLog.Action.PARTICIPANT_CANCELLATION_REJECTED,
            "Cancellation report rejected.",
        ),
    }
    if decision not in decisions:
        raise ValueError("Choose approve, waive or reject for the cancellation.")
    admin_note = admin_note.strip()
    if decision == "reject" and not admin_note:
        raise ValueError("Add an admin note before rejecting the report.")

    # Submission locks Shift first. Keep that order and avoid joined-row locks.
    shift_id = ParticipantCancellation.objects.filter(pk=cancellation_id).values_list("shift_id", flat=True).first()
    if shift_id is None:
        raise CancellationReviewConflict("Cancellation is no longer awaiting review.")
    try:
        shift = Shift.objects.select_for_update(of=("self",)).get(pk=shift_id)
        cancellation = ParticipantCancellation.objects.select_for_update(of=("self",)).get(
            pk=cancellation_id, shift_id=shift_id,
        )
    except (Shift.DoesNotExist, ParticipantCancellation.DoesNotExist) as exc:
        raise CancellationReviewConflict("Cancellation is no longer awaiting review.") from exc
    if cancellation.status != ParticipantCancellation.Status.PENDING:
        raise CancellationReviewConflict("Cancellation is no longer awaiting review.")

    status, audit_action, message = decisions[decision]
    cancellation.status = status
    cancellation.admin_note = admin_note
    cancellation.reviewed_by = actor
    cancellation.reviewed_at = timezone.now()
    cancellation.save(update_fields=[
        "status", "admin_note", "reviewed_by", "reviewed_at", "updated_at",
    ])
    shift.status = cancellation.previous_shift_status if decision == "reject" else Shift.Status.CANCELLED
    shift.save(update_fields=["status", "updated_at"])
    cancellation.shift = shift
    write_audit_log(actor, audit_action, cancellation, f"{message} Shift {shift.id}.")
    return cancellation
