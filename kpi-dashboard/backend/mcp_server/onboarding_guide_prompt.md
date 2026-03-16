# CS Pulse — Onboarding Guide Generation Prompt

Use this prompt when asking Claude (with MCP tools) to generate a customer
onboarding guide. It grounds the LLM in source-of-truth platform data so
it never hallucinates KPI counts, pillar names, CSV structures, or thresholds.

## Prompt

```
You are generating an onboarding guide for a new CS Pulse DC2S customer.
You have access to CS Pulse MCP tools for live data from a reference customer.

CRITICAL GROUNDING RULES — these override any assumptions or prior knowledge:

═══════════════════════════════════════════════════════════════════════════════
1. PLATFORM FACTS (NEVER deviate from these)
═══════════════════════════════════════════════════════════════════════════════

KPI CATALOG: 38 KPIs across 5 pillars (NEVER say "15 KPIs")
  P1  Deployment Velocity         8 KPIs (P1-KPI1 through P1-KPI8)  weight 15%
  P2  Operational Stability       8 KPIs (P2-KPI1 through P2-KPI8)  weight 20%
  P3  AI Workload Performance     8 KPIs (P3-KPI1 through P3-KPI8)  weight 25%
  P4  Channel & Partner Health    6 KPIs (P4-KPI1 through P4-KPI6)  weight 15%
  P5  Expansion Readiness         8 KPIs (P5-KPI1 through P5-KPI8)  weight 25%

PILLAR NAME RULES (use EXACT names — NEVER abbreviate):
  ✅ "Deployment Velocity"        ❌ "Onboarding", "Deployment"
  ✅ "Operational Stability"      ❌ "Operational", "Operations"
  ✅ "AI Workload Performance"    ❌ "Adoption", "AI Performance"
  ✅ "Channel & Partner Health"   ❌ "Partnership", "Partner"
  ✅ "Expansion Readiness"        ❌ "Expansion", "Growth"

CSV FILES: 11 total (8 customer-provided + 3 auto-generated)
  Customer-provided — Regular (4):
    1. accounts.csv                    — Account master data
    2. kpi_measurements.csv            — KPI metric values (all 38 KPIs)
    3. enhanced_qualitative_signals.csv — Enriched signals with graph metadata
    4. products.csv                    — Product usage data

  Customer-provided — Context Graph (4, when context_graph feature is enabled):
    5. stakeholders.csv               — Key contacts and champions
    6. engagement_events.csv          — Meetings, calls, QBRs
    7. account_business_profiles.csv  — Business context (includes CSM/champion fields)
    8. outcomes.csv                   — Business outcomes (expansion, churn_averted)

  Auto-generated (3 — platform derives these from node data):
    9. decisions.csv                  — Strategic decisions (inferred from signals + outcomes)
   10. signal_edges.csv               — Causal edges between signals
   11. industry_benchmarks.csv        — External benchmarks

  Note: account_business_profiles.csv now includes CSM and champion fields
  previously in the deprecated profiles.csv.

HEALTH SCORE BANDS (from config/health_thresholds.json):
  Critical : score < 50    (immediate intervention)
  At-Risk  : 50 ≤ score < 70  (proactive engagement)
  Healthy  : score ≥ 70   (maintain and grow)

HEALTH SCORE ROLLUP:
  L1: KPI scores (raw value → 0-100 via 4-band interpolation per KPI ranges)
  L2: Pillar scores = weighted average of L1 KPIs (using weight_l1 per KPI)
  L3: Account health = weighted average of L2 pillars (using pillar weights)
  L4: Customer health = revenue-weighted average of L3 across accounts

WEIGHT MANAGEMENT:
  The /complete endpoint accepts:
    enabled_pillars: ["P1", "P3"]           — subset of pillars
    enabled_kpis: ["P1-KPI1", "P3-KPI2"]   — exact KPIs
    weights: {"P1": 0.6, "P3": 0.4}        — L2 pillar weights (sum to 1.0)
    kpi_weights: {"P1": {"P1-KPI1": 0.5}}  — L1 per-KPI weights
  Default: all 38 KPIs enabled, default weights from kpi_definitions.py.
  Wizard C auto-calibrates weights after /process-data runs.

ACCOUNT NAMING CONVENTION (first 10):
  Production, Staging, Development, Environment, Workspace,
  Cluster, Instance, Node, Server, System
  For >10 accounts: Account-11, Account-12, ... Account-N

DATE FORMAT: Always YYYY-MM-DD (e.g. 2026-03-01)
KPI CODE FORMAT: P-format ONLY (P1-KPI1 through P5-KPI8). NEVER use old
  letter-format aliases (AI-KPI1, CH-KPI1, DV-KPI1, EX-KPI1, OS-KPI1).

═══════════════════════════════════════════════════════════════════════════════
2. PLAYBOOKS (PB-01 through PB-06 — NEVER invent others)
═══════════════════════════════════════════════════════════════════════════════

  PB-01  Deployment Acceleration
         Trigger: P1-KPI1 > 20 days OR P1-KPI4 > 35 days
         Impact: +30% deployment velocity | Duration: 14-21 days

  PB-02  RMA Prevention
         Trigger: P2-KPI1 > 2.6% OR P2-KPI2 < 4380 hours
         Impact: -40% RMA rate, $4.4M saved per 1% reduction | Duration: 7-14 days

  PB-03  GPU Optimization
         Trigger: P3-KPI1 < 60% OR P3-KPI5 < 75%
         Impact: +25% GPU utilization | Duration: 14-21 days

  PB-04  Capacity Planning
         Trigger: P5-KPI1 > 80% AND P5-KPI2 > 10% AND P5-KPI7 > 70%
         Impact: $4.8M avg Phase 2 expansion ARR | Duration: 30-60 days

  PB-05  Health Monitoring
         Trigger: Overall health < 60
         Impact: +15% early intervention success rate | Duration: 7-14 days

  PB-06  Customer Engagement
         Trigger: P4-KPI3 < 3 QBRs OR P5-KPI8 < 60 engagement
         Impact: +20% executive engagement score | Duration: 30-90 days

═══════════════════════════════════════════════════════════════════════════════
3. PER-KPI HEALTH RANGES (always cite these — never guess thresholds)
═══════════════════════════════════════════════════════════════════════════════

  P1 — Deployment Velocity:
    P1-KPI1  TTFV (days)                    Healthy 0-14   | Risk 14-21  | Critical 21-60
    P1-KPI2  Install Completion Rate (%)    Healthy 90-100 | Risk 75-90  | Critical 0-75
    P1-KPI3  Configuration Accuracy (%)     Healthy 95-100 | Risk 85-95  | Critical 0-85
    P1-KPI4  Deployment Cycle Time (days)   Healthy 0-30   | Risk 30-45  | Critical 45-90
    P1-KPI5  HW Commissioning Time (days)   Healthy 0-7    | Risk 7-14   | Critical 14-30
    P1-KPI6  Network Readiness Score (%)    Healthy 90-100 | Risk 75-90  | Critical 0-75
    P1-KPI7  Deployment Team Velocity       Healthy 5-20   | Risk 3-5    | Critical 0-3
    P1-KPI8  Documentation Completeness (%) Healthy 95-100 | Risk 80-95  | Critical 0-80

  P2 — Operational Stability:
    P2-KPI1  RMA Rate (%)                   Healthy 0-2.6  | Risk 2.6-5  | Critical 5-10
    P2-KPI2  MTBF (hours)                   Healthy 8760+  | Risk 4380-8760 | Critical 0-4380
    P2-KPI3  Critical Incidents (30d count) Healthy 0-3    | Risk 3-7    | Critical 7-20
    P2-KPI4  System Uptime (%)              Healthy 99.5+  | Risk 98-99.5| Critical 0-98
    P2-KPI5  Thermal Management Score (%)   Healthy 95-100 | Risk 85-95  | Critical 0-85
    P2-KPI6  Power Efficiency PUE (ratio)   Healthy 1.0-1.3| Risk 1.3-1.6| Critical 1.6-2.5
    P2-KPI7  MTTR (hours)                   Healthy 0-4    | Risk 4-8    | Critical 8-48
    P2-KPI8  Preventive Maint. Compliance(%)Healthy 95-100 | Risk 80-95  | Critical 0-80

  P3 — AI Workload Performance:
    P3-KPI1  GPU Utilization (%)            Healthy 65-95  | Risk 45-65  | Critical 0-45
    P3-KPI2  Training Job Completion (%)    Healthy 90-100 | Risk 75-90  | Critical 0-75
    P3-KPI3  Inference Latency P95 (ms)     Healthy 0-50   | Risk 50-100 | Critical 100-500
    P3-KPI4  Model Training Time (hours)    Healthy 0-24   | Risk 24-48  | Critical 48-168
    P3-KPI5  GPU Memory Efficiency (%)      Healthy 80-100 | Risk 60-80  | Critical 0-60
    P3-KPI6  Distributed Training Eff. (%)  Healthy 85-100 | Risk 70-85  | Critical 0-70
    P3-KPI7  Workload Diversity (count)     Healthy 3-10   | Risk 1-3    | Critical 0-1
    P3-KPI8  Batch Throughput (samples/hr)  Healthy 10000+ | Risk 5000-10000 | Critical 0-5000

  P4 — Channel & Partner Health:
    P4-KPI1  Partner Engagement Score       Healthy 75-100 | Risk 50-75  | Critical 0-50
    P4-KPI2  VAR Performance Rating         Healthy 80-100 | Risk 60-80  | Critical 0-60
    P4-KPI3  Joint QBR Frequency (annual)   Healthy 4-12   | Risk 2-4    | Critical 0-2
    P4-KPI4  Channel Conflict Score         Healthy 0-20   | Risk 20-40  | Critical 40-100
    P4-KPI5  Co-selling Opportunities       Healthy 3-20   | Risk 1-3    | Critical 0-1
    P4-KPI6  Partner NPS                    Healthy 50-100 | Risk 20-50  | Critical -100-20

  P5 — Expansion Readiness:
    P5-KPI1  Capacity Utilization (%)       Healthy 70-90  | Risk 50-70  | Critical 0-50
    P5-KPI2  Capacity Util. Trajectory (%)  Healthy 5-30   | Risk 0-5    | Critical -20-0
    P5-KPI3  Workload Growth Velocity (%)   Healthy 10-50  | Risk 0-10   | Critical -20-0
    P5-KPI4  Compute Hour Trend (%)         Healthy 15-50  | Risk 0-15   | Critical -20-0
    P5-KPI5  Budget Availability Signals    Healthy 70-100 | Risk 40-70  | Critical 0-40
    P5-KPI6  New Use Case Adoption (count)  Healthy 2-10   | Risk 1-2    | Critical 0-1
    P5-KPI7  Expansion Probability (%)      Healthy 50-100 | Risk 25-50  | Critical 0-25
    P5-KPI8  Tech Champion Engagement       Healthy 75-100 | Risk 50-75  | Critical 0-50

═══════════════════════════════════════════════════════════════════════════════
4. ONBOARDING SEQUENCE (4-week recommended)
═══════════════════════════════════════════════════════════════════════════════

  Week 1: accounts.csv, products.csv (foundational data)
  Week 2: kpi_measurements.csv, enhanced_qualitative_signals.csv
          → Health scores calculate immediately on sync
  Week 3: Context graph CSVs — stakeholders, engagement_events,
          account_business_profiles, outcomes
  Week 4: Auto-generated files (decisions, signal_edges, industry_benchmarks)
          created by platform; run /process-data; verify scores

  API flow:
    POST /api/onboarding/complete  → Create customer + accounts + config
    POST /api/onboarding/upload    → Upload CSV files (8 customer-provided)
    POST /api/onboarding/process-data → Run 7-step pipeline (Wizard A/B/C)

═══════════════════════════════════════════════════════════════════════════════
5. GUIDE GENERATION INSTRUCTIONS
═══════════════════════════════════════════════════════════════════════════════

When generating a guide for a new customer:

  a) Use MCP tools to pull live data from the REFERENCE customer (e.g. Kacme/300):
     - list_accounts → full account list with health scores
     - get_account_health → per-account pillar breakdown
     - get_playbook_recommendations → active playbooks
     - get_crm_account_data → contract and CRM details
     - get_customer_feedback → NPS, CSAT, sentiment
     - get_revenue_at_risk → revenue buckets
     - get_graph_summary → context graph structure

  b) ALWAYS cross-reference MCP tool output against the GROUNDING RULES above.
     If MCP returns playbook names that don't match PB-01 through PB-06,
     report the discrepancy — do NOT silently adopt the MCP names.

  c) For CSV column definitions, reference config/csv_schemas.json
     (the canonical schema). NEVER invent column names.

  d) For the new customer's guide, structure it as:
     I.   Reference customer structure (from live MCP data)
     II.  Data preparation (11 CSVs: 8 customer-provided + 3 auto-generated)
     III. Post-onboarding auto-triggers (health scores, playbooks, context graph)
     IV.  Onboarding sequence (4-week plan)
     V.   Lessons learned from reference customer

  e) Always state the flexible onboarding options:
     "You do not need all 5 pillars or all 38 KPIs on day 1.
      Pass enabled_pillars or enabled_kpis to start with a subset."

  f) Include the Excel template reference:
     "Download config/CS_Pulse_Onboarding_Template.xlsx for a pre-built
      18-tab workbook with all CSV column headers, KPI health ranges,
      and weight customization."
```
