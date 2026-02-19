#!/usr/bin/env python3
"""
Power of 1 Revenue Intelligence Model
=======================================
Encodes the complete "Power of 1" economic framework from the CS GrowthPulse deck.

Core principle: What does a 1% improvement in each key metric mean in dollars?
Every playbook action has a cost, every KPI improvement has a dollar value.
The platform proves non-linear scaling — same $247K investment, 4-6x returns.

Feature flag: 'revenue_intelligence' (per-customer toggle in Settings UI)

This module is the economic brain of the platform. Everything else —
action economics, financial projections, synergy engine — converts through here.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


# ============================================================
# METRIC CATEGORIES
# ============================================================

class MetricCategory(Enum):
    """Power of 1 metric categories — each has a different ROI profile"""
    FOUNDATION_INVESTMENT = "foundation_investment"   # Negative ROI at 1%, but required
    GROWTH_ACCELERATOR = "growth_accelerator"         # Highest ROI
    RETENTION_FOUNDATION = "retention_foundation"     # Protects existing revenue
    EFFICIENCY_BOOSTER = "efficiency_booster"         # Reduces cost, frees capacity
    VALUE_AMPLIFIER = "value_amplifier"               # Drives deeper usage
    REVENUE_DRIVER = "revenue_driver"                 # Direct expansion revenue


class ImpactType(Enum):
    """Dollar impact classification — 80/20 split per the deck"""
    REVENUE_INCREASE = "revenue_increase"
    COST_SAVINGS = "cost_savings"


class CSPillar(Enum):
    """The 5 CS Pillars that map to health score categories"""
    USAGE_ONBOARDING = "usage_onboarding"         # 30% weight
    SUPPORT_ENGAGEMENT = "support_engagement"      # 20% weight
    CUSTOMER_SENTIMENT = "customer_sentiment"      # 20% weight
    BUSINESS_OUTCOMES = "business_outcomes"        # 15% weight
    RELATIONSHIP_STRENGTH = "relationship_strength"  # 15% weight


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
# POWER OF 1 METRIC DEFINITIONS — ALL 6 FROM THE DECK
# ============================================================

@dataclass
class PowerOf1Metric:
    """Complete economic model for a single metric"""
    metric_id: str
    display_name: str
    baseline: float
    unit: str
    direction: str                      # "higher_is_better" or "lower_is_better"
    one_pct_move: float                 # What 1% improvement looks like in absolute terms
    annual_impact_per_pct: float        # Dollar value of 1% improvement
    total_investment: float             # Total cost to achieve 1% improvement
    cs_initiative_cost: float           # Human effort cost component
    platform_cost: float                # Our software cost component
    roi_at_1pct: float                  # ROI at 1% (can be negative for foundation)
    payback_months: float               # Months to break even
    category: MetricCategory
    primary_pillar: CSPillar
    secondary_pillars: List[CSPillar]
    linked_playbooks: List[str]         # Playbook IDs that improve this metric
    linked_kpi_codes: List[str]         # DC2_S or SaaS KPI codes
    total_hours: float                  # Total implementation hours
    quarters: List[str]                 # Implementation quarters
    impact_breakdown: Dict[ImpactType, float]   # Revenue vs cost savings split
    work_packages: List[WorkPackage]


# ============================================================
# THE COMPLETE POWER OF 1 TABLE — 6 METRICS
# ============================================================

POWER_OF_1_METRICS: Dict[str, PowerOf1Metric] = {

    # ── METRIC 1: TIME TO FIRST VALUE ──────────────────────────
    "TTFV": PowerOf1Metric(
        metric_id="TTFV",
        display_name="Time to First Value",
        baseline=30,
        unit="days",
        direction="lower_is_better",
        one_pct_move=0.3,               # 30 * 0.01 = 0.3 days
        annual_impact_per_pct=61250,
        total_investment=75500,
        cs_initiative_cost=59500,        # 75500 - estimated platform portion
        platform_cost=16000,
        roi_at_1pct=-0.19,              # Foundation investment — negative at 1%
        payback_months=14.8,
        category=MetricCategory.FOUNDATION_INVESTMENT,
        primary_pillar=CSPillar.USAGE_ONBOARDING,
        secondary_pillars=[CSPillar.CUSTOMER_SENTIMENT, CSPillar.RELATIONSHIP_STRENGTH],
        linked_playbooks=["activation-blitz"],
        linked_kpi_codes=["P1-KPI1"],    # Time-to-first-workload in DC2_S
        total_hours=1280,
        quarters=["Q1", "Q2"],
        impact_breakdown={
            ImpactType.REVENUE_INCREASE: 30000,  # Expansion from early value
            ImpactType.COST_SAVINGS: 31250,       # CLV optimization + churn prevention
        },
        work_packages=[
            WorkPackage(
                name="standardized_onboarding_journey",
                description="Map customer journey touchpoints, create milestone tracking, build success criteria by segment",
                hours=360,
                roles=RoleAllocation(csm=120, cs_ops=160, product=60, platform=20),
                deliverables=["Journey map", "Milestone tracker", "Segment success criteria"],
            ),
            WorkPackage(
                name="automated_milestone_tracking",
                description="Configure platform milestone APIs, build automated trigger system, create progress dashboards",
                hours=320,
                roles=RoleAllocation(cs_ops=120, platform=160, leadership=40),
                deliverables=["Milestone APIs", "Auto-trigger system", "Progress dashboards"],
            ),
            WorkPackage(
                name="personalized_learning_paths",
                description="Develop role-based content, create in-app tutorials, build adoption playbooks",
                hours=400,
                roles=RoleAllocation(csm=160, cs_ops=120, product=80, leadership=40),
                deliverables=["Role-based content", "In-app tutorials", "Adoption playbooks"],
            ),
            WorkPackage(
                name="success_criteria_definition",
                description="Define value metrics by segment, create measurement framework, build reporting templates",
                hours=200,
                roles=RoleAllocation(csm=40, cs_ops=80, product=20, platform=40, leadership=20),
                deliverables=["Value metrics", "Measurement framework", "Report templates"],
            ),
        ],
    ),

    # ── METRIC 2: NET REVENUE RETENTION ────────────────────────
    "NRR": PowerOf1Metric(
        metric_id="NRR",
        display_name="Net Revenue Retention",
        baseline=105,
        unit="percent",
        direction="higher_is_better",
        one_pct_move=1.05,              # 105 * 0.01 = 1.05 points
        annual_impact_per_pct=105000,
        total_investment=50000,
        cs_initiative_cost=38000,
        platform_cost=12000,
        roi_at_1pct=2.10,               # 210% — highest ROI metric
        payback_months=5.7,
        category=MetricCategory.GROWTH_ACCELERATOR,
        primary_pillar=CSPillar.BUSINESS_OUTCOMES,
        secondary_pillars=[CSPillar.USAGE_ONBOARDING, CSPillar.RELATIONSHIP_STRENGTH],
        linked_playbooks=["expansion-accelerator", "voc-sprint"],
        linked_kpi_codes=["EX-KPI1", "EX-KPI2", "CH-KPI3"],
        total_hours=1000,
        quarters=["Q2", "Q3"],
        impact_breakdown={
            ImpactType.REVENUE_INCREASE: 105000,  # Pure expansion revenue
            ImpactType.COST_SAVINGS: 0,
        },
        work_packages=[
            WorkPackage(
                name="expansion_opportunity_identification",
                description="Build scoring model for expansion readiness, map account whitespace, segment opportunities",
                hours=280,
                roles=RoleAllocation(csm=80, cs_ops=120, platform=60, leadership=20),
                deliverables=["Expansion scoring model", "Whitespace map", "Opportunity segments"],
            ),
            WorkPackage(
                name="upsell_trigger_automation",
                description="Configure usage-based triggers, build expansion alert system, create CSM notification workflows",
                hours=240,
                roles=RoleAllocation(cs_ops=120, platform=80, leadership=40),
                deliverables=["Usage triggers", "Expansion alerts", "CSM notifications"],
            ),
            WorkPackage(
                name="cross_sell_campaigns",
                description="Design cross-sell playbooks, build campaign templates, train CSMs on consultative selling",
                hours=280,
                roles=RoleAllocation(csm=160, cs_ops=80, product=20, leadership=20),
                deliverables=["Cross-sell playbooks", "Campaign templates", "CSM training"],
            ),
            WorkPackage(
                name="value_realization_reviews",
                description="Create QBR value framework, build ROI calculators, develop executive presentation templates",
                hours=200,
                roles=RoleAllocation(csm=160, cs_ops=40),
                deliverables=["QBR value framework", "ROI calculators", "Exec presentations"],
            ),
        ],
    ),

    # ── METRIC 3: GROSS REVENUE RETENTION ──────────────────────
    "GRR": PowerOf1Metric(
        metric_id="GRR",
        display_name="Gross Revenue Retention",
        baseline=85,
        unit="percent",
        direction="higher_is_better",
        one_pct_move=0.85,              # 85 * 0.01 = 0.85 points
        annual_impact_per_pct=100000,
        total_investment=60000,
        cs_initiative_cost=48000,
        platform_cost=12000,
        roi_at_1pct=1.67,               # 167%
        payback_months=7.2,
        category=MetricCategory.RETENTION_FOUNDATION,
        primary_pillar=CSPillar.BUSINESS_OUTCOMES,
        secondary_pillars=[CSPillar.SUPPORT_ENGAGEMENT, CSPillar.CUSTOMER_SENTIMENT],
        linked_playbooks=["renewal-safeguard", "sla-stabilizer"],
        linked_kpi_codes=["CH-KPI1", "CH-KPI2", "OS-KPI3"],
        total_hours=1280,
        quarters=["Q1", "Q2", "Q3", "Q4"],
        impact_breakdown={
            ImpactType.REVENUE_INCREASE: 100000,  # Retained revenue = protected revenue
            ImpactType.COST_SAVINGS: 0,
        },
        work_packages=[
            WorkPackage(
                name="at_risk_detection_system",
                description="Build multi-signal risk scoring, configure early warning triggers, create risk dashboards",
                hours=360,
                roles=RoleAllocation(csm=40, cs_ops=160, platform=120, leadership=40),
                deliverables=["Risk scoring model", "Early warning triggers", "Risk dashboards"],
            ),
            WorkPackage(
                name="proactive_health_monitoring",
                description="Deploy continuous health checks, build anomaly detection, create automated CSM alerts",
                hours=320,
                roles=RoleAllocation(csm=120, cs_ops=120, platform=80),
                deliverables=["Health check automation", "Anomaly detection", "CSM alert system"],
            ),
            WorkPackage(
                name="renewal_playbooks_by_segment",
                description="Design segment-specific renewal strategies, build playbook templates, create renewal timeline automation",
                hours=400,
                roles=RoleAllocation(csm=240, cs_ops=120, leadership=40),
                deliverables=["Segment renewal strategies", "Playbook templates", "Timeline automation"],
            ),
            WorkPackage(
                name="executive_business_reviews",
                description="Create EBR frameworks, build automated deck generation, develop success story templates",
                hours=200,
                roles=RoleAllocation(csm=80, cs_ops=80, product=20, leadership=20),
                deliverables=["EBR framework", "Auto deck generation", "Success story templates"],
            ),
        ],
    ),

    # ── METRIC 4: TICKET RESOLUTION TIME ───────────────────────
    "ticket_resolution_time": PowerOf1Metric(
        metric_id="ticket_resolution_time",
        display_name="Ticket Resolution Time",
        baseline=48,
        unit="hours",
        direction="lower_is_better",
        one_pct_move=0.48,              # 48 * 0.01 = 0.48 hours
        annual_impact_per_pct=38000,
        total_investment=26000,
        cs_initiative_cost=20000,
        platform_cost=6000,
        roi_at_1pct=1.46,               # 146%
        payback_months=8.2,
        category=MetricCategory.EFFICIENCY_BOOSTER,
        primary_pillar=CSPillar.SUPPORT_ENGAGEMENT,
        secondary_pillars=[CSPillar.CUSTOMER_SENTIMENT],
        linked_playbooks=["sla-stabilizer"],
        linked_kpi_codes=["OS-KPI1", "OS-KPI2"],
        total_hours=840,
        quarters=["Q2", "Q3"],
        impact_breakdown={
            ImpactType.REVENUE_INCREASE: 0,
            ImpactType.COST_SAVINGS: 38000,       # Pure efficiency savings
        },
        work_packages=[
            WorkPackage(
                name="ticket_routing_optimization",
                description="Analyze routing patterns, build skill-based routing, optimize escalation paths",
                hours=240,
                roles=RoleAllocation(cs_ops=160, platform=60, leadership=20),
                deliverables=["Routing analysis", "Skill-based routing", "Escalation optimization"],
            ),
            WorkPackage(
                name="knowledge_base_enhancement",
                description="Audit existing KB, create missing articles, build self-service workflows",
                hours=240,
                roles=RoleAllocation(csm=80, cs_ops=80, product=80),
                deliverables=["KB audit report", "New KB articles", "Self-service workflows"],
            ),
            WorkPackage(
                name="tier_1_automation",
                description="Build AI-powered tier-1 triage, create auto-response templates, deploy chatbot deflection",
                hours=240,
                roles=RoleAllocation(cs_ops=80, product=80, platform=60, leadership=20),
                deliverables=["AI triage system", "Auto-response templates", "Chatbot deflection"],
            ),
            WorkPackage(
                name="csm_training_common_issues",
                description="Identify top 20 recurring issues, create resolution playbooks, train CSM team",
                hours=120,
                roles=RoleAllocation(csm=40, cs_ops=80),
                deliverables=["Top 20 issue library", "Resolution playbooks", "Training materials"],
            ),
        ],
    ),

    # ── METRIC 5: PRODUCT ADOPTION RATE ────────────────────────
    "product_adoption": PowerOf1Metric(
        metric_id="product_adoption",
        display_name="Product Adoption Rate",
        baseline=65,
        unit="percent",
        direction="higher_is_better",
        one_pct_move=0.65,              # 65 * 0.01 = 0.65 points
        annual_impact_per_pct=25000,
        total_investment=21000,
        cs_initiative_cost=15000,
        platform_cost=6000,
        roi_at_1pct=1.19,               # 119%
        payback_months=10.1,
        category=MetricCategory.VALUE_AMPLIFIER,
        primary_pillar=CSPillar.USAGE_ONBOARDING,
        secondary_pillars=[CSPillar.CUSTOMER_SENTIMENT],
        linked_playbooks=["activation-blitz"],
        linked_kpi_codes=["AI-KPI2", "AI-KPI3", "DV-KPI1"],
        total_hours=800,
        quarters=["Q3", "Q4"],
        impact_breakdown={
            ImpactType.REVENUE_INCREASE: 25000,   # Adoption uplift drives expansion
            ImpactType.COST_SAVINGS: 0,
        },
        work_packages=[
            WorkPackage(
                name="in_app_training_tutorials",
                description="Design interactive walkthroughs, build feature discovery prompts, create onboarding tours",
                hours=240,
                roles=RoleAllocation(product=120, cs_ops=80, platform=40),
                deliverables=["Interactive walkthroughs", "Feature discovery prompts", "Onboarding tours"],
            ),
            WorkPackage(
                name="feature_adoption_campaigns",
                description="Build adoption email sequences, create in-app nudges, design feature spotlight programs",
                hours=240,
                roles=RoleAllocation(csm=120, cs_ops=80, product=40),
                deliverables=["Adoption email sequences", "In-app nudges", "Feature spotlights"],
            ),
            WorkPackage(
                name="usage_pattern_analysis",
                description="Deploy usage analytics, identify adoption gaps, build cohort analysis dashboards",
                hours=200,
                roles=RoleAllocation(csm=40, cs_ops=80, platform=80),
                deliverables=["Usage analytics", "Adoption gap report", "Cohort dashboards"],
            ),
            WorkPackage(
                name="quarterly_feature_showcases",
                description="Create feature demo library, build webinar program, design customer advisory board",
                hours=120,
                roles=RoleAllocation(csm=80, cs_ops=40),
                deliverables=["Feature demo library", "Webinar program", "Advisory board framework"],
            ),
        ],
    ),

    # ── METRIC 6: EXPANSION RATE ───────────────────────────────
    "expansion_rate": PowerOf1Metric(
        metric_id="expansion_rate",
        display_name="Expansion Rate",
        baseline=20,
        unit="percent",
        direction="higher_is_better",
        one_pct_move=0.20,              # 20 * 0.01 = 0.20 points
        annual_impact_per_pct=20000,
        total_investment=14500,
        cs_initiative_cost=12000,
        platform_cost=2500,
        roi_at_1pct=1.38,               # 138%
        payback_months=8.7,
        category=MetricCategory.REVENUE_DRIVER,
        primary_pillar=CSPillar.BUSINESS_OUTCOMES,
        secondary_pillars=[CSPillar.USAGE_ONBOARDING, CSPillar.RELATIONSHIP_STRENGTH],
        linked_playbooks=["expansion-accelerator"],
        linked_kpi_codes=["EX-KPI1", "EX-KPI3"],
        total_hours=640,
        quarters=["Q3", "Q4"],
        impact_breakdown={
            ImpactType.REVENUE_INCREASE: 20000,   # Direct expansion revenue
            ImpactType.COST_SAVINGS: 0,
        },
        work_packages=[
            WorkPackage(
                name="upsell_trigger_automations",
                description="Build usage threshold triggers, create expansion signal detection, deploy alert workflows",
                hours=200,
                roles=RoleAllocation(cs_ops=80, platform=80, leadership=40),
                deliverables=["Usage threshold triggers", "Expansion signals", "Alert workflows"],
            ),
            WorkPackage(
                name="expansion_pipeline_management",
                description="Build expansion opportunity tracker, create pipeline dashboards, design handoff workflows",
                hours=200,
                roles=RoleAllocation(csm=120, cs_ops=80),
                deliverables=["Opportunity tracker", "Pipeline dashboards", "Handoff workflows"],
            ),
            WorkPackage(
                name="sales_cs_handoff_process",
                description="Define handoff criteria, build shared qualification framework, create SLA between teams",
                hours=160,
                roles=RoleAllocation(csm=80, cs_ops=40, leadership=40),
                deliverables=["Handoff criteria", "Qualification framework", "Team SLA"],
            ),
            WorkPackage(
                name="usage_based_pricing_signals",
                description="Identify pricing trigger patterns, build consumption dashboards, create pricing recommendations",
                hours=80,
                roles=RoleAllocation(cs_ops=40, product=40),
                deliverables=["Pricing trigger patterns", "Consumption dashboards", "Pricing recommendations"],
            ),
        ],
    ),
}


# ============================================================
# METRIC CASCADE / COMPOUNDING FLYWHEEL
# ============================================================
# Metrics are NOT independent. Improving one cascades to others.
# Conservative 15% compounding (industry benchmarks: 20-40%).

METRIC_CASCADES = {
    "TTFV": {
        "amplifies": [
            {
                "target_metric": "product_adoption",
                "multiplier": 0.35,
                "mechanism": "Faster onboarding compresses time-to-adoption",
                "lag_weeks": 4,
            },
            {
                "target_metric": "expansion_rate",
                "multiplier": 0.40,
                "mechanism": "Early value realization opens expansion conversations sooner",
                "lag_weeks": 8,
            },
        ]
    },
    "GRR": {
        "amplifies": [
            {
                "target_metric": "NRR",
                "multiplier": 0.25,
                "mechanism": "Retained customer base is the expandable base — can't expand churned customers",
                "lag_weeks": 4,
            },
        ]
    },
    "ticket_resolution_time": {
        "amplifies": [
            {
                "target_metric": "product_adoption",
                "multiplier": 0.15,
                "mechanism": "Freed CSM capacity enables proactive adoption work",
                "lag_weeks": 6,
            },
            {
                "target_metric": "GRR",
                "multiplier": 0.10,
                "mechanism": "Better support experience reduces churn triggers",
                "lag_weeks": 4,
            },
        ]
    },
    "product_adoption": {
        "amplifies": [
            {
                "target_metric": "NRR",
                "multiplier": 0.20,
                "mechanism": "Higher adoption creates natural expansion demand",
                "lag_weeks": 8,
            },
            {
                "target_metric": "GRR",
                "multiplier": 0.15,
                "mechanism": "Deeply adopted products are stickier",
                "lag_weeks": 4,
            },
        ]
    },
    "NRR": {
        "amplifies": []  # Terminal metric — expansion revenue is the output
    },
    "expansion_rate": {
        "amplifies": [
            {
                "target_metric": "NRR",
                "multiplier": 0.30,
                "mechanism": "Higher expansion rate directly drives net revenue retention",
                "lag_weeks": 4,
            },
        ]
    },
}

# Conservative compounding cap (industry 20-40%, we use 15%)
COMPOUNDING_MULTIPLIER = 0.15


# ============================================================
# NON-LINEAR SCALING MODEL
# ============================================================
# Same $247K investment, exponentially higher returns at 4% and 6%.
# This is the "Power of Execution" thesis.

SCALING_SCENARIOS = {
    "1_pct": {
        "improvement_pct": 1,
        "label": "Budget (Conservative)",
        "direct_impact": 349250,         # Sum of 6 metrics at 1%
        "compounding_impact": 52388,     # +15%
        "total_impact": 401638,
        "investment": 247000,
        "year_1_roi": 0.63,              # 63%
        "payback_months": 7.4,
        "three_year_net": None,          # Break-even territory
    },
    "4_pct": {
        "improvement_pct": 4,
        "label": "Target (Industry Leading)",
        "direct_impact": 1397000,
        "compounding_impact": 209550,
        "total_impact": 1607000,
        "investment": 247000,            # SAME investment
        "year_1_roi": 5.50,             # 550%
        "payback_months": 1.8,
        "three_year_net": 4500000,
    },
    "6_pct": {
        "improvement_pct": 6,
        "label": "Celebrate (World Class)",
        "direct_impact": 2095650,
        "compounding_impact": 314348,
        "total_impact": 2410000,
        "investment": 247000,            # STILL the same investment
        "year_1_roi": 8.76,             # 876%
        "payback_months": 1.2,
        "three_year_net": 7000000,
    },
}


# ============================================================
# INVESTMENT SUMMARY
# ============================================================

INVESTMENT_SUMMARY = {
    "total_investment": 247000,
    "cs_initiatives": 197000,            # 80% — human effort
    "platform_cost": 50000,              # 20% — our software
    "total_hours": 5840,
    "total_fte": 2.81,
    "revenue_increase_pct": 0.802,       # 80.2% of impact is revenue
    "cost_savings_pct": 0.198,           # 19.8% is cost savings
    "revenue_increase_total": 280000,
    "cost_savings_total": 69250,
    "direct_impact_total": 349250,
    "compounding_effect": 52388,
    "total_year_1_impact": 401638,
}


# ============================================================
# 3-YEAR TIME ECONOMICS (from Slide 21)
# ============================================================
# "The platform doesn't ADD work — it eliminates 80% of manual CS tasks"

TIME_ECONOMICS = {
    "year_1": {
        "label": "Building the Infrastructure",
        "hours_invested": 5840,
        "breakdown": {
            "platform_auto_setup": {"hours": 1840, "pct": 0.31, "note": "AI does the work"},
            "one_time_playbooks": {"hours": 2400, "pct": 0.41, "note": "Build once, run forever"},
            "reduced_execution": {"hours": 1600, "pct": 0.28, "note": "80% less vs manual"},
        },
        "hours_saved": 2920,             # Saves 2,920 hours in Year 1 alone
        "net_savings": -2920,            # Net negative in Year 1 (investment year)
    },
    "year_2": {
        "label": "Maintenance Only",
        "hours_invested": 800,
        "hours_saved": 8760,
        "net_savings": 7960,
    },
    "year_3": {
        "label": "Optimization",
        "hours_invested": 600,
        "hours_saved": 10950,
        "net_savings": 10350,
    },
    "three_year_totals": {
        "hours_invested": 7240,
        "hours_saved": 22630,
        "net_savings": 15390,
        "time_roi_multiplier": 3.1,      # 3.1x time savings
        "fte_equivalent_freed": 7.4,     # Equivalent to freeing 7.4 FTEs
    },
}


# ============================================================
# IMPLEMENTATION PHASES (3-Phase GrowthPulse Approach)
# ============================================================

IMPLEMENTATION_PHASES = {
    "foundational": {
        "label": "Foundational",
        "weeks": [1, 2],
        "quarter": "Q1",
        "activity_level": "high",
        "streams": {
            "platform_setup": "Setup Complete",
            "data_integration": "CRM, Support connected",
            "ttfv_playbooks": "Build",
            "health_scoring": "Model Build",
            "nrr_grr_programs": "Design",
            "support_automation": "Plan",
            "adoption_campaigns": None,    # Not started
            "expansion_pipeline": None,    # Not started
        },
    },
    "intelligence": {
        "label": "Intelligence",
        "weeks": [3, 6],
        "quarter": "Q1",
        "activity_level": "medium",
        "streams": {
            "platform_setup": "Config",
            "data_integration": "Product data",
            "ttfv_playbooks": "Deploy & Test",
            "health_scoring": "Calibrate",
            "nrr_grr_programs": "Launch",
            "support_automation": "Build KB",
            "adoption_campaigns": "Design",
            "expansion_pipeline": "Design",
        },
    },
    "excellence": {
        "label": "Excellence",
        "weeks": [7, 12],
        "quarter": "Q1-Q2",
        "activity_level": "low",
        "streams": {
            "platform_setup": "Monitor",
            "data_integration": "Monitor",
            "ttfv_playbooks": "Optimize",
            "health_scoring": "Refine v2",
            "nrr_grr_programs": "Scale",
            "support_automation": "Tier-1 Auto",
            "adoption_campaigns": "Launch",
            "expansion_pipeline": "Build",
        },
    },
    "optimization": {
        "label": "Optimization",
        "weeks": [13, 52],
        "quarter": "Q2-Q4",
        "activity_level": "minimal",
        "streams": {
            "platform_setup": "Monitor",
            "data_integration": "Monitor",
            "ttfv_playbooks": "Sustain",
            "health_scoring": "Monitor",
            "nrr_grr_programs": "Optimize",
            "support_automation": "Refine",
            "adoption_campaigns": "Iterate",
            "expansion_pipeline": "Scale",
        },
    },
}


# ============================================================
# PLATFORM AUTOMATION DELIVERY TIMELINE (from Slide 20)
# ============================================================

AUTOMATION_TIMELINE = {
    "week_1_2": {
        "label": "Instant Insights",
        "capabilities": [
            "Real-time dashboard (all 6 metrics)",
            "AI health scores (100 customers)",
            "Predictive churn alerts",
            "Automated milestone tracking",
            "Integration with CRM/Support/Product",
        ],
    },
    "week_3_6": {
        "label": "Auto-Execution",
        "capabilities": [
            "At-risk customer alerts",
            "Expansion opportunity flags",
            "Automated email workflows",
            "QBR deck generation (AI)",
            "Support ticket routing (AI)",
        ],
    },
    "week_7_12": {
        "label": "Full Automation",
        "capabilities": [
            "24 playbooks running auto",
            "Daily health monitoring",
            "Weekly AI reports",
            "Auto-triggered interventions",
            "Continuous optimization",
        ],
    },
    "automation_impact": {
        "manual_monitoring_reduction_pct": 92,
        "hours_saved_per_qbr": 3.5,
        "annual_hours_saved": 4380,
    },
}


# ============================================================
# QUARTERLY CHECKPOINTS (Year 1 Roadmap)
# ============================================================

QUARTERLY_CHECKPOINTS = {
    "Q1": {
        "label": "Foundation & Launch",
        "month_range": "Jan-Mar",
        "targets": {
            "TTFV": {"value": 30.0, "milestone": "baseline"},
            "platform": {"milestone": "go_live"},
            "health_model": {"milestone": "built"},
        },
        "review": "Baseline established",
    },
    "Q2": {
        "label": "Intelligence & Early Wins",
        "month_range": "Apr-Jun",
        "targets": {
            "TTFV": {"value": 29.5, "milestone": "optimizing"},
            "NRR": {"value": 105.5, "milestone": "launched"},
            "ticket_resolution_time": {"value": 47.5, "milestone": "improved"},
            "platform": {"milestone": "dashboards_validated"},
        },
        "review": "First Review",
    },
    "Q3": {
        "label": "Scale & Expand",
        "month_range": "Jul-Sep",
        "targets": {
            "TTFV": {"value": 29.0, "milestone": "refined"},
            "GRR": {"value": 85.5, "milestone": "deployed"},
            "expansion_rate": {"value": 20.1, "milestone": "pipeline_built"},
            "platform": {"milestone": "health_v2_live"},
        },
        "review": "Mid-Year Review",
    },
    "Q4": {
        "label": "Optimize & Validate ROI",
        "month_range": "Oct-Dec",
        "targets": {
            "TTFV": {"value": 29.0, "milestone": "complete"},
            "NRR": {"value": "targets_hit", "milestone": "optimized"},
            "GRR": {"value": "targets_hit", "milestone": "optimized"},
            "product_adoption": {"value": 65.65, "milestone": "campaigns_complete"},
            "expansion_rate": {"value": 20.2, "milestone": "full_auto"},
            "overall_roi": {"value": 0.63, "milestone": "63% ROI validated"},
        },
        "review": "Year-End Review",
    },
}


# ============================================================
# CS PILLAR WEIGHTS (maps to health score categories)
# ============================================================

CS_PILLAR_WEIGHTS = {
    CSPillar.USAGE_ONBOARDING: 0.30,
    CSPillar.SUPPORT_ENGAGEMENT: 0.20,
    CSPillar.CUSTOMER_SENTIMENT: 0.20,
    CSPillar.BUSINESS_OUTCOMES: 0.15,
    CSPillar.RELATIONSHIP_STRENGTH: 0.15,
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
        Dict with direct_impact, compounding_impact, total_impact, roi, breakdown
    """
    metric = POWER_OF_1_METRICS.get(metric_id)
    if not metric:
        return {"error": f"Unknown metric: {metric_id}"}

    # Scale factor: if account ARR differs from assumed $10M base
    arr_scale = 1.0
    if account_arr is not None:
        arr_scale = account_arr / 10_000_000  # Deck assumes ~$10M ARR base

    direct_impact = metric.annual_impact_per_pct * improvement_pct * arr_scale

    # Calculate compounding via cascade
    compounding_impact = _calculate_cascade_impact(metric_id, improvement_pct, arr_scale)

    total_impact = direct_impact + compounding_impact

    # Investment scales linearly with improvement only for the first 1%.
    # Beyond 1%, the platform absorbs the incremental effort (non-linear scaling thesis).
    investment = metric.total_investment  # Fixed — same cost regardless of improvement %

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
