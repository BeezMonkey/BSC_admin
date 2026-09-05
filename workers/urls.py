from django.urls import path

from .views import (
    worker_create,
    worker_detail,
    worker_edit,
    worker_list,
    worker_profile,
    worker_reset_password,
)

urlpatterns = [
    path("workers/", worker_list, name="worker_list"),
    path("workers/new/", worker_create, name="worker_create"),
    path("workers/<int:worker_id>/", worker_detail, name="worker_detail"),
    path("workers/<int:worker_id>/edit/", worker_edit, name="worker_edit"),
    path(
        "workers/<int:worker_id>/reset-password/",
        worker_reset_password,
        name="worker_reset_password",
    ),
    path("sw/profile/", worker_profile, name="worker_profile"),
]
