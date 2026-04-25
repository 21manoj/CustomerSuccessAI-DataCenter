#!/usr/bin/env python3
"""
claude_driven_generate_backtest.py
===================================

Generate 20 synthetic CS Pulse customers (10 accounts each) for
NRR+ROI forecast backtest and sales-demo coverage.

Each tenant = one Claude API call producing:
  - 4 CSVs the customer uploads at onboarding
      (account_details, kpi_measurements, qualitative_signals, outcomes)
  - Sidecar `future_truth` per account:
      - Organic 6-month NRR outcome (what customer achieves WITHOUT CS Pulse)
      - Organic 6-month ROI outcome (what their own CS team delivers for
        what they spend)

Pipeline code NEVER reads the sidecar — only the pytest harness does at
grading time. Wizard B's `without_cs_pulse_*` forecasts are compared
against the sidecar. The `with_cs_pulse_*` forecasts are math projections
from MOD-005/006 — anchored by baseline accuracy but not directly testable.

Output: scripts/datasets/claude_driven_backtest_v1.json

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    python3 scripts/claude_driven_generate_backtest.py

Cost: ~$2 for 200 accounts. Runtime: ~3 min wall clock.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

try:
    import anthropic
except ImportError:
    print("ERROR: pip install anthropic", file=sys.stderr)
    sys.exit(1)

MODEL = "claude-sonnet-4-20250514"


# ════════════════════════════════════════════════════════════════════
# TENANT SPECS — 20 dimension-grid cells
# ════════════════════════════════════════════════════════════════════
# Each spec configures one synthetic customer. Dimensions collectively
# cover the test surface the load-driver's manifests span, without
# importing any manifest's specific arc patterns.
# Fields: (idx, kpi_tier, n_accts, vertical_focus, arc_phase,
#          health_skew, renewal_window)

TENANT_SPECS = [
    ( 1, "starter_9",      5, "fintech",     "baseline",      "balanced",        "mid"),
    ( 2, "predictive_11",  5, "healthtech",  "4phase",        "crisis_heavy",    "near"),
    ( 3, "starter_9",      5, "mixed",       "intervention",  "stable_heavy",    "long"),
    ( 4, "predictive_11",  5, "devtools",    "baseline",      "expansion_heavy", "near"),
    ( 5, "predictive_11",  5, "legal_tech",  "deterioration", "crisis_heavy",    "mid"),
    ( 6, "starter_9",      5, "adtech",      "4phase",        "balanced",        "long"),
    ( 7, "predictive_11",  5, "mixed",       "intervention",  "balanced",        "near"),
    ( 8, "starter_9",      5, "retail_tech", "baseline",      "stable_heavy",    "long"),
    ( 9, "predictive_11",  5, "hrtech",      "4phase",        "churn_heavy",     "mid"),
    (10, "starter_9",      5, "edtech",      "baseline",      "expansion_heavy", "near"),
    (11, "predictive_11",  5, "fintech",     "intervention",  "crisis_heavy",    "mid"),
    (12, "starter_9",      5, "mixed",       "deterioration", "stable_heavy",    "long"),
    (13, "predictive_11",  5, "logistics",   "4phase",        "balanced",        "near"),
    (14, "starter_9",      5, "healthtech",  "baseline",      "churn_heavy",     "mid"),
    (15, "predictive_11",  5, "devtools",    "intervention",  "expansion_heavy", "long"),
    (16, "starter_9",      5, "mixed",       "4phase",        "balanced",        "mid"),
    (17, "predictive_11",  5, "adtech",      "deterioration", "stable_heavy",    "near"),
    (18, "starter_9",      5, "legal_tech",  "baseline",      "crisis_heavy",    "long"),
    (19, "predictive_11",  5, "edtech",      "intervention",  "balanced",        "mid"),
    (20, "starter_9",      5, "hrtech",      "4phase",        "churn_heavy",     "near"),
]


# ════════════════════════════════════════════════════════════════════
# PINNED TENANT SPECS — slide-deck-matched demo customer
# ════════════════════════════════════════════════════════════════════
# Unlike TENANT_SPECS (which give Claude free rein over account names,
# ARRs, and health trajectories), PINNED specs mirror the slide-deck
# SaaS demo exactly. Claude's job shrinks to: fill in monthly KPI values
# that produce the pinned 6-month health arcs under starter_9 weights,
# plus signals/outcomes/sidecar consistent with each account's narrative.
#
# Effect on the sales story:
#   The 10 accounts in CS_Pulse_VP_CS_Tutorial.pptx become tenant 21 of
#   the backtest dataset. Wizard B's forecast for Drift/Relay/Horizon
#   inside the demo is now a backtest data point — ±MAPE error bar
#   attaches directly to the forecast the buyer sees on the slide.

PINNED_TENANT_PHOENIX = {
    "tenant_idx": 21,
    "tenant_id": "phoenix-saas-demo",
    "kpi_tier": "starter_9",
    "vertical_focus": "saas_mixed",
    "narrative": "Slide-deck-mirror: 10 SaaS accounts, $48.5M ARR. "
                 "Matches CS_Pulse_VP_CS_Tutorial.pptx + CSM deck.",
    # Today is 2026-04-24. Health arc months correspond to 2025-11..2026-04
    # (last 6 of the 12 KPI history months). Months 2025-05..2025-10 let
    # Claude pick pre-trajectory values consistent with the arc direction.
    "pinned_accounts": [
        {
            "name": "Drift Analytics",           "arr_usd": 1_800_000,
            "health_arc_nov_apr": [49, 48, 45, 43, 42, 42],
            "arc_label": "silent_churn_champion_loss",
            "difficulty": "HARD",
            "renewal_date": "2026-03-01",  # OVERDUE in the deck
            "region": "NA-East",
            "industry": "analytics_saas",
            "assigned_csm": "Emily Park",
            "narrative": "Champion VP Engineering departed Apr 12; adoption "
                         "collapse; renewal overdue; silent churn pattern.",
            "organic_nrr_outcome": "churned",
            "organic_nrr_pct_hint": 0,
        },
        {
            "name": "Relay Healthcare",          "arr_usd": 3_800_000,
            "health_arc_nov_apr": [44, 46, 49, 52, 56, 56],
            "arc_label": "exec_sponsor_recovery",
            "difficulty": "MEDIUM",
            "renewal_date": "2026-04-15",
            "region": "NA-East",
            "industry": "healthtech",
            "assigned_csm": "Sarah Chen",
            "narrative": "Exec sponsor loss in Q4; new sponsor onboarded "
                         "Feb; recovery trajectory but renewal at risk.",
            "organic_nrr_outcome": "contracted",
            "organic_nrr_pct_hint": 85,
        },
        {
            "name": "Horizon Fintech",           "arr_usd": 7_200_000,
            "health_arc_nov_apr": [51, 50, 52, 56, 61, 61],
            "arc_label": "competitive_recovery",
            "difficulty": "MEDIUM",
            "renewal_date": "2026-06-15",
            "region": "NA-West",
            "industry": "fintech",
            "assigned_csm": "Sarah Chen",
            "narrative": "Competitor evaluation in Q4; client won back "
                         "via feature parity; renewal trending favorable.",
            "organic_nrr_outcome": "renewed_flat",
            "organic_nrr_pct_hint": 100,
        },
        {
            "name": "Stratos Logistics",         "arr_usd": 5_800_000,
            "health_arc_nov_apr": [68, 65, 62, 60, 58, 58],
            "arc_label": "deployment_stall",
            "difficulty": "MEDIUM",
            "renewal_date": "2026-05-01",
            "region": "EU-West",
            "industry": "logistics_saas",
            "assigned_csm": "Marcus Rivera",
            "narrative": "Phase-2 deployment stalled on integration; "
                         "usage flat; renewal at risk 10d out.",
            "organic_nrr_outcome": "contracted",
            "organic_nrr_pct_hint": 80,
        },
        {
            "name": "Canopy EdTech",             "arr_usd": 4_200_000,
            "health_arc_nov_apr": [67, 63, 61, 59, 57, 57],
            "arc_label": "qbr_overdue_drift",
            "difficulty": "MEDIUM",
            "renewal_date": "2026-08-30",
            "region": "NA-East",
            "industry": "edtech",
            "assigned_csm": "Marcus Rivera",
            "narrative": "QBR 120 days overdue; adoption slowly declining "
                         "on free-seat expansion; P1 ticket clustering.",
            "organic_nrr_outcome": "contracted",
            "organic_nrr_pct_hint": 88,
        },
        {
            "name": "Orbit Commerce",            "arr_usd": 8_200_000,
            "health_arc_nov_apr": [82, 85, 85, 83, 83, 83],
            "arc_label": "expansion_ready",
            "difficulty": "EASY",
            "renewal_date": "2026-09-15",
            "region": "NA-West",
            "industry": "ecommerce_saas",
            "assigned_csm": "Sarah Chen",
            "narrative": "Usage 140% of plan; new business unit onboarding; "
                         "stakeholder expansion signals strong.",
            "organic_nrr_outcome": "renewed_expansion",
            "organic_nrr_pct_hint": 118,
        },
        {
            "name": "Nexus Enterprise",          "arr_usd": 6_500_000,
            "health_arc_nov_apr": [80, 81, 82, 83, 83, 83],
            "arc_label": "capacity_healthy",
            "difficulty": "EASY",
            "renewal_date": "2026-11-01",
            "region": "NA-East",
            "industry": "enterprise_saas",
            "assigned_csm": "Marcus Rivera",
            "narrative": "Stable, high-usage flagship account; renewal "
                         "conversations positive.",
            "organic_nrr_outcome": "renewed_flat",
            "organic_nrr_pct_hint": 105,
        },
        {
            "name": "Verdant Media",             "arr_usd": 4_800_000,
            "health_arc_nov_apr": [72, 73, 73, 74, 74, 74],
            "arc_label": "steady_healthy",
            "difficulty": "EASY",
            "renewal_date": "2026-07-01",
            "region": "NA-West",
            "industry": "media_saas",
            "assigned_csm": "Alex Johnson",
            "narrative": "Stable mid-market account; healthy adoption, "
                         "minor ticket noise.",
            "organic_nrr_outcome": "renewed_flat",
            "organic_nrr_pct_hint": 102,
        },
        {
            "name": "Fern Health",               "arr_usd": 2_400_000,
            "health_arc_nov_apr": [66, 68, 68, 69, 69, 69],
            "arc_label": "slow_improve",
            "difficulty": "EASY",
            "renewal_date": "2026-10-15",
            "region": "NA-East",
            "industry": "healthtech",
            "assigned_csm": "Emily Park",
            "narrative": "Post-onboarding ramp; adoption improving but "
                         "not yet at expansion threshold.",
            "organic_nrr_outcome": "renewed_flat",
            "organic_nrr_pct_hint": 100,
        },
        {
            "name": "Atlas Biotech",             "arr_usd": 4_000_000,
            "health_arc_nov_apr": [70, 70, 71, 71, 72, 72],
            "arc_label": "steady_healthy",
            "difficulty": "EASY",
            "renewal_date": "2026-12-20",
            "region": "EU-West",
            "industry": "biotech_saas",
            "assigned_csm": "Alex Johnson",
            "narrative": "Regulated-industry account, predictable usage, "
                         "no risk signals.",
            "organic_nrr_outcome": "renewed_flat",
            "organic_nrr_pct_hint": 103,
        },
    ],
}


# ════════════════════════════════════════════════════════════════════
# Prompt — 4 CSVs + dual-metric sidecar (NRR + ROI)
# ════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = r"""
Generate data for a single synthetic CS Pulse customer onboarding.

