from django.contrib import admin

from .models import Participant


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

# Register your models here.
