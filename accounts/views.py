from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect

from .models import UserProfile


class BSCLoginView(LoginView):
    template_name = "accounts/login.html"


class BSCLogoutView(LogoutView):
    pass


@login_required
def role_redirect(request):
    profile = getattr(request.user, "userprofile", None)
    if profile is None:
        return redirect("login")
    if profile.role in [UserProfile.Role.SUPER_ADMIN, UserProfile.Role.ADMIN]:
        return redirect("admin_dashboard")
    if profile.role == UserProfile.Role.SUPPORT_WORKER:
        return redirect("worker_dashboard")
    if profile.role == UserProfile.Role.ACCOUNTANT:
        return redirect("invoice_placeholder")
    return redirect("login")

# Create your views here.