The customer uploads 4 CSVs of historical data (past 12 months). You also
produce a SIDECAR per account recording what the customer achieves
ORGANICALLY over the NEXT 6 months — without CS Pulse. The sidecar has
two parallel ground-truth branches:

  1. NRR branch — Did the account renew? At what ARR? Portfolio-rolled up
     this is the "organic NRR" Wizard B's baseline forecast is graded against.
  2. ROI branch — What $ did the customer's own CS team protect and expand,
     for what $ they spent? This is the "organic ROI" the ROI engine's
     baseline projection is graded against.

The product's killer-value sales story is:
  "We predict your organic NRR at 107% (matches reality). We also predict
   you'd reach 115% NRR with CS Pulse adoption, at an ROI multiple of 12×
   on the CS Pulse investment." The accuracy of the ORGANIC prediction
   anchors trust in the UPLIFT claim.

=== INDEPENDENCE CONSTRAINTS ===
Forbidden arc labels (target model was developed against these):
  crisis_recovery, land_and_expand, competitive_displacement,
  silent_churn, expansion_champion, champion_loss

Invent new labels. Examples:
  vendor_consolidation_survivor, integration_debt_freeze,
  acq_parent_rationalization, procurement_rescope,
  usage_plateau_breakout, renewal_gate_flip, budget_cycle_mismatch,
  champion_transition_delayed, pilot_extension_stall

