from django.db import models
from django.urls import reverse
from django.conf import settings


class SupportItem(models.Model):
    class Unit(models.TextChoices):
        HOUR = "hour", "Hour"
        EACH = "each", "Each"
        KM = "km", "Kilometre"

    class GSTCode(models.TextChoices):
        GST_FREE = "gst_free", "GST-free"
        TAXABLE = "taxable", "Taxable"

    item_number = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=150, blank=True)
    unit = models.CharField(max_length=20, choices=Unit.choices, default=Unit.HOUR)
    price_limit = models.DecimalField(max_digits=10, decimal_places=2)
    gst_code = models.CharField(
        max_length=20,
        choices=GSTCode.choices,
        default=GSTCode.GST_FREE,
    )
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category", "item_number"]

    def __str__(self):
        return f"{self.item_number} - {self.name}"

    def get_absolute_url(self):
        return reverse("support_item_detail", args=[self.id])

    @classmethod
    def active_items(cls):
        return cls.objects.filter(is_active=True)


class Shift(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        CONFIRMED = "confirmed", "Confirmed"
        CANCELLATION_REVIEW = "cancellation_review", "Cancellation review"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"
        NO_SHOW = "no_show", "No show"

    class Source(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        UNSCHEDULED = "unscheduled", "Unscheduled"

    class ServiceType(models.TextChoices):
        COMMUNITY_ACCESS = "community_access", "Community access"
        PERSONAL_CARE = "personal_care", "Personal care"
        DOMESTIC_ASSISTANCE = "domestic_assistance", "Domestic assistance"
        TRANSPORT = "transport", "Transport"
        CAPACITY_BUILDING = "capacity_building", "Capacity building"
        OTHER = "other", "Other"

    ACTIVE_CONFLICT_STATUSES = (
        Status.DRAFT,
        Status.PUBLISHED,
        Status.CONFIRMED,
        Status.CANCELLATION_REVIEW,
    )
    WORKER_VISIBLE_STATUSES = (
        Status.PUBLISHED,
        Status.CONFIRMED,
        Status.CANCELLATION_REVIEW,
        Status.COMPLETED,
        Status.CANCELLED,
        Status.NO_SHOW,
    )

    participant = models.ForeignKey(
        "participants.Participant",
        on_delete=models.PROTECT,
        related_name="shifts",
    )
    worker = models.ForeignKey(
        "workers.SupportWorker",
        on_delete=models.PROTECT,
        related_name="shifts",
    )
    service_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    break_minutes = models.PositiveIntegerField(default=0)
    planned_hours = models.DecimalField(max_digits=6, decimal_places=2)
    support_item = models.ForeignKey(
        SupportItem,
        on_delete=models.PROTECT,
        related_name="shifts",
    )
    service_type = models.CharField(max_length=40, choices=ServiceType.choices)
    source = models.CharField(
        max_length=20,
        choices=Source.choices,
        default=Source.SCHEDULED,
    )
    location = models.CharField(max_length=150, blank=True)
    address = models.TextField(blank=True)
    instructions = models.TextField(blank=True)
    admin_notes = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    cancellation_reason = models.TextField(blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_shifts",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["service_date", "start_time"]

    def __str__(self):
        return f"{self.service_date} {self.start_time} {self.participant} / {self.worker}"

    def get_absolute_url(self):
        return reverse("shift_detail", args=[self.id])


class ParticipantCancellation(models.Model):
    class CancellationType(models.TextChoices):
        SHORT_NOTICE = "short_notice", "Short notice cancellation"
        NO_SHOW = "no_show", "Participant did not attend"

    class Reason(models.TextChoices):
        HEALTH = "health", "Health"
        FAMILY = "family", "Family circumstances"
        TRANSPORT = "transport", "Transport"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending review"
        APPROVED = "approved", "Approved for charging"
        WAIVED = "waived", "Charge waived"
        REJECTED = "rejected", "Rejected"

    shift = models.OneToOneField(
        Shift,
        on_delete=models.PROTECT,
        related_name="participant_cancellation",
    )
    cancellation_type = models.CharField(max_length=20, choices=CancellationType.choices)
    reason = models.CharField(max_length=20, choices=Reason.choices)
    details = models.TextField()
    received_at = models.DateTimeField()
    previous_shift_status = models.CharField(max_length=20, choices=Shift.Status.choices)
    claim_type = models.CharField(max_length=10, default="CANC", editable=False)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    admin_note = models.TextField(blank=True)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="submitted_participant_cancellations",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reviewed_participant_cancellations",
        null=True,
        blank=True,
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-submitted_at", "-id"]

    def __str__(self):
        return f"Cancellation for shift {self.shift_id} ({self.get_status_display()})"


class PlannedMultiWorkerSupport(models.Model):
    class Reason(models.TextChoices):
        MANUAL_HANDLING = "manual_handling", "Manual handling"
        BEHAVIOUR_SUPPORT = "behaviour_support", "Behaviour support"
        SAFETY = "safety", "Safety"
        OTHER = "other", "Other"

    participant = models.ForeignKey(
        "participants.Participant",
        on_delete=models.PROTECT,
        related_name="planned_multi_worker_supports",
    )
    service_date = models.DateField()
    overlap_start_time = models.TimeField()
    overlap_end_time = models.TimeField()
    worker_count = models.PositiveSmallIntegerField()
    reason = models.CharField(max_length=30, choices=Reason.choices)
    notes = models.TextField(blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="approved_multi_worker_supports",
        null=True,
        blank=True,
    )
    approved_at = models.DateTimeField(auto_now_add=True)
    shifts = models.ManyToManyField(
        Shift,
        related_name="planned_multi_worker_supports",
    )

    class Meta:
        ordering = ["service_date", "overlap_start_time", "id"]

    def __str__(self):
        return (
            f"{self.worker_count}:1 support for {self.participant} "
            f"on {self.service_date}"
        )
