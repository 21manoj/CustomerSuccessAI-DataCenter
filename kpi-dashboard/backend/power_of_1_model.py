#!/usr/bin/env python3
"""
Power of 1 Revenue Intelligence Model
=======================================
Encodes the complete "Power of 1" economic framework from the CS GrowthPulse deck.

Core principle: What does a 1% improvement in each key metric mean in dollars?
Every playbook action has a cost, every KPI improvement has a dollar value.
The platform proves non-linear scaling — same investment, 4-6x returns.

Feature flag: 'revenue_intelligence' (per-customer toggle in Settings UI)

DATA SOURCE: All economics loaded from config/power_of_1_economics.json
             and config/investment_summary.json — editable via Settings UI.
"""

import json
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


# ============================================================
# CONFIG LOADER
# ============================================================

_CONFIG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config")


def _load_json(filename: str) -> dict:
    """Load a JSON config file from the config/ directory."""
    path = os.path.join(_CONFIG_DIR, filename)
    with open(path, "r") as f:
        return json.load(f)


def reload_config():
    """
    Reload all economic config from JSON files.
    Call this after the Settings UI saves new values.
    """
    global POWER_OF_1_METRICS, METRIC_CASCADES, COMPOUNDING_MULTIPLIER
    global SCALING_SCENARIOS, INVESTMENT_SUMMARY, TIME_ECONOMICS
    global IMPLEMENTATION_PHASES, AUTOMATION_TIMELINE
    global QUARTERLY_CHECKPOINTS, CS_PILLAR_WEIGHTS

    economics = _load_json("power_of_1_economics.json")
    inv_cfg = _load_json("investment_summary.json")

    POWER_OF_1_METRICS = _build_metrics(economics)
    METRIC_CASCADES = economics.get("metric_cascades", {})
    COMPOUNDING_MULTIPLIER = economics.get("compounding_multiplier", 0.15)
    SCALING_SCENARIOS = economics.get("scaling_scenarios", {})
    TIME_ECONOMICS = economics.get("time_economics", {})

    INVESTMENT_SUMMARY = {
        k: v for k, v in inv_cfg.items()
        if not k.startswith("_") and k not in (
            "implementation_phases", "automation_timeline",
            "quarterly_checkpoints", "cs_pillar_weights",
        )
    }
    IMPLEMENTATION_PHASES = inv_cfg.get("implementation_phases", {})
    AUTOMATION_TIMELINE = inv_cfg.get("automation_timeline", {})
    QUARTERLY_CHECKPOINTS = inv_cfg.get("quarterly_checkpoints", {})
    CS_PILLAR_WEIGHTS = {
        CSPillar(k): v
        for k, v in inv_cfg.get("cs_pillar_weights", {}).items()
    }


# ============================================================
# METRIC CATEGORIES
# ============================================================

class MetricCategory(Enum):
    """Power of 1 metric categories — each has a different ROI profile"""
    FOUNDATION_INVESTMENT = "foundation_investment"
    GROWTH_ACCELERATOR = "growth_accelerator"
    RETENTION_FOUNDATION = "retention_foundation"
    EFFICIENCY_BOOSTER = "efficiency_booster"
    VALUE_AMPLIFIER = "value_amplifier"
    REVENUE_DRIVER = "revenue_driver"


class ImpactType(Enum):
    """Dollar impact classification — 80/20 split per the deck"""
    REVENUE_INCREASE = "revenue_increase"
    COST_SAVINGS = "cost_savings"


class CSPillar(Enum):
    """The 5 CS Pillars that map to health score categories"""
    USAGE_ONBOARDING = "usage_onboarding"
    SUPPORT_ENGAGEMENT = "support_engagement"
    CUSTOMER_SENTIMENT = "customer_sentiment"
    BUSINESS_OUTCOMES = "business_outcomes"
    RELATIONSHIP_STRENGTH = "relationship_strength"


# ============================================================
# WORK PACKAGE DEFINITIONS
# ============================================================