=== KPI TIERS (emit ONLY the KPIs of the selected tier) ===

STARTER_9 (9 KPIs):
  P1-KPI1  dau_rate                    range 10-95%   higher_better
  P1-KPI3  mau_to_licensed_ratio       range 20-100%  higher_better
  P2-KPI1  nps                         range -100..100 higher_better
  P3-KPI1  ticket_volume_per_user      range 0-20     lower_better
  P3-KPI3  p1_ticket_count             range 0-50     lower_better
  P3-KPI4  sla_compliance_pct          range 50-100%  higher_better
  P5-KPI1  renewal_probability_pct     range 0-100%   higher_better
  P5-KPI2  expansion_pipeline_usd      range 0-20M    higher_better
  P5-KPI3  expansion_closed_usd        range 0-10M    higher_better

PREDICTIVE_11 (adds 2):
  P1-KPI10 api_usage_trend_pct         range -50..+300 higher_better
  P2-KPI8  first_call_resolution_rate  range 0-100%   higher_better

Neither tier has P4 Engagement KPIs. Pillar weights cover only P1/P2/P3/P5.

=== ORDER OF OPERATIONS PER ACCOUNT ===

STEP 1. Commit ORGANIC 6-month NRR outcome (what happens WITHOUT CS Pulse).
        Distribution across a batch: renewed_flat 55%, renewed_expansion 15%,
        contracted 15%, churned 12%, non_renewal_event 3%.

