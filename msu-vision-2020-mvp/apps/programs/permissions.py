from apps.core.permissions import user_stakeholder_codes
from apps.stakeholders.models import UserProfile


def can_manage_programs(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    codes = user_stakeholder_codes(user)
    return bool(
        codes
        & {
            UserProfile.StakeholderType.FOUNDATION_ADMIN,
            UserProfile.StakeholderType.GOVERNANCE,
        }
    )


def can_edit_program(user, program):
    if can_manage_programs(user):
        return True
    return program.admins.filter(pk=user.pk).exists()
