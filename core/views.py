from django.shortcuts import get_object_or_404, render

from accounts.decorators import admin_required, worker_required

from .models import AuditLog


@admin_required
def admin_dashboard(request):
    return render(request, "core/admin_dashboard.html")


@worker_required
def worker_dashboard(request):
    return render(request, "core/worker_dashboard.html")


@admin_required
def audit_log_list(request):
    audit_logs = AuditLog.objects.select_related("actor")
    return render(request, "core/audit_log_list.html", {"audit_logs": audit_logs})


@admin_required
def audit_log_detail(request, audit_log_id):
    audit_log = get_object_or_404(AuditLog.objects.select_related("actor"), id=audit_log_id)
    return render(request, "core/audit_log_detail.html", {"audit_log": audit_log})

# Create your views here.