@dataclass
class RoleAllocation:
    """Hours allocated per role for a work package"""
    csm: float = 0
    cs_ops: float = 0
    product: float = 0
    platform: float = 0
    leadership: float = 0

    @property
    def total_hours(self) -> float:
        return self.csm + self.cs_ops + self.product + self.platform + self.leadership


@dataclass
class WorkPackage:
    """A discrete unit of work within a metric improvement initiative"""
    name: str
    description: str
    hours: float
    roles: RoleAllocation
    deliverables: List[str] = field(default_factory=list)


# ============================================================
# POWER OF 1 METRIC DEFINITIONS
# ============================================================

@dataclass
class PowerOf1Metric:
    """Complete economic model for a single metric"""
    metric_id: str
    display_name: str
    baseline: float
    unit: str
    direction: str
    one_pct_move: float
    annual_impact_per_pct: float
    total_investment: float
    cs_initiative_cost: float
    platform_cost: float
    roi_at_1pct: float
    payback_months: float
    category: MetricCategory
    primary_pillar: CSPillar
    secondary_pillars: List[CSPillar]
    linked_playbooks: List[str]
    linked_kpi_codes: List[str]
    total_hours: float
    quarters: List[str]
    impact_breakdown: Dict[ImpactType, float]
    work_packages: List[WorkPackage]


# ============================================================
# BUILD METRICS FROM JSON
# ============================================================

def _build_metrics(economics: dict) -> Dict[str, PowerOf1Metric]:
    """Parse the JSON metrics config into PowerOf1Metric dataclass instances."""
    metrics = {}
    for metric_id, m in economics.get("metrics", {}).items():
        work_packages = []
        for wp in m.get("work_packages", []):
            roles_data = wp.get("roles", {})
            work_packages.append(WorkPackage(
                name=wp["name"],
                description=wp["description"],
                hours=wp["hours"],
                roles=RoleAllocation(
                    csm=roles_data.get("csm", 0),
                    cs_ops=roles_data.get("cs_ops", 0),
                    product=roles_data.get("product", 0),
                    platform=roles_data.get("platform", 0),
                    leadership=roles_data.get("leadership", 0),
                ),
                deliverables=wp.get("deliverables", []),
            ))

        impact_raw = m.get("impact_breakdown", {})
        impact_breakdown = {
            ImpactType.REVENUE_INCREASE: impact_raw.get("revenue_increase", 0),
            ImpactType.COST_SAVINGS: impact_raw.get("cost_savings", 0),
        }

        secondary = [CSPillar(p) for p in m.get("secondary_pillars", [])]

        metrics[metric_id] = PowerOf1Metric(
            metric_id=metric_id,
            display_name=m["display_name"],
            baseline=m["baseline"],
            unit=m["unit"],
            direction=m["direction"],
            one_pct_move=m["one_pct_move"],
            annual_impact_per_pct=m["annual_impact_per_pct"],
            total_investment=m["total_investment"],
            cs_initiative_cost=m["cs_initiative_cost"],
            platform_cost=m["platform_cost"],
            roi_at_1pct=m["roi_at_1pct"],
            payback_months=m["payback_months"],
            category=MetricCategory(m["category"]),
            primary_pillar=CSPillar(m["primary_pillar"]),
            secondary_pillars=secondary,
            linked_playbooks=m.get("linked_playbooks", []),
            linked_kpi_codes=m.get("linked_kpi_codes", []),
            total_hours=m["total_hours"],
            quarters=m.get("quarters", []),
            impact_breakdown=impact_breakdown,
            work_packages=work_packages,
        )
    return metrics


# ============================================================
# MODULE-LEVEL CONSTANTS — loaded from JSON at import time
# ============================================================
# These are the same names every other module imports.
# reload_config() re-populates them from disk.

_economics = _load_json("power_of_1_economics.json")
_inv_cfg = _load_json("investment_summary.json")

POWER_OF_1_METRICS: Dict[str, PowerOf1Metric] = _build_metrics(_economics)

