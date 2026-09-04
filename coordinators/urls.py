from django.urls import path

from . import views

urlpatterns = [
    path("coordinators/", views.coordinator_list, name="coordinator_list"),
    path("coordinators/new/", views.coordinator_create, name="coordinator_create"),
    path(
        "coordinators/<int:coordinator_id>/",
        views.coordinator_detail,
        name="coordinator_detail",
    ),
    path(
        "coordinators/<int:coordinator_id>/edit/",
        views.coordinator_edit,
        name="coordinator_edit",
    ),
    path(
        "coordinators/<int:coordinator_id>/assign/",
        views.coordinator_assign_participant,
        name="coordinator_assign_participant",
    ),
    path("sc/dashboard/", views.coordinator_dashboard, name="coordinator_dashboard"),
]
