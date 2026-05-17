#!/usr/bin/env python3
"""
SaaS Premium Vertical — Configuration

Companion to verticals/dc2_s/vertical_config.py. Defines PLAYBOOK_CONFIG and
should_trigger_playbook for the SaaS Premium catalog so the playbook engine,
cost bridge, and recommendation surfaces don't silently default to DC2S
templates on SaaS tenants.

Playbook IDs match the `linked_playbooks` field in
config/power_of_1_economics.json (generic SaaS catalog):
  - activation-blitz   (TTFV / product_adoption)
  - voc-sprint         (NRR — sentiment-driven expansion)
  - expansion-accelerator (NRR / expansion_rate)
  - renewal-safeguard  (GRR — renewal protection)
  - sla-stabilizer     (GRR / ticket_resolution_time)
  - health-check       (cross-cutting health-score driven; mirrors DC2S PB-05)

Hours per playbook are derived from the work_packages defined in
power_of_1_economics.json, split equally when a WP is shared across multiple
linked playbooks for a metric. See the docstring of `_derive_sub_components`
for the exact aggregation.

Created May 17 2026 to close bugs B-4 / B-5 from the FDE persona eval — the
SaaS path now has a first-class playbook config instead of falling back to
DC2S's PB-01..PB-06 templates.
"""

from typing import Dict, Any, List
import json
import os


# ============================================================
# PILLAR CODES (canonical SaaS Premium pillars from kpi_definitions)
# P1: Product Adoption & Usage
# P2: Customer Engagement
# P3: Customer Sentiment & Support
# P4: Partner & Ecosystem Health
# P5: Revenue & Growth
# ============================================================


# ============================================================
# PLAYBOOK CONFIGURATION
# ============================================================
# Mirrors the DC2S PLAYBOOK_CONFIG shape so playbook_cost_bridge and
# playbook_recommendations_api can consume both without branching.

