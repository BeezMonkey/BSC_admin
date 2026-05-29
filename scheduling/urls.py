from django.urls import path

from .views import (
    roster_list,
    support_item_create,
    support_item_detail,
    support_item_edit,
    support_item_list,
    worker_shift_list,
)

urlpatterns = [
    path("roster/", roster_list, name="roster_list"),
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
]
