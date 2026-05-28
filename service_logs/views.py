from django.shortcuts import render

from accounts.decorators import admin_required, worker_required


@admin_required
def service_log_list(request):
    return render(
        request,
        "core/admin_placeholder.html",
        {"title": "Service Logs", "message": "Service log review starts in Phase 8."},
    )


@worker_required
def worker_log_list(request):
    return render(
        request,
        "core/worker_placeholder.html",
        {"title": "My Logs", "message": "Worker logs start in Phase 7."},
    )
