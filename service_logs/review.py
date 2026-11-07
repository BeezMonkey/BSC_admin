"""Canonical service-log review transitions shared by admin entry points."""

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

from accounts.permissions import ADMIN_ROLES, has_role
from core.audit import write_audit_log
from core.models import AuditLog
from scheduling.models import Shift

from .models import ServiceLog


class ServiceLogReviewConflict(ValueError):
    """The source no longer exists or is no longer awaiting review."""


@transaction.atomic
def review_service_log(*, actor, service_log_id, decision, reason=""):
    """Review a submitted log once, recording the decision and audit atomically.

    PermissionDenied denies non-admin callers; ValueError rejects invalid input;
    ServiceLogReviewConflict rejects missing or already-reviewed sources.
    """
    if not getattr(actor, "is_authenticated", False) or not has_role(actor, ADMIN_ROLES):
        raise PermissionDenied
    if decision not in ("approve", "reject"):
        raise ValueError("Choose approve or reject for the service log.")
    reason = reason.strip()
    if decision == "reject" and not reason:
        raise ValueError("Rejection reason is required.")

    # Lock the source shift first, matching cancellation submission/review order.
    shift_id = ServiceLog.objects.filter(pk=service_log_id).values_list("shift_id", flat=True).first()
    if shift_id is None:
        raise ServiceLogReviewConflict("Service log is no longer awaiting review.")
    try:
        Shift.objects.select_for_update(of=("self",)).get(pk=shift_id)
        service_log = ServiceLog.objects.select_for_update(of=("self",)).get(
            pk=service_log_id, shift_id=shift_id,
        )
    except (Shift.DoesNotExist, ServiceLog.DoesNotExist) as exc:
        raise ServiceLogReviewConflict("Service log is no longer awaiting review.") from exc
    if service_log.status != ServiceLog.Status.SUBMITTED:
        raise ServiceLogReviewConflict("Service log is no longer awaiting review.")

    approved = decision == "approve"
    service_log.status = ServiceLog.Status.APPROVED if approved else ServiceLog.Status.REJECTED
    service_log.reviewed_by = actor
    service_log.reviewed_at = timezone.now()
    service_log.rejection_reason = "" if approved else reason
    service_log.save(update_fields=[
        "status", "reviewed_by", "reviewed_at", "rejection_reason", "updated_at",
    ])
    write_audit_log(
        actor,
        AuditLog.Action.SERVICE_LOG_APPROVED if approved else AuditLog.Action.SERVICE_LOG_REJECTED,
        service_log,
        f"{'Approved' if approved else 'Rejected'} service log {service_log.id}.",
    )
    return service_log
