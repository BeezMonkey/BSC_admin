from django.urls import path

from .views import worker_list, worker_profile

urlpatterns = [
    path("workers/", worker_list, name="worker_list"),
    path("sw/profile/", worker_profile, name="worker_profile"),
]
