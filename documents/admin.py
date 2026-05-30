from django.contrib import admin

from .models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "participant", "worker", "uploaded_by", "created_at")
    list_filter = ("category", "created_at")
    search_fields = (
        "title",
        "notes",
        "participant__first_name",
        "participant__last_name",
        "worker__first_name",
        "worker__last_name",
    )
