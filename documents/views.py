from django.shortcuts import render

from accounts.decorators import admin_required


@admin_required
def document_list(request):
    return render(
        request,
        "core/admin_placeholder.html",
        {"title": "Documents", "message": "Document management starts in Phase 12."},
    )
