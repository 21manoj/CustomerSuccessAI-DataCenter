from django.db.models import Q

from apps.core.permissions import user_stakeholder_codes
from apps.stakeholders.models import UserProfile


def filter_contributions(qs, user):
    if not user.is_authenticated:
        return qs.none()
    codes = user_stakeholder_codes(user)
    if user.is_superuser or codes & {
        UserProfile.StakeholderType.FOUNDATION_ADMIN,
        UserProfile.StakeholderType.FINANCE_CONTROLLER,
        UserProfile.StakeholderType.GOVERNANCE,
        UserProfile.StakeholderType.AUDITOR,
    }:
        return qs
    if UserProfile.StakeholderType.DONOR in codes:
        return qs.filter(donor=user)
    if codes & {
        UserProfile.StakeholderType.PROJECT_LEAD,
        UserProfile.StakeholderType.VOLUNTEER,
    }:
        return qs.filter(
            Q(project__lead=user)
            | Q(project__team_members__user=user)
            | Q(volunteer_lead=user)
        ).distinct()
    return qs.none()


def filter_expenses(qs, user):
    if not user.is_authenticated:
        return qs.none()
    codes = user_stakeholder_codes(user)
    if user.is_superuser or codes & {
        UserProfile.StakeholderType.FOUNDATION_ADMIN,
        UserProfile.StakeholderType.FINANCE_CONTROLLER,
        UserProfile.StakeholderType.GOVERNANCE,
        UserProfile.StakeholderType.AUDITOR,
    }:
        return qs
    if UserProfile.StakeholderType.PROJECT_LEAD in codes:
        return qs.filter(project__lead=user)
    return qs.none()


def can_record_contribution(user):
    codes = user_stakeholder_codes(user)
    return user.is_superuser or codes & {
        UserProfile.StakeholderType.FOUNDATION_ADMIN,
        UserProfile.StakeholderType.FINANCE_CONTROLLER,
    }


def can_manage_expense(user):
    codes = user_stakeholder_codes(user)
    return user.is_superuser or codes & {
        UserProfile.StakeholderType.FOUNDATION_ADMIN,
        UserProfile.StakeholderType.FINANCE_CONTROLLER,
        UserProfile.StakeholderType.PROJECT_LEAD,
    }


def can_approve_expense(user):
    codes = user_stakeholder_codes(user)
    return user.is_superuser or codes & {
        UserProfile.StakeholderType.FOUNDATION_ADMIN,
        UserProfile.StakeholderType.FINANCE_CONTROLLER,
        UserProfile.StakeholderType.GOVERNANCE,
    }
