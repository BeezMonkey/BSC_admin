from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.db import models
from django.urls import reverse


def document_upload_path(instance, filename):
    extension = Path(filename).suffix.lower()
    return f"documents/{uuid4().hex}{extension}"


class Document(models.Model):
    class Category(models.TextChoices):
        PLAN = "plan", "Plan"
        COMPLIANCE = "compliance", "Compliance"
        INVOICE = "invoice", "Invoice"
        SERVICE_LOG = "service_log", "Service log"
        GENERAL = "general", "General"

    class ReviewStatus(models.TextChoices):
        PENDING_REVIEW = "pending_review", "Pending review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    class RequiredDocumentType(models.TextChoices):
        POLICE_CHECK = "police_check", "Police Check"
        NDIS_WORKER_SCREENING = "ndis_worker_screening", "NDIS Worker Screening Check"
        FIRST_AID = "first_aid", "First Aid Certificate"
        CPR = "cpr", "CPR Certificate"
        WWCC = "wwcc", "Working With Children Check"
        DRIVER_LICENCE = "driver_licence", "Driver Licence"
        NDIS_ORIENTATION = "ndis_orientation", "NDIS Worker Orientation Module"
        RESUME = "resume", "Resume"
        VISA = "visa", "Visa Document"
        QUALIFICATION = "qualification", "Educational Qualification"

    title = models.CharField(max_length=200)
    category = models.CharField(
        max_length=30,
        choices=Category.choices,
        default=Category.GENERAL,
    )
    file = models.FileField(upload_to=document_upload_path)
    original_filename = models.CharField(max_length=255, blank=True)
    required_document_type = models.CharField(
        max_length=60,
        choices=RequiredDocumentType.choices,
        blank=True,
    )
    review_status = models.CharField(
        max_length=30,
        choices=ReviewStatus.choices,
        default=ReviewStatus.APPROVED,
    )
    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
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
        return self.original_filename or Path(self.file.name).name

    @property
    def extension(self):
        return Path(self.filename).suffix.lower()

    @property
    def is_image(self):
        return self.extension in {".jpg", ".jpeg", ".png"}

    @property
    def is_pdf(self):
        return self.extension == ".pdf"

    @property
    def is_previewable(self):
        return self.is_image or self.is_pdf

    @property
    def preview_content_type(self):
        content_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".pdf": "application/pdf",
        }
        return content_types.get(self.extension, "")

    def get_absolute_url(self):
        return reverse("document_detail", args=[self.id])
