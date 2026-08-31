from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect

from .permissions import ACCOUNTANT, ADMIN_ROLES, SUPPORT_WORKER, get_role


LOGIN_PORTAL_CONTEXT = {
    "admin.bscare.com.au": {
        "portal_name": "NDIS Admin Portal",
        "login_button_label": "Login to Admin Portal",
    },
    "sw.bscare.com.au": {
        "portal_name": "Support Worker Portal",
        "login_button_label": "Login to Worker Portal",
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
    if role == ACCOUNTANT:
        return redirect("invoice_placeholder")
    return redirect("login")

# Create your views here.
