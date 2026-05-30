from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.conf import settings

from scheduling.models import Shift, SupportItem


class ServiceLogManager(models.Manager):
    def create_from_shift(self, shift, **kwargs):
        return self.create(
            shift=shift,
            participant=shift.participant,
            worker=shift.worker,
            support_item=shift.support_item,
            service_date=shift.service_date,
            **kwargs,
        )


class ServiceLog(models.Model):
    class Status(models.TextChoices):
        SUBMITTED = "submitted", "Submitted"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        INVOICED = "invoiced", "Invoiced"

    shift = models.OneToOneField(
        Shift,
        on_delete=models.PROTECT,
        related_name="service_log",
    )
    participant = models.ForeignKey(
        "participants.Participant",
        on_delete=models.PROTECT,
        related_name="service_logs",
    )
    worker = models.ForeignKey(
        "workers.SupportWorker",
        on_delete=models.PROTECT,
        related_name="service_logs",
    )
    support_item = models.ForeignKey(
        SupportItem,
        on_delete=models.PROTECT,
        related_name="service_logs",
    )
    service_date = models.DateField()
    actual_start_time = models.TimeField()
    actual_end_time = models.TimeField()
    break_minutes = models.PositiveIntegerField(default=0)
    actual_hours = models.DecimalField(max_digits=6, decimal_places=2)
    kilometres = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    case_notes = models.TextField()
    worker_notes = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SUBMITTED,
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reviewed_service_logs",
        null=True,
        blank=True,
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    submitted_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ServiceLogManager()

    class Meta:
        ordering = ["-service_date", "-submitted_at"]

    def __str__(self):
        return f"{self.service_date} {self.participant} / {self.worker}"

    def get_absolute_url(self):
        return reverse("service_log_detail", args=[self.id])
