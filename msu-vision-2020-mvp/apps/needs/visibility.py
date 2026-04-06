from django.db.models import Q

from apps.core.permissions import user_stakeholder_codes
from apps.stakeholders.models import UserProfile


def filter_needs_for_user(qs, user):
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

    q = None
    if UserProfile.StakeholderType.HOD in codes:
        org_id = getattr(user.profile, "organization_id", None)
        hod_q = (
            Q(created_by=user) | Q(department_id=org_id) if org_id else Q(created_by=user)
        )
        q = hod_q if q is None else q | hod_q
    if UserProfile.StakeholderType.DONOR in codes:
        d_q = Q(matched_donors=user)
        q = d_q if q is None else q | d_q
    if codes & {
        UserProfile.StakeholderType.PROJECT_LEAD,
        UserProfile.StakeholderType.VOLUNTEER,
    }:
        pv_q = Q(projects__lead=user) | Q(projects__team_members__user=user)
        q = pv_q if q is None else q | pv_q

    if q is None:
        return qs.filter(created_by=user)
    return qs.filter(q).distinct()


def filter_projects_for_user(qs, user):
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

    q = None
    if UserProfile.StakeholderType.DONOR in codes:
        d_q = Q(need__matched_donors=user)
        q = d_q if q is None else q | d_q
    if UserProfile.StakeholderType.HOD in codes:
        org_id = getattr(user.profile, "organization_id", None)
        hod_q = (
            Q(need__created_by=user) | Q(need__department_id=org_id)
            if org_id
            else Q(need__created_by=user)
        )
        q = hod_q if q is None else q | hod_q

    if q is None:
        return qs.filter(Q(lead=user) | Q(team_members__user=user)).distinct()
    return qs.filter(q | Q(lead=user) | Q(team_members__user=user)).distinct()


def can_edit_need(user, need):
    codes = user_stakeholder_codes(user)
    if user.is_superuser or UserProfile.StakeholderType.FOUNDATION_ADMIN in codes:
        return True
    if UserProfile.StakeholderType.HOD in codes and need.created_by_id == user.id and need.status == "draft":
        return True
    return False


def can_transition_need(user, need):
    """Architecture §5.2 — need status changes: Admin; high-value governance path."""
    codes = user_stakeholder_codes(user)
    if user.is_superuser or UserProfile.StakeholderType.FOUNDATION_ADMIN in codes:
        return True
    if UserProfile.StakeholderType.GOVERNANCE in codes and need.status == "pending_governance":
        return True
    return False


def can_match_need(user):
    codes = user_stakeholder_codes(user)
    return user.is_superuser or UserProfile.StakeholderType.FOUNDATION_ADMIN in codes


def can_create_project(user, need):
    """Matched need → project; Foundation Admin or Governance (architecture RBAC + request)."""
    codes = user_stakeholder_codes(user)
    if need.status != "matched":
        return False
    return user.is_superuser or codes & {
        UserProfile.StakeholderType.FOUNDATION_ADMIN,
        UserProfile.StakeholderType.GOVERNANCE,
    }


def can_initiate_project_creation(user):
    """Who may start the create flow (choose a matched need)."""
    codes = user_stakeholder_codes(user)
    return user.is_superuser or codes & {
        UserProfile.StakeholderType.FOUNDATION_ADMIN,
        UserProfile.StakeholderType.GOVERNANCE,
    }


def can_manage_milestones(user, project):
    codes = user_stakeholder_codes(user)
    if user.is_superuser or UserProfile.StakeholderType.FOUNDATION_ADMIN in codes:
        return True
    if UserProfile.StakeholderType.PROJECT_LEAD in codes and project.lead_id == user.id:
        return True
    return False


def can_release_milestone_funding(user):
    codes = user_stakeholder_codes(user)
    return user.is_superuser or codes & {
        UserProfile.StakeholderType.FOUNDATION_ADMIN,
        UserProfile.StakeholderType.GOVERNANCE,
    }
