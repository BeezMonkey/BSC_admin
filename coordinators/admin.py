from django.contrib import admin

from .models import CoordinationLog, CoordinationLogChange, ParticipantCoordinatorAssignment, SupportCoordinator


@admin.register(SupportCoordinator)
class SupportCoordinatorAdmin(admin.ModelAdmin):
    list_display = ("display_name", "email", "phone", "status")
    list_filter = ("status",)
    search_fields = ("first_name", "last_name", "email", "phone")


@admin.register(ParticipantCoordinatorAssignment)
class ParticipantCoordinatorAssignmentAdmin(admin.ModelAdmin):
    list_display = ("participant", "coordinator", "start_date", "end_date", "is_active")
    list_filter = ("is_active", "start_date", "end_date")
    search_fields = (
        "participant__first_name",
        "participant__last_name",
        "coordinator__first_name",
        "coordinator__last_name",
    )


@admin.register(CoordinationLog)
class CoordinationLogAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    list_display = (
        "service_date",
        "participant",
        "coordinator",
        "coordination_type",
        "actual_hours",
        "status",
    )
    list_filter = ("status", "coordination_type", "service_date")
    search_fields = (
        "participant__first_name",
        "participant__last_name",
        "coordinator__first_name",
        "coordinator__last_name",
        "case_notes",
    )


@admin.register(CoordinationLogChange)
class CoordinationLogChangeAdmin(admin.ModelAdmin):
    list_display = ("log", "kind", "actor", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