STEP 2. Commit ORGANIC 6-month ROI outcome consistent with the NRR outcome.
        Variables to invent:
          - organic_cs_investment_usd_annual: what the customer spends on
            their own CS function. Typical: 0.8%-2.5% of ARR for B2B SaaS.
          - realized_protected_arr_usd: sum of POSITIVE renewal/save events
            their CS team achieves over the 6mo window
          - realized_lost_arr_usd: sum of NEGATIVE events (churn, contract)
          - realized_expanded_arr_usd: upsell/cross-sell their team closes
          - realized_organic_net_impact_usd = protected + expanded - lost
          - realized_organic_roi_pct = (net_impact / cs_investment_annual/2) × 100
            (6-month window so half-annual investment)

STEP 3. Assign difficulty tier for NRR AND ROI jointly:
          EASY   60% — past telegraphs both outcomes
          MEDIUM 25% — past hints at outcomes but with red herrings
          HARD   15% — past misleads; outcome driven by unobservable cause

STEP 4. Write 1-sentence narrative explaining the organic trajectory.

STEP 5. Generate the 4 CSVs' worth of past data (12 months ending
        2026-04-24) consistent with the narrative.
        DO NOT simulate CS Pulse running playbooks — no CS Pulse exists
        in this trajectory. The customer's own CS team is doing ordinary
        work.

STEP 6. Emit the account object.

