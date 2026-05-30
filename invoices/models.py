from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone

from service_logs.models import ServiceLog


class Invoice(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ISSUED = "issued", "Issued"
        PAID = "paid", "Paid"
        CANCELLED = "cancelled", "Cancelled"

    invoice_number = models.CharField(max_length=30, unique=True, blank=True)
    participant = models.ForeignKey(
        "participants.Participant",
        on_delete=models.PROTECT,
        related_name="invoices",
    )
    period_start = models.DateField()
    period_end = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_invoices",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            today = timezone.localdate()
            prefix = f"INV-{today:%Y%m%d}"
            count = Invoice.objects.filter(invoice_number__startswith=prefix).count() + 1
            self.invoice_number = f"{prefix}-{count:04d}"
        super().save(*args, **kwargs)

    @property
    def total_amount(self):
        total = self.lines.aggregate(total=models.Sum("line_total"))["total"]
        return total or Decimal("0.00")

    def __str__(self):
        return self.invoice_number

    def get_absolute_url(self):
        return reverse("invoice_detail", args=[self.id])


class InvoiceLineManager(models.Manager):
    def create_from_service_log(self, invoice, service_log):
        support_item = service_log.support_item
        quantity = service_log.actual_hours
        unit_price = support_item.price_limit
        line_total = (quantity * unit_price).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
        return self.create(
            invoice=invoice,
            service_log=service_log,
            support_item_number=support_item.item_number,
            description=support_item.name,
            unit=support_item.unit,
            unit_price=unit_price,
            quantity=quantity,
            gst_code=support_item.gst_code,
            line_total=line_total,
        )


class InvoiceLine(models.Model):
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    service_log = models.OneToOneField(
        ServiceLog,
        on_delete=models.PROTECT,
        related_name="invoice_line",
    )
    support_item_number = models.CharField(max_length=50)
    description = models.CharField(max_length=255)
    unit = models.CharField(max_length=20)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.DecimalField(max_digits=8, decimal_places=2)
    gst_code = models.CharField(max_length=20)
    line_total = models.DecimalField(max_digits=10, decimal_places=2)

    objects = InvoiceLineManager()

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.invoice} - {self.support_item_number}"
