from django.urls import path

from .views import (
    recurring_shift_create,
    roster_list,
    roster_planner,
    shift_cancel,
    shift_create,
    shift_detail,
    shift_edit,
    shift_bulk_publish,
    shift_publish,
    support_item_create,
    support_item_detail,
    support_item_edit,
    support_item_list,
    worker_shift_confirm,
    worker_shift_detail,
    worker_shift_list,
)

urlpatterns = [
    path("roster/", roster_list, name="roster_list"),
    path("roster/planner/", roster_planner, name="roster_planner"),
    path("roster/new/", shift_create, name="shift_create"),
    path("roster/recurring/new/", recurring_shift_create, name="recurring_shift_create"),
    path("roster/publish-shown/", shift_bulk_publish, name="shift_bulk_publish"),
    path("roster/<int:shift_id>/", shift_detail, name="shift_detail"),
    path("roster/<int:shift_id>/edit/", shift_edit, name="shift_edit"),
    path("roster/<int:shift_id>/publish/", shift_publish, name="shift_publish"),
    path("roster/<int:shift_id>/cancel/", shift_cancel, name="shift_cancel"),
    path("settings/support-items/", support_item_list, name="support_item_list"),
    path("settings/support-items/new/", support_item_create, name="support_item_create"),
    path(
        "settings/support-items/<int:support_item_id>/",
        support_item_detail,
        name="support_item_detail",
    ),
    path(
        "settings/support-items/<int:support_item_id>/edit/",
        support_item_edit,
        name="support_item_edit",
    ),
    path("sw/shifts/", worker_shift_list, name="worker_shift_list"),
    path("sw/shifts/<int:shift_id>/", worker_shift_detail, name="worker_shift_detail"),
    path(
        "sw/shifts/<int:shift_id>/confirm/",
        worker_shift_confirm,
        name="worker_shift_confirm",
    ),
]