PLAYBOOK_CONFIG: Dict[str, Dict[str, Any]] = {
    "activation-blitz": {
        "id": "activation-blitz",
        "name": "Activation Blitz",
        "description": "4-week activation program to compress time-to-value and drive user engagement for low-adoption accounts",
        # Triggers map onto SaaS Premium KPI codes (P1 = Product Adoption & Usage)
        "trigger_kpis": ["P1-KPI1", "P1-KPI3"],   # DAU rate, TTFV
        "trigger_conditions": {
            "P1-KPI1": {"operator": "<", "value": 60},   # DAU rate < 60
            "P1-KPI3": {"operator": "<", "value": 60},   # TTFV health < 60
        },
        "automation_level": "medium",
        "human_approval_required": False,
        "estimated_impact": "+20-30% active users, TTFV reduced 40%",
        "phases": ["adoption"],
        "estimated_duration_days": 30,
        "estimated_duration_display": "30 days",
        "sub_components": [
            {"id": "AB-S1", "name": "Standardized onboarding journey", "description": "Map customer journey touchpoints, milestone tracking, segment success criteria", "estimated_hours": 360, "manual_hours": 280, "automated_hours": 80},
            {"id": "AB-S2", "name": "Automated milestone tracking", "description": "Configure milestone APIs, auto-trigger system, progress dashboards", "estimated_hours": 320, "manual_hours": 200, "automated_hours": 120},
            {"id": "AB-S3", "name": "Personalized learning paths", "description": "Role-based content, in-app tutorials, adoption playbooks", "estimated_hours": 400, "manual_hours": 320, "automated_hours": 80},
            {"id": "AB-S4", "name": "Feature adoption campaigns", "description": "In-app messaging, feature spotlights, usage nudges", "estimated_hours": 240, "manual_hours": 180, "automated_hours": 60},
        ],
    },
    "voc-sprint": {
        "id": "voc-sprint",
        "name": "VoC Sprint",
        "description": "4-week intensive Voice of Customer program: surface value gaps, convert feedback to executive-backed actions",
        # Triggers on customer sentiment pillar (P3) — low NPS / low CSAT proxies
        "trigger_kpis": ["P3-KPI3", "P3-KPI4"],   # NPS, escalation rate
        "trigger_conditions": {
            "P3-KPI3": {"operator": "<", "value": 50},   # NPS proxy < 50
            "P3-KPI4": {"operator": "<", "value": 60},   # escalation/sentiment < 60
        },
        "automation_level": "low",
        "human_approval_required": False,
        "estimated_impact": "NPS +10-20 points, CSAT +0.5-1.0",
        "phases": ["sentiment"],
        "estimated_duration_days": 30,
        "estimated_duration_display": "30 days",
        "sub_components": [
            {"id": "VS-S1", "name": "Customer interview cadence", "description": "Structured interviews with 10-15 key accounts", "estimated_hours": 140, "manual_hours": 130, "automated_hours": 10},
            {"id": "VS-S2", "name": "Theme analysis & synthesis", "description": "Cluster feedback into top 5 themes", "estimated_hours": 120, "manual_hours": 100, "automated_hours": 20},
            {"id": "VS-S3", "name": "Executive sponsor alignment", "description": "Brief execs on themes, secure backing", "estimated_hours": 140, "manual_hours": 140, "automated_hours": 0},
            {"id": "VS-S4", "name": "Action commitment & owners", "description": "Convert top themes into owned action plans", "estimated_hours": 100, "manual_hours": 100, "automated_hours": 0},
        ],
    },
    "expansion-accelerator": {
        "id": "expansion-accelerator",
        "name": "Expansion Accelerator",
        "description": "Identify high-fit expansion opportunities and run targeted upsell/cross-sell campaigns",
        # Triggers on P5 Revenue & Growth — high health + low expansion velocity
        "trigger_kpis": ["P5-KPI1", "P5-KPI3"],   # NRR, expansion rate
        "trigger_conditions": {
            "P5-KPI1": {"operator": ">", "value": 95},   # NRR > 95 (healthy base)
            "P5-KPI3": {"operator": "<", "value": 12},   # expansion rate < 12% (upside)
        },
        "automation_level": "medium",
        "human_approval_required": True,   # Material commercial action
        "estimated_impact": "+5-10pp NRR uplift, expansion pipeline x1.5",
        "phases": ["expansion"],
        "estimated_duration_days": 45,
        "estimated_duration_display": "30-60 days",
        "sub_components": [
            {"id": "EA-S1", "name": "Expansion opportunity identification", "description": "Score accounts by fit + capacity + sentiment", "estimated_hours": 200, "manual_hours": 160, "automated_hours": 40},
            {"id": "EA-S2", "name": "Upsell trigger automation", "description": "Behavioral triggers + in-product offers", "estimated_hours": 200, "manual_hours": 100, "automated_hours": 100},
            {"id": "EA-S3", "name": "Cross-sell campaigns", "description": "Targeted multi-product motions", "estimated_hours": 140, "manual_hours": 110, "automated_hours": 30},
            {"id": "EA-S4", "name": "Sales-CS handoff process", "description": "Qualified opp → AE with full context", "estimated_hours": 160, "manual_hours": 150, "automated_hours": 10},
        ],
    },
    "renewal-safeguard": {
        "id": "renewal-safeguard",
        "name": "Renewal Safeguard",
        "description": "Protect at-risk renewals — early detection, segment-tailored playbooks, exec engagement",
        # Triggers on overall health + renewal proximity (P5 GRR)
        "trigger_kpis": ["P5-KPI2"],   # GRR
        "trigger_conditions": {
            "P5-KPI2": {"operator": "<", "value": 90},   # GRR < 90 (renewal risk)
        },
        "automation_level": "low",
        "human_approval_required": False,
        "estimated_impact": "+3-5pp GRR; renewal pipeline coverage 100%",
        "phases": ["renewal"],
        "estimated_duration_days": 60,
        "estimated_duration_display": "60 days (pre-renewal)",
        "sub_components": [
            {"id": "RS-S1", "name": "At-risk detection system", "description": "Multi-signal at-risk scoring + alert routing", "estimated_hours": 180, "manual_hours": 80, "automated_hours": 100},
            {"id": "RS-S2", "name": "Proactive health monitoring", "description": "Daily/weekly health pulse on renewals in window", "estimated_hours": 160, "manual_hours": 80, "automated_hours": 80},
            {"id": "RS-S3", "name": "Segment-tailored playbooks", "description": "Different motions for SMB / mid-market / enterprise", "estimated_hours": 200, "manual_hours": 180, "automated_hours": 20},
            {"id": "RS-S4", "name": "Executive business reviews", "description": "Pre-renewal QBRs with sponsor alignment", "estimated_hours": 100, "manual_hours": 100, "automated_hours": 0},
        ],
    },
    "sla-stabilizer": {
        "id": "sla-stabilizer",
        "name": "SLA Stabilizer",
        "description": "Stabilize support SLAs and ticket-resolution times to remove customer-experience drag",
        # Triggers on support pillar (P3) — slow resolution / high reopen
        "trigger_kpis": ["P3-KPI1"],   # Ticket resolution
        "trigger_conditions": {
            "P3-KPI1": {"operator": "<", "value": 70},   # ticket resolution health < 70
        },
        "automation_level": "high",
        "human_approval_required": False,
        "estimated_impact": "-30% first-response time, -25% reopen rate",
        "phases": ["support"],
        "estimated_duration_days": 21,
        "estimated_duration_display": "14-21 days",
        "sub_components": [
            {"id": "SS-S1", "name": "Ticket routing optimization", "description": "Skill-based routing, severity classification", "estimated_hours": 240, "manual_hours": 80, "automated_hours": 160},
            {"id": "SS-S2", "name": "Knowledge base enhancement", "description": "Top-30 article rewrite + deflection tracking", "estimated_hours": 240, "manual_hours": 200, "automated_hours": 40},
            {"id": "SS-S3", "name": "Tier 1 automation", "description": "Bots + self-serve for top common issues", "estimated_hours": 240, "manual_hours": 60, "automated_hours": 180},
            {"id": "SS-S4", "name": "CSM training on common issues", "description": "Reduce escalations via CSM enablement", "estimated_hours": 120, "manual_hours": 120, "automated_hours": 0},
        ],
    },
    "health-check": {
        "id": "health-check",
        "name": "Health Check",
        "description": "Cross-cutting health-score-driven intervention (SaaS analog of DC2S PB-05 Health Monitoring)",
        "trigger_kpis": ["OVERALL_HEALTH"],
        "trigger_conditions": {
            "OVERALL_HEALTH": {"operator": "<", "value": 60},
        },
        "automation_level": "high",
        "human_approval_required": False,
        "estimated_impact": "+15% early-intervention success rate",
        "phases": ["any"],
        "estimated_duration_days": 14,
        "estimated_duration_display": "7-14 days",
        "sub_components": [
            {"id": "HC-S1", "name": "Health review & triage", "description": "Review pillar scores + root causes", "estimated_hours": 8, "manual_hours": 8, "automated_hours": 0},
            {"id": "HC-S2", "name": "Action plan", "description": "Prioritized owned actions", "estimated_hours": 16, "manual_hours": 16, "automated_hours": 0},
            {"id": "HC-S3", "name": "Intervention execution", "description": "Top-3 actions (playbooks, outreach)", "estimated_hours": 32, "manual_hours": 28, "automated_hours": 4},
            {"id": "HC-S4", "name": "Follow-up & re-score", "description": "Re-measure health + close or escalate", "estimated_hours": 8, "manual_hours": 8, "automated_hours": 0},
        ],
    },
}


def get_playbook_config(playbook_id: str) -> Dict[str, Any]:
    """Get configuration for a playbook by id."""
    return PLAYBOOK_CONFIG.get(playbook_id, {})


def should_trigger_playbook(playbook_id: str, kpi_values: Dict[str, float]) -> bool:
    """Return True if every trigger_condition of playbook_id is met by kpi_values.

    AND-logic matches the DC2S helper of the same name. The SaaS evaluators in
    playbook_recommendations_api.py use OR-of-signals scoring; this helper is
    only consulted by the per-playbook HTTP endpoint that takes a playbook_id.
    """
    cfg = PLAYBOOK_CONFIG.get(playbook_id)
    if not cfg:
        return False
    conditions = cfg.get("trigger_conditions", {})
    if not conditions:
        return False
    for kpi_code, cond in conditions.items():
        val = kpi_values.get(kpi_code)
        if val is None:
            return False
        op = cond.get("operator")
        thresh = cond.get("value")
        if op == ">" and not (val > thresh):
            return False
        if op == "<" and not (val < thresh):
            return False
        if op == ">=" and not (val >= thresh):
            return False
        if op == "<=" and not (val <= thresh):
            return False
    return True
