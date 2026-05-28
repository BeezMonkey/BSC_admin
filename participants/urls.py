from django.urls import path

from .views import participant_list

urlpatterns = [
    path("participants/", participant_list, name="participant_list"),
]
