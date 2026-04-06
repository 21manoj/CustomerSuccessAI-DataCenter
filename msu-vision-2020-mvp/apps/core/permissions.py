from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.shortcuts import redirect

# Maps architecture §5.1 roles to UserProfile.stakeholder_type values
ROLE_ADMIN = "foundation_admin"


def user_stakeholder_codes(user):
    """All effective persona codes for RBAC (multi-persona)."""
    if not user.is_authenticated:
        return frozenset()
    if user.is_superuser:
        return frozenset({ROLE_ADMIN})
    prof = getattr(user, "profile", None)
    if not prof:
        return frozenset()
    return frozenset(prof.persona_codes())


def has_stakeholder_type(user, *types):
    """True if user has any of the given stakeholder persona codes (or is admin/superuser)."""
    codes = user_stakeholder_codes(user)
    if ROLE_ADMIN in codes:
        return True
    return bool(codes & set(types))


def profile_role(user):
    """
    One representative role for legacy call sites (highest privilege among personas).
    Prefer has_stakeholder_type(...) for permission checks.
    """
    if not user.is_authenticated:
        return None
    if user.is_superuser:
        return ROLE_ADMIN
    prof = getattr(user, "profile", None)
    if not prof:
        return None
    codes = prof.persona_codes()
    if not codes:
        return prof.stakeholder_type
    from apps.stakeholders.persona_utils import pick_primary_persona

    return pick_primary_persona(codes) or prof.stakeholder_type


def has_role(user, *allowed):
    return has_stakeholder_type(user, *allowed)


def roles_required(*allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if not has_role(request.user, *allowed_roles):
                return redirect("dashboard:home")
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator
