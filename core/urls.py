from django.urls import path

from .views import admin_dashboard, audit_log_detail, audit_log_list, worker_dashboard

urlpatterns = [
    path("admin-dashboard/", admin_dashboard, name="admin_dashboard"),
    path("audit-logs/", audit_log_list, name="audit_log_list"),
    path("audit-logs/<int:audit_log_id>/", audit_log_detail, name="audit_log_detail"),
    path("sw/dashboard/", worker_dashboard, name="worker_dashboard"),
]
