from django.shortcuts import render

from accounts.decorators import admin_required, worker_required


@admin_required
def admin_dashboard(request):
    return render(request, "core/admin_dashboard.html")


@worker_required
def worker_dashboard(request):
    return render(request, "core/worker_dashboard.html")

# Create your views here.
