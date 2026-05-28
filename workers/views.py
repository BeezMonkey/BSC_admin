from django.shortcuts import render

from accounts.decorators import admin_required, worker_required


@admin_required
def worker_list(request):
    return render(
        request,
        "core/admin_placeholder.html",
        {
            "title": "Support Workers",
            "message": "Support worker management starts in Phase 3.",
        },
    )


@worker_required
def worker_profile(request):
    return render(
        request,
        "core/worker_placeholder.html",
        {"title": "My Profile", "message": "Worker profile starts in Phase 3."},
    )
