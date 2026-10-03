from datetime import date, datetime, time
from decimal import Decimal

from django.core import signing

from core.audit import write_audit_log
from core.models import AuditLog

from .models import CoordinationLogChange


EDITABLE_FIELDS = (
    "service_date", "start_time", "end_time", "break_minutes", "actual_hours",
    "coordination_type", "case_notes", "coordinator_notes",
)
TOKEN_SALT = "coordinators.log-revision"


def revision_token(log):
    return signing.dumps({"id": log.pk, "updated_at": log.updated_at.isoformat()}, salt=TOKEN_SALT)


def revision_is_current(log, token):
    try:
        return signing.loads(token, salt=TOKEN_SALT) == {
            "id": log.pk, "updated_at": log.updated_at.isoformat(),
        }
    except (signing.BadSignature, TypeError, ValueError):
        return False


def log_snapshot(log):
    fields = EDITABLE_FIELDS + (
        "participant_id", "coordinator_id", "status", "reviewed_by_id",
        "reviewed_at", "rejection_reason", "submitted_at",
    )
    snapshot = {}
    for field in fields:
        value = getattr(log, field)
        if isinstance(value, (date, datetime, time)):
            value = value.isoformat()
        elif isinstance(value, Decimal):
            value = str(value)
        snapshot[field] = value
    snapshot["reviewed_by"] = str(log.reviewed_by) if log.reviewed_by_id else ""
    return snapshot


def record_log_change(log, actor, kind, before, *, reason="", details=""):
    """Call within the transaction holding the coordination log's row lock."""
    change = CoordinationLogChange.objects.create(
        log=log, actor=actor, kind=kind, before=before, after=log_snapshot(log),
        reason=reason, details=details,
    )
    actions = {
        CoordinationLogChange.Kind.REVISION: AuditLog.Action.COORDINATION_LOG_REVISED,
        CoordinationLogChange.Kind.APPROVAL: AuditLog.Action.COORDINATION_LOG_APPROVED,
        CoordinationLogChange.Kind.REJECTION: AuditLog.Action.COORDINATION_LOG_REJECTED,
        CoordinationLogChange.Kind.CORRECTION: AuditLog.Action.COORDINATION_LOG_CORRECTED,
        CoordinationLogChange.Kind.BILLING_REVIEW: AuditLog.Action.COORDINATION_LOG_CORRECTED,
    }
    summary = f"{change.get_kind_display()} coordination log {log.pk}. Change {change.pk}."
    write_audit_log(actor, actions[kind], log, summary)
    return change
