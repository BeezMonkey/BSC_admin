from django.contrib import admin

from .models import SupportItem


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
