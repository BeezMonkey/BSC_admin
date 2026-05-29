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
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"
        NO_SHOW = "no_show", "No show"

    class ServiceType(models.TextChoices):
        COMMUNITY_ACCESS = "community_access", "Community access"
        PERSONAL_CARE = "personal_care", "Personal care"
        DOMESTIC_ASSISTANCE = "domestic_assistance", "Domestic assistance"
        TRANSPORT = "transport", "Transport"
        CAPACITY_BUILDING = "capacity_building", "Capacity building"
        OTHER = "other", "Other"

    ACTIVE_CONFLICT_STATUSES = (Status.DRAFT, Status.PUBLISHED, Status.CONFIRMED)
    WORKER_VISIBLE_STATUSES = (
        Status.PUBLISHED,
        Status.CONFIRMED,
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
