from django.conf import settings
from django.db import models
from django.urls import reverse


class SupportWorker(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"

    class EmploymentType(models.TextChoices):
        EMPLOYEE = "employee", "Employee"
        SUBCONTRACTOR = "subcontractor", "Subcontractor"

    class ComplianceStatus(models.TextChoices):
        NOT_PROVIDED = "not_provided", "Not provided"
        PENDING = "pending", "Pending"
        CURRENT = "current", "Current"
        EXPIRED = "expired", "Expired"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=30, blank=True)
    address = models.TextField(blank=True)
    employment_type = models.CharField(
        max_length=30,
        choices=EmploymentType.choices,
        default=EmploymentType.EMPLOYEE,
    )
    abn = models.CharField(max_length=20, blank=True)
    start_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    police_check_status = models.CharField(
        max_length=30,
        choices=ComplianceStatus.choices,
        default=ComplianceStatus.NOT_PROVIDED,
    )
    police_check_expiry = models.DateField(null=True, blank=True)
    wwcc_status = models.CharField(
        "WWCC / Blue Card status",
        max_length=30,
        choices=ComplianceStatus.choices,
        default=ComplianceStatus.NOT_PROVIDED,
    )
    wwcc_expiry = models.DateField("WWCC / Blue Card expiry", null=True, blank=True)
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

    def get_absolute_url(self):
        return reverse("worker_detail", args=[self.id])
