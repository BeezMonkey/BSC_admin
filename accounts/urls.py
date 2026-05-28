from django.urls import path

from .views import BSCLoginView, BSCLogoutView, role_redirect

urlpatterns = [
    path("login/", BSCLoginView.as_view(), name="login"),
    path("logout/", BSCLogoutView.as_view(), name="logout"),
    path("role-redirect/", role_redirect, name="role_redirect"),
]
