from django.urls import path

from .views import service_log_list, worker_log_list

urlpatterns = [
    path("service-logs/", service_log_list, name="service_log_list"),
    path("sw/logs/", worker_log_list, name="worker_log_list"),
]
