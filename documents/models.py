from pathlib import Path

from django.conf import settings
from django.db import models
from django.urls import reverse


class Document(models.Model):
    class Category(models.TextChoices):
        PLAN = "plan", "Plan"
        COMPLIANCE = "compliance", "Compliance"
        INVOICE = "invoice", "Invoice"
        SERVICE_LOG = "service_log", "Service log"
        GENERAL = "general", "General"

    title = models.CharField(max_length=200)
    category = models.CharField(
        max_length=30,
        choices=Category.choices,
        default=Category.GENERAL,
    )
    file = models.FileField(upload_to="documents/")
    participant = models.ForeignKey(
        "participants.Participant",
        on_delete=models.CASCADE,
        related_name="documents",
        null=True,
        blank=True,
    )
    worker = models.ForeignKey(
        "workers.SupportWorker",
        on_delete=models.CASCADE,
        related_name="documents",
        null=True,
        blank=True,
    )
    invoice = models.ForeignKey(
        "invoices.Invoice",
        on_delete=models.CASCADE,
        related_name="documents",
        null=True,
        blank=True,
    )
    service_log = models.ForeignKey(
        "service_logs.ServiceLog",
        on_delete=models.CASCADE,
        related_name="documents",
        null=True,
        blank=True,
    )
    notes = models.TextField(blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="uploaded_documents",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    @property
    def filename(self):
        return Path(self.file.name).name

    def get_absolute_url(self):
        return reverse("document_detail", args=[self.id])
