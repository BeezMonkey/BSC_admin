from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime, parse_time
from django.utils.formats import date_format


class SupportCoordinator(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=30, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return self.display_name

    @property
    def display_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def initials(self):
        parts = [self.first_name, self.last_name]
        letters = [part.strip()[0] for part in parts if part and part.strip()]
        return "".join(letters[:2]).upper() or "C"

    def get_absolute_url(self):
        return reverse("coordinator_detail", args=[self.id])


class ParticipantCoordinatorAssignment(models.Model):
    participant = models.ForeignKey(
        "participants.Participant",
        on_delete=models.CASCADE,
        related_name="coordinator_assignments",
    )
    coordinator = models.ForeignKey(
        SupportCoordinator,
        on_delete=models.CASCADE,
        related_name="participant_assignments",
    )
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_active", "-start_date", "coordinator__last_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["participant", "coordinator"],
                condition=models.Q(is_active=True),
                name="unique_active_participant_coordinator_assignment",
            )
        ]

    def __str__(self):
        return f"{self.participant} -> {self.coordinator}"


class CoordinationLog(models.Model):
    class Status(models.TextChoices):
        SUBMITTED = "submitted", "Submitted"
        APPROVED = "approved", "Approved"
        INVOICED = "invoiced", "Invoiced"
        REJECTED = "rejected", "Rejected"

    class CoordinationType(models.TextChoices):
        GENERAL = "general", "General coordination"
        PARTICIPANT_CONTACT = "participant_contact", "Participant / family contact"
        PROVIDER_CONTACT = "provider_contact", "Provider contact"
        PLAN_REVIEW = "plan_review", "Plan review / funding discussion"
        INCIDENT_FOLLOW_UP = "incident_follow_up", "Incident or concern follow-up"
        OTHER = "other", "Other"

    participant = models.ForeignKey(
        "participants.Participant",
        on_delete=models.PROTECT,
        related_name="coordination_logs",
    )
    coordinator = models.ForeignKey(
        SupportCoordinator,
        on_delete=models.PROTECT,
        related_name="coordination_logs",
    )
    service_date = models.DateField()
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    break_minutes = models.PositiveIntegerField(default=0)
    actual_hours = models.DecimalField(max_digits=6, decimal_places=2)
    coordination_type = models.CharField(
        max_length=40,
        choices=CoordinationType.choices,
        default=CoordinationType.GENERAL,
    )
    case_notes = models.TextField()
    coordinator_notes = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SUBMITTED,
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reviewed_coordination_logs",
        null=True,
        blank=True,
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    submitted_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-service_date", "-submitted_at"]

    def __str__(self):
        return f"{self.service_date} {self.participant} / {self.coordinator}"

    def get_absolute_url(self):
        return reverse("coordination_log_detail", args=[self.id])

    @property
    def duration_parts(self):
        minutes = int(((self.actual_hours or Decimal("0")) * 60).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP,
        ))
        return divmod(minutes, 60)

    @property
    def service_duration_display(self):
        hours, minutes = self.duration_parts
        return f"{hours}h {minutes}m" if hours else f"{minutes}m"

    @property
    def can_coordinator_edit(self):
        return self.status in (
            self.Status.SUBMITTED, self.Status.APPROVED, self.Status.REJECTED,
        ) and not self.invoice_lines.exists()


class CoordinationLogChange(models.Model):
    class Kind(models.TextChoices):
        REVISION = "revision", "Revised and resubmitted"
        APPROVAL = "approval", "Approved"
        REJECTION = "rejection", "Rejected"
        CORRECTION = "correction", "Correction note"
        BILLING_REVIEW = "billing_review", "Invoice review required"

    log = models.ForeignKey(CoordinationLog, on_delete=models.PROTECT, related_name="changes")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    kind = models.CharField(max_length=20, choices=Kind.choices)
    reason = models.TextField(blank=True)
    details = models.TextField(blank=True)
    before = models.JSONField(default=dict)
    after = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-pk"]

    @staticmethod
    def display_value(field, value):
        if value is None or value == "":
            return "-"
        if field == "service_date":
            return date_format(parse_date(value), "d/m/Y")
        if field in ("start_time", "end_time"):
            return date_format(parse_time(value), "H:i")
        if field in ("reviewed_at", "submitted_at"):
            return date_format(timezone.localtime(parse_datetime(value)), "d/m/Y H:i")
        if field == "status":
            return dict(CoordinationLog.Status.choices).get(value, value)
        if field == "coordination_type":
            return dict(CoordinationLog.CoordinationType.choices).get(value, value)
        return str(value)

    @property
    def field_changes(self):
        labels = {
            "service_date": "Service date", "start_time": "Start time",
            "end_time": "End time", "break_minutes": "Break minutes",
            "actual_hours": "Actual hours", "coordination_type": "Coordination type",
            "case_notes": "Case notes", "coordinator_notes": "Coordinator notes",
            "status": "Status", "reviewed_by": "Reviewed by",
            "reviewed_at": "Reviewed at", "rejection_reason": "Rejection reason",
            "submitted_at": "Submitted at",
        }
        return [
            {
                "key": key,
                "label": label,
                "before": self.display_value(key, self.before.get(key)),
                "after": self.display_value(key, self.after.get(key)),
            }
            for key, label in labels.items()
            if self.before.get(key) != self.after.get(key)
        ]

    @property
    def content_changes(self):
        review_keys = {"status", "reviewed_by", "reviewed_at", "rejection_reason", "submitted_at"}
        return [field for field in self.field_changes if field["key"] not in review_keys]

    @property
    def review_changes(self):
        content_keys = {field["key"] for field in self.content_changes}
        return [field for field in self.field_changes if field["key"] not in content_keys]

    @property
    def changed_fields_summary(self):
        fields = self.content_changes
        summary = ", ".join(field["label"] for field in fields[:2])
        if len(fields) > 2:
            summary += f" + {len(fields) - 2} more"
        return summary
