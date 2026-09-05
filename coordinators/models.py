from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone


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
    start_time = models.TimeField()
    end_time = models.TimeField()
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
