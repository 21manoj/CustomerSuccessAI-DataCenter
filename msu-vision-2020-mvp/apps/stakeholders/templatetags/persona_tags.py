from django import template

from apps.core.permissions import has_stakeholder_type

register = template.Library()


@register.filter
def has_any_persona(user, comma_codes):
    """
    True if user has any of the comma-separated stakeholder codes (or is superuser).
    Usage: {% if user|has_any_persona:"governance,foundation_admin" %}
    """
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    parts = [p.strip() for p in (comma_codes or "").split(",") if p.strip()]
    if not parts:
        return False
    return has_stakeholder_type(user, *parts)
