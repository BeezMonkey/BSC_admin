from django.contrib import admin

from .models import Participant, ParticipantWorkerAssignment


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = (
        "display_name",
        "ndis_number",
        "management_type",
        "plan_start_date",
        "plan_end_date",
        "status",
    )
    list_filter = ("status", "management_type", "state")
    search_fields = (
        "first_name",
        "last_name",
        "preferred_name",
        "ndis_number",
        "support_coordinator_name",
    )


@admin.register(ParticipantWorkerAssignment)
class ParticipantWorkerAssignmentAdmin(admin.ModelAdmin):
    list_display = ("participant", "worker", "start_date", "end_date", "is_active")
    list_filter = ("is_active", "start_date", "end_date")
    search_fields = (
        "participant__first_name",
        "participant__last_name",
        "worker__first_name",
        "worker__last_name",
    )

# Register your models here.
