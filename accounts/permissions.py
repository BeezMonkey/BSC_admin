from .models import UserProfile

SUPER_ADMIN = UserProfile.Role.SUPER_ADMIN
ADMIN = UserProfile.Role.ADMIN
SUPPORT_WORKER = UserProfile.Role.SUPPORT_WORKER
SUPPORT_COORDINATOR = UserProfile.Role.SUPPORT_COORDINATOR
ACCOUNTANT = UserProfile.Role.ACCOUNTANT

ADMIN_ROLES = (SUPER_ADMIN, ADMIN)
WORKER_ROLES = (SUPPORT_WORKER,)
COORDINATOR_ROLES = (SUPPORT_COORDINATOR,)
FINANCE_ROLES = (SUPER_ADMIN, ADMIN, ACCOUNTANT)


def get_role(user):
    profile = getattr(user, "userprofile", None)
    if profile is None:
        return None
    return profile.role


def has_role(user, roles):
    return get_role(user) in roles
