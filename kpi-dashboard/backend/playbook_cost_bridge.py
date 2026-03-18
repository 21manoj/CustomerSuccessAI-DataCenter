"""
Playbook-to-ROI Cost Bridge Module.

Architecture: Option B — JSON benchmarks (power_of_1_economics.json) stay as
source of truth for investment budgets. Playbook costs (from PLAYBOOK_CONFIG)
provide operational transparency. The bridge derives affordable_runs from budget.

Bridge formula (equal split):
  For each metric M with N linked playbooks:
    per_playbook_budget = M.cs_initiative_cost / N
    For each playbook P:
      manual_cost = sum(manual_hours) * csm_rate
      affordable_runs = per_playbook_budget / manual_cost
      lift_per_run = (1% / N) / affordable_runs
      impact_per_run = lift * annual_impact_per_pct * arr_scale
      roi_per_run = impact_per_run / manual_cost

No DB access, no Flask dependency. Pure calculation.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class PlaybookEconomics:
    """Per-playbook economics derived from the cost bridge."""
    playbook_id: str
    playbook_name: str
    metric_id: str
    metric_display_name: str
    # Hour breakdown
    total_hours: float
    manual_hours: float
    automated_hours: float
    automation_pct: float               # automated / total * 100
    # Cost per run
    manual_cost: float                  # manual_hours * csm_rate
    cost_without_platform: float        # total_hours * csm_rate (counterfactual)
    platform_savings_per_run: float     # cost_without_platform - manual_cost
    # Bridge economics
    budget_allocated: float             # cs_initiative_cost / N
    affordable_runs: float              # budget / manual_cost
    lift_per_run_pct: float             # (1% / N) / affordable_runs
    impact_per_run: float               # lift * annual_impact_per_pct * arr_scale
    roi_per_run: float                  # impact / manual_cost
    break_even_arr: float               # (manual_cost / impact_at_10M) * $10M
    # Sub-component detail
    sub_components: List[Dict] = field(default_factory=list)


@dataclass
class MetricBridgeEconomics:
    """Per-metric bridge economics aggregating linked playbooks."""
    metric_id: str
    metric_display_name: str
    cs_initiative_cost: float
    platform_cost: float
    total_investment: float
    annual_impact_per_pct: float
    linked_playbook_count: int
    per_playbook_budget: float
    playbooks: List[PlaybookEconomics] = field(default_factory=list)
    # 3-column breakdown
    investment_csm: float = 0.0
    investment_platform: float = 0.0
    investment_misc: float = 0.0


@dataclass
class CostBridgeResult:
    """Complete cost bridge output."""
    metrics: Dict[str, MetricBridgeEconomics] = field(default_factory=dict)
    playbooks: Dict[str, PlaybookEconomics] = field(default_factory=dict)
    totals: Dict[str, float] = field(default_factory=dict)
    csm_rate: float = 95.0
    arr_scale: float = 1.0
    arr_basis: float = 10_000_000


# ---------------------------------------------------------------------------
# Primary mapping: playbook → primary Power-of-1 metric (for single lookups)
# Matches _PLAYBOOK_ROI_MAP in api_routes.py
# ---------------------------------------------------------------------------

_PRIMARY_METRIC_MAP = {
    'PB-01': 'TTFV',
    'PB-02': 'ticket_resolution_time',
    'PB-03': 'product_adoption',
    'PB-04': 'expansion_rate',
    'PB-05': 'GRR',
    'PB-06': 'expansion_rate',
}


# ---------------------------------------------------------------------------
# Core bridge calculation
# ---------------------------------------------------------------------------

def calculate_cost_bridge(
    account_arr: Optional[float] = None,
    csm_rate_override: Optional[float] = None,
) -> CostBridgeResult:
    """
    Build the complete playbook-to-ROI cost bridge.

    For each metric in power_of_1_economics.json:
      - Get dc2s_linked_playbooks (the playbooks that serve this metric)
      - Equal-split the cs_initiative_cost budget across N playbooks
      - Derive affordable_runs, lift_per_run, impact_per_run, roi_per_run

    Args:
        account_arr: Customer ARR for scaling (default: $10M baseline)
        csm_rate_override: Override CSM hourly rate (default: from resource_rates.json)

    Returns:
        CostBridgeResult with per-metric and per-playbook economics
    """
    # Lazy imports to avoid circular dependencies
    from verticals.dc2_s.vertical_config import PLAYBOOK_CONFIG
    from power_of_1_model import POWER_OF_1_METRICS

    # Get CSM rate
    csm_rate = csm_rate_override or _get_csm_rate()
    arr = account_arr or 10_000_000
    arr_scale = arr / 10_000_000

    result = CostBridgeResult(
        csm_rate=csm_rate,
        arr_scale=arr_scale,
        arr_basis=arr,
    )

    total_csm = 0.0
    total_platform = 0.0
    total_misc = 0.0

    for metric_id, metric in POWER_OF_1_METRICS.items():
        linked_pbs = metric.dc2s_linked_playbooks
        if not linked_pbs:
            continue

        N = len(linked_pbs)
        per_pb_budget = metric.cs_initiative_cost / N

        metric_bridge = MetricBridgeEconomics(
            metric_id=metric_id,
            metric_display_name=metric.display_name,
            cs_initiative_cost=metric.cs_initiative_cost,
            platform_cost=metric.platform_cost,
            total_investment=metric.total_investment,
            annual_impact_per_pct=metric.annual_impact_per_pct,
            linked_playbook_count=N,
            per_playbook_budget=per_pb_budget,
        )

        for pb_id in linked_pbs:
            pb_config = PLAYBOOK_CONFIG.get(pb_id)
            if not pb_config:
                continue

            sub_comps = pb_config.get('sub_components', [])
            total_hrs = sum(sc.get('estimated_hours', 0) for sc in sub_comps)
            manual_hrs = sum(sc.get('manual_hours', sc.get('estimated_hours', 0)) for sc in sub_comps)
            auto_hrs = sum(sc.get('automated_hours', 0) for sc in sub_comps)

            manual_cost = manual_hrs * csm_rate
            cost_without = total_hrs * csm_rate
            savings = cost_without - manual_cost

            # Bridge calculations
            affordable_runs = per_pb_budget / manual_cost if manual_cost > 0 else 0
            # Each playbook contributes (1/N) of the 1% target improvement
            lift_per_run = ((1.0 / N) / affordable_runs) if affordable_runs > 0 else 0
            impact_per_run = lift_per_run * metric.annual_impact_per_pct * arr_scale
            roi_per_run = impact_per_run / manual_cost if manual_cost > 0 else 0

            # Break-even: at what ARR does a single run pay for itself?
            impact_at_10M = lift_per_run * metric.annual_impact_per_pct  # at $10M base
            break_even = (manual_cost / impact_at_10M * 10_000_000) if impact_at_10M > 0 else float('inf')

            automation_pct = round(auto_hrs / total_hrs * 100, 1) if total_hrs > 0 else 0

            # Build sub-component detail
            sc_detail = []
            for sc in sub_comps:
                sc_manual = sc.get('manual_hours', sc.get('estimated_hours', 0))
                sc_auto = sc.get('automated_hours', 0)
                sc_detail.append({
                    'id': sc['id'],
                    'name': sc['name'],
                    'estimated_hours': sc.get('estimated_hours', 0),
                    'manual_hours': sc_manual,
                    'automated_hours': sc_auto,
                    'manual_cost': round(sc_manual * csm_rate, 2),
                })

            pb_econ = PlaybookEconomics(
                playbook_id=pb_id,
                playbook_name=pb_config.get('name', pb_id),
                metric_id=metric_id,
                metric_display_name=metric.display_name,
                total_hours=total_hrs,
                manual_hours=manual_hrs,
                automated_hours=auto_hrs,
                automation_pct=automation_pct,
                manual_cost=round(manual_cost, 2),
                cost_without_platform=round(cost_without, 2),
                platform_savings_per_run=round(savings, 2),
                budget_allocated=round(per_pb_budget, 2),
                affordable_runs=round(affordable_runs, 2),
                lift_per_run_pct=round(lift_per_run, 6),
                impact_per_run=round(impact_per_run, 2),
                roi_per_run=round(roi_per_run, 2),
                break_even_arr=round(break_even, 0),
                sub_components=sc_detail,
            )

            metric_bridge.playbooks.append(pb_econ)
            key = f"{pb_id}:{metric_id}"
            result.playbooks[key] = pb_econ

        # 3-column breakdown for this metric
        metric_bridge.investment_csm = round(metric.cs_initiative_cost, 2)
        metric_bridge.investment_platform = round(metric.platform_cost, 2)
        metric_bridge.investment_misc = round(
            metric.total_investment - metric.cs_initiative_cost - metric.platform_cost, 2
        )

        total_csm += metric_bridge.investment_csm
        total_platform += metric_bridge.investment_platform
        total_misc += metric_bridge.investment_misc

        result.metrics[metric_id] = metric_bridge

    result.totals = {
        'total_csm': round(total_csm, 2),
        'total_platform': round(total_platform, 2),
        'total_misc': round(total_misc, 2),
        'grand_total': round(total_csm + total_platform + total_misc, 2),
    }

    return result


# ---------------------------------------------------------------------------
# Single-playbook lookup (for CSM daily actions integration)
# ---------------------------------------------------------------------------

def get_playbook_economics(
    playbook_id: str,
    metric_id: Optional[str] = None,
    account_arr: Optional[float] = None,
) -> Optional[PlaybookEconomics]:
    """
    Get economics for a single playbook.

    If metric_id is not specified, uses the primary metric from _PRIMARY_METRIC_MAP.
    This is the function called by CSM daily actions to enrich each action
    with cost context.

    Args:
        playbook_id: e.g. "PB-05"
        metric_id: e.g. "GRR" (optional, auto-resolved)
        account_arr: Customer ARR for scaling

    Returns:
        PlaybookEconomics or None if not found
    """
    if not metric_id:
        metric_id = _PRIMARY_METRIC_MAP.get(playbook_id)
    if not metric_id:
        return None

    bridge = calculate_cost_bridge(account_arr=account_arr)
    key = f"{playbook_id}:{metric_id}"
    return bridge.playbooks.get(key)


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------

def bridge_to_dict(result: CostBridgeResult) -> Dict:
    """Serialize CostBridgeResult for API response."""
    metrics_dict = {}
    for metric_id, m in result.metrics.items():
        metrics_dict[metric_id] = {
            'metric_id': m.metric_id,
            'metric_display_name': m.metric_display_name,
            'cs_initiative_cost': m.cs_initiative_cost,
            'platform_cost': m.platform_cost,
            'total_investment': m.total_investment,
            'annual_impact_per_pct': m.annual_impact_per_pct,
            'linked_playbook_count': m.linked_playbook_count,
            'per_playbook_budget': m.per_playbook_budget,
            'investment_csm': m.investment_csm,
            'investment_platform': m.investment_platform,
            'investment_misc': m.investment_misc,
            'playbooks': [_pb_to_dict(pb) for pb in m.playbooks],
        }

    playbooks_dict = {}
    for key, pb in result.playbooks.items():
        playbooks_dict[key] = _pb_to_dict(pb)

    return {
        'metrics': metrics_dict,
        'playbooks': playbooks_dict,
        'totals': result.totals,
        'csm_rate': result.csm_rate,
        'arr_scale': result.arr_scale,
        'arr_basis': result.arr_basis,
    }


def _pb_to_dict(pb: PlaybookEconomics) -> Dict:
    """Serialize a single PlaybookEconomics."""
    return {
        'playbook_id': pb.playbook_id,
        'playbook_name': pb.playbook_name,
        'metric_id': pb.metric_id,
        'metric_display_name': pb.metric_display_name,
        'total_hours': pb.total_hours,
        'manual_hours': pb.manual_hours,
        'automated_hours': pb.automated_hours,
        'automation_pct': pb.automation_pct,
        'manual_cost': pb.manual_cost,
        'cost_without_platform': pb.cost_without_platform,
        'platform_savings_per_run': pb.platform_savings_per_run,
        'budget_allocated': pb.budget_allocated,
        'affordable_runs': pb.affordable_runs,
        'lift_per_run_pct': pb.lift_per_run_pct,
        'impact_per_run': pb.impact_per_run,
        'roi_per_run': pb.roi_per_run,
        'break_even_arr': pb.break_even_arr,
        'sub_components': pb.sub_components,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_csm_rate() -> float:
    """Get CSM hourly rate from resource_rates.json (via resource_capacity_model)."""
    try:
        from resource_capacity_model import ROLE_RATES
        return ROLE_RATES.get('csm', 95.0)
    except (ImportError, Exception):
        return 95.0  # Fallback
