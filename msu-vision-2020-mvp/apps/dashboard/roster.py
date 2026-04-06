"""
Governance roster: group users by stakeholder persona, search, and simple availability hints
for assigning project leads and volunteers (based on current workload only; not calendars).
"""

from django.contrib.auth import get_user_model
from django.db.models import Count, Q

from apps.projects.models import Project, ProjectTeam
from apps.stakeholders.models import UserProfile
from apps.stakeholders.persona_utils import pick_primary_persona

User = get_user_model()

# Projects where being "lead" counts toward capacity
ACTIVE_LEAD_STATUSES = (
    Project.Status.PROPOSED,
    Project.Status.PENDING_GOVERNANCE,
    Project.Status.APPROVED,
    Project.Status.IN_PROGRESS,
    Project.Status.ON_HOLD,
)

# At or below → show as likely available for new lead / volunteer slot
MAX_LEADS_FOR_AVAILABLE = 2
MAX_VOLUNTEER_TEAMS_FOR_AVAILABLE = 4


def _lead_count_by_user():
    return dict(
        Project.objects.filter(status__in=ACTIVE_LEAD_STATUSES, lead_id__isnull=False)
        .values("lead_id")
        .annotate(c=Count("id"))
        .values_list("lead_id", "c")
    )


def _volunteer_team_count_by_user():
    return dict(
        ProjectTeam.objects.filter(role=ProjectTeam.Role.VOLUNTEER)
        .values("user_id")
        .annotate(c=Count("id"))
        .values_list("user_id", "c")
    )


def availability_for(stakeholder_type: str, user_id: int, lead_counts: dict, vol_counts: dict):
    """Return (status, metric_int|None, short_hint). status in: available, busy, neutral."""
    if stakeholder_type == UserProfile.StakeholderType.PROJECT_LEAD:
        n = lead_counts.get(user_id, 0)
        if n <= MAX_LEADS_FOR_AVAILABLE:
            return "available", n, f"{n} active lead role(s)"
        return "busy", n, f"{n} active lead role(s) — consider before adding"
    if stakeholder_type == UserProfile.StakeholderType.VOLUNTEER:
        n = vol_counts.get(user_id, 0)
        if n <= MAX_VOLUNTEER_TEAMS_FOR_AVAILABLE:
            return "available", n, f"{n} project team(s)"
        return "busy", n, f"{n} project team(s) — may be at capacity"
    return "neutral", None, "Use for governance / sponsorship / oversight roles"


def active_users_queryset(search: str):
    qs = (
        User.objects.filter(is_active=True, profile__isnull=False)
        .select_related("profile", "profile__organization")
        .order_by("username")
    )
    q = (search or "").strip()
    if q:
        qs = qs.filter(
            Q(username__icontains=q)
            | Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(email__icontains=q)
        )
    return qs


def users_needing_persona_assignment(search: str):
    """Imported / incomplete profiles flagged for governance."""
    return list(
        active_users_queryset(search)
        .filter(profile__needs_persona_assignment=True)
        .prefetch_related("stakeholder_personas")
    )


def persona_cards(search: str):
    lead_counts = _lead_count_by_user()
    vol_counts = _volunteer_team_count_by_user()
    base = active_users_queryset(search)
    choice_map = dict(UserProfile.StakeholderType.choices)
    cards = []
    for value, label in UserProfile.StakeholderType.choices:
        qs = base.filter(stakeholder_personas__persona_type=value).distinct()
        total = qs.count()
        rows = []
        for u in qs[:40]:
            st, metric, hint = availability_for(value, u.pk, lead_counts, vol_counts)
            persona_labels = ", ".join(
                choice_map[t] for t in sorted(u.stakeholder_personas.values_list("persona_type", flat=True))
            )
            rows.append(
                {
                    "user": u,
                    "availability": st,
                    "metric": metric,
                    "hint": hint,
                    "persona_labels": persona_labels or label,
                }
            )
        cards.append(
            {
                "key": value,
                "label": label,
                "count": total,
                "rows": rows,
                "truncated": total > 40,
            }
        )
    return cards


def unified_search_hits(search: str):
    """Cross-persona matches when user typed a name (max 80)."""
    q = (search or "").strip()
    if not q:
        return []
    lead_counts = _lead_count_by_user()
    vol_counts = _volunteer_team_count_by_user()
    choice_map = dict(UserProfile.StakeholderType.choices)
    out = []
    for u in active_users_queryset(q)[:80]:
        codes = u.profile.persona_codes()
        st = pick_primary_persona(codes) or u.profile.stakeholder_type
        av, metric, hint = availability_for(st, u.pk, lead_counts, vol_counts)
        linked = sorted(u.stakeholder_personas.values_list("persona_type", flat=True))
        if u.profile.needs_persona_assignment and not linked:
            role_label = "Persona not identified"
        elif linked:
            role_label = ", ".join(choice_map[t] for t in linked)
        else:
            role_label = u.profile.get_stakeholder_type_display()
        out.append(
            {
                "user": u,
                "role_label": role_label,
                "stakeholder_type": st,
                "availability": av,
                "metric": metric,
                "hint": hint,
                "org": u.profile.organization.name if u.profile.organization_id else None,
                "needs_persona_assignment": u.profile.needs_persona_assignment and not linked,
            }
        )
    return out
