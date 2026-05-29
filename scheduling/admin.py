from django.contrib import admin

from .models import Shift, SupportItem


@admin.register(SupportItem)
class SupportItemAdmin(admin.ModelAdmin):
    list_display = (
        "item_number",
        "name",
        "category",
        "unit",
        "price_limit",
        "gst_code",
        "is_active",
    )
    list_filter = ("is_active", "category", "unit", "gst_code")
    search_fields = ("item_number", "name", "category")


@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = (
        "service_date",
        "start_time",
        "end_time",
        "participant",
        "worker",
        "status",
    )
    list_filter = ("status", "service_date", "service_type")
    search_fields = (
        "participant__first_name",
        "participant__last_name",
        "worker__first_name",
        "worker__last_name",
    )
