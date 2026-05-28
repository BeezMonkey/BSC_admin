from django.db import models
from django.urls import reverse


class Participant(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        ARCHIVED = "archived", "Archived"

    class ManagementType(models.TextChoices):
        NDIA_MANAGED = "ndia_managed", "NDIA managed"
        PLAN_MANAGED = "plan_managed", "Plan managed"
        SELF_MANAGED = "self_managed", "Self managed"

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    preferred_name = models.CharField(max_length=100, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    ndis_number = models.CharField(max_length=30, unique=True, null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    address_line_1 = models.CharField(max_length=255, blank=True)
    address_line_2 = models.CharField(max_length=255, blank=True)
    suburb = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=20, blank=True)
    postcode = models.CharField(max_length=4, blank=True)

    emergency_contact_name = models.CharField(max_length=150, blank=True)
    emergency_contact_relationship = models.CharField(max_length=100, blank=True)
    emergency_contact_phone = models.CharField(max_length=30, blank=True)
    emergency_contact_email = models.EmailField(blank=True)

    plan_start_date = models.DateField(null=True, blank=True)
    plan_end_date = models.DateField(null=True, blank=True)
    management_type = models.CharField(
        max_length=30,
        choices=ManagementType.choices,
        blank=True,
    )
    plan_manager_name = models.CharField(max_length=150, blank=True)
    plan_manager_email = models.EmailField(blank=True)
    plan_manager_phone = models.CharField(max_length=30, blank=True)
    support_coordinator_name = models.CharField(max_length=150, blank=True)
    support_coordinator_email = models.EmailField(blank=True)
    support_coordinator_phone = models.CharField(max_length=30, blank=True)

    worker_visible_notes = models.TextField(blank=True)
    address_access_instructions = models.TextField(blank=True)
    risk_safety_notes = models.TextField(blank=True)
    internal_notes = models.TextField(blank=True)

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
        return reverse("participant_detail", args=[self.id])

# Create your models here.
