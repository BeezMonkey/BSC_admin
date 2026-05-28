from django.shortcuts import render

from accounts.decorators import admin_required, worker_required


@admin_required
def roster_list(request):
    return render(
        request,
        "core/admin_placeholder.html",
        {"title": "Roster", "message": "Scheduling starts in Phase 6."},
    )


@worker_required
def worker_shift_list(request):
    return render(
        request,
        "core/worker_placeholder.html",
        {"title": "My Shifts", "message": "Worker shifts start in Phase 6."},
    )
