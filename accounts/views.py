from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect

from .permissions import ACCOUNTANT, ADMIN_ROLES, SUPPORT_WORKER, get_role


class BSCLoginView(LoginView):
    template_name = "accounts/login.html"


class BSCLogoutView(LogoutView):
    pass


@login_required
def role_redirect(request):
    role = get_role(request.user)
    if role is None:
        return redirect("login")
    if role in ADMIN_ROLES:
        return redirect("admin_dashboard")
    if role == SUPPORT_WORKER:
        return redirect("worker_dashboard")
    if role == ACCOUNTANT:
        return redirect("invoice_placeholder")
    return redirect("login")

# Create your views here.
