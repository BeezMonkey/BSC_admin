from django.urls import path

from .views import admin_dashboard, worker_dashboard

urlpatterns = [
    path("admin-dashboard/", admin_dashboard, name="admin_dashboard"),
    path("sw/dashboard/", worker_dashboard, name="worker_dashboard"),
]