=== OUTPUT SCHEMA (per account) ===
{
  "account_id": "syn-tNN-aMM",
  "kpi_tier": "predictive_11" | "starter_9",

  "csv_1_account_details": {
    "source_account_id": "syn-t05-a03",
    "account_name": "Acme Fintech Inc",
    "arr": 1250000,
    "industry": "consumer_lending",
    "vertical": "fintech",
    "region": "NA-East" | "NA-West" | "EU-West" | "APAC" | "LATAM",
    "employee_count": 450,
    "assigned_csm": "Sarah Chen" | "Marcus Rivera" | "Emily Park" | "Alex Johnson",
    "renewal_date": "2026-10-15",
    "primary_champion_name": "J. Chen",
    "primary_champion_title": "VP Engineering",
    "primary_champion_engagement_score": 78,
    "stakeholders_json": [
      {"name": "J. Chen", "title": "VP Engineering",
       "role": "champion", "influence_score": 0.85}
    ],
    "products_json": [
      {"product_id": "core_platform", "seats": 150, "usage_pct": 78}
    ]
  },

  // KPI values use COMPACT format: one entry per KPI with 12 monthly values.
  // Months are FIXED: 2025-05..2026-04 (index 0..11). Ingest expands this
  // into standard kpi_measurements.csv rows.
  "kpi_monthly_values": {
    "P1-KPI1": [78.2, 82.1, 85.0, 81.3, 77.8, 74.2, 71.6, 68.9, 65.4, 62.1, 58.7, 55.3],
    "P1-KPI3": [72, 75, 78, 74, 70, 66, 62, 58, 54, 51, 48, 45]
    // ... one entry per KPI in the selected tier. All arrays MUST have
    // exactly 12 numeric values corresponding to months 2025-05..2026-04.
  },

  "csv_3_qualitative_signals": [
    {"source_account_id": "syn-t05-a03", "signal_date": "2025-06-14",
     "signal_type": "champion_departure" | "kpi_decline" |
                    "executive_engagement" | "ticket_spike" |
                    "budget_pressure" | "competitor_mention" |
                    "feature_adoption_push" | "exec_absence" |
                    "contract_negotiation_opened" | ...,
     "sentiment": "negative" | "positive" | "neutral",
     "description": "short narrative, no PII"}
    // 10-25 signals over the 12 months
  ],

  "csv_4_outcomes": [
    {"source_account_id": "syn-t05-a03", "outcome_date": "2025-09-15",
     "title": "Q3 Expansion Closed",
     "outcome_type": "expansion_closed" | "renewal_secured" |
                     "churn_averted" | "revenue_protected" |
                     "revenue_at_risk" | "contraction" | ...,
     "revenue_value": 250000, "confidence": 1.0}
    // 2-6 HISTORICAL outcomes — all dates in past 12 months
  ],

  "future_truth": {
    "scenario": "organic_no_cs_pulse_intervention",
    "difficulty": "EASY" | "MEDIUM" | "HARD",
    "narrative": "1-sentence explanation",

    // NRR branch
    "realized_renewal_date": "2026-10-15",
    "realized_nrr_outcome": "renewed_flat" | "renewed_expansion" |
                            "contracted" | "churned" | "non_renewal_event",
    "realized_arr_change_usd": -250000,
    "realized_nrr_pct_for_account": 80,
    "is_nrr_forecastable_from_history": true,

    // ROI branch — what the customer's OWN CS team delivers, for what they spend
    "organic_cs_investment_usd_annual": 25000,
    "realized_protected_arr_usd": 350000,
    "realized_expanded_arr_usd": 50000,
    "realized_lost_arr_usd": 250000,
    "realized_organic_net_impact_usd": 150000,
    "realized_organic_roi_pct": 1200,
    "is_roi_forecastable_from_history": true
  }
}

Valid JSON array only, 10 accounts per response. No markdown fences.
"""

USER_PROMPT_TEMPLATE = """
Generate a synthetic CS Pulse tenant with EXACTLY {n} accounts.

Tenant spec:
- tenant_idx: {tenant_idx:02d}
- kpi_tier: {kpi_tier}
- vertical_focus: {vertical_focus}
- arc_phase coverage: {arc_phase_directive}
- portfolio health skew: {health_skew_directive}
- renewal window: {renewal_window_directive}

Account IDs: syn-t{tenant_idx:02d}-a01 through syn-t{tenant_idx:02d}-a{n:02d}.

Difficulty distribution within the tenant: ~60% EASY, 25% MEDIUM, 15% HARD.
Each account's future_truth MUST describe ORGANIC outcomes — what the
customer achieves WITHOUT CS Pulse, their own CS team doing normal work.
Include BOTH NRR and ROI branches in every future_truth.

Valid JSON array only.
"""

ARC_PHASE_DIRECTIVE = {
    "baseline":      "all accounts in baseline (no deterioration) throughout 12 months",
    "deterioration": "~70% of accounts show ongoing decline without recovery",
    "intervention":  "~60% decline then customer-led recovery in months 7-12",
    "4phase":        "~40% complete baseline→deterioration→intervention→resolution",
}
HEALTH_SKEW_DIRECTIVE = {
    "crisis_heavy":    "~60% end with aggregate health <50; ~30% in 50-70; ~10% >=70",
    "stable_heavy":    "~60% stay in 70-85 range throughout",
    "expansion_heavy": "~50% show sustained growth reaching 85+ with positive revenue",
    "churn_heavy":     "~35% deteriorate to churn; ~30% contract; ~35% renew flat",
    "balanced":        "accounts uniformly distributed across health bands",
}
RENEWAL_WINDOW_DIRECTIVE = {
    "near":  "renewal_dates within 60 days of 2026-10-24 (6mo from today 2026-04-24)",
    "mid":   "renewal_dates 90-180 days out from today",
    "long":  "renewal_dates 180-300 days out from today",
}


# ════════════════════════════════════════════════════════════════════
# Pinned-tenant prompt — slide-deck-matched data
# ════════════════════════════════════════════════════════════════════

PINNED_USER_PROMPT_TEMPLATE = """
Generate a synthetic CS Pulse tenant with EXACTLY {n} pinned accounts.

