from django.shortcuts import render

from accounts.decorators import role_required


@role_required("super_admin", "admin")
def admin_dashboard(request):
    return render(request, "core/admin_dashboard.html")


@role_required("support_worker")
def worker_dashboard(request):
    return render(request, "core/worker_dashboard.html")

# Create your views here.
