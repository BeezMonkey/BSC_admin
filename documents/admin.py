from django.contrib import admin

from .models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "category",
        "review_status",
        "required_document_type",
        "participant",
        "worker",
        "uploaded_by",
        "created_at",
    )
    list_filter = ("category", "review_status", "required_document_type", "created_at")
    search_fields = (
        "title",
        "notes",
        "participant__first_name",
        "participant__last_name",
        "worker__first_name",
        "worker__last_name",
    )
