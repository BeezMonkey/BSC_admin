from .models import AuditLog


def write_audit_log(actor, action, obj, summary):
    return AuditLog.objects.create(
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        action=action,
        object_type=obj.__class__.__name__,
        object_id=str(obj.pk),
        summary=summary,
    )
