#!/usr/bin/env python3
"""
Outcome ROI Engine — Historical Proof + Forward Projection
============================================================
Both views are OUTCOME-FOCUSED, not operations-focused.

The headline is always dollars and Power of 1 metrics.
The 38 KPIs are mechanism/evidence — drill-in only.

Historical:  "We invested $X, we delivered $Y → here's the ROI"
Forward:     "We'll invest $X, we'll deliver $Y → here's the projected ROI"

Both use the same Power of 1 economic model. The difference:
  - Historical: actual metric movements → realized dollars
  - Forward:    projected metric movements → projected dollars
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime, date, timedelta
from enum import Enum

from power_of_1_model import (
    POWER_OF_1_METRICS,
    INVESTMENT_SUMMARY,
    SCALING_SCENARIOS,
    METRIC_CASCADES,
    COMPOUNDING_MULTIPLIER,
    ImpactType,
    calculate_power_of_1_impact,
    calculate_portfolio_impact,
    _calculate_new_value,
)


# ============================================================
# LEARNED INVESTMENT MODEL
# ============================================================
# Instead of using static config-driven costs, learn from actual
# playbook executions and their measured outcomes.
#
# Fallback chain:
#   1. ActionEconomics actuals (real cost data from executed playbooks)
#   2. PlaybookExecution count × per-metric benchmark cost (real count, benchmark cost)
#   3. power_of_1_economics.json per-metric investment (static fallback)

@dataclass
class LearnedInvestment:
    """Empirical investment data learned from historical actuals."""
    total_investment: float
    cs_initiative_cost: float
    platform_cost: float
    per_metric: Dict[str, Dict]  # metric_id → {cost, improvement_pct, cost_per_point, playbook_runs}
    source: str  # 'action_economics', 'playbook_executions', 'benchmark_fallback'
    playbook_runs: int
    observation_months: int


def learn_investment_from_actuals(
    customer_id: int,
    account_ids: List[int],
    months: int = 6,
) -> LearnedInvestment:
    """
    Learn the investment model from actual execution history.

    Queries ActionEconomics and PlaybookExecution tables to build an
    empirical cost-per-improvement-point model per metric.

    Falls back to Power of 1 economics benchmarks only when no history exists.
    """
    from extensions import db
    from models import ActionEconomics, PlaybookExecution
    from datetime import datetime, timedelta

    cutoff = datetime.utcnow() - timedelta(days=months * 30)

    # ── Path 1: ActionEconomics (best — has real cost + real KPI deltas) ──
    action_records = ActionEconomics.query.filter(
        ActionEconomics.customer_id == customer_id,
        ActionEconomics.account_id.in_(account_ids),
        ActionEconomics.measured_at >= cutoff,
    ).all()

    if action_records and len(action_records) >= 2:
        return _build_learned_from_action_economics(action_records, months)

    # ── Path 2: PlaybookExecution count × benchmark cost ──
    executions = PlaybookExecution.query.filter(
        PlaybookExecution.customer_id == customer_id,
        PlaybookExecution.status == 'completed',
        PlaybookExecution.started_at >= cutoff,
    ).all()

    if executions:
        return _build_learned_from_playbook_executions(executions, months)

    # ── Path 3: Static fallback — Power of 1 economics benchmarks ──
    return _build_benchmark_fallback(months)


def _build_learned_from_action_economics(
    records: list,
    months: int,
) -> LearnedInvestment:
    """Build learned investment from ActionEconomics records (actual costs + deltas)."""
    per_metric = {}
    total_cost = 0
    total_cs = 0
    total_plat = 0
    total_runs = 0

    # Group by Power of 1 metric
    from collections import defaultdict
    metric_groups = defaultdict(list)
    for rec in records:
        metric_id = rec.power_of_1_metric
        if metric_id:
            metric_groups[metric_id].append(rec)

    for metric_id, recs in metric_groups.items():
        metric_cost = sum(float(r.total_action_cost or 0) for r in recs)
        metric_cs = sum(float(r.cs_initiative_cost or 0) for r in recs)
        metric_plat = sum(float(r.platform_cost or 0) for r in recs)
        metric_improvement = sum(float(r.improvement_pct or 0) for r in recs)
        runs = len(recs)

        cost_per_point = (metric_cost / metric_improvement) if metric_improvement > 0 else 0

        per_metric[metric_id] = {
            'cost': round(metric_cost, 2),
            'cs_cost': round(metric_cs, 2),
            'platform_cost': round(metric_plat, 2),
            'improvement_pct': round(metric_improvement, 2),
            'cost_per_point': round(cost_per_point, 2),
            'playbook_runs': runs,
        }

        total_cost += metric_cost
        total_cs += metric_cs
        total_plat += metric_plat
        total_runs += runs

    return LearnedInvestment(
        total_investment=round(total_cost, 2),
        cs_initiative_cost=round(total_cs, 2),
        platform_cost=round(total_plat, 2),
        per_metric=per_metric,
        source='action_economics',
        playbook_runs=total_runs,
        observation_months=months,
    )


def _build_learned_from_playbook_executions(
    executions: list,
    months: int,
) -> LearnedInvestment:
    """Build learned investment from PlaybookExecution count × per-metric benchmark cost."""
    from collections import Counter

    # Map playbook_id → primary Power of 1 metric
    PB_METRIC_MAP = {
        'PB-01': 'TTFV',
        'PB-02': 'ticket_resolution_time',
        'PB-03': 'product_adoption',
        'PB-04': 'expansion_rate',
        'PB-05': 'GRR',
        'PB-06': 'NRR',
        # Generic names
        'activation-blitz': 'TTFV',
        'sla-stabilizer': 'ticket_resolution_time',
        'renewal-safeguard': 'GRR',
        'expansion-accelerator': 'expansion_rate',
        'voc-sprint': 'NRR',
    }

    # Count executions per metric
    metric_runs = Counter()
    total_runs = 0
    for ex in executions:
        metric_id = PB_METRIC_MAP.get(ex.playbook_id)
        if metric_id:
            metric_runs[metric_id] += 1
            total_runs += 1

    # Cost per run = per-metric benchmark investment / expected runs per period
    # (benchmark assumes ~1 full deployment = all work packages for 1% improvement)
    per_metric = {}
    total_cost = 0
    total_cs = 0
    total_plat = 0

    for metric_id, runs in metric_runs.items():
        metric = POWER_OF_1_METRICS.get(metric_id)
        if not metric:
            continue

        # Each playbook run ≈ fraction of the full 1% work package
        # Benchmark: full work package = metric.total_investment for 1% improvement
        # Typical deployment has ~4 work packages, each run covers ~1 work package
        num_work_packages = len(metric.work_packages) or 1
        cost_per_run = metric.total_investment / num_work_packages
        metric_cost = cost_per_run * runs

        cs_ratio = metric.cs_initiative_cost / metric.total_investment if metric.total_investment > 0 else 0.8
        plat_ratio = 1 - cs_ratio

        per_metric[metric_id] = {
            'cost': round(metric_cost, 2),
            'cs_cost': round(metric_cost * cs_ratio, 2),
            'platform_cost': round(metric_cost * plat_ratio, 2),
            'improvement_pct': 0,  # Unknown — will be learned from health trends
            'cost_per_point': 0,
            'playbook_runs': runs,
        }

        total_cost += metric_cost
        total_cs += metric_cost * cs_ratio
        total_plat += metric_cost * plat_ratio

    return LearnedInvestment(
        total_investment=round(total_cost, 2),
        cs_initiative_cost=round(total_cs, 2),
        platform_cost=round(total_plat, 2),
        per_metric=per_metric,
        source='playbook_executions',
        playbook_runs=total_runs,
        observation_months=months,
    )


def _build_benchmark_fallback(months: int) -> LearnedInvestment:
    """Static fallback: use Power of 1 economics.json benchmarks, prorated by period."""
    per_metric = {}
    total_cost = 0
    total_cs = 0
    total_plat = 0

    # Prorate annual benchmarks to the observation period
    period_fraction = months / 12.0

    for metric_id, metric in POWER_OF_1_METRICS.items():
        metric_cost = metric.total_investment * period_fraction
        per_metric[metric_id] = {
            'cost': round(metric_cost, 2),
            'cs_cost': round(metric.cs_initiative_cost * period_fraction, 2),
            'platform_cost': round(metric.platform_cost * period_fraction, 2),
            'improvement_pct': 0,
            'cost_per_point': round(metric.total_investment, 2),  # Full cost per 1% at annual rate
            'playbook_runs': 0,
        }
        total_cost += metric_cost
        total_cs += metric.cs_initiative_cost * period_fraction
        total_plat += metric.platform_cost * period_fraction

    return LearnedInvestment(
        total_investment=round(total_cost, 2),
        cs_initiative_cost=round(total_cs, 2),
        platform_cost=round(total_plat, 2),
        per_metric=per_metric,
        source='benchmark_fallback',
        playbook_runs=0,
        observation_months=months,
    )


def extrapolate_forward_investment(
    learned: LearnedInvestment,
    per_metric_pcts: Dict[str, float],
    projection_months: int = 6,
) -> Dict:
    """
    Extrapolate forward investment from learned empirical model.

    Uses the learned cost-per-improvement-point to estimate what
    the projected improvement will cost. If cost_per_point is unknown,
    falls back to economics.json benchmark for that metric.

    Returns:
        Dict with total_investment, cs_cost, platform_cost, per_metric breakdown, source
    """
    per_metric = {}
    total_cost = 0
    total_cs = 0
    total_plat = 0

    for metric_id, projected_pct in per_metric_pcts.items():
        if projected_pct <= 0:
            continue

        metric = POWER_OF_1_METRICS.get(metric_id)
        if not metric:
            continue

        learned_data = learned.per_metric.get(metric_id, {})
        cost_per_point = learned_data.get('cost_per_point', 0)

        if cost_per_point > 0 and learned.source != 'benchmark_fallback':
            # Empirical: use the learned cost curve
            metric_cost = cost_per_point * projected_pct
            source = 'learned'
        else:
            # Fallback: use economics.json benchmark, prorated
            # At 1%, cost = total_investment. Scale sub-linearly for higher %
            # (diminishing marginal cost — first % is most expensive)
            cost_scale = max(1.0, 1.0 + 0.5 * (projected_pct - 1.0))
            metric_cost = metric.total_investment * cost_scale * (projection_months / 12.0)
            source = 'benchmark'

        cs_ratio = metric.cs_initiative_cost / metric.total_investment if metric.total_investment > 0 else 0.8
        plat_ratio = 1 - cs_ratio

        per_metric[metric_id] = {
            'cost': round(metric_cost, 2),
            'cs_cost': round(metric_cost * cs_ratio, 2),
            'platform_cost': round(metric_cost * plat_ratio, 2),
            'projected_pct': round(projected_pct, 2),
            'cost_per_point': round(cost_per_point, 2),
            'source': source,
        }

        total_cost += metric_cost
        total_cs += metric_cost * cs_ratio
        total_plat += metric_cost * plat_ratio

    return {
        'total_investment': round(total_cost, 2),
        'cs_initiative_cost': round(total_cs, 2),
        'platform_cost': round(total_plat, 2),
        'per_metric': per_metric,
        'learned_source': learned.source,
        'playbook_runs_observed': learned.playbook_runs,
    }


# ============================================================
# DATA CLASSES
# ============================================================

class OutcomeCategory(Enum):
    REVENUE_PROTECTED = "revenue_protected"
    REVENUE_EXPANDED = "revenue_expanded"
    COST_REDUCED = "cost_reduced"
    TIME_SAVED = "time_saved"


@dataclass
class MetricOutcome:
    """Outcome for a single Power of 1 metric."""
    metric_id: str
    display_name: str
    baseline_value: float
    current_value: float
    improvement_pct: float
    unit: str
    direction: str
    dollar_impact: float
    revenue_portion: float
    savings_portion: float
    category: str
    linked_kpis: List[str]
    linked_playbooks: List[str]
    data_source: str = "benchmark"


@dataclass
class ROISummary:
    """Aggregated ROI summary — the headline numbers."""
    total_investment: float
    total_impact: float
    revenue_protected: float
    revenue_expanded: float
    cost_savings: float
    compounding_effect: float
    roi_pct: float
    payback_months: float
    improvement_pct_avg: float


@dataclass
class OutcomeROIResult:
    """Complete outcome-focused ROI result."""
    view_type: str  # "historical" or "forward"
    period_label: str
    period_start: str
    period_end: str
    summary: ROISummary
    metric_outcomes: List[MetricOutcome]
    investment_breakdown: Dict
    top_outcomes: List[Dict]  # Top 3 ranked by $ impact
    # Auditor-defensibility disclosure. Populated when the historical window
    # surfaces non-repeatable, one-time gains (e.g. fresh-tenant decline→recovery
    # trajectories). Structured so the frontend can render a prominent tile-level
    # caveat without re-parsing free-text narratives.
    #
    # Shape when populated:
    #   {
    #       "non_repeatable": bool,        # true when one-time gains dominate
    #       "period_basis": str,           # "since_onboarding" | "trailing_window" | "stable_window"
    #       "headline": str,               # short auditor-facing label
    #       "detail": str,                 # full disclosure paragraph
    #       "recommended_label": str,      # what the tile/narrative should display
    #   }
    disclosure: Optional[Dict] = None


# ============================================================
# HISTORICAL ROI — "We proved it works"
# ============================================================

def calculate_historical_roi(
    metric_actuals: Dict[str, Dict],
    account_arr: Optional[float] = None,
    investment_override: Optional[float] = None,
    period_label: str = "Last 6 Months",
    period_start: Optional[str] = None,
    period_end: Optional[str] = None,
    vertical: Optional[str] = None,
    learned_investment: Optional[LearnedInvestment] = None,
    data_source: str = "benchmark",
    period_basis: str = "trailing_window",
    forward_steady_state_pct: Optional[float] = None,
) -> OutcomeROIResult:
    """
    Calculate realized ROI from actual metric movements.

    Investment is determined from the learned model (empirical actuals from
    ActionEconomics/PlaybookExecution), falling back to Power of 1 benchmarks.

    Args:
        metric_actuals: Dict of metric_id → {"baseline": float, "current": float}
        account_arr: Total ARR for scaling
        investment_override: Override the learned/default investment
        period_label: Display label for the period
        learned_investment: Empirical investment data from learn_investment_from_actuals()
        period_basis: How the baseline anchor was selected. One of
            'trailing_window' (default; baseline = earliest measurement in the
            requested N-month window, can drift on fresh tenants),
            'since_onboarding' (baseline = first available measurement, with
            explicit disclosure that gains include one-time onboarding lift), or
            'stable_window' (baseline = earliest measurement after skipping the
            early unstable phase — Option A path).
        forward_steady_state_pct: The steady-state forward improvement-pct used
            in the companion forward projection. Used purely to decide whether
            the historical view is reporting non-repeatable, one-time gains
            (heuristic: avg historical improvement > 2× forward steady-state).
    """
    arr_scale = 1.0
    if account_arr is not None:
        arr_scale = account_arr / 10_000_000

    now = datetime.now()

    metric_outcomes = []
    total_revenue_protected = 0
    total_revenue_expanded = 0
    total_cost_savings = 0
    total_direct_impact = 0
    improvement_pcts = []

    for metric_id, metric in POWER_OF_1_METRICS.items():
        actuals = metric_actuals.get(metric_id, {})
        baseline = actuals.get("baseline", metric.baseline)
        current = actuals.get("current", metric.baseline)

        # Calculate improvement percentage
        if metric.direction == "lower_is_better":
            absolute_improvement = baseline - current
        else:
            absolute_improvement = current - baseline

        improvement_pct = (absolute_improvement / metric.one_pct_move) if metric.one_pct_move else 0
        improvement_pct = max(0, improvement_pct)  # Only count positive improvements
        improvement_pcts.append(improvement_pct)

        # Dollar impact via Power of 1
        direct_impact = metric.annual_impact_per_pct * improvement_pct * arr_scale

        # Split into revenue vs savings
        rev_ratio = metric.impact_breakdown.get(
            ImpactType.REVENUE_INCREASE, 0
        ) / metric.annual_impact_per_pct if metric.annual_impact_per_pct else 0
        sav_ratio = 1 - rev_ratio

        revenue_portion = direct_impact * rev_ratio
        savings_portion = direct_impact * sav_ratio

        # Classify as protected vs expanded revenue
        if metric.metric_id in ("GRR", "ticket_resolution_time"):
            total_revenue_protected += revenue_portion
        else:
            total_revenue_expanded += revenue_portion
        total_cost_savings += savings_portion
        total_direct_impact += direct_impact

        metric_outcomes.append(MetricOutcome(
            metric_id=metric_id,
            display_name=metric.display_name,
            baseline_value=baseline,
            current_value=current,
            improvement_pct=round(improvement_pct, 2),
            unit=metric.unit,
            direction=metric.direction,
            dollar_impact=round(direct_impact, 2),
            revenue_portion=round(revenue_portion, 2),
            savings_portion=round(savings_portion, 2),
            category=metric.category.value,
            linked_kpis=metric.linked_kpi_codes,
            linked_playbooks=metric.get_playbooks(vertical),
            data_source=data_source,
        ))

    # ── Investment: use learned model or fallback ──
    if investment_override:
        investment = investment_override
        cs_pct = 0.80
        plat_pct = 0.20
    elif learned_investment and learned_investment.source != 'benchmark_fallback':
        # Use empirical data directly — no ARR scaling on investment
        # (work packages cost what they cost, regardless of customer ARR)
        investment = learned_investment.total_investment
        total_inv = learned_investment.cs_initiative_cost + learned_investment.platform_cost
        cs_pct = learned_investment.cs_initiative_cost / total_inv if total_inv > 0 else 0.80
        plat_pct = 1 - cs_pct
    else:
        # Benchmark fallback: prorate by observed improvement per metric
        investment = 0
        total_cs = 0
        total_plat = 0
        for i, (metric_id, metric) in enumerate(POWER_OF_1_METRICS.items()):
            imp = improvement_pcts[i]
            if imp > 0:
                # Cost scales with improvement: 1%→1x, 2%→1.5x, 4%→2.5x
                cost_scale = max(1.0, 1.0 + 0.5 * (imp - 1.0))
                # Prorate to observation period (6mo = half of annual benchmark)
                period_fraction = (learned_investment.observation_months / 12.0) if learned_investment else 0.5
                metric_cost = metric.total_investment * cost_scale * period_fraction
                investment += metric_cost
                total_cs += metric.cs_initiative_cost * cost_scale * period_fraction
                total_plat += metric.platform_cost * cost_scale * period_fraction
        cs_pct = total_cs / (total_cs + total_plat) if (total_cs + total_plat) > 0 else 0.80
        plat_pct = 1 - cs_pct

    # Compounding
    compounding = total_direct_impact * COMPOUNDING_MULTIPLIER
    total_impact = total_direct_impact + compounding

    # ROI
    roi_pct = ((total_impact - investment) / investment * 100) if investment > 0 else 0
    payback_months = (investment / (total_impact / 12)) if total_impact > 0 else float('inf')
    avg_improvement = sum(improvement_pcts) / len(improvement_pcts) if improvement_pcts else 0

    # Sort by dollar impact for top outcomes
    sorted_outcomes = sorted(metric_outcomes, key=lambda m: m.dollar_impact, reverse=True)
    top_outcomes = [
        {
            "metric_id": m.metric_id,
            "display_name": m.display_name,
            "dollar_impact": m.dollar_impact,
            "improvement_pct": m.improvement_pct,
            "headline": _make_outcome_headline(m, "historical"),
        }
        for m in sorted_outcomes[:3]
    ]

    summary = ROISummary(
        total_investment=round(investment, 2),
        total_impact=round(total_impact, 2),
        revenue_protected=round(total_revenue_protected, 2),
        revenue_expanded=round(total_revenue_expanded, 2),
        cost_savings=round(total_cost_savings, 2),
        compounding_effect=round(compounding, 2),
        roi_pct=round(roi_pct, 1),
        payback_months=round(payback_months, 1),
        improvement_pct_avg=round(avg_improvement, 2),
    )

    # ── Auditor-defensibility disclosure ──
    # Detect when the historical window is reporting one-time gains that won't
    # repeat (typical on freshly-onboarded tenants whose 18-month synthetic
    # trajectory carries a decline → recovery arc, anchored at the low point).
    # The CFO/auditor litmus test is: "Would I report this number to my board?"
    # If the improvement is wildly above steady-state forward, it's a one-time
    # turnaround — say so explicitly.
    disclosure, effective_period_label = _build_historical_disclosure(
        period_label=period_label,
        period_basis=period_basis,
        roi_pct=roi_pct,
        improvement_pct_avg=avg_improvement,
        forward_steady_state_pct=forward_steady_state_pct,
        data_source=data_source,
    )

    return OutcomeROIResult(
        view_type="historical",
        period_label=effective_period_label,
        period_start=period_start or (now - timedelta(days=180)).strftime("%Y-%m-%d"),
        period_end=period_end or now.strftime("%Y-%m-%d"),
        summary=summary,
        metric_outcomes=metric_outcomes,
        investment_breakdown={
            "total": round(investment, 2),
            "cs_initiatives": round(investment * cs_pct, 2),
            "platform": round(investment * plat_pct, 2),
        },
        top_outcomes=top_outcomes,
        disclosure=disclosure,
    )


def _build_historical_disclosure(
    period_label: str,
    period_basis: str,
    roi_pct: float,
    improvement_pct_avg: float,
    forward_steady_state_pct: Optional[float],
    data_source: str,
) -> tuple:
    """
    Compute the auditor-facing disclosure for a historical ROI result.

    Returns (disclosure_dict, effective_period_label). The disclosure dict is
    None when the historical view is repeat-able (i.e. the gains are
    incremental, the window is stable). When populated it carries:

      * non_repeatable: True if the historical gain is dominated by one-time
        turnaround moves (fresh tenant onboarding lift, decline→recovery arc).
      * period_basis: provenance of the baseline anchor.
      * headline: short auditor-facing label.
      * detail: full paragraph (safe to surface verbatim on a CFO tile).
      * recommended_label: what the tile should display in place of the raw
        "Last 6 Months" framing.

    Heuristic for non_repeatable:
      * ROI > 500% (well above steady-state CS ROI, which sits in 200–500%
        range per Bain/TSIA benchmarks), AND
      * avg historical improvement > 2× forward steady-state (or > 2.0pp
        absolute when no forward signal is supplied — steady-state Power of 1
        target is 1pp/period).
    """
    # Steady-state threshold for "improvement that could repeat next period"
    if forward_steady_state_pct is not None and forward_steady_state_pct > 0:
        steady_state_threshold = max(2.0, forward_steady_state_pct * 2.0)
    else:
        steady_state_threshold = 2.0

    non_repeatable = (
        roi_pct > 500.0
        and improvement_pct_avg > steady_state_threshold
    )

    # If neither condition fires AND the caller didn't ask for a specific
    # basis other than 'trailing_window', no disclosure is needed — the
    # number is defensible as-is.
    if not non_repeatable and period_basis == "trailing_window":
        return None, period_label

    if non_repeatable:
        basis = "since_onboarding"
        recommended_label = f"{period_label} (since onboarding — includes one-time gains)"
        headline = "Includes one-time onboarding gains"
        detail = (
            f"This historical ROI ({roi_pct:.0f}%) reflects the full improvement "
            f"trajectory since the portfolio was onboarded — average lift of "
            f"{improvement_pct_avg:.1f}% per KPI, which materially exceeds "
            f"steady-state Power-of-1 improvement (~{forward_steady_state_pct or 1.0:.1f}% per period). "
            "These gains are now captured in the current baseline and will not "
            "repeat at the same magnitude. Forward projections assume incremental, "
            "steady-state improvement on the new, higher baseline and are the "
            "repeatable number to report. Where the buyer requires a strict "
            "trailing-window proof, regenerate with a stable-window baseline "
            "(skip the first 3 months of onboarding ramp)."
        )
    else:
        # Caller explicitly tagged a non-default basis. Surface it without
        # the non-repeatable warning.
        basis = period_basis
        recommended_label = period_label
        headline = (
            "Baseline anchored on stable window" if period_basis == "stable_window"
            else f"Baseline anchored on '{period_basis}'"
        )
        detail = (
            f"Historical baseline was anchored using '{period_basis}' rather than the "
            f"default trailing window. ROI ({roi_pct:.0f}%) reflects this anchor."
        )

    return {
        "non_repeatable": non_repeatable,
        "period_basis": basis,
        "headline": headline,
        "detail": detail,
        "recommended_label": recommended_label,
        "data_source": data_source,
    }, recommended_label


# ============================================================
# FORWARD ROI — "Here's what's next"
# ============================================================

def calculate_forward_roi(
    current_values: Dict[str, float],
    target_improvement_pct: float = 1.0,
    account_arr: Optional[float] = None,
    investment_override: Optional[float] = None,
    projection_months: int = 6,
    period_label: Optional[str] = None,
    vertical: Optional[str] = None,
    per_metric_pcts: Optional[Dict[str, float]] = None,
    learned_investment: Optional[LearnedInvestment] = None,
    data_source: str = "benchmark",
) -> OutcomeROIResult:
    """
    Project forward ROI from current metric values to target improvement.

    Investment is extrapolated from the learned empirical model when available.
    The learned cost-per-improvement-point from historical actuals is used to
    predict what the projected improvement will cost. Falls back to Power of 1
    benchmarks when no execution history exists.

    Args:
        current_values: Dict of metric_id → current value
        target_improvement_pct: Target % improvement (1-6%), used when per_metric_pcts is None
        account_arr: Total ARR for scaling IMPACT (not investment)
        investment_override: Override learned/default investment
        projection_months: How far forward to project
        per_metric_pcts: Per-metric improvement rates from velocity model
        learned_investment: Empirical investment data from learn_investment_from_actuals()
    """
    arr_scale = 1.0
    if account_arr is not None:
        arr_scale = account_arr / 10_000_000

    now = datetime.now()

    metric_outcomes = []
    total_revenue_protected = 0
    total_revenue_expanded = 0
    total_cost_savings = 0
    total_direct_impact = 0
    improvement_pcts_map = {}  # metric_id → improvement_pct

    for metric_id, metric in POWER_OF_1_METRICS.items():
        current = current_values.get(metric_id, metric.baseline)

        # Use per-metric rate if available, otherwise fall back to flat rate
        metric_improvement = (per_metric_pcts or {}).get(metric_id, target_improvement_pct or 4.0)

        # Project ADDITIONAL improvement from current value
        additional_move = metric.one_pct_move * metric_improvement
        if metric.direction == "lower_is_better":
            projected_value = current - additional_move
        else:
            projected_value = current + additional_move
        projected_value = round(projected_value, 2)

        improvement_pcts_map[metric_id] = metric_improvement

        # Dollar impact — annualized, then scaled to projection period
        # Impact DOES scale with ARR (bigger customer = bigger dollar outcome)
        annual_impact = metric.annual_impact_per_pct * metric_improvement * arr_scale
        period_impact = annual_impact * (projection_months / 12.0)

        # Split
        rev_ratio = metric.impact_breakdown.get(
            ImpactType.REVENUE_INCREASE, 0
        ) / metric.annual_impact_per_pct if metric.annual_impact_per_pct else 0
        sav_ratio = 1 - rev_ratio

        revenue_portion = period_impact * rev_ratio
        savings_portion = period_impact * sav_ratio

        if metric.metric_id in ("GRR", "ticket_resolution_time"):
            total_revenue_protected += revenue_portion
        else:
            total_revenue_expanded += revenue_portion
        total_cost_savings += savings_portion
        total_direct_impact += period_impact

        metric_outcomes.append(MetricOutcome(
            metric_id=metric_id,
            display_name=metric.display_name,
            baseline_value=current,
            current_value=projected_value,
            improvement_pct=round(metric_improvement, 2),
            unit=metric.unit,
            direction=metric.direction,
            dollar_impact=round(period_impact, 2),
            revenue_portion=round(revenue_portion, 2),
            savings_portion=round(savings_portion, 2),
            category=metric.category.value,
            linked_kpis=metric.linked_kpi_codes,
            linked_playbooks=metric.get_playbooks(vertical),
            data_source=data_source,
        ))

    # ── Investment: extrapolate from learned model ──
    # Investment does NOT scale with ARR — work packages cost what they cost
    if investment_override:
        investment = investment_override
        cs_pct = 0.80
        plat_pct = 0.20
    elif learned_investment:
        fwd_inv = extrapolate_forward_investment(
            learned=learned_investment,
            per_metric_pcts=improvement_pcts_map,
            projection_months=projection_months,
        )
        investment = fwd_inv['total_investment']
        total_cs = fwd_inv['cs_initiative_cost']
        total_plat = fwd_inv['platform_cost']
        cs_pct = total_cs / (total_cs + total_plat) if (total_cs + total_plat) > 0 else 0.80
        plat_pct = 1 - cs_pct
    else:
        # No learned data, no override → benchmark fallback per metric
        # Benchmarks are calibrated for $10M ARR base. Scale investment
        # proportionally for different ARR sizes (sub-linear: sqrt scaling)
        # so smaller accounts get proportionally less, not the same flat cost.
        investment = 0
        total_cs = 0
        total_plat = 0
        inv_arr_scale = 1.0
        if account_arr and account_arr > 0:
            # Sub-linear: sqrt(arr/10M) — $3.2M → 0.57x, $8.2M → 0.91x, $20M → 1.41x
            inv_arr_scale = (account_arr / 10_000_000) ** 0.5
        for metric_id, metric in POWER_OF_1_METRICS.items():
            imp = improvement_pcts_map.get(metric_id, 0)
            if imp > 0:
                cost_scale = max(1.0, 1.0 + 0.5 * (imp - 1.0))
                period_fraction = projection_months / 12.0
                investment += metric.total_investment * cost_scale * period_fraction * inv_arr_scale
                total_cs += metric.cs_initiative_cost * cost_scale * period_fraction * inv_arr_scale
                total_plat += metric.platform_cost * cost_scale * period_fraction * inv_arr_scale
        cs_pct = total_cs / (total_cs + total_plat) if (total_cs + total_plat) > 0 else 0.80
        plat_pct = 1 - cs_pct

    # ── ARR-proportional investment cap (1.5% max) ──
    # CS investment should be 1–2.5% of ARR per industry benchmarks.
    # Cap at 1.5% to show realistic ROI (not inflated costs).
    if account_arr and account_arr > 0:
        max_investment = account_arr * 0.015
        if investment > max_investment:
            investment = max_investment

    # Compounding
    compounding = total_direct_impact * COMPOUNDING_MULTIPLIER
    total_impact = total_direct_impact + compounding

    # ROI
    roi_pct = ((total_impact - investment) / investment * 100) if investment > 0 else 0
    payback_months = (investment / (total_impact / (projection_months))) if total_impact > 0 else float('inf')
    all_pcts = list(improvement_pcts_map.values())
    avg_improvement = sum(all_pcts) / len(all_pcts) if all_pcts else 0

    # Top outcomes
    sorted_outcomes = sorted(metric_outcomes, key=lambda m: m.dollar_impact, reverse=True)
    top_outcomes = [
        {
            "metric_id": m.metric_id,
            "display_name": m.display_name,
            "dollar_impact": m.dollar_impact,
            "improvement_pct": m.improvement_pct,
            "headline": _make_outcome_headline(m, "forward"),
        }
        for m in sorted_outcomes[:3]
    ]

    label = period_label or f"Next {projection_months} Months"
    summary = ROISummary(
        total_investment=round(investment, 2),
        total_impact=round(total_impact, 2),
        revenue_protected=round(total_revenue_protected, 2),
        revenue_expanded=round(total_revenue_expanded, 2),
        cost_savings=round(total_cost_savings, 2),
        compounding_effect=round(compounding, 2),
        roi_pct=round(roi_pct, 1),
        payback_months=round(payback_months, 1),
        improvement_pct_avg=round(avg_improvement, 2),
    )

    return OutcomeROIResult(
        view_type="forward",
        period_label=label,
        period_start=now.strftime("%Y-%m-%d"),
        period_end=(now + timedelta(days=projection_months * 30)).strftime("%Y-%m-%d"),
        summary=summary,
        metric_outcomes=metric_outcomes,
        investment_breakdown={
            "total": round(investment, 2),
            "cs_initiatives": round(investment * cs_pct, 2),
            "platform": round(investment * plat_pct, 2),
        },
        top_outcomes=top_outcomes,
    )


# ============================================================
# COMBINED STORY — "Proof + Projection"
# ============================================================

def calculate_outcome_story(
    metric_actuals: Dict[str, Dict],
    target_improvement_pct: float = 1.0,
    account_arr: Optional[float] = None,
    investment_override: Optional[float] = None,
    projection_months: int = 6,
    historical_period_label: str = "Last 6 Months",
    accounts_at_risk: Optional[Dict[str, List]] = None,
    customer_id: Optional[int] = None,
    account_ids: Optional[List[int]] = None,
    vertical: Optional[str] = None,
    per_metric_pcts: Optional[Dict[str, float]] = None,
    learned_investment: Optional[LearnedInvestment] = None,
    data_source: str = "benchmark",
    historical_period_basis: str = "trailing_window",
) -> Dict:
    """
    Build the complete outcome story: historical proof + forward projection.

    Returns both sides with a bridging narrative showing continuity.
    When context graph is enabled, includes graph-based causal evidence.

    The learned_investment parameter feeds the empirical cost model into both
    the historical and forward ROI calculations.
    """
    # Forward ROI first — we use its steady-state improvement to decide whether
    # the historical view is reporting non-repeatable, one-time gains.
    current_values = {}
    for metric_id, actuals in metric_actuals.items():
        current_values[metric_id] = actuals.get("current", POWER_OF_1_METRICS[metric_id].baseline)

    forward = calculate_forward_roi(
        current_values=current_values,
        target_improvement_pct=target_improvement_pct,
        account_arr=account_arr,
        investment_override=investment_override,
        projection_months=projection_months,
        vertical=vertical,
        per_metric_pcts=per_metric_pcts,
        learned_investment=learned_investment,
        data_source=data_source,
    )

    # Historical ROI — uses learned investment for actual cost, with auditor
    # disclosure when one-time gains dominate (heuristic anchored on forward
    # steady-state).
    historical = calculate_historical_roi(
        metric_actuals=metric_actuals,
        account_arr=account_arr,
        investment_override=investment_override,
        period_label=historical_period_label,
        vertical=vertical,
        learned_investment=learned_investment,
        data_source=data_source,
        period_basis=historical_period_basis,
        forward_steady_state_pct=forward.summary.improvement_pct_avg,
    )

    # Combined totals
    combined_impact = historical.summary.total_impact + forward.summary.total_impact
    combined_investment = historical.summary.total_investment + forward.summary.total_investment
    combined_roi = ((combined_impact - combined_investment) / combined_investment * 100) if combined_investment > 0 else 0

    # Build the bridge narrative
    bridge = _build_bridge_narrative(historical, forward)

    # ARR scaling for scenarios and roadmap
    arr_scale = 1.0
    arr_basis = "baseline_10m"
    arr_basis_value = 10_000_000
    if account_arr is not None:
        arr_scale = account_arr / 10_000_000
        arr_basis = "explicit"
        arr_basis_value = account_arr

    # Build roadmap from Power of 1 work packages — aligned to forward projection
    roadmap = _build_implementation_roadmap(
        target_improvement_pct=target_improvement_pct,
        projection_months=projection_months,
        forward_result=forward,
        accounts_at_risk=accounts_at_risk,
        arr_scale=arr_scale,
        vertical=vertical,
    )

    # Scale scenarios dynamically if ARR differs from $10M base
    from power_of_1_model import _scale_scenarios
    scaled_scenarios = _scale_scenarios(arr_scale) if arr_scale != 1.0 else SCALING_SCENARIOS

    result = {
        "arr_basis": arr_basis,
        "arr_basis_value": arr_basis_value,
        "arr_scale": round(arr_scale, 6),
        "historical": _result_to_dict(historical),
        "forward": _result_to_dict(forward),
        "combined": {
            "total_impact": round(combined_impact, 2),
            "total_investment": round(combined_investment, 2),
            "combined_roi_pct": round(combined_roi, 1),
            "revenue_protected": round(
                historical.summary.revenue_protected + forward.summary.revenue_protected, 2
            ),
            "revenue_expanded": round(
                historical.summary.revenue_expanded + forward.summary.revenue_expanded, 2
            ),
            "cost_savings": round(
                historical.summary.cost_savings + forward.summary.cost_savings, 2
            ),
        },
        "bridge": bridge,
        "scaling_scenarios": scaled_scenarios,
        "roadmap": roadmap,
    }

    # ── Expected value churn risk ──
    # CRM renewal probability gives a more accurate risk picture than
    # context graph outcomes alone: EV = ARR × (1 - renewal_probability)
    if account_arr and account_arr > 0:
        # Extract GRR from actuals if available — lower GRR = higher churn risk
        grr_val = metric_actuals.get('GRR', {}).get('current', 90.0)
        # Derive renewal probability from GRR (GRR 85% → ~65% renewal, GRR 95% → ~90% renewal)
        renewal_prob = min(0.95, max(0.30, (grr_val - 50) / 50.0))
        churn_prob = 1.0 - renewal_prob
        ev_risk = account_arr * churn_prob
        result['risk_analysis'] = {
            'account_arr': round(account_arr, 2),
            'renewal_probability': round(renewal_prob * 100, 1),
            'churn_probability': round(churn_prob * 100, 1),
            'expected_value_at_risk': round(ev_risk, 2),
            'context_graph_at_risk': result.get('combined', {}).get('revenue_protected', 0),
            'note': 'Expected value = ARR × churn_probability. More accurate than summing context graph outcomes alone.',
        }

    # ── KPI trend summary (shows trends even with no playbooks) ──
    kpi_trends = {}
    for metric_id, actuals in metric_actuals.items():
        baseline = actuals.get('baseline', actuals.get('start', None))
        current = actuals.get('current', None)
        if baseline is not None and current is not None:
            delta = current - baseline
            direction = 'improving' if delta > 0 else ('declining' if delta < 0 else 'flat')
            metric = POWER_OF_1_METRICS.get(metric_id)
            if metric and metric.direction == 'lower_is_better':
                direction = 'improving' if delta < 0 else ('declining' if delta > 0 else 'flat')
            kpi_trends[metric_id] = {
                'baseline': round(baseline, 2),
                'current': round(current, 2),
                'delta': round(delta, 2),
                'delta_pct': round((delta / baseline * 100) if baseline else 0, 1),
                'direction': direction,
            }
    if kpi_trends:
        result['kpi_trends'] = kpi_trends

    # Context graph enrichment (feature-toggle gated, graceful fallback)
    if customer_id and account_ids:
        try:
            graph_evidence = _build_graph_enrichment(customer_id, account_ids)
            if graph_evidence:
                result['context_graph'] = graph_evidence
        except Exception:
            pass  # Graph data is enrichment, not required

    return result


# ============================================================
# IMPLEMENTATION ROADMAP
# ============================================================

def _build_implementation_roadmap(
    target_improvement_pct: float,
    projection_months: int,
    forward_result: Optional[OutcomeROIResult] = None,
    accounts_at_risk: Optional[Dict[str, List]] = None,
    arr_scale: float = 1.0,
    vertical: Optional[str] = None,
) -> Dict:
    """
    Build the 'how to get there' roadmap from Power of 1 work packages.

    ALIGNED to forward projection:
    - Dollar impacts match forward panel exactly (period-scaled, not annual)
    - Investment matches forward projection's resource-model figure
    - ALL 6 metrics shown in summary (not filtered by quarter)
    - Quarters scoped to projection window (6mo → Q1+Q2)
    """
    # ── Determine active quarters based on projection window ──
    num_quarters = max(1, min(4, (projection_months + 2) // 3))  # 6mo→2, 9mo→3, 12mo→4
    all_quarter_names = ["Q1", "Q2", "Q3", "Q4"]
    active_quarter_names = all_quarter_names[:num_quarters]

    quarter_labels = {
        "Q1": {"label": "Foundation", "months": "Months 1-3", "focus": "Setup & quick wins"},
        "Q2": {"label": "Intelligence", "months": "Months 4-6", "focus": "Data-driven insights"},
        "Q3": {"label": "Excellence", "months": "Months 7-9", "focus": "Optimization & scaling"},
        "Q4": {"label": "Optimization", "months": "Months 10-12", "focus": "Sustained performance"},
    }

    # Hourly rates for cost estimation (work package detail only)
    ROLE_RATES = {"csm": 95, "cs_ops": 85, "product": 110, "platform": 120, "leadership": 150}

    # ── Build forward-aligned metric impact lookup ──
    # Use the EXACT dollar_impact from forward projection for each metric
    forward_impact_by_metric = {}
    if forward_result:
        for m in forward_result.metric_outcomes:
            forward_impact_by_metric[m.metric_id] = m.dollar_impact

    # ── Metric summary: ALL 6 metrics with period-scaled impacts ──
    metric_summary = []
    for metric_id, metric in POWER_OF_1_METRICS.items():
        # Dollar impact: use forward projection's exact figure if available,
        # otherwise compute period-scaled value ourselves (with ARR scaling)
        if metric_id in forward_impact_by_metric:
            estimated_impact = forward_impact_by_metric[metric_id]
        else:
            estimated_impact = round(
                metric.annual_impact_per_pct * target_improvement_pct * (projection_months / 12.0) * arr_scale, 0
            )

        # Dollar impact per 1% — scaled by ARR
        dollar_impact_per_pct = round(
            metric.annual_impact_per_pct * (projection_months / 12.0) * arr_scale, 0
        )

        # Which quarters does this metric's work fall in?
        metric_quarters = [q for q in metric.quarters if q in active_quarter_names]

        # Accounts needing attention for this metric (top 5 worst)
        metric_at_risk = []
        if accounts_at_risk and metric_id in accounts_at_risk:
            metric_at_risk = accounts_at_risk[metric_id][:5]  # Top 5 worst

        at_risk_revenue = sum(a.get('revenue', 0) for a in metric_at_risk)

        metric_summary.append({
            "metric_id": metric_id,
            "display_name": metric.display_name,
            "estimated_impact": round(estimated_impact, 0),
            "dollar_impact_per_pct": dollar_impact_per_pct,
            "target_improvement_pct": target_improvement_pct,
            "active_quarters": metric_quarters,
            "all_quarters": metric.quarters,
            "linked_kpis": metric.linked_kpi_codes,
            "linked_playbooks": metric.get_playbooks(vertical),
            "accounts_at_risk": metric_at_risk,
            "at_risk_revenue": round(at_risk_revenue, 0),
            "at_risk_count": len(accounts_at_risk.get(metric_id, [])) if accounts_at_risk else 0,
        })

    # ── Build quarterly work-package breakdown (only active quarters) ──
    quarters = []
    for q_name in active_quarter_names:
        q_info = quarter_labels[q_name]
        q_metrics = []
        q_total_hours = 0
        q_total_cost = 0

        for metric_id, metric in POWER_OF_1_METRICS.items():
            if q_name not in metric.quarters:
                continue

            # Use forward-aligned impact for this metric
            if metric_id in forward_impact_by_metric:
                est_impact = forward_impact_by_metric[metric_id]
            else:
                est_impact = round(
                    metric.annual_impact_per_pct * target_improvement_pct * (projection_months / 12.0) * arr_scale, 0
                )

            # Distribute impact across the metric's active quarters
            active_qs_for_metric = [q for q in metric.quarters if q in active_quarter_names]
            quarter_share = len(active_qs_for_metric)
            per_quarter_impact = round(est_impact / max(quarter_share, 1), 0)

            metric_wps = []
            for wp in metric.work_packages:
                wp_cost = sum(
                    getattr(wp.roles, role, 0) * rate
                    for role, rate in ROLE_RATES.items()
                )
                metric_wps.append({
                    "name": wp.name.replace("_", " ").title(),
                    "description": wp.description,
                    "hours": wp.hours,
                    "cost": round(wp_cost, 0),
                    "roles": {
                        "CSM": getattr(wp.roles, "csm", 0),
                        "CS Ops": getattr(wp.roles, "cs_ops", 0),
                        "Product": getattr(wp.roles, "product", 0),
                        "Platform": getattr(wp.roles, "platform", 0),
                        "Leadership": getattr(wp.roles, "leadership", 0),
                    },
                    "deliverables": wp.deliverables,
                })
                q_total_hours += wp.hours
                q_total_cost += wp_cost

            # Top 3 at-risk accounts for this metric in this quarter's view
            q_metric_at_risk = []
            if accounts_at_risk and metric_id in accounts_at_risk:
                q_metric_at_risk = accounts_at_risk[metric_id][:3]

            if metric_wps:
                q_metrics.append({
                    "metric_id": metric_id,
                    "display_name": metric.display_name,
                    "dollar_impact_per_pct": round(metric.annual_impact_per_pct * (projection_months / 12.0) * arr_scale, 0),
                    "target_improvement_pct": target_improvement_pct,
                    "estimated_impact": round(per_quarter_impact, 0),
                    "total_metric_impact": round(est_impact, 0),
                    "work_packages": metric_wps,
                    "accounts_at_risk": q_metric_at_risk,
                })

        quarters.append({
            "quarter": q_name,
            "label": q_info["label"],
            "months": q_info["months"],
            "focus": q_info["focus"],
            "metrics": q_metrics,
            "total_hours": round(q_total_hours, 0),
            "total_cost": round(q_total_cost, 0),
        })

    # ── Totals: use forward projection's investment (resource-model based) ──
    wp_total_hours = sum(q["total_hours"] for q in quarters)
    wp_total_cost = sum(q["total_cost"] for q in quarters)

    # Use forward projection's real investment if available (resource-model based);
    # fall back to summed work-package costs for the active quarters
    if forward_result:
        total_investment = forward_result.summary.total_investment
        total_impact = forward_result.summary.total_impact
        roi_pct = forward_result.summary.roi_pct
    else:
        total_investment = wp_total_cost
        total_impact = sum(m["estimated_impact"] for m in metric_summary)
        roi_pct = ((total_impact - total_investment) / total_investment * 100) if total_investment > 0 else 0

    return {
        "projection_months": projection_months,
        "target_improvement_pct": target_improvement_pct,
        "metric_summary": metric_summary,
        "quarters": quarters,
        "total_hours": round(wp_total_hours, 0),
        "total_cost": round(total_investment, 0),
        "total_projected_impact": round(total_impact, 0),
        "roi_pct": round(roi_pct, 1),
        "source_note": "** Based on CS GrowthPulse Power of 1 framework. Dollar impacts are period-scaled ({0}mo). Benchmarks: Gainsight Pulse 2024, TSIA Research, KeyBanc SaaS Metrics Survey, Bain & Co. NPS Economics.".format(projection_months),
    }


# ============================================================
# SERIALIZATION
# ============================================================

def _result_to_dict(result: OutcomeROIResult) -> Dict:
    """Serialize an OutcomeROIResult for API response."""
    payload = {
        "view_type": result.view_type,
        "period_label": result.period_label,
        "period_start": result.period_start,
        "period_end": result.period_end,
        "summary": {
            "total_investment": result.summary.total_investment,
            "total_impact": result.summary.total_impact,
            "revenue_protected": result.summary.revenue_protected,
            "revenue_expanded": result.summary.revenue_expanded,
            "cost_savings": result.summary.cost_savings,
            "compounding_effect": result.summary.compounding_effect,
            "roi_pct": result.summary.roi_pct,
            "payback_months": result.summary.payback_months,
            "improvement_pct_avg": result.summary.improvement_pct_avg,
        },
        "metric_outcomes": [
            {
                "metric_id": m.metric_id,
                "display_name": m.display_name,
                "baseline_value": m.baseline_value,
                "current_value": m.current_value,
                "improvement_pct": m.improvement_pct,
                "unit": m.unit,
                "direction": m.direction,
                "dollar_impact": m.dollar_impact,
                "revenue_portion": m.revenue_portion,
                "savings_portion": m.savings_portion,
                "category": m.category,
                "linked_kpis": m.linked_kpis,
                "linked_playbooks": m.linked_playbooks,
                "data_source": m.data_source,
            }
            for m in result.metric_outcomes
        ],
        "investment_breakdown": result.investment_breakdown,
        "top_outcomes": result.top_outcomes,
    }
    # Surface the auditor-facing disclosure as a top-level field so the
    # frontend tile can render it without parsing free-text narratives.
    if result.disclosure is not None:
        payload["disclosure"] = result.disclosure
    return payload


# ============================================================
# INTERNAL HELPERS
# ============================================================

def _format_metric_value_suffix(unit: str) -> str:
    """Return display suffix for non-$ metric units: percent→%, days→' days', hours→' hrs'."""
    if not unit:
        return ""
    u = unit.lower()
    if u == "percent":
        return "%"
    if u == "days":
        return " days"
    if u == "hours":
        return " hrs"
    return f" {unit}"


def _make_outcome_headline(metric: MetricOutcome, view_type: str) -> str:
    """Generate an outcome-focused headline for a metric."""
    if metric.dollar_impact <= 0:
        return f"{metric.display_name}: No change yet"

    verb = "Delivered" if view_type == "historical" else "Will deliver"
    dollar_str = _format_dollars(metric.dollar_impact)
    suffix = _format_metric_value_suffix(metric.unit)

    if metric.direction == "lower_is_better":
        direction_str = f"{metric.baseline_value:.0f}{suffix} → {metric.current_value:.0f}{suffix}"
    else:
        direction_str = f"{metric.baseline_value:.1f}{suffix} → {metric.current_value:.1f}{suffix}"

    return f"{verb} {dollar_str} ({direction_str})"


def _format_dollars(amount: float) -> str:
    """Format dollar amounts for display."""
    if abs(amount) >= 1_000_000:
        return f"${amount / 1_000_000:.1f}M"
    if abs(amount) >= 1_000:
        return f"${amount / 1_000:.0f}K"
    return f"${amount:.0f}"


def _build_bridge_narrative(
    historical: OutcomeROIResult,
    forward: OutcomeROIResult,
) -> Dict:
    """Build the narrative that bridges historical proof to forward projection."""
    # Find metrics that improved historically and have more room to grow
    momentum_metrics = []
    for h_metric in historical.metric_outcomes:
        f_metric = next(
            (f for f in forward.metric_outcomes if f.metric_id == h_metric.metric_id),
            None,
        )
        if h_metric.improvement_pct > 0 and f_metric and f_metric.dollar_impact > 0:
            momentum_metrics.append({
                "metric_id": h_metric.metric_id,
                "display_name": h_metric.display_name,
                "historical_improvement": h_metric.improvement_pct,
                "historical_dollars": h_metric.dollar_impact,
                "forward_improvement": f_metric.improvement_pct,
                "forward_dollars": f_metric.dollar_impact,
                "total_dollars": h_metric.dollar_impact + f_metric.dollar_impact,
            })

    # Sort by total dollar impact
    momentum_metrics.sort(key=lambda m: m["total_dollars"], reverse=True)

    bridge = {
        "momentum_metrics": momentum_metrics[:3],
        "historical_roi_pct": historical.summary.roi_pct,
        "forward_roi_pct": forward.summary.roi_pct,
        "trajectory": "accelerating" if forward.summary.roi_pct > historical.summary.roi_pct else "sustaining",
        "narrative": _generate_narrative(historical, forward),
    }
    # Hoist the historical disclosure to the bridge level so callers reading
    # only the bridge (e.g. Ask AI summaries, slide-deck pulls) see the caveat
    # without having to descend into historical.disclosure.
    if historical.disclosure is not None:
        bridge["historical_disclosure"] = historical.disclosure
        # When the historical view is non-repeatable, recommend forward ROI as
        # the headline number a CFO/board should quote.
        if historical.disclosure.get("non_repeatable"):
            bridge["recommended_headline_roi_pct"] = forward.summary.roi_pct
            bridge["recommended_headline_basis"] = "forward_steady_state"
    return bridge


def _build_graph_enrichment(
    customer_id: int,
    account_ids: List[int],
) -> Optional[Dict]:
    """
    Pull context graph evidence to enrich the outcome story.

    Returns None if context graph is disabled or no data exists.
    Gracefully degrades — never raises.
    """
    try:
        from feature_toggles import is_context_graph_enabled
        if not is_context_graph_enabled(customer_id):
            return None
    except ImportError:
        return None

    from utils.context_graph import get_revenue_at_risk
    from models import ContextNode, ContextEdge, Account
    from extensions import db

    # ── Aggregate revenue across all accounts ──
    total_rev = {'at_risk': 0, 'protected': 0, 'expansion': 0, 'lost': 0, 'net_impact': 0}
    accounts_with_graph = 0

    for aid in account_ids:
        try:
            rev = get_revenue_at_risk(aid)
            if rev.get('node_count', 0) > 0:
                accounts_with_graph += 1
                for k in ('at_risk', 'protected', 'expansion', 'lost', 'net_impact'):
                    total_rev[k] += rev.get(k, 0)
        except Exception:
            continue

    if accounts_with_graph == 0:
        return None

    # ── Count signals and edges across customer's accounts ──
    now = datetime.utcnow()
    signal_count = ContextNode.query.filter(
        ContextNode.account_id.in_(account_ids),
        ContextNode.node_type == 'SIGNAL',
        db.or_(
            ContextNode.expires_at.is_(None),
            ContextNode.expires_at > now,
        ),
    ).count()

    # Edge count: edges where either end belongs to these accounts
    account_node_ids = db.session.query(ContextNode.node_id).filter(
        ContextNode.account_id.in_(account_ids),
    ).subquery()

    edge_count = ContextEdge.query.filter(
        db.or_(
            ContextEdge.from_node_id.in_(account_node_ids),
            ContextEdge.to_node_id.in_(account_node_ids),
        ),
    ).count()

    # ── Top 5 OUTCOME nodes by revenue_impact ──
    outcome_nodes = ContextNode.query.filter(
        ContextNode.account_id.in_(account_ids),
        ContextNode.node_type == 'OUTCOME',
        ContextNode.revenue_impact.isnot(None),
        db.or_(
            ContextNode.expires_at.is_(None),
            ContextNode.expires_at > now,
        ),
    ).order_by(
        db.func.abs(ContextNode.revenue_impact).desc()
    ).limit(5).all()

    key_outcomes = []
    for n in outcome_nodes:
        account = Account.query.filter_by(account_id=n.account_id).first()
        key_outcomes.append({
            'title': n.title,
            'account_id': n.account_id,
            'account_name': account.account_name if account else str(n.account_id),
            'revenue_impact': float(n.revenue_impact) if n.revenue_impact else 0,
            'revenue_impact_type': n.revenue_impact_type or 'at_risk',
            'occurred_at': n.occurred_at.isoformat() if n.occurred_at else None,
        })

    # ── DECISION nodes (most recent 10) ──
    decision_nodes = ContextNode.query.filter(
        ContextNode.account_id.in_(account_ids),
        ContextNode.node_type == 'DECISION',
        db.or_(
            ContextNode.expires_at.is_(None),
            ContextNode.expires_at > now,
        ),
    ).order_by(ContextNode.occurred_at.desc()).limit(10).all()

    key_decisions = []
    for n in decision_nodes:
        account = Account.query.filter_by(account_id=n.account_id).first()
        key_decisions.append({
            'title': n.title,
            'account_id': n.account_id,
            'account_name': account.account_name if account else str(n.account_id),
            'revenue_impact': float(n.revenue_impact) if n.revenue_impact else 0,
            'occurred_at': n.occurred_at.isoformat() if n.occurred_at else None,
            'node_subtype': n.node_subtype,
        })

    return {
        'revenue_summary': {k: round(v, 2) for k, v in total_rev.items()},
        'graph_signal_count': signal_count,
        'graph_edge_count': edge_count,
        'key_outcomes': key_outcomes,
        'key_decisions': key_decisions,
        'accounts_with_graph': accounts_with_graph,
        'total_accounts': len(account_ids),
    }


def _generate_narrative(
    historical: OutcomeROIResult,
    forward: OutcomeROIResult,
) -> str:
    """Generate a human-readable narrative bridging historical and forward."""
    h = historical.summary
    f = forward.summary

    historical_dollar = _format_dollars(h.total_impact)
    forward_dollar = _format_dollars(f.total_impact)
    combined = _format_dollars(h.total_impact + f.total_impact)

    parts = [
        f"Over {historical.period_label.lower()}, your CS investment delivered "
        f"{historical_dollar} in realized outcomes ({h.roi_pct:.0f}% ROI).",
    ]

    if f.total_impact > 0:
        parts.append(
            f"Looking ahead over {forward.period_label.lower()}, the same investment "
            f"is projected to deliver {forward_dollar} ({f.roi_pct:.0f}% ROI)."
        )

    # Surface the auditor disclosure when one-time gains dominate. Prefer the
    # structured disclosure (single source of truth) over re-deriving the
    # heuristic in narrative form.
    if historical.disclosure and historical.disclosure.get("non_repeatable"):
        parts.append(historical.disclosure.get("detail", ""))
    elif h.roi_pct > 0 and f.roi_pct > 0 and h.roi_pct > f.roi_pct * 3:
        # Legacy fallback for paths that bypass the structured disclosure
        # (e.g. callers that build a historical view via the older entry point).
        parts.append(
            f"The historical ROI includes one-time turnaround gains from accounts "
            f"that moved from critical to healthy — these gains are now captured in "
            f"the baseline. Forward projections assume incremental {f.improvement_pct_avg:.0f}% "
            f"improvement on the new, higher baseline."
        )

    if h.total_impact > 0 and f.total_impact > 0:
        parts.append(
            f"Combined trajectory: {combined} in total outcome value."
        )

    return " ".join(parts)


# ============================================================
# HISTORICAL TIMELINE — "What happened and why"
# ============================================================

def build_historical_timeline(
    customer_id: int,
    account_ids: List[int],
    metric_actuals: Dict[str, Dict],
    months: int = 6,
) -> Optional[Dict]:
    """
    Build a month-by-month timeline correlating ROI metric movements
    with context graph signals, decisions, and outcomes.

    Returns None if context graph is disabled or no data exists.
    """
    try:
        from feature_toggles import is_context_graph_enabled
        if not is_context_graph_enabled(customer_id):
            return None
    except ImportError:
        return None

    from models import ContextNode, ContextEdge, Account, KPIScore
    from extensions import db
    from utils.context_graph import get_causal_chain
    from power_of_1_model import get_metric_for_kpi_code
    from dateutil.relativedelta import relativedelta

    now = datetime.utcnow()
    period_end = now.replace(day=1)  # First of current month
    period_start = period_end - relativedelta(months=months)

    # ── Build monthly bins ──
    timeline = []
    cumulative = {'protected': 0, 'expanded': 0, 'at_risk': 0, 'lost': 0}
    all_outcome_nodes = []

    for i in range(months):
        month_start = period_start + relativedelta(months=i)
        month_end = month_start + relativedelta(months=1)
        month_key = month_start.strftime('%Y-%m')
        month_label = month_start.strftime('%b %Y')

        # Query context nodes for this month
        month_nodes = ContextNode.query.filter(
            ContextNode.account_id.in_(account_ids),
            ContextNode.occurred_at >= month_start,
            ContextNode.occurred_at < month_end,
        ).all()

        # Group by node_type
        signals = []
        decisions = []
        outcomes = []
        stakeholder_count = 0
        month_rev = {'protected': 0, 'expanded': 0, 'at_risk': 0, 'lost': 0}

        for n in month_nodes:
            entry = {
                'node_id': n.node_id,
                'title': n.title,
                'subtype': n.node_subtype,
                'account_id': n.account_id,
                'revenue_impact': float(n.revenue_impact) if n.revenue_impact else 0,
                'revenue_impact_type': n.revenue_impact_type or 'at_risk',
                'occurred_at': n.occurred_at.isoformat() if n.occurred_at else None,
            }

            if n.node_type == 'SIGNAL':
                signals.append(entry)
            elif n.node_type == 'DECISION':
                decisions.append(entry)
            elif n.node_type == 'OUTCOME':
                outcomes.append(entry)
                all_outcome_nodes.append(n)
            elif n.node_type == 'STAKEHOLDER':
                stakeholder_count += 1

            # Accumulate revenue by type
            if n.revenue_impact:
                impact = float(n.revenue_impact) * float(n.confidence or 1.0)
                bucket = n.revenue_impact_type or 'at_risk'
                if bucket == 'expansion':
                    month_rev['expanded'] += impact
                elif bucket == 'protected':
                    month_rev['protected'] += impact
                elif bucket == 'lost':
                    month_rev['lost'] += impact
                else:
                    month_rev['at_risk'] += impact

        # Update cumulative
        for k in cumulative:
            cumulative[k] += month_rev[k]

        # Query KPI movements for this month
        month_date = month_start.date()
        kpi_movements = []
        kpi_scores = KPIScore.query.filter(
            KPIScore.account_id.in_(account_ids),
            KPIScore.measurement_month == month_date,
            KPIScore.kpi_score.isnot(None),
        ).all()

        # Group by kpi_code, compute average score across accounts
        kpi_map = {}
        for ks in kpi_scores:
            code = ks.kpi_code
            if code not in kpi_map:
                kpi_map[code] = {'scores': [], 'values': []}
            kpi_map[code]['scores'].append(float(ks.kpi_score))
            if ks.kpi_value is not None:
                kpi_map[code]['values'].append(float(ks.kpi_value))

        for code, data in kpi_map.items():
            avg_score = sum(data['scores']) / len(data['scores'])
            metric_name = get_metric_for_kpi_code(code)
            kpi_movements.append({
                'kpi_code': code,
                'metric': metric_name,
                'avg_score': round(avg_score, 1),
                'account_count': len(data['scores']),
            })

        # Sort signals by revenue impact (highest first)
        signals.sort(key=lambda s: abs(s['revenue_impact']), reverse=True)

        timeline.append({
            'month': month_key,
            'label': month_label,
            'signals': signals[:10],  # Top 10 per month
            'decisions': decisions,
            'outcomes': outcomes,
            'stakeholder_actions': stakeholder_count,
            'kpi_movements': kpi_movements[:8],  # Top 8
            'revenue_impact': {k: round(v, 2) for k, v in month_rev.items()},
            'cumulative_impact': {k: round(v, 2) for k, v in cumulative.items()},
            'signal_count': len(signals),
            'decision_count': len(decisions),
            'outcome_count': len(outcomes),
        })

    # ── Build causal highlights for top outcomes ──
    causal_highlights = []
    # Sort outcomes by revenue impact
    all_outcome_nodes.sort(
        key=lambda n: abs(float(n.revenue_impact or 0)),
        reverse=True,
    )

    for outcome_node in all_outcome_nodes[:5]:
        try:
            chain_raw = get_causal_chain(
                outcome_node.node_id,
                direction='upstream',
                max_depth=4,
            )
            chain_entries = []
            # Add upstream cause nodes
            for step in chain_raw:
                node_data = step['node']
                chain_entries.append({
                    'type': node_data.get('node_type', 'UNKNOWN'),
                    'title': node_data.get('title', ''),
                    'month': node_data.get('occurred_at', '')[:7] if node_data.get('occurred_at') else '',
                    'revenue_impact': node_data.get('revenue_impact', 0),
                })

            # Add the outcome itself at the end
            chain_entries.append({
                'type': 'OUTCOME',
                'title': outcome_node.title,
                'month': outcome_node.occurred_at.strftime('%Y-%m') if outcome_node.occurred_at else '',
                'revenue_impact': float(outcome_node.revenue_impact) if outcome_node.revenue_impact else 0,
            })

            # Reverse so it reads signal → decision → outcome (chronological)
            chain_entries.reverse()
            # Re-reverse: upstream chain was already in upstream order,
            # we want chronological: earliest first
            # Actually: chain_raw is in traversal order (upstream),
            # so reverse gives chronological
            # The outcome was appended last, so after reverse it's first — swap:
            # Let's sort by month instead
            chain_entries.sort(key=lambda e: e.get('month', ''))

            if chain_entries:
                causal_highlights.append({
                    'outcome': {
                        'title': outcome_node.title,
                        'revenue': float(outcome_node.revenue_impact) if outcome_node.revenue_impact else 0,
                        'type': outcome_node.revenue_impact_type or 'at_risk',
                        'account_id': outcome_node.account_id,
                    },
                    'chain': chain_entries,
                })
        except Exception:
            continue

    # ── Summary stats ──
    total_signals = sum(m['signal_count'] for m in timeline)
    total_decisions = sum(m['decision_count'] for m in timeline)
    total_outcomes = sum(m['outcome_count'] for m in timeline)

    # Find peak risk month
    peak_risk_month = ''
    peak_risk_amount = 0
    for m in timeline:
        risk = m['revenue_impact'].get('at_risk', 0)
        if risk > peak_risk_amount:
            peak_risk_amount = risk
            peak_risk_month = m['month']

    return {
        'period': {
            'start': period_start.strftime('%Y-%m-%d'),
            'end': period_end.strftime('%Y-%m-%d'),
            'months': months,
        },
        'timeline': timeline,
        'causal_highlights': causal_highlights,
        'summary': {
            'total_signals': total_signals,
            'total_decisions': total_decisions,
            'total_outcomes': total_outcomes,
            'total_revenue_protected': round(cumulative['protected'], 2),
            'total_revenue_expanded': round(cumulative['expanded'], 2),
            'total_revenue_at_risk': round(cumulative['at_risk'], 2),
            'total_revenue_lost': round(cumulative['lost'], 2),
            'peak_risk_month': peak_risk_month,
            'peak_risk_amount': round(peak_risk_amount, 2),
        },
    }
