#!/usr/bin/env python3
"""
Vertical Configuration System
===============================
Three-tier config: Platform defaults → Vertical overrides → Customer overrides.

Tier 1 — Platform defaults (this file, BaseVerticalConfig)
Tier 2 — Vertical overrides (DataCenterConfig, SaaSConfig, etc.)
Tier 3 — Customer overrides (database-backed, via Settings UI)

Every module that previously hardcoded tunable values now calls:
    cfg = get_config(customer_id)
    cfg.power_of_1.metrics['NRR'].baseline

The config is immutable once loaded. Customer overrides are merged on
top of the vertical defaults at load time.
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum


# ============================================================
# METRIC CONFIG
# ============================================================

@dataclass
class MetricConfig:
    """Configuration for a single Power-of-1 metric."""
    baseline: float
    one_pct_move: float
    annual_impact_per_pct: float
    total_investment: float
    roi_at_1_pct: float
    unit: str
    direction: str  # 'higher_is_better' | 'lower_is_better'
    display_name: str
    work_package_hours: float = 0  # total WP hours for this metric


@dataclass
class PowerOf1Config:
    """All Power-of-1 economic model tunables."""
    metrics: Dict[str, MetricConfig] = field(default_factory=dict)
    compounding_multiplier: float = 0.15
    cascade_multipliers: Dict[str, Dict[str, float]] = field(default_factory=dict)
    total_investment: float = 247_000
    total_fte: float = 2.81
    total_hours: int = 5840
    arr_scale_base: float = 10_000_000


# ============================================================
# RESOURCE POOL CONFIG
# ============================================================

@dataclass
class RoleConfig:
    """Configuration for a single CS role."""
    annual_hours: float
    fte: float
    hourly_rate: float
    display_name: str
    description: str


@dataclass
class ResourcePoolConfig:
    """All resource pool tunables."""
    roles: Dict[str, RoleConfig] = field(default_factory=dict)
    metric_allocations: Dict[str, Dict[str, float]] = field(default_factory=dict)
    # metric_id → {role_id: hours}


# ============================================================
# QUARTERLY CHECKPOINT CONFIG
# ============================================================

@dataclass
class QuarterTargetConfig:
    """Targets for a single quarter."""
    label: str
    month_range: str
    metric_targets: Dict[str, float] = field(default_factory=dict)


@dataclass
class QuarterlyConfig:
    """All quarterly checkpoint tunables."""
    targets: Dict[str, QuarterTargetConfig] = field(default_factory=dict)
    on_track_threshold: float = 0.15
    at_risk_threshold: float = 0.40


# ============================================================
# PLAYBOOK CONFIG
# ============================================================

@dataclass
class PlaybookTriggerConfig:
    """Trigger conditions for a playbook."""
    thresholds: Dict[str, Any] = field(default_factory=dict)
    duration_days: int = 30
    expected_outcomes: Dict[str, str] = field(default_factory=dict)


@dataclass
class PlaybookSystemConfig:
    """All playbook trigger tunables."""
    triggers: Dict[str, PlaybookTriggerConfig] = field(default_factory=dict)
    auto_approve_threshold: float = 0.80
    auto_reject_threshold: float = 0.40


# ============================================================
# SYNERGY CONFIG
# ============================================================

@dataclass
class SynergyCurveConfig:
    """Synergy curve parameters for one synergy type."""
    base_lift_pct: float
    decay_rate: float
    max_companies: int


@dataclass
class SynergyConfig:
    """All synergy engine tunables."""
    curves: Dict[str, SynergyCurveConfig] = field(default_factory=dict)


# ============================================================
# HEALTH SCORE CONFIG
# ============================================================

@dataclass
class KPIRangeConfig:
    """Reference range for a single KPI."""
    low_max: float
    medium_max: float
    high_max: float
    unit: str = ""
    direction: str = "higher_is_better"


@dataclass
class HealthScoreConfig:
    """All health score tunables."""
    category_weights: Dict[str, float] = field(default_factory=dict)
    kpi_reference_ranges: Dict[str, KPIRangeConfig] = field(default_factory=dict)
    health_threshold_high: float = 67.0
    health_threshold_medium: float = 34.0
    pillar_weights: Dict[str, float] = field(default_factory=dict)


# ============================================================
# FEEDBACK & LEARNING CONFIG
# ============================================================

@dataclass
class FeedbackConfig:
    """All feedback loop tunables."""
    default_weights: Dict[str, float] = field(default_factory=dict)
    learning_rate: float = 0.10
    recalibration_window_days: int = 90
    cache_ttl_seconds: int = 86400
    accuracy_good_threshold: float = 0.70
    accuracy_poor_threshold: float = 0.50


# ============================================================
# AI AGENT CONFIG
# ============================================================

@dataclass
class AgentConfig:
    """AI agent tunables."""
    default_provider: str = "openai"
    openai_model: str = "gpt-4o"
    claude_model: str = "claude-sonnet-4-5-20250929"
    temperature: float = 0.3
    max_tokens: int = 3000
    decision_matrix_model: str = "gpt-4o-mini"


# ============================================================
# FINANCIAL PROJECTION CONFIG
# ============================================================

@dataclass
class FinancialCoefficientConfig:
    """Financial impact coefficients for one category."""
    expansion_weight: float
    churn_weight: float
    renewal_weight: float


@dataclass
class FinancialConfig:
    """Financial projections tunables."""
    coefficients: Dict[str, FinancialCoefficientConfig] = field(default_factory=dict)
    aggregation_weights: Dict[str, float] = field(default_factory=dict)
    improvement_divisor: float = 10.0


# ============================================================
# COMPOSITE VERTICAL CONFIG
# ============================================================

@dataclass
class VerticalConfig:
    """Complete configuration for a vertical + customer."""
    vertical_id: str
    vertical_name: str
    power_of_1: PowerOf1Config = field(default_factory=PowerOf1Config)
    resource_pool: ResourcePoolConfig = field(default_factory=ResourcePoolConfig)
    quarterly: QuarterlyConfig = field(default_factory=QuarterlyConfig)
    playbooks: PlaybookSystemConfig = field(default_factory=PlaybookSystemConfig)
    synergy: SynergyConfig = field(default_factory=SynergyConfig)
    health_score: HealthScoreConfig = field(default_factory=HealthScoreConfig)
    feedback: FeedbackConfig = field(default_factory=FeedbackConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)
    financial: FinancialConfig = field(default_factory=FinancialConfig)

    def to_dict(self) -> Dict:
        return asdict(self)


# ============================================================
# PLATFORM DEFAULTS (Tier 1)
# ============================================================

def _build_platform_defaults() -> VerticalConfig:
    """Build Tier-1 platform defaults used by all verticals."""
    cfg = VerticalConfig(
        vertical_id="platform",
        vertical_name="Platform Defaults",
    )

    # ── Resource Pool defaults ──
    cfg.resource_pool.roles = {
        "csm":        RoleConfig(1920, 0.92, 95.00,  "Customer Success Managers", "Direct customer engagement, QBRs"),
        "cs_ops":     RoleConfig(1760, 0.85, 85.00,  "CS Operations",            "Process design, automation, analytics"),
        "product":    RoleConfig( 760, 0.37, 110.00, "Product Team",             "Feature development, integrations"),
        "platform":   RoleConfig( 920, 0.44, 120.00, "Platform Team (Us)",       "Platform configuration, APIs, dashboards"),
        "leadership": RoleConfig( 480, 0.23, 150.00, "CS Leadership",            "Strategy, governance, executive alignment"),
    }

    # ── Power of 1 defaults ──
    cfg.power_of_1 = PowerOf1Config(
        metrics={
            "TTFV": MetricConfig(30.0, 0.30, 61250, 75500, -0.19, "days", "lower_is_better", "Time to First Value", 1280),
            "NRR":  MetricConfig(105.0, 1.05, 105000, 50000, 2.10, "%", "higher_is_better", "Net Revenue Retention", 1000),
            "GRR":  MetricConfig(85.0, 0.85, 100000, 60000, 0.67, "%", "higher_is_better", "Gross Revenue Retention", 1280),
            "ticket_resolution_time": MetricConfig(48.0, 0.48, 38000, 26000, 0.46, "hours", "lower_is_better", "Ticket Resolution Time", 840),
            "product_adoption": MetricConfig(65.0, 0.65, 32500, 21000, 0.55, "%", "higher_is_better", "Product Adoption", 800),
            "expansion_rate":   MetricConfig(20.0, 0.20, 65000, 14500, 3.48, "%", "higher_is_better", "Expansion Rate", 640),
        },
        compounding_multiplier=0.15,
        total_investment=247000,
        total_fte=2.81,
        total_hours=5840,
        arr_scale_base=10_000_000,
    )

    # ── Quarterly Checkpoints ──
    cfg.quarterly = QuarterlyConfig(
        targets={
            "Q1": QuarterTargetConfig("Foundation", "Jan-Mar", {"TTFV": 30.0}),
            "Q2": QuarterTargetConfig("Acceleration", "Apr-Jun", {"TTFV": 29.5, "NRR": 105.5, "ticket_resolution_time": 47.5}),
            "Q3": QuarterTargetConfig("Expansion", "Jul-Sep", {"TTFV": 29.0, "NRR": 105.8, "GRR": 85.5, "product_adoption": 65.3, "expansion_rate": 20.1}),
            "Q4": QuarterTargetConfig("Optimization", "Oct-Dec", {"TTFV": 29.0, "NRR": 106.0, "GRR": 86.0, "ticket_resolution_time": 47.0, "product_adoption": 65.65, "expansion_rate": 20.2}),
        },
        on_track_threshold=0.15,
        at_risk_threshold=0.40,
    )

    # ── Playbook Triggers ──
    cfg.playbooks = PlaybookSystemConfig(
        triggers={
            "voc-sprint": PlaybookTriggerConfig(
                thresholds={"nps": 10, "csat": 3.6, "churn_risk": 0.30, "health_drop": 10},
                duration_days=30,
                expected_outcomes={"nps_improvement": "+10-20", "csat_improvement": "+0.5-1.0"},
            ),
            "activation-blitz": PlaybookTriggerConfig(
                thresholds={"adoption_index": 60, "active_users": 50, "dau_mau_ratio": 0.25, "feature_adoption": 0.40},
                duration_days=30,
                expected_outcomes={"active_user_growth": "20-30%", "feature_adoption_improvement": "15-25%"},
            ),
            "sla-stabilizer": PlaybookTriggerConfig(
                thresholds={"sla_breaches_per_month": 5, "response_time_multiplier": 2.0, "reopen_rate": 0.20},
                duration_days=21,
                expected_outcomes={"sla_compliance": "95%+", "response_time_reduction": "40-60%"},
            ),
            "renewal-safeguard": PlaybookTriggerConfig(
                thresholds={"renewal_window_days": 90, "health_score": 70, "nps_below": 0, "churn_risk": 0.40},
                duration_days=42,
                expected_outcomes={"renewal_rate": "85-95%", "health_score_improvement": "+15-25"},
            ),
            "expansion-timing": PlaybookTriggerConfig(
                thresholds={"health_score_above": 80, "adoption_above": 0.85, "usage_above": 0.80},
                duration_days=45,
                expected_outcomes={"expansion_conversion": "25-40%", "arr_uplift": "15-30%"},
            ),
        },
        auto_approve_threshold=0.80,
        auto_reject_threshold=0.40,
    )

    # ── Synergy Curves ──
    cfg.synergy = SynergyConfig(
        curves={
            "shared_playbooks":  SynergyCurveConfig(12.0, 0.70, 15),
            "shared_resources":  SynergyCurveConfig(18.0, 0.80, 15),
            "vendor_leverage":   SynergyCurveConfig( 8.0, 0.65, 10),
            "cross_sell":        SynergyCurveConfig( 5.0, 0.60, 10),
            "benchmarking":      SynergyCurveConfig(10.0, 0.75, 20),
        },
    )

    # ── Health Score ──
    cfg.health_score = HealthScoreConfig(
        category_weights={
            "Product Usage": 0.20,
            "Support": 0.20,
            "Customer Sentiment": 0.20,
            "Business Outcomes": 0.25,
            "Relationship Strength": 0.15,
        },
        health_threshold_high=67.0,
        health_threshold_medium=34.0,
        pillar_weights={
            "usage_onboarding": 0.30,
            "business_outcomes": 0.20,
            "support_engagement": 0.20,
            "sentiment": 0.15,
            "relationship": 0.15,
        },
    )

    # ── Feedback Loop ──
    cfg.feedback = FeedbackConfig(
        default_weights={
            "quantitative_signals": 0.40,
            "qualitative_signals": 0.30,
            "historical_patterns": 0.20,
            "playbook_feedback": 0.10,
        },
        learning_rate=0.10,
        recalibration_window_days=90,
        cache_ttl_seconds=86400,
        accuracy_good_threshold=0.70,
        accuracy_poor_threshold=0.50,
    )

    # ── Agent ──
    cfg.agent = AgentConfig(
        default_provider="openai",
        openai_model="gpt-4o",
        claude_model="claude-sonnet-4-5-20250929",
        temperature=0.3,
        max_tokens=3000,
        decision_matrix_model="gpt-4o-mini",
    )

    # ── Financial Projections ──
    cfg.financial = FinancialConfig(
        coefficients={
            "Product Usage":        FinancialCoefficientConfig(0.15, -0.05, 0.08),
            "Support":              FinancialCoefficientConfig(0.08, -0.12, 0.12),
            "Customer Sentiment":   FinancialCoefficientConfig(0.20, -0.03, 0.15),
            "Business Outcomes":    FinancialCoefficientConfig(0.25, -0.08, 0.10),
            "Relationship Strength": FinancialCoefficientConfig(0.18, -0.04, 0.20),
        },
        aggregation_weights={
            "Product Usage": 0.30,
            "Support": 0.20,
            "Customer Sentiment": 0.20,
            "Business Outcomes": 0.15,
            "Relationship Strength": 0.15,
        },
        improvement_divisor=10.0,
    )

    return cfg


PLATFORM_DEFAULTS: VerticalConfig = _build_platform_defaults()


# ============================================================
# DATA CENTER VERTICAL (Tier 2)
# ============================================================

def build_datacenter_config() -> VerticalConfig:
    """
    Data Center vertical overrides on top of platform defaults.
    Everything NOT set here inherits from PLATFORM_DEFAULTS.
    """
    cfg = copy.deepcopy(PLATFORM_DEFAULTS)
    cfg.vertical_id = "datacenter"
    cfg.vertical_name = "Data Center Infrastructure"

    # DC-specific metric baselines
    cfg.power_of_1.metrics["TTFV"].baseline = 45.0          # DC deployments take longer
    cfg.power_of_1.metrics["TTFV"].annual_impact_per_pct = 72000
    cfg.power_of_1.metrics["ticket_resolution_time"].baseline = 72.0  # Hardware SLA is slower
    cfg.power_of_1.metrics["product_adoption"].baseline = 55.0        # Infrastructure adoption curves differ
    cfg.power_of_1.metrics["expansion_rate"].baseline = 15.0          # DC expansion is more deliberate

    # DC quarterly targets
    cfg.quarterly.targets["Q1"].metric_targets = {"TTFV": 44.0}
    cfg.quarterly.targets["Q2"].metric_targets = {"TTFV": 42.0, "NRR": 105.0, "ticket_resolution_time": 70.0}
    cfg.quarterly.targets["Q3"].metric_targets = {"TTFV": 40.0, "NRR": 105.5, "GRR": 85.0, "expansion_rate": 15.3}
    cfg.quarterly.targets["Q4"].metric_targets = {"TTFV": 38.0, "NRR": 106.0, "GRR": 86.0, "expansion_rate": 15.6}

    # DC health score weights — reliability + capacity matter more
    cfg.health_score.category_weights = {
        "Product Usage": 0.15,
        "Support": 0.25,
        "Customer Sentiment": 0.15,
        "Business Outcomes": 0.25,
        "Relationship Strength": 0.20,
    }

    cfg.health_score.pillar_weights = {
        "P3": 0.20,
        "P4": 0.25,
        "P1": 0.20,
        "P5": 0.15,
        "P2": 0.20,
    }

    # DC playbook trigger adjustments
    cfg.playbooks.triggers["sla-stabilizer"].thresholds["sla_breaches_per_month"] = 3  # tighter SLA
    cfg.playbooks.triggers["sla-stabilizer"].thresholds["response_time_multiplier"] = 1.5

    # DC synergy — shared infrastructure resources have higher lift
    cfg.synergy.curves["shared_resources"].base_lift_pct = 22.0
    cfg.synergy.curves["vendor_leverage"].base_lift_pct = 12.0

    return cfg


# ============================================================
# SAAS VERTICAL (Tier 2)
# ============================================================

def build_saas_config() -> VerticalConfig:
    """
    SaaS vertical overrides on top of platform defaults.
    Most SaaS values ARE the platform defaults, so fewer overrides.
    """
    cfg = copy.deepcopy(PLATFORM_DEFAULTS)
    cfg.vertical_id = "saas"
    cfg.vertical_name = "SaaS Customer Success"

    # SaaS has faster onboarding
    cfg.power_of_1.metrics["TTFV"].baseline = 21.0
    cfg.power_of_1.metrics["ticket_resolution_time"].baseline = 36.0

    # SaaS health score — engagement and sentiment matter more
    cfg.health_score.category_weights = {
        "Product Usage": 0.25,
        "Support": 0.15,
        "Customer Sentiment": 0.25,
        "Business Outcomes": 0.20,
        "Relationship Strength": 0.15,
    }

    cfg.health_score.pillar_weights = {
        "usage_onboarding": 0.30,
        "business_outcomes": 0.20,
        "support_engagement": 0.15,
        "sentiment": 0.20,
        "relationship": 0.15,
    }

    # SaaS synergy — cross-sell has higher lift
    cfg.synergy.curves["cross_sell"].base_lift_pct = 10.0

    return cfg


# ============================================================
# VERTICAL REGISTRY
# ============================================================

VERTICAL_REGISTRY: Dict[str, VerticalConfig] = {
    "datacenter": build_datacenter_config(),
    "dc2_s":      build_datacenter_config(),   # alias
    "saas":       build_saas_config(),
    "platform":   PLATFORM_DEFAULTS,
}


def register_vertical(vertical_id: str, builder) -> None:
    """Register a new vertical config builder (for future verticals)."""
    VERTICAL_REGISTRY[vertical_id] = builder()


# ============================================================
# CONFIG RESOLUTION (Tier 3 — customer overrides)
# ============================================================

def _apply_customer_overrides(
    base: VerticalConfig,
    overrides: Dict[str, Any],
) -> VerticalConfig:
    """
    Deep-merge customer overrides from the Settings UI / database
    onto the vertical defaults.  Only the keys present in `overrides`
    are changed; everything else inherits.
    """
    cfg = copy.deepcopy(base)

    # Resource pool overrides
    if "resource_pool" in overrides:
        rp = overrides["resource_pool"]
        if "roles" in rp:
            for role_id, role_data in rp["roles"].items():
                if role_id in cfg.resource_pool.roles:
                    for k, v in role_data.items():
                        setattr(cfg.resource_pool.roles[role_id], k, v)

    # Power of 1 overrides
    if "power_of_1" in overrides:
        po1 = overrides["power_of_1"]
        if "metrics" in po1:
            for mid, mdata in po1["metrics"].items():
                if mid in cfg.power_of_1.metrics:
                    for k, v in mdata.items():
                        setattr(cfg.power_of_1.metrics[mid], k, v)
        for k in ("compounding_multiplier", "total_investment", "total_fte", "arr_scale_base"):
            if k in po1:
                setattr(cfg.power_of_1, k, po1[k])

    # Health score overrides
    if "health_score" in overrides:
        hs = overrides["health_score"]
        if "category_weights" in hs:
            cfg.health_score.category_weights.update(hs["category_weights"])
        if "pillar_weights" in hs:
            cfg.health_score.pillar_weights.update(hs["pillar_weights"])
        for k in ("health_threshold_high", "health_threshold_medium"):
            if k in hs:
                setattr(cfg.health_score, k, hs[k])

    # Quarterly overrides
    if "quarterly" in overrides:
        qt = overrides["quarterly"]
        if "targets" in qt:
            for q, tdata in qt["targets"].items():
                if q in cfg.quarterly.targets:
                    cfg.quarterly.targets[q].metric_targets.update(tdata.get("metric_targets", {}))
        for k in ("on_track_threshold", "at_risk_threshold"):
            if k in qt:
                setattr(cfg.quarterly, k, qt[k])

    # Playbook overrides
    if "playbooks" in overrides:
        pb = overrides["playbooks"]
        if "triggers" in pb:
            for pid, pdata in pb["triggers"].items():
                if pid in cfg.playbooks.triggers:
                    if "thresholds" in pdata:
                        cfg.playbooks.triggers[pid].thresholds.update(pdata["thresholds"])
                    if "duration_days" in pdata:
                        cfg.playbooks.triggers[pid].duration_days = pdata["duration_days"]
        for k in ("auto_approve_threshold", "auto_reject_threshold"):
            if k in pb:
                setattr(cfg.playbooks, k, pb[k])

    # Synergy overrides
    if "synergy" in overrides:
        sy = overrides["synergy"]
        if "curves" in sy:
            for sid, sdata in sy["curves"].items():
                if sid in cfg.synergy.curves:
                    for k, v in sdata.items():
                        setattr(cfg.synergy.curves[sid], k, v)

    # Feedback overrides
    if "feedback" in overrides:
        fb = overrides["feedback"]
        if "default_weights" in fb:
            cfg.feedback.default_weights.update(fb["default_weights"])
        for k in ("learning_rate", "recalibration_window_days", "cache_ttl_seconds"):
            if k in fb:
                setattr(cfg.feedback, k, fb[k])

    # Agent overrides
    if "agent" in overrides:
        ag = overrides["agent"]
        for k in ("default_provider", "openai_model", "claude_model", "temperature", "max_tokens"):
            if k in ag:
                setattr(cfg.agent, k, ag[k])

    # Financial overrides
    if "financial" in overrides:
        fin = overrides["financial"]
        if "aggregation_weights" in fin:
            cfg.financial.aggregation_weights.update(fin["aggregation_weights"])
        if "improvement_divisor" in fin:
            cfg.financial.improvement_divisor = fin["improvement_divisor"]

    return cfg


# ============================================================
# PUBLIC API
# ============================================================

_config_cache: Dict[Tuple[str, int], VerticalConfig] = {}


def get_config(
    customer_id: Optional[int] = None,
    vertical: str = "platform",
    customer_overrides: Optional[Dict[str, Any]] = None,
) -> VerticalConfig:
    """
    Get the resolved config for a customer.

    Resolution order:
      1. Start with platform defaults
      2. Apply vertical overrides (datacenter / saas)
      3. Apply customer overrides (from Settings UI / DB)

    Results are cached per (vertical, customer_id) for the process lifetime.
    """
    cache_key = (vertical, customer_id or 0)

    if cache_key not in _config_cache or customer_overrides:
        # Step 1+2: Get vertical config (already includes platform defaults)
        base = VERTICAL_REGISTRY.get(vertical, PLATFORM_DEFAULTS)

        # Step 3: Apply customer overrides if provided
        if customer_overrides:
            resolved = _apply_customer_overrides(base, customer_overrides)
        else:
            resolved = copy.deepcopy(base)

        _config_cache[cache_key] = resolved

    return _config_cache[cache_key]


def clear_config_cache(customer_id: Optional[int] = None) -> None:
    """Clear config cache (call after Settings UI changes)."""
    if customer_id is not None:
        keys_to_remove = [k for k in _config_cache if k[1] == customer_id]
        for k in keys_to_remove:
            del _config_cache[k]
    else:
        _config_cache.clear()


def get_config_for_customer_from_db(customer_id: int) -> VerticalConfig:
    """
    Load vertical + overrides from DB and return resolved config.
    This is the main entry point for production code.
    """
    try:
        from extensions import db
        from models import CustomerConfig

        cc = CustomerConfig.query.filter_by(customer_id=customer_id).first()
        if not cc:
            return get_config(customer_id=customer_id, vertical="platform")

        vertical = cc.vertical or "saas"
        overrides = cc.config if isinstance(cc.config, dict) else {}

        return get_config(
            customer_id=customer_id,
            vertical=vertical,
            customer_overrides=overrides,
        )
    except Exception:
        return get_config(customer_id=customer_id, vertical="platform")


def export_config_schema() -> Dict[str, Any]:
    """
    Export the config schema for the Settings UI.
    Returns a dict of all tunable fields with their types, defaults, and descriptions.
    """
    return {
        "resource_pool": {
            "description": "FTE pool, hourly rates, and capacity constraints",
            "fields": {
                "roles": {
                    "type": "object",
                    "properties": {
                        role_id: {
                            "annual_hours": {"type": "number", "default": r.annual_hours},
                            "fte": {"type": "number", "default": r.fte},
                            "hourly_rate": {"type": "number", "default": r.hourly_rate},
                        }
                        for role_id, r in PLATFORM_DEFAULTS.resource_pool.roles.items()
                    },
                },
            },
        },
        "power_of_1": {
            "description": "Power of 1 economic model parameters",
            "fields": {
                "metrics": {
                    "type": "object",
                    "properties": {
                        mid: {
                            "baseline": {"type": "number", "default": m.baseline},
                            "annual_impact_per_pct": {"type": "number", "default": m.annual_impact_per_pct},
                            "total_investment": {"type": "number", "default": m.total_investment},
                        }
                        for mid, m in PLATFORM_DEFAULTS.power_of_1.metrics.items()
                    },
                },
                "total_investment": {"type": "number", "default": 247000},
                "compounding_multiplier": {"type": "number", "default": 0.15, "min": 0, "max": 1},
            },
        },
        "health_score": {
            "description": "Health scoring weights and thresholds",
            "fields": {
                "category_weights": {"type": "object", "default": PLATFORM_DEFAULTS.health_score.category_weights},
                "health_threshold_high": {"type": "number", "default": 67},
                "health_threshold_medium": {"type": "number", "default": 34},
            },
        },
        "playbooks": {
            "description": "Playbook trigger thresholds and automation settings",
            "fields": {
                "auto_approve_threshold": {"type": "number", "default": 0.80, "min": 0, "max": 1},
                "auto_reject_threshold": {"type": "number", "default": 0.40, "min": 0, "max": 1},
            },
        },
        "agent": {
            "description": "AI agent model selection and parameters",
            "fields": {
                "default_provider": {"type": "string", "enum": ["openai", "anthropic"], "default": "openai"},
                "temperature": {"type": "number", "default": 0.3, "min": 0, "max": 1},
                "max_tokens": {"type": "integer", "default": 3000, "min": 500, "max": 8000},
            },
        },
        "feedback": {
            "description": "Feedback loop and weight recalibration settings",
            "fields": {
                "learning_rate": {"type": "number", "default": 0.10, "min": 0.01, "max": 0.50},
                "recalibration_window_days": {"type": "integer", "default": 90, "min": 30, "max": 365},
            },
        },
    }
