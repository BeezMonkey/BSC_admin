from django.urls import path

from .views import (
    participant_archive,
    participant_create,
    participant_detail,
    participant_edit,
    participant_list,
)

urlpatterns = [
    path("participants/", participant_list, name="participant_list"),
    path("participants/new/", participant_create, name="participant_create"),
    path("participants/<int:participant_id>/", participant_detail, name="participant_detail"),
    path("participants/<int:participant_id>/edit/", participant_edit, name="participant_edit"),
    path(
        "participants/<int:participant_id>/archive/",
        participant_archive,
        name="participant_archive",
    ),
]
