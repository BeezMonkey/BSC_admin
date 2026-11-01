from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect

from .permissions import (
    ACCOUNTANT,
    ADMIN_ROLES,
    SUPPORT_COORDINATOR,
    SUPPORT_WORKER,
    get_role,
)


LOGIN_PORTAL_CONTEXT = {
    "admin.bscare.com.au": {
        "portal_name": "Administrator",
        "portal_badge": "ADMIN",
        "login_button_label": "Login",
    },
    "sw.bscare.com.au": {
        "portal_name": "Support Worker",
        "portal_badge": "SW",
        "login_button_label": "Login",
    },
    "sc.bscare.com.au": {
        "portal_name": "Support Coordinator",
        "portal_badge": "SC",
        "login_button_label": "Login",
    },
}

DEFAULT_LOGIN_PORTAL_CONTEXT = {
    "portal_name": "NDIS Admin System",
    "login_button_label": "Login",
}


def get_login_portal_context(host):
    hostname = host.split(":", 1)[0].lower()
    return LOGIN_PORTAL_CONTEXT.get(hostname, DEFAULT_LOGIN_PORTAL_CONTEXT)


class BSCLoginView(LoginView):
    template_name = "accounts/login.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_login_portal_context(self.request.get_host()))
        context["form"].fields["username"].widget.attrs["placeholder"] = "Enter your username"
        return context


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
    if role == SUPPORT_COORDINATOR:
        return redirect("coordinator_dashboard")
    if role == ACCOUNTANT:
        return redirect("invoice_placeholder")
    return redirect("login")

# Create your views here.
