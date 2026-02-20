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
) -> OutcomeROIResult:
    """
    Calculate realized ROI from actual metric movements.

    Args:
        metric_actuals: Dict of metric_id → {
            "baseline": float,   # Where it started
            "current": float,    # Where it is now
        }
        account_arr: Total ARR for scaling
        investment_override: Override the default $247K investment
        period_label: Display label for the period
        period_start: ISO date string for period start
        period_end: ISO date string for period end

    Returns:
        OutcomeROIResult with realized outcomes
    """
    arr_scale = 1.0
    if account_arr is not None:
        arr_scale = account_arr / 10_000_000

    investment = investment_override or INVESTMENT_SUMMARY["total_investment"]
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
            linked_playbooks=metric.linked_playbooks,
        ))

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
        total_investment=investment,
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
        view_type="historical",
        period_label=period_label,
        period_start=period_start or (now - timedelta(days=180)).strftime("%Y-%m-%d"),
        period_end=period_end or now.strftime("%Y-%m-%d"),
        summary=summary,
        metric_outcomes=metric_outcomes,
        investment_breakdown={
            "total": investment,
            "cs_initiatives": round(investment * 0.80, 2),
            "platform": round(investment * 0.20, 2),
        },
        top_outcomes=top_outcomes,
    )


# ============================================================
# FORWARD ROI — "Here's what's next"
# ============================================================

def calculate_forward_roi(
    current_values: Dict[str, float],
    target_improvement_pct: float = 4.0,
    account_arr: Optional[float] = None,
    investment_override: Optional[float] = None,
    projection_months: int = 6,
    period_label: Optional[str] = None,
) -> OutcomeROIResult:
    """
    Project forward ROI from current metric values to target improvement.

    Args:
        current_values: Dict of metric_id → current value
        target_improvement_pct: Target % improvement (1-6%)
        account_arr: Total ARR for scaling
        investment_override: Override default investment
        projection_months: How far forward to project
        period_label: Display label

    Returns:
        OutcomeROIResult with projected outcomes
    """
    arr_scale = 1.0
    if account_arr is not None:
        arr_scale = account_arr / 10_000_000

    investment = investment_override or INVESTMENT_SUMMARY["total_investment"]
    now = datetime.now()

    metric_outcomes = []
    total_revenue_protected = 0
    total_revenue_expanded = 0
    total_cost_savings = 0
    total_direct_impact = 0
    improvement_pcts = []

    for metric_id, metric in POWER_OF_1_METRICS.items():
        current = current_values.get(metric_id, metric.baseline)

        # Project ADDITIONAL improvement from current value
        # target_improvement_pct is the additional % to gain from here
        additional_move = metric.one_pct_move * target_improvement_pct
        if metric.direction == "lower_is_better":
            projected_value = current - additional_move
        else:
            projected_value = current + additional_move
        projected_value = round(projected_value, 2)

        # The improvement is exactly the target (from current, not baseline)
        improvement_pct = target_improvement_pct
        improvement_pcts.append(improvement_pct)

        # Dollar impact — annualized, then scaled to projection period
        annual_impact = metric.annual_impact_per_pct * improvement_pct * arr_scale
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
            improvement_pct=round(improvement_pct, 2),
            unit=metric.unit,
            direction=metric.direction,
            dollar_impact=round(period_impact, 2),
            revenue_portion=round(revenue_portion, 2),
            savings_portion=round(savings_portion, 2),
            category=metric.category.value,
            linked_kpis=metric.linked_kpi_codes,
            linked_playbooks=metric.linked_playbooks,
        ))

    # Compounding
    compounding = total_direct_impact * COMPOUNDING_MULTIPLIER
    total_impact = total_direct_impact + compounding

    # ROI
    roi_pct = ((total_impact - investment) / investment * 100) if investment > 0 else 0
    payback_months = (investment / (total_impact / (projection_months))) if total_impact > 0 else float('inf')
    avg_improvement = sum(improvement_pcts) / len(improvement_pcts) if improvement_pcts else 0

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
        total_investment=investment,
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
            "total": investment,
            "cs_initiatives": round(investment * 0.80, 2),
            "platform": round(investment * 0.20, 2),
        },
        top_outcomes=top_outcomes,
    )


# ============================================================
# COMBINED STORY — "Proof + Projection"
# ============================================================

def calculate_outcome_story(
    metric_actuals: Dict[str, Dict],
    target_improvement_pct: float = 4.0,
    account_arr: Optional[float] = None,
    investment_override: Optional[float] = None,
    projection_months: int = 6,
    historical_period_label: str = "Last 6 Months",
) -> Dict:
    """
    Build the complete outcome story: historical proof + forward projection.

    Returns both sides with a bridging narrative showing continuity.
    """
    # Historical ROI
    historical = calculate_historical_roi(
        metric_actuals=metric_actuals,
        account_arr=account_arr,
        investment_override=investment_override,
        period_label=historical_period_label,
    )

    # Extract current values from actuals for forward projection
    current_values = {}
    for metric_id, actuals in metric_actuals.items():
        current_values[metric_id] = actuals.get("current", POWER_OF_1_METRICS[metric_id].baseline)

    # Forward ROI
    forward = calculate_forward_roi(
        current_values=current_values,
        target_improvement_pct=target_improvement_pct,
        account_arr=account_arr,
        investment_override=investment_override,
        projection_months=projection_months,
    )

    # Combined totals
    combined_impact = historical.summary.total_impact + forward.summary.total_impact
    combined_investment = historical.summary.total_investment + forward.summary.total_investment
    combined_roi = ((combined_impact - combined_investment) / combined_investment * 100) if combined_investment > 0 else 0

    # Build the bridge narrative
    bridge = _build_bridge_narrative(historical, forward)

    return {
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
        "scaling_scenarios": SCALING_SCENARIOS,
    }


# ============================================================
# SERIALIZATION
# ============================================================

def _result_to_dict(result: OutcomeROIResult) -> Dict:
    """Serialize an OutcomeROIResult for API response."""
    return {
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
            }
            for m in result.metric_outcomes
        ],
        "investment_breakdown": result.investment_breakdown,
        "top_outcomes": result.top_outcomes,
    }


# ============================================================
# INTERNAL HELPERS
# ============================================================

def _make_outcome_headline(metric: MetricOutcome, view_type: str) -> str:
    """Generate an outcome-focused headline for a metric."""
    if metric.dollar_impact <= 0:
        return f"{metric.display_name}: No change yet"

    verb = "Delivered" if view_type == "historical" else "Will deliver"
    dollar_str = _format_dollars(metric.dollar_impact)

    if metric.direction == "lower_is_better":
        direction_str = f"{metric.baseline_value:.0f} → {metric.current_value:.0f} {metric.unit}"
    else:
        direction_str = f"{metric.baseline_value:.1f} → {metric.current_value:.1f}{metric.unit}"

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

    return {
        "momentum_metrics": momentum_metrics[:3],
        "historical_roi_pct": historical.summary.roi_pct,
        "forward_roi_pct": forward.summary.roi_pct,
        "trajectory": "accelerating" if forward.summary.roi_pct > historical.summary.roi_pct else "sustaining",
        "narrative": _generate_narrative(historical, forward),
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

    if h.total_impact > 0 and f.total_impact > 0:
        parts.append(
            f"Combined trajectory: {combined} in total outcome value."
        )

    return " ".join(parts)
