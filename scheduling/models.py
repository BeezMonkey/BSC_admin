from django.db import models
from django.urls import reverse


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