METRIC_CASCADES = _economics.get("metric_cascades", {})
COMPOUNDING_MULTIPLIER = _economics.get("compounding_multiplier", 0.15)
SCALING_SCENARIOS = _economics.get("scaling_scenarios", {})
TIME_ECONOMICS = _economics.get("time_economics", {})

INVESTMENT_SUMMARY = {
    k: v for k, v in _inv_cfg.items()
    if not k.startswith("_") and k not in (
        "implementation_phases", "automation_timeline",
        "quarterly_checkpoints", "cs_pillar_weights",
    )
}
IMPLEMENTATION_PHASES = _inv_cfg.get("implementation_phases", {})
AUTOMATION_TIMELINE = _inv_cfg.get("automation_timeline", {})
QUARTERLY_CHECKPOINTS = _inv_cfg.get("quarterly_checkpoints", {})
CS_PILLAR_WEIGHTS = {
    CSPillar(k): v
    for k, v in _inv_cfg.get("cs_pillar_weights", {}).items()
}


# ============================================================
# CALCULATION FUNCTIONS
# ============================================================

def calculate_power_of_1_impact(
    metric_id: str,
    improvement_pct: float,
    account_arr: Optional[float] = None,
    vertical: str = "dc2_s",
) -> Dict:
    """
    Calculate the dollar impact of an improvement in a Power of 1 metric.

    Args:
        metric_id: One of the 6 Power of 1 metric IDs
        improvement_pct: The percentage improvement achieved (e.g., 1.0, 4.0, 6.0)
        account_arr: If provided, scales impact proportionally to account ARR.
                     Default economics assume $10M ARR base.
        vertical: Vertical identifier for future multi-vertical calibration.

    Returns:
        Dict with direct_impact, compounding_impact, total_impact, roi,
        investment (per-metric cost), and breakdown
    """
    metric = POWER_OF_1_METRICS.get(metric_id)
    if not metric:
        return {"error": f"Unknown metric: {metric_id}"}

    # Scale factor: if account ARR differs from assumed $10M base
    arr_scale = 1.0
    if account_arr is not None:
        arr_scale = account_arr / 10_000_000

    direct_impact = metric.annual_impact_per_pct * improvement_pct * arr_scale

    # Calculate compounding via cascade
    compounding_impact = _calculate_cascade_impact(metric_id, improvement_pct, arr_scale)

    total_impact = direct_impact + compounding_impact

    # Per-metric investment cost (from JSON config)
    investment = metric.total_investment

    roi = (total_impact - investment) / investment if investment > 0 else 0
    payback_months = (investment / (total_impact / 12)) if total_impact > 0 else float('inf')

    return {
        "metric_id": metric_id,
        "display_name": metric.display_name,
        "improvement_pct": improvement_pct,
        "baseline": metric.baseline,
        "new_value": _calculate_new_value(metric, improvement_pct),
        "direct_impact": round(direct_impact, 2),
        "compounding_impact": round(compounding_impact, 2),
        "total_impact": round(total_impact, 2),
        "investment": investment,
        "cs_initiative_cost": metric.cs_initiative_cost,
        "platform_cost": metric.platform_cost,
        "roi": round(roi, 4),
        "payback_months": round(payback_months, 1),
        "category": metric.category.value,
        "impact_breakdown": {
            "revenue_increase": round(
                metric.impact_breakdown.get(ImpactType.REVENUE_INCREASE, 0) * improvement_pct * arr_scale, 2
            ),
            "cost_savings": round(
                metric.impact_breakdown.get(ImpactType.COST_SAVINGS, 0) * improvement_pct * arr_scale, 2
            ),
        },
    }


