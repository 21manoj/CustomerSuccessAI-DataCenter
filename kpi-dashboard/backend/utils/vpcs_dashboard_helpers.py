"""VPCS dashboard helpers — capacity planning, allocation, critical→expansion performers."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List

import utils.health_thresholds as ht


def _assigned_csm(acct) -> str:
    meta = acct.profile_metadata if isinstance(acct.profile_metadata, dict) else {}
    return meta.get('assigned_csm') or meta.get('csm_name') or 'Unassigned'


def build_capacity_planning(customer_id: int, accounts: list) -> Dict[str, Any]:
    """
    Headcount + allocation guidance for VP CS.
    Uses account load, hours feasibility (when available), and playbook outcomes.
    """
    from models import PlaybookExecutionV2

    healthy_min = ht.healthy_min()
    at_risk_min = ht.at_risk_min()

    acct_by_csm: Dict[str, list] = defaultdict(list)
    for acct in accounts:
        acct_by_csm[_assigned_csm(acct)].append(acct)

    csm_names = [c for c in acct_by_csm if c != 'Unassigned']
    csm_count = max(len(csm_names), 1)
    total_accounts = len(accounts)
    target_per_csm = 6
    at_risk = sum(
        1 for a in accounts
        if _latest_health(a) < healthy_min
    )

    # Recommended CSMs: cover at-risk load (2:1 at-risk:CSM cap) + portfolio breadth
    at_risk_per_csm_cap = 4
    need_for_risk = max(1, (at_risk + at_risk_per_csm_cap - 1) // at_risk_per_csm_cap) if at_risk else 0
    need_for_breadth = max(1, (total_accounts + target_per_csm - 1) // target_per_csm)
    recommended = max(csm_count, need_for_risk, need_for_breadth)

    cutoff = datetime.utcnow() - timedelta(days=90)
    execs = PlaybookExecutionV2.query.filter(
        PlaybookExecutionV2.customer_id == customer_id,
        PlaybookExecutionV2.triggered_at >= cutoff,
    ).all()

    recovery_wins: Dict[str, int] = defaultdict(int)
    expansion_dollars: Dict[str, float] = defaultdict(float)
    playbook_expansion: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    playbook_recovery: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

    acct_id_to_csm = {a.account_id: _assigned_csm(a) for a in accounts}

    for ex in execs:
        csm = acct_id_to_csm.get(ex.account_id, 'Unassigned')
        hd = float(ex.health_delta or 0)
        rev_exp = float(ex.revenue_expanded or 0)
        rev_prot = float(ex.revenue_protected or 0)
        pb = ex.playbook_id or 'unknown'

        if ex.outcome == 'resolved' and hd >= 5:
            recovery_wins[csm] += 1
            playbook_recovery[csm][pb] += 1
        if rev_exp > 0:
            expansion_dollars[csm] += rev_exp
            playbook_expansion[csm][pb] += 1
        elif rev_prot > 0 and hd > 0:
            recovery_wins[csm] += 1
            playbook_recovery[csm][pb] += 1

    # Health transitions critical/at_risk → healthy (portfolio history signal)
    try:
        from models import HealthScore

        for acct in accounts:
            scores = (
                HealthScore.query.filter_by(account_id=acct.account_id)
                .order_by(HealthScore.measurement_month.asc())
                .all()
            )
            if len(scores) < 2:
                continue
            first_s = float(scores[0].health_score or 0)
            last_s = float(scores[-1].health_score or 0)
            if first_s < healthy_min and last_s >= healthy_min:
                csm = _assigned_csm(acct)
                recovery_wins[csm] += 1
    except Exception:
        pass

    performers: List[Dict[str, Any]] = []
    for csm in sorted(csm_names, key=lambda c: (-recovery_wins[c], -expansion_dollars[c])):
        top_pbs = sorted(
            playbook_expansion[csm].items(),
            key=lambda x: -x[1],
        )[:3]
        performers.append({
            'csm_name': csm,
            'recovery_wins': recovery_wins[csm],
            'expansion_dollars': round(expansion_dollars[csm], 0),
            'critical_to_expansion_score': recovery_wins[csm] + (
                1 if expansion_dollars[csm] > 0 else 0
            ),
            'top_playbooks': [
                {'playbook_id': pb, 'expansion_events': n}
                for pb, n in top_pbs
            ],
            'top_recovery_playbooks': [
                {'playbook_id': pb, 'recovery_events': n}
                for pb, n in sorted(
                    playbook_recovery[csm].items(), key=lambda x: -x[1]
                )[:3]
            ],
        })

    performers.sort(
        key=lambda p: (
            -p['critical_to_expansion_score'],
            -p['expansion_dollars'],
            -p['recovery_wins'],
        ),
    )

    return {
        'csm_count_current': csm_count,
        'recommended_csm_count': recommended,
        'target_accounts_per_csm': target_per_csm,
        'accounts_per_csm_current': round(total_accounts / csm_count, 1),
        'at_risk_accounts': at_risk,
        'allocation_rationale': (
            f'{total_accounts} accounts across {csm_count} CSM(s); '
            f'{at_risk} below health {healthy_min}. '
            f'Target ~{target_per_csm} accounts/CSM; recommend {recommended} CSM(s) '
            f'to keep at-risk load ≤{at_risk_per_csm_cap} per CSM.'
        ),
        'top_performers': performers[:8],
        'label_modeled': True,
    }


def build_uncovered_at_risk(customer_id: int, accounts: list, days_without_touch: int = 45) -> List[Dict[str, Any]]:
    """Accounts below healthy threshold with no playbook execution in window."""
    from models import PlaybookExecutionV2

    healthy_min = ht.healthy_min()
    cutoff = datetime.utcnow() - timedelta(days=days_without_touch)
    uncovered = []

    for acct in accounts:
        if _latest_health(acct) >= healthy_min:
            continue
        last_exec = (
            PlaybookExecutionV2.query.filter_by(
                customer_id=customer_id,
                account_id=acct.account_id,
            )
            .order_by(PlaybookExecutionV2.triggered_at.desc())
            .first()
        )
        if last_exec and last_exec.triggered_at and last_exec.triggered_at >= cutoff:
            continue
        days_since = days_without_touch
        if last_exec and last_exec.triggered_at:
            days_since = (datetime.utcnow() - last_exec.triggered_at).days
        uncovered.append({
            'account_id': acct.account_id,
            'account_name': acct.account_name,
            'health_score': round(_latest_health(acct), 1),
            'arr': float(acct.revenue or 0),
            'assigned_csm': _assigned_csm(acct),
            'days_without_playbook': days_since,
        })

    uncovered.sort(key=lambda x: (-x['arr'], x['health_score']))
    return uncovered[:15]


def _latest_health(acct) -> float:
    try:
        from verticals.dc2_s.api_routes import get_precalculated_scores
        h, _, _, _ = get_precalculated_scores(acct.account_id)
        return float(h or 0)
    except Exception:
        return 0.0