Tenant: {tenant_id}  (tenant_idx={tenant_idx:02d})
KPI tier: {kpi_tier}
Narrative: {tenant_narrative}

This is a PINNED tenant — every account's name, ARR, 6-month health
trajectory, renewal date, arc label, difficulty, and organic NRR outcome
are PRE-DETERMINED below. Your job is to fill in the plausible details:

  - 12 monthly KPI values per account (months 2025-05..2026-04)
    such that the rolled-up health score MATCHES the pinned health_arc
    for months 2025-11..2026-04 (the last 6 months).
  - 10-25 qualitative signals per account consistent with the arc_label
    and narrative (use positive signals for improving arcs, negative for
    deterioration arcs, expansion signals for expansion_ready).
  - 2-6 historical outcomes per account (past 12 months only).
  - future_truth sidecar with BOTH NRR and ROI branches. The
    realized_nrr_outcome and realized_nrr_pct_for_account MUST match the
    pinned organic_nrr_outcome and organic_nrr_pct_hint. Invent plausible
    ROI branch values (organic_cs_investment 1-2% of ARR etc).

Account IDs: syn-t{tenant_idx:02d}-a01 through syn-t{tenant_idx:02d}-a{n:02d}.
Use the PINNED account names in csv_1_account_details.account_name.

PINNED ACCOUNTS (must be produced in this order with these exact values):
{pinned_accounts_block}

=== HEALTH-ARC TARGETING ===
For starter_9, rolled-up account health is computed from KPI values using
pillar weights P1=P2=P3=P5=0.25 and KPI weights roughly uniform within
each pillar. To land a target health of, e.g., 42, aim KPI values such
that the pillar scores average ~42. Higher_better KPIs score proportional
to value/range_max; lower_better KPIs score proportional to
(range_max - value) / range_max.

Don't overthink the math — approximate is fine. The sidecar is the ground
truth; health arcs are directional targets.

