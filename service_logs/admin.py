from django.contrib import admin

from .models import ServiceLog


@admin.register(ServiceLog)
class ServiceLogAdmin(admin.ModelAdmin):
    list_display = (
        "service_date",
        "participant",
        "worker",
        "status",
        "actual_hours",
        "submitted_at",
    )
    list_filter = ("status", "service_date")
    search_fields = (
        "participant__first_name",
        "participant__last_name",
        "worker__first_name",
        "worker__last_name",
        "case_notes",
    )
