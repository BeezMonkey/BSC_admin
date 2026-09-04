from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    class Action(models.TextChoices):
        SERVICE_LOG_APPROVED = "service_log_approved", "Service log approved"
        SERVICE_LOG_REJECTED = "service_log_rejected", "Service log rejected"
        SHIFT_CANCELLED = "shift_cancelled", "Shift cancelled"
        INVOICE_CREATED = "invoice_created", "Invoice created"
        INVOICE_MARKED_ISSUED = "invoice_marked_issued", "Invoice marked issued"
        INVOICE_MARKED_PAID = "invoice_marked_paid", "Invoice marked paid"
        INVOICE_CANCELLED = "invoice_cancelled", "Invoice cancelled"
        INVOICE_DELETED = "invoice_deleted", "Invoice deleted"
        DOCUMENT_UPLOADED = "document_uploaded", "Document uploaded"
        DOCUMENT_APPROVED = "document_approved", "Document approved"
        DOCUMENT_REJECTED = "document_rejected", "Document rejected"
        DOCUMENT_DOWNLOADED = "document_downloaded", "Document downloaded"
        SUPPORT_COORDINATOR_CREATED = (
            "support_coordinator_created",
            "Support coordinator created",
        )
        SUPPORT_COORDINATOR_UPDATED = (
            "support_coordinator_updated",
            "Support coordinator updated",
        )
        PARTICIPANT_COORDINATOR_ASSIGNED = (
            "participant_coordinator_assigned",
            "Participant assigned to support coordinator",
        )
        COORDINATION_LOG_SUBMITTED = (
            "coordination_log_submitted",
            "Coordination log submitted",
        )
        COORDINATION_LOG_APPROVED = (
            "coordination_log_approved",
            "Coordination log approved",
        )
        COORDINATION_LOG_REJECTED = (
            "coordination_log_rejected",
            "Coordination log rejected",
        )

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
        null=True,
        blank=True,
    )
    action = models.CharField(max_length=50, choices=Action.choices)
    object_type = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100)
    summary = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_action_display()} - {self.object_type} {self.object_id}"
