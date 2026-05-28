from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from .permissions import ADMIN_ROLES, FINANCE_ROLES, WORKER_ROLES, has_role


def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            if not has_role(request.user, roles):
                raise PermissionDenied
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


admin_required = role_required(*ADMIN_ROLES)
worker_required = role_required(*WORKER_ROLES)
finance_required = role_required(*FINANCE_ROLES)
