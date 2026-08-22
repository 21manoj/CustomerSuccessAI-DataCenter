"""
CFO dashboard helpers — Phase 3 modeled ROI scaling + playbook-economics efficiency.

Pure functions (no Flask) for unit tests and executive_dashboard_api.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

# Cap modeled ROI % shown on scaling cards (Po1 sums all metric impacts).
ROI_PCT_DISPLAY_CAP = 500


def resolve_cfo_roi_pct(
    roi_snap: Any,
    power_of_1_metrics: List[dict],
    estimated_investment: float,
    *,
    roi_impact: float = 0.0,
) -> Tuple[int, float, bool]:
    """
    Resolve portfolio ROI % for CFO scaling tiles.

    Returns (roi_pct_capped, roi_multiple, is_modeled).
    When snapshot ROI is 0 but Po1 metrics exist, derive from benchmark impacts.
    """
    roi_pct = 0
    investment = estimated_investment or 0.0
    impact = roi_impact or 0.0
    is_modeled = False

    if roi_snap:
        roi_pct = round(roi_snap.historical_roi_pct or roi_snap.combined_roi_pct or 0)
        impact = impact or float(roi_snap.historical_impact or roi_snap.forward_impact or 0)
        if roi_snap.historical_investment:
            investment = float(roi_snap.historical_investment)

    if roi_pct <= 0 and power_of_1_metrics and investment > 0:
        from power_of_1_model import dedupe_portfolio_dollar_impact
        total_impact = dedupe_portfolio_dollar_impact(power_of_1_metrics)
        if total_impact > 0:
            impact = total_impact
            is_modeled = True
            roi_pct = _impact_to_roi_pct(total_impact, investment)

    if roi_pct > ROI_PCT_DISPLAY_CAP:
        roi_pct = ROI_PCT_DISPLAY_CAP

    multiple = round(impact / investment, 1) if investment > 0 and impact > 0 else 0.0
    return roi_pct, multiple, is_modeled


def _impact_to_roi_pct(total_impact: float, investment: float) -> int:
    if investment <= 0:
        return 0
    multiple = total_impact / investment
    raw = round((multiple - 1) * 100) if multiple > 1 else round(multiple * 100)
    return min(max(raw, 0), ROI_PCT_DISPLAY_CAP)


def build_roi_scaling(
    roi_pct: int,
    num_accounts: int,
    *,
    is_modeled: bool = False,
) -> Dict[str, Any]:
    """Non-linear scaling projections with data-driven growth_bar widths."""
    projections: List[Dict[str, Any]] = []
    raw_values: List[int] = []

    for target_accounts in [10, 50, 200]:
        if num_accounts > 0 and roi_pct > 0:
            scale_factor = 1 + math.log(
                max(target_accounts / max(num_accounts, 1), 1) + 1
            ) * 0.8
            projected_roi = round(roi_pct * scale_factor)
        else:
            projected_roi = 0
        raw_values.append(projected_roi)
        projections.append({'accounts': target_accounts, 'roi': projected_roi})

    max_roi = max(raw_values) if raw_values else 0
    for i, proj in enumerate(projections):
        roi_val = proj['roi']
        if max_roi > 0 and roi_val > 0:
            growth_bar = max(8, round(roi_val / max_roi * 100))
        else:
            growth_bar = 0
        proj['growth_bar'] = growth_bar

    return {
        'current_accounts': num_accounts,
        'current_roi': roi_pct,
        'roi_multiple': None,  # filled by caller if needed
        'is_modeled': is_modeled,
        'projections': projections,
    }


def build_cfo_efficiency_metrics(
    customer_id: int,
    total_arr: float,
    proof_data: Dict[str, Any],
    effective_investment: float,
    roi_impact: float,
) -> Dict[str, Any]:
    """
    Efficiency block from playbook cost bridge (modeled) or closed executions (proof).
    """
    empty = {
        'available': False,
        'source': 'unavailable',
        'efficiency_score': 0,
        'automation_rate': 0,
        'time_saved_hours': 0,
        'rev_per_cs_dollar': 0.0,
    }

    proof_cost = float(proof_data.get('total_cost') or 0)
    proof_value = float(proof_data.get('revenue_protected') or 0) + float(
        proof_data.get('revenue_expanded') or 0
    )

    if proof_cost > 0 and proof_value > 0:
        rev_per = round(proof_value / proof_cost, 1)
        return {
            'available': True,
            'source': 'csPulseProof',
            'efficiency_score': min(100, round(rev_per * 12)),
            'automation_rate': 0,
            'time_saved_hours': round(float(proof_data.get('csm_hours') or 0) * 0.35, 0),
            'rev_per_cs_dollar': rev_per,
            'label': 'Revenue per CS dollar (playbook proof)',
        }

    if total_arr <= 0:
        return empty

    try:
        from playbook_cost_bridge import calculate_cost_bridge

        vertical = _customer_vertical(customer_id)
        bridge = calculate_cost_bridge(account_arr=float(total_arr), vertical=vertical)
    except Exception:
        return empty

    total_hours = 0.0
    auto_hours = 0.0
    for pb in bridge.playbooks.values():
        runs = max(float(pb.affordable_runs or 0), 1.0)
        total_hours += float(pb.total_hours or 0) * runs
        auto_hours += float(pb.automated_hours or 0) * runs

    if total_hours <= 0:
        return empty

    automation_rate = round(auto_hours / total_hours * 100, 1)
    time_saved_hours = round(auto_hours, 0)
    rev_per = (
        round(roi_impact / effective_investment, 1)
        if effective_investment > 0 and roi_impact > 0
        else 0.0
    )
    efficiency_score = min(100, round(rev_per * 12)) if rev_per > 0 else min(
        100, round(automation_rate * 1.2)
    )

    return {
        'available': True,
        'source': 'benchmark',
        'efficiency_score': efficiency_score,
        'automation_rate': automation_rate,
        'time_saved_hours': time_saved_hours,
        'rev_per_cs_dollar': rev_per,
        'label': 'Modeled from playbook economics (Power-of-1)',
    }


def _customer_vertical(customer_id: int) -> str:
    try:
        from models import Customer, CustomerConfig
        from utils.vertical_registry import normalize_vertical

        cfg = CustomerConfig.query.filter_by(customer_id=int(customer_id)).first()
        if cfg and cfg.vertical:
            return normalize_vertical(cfg.vertical)
        cust = Customer.query.get(int(customer_id))
        return normalize_vertical(getattr(cust, 'vertical', None) or 'dc2_s')
    except Exception:
        return 'dc2_s'
