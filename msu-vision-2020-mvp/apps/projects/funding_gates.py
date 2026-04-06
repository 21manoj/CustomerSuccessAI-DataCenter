"""Milestone-based funding tranches (% of project budget) and governance release metrics."""

from apps.projects.models import Milestone, Project


def project_funding_gate_metrics(project: Project) -> dict:
    """
    Percents are shares of total project budget (next_tranche_budget_percent per milestone).
    - released: done + governance released
    - pending_governance: done + awaiting governance (proof required to reach done)
    - upcoming: milestone not done yet (tranche not yet eligible)
    - rejected: done + governance rejected this tranche
    """
    ms = project.milestones.exclude(status=Milestone.Status.CANCELLED)
    released = pending = upcoming = rejected = 0
    for m in ms:
        pct = m.next_tranche_budget_percent or 0
        if pct <= 0:
            continue
        if m.status != Milestone.Status.DONE:
            upcoming += pct
            continue
        st = m.tranche_governance_status
        if st == Milestone.TrancheGovernance.RELEASED:
            released += pct
        elif st == Milestone.TrancheGovernance.AWAITING_GOVERNANCE:
            pending += pct
        elif st == Milestone.TrancheGovernance.REJECTED:
            rejected += pct
        else:
            pending += pct
    tranches_total = released + pending + upcoming + rejected
    return {
        "released_pct": released,
        "pending_governance_pct": pending,
        "upcoming_pct": upcoming,
        "rejected_pct": rejected,
        "tranches_total_pct": tranches_total,
    }


def milestones_awaiting_funding_release():
    return (
        Milestone.objects.filter(
            status=Milestone.Status.DONE,
            tranche_governance_status=Milestone.TrancheGovernance.AWAITING_GOVERNANCE,
            next_tranche_budget_percent__gt=0,
        )
        .select_related("project", "project__need")
        .order_by("project_id", "sequence")
    )