Output: Valid JSON array only, exactly {n} account objects in the same
order as the PINNED list. No markdown fences.
"""


def _format_pinned_accounts_block(pinned_accounts: list[dict]) -> str:
    lines = []
    for i, a in enumerate(pinned_accounts, 1):
        arc_str = ",".join(str(v) for v in a["health_arc_nov_apr"])
        lines.append(
            f"  {i}. name={a['name']!r} arr_usd={a['arr_usd']} "
            f"health_arc_nov_apr=[{arc_str}]"
        )
        lines.append(
            f"     arc_label={a['arc_label']!r} difficulty={a['difficulty']!r} "
            f"renewal_date={a['renewal_date']!r} region={a['region']!r}"
        )
        lines.append(
            f"     industry={a['industry']!r} assigned_csm={a['assigned_csm']!r}"
        )
        lines.append(
            f"     narrative={a['narrative']!r}"
        )
        lines.append(
            f"     organic_nrr_outcome={a['organic_nrr_outcome']!r} "
            f"organic_nrr_pct_hint={a['organic_nrr_pct_hint']}"
        )
    return "\n".join(lines)


def call_claude_for_pinned_tenant(client, pinned_spec: dict) -> list[dict]:
    n = len(pinned_spec["pinned_accounts"])
    user = PINNED_USER_PROMPT_TEMPLATE.format(
        n=n,
        tenant_id=pinned_spec["tenant_id"],
        tenant_idx=pinned_spec["tenant_idx"],
        kpi_tier=pinned_spec["kpi_tier"],
        tenant_narrative=pinned_spec["narrative"],
        pinned_accounts_block=_format_pinned_accounts_block(
            pinned_spec["pinned_accounts"]
        ),
    )
    with client.messages.stream(
        model=MODEL,
        max_tokens=32000,
        temperature=0.55,  # lower temp so Claude respects pinned values
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user}],
    ) as stream:
        resp = stream.get_final_message()
    text = _strip_fences(resp.content[0].text) if resp.content else ""
    text = _repair_json(text)
    try:
        accounts = json.loads(text)
        if not isinstance(accounts, list):
            print(f"  WARN pinned {pinned_spec['tenant_id']}: expected list, got {type(accounts).__name__}",
                  file=sys.stderr)
            return []
    except json.JSONDecodeError as e:
        print(f"  WARN pinned {pinned_spec['tenant_id']}: JSON parse failed — {e}",
              file=sys.stderr)
        print(f"     first 200 chars: {text[:200]}", file=sys.stderr)
        # Dump raw response for debugging
        debug_path = Path(f"/tmp/claude_pinned_{pinned_spec['tenant_id']}_raw.json")
        debug_path.write_text(text)
        print(f"     raw response saved to {debug_path}", file=sys.stderr)
        return []

    tin = getattr(resp.usage, "input_tokens", 0)
    tout = getattr(resp.usage, "output_tokens", 0)
    cost = tin * 3e-6 + tout * 15e-6
    print(f"  pinned {pinned_spec['tenant_id']}: {len(accounts)} accts, "
          f"{tin}in/{tout}out = ${cost:.3f}", file=sys.stderr)
    return accounts


# ════════════════════════════════════════════════════════════════════
# Driver
# ════════════════════════════════════════════════════════════════════

def _strip_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t
        if t.rstrip().endswith("```"):
            t = t.rstrip()[:-3]
    return t.strip()


def _repair_json(text: str) -> str:
    """Fix known Claude JSON mistakes in this prompt's outputs.

    Observed Apr 24: when the prompt asks for `kpi_monthly_values` as a
    JSON *object* and the next field is `csv_3_qualitative_signals`
    (an array), Claude sometimes mis-closes the object with `]` instead
    of `}`. Rewrite that specific pattern in-place.
    """
    import re
    # `],\n    "csv_3_qualitative_signals"` → `},\n    "csv_3_qualitative_signals"`
    text = re.sub(
        r'\](,\s*\n\s*"csv_3_qualitative_signals")',
        r'}\1',
        text,
    )
    return text


def call_claude_for_tenant(client, spec) -> list[dict]:
    idx, tier, n, vertical, arc_phase, health_skew, renewal_window = spec
    user = USER_PROMPT_TEMPLATE.format(
        n=n, tenant_idx=idx, kpi_tier=tier, vertical_focus=vertical,
        arc_phase_directive=ARC_PHASE_DIRECTIVE[arc_phase],
        health_skew_directive=HEALTH_SKEW_DIRECTIVE[health_skew],
        renewal_window_directive=RENEWAL_WINDOW_DIRECTIVE[renewal_window],
    )
    # 10 accounts × (4 CSVs incl. 132 KPI rows) easily exceeds 16K tokens.
    # Bumped to 32K after observing truncation on first real run (Apr 24 2026).
    # Stream because non-streaming mode refuses >10min-potential operations
    # at this max_tokens size.
    with client.messages.stream(
        model=MODEL,
        max_tokens=32000,
        temperature=0.75,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user}],
    ) as stream:
        resp = stream.get_final_message()
    text = _strip_fences(resp.content[0].text) if resp.content else ""
    text = _repair_json(text)
    try:
        accounts = json.loads(text)
        if not isinstance(accounts, list):
            print(f"  WARN tenant {idx}: expected list, got {type(accounts).__name__}",
                  file=sys.stderr)
            return []
    except json.JSONDecodeError as e:
        print(f"  WARN tenant {idx}: JSON parse failed — {e}", file=sys.stderr)
        print(f"     first 200 chars: {text[:200]}", file=sys.stderr)
        return []

    tin = getattr(resp.usage, "input_tokens", 0)
    tout = getattr(resp.usage, "output_tokens", 0)
    cost = tin * 3e-6 + tout * 15e-6
    print(f"  tenant {idx:02d} [{tier}, {vertical}, {health_skew}]: "
          f"{len(accounts)} accts, {tin}in/{tout}out = ${cost:.3f}",
          file=sys.stderr)
    return accounts


def coverage_audit(tenants: list[dict]) -> dict:
    """Verify generated dataset covers the dimensions requested."""
    all_accts = [a for t in tenants for a in t.get("accounts", [])]
    if not all_accts:
        return {"failures": ["no accounts generated"], "total_accounts": 0}

    tiers = Counter(a.get("kpi_tier", "?") for a in all_accts)
    difficulties = Counter(
        a.get("future_truth", {}).get("difficulty", "?") for a in all_accts
    )
    outcomes = Counter(
        a.get("future_truth", {}).get("realized_nrr_outcome", "?") for a in all_accts
    )
    verticals = Counter(
        a.get("csv_1_account_details", {}).get("vertical", "?") for a in all_accts
    )
    # ROI coverage — % of accounts with both NRR + ROI branches in sidecar
    with_roi = sum(
        1 for a in all_accts
        if "realized_organic_roi_pct" in a.get("future_truth", {})
    )

    failures = []
    if len(verticals) < 7:
        failures.append(f"verticals_covered={len(verticals)} (need ≥7)")
    if difficulties.get("HARD", 0) / len(all_accts) < 0.10:
        failures.append(f"HARD underrepresented: {difficulties.get('HARD', 0)}/{len(all_accts)}")
    if tiers.get("starter_9", 0) < 20:
        failures.append(f"starter_9 accts={tiers.get('starter_9', 0)} (need ≥20)")
    if tiers.get("predictive_11", 0) < 20:
        failures.append(f"predictive_11 accts={tiers.get('predictive_11', 0)} (need ≥20)")
    if outcomes.get("churned", 0) == 0:
        failures.append("no churned outcomes in dataset")
    if with_roi < 0.95 * len(all_accts):
        failures.append(f"ROI branch missing on {len(all_accts) - with_roi} accounts")

    return {
        "total_accounts": len(all_accts),
        "tiers": dict(tiers),
        "verticals_covered": len(verticals),
        "difficulty_distribution": dict(difficulties),
        "nrr_outcome_distribution": dict(outcomes),
        "roi_branch_coverage_pct": round(100 * with_roi / len(all_accts), 1),
        "failures": failures,
    }


def main():
    parser = argparse.ArgumentParser(description="Claude-driven synthetic backtest generator")
    parser.add_argument("--output", type=Path,
                        default=Path("scripts/datasets/claude_driven_backtest_v1.json"))
    parser.add_argument("--tenants", type=int, default=20,
                        help="Number of tenants to generate from TENANT_SPECS")
    parser.add_argument("--include-phoenix", action="store_true", default=True,
                        help="Also generate the pinned slide-deck tenant (default: on)")
    parser.add_argument("--skip-phoenix", dest="include_phoenix",
                        action="store_false",
                        help="Skip the pinned phoenix-saas-demo tenant")
    parser.add_argument("--only-phoenix", action="store_true",
                        help="Generate ONLY the phoenix tenant (skip the 20 synthetic)")
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY env var required", file=sys.stderr)
        sys.exit(1)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    client = anthropic.Anthropic()

    t0 = time.time()
    tenants = []

    if not args.only_phoenix:
        specs = TENANT_SPECS[: args.tenants]
        print(f"generating {len(specs)} synthetic tenants...", file=sys.stderr)
        for spec in specs:
            accounts = call_claude_for_tenant(client, spec)
            tenants.append({
                "tenant_idx": spec[0],
                "kpi_tier": spec[1],
                "n_accts_requested": spec[2],
                "vertical_focus": spec[3],
                "arc_phase": spec[4],
                "health_skew": spec[5],
                "renewal_window": spec[6],
                "accounts": accounts,
            })
            time.sleep(0.3)

    if args.include_phoenix or args.only_phoenix:
        print(f"generating pinned phoenix-saas-demo tenant...", file=sys.stderr)
        phoenix_accts = call_claude_for_pinned_tenant(client, PINNED_TENANT_PHOENIX)
        tenants.append({
            "tenant_idx": PINNED_TENANT_PHOENIX["tenant_idx"],
            "tenant_id": PINNED_TENANT_PHOENIX["tenant_id"],
            "kpi_tier": PINNED_TENANT_PHOENIX["kpi_tier"],
            "n_accts_requested": len(PINNED_TENANT_PHOENIX["pinned_accounts"]),
            "vertical_focus": PINNED_TENANT_PHOENIX["vertical_focus"],
            "narrative": PINNED_TENANT_PHOENIX["narrative"],
            "is_pinned": True,
            "pinned_spec": PINNED_TENANT_PHOENIX["pinned_accounts"],
            "accounts": phoenix_accts,
        })

    audit = coverage_audit(tenants)
    if audit["failures"]:
        print(f"\n⚠️  coverage failures: {audit['failures']}", file=sys.stderr)
    else:
        print(f"\n✓ coverage OK", file=sys.stderr)

    payload = {
        "dataset_version": "v1",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "model_used": MODEL,
        "coverage_audit": audit,
        "tenants": tenants,
    }
    args.output.write_text(json.dumps(payload, indent=2))
    print(
        f"\n✅ wrote {audit['total_accounts']} accounts across {len(tenants)} tenants → {args.output}",
        file=sys.stderr,
    )
    print(f"   runtime {round(time.time()-t0, 1)}s", file=sys.stderr)


if __name__ == "__main__":
    main()
