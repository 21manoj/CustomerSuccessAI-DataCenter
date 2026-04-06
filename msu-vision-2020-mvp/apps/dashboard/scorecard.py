"""Organization-wide impact stats for the home dashboard scorecard."""

from decimal import Decimal

from django.db.models import Sum

from apps.funding.models import Contribution
from apps.projects.models import Project


def organization_scorecard():
    """
    Donations: USD totals from Contribution.amount_usd (MVP FX on save).
    Collected = received / allocated / utilized; pledged = pledged status only.
    Projects: all except rejected. Students: sum of optional Project.students_impacted.
    """
    collected = (
        Contribution.objects.filter(
            status__in=(
                Contribution.Status.RECEIVED,
                Contribution.Status.ALLOCATED,
                Contribution.Status.UTILIZED,
            )
        ).aggregate(s=Sum("amount_usd"))["s"]
        or Decimal("0")
    )
    pledged = (
        Contribution.objects.filter(status=Contribution.Status.PLEDGED).aggregate(s=Sum("amount_usd"))["s"]
        or Decimal("0")
    )
    projects_qs = Project.objects.exclude(status=Project.Status.REJECTED)
    projects_count = projects_qs.count()
    students = projects_qs.aggregate(s=Sum("students_impacted"))["s"] or 0
    return {
        "donations_collected_usd": collected,
        "donations_pledged_usd": pledged,
        "projects_count": projects_count,
        "students_impacted": int(students),
    }
