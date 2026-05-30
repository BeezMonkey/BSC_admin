from django.urls import path

from .views import (
    service_log_detail,
    service_log_list,
    worker_log_list,
    worker_service_log_create,
    worker_service_log_detail,
)

urlpatterns = [
    path("service-logs/", service_log_list, name="service_log_list"),
    path("service-logs/<int:service_log_id>/", service_log_detail, name="service_log_detail"),
    path("sw/logs/", worker_log_list, name="worker_log_list"),
    path(
        "sw/logs/<int:service_log_id>/",
        worker_service_log_detail,
        name="worker_service_log_detail",
    ),
    path(
        "sw/shifts/<int:shift_id>/complete-log/",
        worker_service_log_create,
        name="worker_service_log_create",
    ),
]
