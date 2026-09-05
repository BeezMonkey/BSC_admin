from django.urls import path

from . import views

urlpatterns = [
    path(
        "coordination-logs/",
        views.coordination_log_list,
        name="coordination_log_list",
    ),
    path(
        "coordination-logs/<int:log_id>/",
        views.coordination_log_detail,
        name="coordination_log_detail",
    ),
    path(
        "coordination-logs/<int:log_id>/approve/",
        views.coordination_log_approve,
        name="coordination_log_approve",
    ),
    path(
        "coordination-logs/<int:log_id>/reject/",
        views.coordination_log_reject,
        name="coordination_log_reject",
    ),
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
        "coordinators/<int:coordinator_id>/reset-password/",
        views.coordinator_reset_password,
        name="coordinator_reset_password",
    ),
    path(
        "coordinators/<int:coordinator_id>/assign/",
        views.coordinator_assign_participant,
        name="coordinator_assign_participant",
    ),
    path("sc/dashboard/", views.coordinator_dashboard, name="coordinator_dashboard"),
    path("sc/account/", views.coordinator_account, name="coordinator_account"),
    path("sc/logs/", views.coordinator_log_list, name="coordinator_log_list"),
    path("sc/logs/new/", views.coordinator_log_create, name="coordinator_log_create"),
    path(
        "sc/logs/<int:log_id>/",
        views.coordinator_log_detail,
        name="coordinator_log_detail",
    ),
    path(
        "sc/participants/",
        views.coordinator_participant_list,
        name="coordinator_participant_list",
    ),
    path(
        "sc/participants/<int:participant_id>/",
        views.coordinator_participant_detail,
        name="coordinator_participant_detail",
    ),
]