def calculate_portfolio_impact(
    improvement_pct: float = 1.0,
    total_arr: Optional[float] = None,
) -> Dict:
    """
    Calculate total Power of 1 impact across all 6 metrics.

    Returns the full investment summary with scaling scenarios.
    """
    arr_scale = 1.0
    if total_arr is not None:
        arr_scale = total_arr / 10_000_000

    results = {}
    total_direct = 0
    total_revenue = 0
    total_savings = 0

    for metric_id, metric in POWER_OF_1_METRICS.items():
        impact = calculate_power_of_1_impact(metric_id, improvement_pct, total_arr)
        results[metric_id] = impact
        total_direct += impact["direct_impact"]
        total_revenue += impact["impact_breakdown"]["revenue_increase"]
        total_savings += impact["impact_breakdown"]["cost_savings"]

    compounding = total_direct * COMPOUNDING_MULTIPLIER
    total_impact = total_direct + compounding

    investment = INVESTMENT_SUMMARY["total_investment"]
    roi = (total_impact - investment) / investment if investment > 0 else 0

    return {
        "improvement_pct": improvement_pct,
        "metrics": results,
        "totals": {
            "direct_impact": round(total_direct, 2),
            "compounding_effect": round(compounding, 2),
            "total_impact": round(total_impact, 2),
            "revenue_increase": round(total_revenue, 2),
            "cost_savings": round(total_savings, 2),
            "investment": investment,
            "cs_initiatives_cost": INVESTMENT_SUMMARY["cs_initiatives"],
            "platform_cost": INVESTMENT_SUMMARY["platform_cost"],
            "roi": round(roi, 4),
            "payback_months": round(
                (investment / (total_impact / 12)) if total_impact > 0 else float('inf'), 1
            ),
        },
        "scaling_scenarios": SCALING_SCENARIOS,
        "time_economics": TIME_ECONOMICS,
    }


def get_metric_for_kpi_code(kpi_code: str) -> Optional[str]:
    """
    Given a KPI code (e.g., 'P1-KPI1'), return the Power of 1 metric it maps to.
    """
    for metric_id, metric in POWER_OF_1_METRICS.items():
        if kpi_code in metric.linked_kpi_codes:
            return metric_id
    return None


def get_metrics_for_playbook(playbook_id: str) -> List[str]:
    """
    Given a playbook ID (e.g., 'voc-sprint'), return the Power of 1 metrics it improves.
    """
    result = []
    for metric_id, metric in POWER_OF_1_METRICS.items():
        if playbook_id in metric.linked_playbooks:
            result.append(metric_id)
    return result


def get_metric_cost(metric_id: str) -> Dict:
    """
    Return the investment cost for a given metric — used by the ROI engine
    and agentic loop to compute real per-action costs.
    """
    metric = POWER_OF_1_METRICS.get(metric_id)
    if not metric:
        return {"error": f"Unknown metric: {metric_id}"}
    return {
        "metric_id": metric_id,
        "total_investment": metric.total_investment,
        "cs_initiative_cost": metric.cs_initiative_cost,
        "platform_cost": metric.platform_cost,
        "total_hours": metric.total_hours,
    }


# ============================================================
# INTERNAL HELPERS
# ============================================================

def _calculate_cascade_impact(metric_id: str, improvement_pct: float, arr_scale: float) -> float:
    """Calculate cascading compounding impact through the flywheel."""
    cascade = METRIC_CASCADES.get(metric_id, {})
    amplifies = cascade.get("amplifies", [])

    total_cascade = 0
    for amp in amplifies:
        target = POWER_OF_1_METRICS.get(amp["target_metric"])
        if target:
            cascade_impact = (
                target.annual_impact_per_pct
                * improvement_pct
                * amp["multiplier"]
                * arr_scale
            )
            total_cascade += cascade_impact

    # Cap at the conservative compounding multiplier
    direct = POWER_OF_1_METRICS[metric_id].annual_impact_per_pct * improvement_pct * arr_scale
    max_compounding = direct * COMPOUNDING_MULTIPLIER
    return min(total_cascade, max_compounding)


def _calculate_new_value(metric: PowerOf1Metric, improvement_pct: float) -> float:
    """Calculate the new metric value after improvement."""
    absolute_change = metric.one_pct_move * improvement_pct
    if metric.direction == "lower_is_better":
        return round(metric.baseline - absolute_change, 2)
    return round(metric.baseline + absolute_change, 2)
