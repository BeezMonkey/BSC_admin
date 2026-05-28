from django.contrib import admin

from .models import SupportWorker


@admin.register(SupportWorker)
class SupportWorkerAdmin(admin.ModelAdmin):
    list_display = (
        "display_name",
        "email",
        "phone",
        "employment_type",
        "status",
        "police_check_status",
        "wwcc_status",
    )
    list_filter = (
        "status",
        "employment_type",
        "police_check_status",
        "wwcc_status",
    )
    search_fields = ("first_name", "last_name", "email", "phone")
