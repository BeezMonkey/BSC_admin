from django.shortcuts import render

from accounts.decorators import admin_required


@admin_required
def participant_list(request):
    return render(
        request,
        "core/admin_placeholder.html",
        {"title": "Participants", "message": "Participant management starts in Phase 2."},
    )
