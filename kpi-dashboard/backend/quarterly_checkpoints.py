#!/usr/bin/env python3
"""
Step 4 — Quarterly Checkpoints Module
=======================================
Roadmap targets, milestone validation, and phase-gate logic for
the Power of 1 implementation plan.

Provides:
  - Quarterly target definitions (from Slide 22 of the deck)
  - Validation logic: is the customer on-track vs. off-track?
  - Gap analysis: which metrics are behind, by how much?
  - Phase-gate readiness checks: can we advance to the next quarter?
  - Milestone event logging for the execution timeline

Feature flag: 'revenue_intelligence' (per-customer toggle)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
from datetime import datetime, date

from power_of_1_model import (
    POWER_OF_1_METRICS,
    QUARTERLY_CHECKPOINTS as RAW_CHECKPOINTS,
    IMPLEMENTATION_PHASES,
    SCALING_SCENARIOS,
    calculate_power_of_1_impact,
)


# ============================================================
# ENUMS & DATA CLASSES
# ============================================================

class TrackStatus(Enum):
    ON_TRACK = "on_track"
    AT_RISK = "at_risk"
    OFF_TRACK = "off_track"
    AHEAD = "ahead"
    NOT_STARTED = "not_started"


class PhaseGateResult(Enum):
    PASS = "pass"
    CONDITIONAL_PASS = "conditional_pass"
    FAIL = "fail"


@dataclass
class MetricCheckpoint:
    """Target for a single metric in a single quarter."""
    metric_id: str
    target_value: float
    milestone: str
    weight: float = 1.0  # Relative importance in this quarter


@dataclass
class QuarterTarget:
    """Full target set for one quarter."""
    quarter: str
    label: str
    month_range: str
    metric_targets: Dict[str, MetricCheckpoint]
    platform_milestone: Optional[str] = None
    review_label: str = ""


@dataclass
class MetricAssessment:
    """Assessment of one metric vs. its quarterly target."""
    metric_id: str
    display_name: str
    target_value: float
    actual_value: Optional[float]
    gap: float
    gap_pct: float
    status: TrackStatus
    milestone: str
    dollar_impact_of_gap: float  # How much $ the gap represents


@dataclass
class QuarterAssessment:
    """Full assessment for one quarter."""
    quarter: str
    label: str
    metrics: List[MetricAssessment]
    overall_status: TrackStatus
    on_track_count: int
    at_risk_count: int
    off_track_count: int
    total_gap_dollars: float
    phase_gate: PhaseGateResult
    phase_gate_notes: str
    recommendations: List[str]


# ============================================================
# QUARTERLY TARGETS — FROM THE DECK
# ============================================================

QUARTER_TARGETS: Dict[str, QuarterTarget] = {
    "Q1": QuarterTarget(
        quarter="Q1",
        label="Foundation & Launch",
        month_range="Jan-Mar",
        metric_targets={
            "TTFV": MetricCheckpoint("TTFV", 30.0, "baseline", weight=2.0),
        },
        platform_milestone="go_live",
        review_label="Baseline established",
    ),
    "Q2": QuarterTarget(
        quarter="Q2",
        label="Intelligence & Early Wins",
        month_range="Apr-Jun",
        metric_targets={
            "TTFV": MetricCheckpoint("TTFV", 29.5, "optimizing", weight=1.5),
            "NRR": MetricCheckpoint("NRR", 105.5, "launched", weight=2.0),
            "ticket_resolution_time": MetricCheckpoint(
                "ticket_resolution_time", 47.5, "improved", weight=1.0
            ),
        },
        platform_milestone="dashboards_validated",
        review_label="First Review",
    ),
    "Q3": QuarterTarget(
        quarter="Q3",
        label="Scale & Expand",
        month_range="Jul-Sep",
        metric_targets={
            "TTFV": MetricCheckpoint("TTFV", 29.0, "refined", weight=1.0),
            "GRR": MetricCheckpoint("GRR", 85.5, "deployed", weight=2.0),
            "expansion_rate": MetricCheckpoint(
                "expansion_rate", 20.1, "pipeline_built", weight=1.5
            ),
        },
        platform_milestone="health_v2_live",
        review_label="Mid-Year Review",
    ),
    "Q4": QuarterTarget(
        quarter="Q4",
        label="Optimize & Validate ROI",
        month_range="Oct-Dec",
        metric_targets={
            "TTFV": MetricCheckpoint("TTFV", 29.0, "complete", weight=1.0),
            "NRR": MetricCheckpoint("NRR", 106.0, "optimized", weight=2.0),
            "GRR": MetricCheckpoint("GRR", 86.0, "optimized", weight=2.0),
            "product_adoption": MetricCheckpoint(
                "product_adoption", 65.65, "campaigns_complete", weight=1.0
            ),
            "expansion_rate": MetricCheckpoint(
                "expansion_rate", 20.2, "full_auto", weight=1.5
            ),
        },
        platform_milestone="full_optimization",
        review_label="Year-End Review",
    ),
}


# ============================================================
# THRESHOLD DEFINITIONS
# ============================================================

# How far from target before we flag risk / off-track
# Expressed as a fraction of the target improvement from baseline
ON_TRACK_THRESHOLD = 0.15    # Within 15% of target improvement
AT_RISK_THRESHOLD = 0.40     # Within 40% — lagging but recoverable
# Beyond 40% gap → off_track


# ============================================================
# VALIDATION FUNCTIONS
# ============================================================

def assess_metric(
    metric_id: str,
    target: MetricCheckpoint,
    actual_value: Optional[float],
    account_arr: Optional[float] = None,
) -> MetricAssessment:
    """
    Assess a single metric against its quarterly target.

    Args:
        metric_id: Power of 1 metric ID
        target: The quarterly target checkpoint
        actual_value: Current observed value (None if not yet measured)
        account_arr: For scaling dollar impact

    Returns:
        MetricAssessment with gap analysis and status
    """
    metric = POWER_OF_1_METRICS.get(metric_id)
    if not metric:
        return MetricAssessment(
            metric_id=metric_id,
            display_name=metric_id,
            target_value=target.target_value,
            actual_value=actual_value,
            gap=0, gap_pct=0,
            status=TrackStatus.NOT_STARTED,
            milestone=target.milestone,
            dollar_impact_of_gap=0,
        )

    if actual_value is None:
        return MetricAssessment(
            metric_id=metric_id,
            display_name=metric.display_name,
            target_value=target.target_value,
            actual_value=None,
            gap=0, gap_pct=0,
            status=TrackStatus.NOT_STARTED,
            milestone=target.milestone,
            dollar_impact_of_gap=0,
        )

    # Calculate gap — direction-aware
    if metric.direction == "lower_is_better":
        # For lower-is-better: being above target is bad
        gap = actual_value - target.target_value  # positive = behind
        improvement_from_baseline = metric.baseline - target.target_value
    else:
        # For higher-is-better: being below target is bad
        gap = target.target_value - actual_value  # positive = behind
        improvement_from_baseline = target.target_value - metric.baseline

    # Gap as percentage of the required improvement
    gap_pct = (gap / improvement_from_baseline) if improvement_from_baseline != 0 else 0

    # Determine status
    if gap <= 0:
        status = TrackStatus.AHEAD
    elif gap_pct <= ON_TRACK_THRESHOLD:
        status = TrackStatus.ON_TRACK
    elif gap_pct <= AT_RISK_THRESHOLD:
        status = TrackStatus.AT_RISK
    else:
        status = TrackStatus.OFF_TRACK

    # Dollar impact of the gap — how much $ are we leaving on the table?
    # Convert gap to % improvement units, then to dollars via Power of 1
    gap_in_pct_units = abs(gap) / metric.one_pct_move if metric.one_pct_move else 0
    dollar_impact = gap_in_pct_units * metric.annual_impact_per_pct
    if account_arr:
        dollar_impact *= (account_arr / 10_000_000)

    return MetricAssessment(
        metric_id=metric_id,
        display_name=metric.display_name,
        target_value=target.target_value,
        actual_value=actual_value,
        gap=round(gap, 2),
        gap_pct=round(gap_pct, 4),
        status=status,
        milestone=target.milestone,
        dollar_impact_of_gap=round(dollar_impact, 2),
    )


def assess_quarter(
    quarter: str,
    actual_values: Dict[str, float],
    account_arr: Optional[float] = None,
) -> QuarterAssessment:
    """
    Full assessment for a quarter against all its targets.

    Args:
        quarter: 'Q1', 'Q2', 'Q3', or 'Q4'
        actual_values: Dict of metric_id → current value
        account_arr: For scaling dollar impact

    Returns:
        QuarterAssessment with per-metric assessments and overall status
    """
    qt = QUARTER_TARGETS.get(quarter)
    if not qt:
        return QuarterAssessment(
            quarter=quarter, label="Unknown", metrics=[],
            overall_status=TrackStatus.NOT_STARTED,
            on_track_count=0, at_risk_count=0, off_track_count=0,
            total_gap_dollars=0,
            phase_gate=PhaseGateResult.FAIL,
            phase_gate_notes=f"No targets defined for {quarter}",
            recommendations=[],
        )

    assessments = []
    for metric_id, target in qt.metric_targets.items():
        actual = actual_values.get(metric_id)
        assessment = assess_metric(metric_id, target, actual, account_arr)
        assessments.append(assessment)

    # Aggregate counts
    on_track = sum(1 for a in assessments if a.status in (TrackStatus.ON_TRACK, TrackStatus.AHEAD))
    at_risk = sum(1 for a in assessments if a.status == TrackStatus.AT_RISK)
    off_track = sum(1 for a in assessments if a.status == TrackStatus.OFF_TRACK)
    not_started = sum(1 for a in assessments if a.status == TrackStatus.NOT_STARTED)
    total_gap = sum(a.dollar_impact_of_gap for a in assessments if a.gap > 0)

    # Overall status (weighted by metric importance)
    if off_track >= 2 or (off_track >= 1 and at_risk >= 1):
        overall = TrackStatus.OFF_TRACK
    elif at_risk >= 2 or off_track >= 1:
        overall = TrackStatus.AT_RISK
    elif not_started == len(assessments):
        overall = TrackStatus.NOT_STARTED
    else:
        overall = TrackStatus.ON_TRACK

    # Phase gate decision
    phase_gate, gate_notes = _evaluate_phase_gate(quarter, assessments, overall)

    # Generate recommendations
    recommendations = _generate_recommendations(quarter, assessments)

    return QuarterAssessment(
        quarter=quarter,
        label=qt.label,
        metrics=assessments,
        overall_status=overall,
        on_track_count=on_track,
        at_risk_count=at_risk,
        off_track_count=off_track,
        total_gap_dollars=round(total_gap, 2),
        phase_gate=phase_gate,
        phase_gate_notes=gate_notes,
        recommendations=recommendations,
    )


def assess_full_year(
    actual_values_by_quarter: Dict[str, Dict[str, float]],
    account_arr: Optional[float] = None,
) -> Dict[str, QuarterAssessment]:
    """
    Assess all four quarters and return a full-year roadmap status.
    """
    results = {}
    for q in ["Q1", "Q2", "Q3", "Q4"]:
        actuals = actual_values_by_quarter.get(q, {})
        results[q] = assess_quarter(q, actuals, account_arr)
    return results


def get_current_quarter_from_date(d: Optional[date] = None) -> str:
    """Return 'Q1'-'Q4' based on the given or current date."""
    d = d or date.today()
    return f"Q{(d.month - 1) // 3 + 1}"


# ============================================================
# PHASE GATE LOGIC
# ============================================================

def _evaluate_phase_gate(
    quarter: str,
    assessments: List[MetricAssessment],
    overall: TrackStatus,
) -> Tuple[PhaseGateResult, str]:
    """
    Determine if the customer can advance past this quarter's gate.

    Rules:
      - PASS: All metrics on_track or ahead
      - CONDITIONAL_PASS: <=1 metric at_risk, none off_track
      - FAIL: Any metric off_track, or >=2 at_risk
    """
    off_track = [a for a in assessments if a.status == TrackStatus.OFF_TRACK]
    at_risk = [a for a in assessments if a.status == TrackStatus.AT_RISK]

    if not off_track and not at_risk:
        return PhaseGateResult.PASS, f"{quarter} gate passed — all metrics on track"

    if not off_track and len(at_risk) <= 1:
        names = ", ".join(a.display_name for a in at_risk)
        return (
            PhaseGateResult.CONDITIONAL_PASS,
            f"{quarter} conditional pass — {names} at risk, remediation plan required"
        )

    names = ", ".join(
        a.display_name for a in off_track + at_risk
    )
    return (
        PhaseGateResult.FAIL,
        f"{quarter} gate failed — {names} need intervention before advancing"
    )


# ============================================================
# RECOMMENDATION ENGINE
# ============================================================

def _generate_recommendations(
    quarter: str,
    assessments: List[MetricAssessment],
) -> List[str]:
    """Generate prioritized recommendations based on gaps."""
    recs = []

    # Sort by dollar impact descending — fix the biggest $ gaps first
    gaps = sorted(
        [a for a in assessments if a.gap > 0],
        key=lambda a: a.dollar_impact_of_gap,
        reverse=True,
    )

    for a in gaps:
        metric = POWER_OF_1_METRICS.get(a.metric_id)
        if not metric:
            continue

        if a.status == TrackStatus.OFF_TRACK:
            recs.append(
                f"CRITICAL: {a.display_name} is {a.gap:.1f} {metric.unit} behind target "
                f"(${a.dollar_impact_of_gap:,.0f}/yr at risk). "
                f"Activate playbooks: {', '.join(metric.linked_playbooks)}. "
                f"Focus work packages in {metric.primary_pillar.value} pillar."
            )
        elif a.status == TrackStatus.AT_RISK:
            recs.append(
                f"WARNING: {a.display_name} is trending behind by {a.gap:.1f} {metric.unit} "
                f"(${a.dollar_impact_of_gap:,.0f}/yr exposure). "
                f"Review {metric.primary_pillar.value} pillar activities."
            )

    if not recs:
        recs.append(f"{quarter} is on track — maintain current execution cadence.")

    return recs


# ============================================================
# SERIALIZATION
# ============================================================

def assessment_to_dict(assessment: QuarterAssessment) -> Dict:
    """Serialize a QuarterAssessment for API response."""
    return {
        "quarter": assessment.quarter,
        "label": assessment.label,
        "overall_status": assessment.overall_status.value,
        "on_track_count": assessment.on_track_count,
        "at_risk_count": assessment.at_risk_count,
        "off_track_count": assessment.off_track_count,
        "total_gap_dollars": assessment.total_gap_dollars,
        "phase_gate": assessment.phase_gate.value,
        "phase_gate_notes": assessment.phase_gate_notes,
        "recommendations": assessment.recommendations,
        "metrics": [
            {
                "metric_id": m.metric_id,
                "display_name": m.display_name,
                "target_value": m.target_value,
                "actual_value": m.actual_value,
                "gap": m.gap,
                "gap_pct": m.gap_pct,
                "status": m.status.value,
                "milestone": m.milestone,
                "dollar_impact_of_gap": m.dollar_impact_of_gap,
            }
            for m in assessment.metrics
        ],
    }
