from django.urls import path

from .views import roster_list, worker_shift_list

urlpatterns = [
    path("roster/", roster_list, name="roster_list"),
    path("sw/shifts/", worker_shift_list, name="worker_shift_list"),
]
