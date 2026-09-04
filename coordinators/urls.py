from django.urls import path

from . import views

urlpatterns = [
    path("sc/dashboard/", views.coordinator_dashboard, name="coordinator_dashboard"),
]
