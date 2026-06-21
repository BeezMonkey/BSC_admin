from django.contrib import admin

from .models import Invoice, InvoiceLine, InvoiceSettings


class InvoiceLineInline(admin.TabularInline):
    model = InvoiceLine
    extra = 0
    readonly_fields = (
        "service_log",
        "support_item_number",
        "description",
        "unit",
        "unit_price",
        "quantity",
        "gst_code",
        "line_total",
    )


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "invoice_number",
        "participant",
        "period_start",
        "period_end",
        "status",
        "created_at",
    )
    list_filter = ("status", "period_start", "period_end")
    search_fields = ("invoice_number", "participant__first_name", "participant__last_name")
    inlines = [InvoiceLineInline]


@admin.register(InvoiceSettings)
class InvoiceSettingsAdmin(admin.ModelAdmin):
    list_display = ("business_name", "abn", "invoice_prefix", "next_invoice_sequence", "updated_at")
