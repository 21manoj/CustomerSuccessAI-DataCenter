# Plan: Configurable Multi-Vertical Architecture — SaaSPremium & MSPPremium

**Author**: CS Pulse Architecture Team
**Date**: March 2026
**Status**: Draft
**Scope**: Platform-wide refactoring + 2 new vertical configurations

---

## 1. Executive Summary

CS Pulse currently supports a single vertical (`dc2_s` — Data Center Infrastructure). This plan describes how to refactor the platform from a **single-vertical codebase** into a **config-driven multi-vertical engine**, and then instantiate two new verticals:

| Vertical | Slug | Buyer | Pillar Count | KPI Count |
|----------|------|-------|-------------|-----------|
| **SaaSPremium** | `saas_premium` | VP CS / CRO | 5 pillars | 35 KPIs |
| **MSPPremium** | `msp_premium` | MSP Practice Lead / CRO | 5 pillars | ~28 KPIs |

### Design Principle

> **A new vertical should be configured, not coded.**
> Adding a vertical = dropping JSON files into a directory. Zero Python imports, zero blueprint registrations, zero model changes.

```
config/verticals/saas_premium/
    kpi_definitions.json         <-- 30 KPIs, 5 pillars
    power_of_1_metrics.json      <-- 5 economic levers
    default_weights.json         <-- L1 + L2 defaults
    playbooks.json               <-- 6 playbooks with trigger conditions
    journey_phases.json          <-- 3 lifecycle phases
    metadata_schema.json         <-- Account metadata shape
    terminology.json             <-- Domain-specific labels & nomenclature
    onboarding_tiers.json        <-- Quick Start / Standard / Full KPI lists
    story_arcs/                  <-- 4-6 arc manifests for demo data
```

No new Python package. No assertions. No imports.

---

## 2. Current Architecture (What We Have)

### 2.1 Single-Vertical Coupling Points

| Layer | Current State | Problem |
|-------|--------------|---------|
| **KPI Definitions** | `verticals/dc2_s/kpi_definitions.py` (Python) | Hardcoded dict; new vertical = new Python module |
| **API Routes** | `verticals/dc2_s/api_routes.py` blueprint | 2200 lines of DC-specific Flask routes |
| **Score Calculator** | `utils/score_calculator.py` | Imports `DC2S_KPIS` directly |
| **Onboarding API** | `onboarding_api_v2_config_aware.py` | `from verticals.dc2_s.kpi_definitions import DC2S_KPIS` |
| **Power-of-1** | `config/power_of_1_economics.json` | Single config, DC2S metrics only |
| **DB Models** | `DC2SKPI` table, `CustomerConfig.dc2s_*` fields | DC2S-prefixed column names |
| **Test Runner** | `test_runner_api.py` | Hardcoded `dc2_s` directory paths |
| **Frontend** | `KPI_CATALOG` in `types.ts` | 38 DC2S KPIs hardcoded |

### 2.2 What's Already Config-Driven (Reusable)

- Health score thresholds (`config/health_thresholds.json`) -- vertical-agnostic
- CSV schemas (`config/csv_schemas.json`) -- column definitions are generic
- Story arc schema (`config/story_arcs/schema.json`) -- vertical-agnostic manifest format
- Context graph model (`ContextNode` / `ContextEdge`) -- generic graph, not vertical-specific
- Weight hierarchy (L1/L2/L3/L4 rollup) -- the math is universal
- Feature toggles (`feature_toggles.py`) -- already per-customer

---

## 3. Architecture: Config-Driven Vertical Engine

### 3.1 Directory Convention

```
config/verticals/{vertical_slug}/
    manifest.json                 <-- Vertical metadata (name, version, buyer, etc.)
    kpi_definitions.json          <-- Pillars + KPIs (replaces .py)
    power_of_1_metrics.json       <-- Economic levers for ROI calculations
    default_weights.json          <-- L1 weights (per-KPI) + L2 weights (per-pillar)
    playbooks.json                <-- Playbook triggers, actions, success criteria
    journey_phases.json           <-- Lifecycle phases + transitions
    metadata_schema.json          <-- Account-level metadata (JSON Schema format)
    terminology.json              <-- Domain-specific labels, nomenclature
    onboarding_tiers.json         <-- Preset KPI subsets (Quick/Standard/Full)
    csv_column_overrides.json     <-- Optional: column name customizations
    story_arcs/
        arc_*.json                <-- Demo data arc manifests
```

### 3.2 Vertical Manifest (`manifest.json`)

```json
{
  "vertical_id": "saas_premium",
  "vertical_name": "SaaS Premium",
  "version": "1.0.0",
  "description": "Enterprise SaaS Customer Success with deep adoption & expansion analytics",
  "target_buyer": "VP Customer Success / CRO",
  "pillar_count": 5,
  "kpi_count": 35,
  "supported_features": {
    "context_graph": true,
    "power_of_1": true,
    "story_arcs": true,
    "playbooks": true,
    "simulation_mode": true,
    "rag_signals": true
  },
  "arr_baseline_for_economics": 10000000,
  "health_score_model": "weighted_pillar_rollup",
  "created_at": "2026-03-10"
}
```

### 3.3 KPI Definitions Format (`kpi_definitions.json`)

```json
{
  "version": "1.0.0",
  "pillars": [
    {
      "pillar_id": "P1",
      "name": "Product Adoption & Usage",
      "weight_l2": 0.30,
      "description": "Depth and breadth of product usage across licensed features"
    }
  ],
  "kpis": [
    {
      "code": "P1-KPI1",
      "name": "Daily Active Users (DAU)",
      "pillar": "P1",
      "weight_l1": 0.20,
      "frequency": "daily",
      "unit": "count",
      "higher_is_better": true,
      "target": { "operator": ">", "value": 80 },
      "ranges": {
        "healthy":  { "min": 80, "max": 100, "color": "green" },
        "risk":     { "min": 50, "max": 80,  "color": "yellow" },
        "critical": { "min": 0,  "max": 50,  "color": "red" }
      },
      "data_source": "product_telemetry",
      "correlation": 0.65,
      "description": "Percentage of licensed users actively using the product daily"
    }
  ]
}
```

### 3.4 Terminology Overlay (`terminology.json`)

This is the **key differentiator** — domain-specific language that adapts the UI and reports to the vertical's audience.

```json
{
  "entity_labels": {
    "account": "Customer Account",
    "health_score": "Customer Health Index",
    "pillar": "Health Dimension",
    "kpi": "Success Metric",
    "csm": "Customer Success Manager",
    "arr": "ARR",
    "expansion": "Expansion",
    "churn": "Churn"
  },
  "phase_labels": {
    "deployment": "Onboarding",
    "performance": "Adoption",
    "excellence": "Maturity"
  },
  "score_labels": {
    "healthy": "On Track",
    "at_risk": "Needs Attention",
    "critical": "At Risk"
  },
  "dashboard_title": "SaaS Customer Health Dashboard",
  "executive_summary_title": "Customer Portfolio Health",
  "action_labels": {
    "escalate": "Flag for Review",
    "engage": "Schedule Touchpoint",
    "expand": "Identify Expansion Opportunity"
  },
  "report_headers": {
    "qbr_title": "Quarterly Business Review",
    "roi_title": "Value Realization Report",
    "health_title": "Customer Health Summary"
  }
}
```

For MSPPremium, this would use MSP-specific language:

```json
{
  "entity_labels": {
    "account": "Managed Client",
    "health_score": "Service Health Score",
    "pillar": "Service Dimension",
    "kpi": "Service KPI",
    "csm": "Account Manager",
    "arr": "MRR",
    "expansion": "Service Expansion",
    "churn": "Client Offboarding"
  },
  "phase_labels": {
    "deployment": "Service Onboarding",
    "performance": "Steady-State Operations",
    "excellence": "Strategic Partnership"
  }
}
```

### 3.5 Onboarding Tiers (`onboarding_tiers.json`)

```json
{
  "tiers": [
    {
      "id": "quick_start",
      "label": "Quick Start",
      "description": "Core metrics only — fast time-to-value",
      "kpi_count": 8,
      "enabled_kpis": ["P1-KPI1", "P1-KPI2", "P2-KPI1", "P2-KPI2", "P3-KPI1", "P3-KPI2", "P4-KPI1", "P4-KPI2"],
      "enabled_pillars": ["P1", "P2", "P3", "P4"],
      "power_of_1_compliant": false
    },
    {
      "id": "standard",
      "label": "Standard",
      "description": "Balanced coverage, all economic levers mapped",
      "kpi_count": 16,
      "enabled_kpis": ["..."],
      "enabled_pillars": ["P1", "P2", "P3", "P4"],
      "power_of_1_compliant": true
    },
    {
      "id": "full",
      "label": "Full",
      "description": "All KPIs — maximum signal depth",
      "kpi_count": 24,
      "enabled_kpis": ["ALL"],
      "enabled_pillars": ["P1", "P2", "P3", "P4"],
      "power_of_1_compliant": true
    }
  ]
}
```

---

## 4. SaaSPremium Vertical Definition

### 4.1 Buyer & Use Case

| Attribute | Value |
|-----------|-------|
| **Target buyer** | VP Customer Success, CRO |
| **Use case** | Enterprise SaaS companies managing B2B customer portfolios |
| **Health model** | Product-led with expansion focus |
| **Key differentiator** | Deep adoption analytics, NRR-driven |

### 4.2 Pillar Structure (5 Pillars, 35 KPIs)

> **Canonical Source**: `config/verticals/saas_premium/kpi_definitions.json`
> (loaded by `verticals/saas_premium/kpi_definitions.py`).
> Aligned with `scripts/seed_tier_templates.py:SAAS_KPIS` — the production template
> used for tier-based onboarding.

#### P1: Product Adoption & Usage (Weight L2: 0.20)

| Code | KPI Name | Weight L1 | Unit | Target | Direction |
|------|----------|-----------|------|--------|-----------|
| P1-KPI1 | Daily Active Users (DAU) Rate | 0.20 | % | > 60% | higher |
| P1-KPI2 | Feature Adoption Breadth | 0.18 | % | > 45% | higher |
| P1-KPI3 | Time-to-Value (TTV) | 0.16 | days | < 21 | lower |
| P1-KPI4 | Login Frequency | 0.14 | sessions/user/week | > 3.5 | higher |
| P1-KPI5 | API Integration Usage | 0.12 | % | > 30% | higher |
| P1-KPI6 | Workflow Completion Rate | 0.10 | % | > 75% | higher |
| P1-KPI7 | Module Activation Rate | 0.10 | % | > 70% | higher |

*L1 weights sum to 1.0*

#### P2: Customer Engagement (Weight L2: 0.15)

| Code | KPI Name | Weight L1 | Unit | Target | Direction |
|------|----------|-----------|------|--------|-----------|
| P2-KPI1 | Executive Sponsor Engagement | 0.22 | score | > 70 | higher |
| P2-KPI2 | QBR Attendance Rate | 0.18 | % | > 85% | higher |
| P2-KPI3 | Training Completion Rate | 0.15 | % | > 60% | higher |
| P2-KPI4 | Community Participation Score | 0.12 | score | > 40 | higher |
| P2-KPI5 | CSM Interaction Frequency | 0.13 | interactions/month | > 4 | higher |
| P2-KPI6 | Webinar/Event Attendance | 0.10 | % | > 25% | higher |
| P2-KPI7 | Customer Advocacy Score | 0.10 | score | > 50 | higher |

*L1 weights sum to 1.0*

#### P3: Support & Service Quality (Weight L2: 0.15)

| Code | KPI Name | Weight L1 | Unit | Target | Direction |
|------|----------|-----------|------|--------|-----------|
| P3-KPI1 | Ticket Resolution Time | 0.20 | hours | < 24 | lower |
| P3-KPI2 | CSAT Score | 0.18 | score | > 85 | higher |
| P3-KPI3 | NPS Score | 0.15 | score (-100 to 100) | > 40 | higher |
| P3-KPI4 | Escalation Rate | 0.14 | % | < 8% | lower |
| P3-KPI5 | First Contact Resolution Rate | 0.13 | % | > 70% | higher |
| P3-KPI6 | Support Ticket Volume Trend | 0.10 | % MoM | < 5% | lower |
| P3-KPI7 | SLA Compliance Rate | 0.10 | % | > 95% | higher |

*L1 weights sum to 1.0*

#### P4: Partner & Ecosystem Health (Weight L2: 0.20)

| Code | KPI Name | Weight L1 | Unit | Target | Direction |
|------|----------|-----------|------|--------|-----------|
| P4-KPI1 | Partner-Sourced Revenue Rate | 0.20 | % | > 25% | higher |
| P4-KPI2 | Partner Certification Level | 0.16 | score | > 60 | higher |
| P4-KPI3 | Partner Deal Registration Rate | 0.15 | % | > 40% | higher |
| P4-KPI4 | Channel Conflict Resolution Time | 0.13 | days | < 14 | lower |
| P4-KPI5 | Partner Satisfaction Score | 0.14 | score | > 75 | higher |
| P4-KPI6 | Co-Marketing Campaign ROI | 0.12 | % | > 200% | higher |
| P4-KPI7 | Partner Technical Enablement Score | 0.10 | score | > 65 | higher |

*L1 weights sum to 1.0*

#### P5: Revenue & Growth (Weight L2: 0.30)

| Code | KPI Name | Weight L1 | Unit | Target | Direction |
|------|----------|-----------|------|--------|-----------|
| P5-KPI1 | Net Revenue Retention (NRR) | 0.22 | % | > 110% | higher |
| P5-KPI2 | Gross Revenue Retention (GRR) | 0.18 | % | > 92% | higher |
| P5-KPI3 | Expansion Revenue Rate | 0.15 | % | > 15% | higher |
| P5-KPI4 | Annual Contract Value (ACV) Growth | 0.12 | % | > 12% | higher |
| P5-KPI5 | Renewal Probability (90d) | 0.15 | % | > 85% | higher |
| P5-KPI6 | Churn Risk Score | 0.10 | % | < 20% | lower |
| P5-KPI7 | Customer Lifetime Value Trend | 0.08 | ratio | > 2.0 | higher |

*L1 weights sum to 1.0*

### 4.3 Power-of-1 Metrics (6 Levers)

| Metric | Linked KPIs | Annual Impact per 1% | Category |
|--------|-------------|---------------------|----------|
| **NRR** | P5-KPI1, P5-KPI3 | $100,000 @ $10M ARR | revenue_multiplier |
| **GRR** | P5-KPI2, P3-KPI3, P3-KPI1 | $95,000 @ $10M ARR | retention_shield |
| **Product Adoption** | P1-KPI1, P1-KPI2, P1-KPI6 | $72,000 @ $10M ARR | usage_driver |
| **Expansion Rate** | P5-KPI3, P5-KPI5, P4-KPI1 | $85,000 @ $10M ARR | growth_lever |
| **TTV** | P1-KPI3 | $61,250 @ $10M ARR | foundation_investment |
| **Ticket Resolution** | P3-KPI1, P3-KPI2 | $48,000 @ $10M ARR | operational_efficiency |

### 4.4 Journey Phases

| Phase | Duration | Focus Pillars | Entry Criteria | Exit Criteria |
|-------|----------|--------------|----------------|---------------|
| **Onboarding** | 0-60 days | P1 (Adoption), P2 (Engagement) | Contract signed | TTV < 21 days, DAU > 50% |
| **Adoption** | 60-180 days | P1 + P3 (Support Quality) | TTV achieved | Feature adoption > 45%, NPS > 30 |
| **Maturity** | 180+ days | P4 (Partner) + P5 (Revenue) | Adoption stable | NRR > 105%, Renewal prob > 60% |

### 4.5 Playbooks (7)

| ID | Name | Phase | Trigger Conditions | Actions |
|----|------|-------|-------------------|---------|
| PB-01 | Adoption Accelerator | Onboarding | TTV > 21 days OR DAU < 30% (P1) | CSM outreach, training session, feature walkthrough |
| PB-02 | Engagement Recovery | Adoption | Login freq < 1/week AND NPS < 20 (P3) | Executive check-in, usage review, success plan |
| PB-03 | Churn Prevention | Any | GRR < 90% (P5) OR NPS < 20 (P3) | Exec escalation, save call, value demonstration |
| PB-04 | Expansion Discovery | Maturity | Seat util > 90% AND expansion prob > 60% (P5) | Expansion proposal, ROI case, stakeholder mapping |
| PB-05 | Health Monitoring | Cross-phase | Health score < 70 for 2 consecutive months | Automated alert, CSM review, action plan |
| PB-06 | Support Optimization | Adoption+ | Escalation rate > 10% (P3) AND self-service < 25% | KB improvement, training push, process review |
| PB-07 | Champion Enablement | Maturity | Power user ratio > 30% (P1) AND champion count > 3 | Champion program invite, reference opportunity |

### 4.6 Story Arcs (4 Initial)

| Arc | Narrative | Target Audience | ARR Range |
|-----|-----------|-----------------|-----------|
| `arc_adoption_stall` | Customer stops adopting after initial rollout | VP CS | $500K - $2M |
| `arc_expansion_champion` | Power user drives expansion across BUs | CRO | $1M - $5M |
| `arc_silent_churn` | Declining engagement with no visible complaints | VP CS | $200K - $1M |
| `arc_land_and_expand` | Small team grows to enterprise-wide deployment | CRO | $100K - $3M |

### 4.7 Metadata Schema

```json
{
  "vertical": "saas_premium",
  "deployment_type": "cloud|hybrid|on_premise",
  "contract_start_date": "2025-06-01",
  "contract_end_date": "2026-05-31",
  "licensed_seats": 500,
  "active_seats": 425,
  "licensed_modules": ["core", "analytics", "integrations", "ai_copilot"],
  "active_modules": ["core", "analytics"],
  "industry": "technology",
  "company_size": "mid_market",
  "arr": 240000,
  "mrr": 20000,
  "executive_sponsor": "Jane Smith",
  "csm_assigned": "John Doe",
  "implementation_partner": "Acme Consulting",
  "journey_phase": "adoption",
  "phase_entry_date": "2025-08-01",
  "integration_count": 3,
  "sso_enabled": true,
  "api_usage_tier": "standard"
}
```

---

## 5. MSPPremium Vertical Definition

### 5.1 Buyer & Use Case

| Attribute | Value |
|-----------|-------|
| **Target buyer** | MSP Practice Lead, CRO, VP Service Delivery |
| **Use case** | Managed Service Providers managing client portfolios |
| **Health model** | Service delivery-led with client satisfaction focus |
| **Key differentiator** | SLA compliance, multi-client operations, revenue per endpoint |

### 5.2 Pillar Structure (5 Pillars, 28 KPIs)

> **Alignment**: 5-pillar structure consistent with DC2_S and SaaSPremium verticals,
> following the platform pattern: P1=Usage/Delivery, P2=Support, P3=Sentiment, P4=Business, P5=Growth.

#### P1: Service Delivery & SLA Compliance (Weight L2: 0.25)

| Code | KPI Name | Weight L1 | Unit | Target | Direction |
|------|----------|-----------|------|--------|-----------|
| P1-KPI1 | SLA Compliance Rate | 0.20 | % | > 99% | higher |
| P1-KPI2 | Mean Time to Resolve (MTTR) | 0.15 | hours | < 4 | lower |
| P1-KPI3 | First Contact Resolution Rate | 0.15 | % | > 80% | higher |
| P1-KPI4 | Service Uptime | 0.15 | % | > 99.9% | higher |
| P1-KPI5 | Ticket Backlog Aging | 0.10 | avg days open | < 3 | lower |
| P1-KPI6 | Escalation Rate | 0.10 | % of tickets | < 5% | lower |
| P1-KPI7 | Proactive Issue Detection | 0.15 | % issues caught pre-impact | > 60% | higher |

#### P2: Support & Client Communication (Weight L2: 0.15)

| Code | KPI Name | Weight L1 | Unit | Target | Direction |
|------|----------|-----------|------|--------|-----------|
| P2-KPI1 | Client CSAT | 0.25 | score (1-5) | > 4.3 | higher |
| P2-KPI2 | QBR Completion Rate | 0.20 | % | > 95% | higher |
| P2-KPI3 | Client Escalation Frequency | 0.18 | per month | < 2 | lower |
| P2-KPI4 | Response Time Adherence | 0.18 | % within SLA | > 95% | higher |
| P2-KPI5 | Client Communication Score | 0.19 | score (1-10) | > 7 | higher |

#### P3: Client Sentiment & Retention (Weight L2: 0.20)

| Code | KPI Name | Weight L1 | Unit | Target | Direction |
|------|----------|-----------|------|--------|-----------|
| P3-KPI1 | Client NPS | 0.25 | score (-100 to 100) | > 45 | higher |
| P3-KPI2 | Renewal Rate | 0.25 | % | > 92% | higher |
| P3-KPI3 | Client Advocacy Score | 0.15 | referrals/year | > 2 | higher |
| P3-KPI4 | Contract Value Trend | 0.15 | % YoY | > 5% | higher |
| P3-KPI5 | Churn Risk Indicator | 0.20 | score (0-100) | < 30 | lower |

#### P4: Operational Efficiency & Revenue (Weight L2: 0.25)

| Code | KPI Name | Weight L1 | Unit | Target | Direction |
|------|----------|-----------|------|--------|-----------|
| P4-KPI1 | Revenue Per Endpoint (RPE) | 0.18 | $/endpoint/month | > 15 | higher |
| P4-KPI2 | Technician Utilization Rate | 0.17 | % | > 75% | higher |
| P4-KPI3 | Managed Endpoint Growth | 0.13 | % MoM | > 3% | higher |
| P4-KPI4 | Automation Rate | 0.15 | % automated resolutions | > 40% | higher |
| P4-KPI5 | Cost-to-Serve Ratio | 0.18 | % of revenue | < 65% | lower |
| P4-KPI6 | Tool Stack Utilization | 0.19 | % of licensed tools used | > 80% | higher |

#### P5: Growth & Expansion (Weight L2: 0.15)

| Code | KPI Name | Weight L1 | Unit | Target | Direction |
|------|----------|-----------|------|--------|-----------|
| P5-KPI1 | Service Expansion Rate | 0.25 | % new services/client/quarter | > 5% | higher |
| P5-KPI2 | Cross-Sell Penetration | 0.25 | % clients with 3+ services | > 40% | higher |
| P5-KPI3 | New Client Win Rate | 0.20 | % proposals won | > 35% | higher |
| P5-KPI4 | Client Lifetime Value Trend | 0.20 | % YoY change | > 10% | higher |
| P5-KPI5 | Strategic Partner Score | 0.10 | score (0-100) | > 60 | higher |

### 5.3 Power-of-1 Metrics (6 Levers)

| Metric | Linked KPIs | Annual Impact per 1% | Category |
|--------|-------------|---------------------|----------|
| **Client Retention** | P3-KPI2, P2-KPI1, P1-KPI1 | $92,000 @ $10M MRR | retention_shield |
| **Revenue Per Endpoint** | P4-KPI1, P4-KPI3 | $78,000 @ $10M MRR | revenue_multiplier |
| **Service Expansion** | P5-KPI1, P5-KPI2 | $85,000 @ $10M MRR | growth_lever |
| **Operational Efficiency** | P4-KPI2, P4-KPI4, P4-KPI5 | $65,000 @ $10M MRR | cost_optimization |
| **SLA Compliance** | P1-KPI1, P1-KPI2, P1-KPI4 | $55,000 @ $10M MRR | foundation_investment |
| **Client Satisfaction** | P2-KPI1, P3-KPI1, P2-KPI5 | $45,000 @ $10M MRR | relationship_driver |

### 5.4 Journey Phases

| Phase | Duration | Focus Pillars | Entry Criteria | Exit Criteria |
|-------|----------|--------------|----------------|---------------|
| **Service Onboarding** | 0-45 days | P1 (Delivery), P2 (Support) | Contract signed | SLA > 95%, MTTR < 8 hrs |
| **Steady-State Ops** | 45-180 days | P1 + P3 (Sentiment) | SLA met | CSAT > 4.0, Renewal intent confirmed |
| **Strategic Partnership** | 180+ days | P4 (Efficiency) + P5 (Growth) | Client stable | RPE growing, Cross-sell > 30% |

### 5.5 Playbooks (7)

| ID | Name | Phase | Trigger Conditions |
|----|------|-------|-------------------|
| PB-01 | Onboarding Accelerator | Service Onboarding | SLA < 90% in first 30 days (P1) |
| PB-02 | SLA Recovery | Any | SLA < 97% for 2 consecutive weeks (P1) |
| PB-03 | Client Save | Any | CSAT < 3.5 (P2) OR NPS < 20 (P3) |
| PB-04 | Service Expansion Proposal | Strategic Partnership | Cross-sell < 30% AND RPE growing (P5) |
| PB-05 | Operational Efficiency Audit | Steady-State | Cost-to-serve > 70% for 3 months (P4) |
| PB-06 | Automation Uplift | Steady-State | Automation rate < 30% (P4) AND ticket volume > threshold |
| PB-07 | Relationship Deepening | Steady-State+ | Communication score < 5 (P2) AND NPS declining (P3) |

### 5.6 Story Arcs (4 Initial)

| Arc | Narrative | Target Audience |
|-----|-----------|-----------------|
| `arc_sla_breach_cascade` | SLA failures cascade into client escalations | VP Service Delivery |
| `arc_endpoint_explosion` | Rapid endpoint growth strains service capacity | MSP Practice Lead |
| `arc_client_consolidation` | Client consolidates MSP vendors, retention at risk | CRO |
| `arc_automation_transformation` | MSP deploys automation, transforms cost structure | CTO/CRO |

### 5.7 Metadata Schema

```json
{
  "vertical": "msp_premium",
  "service_start_date": "2025-03-01",
  "contract_type": "managed_services|co_managed|break_fix",
  "contract_term_months": 36,
  "managed_endpoints": 2500,
  "managed_servers": 45,
  "managed_network_devices": 120,
  "service_tiers_active": ["silver", "gold"],
  "sla_tier": "gold",
  "response_time_target_hours": 1,
  "resolution_time_target_hours": 4,
  "industry": "healthcare",
  "client_size": "mid_market",
  "mrr": 37500,
  "arr": 450000,
  "technicians_assigned": 3,
  "rmm_tool": "ConnectWise|Datto|NinjaRMM|Kaseya",
  "psa_tool": "ConnectWise_Manage|Autotask|HaloPSA",
  "backup_solution": "Veeam|Datto_BCDR|Acronis",
  "security_stack": ["EDR", "MDR", "SIEM"],
  "journey_phase": "steady_state",
  "phase_entry_date": "2025-06-01",
  "account_manager": "Sarah Johnson"
}
```

---

## 6. Platform Refactoring: From Hardcoded to Config-Driven

### 6.1 New: Vertical Loader Service (`backend/vertical_loader_v2.py`)

A single Python module that replaces all hardcoded vertical imports:

```python
class VerticalRegistry:
    """Discovers and loads verticals from config/verticals/{slug}/ directories."""

    def __init__(self, config_dir: Path):
        self._verticals: Dict[str, VerticalDefinition] = {}
        self._discover(config_dir)

    def _discover(self, config_dir: Path):
        """Auto-discover verticals by scanning config/verticals/*/manifest.json"""
        for manifest_path in config_dir.glob('*/manifest.json'):
            slug = manifest_path.parent.name
            self._verticals[slug] = VerticalDefinition.load(manifest_path.parent)

    def get(self, slug: str) -> VerticalDefinition:
        """Get a vertical's full definition."""
        return self._verticals[slug]

    def list_all(self) -> List[str]:
        """List all available vertical slugs."""
        return list(self._verticals.keys())

    def get_kpi_catalog(self, slug: str) -> Dict[str, KpiDef]:
        """Get the KPI catalog for a vertical."""
        return self._verticals[slug].kpi_catalog

    def get_terminology(self, slug: str) -> Dict[str, str]:
        """Get terminology overrides for a vertical."""
        return self._verticals[slug].terminology

class VerticalDefinition:
    """Parsed representation of a vertical's config directory."""

    slug: str
    manifest: dict         # manifest.json
    kpi_catalog: dict      # kpi_definitions.json (parsed)
    pillars: list          # Extracted from kpi_definitions
    power_of_1: dict       # power_of_1_metrics.json
    default_weights: dict  # default_weights.json (L1 + L2)
    playbooks: dict        # playbooks.json
    journey_phases: list   # journey_phases.json
    metadata_schema: dict  # metadata_schema.json
    terminology: dict      # terminology.json
    onboarding_tiers: list # onboarding_tiers.json
    story_arcs: list       # story_arcs/*.json
```

**Usage across codebase** (replaces `from verticals.dc2_s.kpi_definitions import DC2S_KPIS`):

```python
from vertical_loader_v2 import vertical_registry

# Get KPIs for any vertical
kpis = vertical_registry.get_kpi_catalog(customer.vertical)
pillars = vertical_registry.get(customer.vertical).pillars
weights = vertical_registry.get(customer.vertical).default_weights
terminology = vertical_registry.get_terminology(customer.vertical)
```

### 6.2 DB Model Changes

#### Option A: Generic Vertical Fields (Recommended)

Replace DC2S-prefixed fields with generic ones:

```python
class CustomerConfig(db.Model):
    # REPLACE dc2s_* fields with generic vertical fields
    vertical = Column(String(50), default='dc2_s')
    pillar_weights = Column(JSON)       # Was: dc2s_pillar_weights
    enabled_kpis = Column(JSON)         # Was: dc2s_enabled_kpis
    kpi_overrides = Column(JSON)        # Was: dc2s_kpi_overrides
    kpi_weights = Column(JSON)          # Was: dc2s_kpi_weights
    custom_kpi_definitions = Column(JSON)  # Was: dc2s_kpi_definitions
```

**Migration**: Add generic columns, copy `dc2s_*` data, keep `dc2s_*` as deprecated aliases.

#### Option B: Separate Config Table per Customer+Vertical

```python
class VerticalConfig(db.Model):
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey('customers.customer_id'))
    vertical_slug = Column(String(50))
    pillar_weights = Column(JSON)
    enabled_kpis = Column(JSON)
    kpi_weights = Column(JSON)
    # ... vertical-neutral field names
    __table_args__ = (UniqueConstraint('customer_id', 'vertical_slug'),)
```

**Recommendation**: Option A for simplicity (one customer = one vertical). Option B if a customer can subscribe to multiple verticals simultaneously.

### 6.3 Score Calculator Refactoring

Current: `ScoreCalculator` hardcodes `DC2S_KPIS` import.

**Change**: Accept vertical slug, load definitions from registry.

```python
class ScoreCalculator:
    def __init__(self, customer_id: int):
        customer = Customer.query.get(customer_id)
        self.vertical = customer.vertical or 'dc2_s'
        self.vdef = vertical_registry.get(self.vertical)
        # Now uses self.vdef.kpi_catalog instead of DC2S_KPIS
```

### 6.4 API Routes: Generic Vertical Blueprint

Instead of separate blueprints per vertical, create ONE generic blueprint that dispatches based on the customer's vertical:

```python
# backend/vertical_api.py (replaces verticals/dc2_s/api_routes.py for new verticals)

vertical_api = Blueprint('vertical_api', __name__)

@vertical_api.route('/api/v/<vertical_slug>/health/<int:account_id>')
def get_health(vertical_slug, account_id):
    vdef = vertical_registry.get(vertical_slug)
    # Generic health calculation using vdef.pillars, vdef.kpi_catalog
    ...
```

**Note**: The existing `dc2_s` blueprint remains unchanged (backward compatibility). New verticals use the generic blueprint.

### 6.5 Onboarding API Changes

```python
# onboarding_api_v2_config_aware.py

def complete_onboarding(request_data):
    vertical = request_data.get('vertical', 'dc2_s')
    vdef = vertical_registry.get(vertical)

    # Validate against vertical's KPI catalog
    if request_data.get('enabled_kpis'):
        valid_codes = set(vdef.kpi_catalog.keys())
        invalid = set(request_data['enabled_kpis']) - valid_codes
        if invalid:
            return error(f"Invalid KPI codes for {vertical}: {invalid}")

    # Use vertical's default weights
    weights = request_data.get('weights') or vdef.default_weights['pillar_weights_l2']
```

### 6.6 Frontend: Dynamic Vertical Loading

```typescript
// New: src/utils/verticalLoader.ts

interface VerticalDefinition {
  slug: string;
  manifest: VerticalManifest;
  kpiCatalog: Record<string, KpiDef>;
  pillars: PillarDef[];
  terminology: Record<string, string>;
  onboardingTiers: OnboardingTier[];
}

// API endpoint: GET /api/verticals/{slug}/definition
async function loadVerticalDefinition(slug: string): Promise<VerticalDefinition> {
  const res = await fetch(`/api/verticals/${slug}/definition`);
  return res.json();
}
```

The Test Runner's `KPI_CATALOG` would be loaded dynamically:

```typescript
// Instead of hardcoded KPI_CATALOG in types.ts
const [verticalDef, setVerticalDef] = useState<VerticalDefinition | null>(null);

useEffect(() => {
  loadVerticalDefinition(customerVertical).then(setVerticalDef);
}, [customerVertical]);
```

### 6.7 Test Runner & Load Driver

```python
# test_runner_api.py — detect vertical from customer or request
vertical = options.get('vertical', 'dc2_s')

# load-driver/run_scenario.py — new flag
parser.add_argument('--vertical', default='dc2_s', help='Vertical slug')
```

---

## 7. Implementation Phases

### Phase 1: Foundation (2 weeks)

**Goal**: Create the vertical loader and config format without breaking dc2_s.

| Task | Files | Effort |
|------|-------|--------|
| Create `config/verticals/dc2_s/` directory and extract dc2_s config to JSON | kpi_definitions.json, default_weights.json, playbooks.json, etc. | 3 days |
| Build `VerticalRegistry` and `VerticalDefinition` classes | `backend/vertical_loader_v2.py` | 2 days |
| Add `GET /api/verticals/{slug}/definition` endpoint | `backend/vertical_api.py` | 1 day |
| Add terminology.json for dc2_s (current labels = default) | `config/verticals/dc2_s/terminology.json` | 0.5 day |
| DB migration: add generic vertical fields alongside dc2s_* | `migrations/add_generic_vertical_fields.py` | 1 day |
| Update score_calculator to optionally use registry | `utils/score_calculator.py` | 1 day |
| Verify dc2_s still works end-to-end | All 12 scenarios | 1 day |

**Deliverable**: dc2_s runs identically, but its definitions are now also loadable from JSON.

### Phase 2: SaaSPremium Vertical (1.5 weeks)

| Task | Files | Effort |
|------|-------|--------|
| Create `config/verticals/saas_premium/` with all JSON files | 9 config files + 4 story arcs | 3 days |
| Write CSV generator for SaaS KPIs | `load-driver/saas_csv_generator.py` | 1 day |
| Create onboarding scenario for SaaS vertical | `load-driver/scenarios/scenario_saas_onboarding.py` | 1 day |
| Verify score calculation, Power-of-1, playbooks | Integration tests | 1.5 days |
| Frontend: load vertical definition dynamically in Test Runner | `DCTestRunner.tsx`, `ScenariosTab.tsx` | 1.5 days |

### Phase 3: MSPPremium Vertical (1 week)

| Task | Files | Effort |
|------|-------|--------|
| Create `config/verticals/msp_premium/` with all JSON files | 9 config files + 4 story arcs | 2 days |
| Write CSV generator for MSP KPIs | `load-driver/msp_csv_generator.py` | 1 day |
| Verify full E2E pipeline | Onboarding + scoring + ROI | 2 days |

### Phase 4: Multi-Vertical UI (1 week)

| Task | Files | Effort |
|------|-------|--------|
| Add vertical selector to onboarding flow | Frontend + onboarding API | 2 days |
| Apply terminology overlays to dashboard labels | Dashboard components | 2 days |
| Vertical-aware customer list and filters | Platform State tab | 1 day |

---

## 8. Migration Strategy

### 8.1 Backward Compatibility

- All `dc2s_*` DB columns remain (deprecated aliases)
- The `dc2_s` Flask blueprint stays registered at `/api/dc2s/`
- Existing customers with `vertical='dc2_s'` work unchanged
- New verticals use the generic `/api/v/{slug}/` routes

### 8.2 Data Model Transition

```
Phase 1: dc2s_pillar_weights → copied to → pillar_weights (both exist)
Phase 2: New customers write to generic fields only
Phase 3: Migration script copies dc2s_* → generic for existing customers
Phase 4: (Future) Remove dc2s_* columns
```

### 8.3 Feature Toggle

```python
# feature_toggles.py
MULTI_VERTICAL = FeatureToggle(
    name='multi_vertical',
    default=False,
    description='Enable multi-vertical support (SaaS Premium, MSP Premium)'
)
```

---

## 9. Playbook Customization Strategy

Playbooks are the most domain-specific component. Each vertical needs its own playbooks because:

1. **Trigger conditions reference vertical-specific KPIs** (e.g., `P1-KPI1` = "SLA Compliance" in MSP vs. "DAU" in SaaS)
2. **Actions use vertical-specific language** (e.g., "Schedule QBR" vs. "Schedule Service Review")
3. **Success criteria differ** (e.g., "NPS > 50" vs. "CSAT > 4.3")
4. **Playbook templates should reference the terminology overlay** for labels

### Playbook Config Structure

```json
{
  "playbooks": [
    {
      "id": "PB-01",
      "name": "Adoption Accelerator",
      "phase": "onboarding",
      "urgency": "high",
      "estimated_effort_hours": 4,
      "triggers": {
        "conditions": [
          { "kpi": "P1-KPI4", "operator": ">", "value": 21, "label": "TTFV exceeds 21 days" },
          { "kpi": "P1-KPI1", "operator": "<", "value": 30, "label": "DAU below 30%" }
        ],
        "logic": "ANY"
      },
      "actions": [
        {
          "step": 1,
          "action": "Reach out to {{terminology.csm}} for immediate review",
          "channel": "email",
          "template_id": "adoption_stall_outreach"
        },
        {
          "step": 2,
          "action": "Schedule training session on underutilized features",
          "channel": "calendar",
          "template_id": "feature_training_invite"
        }
      ],
      "success_criteria": {
        "kpi": "P1-KPI1",
        "operator": ">",
        "value": 50,
        "within_days": 30,
        "label": "DAU reaches 50% within 30 days"
      },
      "linked_power_of_1": "product_adoption",
      "projected_impact_formula": "annual_impact_per_pct * 2.5"
    }
  ]
}
```

**Template Variables**: Playbook action descriptions support `{{terminology.*}}` interpolation from the vertical's `terminology.json`, ensuring domain-specific language in all customer-facing outputs.

---

## 10. CSV Schemas, Complete Weights & Data Definitions

### 10.1 CSV File Inventory (15 Files per Vertical)

Each vertical generates the same 15-CSV structure. The **column schema is shared** (`config/csv_schemas.json`), but the **data values, KPI codes, and signal types are vertical-specific**.

#### Regular Model (6 CSVs)

| # | File | Key Columns | Vertical-Specific Content |
|---|------|-------------|---------------------------|
| 1 | `accounts.csv` | account_id, account_name, arr, vertical, uuid, status, profile_metadata | `vertical` field, `profile_metadata` JSON (SaaS: licensed_seats, modules; MSP: managed_endpoints, sla_tier) |
| 2 | `kpi_measurements.csv` | account_id, kpi_code, value, measurement_date, unit, vertical | KPI codes from vertical's catalog (SaaS: P1-KPI1 through P4-KPI4; MSP: P1-KPI1 through P4-KPI4). Different value ranges per KPI. |
| 3 | `qualitative_signals.csv` | account_id, signal_type, severity, description, detected_at, source | Signal types from vertical's catalog (SaaS: `login_drop`, `feature_abandonment`; MSP: `sla_breach`, `ticket_surge`) |
| 4 | `products.csv` | account_id, product_name, product_category, status, arr_contribution | SaaS: modules (Core, Analytics, AI Copilot); MSP: services (Managed Endpoints, MDR, Backup, vCIO) |
| 5 | `profiles.csv` | account_id, profile_key, profile_value | Metadata key-value pairs matching vertical's `metadata_schema.json` |
| 6 | `customers.csv` | customer_id, customer_name, industry, vertical, created_at | `vertical` field set to vertical slug |

#### Context Graph Model (9 additional CSVs)

| # | File | Key Columns | Vertical-Specific Content |
|---|------|-------------|---------------------------|
| 7 | `stakeholders.csv` | account_id, name, role, influence, sentiment | SaaS roles: VP Engineering, Product Manager, End User Champion; MSP roles: vCIO, NOC Manager, Service Desk Lead |
| 8 | `engagement_events.csv` | account_id, event_type, event_date, participants, outcome | SaaS: QBR, Training Session, Feature Demo; MSP: Service Review, SLA Review, Incident Postmortem |
| 9 | `account_business_profiles.csv` | account_id, segment, growth_stage, risk_level | Vertical-specific segmentation |
| 10 | `decisions.csv` | account_id, decision_type, decision_date, stakeholders, outcome | SaaS: Expansion, Renewal, Module Activation; MSP: Service Tier Upgrade, Contract Extension, Tool Consolidation |
| 11 | `outcomes.csv` | account_id, outcome_type, outcome_date, revenue_impact | Vertical-specific outcome taxonomy |
| 12 | `signal_edges.csv` | source_node_id, target_node_id, edge_type, weight | Same schema, edges reference vertical-specific nodes |
| 13 | `decision_evidence.csv` | decision_id, evidence_type, source_signal_id | Same schema |
| 14 | `industry_benchmarks.csv` | industry, kpi_code, benchmark_value, percentile | KPI codes and ranges from vertical's catalog |
| 15 | `enhanced_qualitative_signals.csv` | account_id, signal_type, description, causal_links | Vertical-specific signal types + causal chain references |

### 10.2 SaaSPremium: Complete `default_weights.json`

> **Alignment**: Matches existing `build_saas_config()` pillar structure in `vertical_config.py`:
> usage_onboarding=0.25, support_engagement=0.15, sentiment=0.20, business_outcomes=0.25, relationship=0.15

```json
{
  "version": "1.0.0",
  "vertical": "saas_premium",
  "pillar_weights_L2": {
    "P1": 0.25,
    "P2": 0.15,
    "P3": 0.20,
    "P4": 0.25,
    "P5": 0.15
  },
  "kpi_weights_L1": {
    "P1": {
      "P1-KPI1": 0.15,
      "P1-KPI2": 0.15,
      "P1-KPI3": 0.12,
      "P1-KPI4": 0.14,
      "P1-KPI5": 0.14,
      "P1-KPI6": 0.15,
      "P1-KPI7": 0.15
    },
    "P2": {
      "P2-KPI1": 0.18,
      "P2-KPI2": 0.20,
      "P2-KPI3": 0.18,
      "P2-KPI4": 0.17,
      "P2-KPI5": 0.12,
      "P2-KPI6": 0.15
    },
    "P3": {
      "P3-KPI1": 0.25,
      "P3-KPI2": 0.20,
      "P3-KPI3": 0.15,
      "P3-KPI4": 0.10,
      "P3-KPI5": 0.15,
      "P3-KPI6": 0.15
    },
    "P4": {
      "P4-KPI1": 0.22,
      "P4-KPI2": 0.18,
      "P4-KPI3": 0.12,
      "P4-KPI4": 0.15,
      "P4-KPI5": 0.15,
      "P4-KPI6": 0.10,
      "P4-KPI7": 0.08
    },
    "P5": {
      "P5-KPI1": 0.20,
      "P5-KPI2": 0.18,
      "P5-KPI3": 0.18,
      "P5-KPI4": 0.24,
      "P5-KPI5": 0.10,
      "P5-KPI6": 0.10
    }
  },
  "notes": {
    "L2_sum": "P1(0.25) + P2(0.15) + P3(0.20) + P4(0.25) + P5(0.15) = 1.00",
    "L1_sums": "Each pillar's L1 weights sum to 1.00",
    "pillar_mapping": "P1=Product Adoption, P2=Support, P3=Sentiment, P4=Business Outcomes, P5=Relationship & Expansion",
    "calibration": "Initial defaults; Wizard C recalibrates per customer",
    "alignment": "Mirrors build_saas_config() in vertical_config.py"
  }
}
```

### 10.3 MSPPremium: Complete `default_weights.json`

```json
{
  "version": "1.0.0",
  "vertical": "msp_premium",
  "pillar_weights_L2": {
    "P1": 0.25,
    "P2": 0.15,
    "P3": 0.20,
    "P4": 0.25,
    "P5": 0.15
  },
  "kpi_weights_L1": {
    "P1": {
      "P1-KPI1": 0.20,
      "P1-KPI2": 0.15,
      "P1-KPI3": 0.15,
      "P1-KPI4": 0.15,
      "P1-KPI5": 0.10,
      "P1-KPI6": 0.10,
      "P1-KPI7": 0.15
    },
    "P2": {
      "P2-KPI1": 0.25,
      "P2-KPI2": 0.20,
      "P2-KPI3": 0.18,
      "P2-KPI4": 0.18,
      "P2-KPI5": 0.19
    },
    "P3": {
      "P3-KPI1": 0.25,
      "P3-KPI2": 0.25,
      "P3-KPI3": 0.15,
      "P3-KPI4": 0.15,
      "P3-KPI5": 0.20
    },
    "P4": {
      "P4-KPI1": 0.18,
      "P4-KPI2": 0.17,
      "P4-KPI3": 0.13,
      "P4-KPI4": 0.15,
      "P4-KPI5": 0.18,
      "P4-KPI6": 0.19
    },
    "P5": {
      "P5-KPI1": 0.25,
      "P5-KPI2": 0.25,
      "P5-KPI3": 0.20,
      "P5-KPI4": 0.20,
      "P5-KPI5": 0.10
    }
  },
  "notes": {
    "L2_sum": "P1(0.25) + P2(0.15) + P3(0.20) + P4(0.25) + P5(0.15) = 1.00",
    "L1_sums": "Each pillar's L1 weights sum to 1.00",
    "pillar_mapping": "P1=Service Delivery, P2=Support & Comms, P3=Client Sentiment, P4=Operational Efficiency, P5=Growth & Expansion",
    "calibration": "SLA-heavy weighting (P1+P4=0.50) reflects MSP service delivery focus"
  }
}
```

### 10.4 SaaSPremium: Complete KPI Definitions with Ranges (30 KPIs, 5 Pillars)

| Code | Name | Pillar | L1 Weight | Unit | Target | Healthy Range | At-Risk Range | Critical Range | Direction |
|------|------|--------|-----------|------|--------|---------------|---------------|----------------|-----------|
| P1-KPI1 | Daily Active Users (DAU) | P1 | 0.15 | % | > 80 | 80-100 | 50-80 | 0-50 | higher |
| P1-KPI2 | Feature Adoption Breadth | P1 | 0.15 | % | > 60 | 60-100 | 35-60 | 0-35 | higher |
| P1-KPI3 | Login Frequency | P1 | 0.12 | sessions/wk | > 3 | 3-10 | 1.5-3 | 0-1.5 | higher |
| P1-KPI4 | Time-to-First-Value (TTFV) | P1 | 0.14 | days | < 14 | 0-14 | 14-28 | 28-90 | lower |
| P1-KPI5 | Power User Ratio | P1 | 0.14 | % | > 25 | 25-60 | 10-25 | 0-10 | higher |
| P1-KPI6 | API Integration Depth | P1 | 0.15 | count | > 3 | 3-20 | 1-3 | 0-1 | higher |
| P1-KPI7 | Module Penetration Rate | P1 | 0.15 | % | > 70 | 70-100 | 40-70 | 0-40 | higher |
| P2-KPI1 | Support Ticket Volume | P2 | 0.18 | tickets/mo | < 5 | 0-5 | 5-12 | 12-50 | lower |
| P2-KPI2 | CSAT (Support) | P2 | 0.20 | score | > 4.2 | 4.2-5.0 | 3.5-4.2 | 1.0-3.5 | higher |
| P2-KPI3 | First Response Time | P2 | 0.18 | hours | < 4 | 0-4 | 4-8 | 8-24 | lower |
| P2-KPI4 | Ticket Resolution Time | P2 | 0.17 | hours | < 36 | 0-36 | 36-72 | 72-168 | lower |
| P2-KPI5 | Escalation Rate | P2 | 0.12 | % | < 5 | 0-5 | 5-12 | 12-30 | lower |
| P2-KPI6 | Self-Service Ratio | P2 | 0.15 | % | > 40 | 40-80 | 20-40 | 0-20 | higher |
| P3-KPI1 | NPS Score | P3 | 0.25 | score | > 50 | 50-100 | 20-50 | -100-20 | higher |
| P3-KPI2 | Executive Sponsor Engagement | P3 | 0.20 | touchpoints/mo | > 2 | 2-8 | 1-2 | 0-1 | higher |
| P3-KPI3 | QBR Attendance Rate | P3 | 0.15 | % | > 90 | 90-100 | 70-90 | 0-70 | higher |
| P3-KPI4 | Community Participation | P3 | 0.10 | posts/mo | > 3 | 3-20 | 1-3 | 0-1 | higher |
| P3-KPI5 | Training Completion Rate | P3 | 0.15 | % | > 75 | 75-100 | 40-75 | 0-40 | higher |
| P3-KPI6 | Sentiment Trend | P3 | 0.15 | score | > 7 | 7-10 | 4-7 | 0-4 | higher |
| P4-KPI1 | Net Revenue Retention (NRR) | P4 | 0.22 | % | > 110 | 110-150 | 95-110 | 0-95 | higher |
| P4-KPI2 | Gross Revenue Retention (GRR) | P4 | 0.18 | % | > 95 | 95-100 | 85-95 | 0-85 | higher |
| P4-KPI3 | Invoice Payment Timeliness | P4 | 0.12 | days past due | < 5 | 0-5 | 5-15 | 15-60 | lower |
| P4-KPI4 | Contract Utilization Rate | P4 | 0.15 | % | > 80 | 80-100 | 50-80 | 0-50 | higher |
| P4-KPI5 | Expansion Pipeline Value | P4 | 0.15 | % of ARR | > 20 | 20-80 | 8-20 | 0-8 | higher |
| P4-KPI6 | Discount Trend | P4 | 0.10 | % | < 15 | 0-15 | 15-30 | 30-60 | lower |
| P4-KPI7 | Value Realization Score | P4 | 0.08 | score | > 70 | 70-100 | 40-70 | 0-40 | higher |
| P5-KPI1 | Seat Utilization Rate | P5 | 0.20 | % | > 85 | 85-100 | 60-85 | 0-60 | higher |
| P5-KPI2 | Usage Growth Velocity | P5 | 0.18 | % MoM | > 5 | 5-25 | 0-5 | -20-0 | higher |
| P5-KPI3 | Cross-Sell Opportunity Score | P5 | 0.18 | score | > 60 | 60-100 | 30-60 | 0-30 | higher |
| P5-KPI4 | Expansion Probability (90d) | P5 | 0.24 | % | > 50 | 50-95 | 25-50 | 0-25 | higher |
| P5-KPI5 | Champion Count | P5 | 0.10 | count | > 3 | 3-10 | 1-3 | 0-1 | higher |
| P5-KPI6 | Multi-Thread Depth | P5 | 0.10 | contacts | > 5 | 5-15 | 2-5 | 0-2 | higher |

### 10.5 MSPPremium: Complete KPI Definitions with Ranges (28 KPIs, 5 Pillars)

| Code | Name | Pillar | L1 Weight | Unit | Target | Healthy Range | At-Risk Range | Critical Range | Direction |
|------|------|--------|-----------|------|--------|---------------|---------------|----------------|-----------|
| P1-KPI1 | SLA Compliance Rate | P1 | 0.20 | % | > 99 | 99-100 | 95-99 | 0-95 | higher |
| P1-KPI2 | Mean Time to Resolve (MTTR) | P1 | 0.15 | hours | < 4 | 0-4 | 4-8 | 8-48 | lower |
| P1-KPI3 | First Contact Resolution Rate | P1 | 0.15 | % | > 80 | 80-100 | 60-80 | 0-60 | higher |
| P1-KPI4 | Service Uptime | P1 | 0.15 | % | > 99.9 | 99.9-100 | 99.0-99.9 | 0-99.0 | higher |
| P1-KPI5 | Ticket Backlog Aging | P1 | 0.10 | days | < 3 | 0-3 | 3-7 | 7-30 | lower |
| P1-KPI6 | Escalation Rate | P1 | 0.10 | % | < 5 | 0-5 | 5-12 | 12-30 | lower |
| P1-KPI7 | Proactive Issue Detection | P1 | 0.15 | % | > 60 | 60-100 | 35-60 | 0-35 | higher |
| P2-KPI1 | Client CSAT | P2 | 0.25 | score | > 4.3 | 4.3-5.0 | 3.5-4.3 | 1.0-3.5 | higher |
| P2-KPI2 | QBR Completion Rate | P2 | 0.20 | % | > 95 | 95-100 | 80-95 | 0-80 | higher |
| P2-KPI3 | Client Escalation Frequency | P2 | 0.18 | per month | < 2 | 0-2 | 2-5 | 5-20 | lower |
| P2-KPI4 | Response Time Adherence | P2 | 0.18 | % | > 95 | 95-100 | 85-95 | 0-85 | higher |
| P2-KPI5 | Client Communication Score | P2 | 0.19 | score | > 7 | 7-10 | 4-7 | 0-4 | higher |
| P3-KPI1 | Client NPS | P3 | 0.25 | score | > 45 | 45-100 | 15-45 | -100-15 | higher |
| P3-KPI2 | Renewal Rate | P3 | 0.25 | % | > 92 | 92-100 | 80-92 | 0-80 | higher |
| P3-KPI3 | Client Advocacy Score | P3 | 0.15 | referrals/yr | > 2 | 2-8 | 1-2 | 0-1 | higher |
| P3-KPI4 | Contract Value Trend | P3 | 0.15 | % YoY | > 5 | 5-25 | 0-5 | -15-0 | higher |
| P3-KPI5 | Churn Risk Indicator | P3 | 0.20 | score | < 30 | 0-30 | 30-60 | 60-100 | lower |
| P4-KPI1 | Revenue Per Endpoint (RPE) | P4 | 0.18 | $/endpoint/mo | > 15 | 15-40 | 8-15 | 0-8 | higher |
| P4-KPI2 | Technician Utilization Rate | P4 | 0.17 | % | > 75 | 75-95 | 55-75 | 0-55 | higher |
| P4-KPI3 | Managed Endpoint Growth | P4 | 0.13 | % MoM | > 3 | 3-15 | 0-3 | -10-0 | higher |
| P4-KPI4 | Automation Rate | P4 | 0.15 | % | > 40 | 40-80 | 20-40 | 0-20 | higher |
| P4-KPI5 | Cost-to-Serve Ratio | P4 | 0.18 | % | < 65 | 0-65 | 65-80 | 80-100 | lower |
| P4-KPI6 | Tool Stack Utilization | P4 | 0.19 | % | > 80 | 80-100 | 50-80 | 0-50 | higher |
| P5-KPI1 | Service Expansion Rate | P5 | 0.25 | % | > 5 | 5-20 | 2-5 | 0-2 | higher |
| P5-KPI2 | Cross-Sell Penetration | P5 | 0.25 | % | > 40 | 40-80 | 20-40 | 0-20 | higher |
| P5-KPI3 | New Client Win Rate | P5 | 0.20 | % | > 35 | 35-60 | 20-35 | 0-20 | higher |
| P5-KPI4 | Client Lifetime Value Trend | P5 | 0.20 | % YoY | > 10 | 10-40 | 0-10 | -20-0 | higher |
| P5-KPI5 | Strategic Partner Score | P5 | 0.10 | score | > 60 | 60-100 | 30-60 | 0-30 | higher |

### 10.6 SaaSPremium: Complete `power_of_1_metrics.json` (6 Levers)

```json
{
  "version": "1.0.0",
  "vertical": "saas_premium",
  "arr_baseline": 10000000,
  "metrics": {
    "NRR": {
      "label": "Net Revenue Retention",
      "baseline": 108,
      "one_pct_move": 1.08,
      "annual_impact_per_pct": 100000,
      "total_investment": 120000,
      "roi_at_1pct": -0.17,
      "category": "revenue_multiplier",
      "primary_pillar": "P4",
      "linked_kpi_codes": ["P4-KPI1", "P5-KPI2"],
      "linked_playbooks": ["PB-04"],
      "work_packages": [
        {"name": "Expansion playbook design", "cost": 35000, "hours": 120},
        {"name": "CSM expansion training", "cost": 25000, "hours": 80},
        {"name": "Usage analytics dashboard", "cost": 60000, "hours": 200}
      ]
    },
    "GRR": {
      "label": "Gross Revenue Retention",
      "baseline": 94,
      "one_pct_move": 0.94,
      "annual_impact_per_pct": 95000,
      "total_investment": 95000,
      "roi_at_1pct": 0.00,
      "category": "retention_shield",
      "primary_pillar": "P4",
      "linked_kpi_codes": ["P4-KPI2", "P3-KPI1", "P2-KPI1"],
      "linked_playbooks": ["PB-03", "PB-05"]
    },
    "product_adoption": {
      "label": "Product Adoption",
      "baseline": 62,
      "one_pct_move": 0.62,
      "annual_impact_per_pct": 72000,
      "total_investment": 85000,
      "roi_at_1pct": -0.15,
      "category": "usage_driver",
      "primary_pillar": "P1",
      "linked_kpi_codes": ["P1-KPI1", "P1-KPI2", "P1-KPI5"],
      "linked_playbooks": ["PB-01", "PB-07"]
    },
    "expansion_rate": {
      "label": "Expansion Rate",
      "baseline": 18,
      "one_pct_move": 0.18,
      "annual_impact_per_pct": 85000,
      "total_investment": 75000,
      "roi_at_1pct": 0.13,
      "category": "growth_lever",
      "primary_pillar": "P5",
      "linked_kpi_codes": ["P5-KPI1", "P5-KPI4", "P4-KPI5"],
      "linked_playbooks": ["PB-04"]
    },
    "TTFV": {
      "label": "Time to First Value",
      "baseline": 18,
      "one_pct_move": 0.18,
      "annual_impact_per_pct": 61250,
      "total_investment": 75500,
      "roi_at_1pct": -0.19,
      "category": "foundation_investment",
      "primary_pillar": "P1",
      "linked_kpi_codes": ["P1-KPI4"],
      "linked_playbooks": ["PB-01"]
    },
    "ticket_resolution_time": {
      "label": "Ticket Resolution Time",
      "baseline": 36,
      "one_pct_move": 0.36,
      "annual_impact_per_pct": 48000,
      "total_investment": 55000,
      "roi_at_1pct": -0.13,
      "category": "operational_efficiency",
      "primary_pillar": "P2",
      "linked_kpi_codes": ["P2-KPI4", "P2-KPI2"],
      "linked_playbooks": ["PB-06"]
    }
  }
}
```

### 10.7 MSPPremium: Complete `power_of_1_metrics.json`

```json
{
  "version": "1.0.0",
  "vertical": "msp_premium",
  "arr_baseline": 10000000,
  "metrics": {
    "client_retention": {
      "label": "Client Retention",
      "baseline": 91,
      "one_pct_move": 0.91,
      "annual_impact_per_pct": 92000,
      "total_investment": 88000,
      "roi_at_1pct": 0.05,
      "category": "retention_shield",
      "primary_pillar": "P3",
      "linked_kpi_codes": ["P3-KPI2", "P2-KPI1", "P1-KPI1"],
      "linked_playbooks": ["PB-03"]
    },
    "revenue_per_endpoint": {
      "label": "Revenue Per Endpoint",
      "baseline": 14.5,
      "one_pct_move": 0.145,
      "annual_impact_per_pct": 78000,
      "total_investment": 65000,
      "roi_at_1pct": 0.20,
      "category": "revenue_multiplier",
      "primary_pillar": "P4",
      "linked_kpi_codes": ["P4-KPI1", "P4-KPI3"],
      "linked_playbooks": ["PB-04"]
    },
    "service_expansion": {
      "label": "Service Expansion",
      "baseline": 12,
      "one_pct_move": 0.12,
      "annual_impact_per_pct": 85000,
      "total_investment": 70000,
      "roi_at_1pct": 0.21,
      "category": "growth_lever",
      "primary_pillar": "P5",
      "linked_kpi_codes": ["P5-KPI1", "P5-KPI2"],
      "linked_playbooks": ["PB-04"]
    },
    "operational_efficiency": {
      "label": "Operational Efficiency",
      "baseline": 68,
      "one_pct_move": 0.68,
      "annual_impact_per_pct": 65000,
      "total_investment": 55000,
      "roi_at_1pct": 0.18,
      "category": "cost_optimization",
      "primary_pillar": "P4",
      "linked_kpi_codes": ["P4-KPI2", "P4-KPI4", "P4-KPI5"],
      "linked_playbooks": ["PB-05", "PB-06"]
    },
    "sla_compliance": {
      "label": "SLA Compliance",
      "baseline": 97.5,
      "one_pct_move": 0.975,
      "annual_impact_per_pct": 55000,
      "total_investment": 72000,
      "roi_at_1pct": -0.24,
      "category": "foundation_investment",
      "primary_pillar": "P1",
      "linked_kpi_codes": ["P1-KPI1", "P1-KPI2", "P1-KPI4"],
      "linked_playbooks": ["PB-01", "PB-02"]
    },
    "client_satisfaction": {
      "label": "Client Satisfaction",
      "baseline": 4.1,
      "one_pct_move": 0.041,
      "annual_impact_per_pct": 45000,
      "total_investment": 42000,
      "roi_at_1pct": 0.07,
      "category": "relationship_driver",
      "primary_pillar": "P2",
      "linked_kpi_codes": ["P2-KPI1", "P3-KPI1", "P2-KPI5"],
      "linked_playbooks": ["PB-03", "PB-07"]
    }
  }
}
```

### 10.8 CSV Column Schema Compatibility

The existing `config/csv_schemas.json` defines column names that are **vertical-neutral**:

```json
{
  "kpi_measurements": ["account_id", "kpi_code", "value", "measurement_date", "unit", "vertical", "uuid", "status"],
  "qualitative_signals": ["account_id", "signal_type", "severity", "description", "detected_at", "source"],
  "accounts": ["account_id", "account_name", "arr", "vertical", "uuid", "status", "profile_metadata"]
}
```

**No schema changes needed** — the same columns work for all verticals. What changes is:
- `kpi_code` values (SaaS P1-KPI1 = "DAU" vs. DC2_S P1-KPI1 = "Time-to-First-Workload")
- `signal_type` values (SaaS: `login_drop` vs. MSP: `sla_breach`)
- `vertical` column value (`saas_premium` vs. `msp_premium` vs. `dc2_s`)
- `profile_metadata` JSON structure (matches vertical's `metadata_schema.json`)

Optional per-vertical `csv_column_overrides.json` allows adding extra columns if a vertical needs them (e.g., MSP might add `endpoint_count` to accounts.csv).

---

## 11. Verification Checklist

### Per-Vertical Smoke Test

| # | Test | Expected |
|---|------|----------|
| 1 | `GET /api/verticals/{slug}/definition` | Returns full vertical definition |
| 2 | Onboarding with vertical flag | Customer created with correct KPI set |
| 3 | Score calculation | Pillar scores use vertical's L1/L2 weights |
| 4 | Power-of-1 calculation | Returns vertical-specific economic metrics |
| 5 | Playbook trigger evaluation | Fires playbooks from vertical's `playbooks.json` |
| 6 | CSM Daily Actions | Actions reference correct vertical KPIs |
| 7 | ROI Story generation | Uses vertical's Power-of-1 metrics |
| 8 | Context graph + story arc | Generates nodes/edges from vertical's arc manifests |
| 9 | Dashboard labels | Uses terminology overlay |
| 10 | Test Runner KPI presets | Shows vertical-specific onboarding tiers |

### Cross-Vertical Isolation

| # | Test | Expected |
|---|------|----------|
| 1 | Customer A (dc2_s) and Customer B (saas_premium) in same DB | Different KPI sets, no cross-contamination |
| 2 | Score calculation for A vs. B | Different pillar names, weights, thresholds |
| 3 | MCP server queries | Returns only customer's vertical KPIs |
| 4 | Power-of-1 for A vs. B | Different economic levers |

---

## 12. Open Questions

1. **Can a customer switch verticals?** — Likely no (different KPI sets make migration complex). Recommend creating a new customer.

2. **Shared KPIs across verticals?** — e.g., NPS exists in both SaaS and MSP. Use same code format (`P2-KPI1`) but different targets/weights. No cross-vertical KPI sharing at DB level.

3. **Custom verticals?** — Should customers be able to create their own verticals through the UI? Phase 5 consideration. Start with admin-provisioned verticals.

4. **Vertical marketplace?** — Could verticals be shared/imported like templates? Future consideration for partner ecosystem.

5. **MCP server vertical awareness?** — See Section 12 below. The MCP server has **significant DC2_S coupling** that must be addressed.

---

## 13. MCP Server: Vertical Decoupling Plan

### 12.1 Current State — Heavy DC2_S Coupling

The MCP server (`backend/mcp_server/cs_pulse_mcp_server.py`, 1600+ lines) is **deeply coupled to DC2_S**. This is the single largest refactoring blocker for multi-vertical support.

#### Coupling Category A: Hardcoded Vertical Filters

Every account-fetching tool hardcodes `Account.vertical == 'dc2_s'`:

| Line(s) | Tool | Filter |
|---------|------|--------|
| ~248 | `list_accounts()` | `Account.vertical == 'dc2_s'` |
| ~371 | `get_at_risk_accounts()` | `Account.vertical == 'dc2_s'` |
| ~600 | `calculate_power_of_1()` | `Account.vertical == 'dc2_s'` |
| ~1120 | `get_csm_daily_actions()` | `Account.vertical == 'dc2_s'` |
| ~1431 | `list_portfolio_customers()` | `Account.vertical == 'dc2_s'` |
| ~1534 | `get_portfolio_cross_customer_comparison()` | `Account.vertical == 'dc2_s'` |

**Fix**: Replace hardcoded filter with customer's actual vertical from DB:
```python
# Before:
accounts = Account.query.filter_by(customer_id=cid, vertical='dc2_s').all()

# After:
customer = Customer.query.get(cid)
accounts = Account.query.filter_by(customer_id=cid, vertical=customer.vertical).all()
```

#### Coupling Category B: Direct `verticals.dc2_s` Imports

| Line(s) | Tool | Import |
|---------|------|--------|
| ~240 | `list_accounts()` | `from verticals.dc2_s.api_routes import calculate_kpi_health, _get_trailing_kpi_values, get_precalculated_scores` |
| ~1114 | `get_csm_daily_actions()` | `from verticals.dc2_s.vertical_config import PLAYBOOK_CONFIG, should_trigger_playbook` |
| ~1115 | `get_csm_daily_actions()` | `from verticals.dc2_s.kpi_definitions import DC2S_KPIS` |

**Fix**: Use the `VerticalRegistry` to load definitions dynamically:
```python
# Before:
from verticals.dc2_s.vertical_config import PLAYBOOK_CONFIG, should_trigger_playbook
from verticals.dc2_s.kpi_definitions import DC2S_KPIS

# After:
vdef = vertical_registry.get(customer.vertical)
playbook_config = vdef.playbooks
kpi_definitions = vdef.kpi_catalog
```

#### Coupling Category C: Hardcoded KPI Code References

These tools extract specific DC2_S KPI values by code:

| Tool | Hardcoded KPI Codes | Purpose |
|------|---------------------|---------|
| `get_crm_account_data()` | P3-KPI1 (GPU util), P5-KPI1 (capacity), P2-KPI4 (uptime) | CRM renewal assessment |
| `get_support_tickets()` | P2-KPI1 (RMA), P2-KPI2 (MTBF), P2-KPI3 (incidents), P2-KPI4 (uptime), P2-KPI5 (thermal), P2-KPI7 (MTTR), P2-KPI8 (preventive maint) | Support ticket simulation |
| `get_customer_feedback()` | P4-KPI6 (partner NPS), P5-KPI7 (expansion prob), P5-KPI8 (champion engagement) | Feedback simulation |
| `get_csm_daily_actions()` | P4-KPI3 (QBR freq), P5-KPI7 (expansion prob) | Action prioritization |

**Fix**: Define KPI role mappings per vertical in config:
```json
// config/verticals/saas_premium/kpi_role_mappings.json
{
  "crm_integration": {
    "primary_usage_metric": "P1-KPI1",      // DAU (was GPU util for DC2_S)
    "capacity_metric": "P4-KPI1",            // Seat utilization
    "uptime_metric": null                     // N/A for SaaS
  },
  "support_simulation": {
    "incident_count": "P2-KPI5",             // Support ticket trend
    "resolution_time": null,                  // No MTTR in SaaS
    "satisfaction": "P2-KPI2"                 // CSAT
  },
  "feedback_simulation": {
    "nps_metric": "P2-KPI1",                 // NPS
    "expansion_probability": "P4-KPI4",      // Expansion probability
    "champion_engagement": "P1-KPI5"         // Power user ratio
  },
  "action_priorities": {
    "qbr_metric": "P2-KPI4",                // QBR attendance rate
    "expansion_metric": "P4-KPI4"            // Expansion probability
  }
}
```

#### Coupling Category D: System Prompt & Docstrings

The MCP system prompt (`config/mcp_system_prompt.md`) hardcodes DC2_S pillar names:
```
P1 - AI/ML Workload Performance
P2 - Infrastructure Reliability
P3 - Cloud & DevOps Maturity
P4 - Customer Engagement
P5 - Commercial & Expansion
```

Tool docstrings also reference DC2_S terminology.

**Fix**: Generate system prompt dynamically from vertical config:
```python
def build_system_prompt(vertical_slug: str) -> str:
    vdef = vertical_registry.get(vertical_slug)
    pillar_lines = "\n".join(
        f"- {p['pillar_id']} - {p['name']}"
        for p in vdef.pillars
    )
    return SYSTEM_PROMPT_TEMPLATE.format(
        vertical_name=vdef.manifest['vertical_name'],
        pillar_list=pillar_lines,
        kpi_count=vdef.manifest['kpi_count'],
        terminology=json.dumps(vdef.terminology, indent=2)
    )
```

### 12.2 Vertical Coupling Summary by Tool

| Tool | Vertical-Agnostic? | Refactoring Effort |
|------|--------------------|--------------------|
| `list_accounts()` | No — dc2_s filter | Low (change filter) |
| `get_account_health()` | No — dc2_s imports | Low |
| `get_at_risk_accounts()` | No — dc2_s filter | Low |
| `get_revenue_at_risk()` | **Yes** (context graph) | None |
| `get_graph_summary()` | **Yes** | None |
| `search_signals()` | **Yes** | None |
| `get_causal_chain()` | **Yes** | None |
| `calculate_power_of_1()` | Partial — dc2_s filter, economics | Medium |
| `get_outcome_roi_story()` | Partial | Medium |
| `get_playbook_recommendations()` | No — dc2_s playbooks | High |
| `get_crm_account_data()` | No — 3 hardcoded KPI codes | Medium |
| `get_support_tickets()` | No — 7 hardcoded KPI codes | High |
| `get_customer_feedback()` | No — 3 hardcoded KPI codes | Medium |
| `get_csm_daily_actions()` | No — playbooks + KPI codes | **Highest** |
| `get_portfolio_roi_summary()` | Partial | Medium |
| `list_portfolio_customers()` | No — dc2_s filter | Low |
| `get_portfolio_cross_customer_comparison()` | No — dc2_s filter | Low |

**Context Graph tools (4 tools) are already vertical-agnostic** — good news.

### 12.3 MCP Refactoring Strategy

#### Option A: Single MCP Server, Vertical-Aware (Recommended)

One server that detects the customer's vertical and loads the right config:

```python
@mcp_tool
async def get_csm_daily_actions(customer_id: int):
    customer = Customer.query.get(customer_id)
    vdef = vertical_registry.get(customer.vertical)

    # Load playbooks from vertical config (not hardcoded import)
    playbook_config = vdef.playbooks
    kpi_defs = vdef.kpi_catalog
    role_mappings = vdef.kpi_role_mappings

    # Generic playbook evaluation using vertical's config
    for pb_id, pb_cfg in playbook_config.items():
        if evaluate_triggers(pb_cfg['triggers'], normalized_kpis, kpi_defs):
            actions.append(build_action(pb_cfg, role_mappings, vdef.terminology))
```

**Pros**: Single server, single codebase, customer vertical auto-detected.
**Cons**: Larger refactoring effort; must parameterize all KPI references.

#### Option B: One MCP Server per Vertical

Separate server instances per vertical, each with its own config:

```
mcp_server/
    cs_pulse_mcp_server.py          # Generic base with shared logic
    verticals/
        dc2_s_mcp_config.json       # DC2_S-specific KPI mappings
        saas_premium_mcp_config.json
        msp_premium_mcp_config.json
```

**Pros**: Clean separation; DC2_S unchanged.
**Cons**: Code duplication; harder to maintain; customer must know which server to use.

#### Recommendation: **Option A** (single server, vertical-aware)

The refactoring is concentrated in ~6 tools that hardcode KPI references. The context graph tools (4 tools) already work for any vertical. The remaining tools just need vertical filter changes.

### 12.4 MCP Server Refactoring Tasks

| # | Task | Files | Effort |
|---|------|-------|--------|
| 1 | Replace all `Account.vertical == 'dc2_s'` with customer's actual vertical | `cs_pulse_mcp_server.py` (6 locations) | 1 day |
| 2 | Replace `from verticals.dc2_s` imports with registry lookups | `cs_pulse_mcp_server.py` (3 locations) | 1 day |
| 3 | Create `kpi_role_mappings.json` per vertical for simulated integrations | `config/verticals/*/kpi_role_mappings.json` | 1 day |
| 4 | Refactor `get_csm_daily_actions()` to use generic playbook evaluation | `cs_pulse_mcp_server.py` | 2 days |
| 5 | Refactor `get_support_tickets()` / `get_crm_account_data()` / `get_customer_feedback()` to use role mappings | `cs_pulse_mcp_server.py` | 1.5 days |
| 6 | Generate system prompt dynamically from vertical config | `cs_pulse_mcp_server.py`, template file | 1 day |
| 7 | Load Power-of-1 metrics from vertical config | `cs_pulse_mcp_server.py`, `power_of_1_model.py` | 1 day |
| 8 | E2E test: MCP tools return correct data for each vertical | Integration tests | 1 day |

**Total MCP effort: ~9.5 days** (can overlap with Phase 2/3 of main plan)

### 12.5 New Config File: `kpi_role_mappings.json`

Each vertical defines how its KPIs map to the generic roles used by MCP simulation tools:

```json
{
  "version": "1.0.0",
  "roles": {
    "primary_usage": { "kpi": "P1-KPI1", "label": "Daily Active Users" },
    "capacity_utilization": { "kpi": "P4-KPI1", "label": "Seat Utilization" },
    "system_uptime": null,
    "incident_count": { "kpi": "P2-KPI5", "label": "Support Ticket Trend" },
    "resolution_time": null,
    "nps": { "kpi": "P2-KPI1", "label": "NPS Score" },
    "csat": { "kpi": "P2-KPI2", "label": "CSAT" },
    "expansion_probability": { "kpi": "P4-KPI4", "label": "Expansion Probability" },
    "champion_engagement": { "kpi": "P1-KPI5", "label": "Power User Ratio" },
    "qbr_metric": { "kpi": "P2-KPI4", "label": "QBR Attendance Rate" },
    "partner_nps": null,
    "rma_rate": null,
    "thermal_score": null,
    "preventive_maintenance": null
  }
}
```

Roles that are `null` for a vertical are gracefully skipped by the MCP tools.

---

## 14. Load Test Runner: Per-Vertical Scenarios

### 13.1 Architecture: Vertical-Aware Test Runner

The load test runner currently runs 12 scenarios, all assuming DC2_S. To support multiple verticals:

```
load-driver/
    run_scenario.py                      # Entry point (add --vertical flag)
    scenarios/
        base.py                          # BaseScenario (unchanged)
        scenario_onboarding.py           # Generic — passes vertical to API
        scenario_health_scores.py        # Generic — reads whatever KPIs exist
        scenario_power_of_1.py           # Needs vertical's P-of-1 metrics
        scenario_csm_actions.py          # Needs vertical's playbooks
        scenario_context_graph.py        # Generic — uses story arcs
        scenario_roi_simulation.py       # Needs vertical's economics
        ...
    vertical_configs/
        dc2_s.json                       # Scenario config for DC2_S
        saas_premium.json                # Scenario config for SaaS Premium
        msp_premium.json                 # Scenario config for MSP Premium
    csv_generators/
        dc2_s_csv_gen.py                 # DC2_S synthetic data (existing)
        saas_premium_csv_gen.py          # SaaS synthetic data (new)
        msp_premium_csv_gen.py           # MSP synthetic data (new)
```

### 13.2 SaaSPremium Load Test Scenarios (13 scenarios)

All scenarios inherit the same IDs (1-12 + N8N) but generate/validate SaaS-specific data.

| # | Scenario | SaaS-Specific Behavior | Est. Time |
|---|----------|------------------------|-----------|
| **1** | **Onboarding** | Creates customer with 24 SaaS KPIs across 4 pillars. Generates `kpi_measurements.csv` with DAU, feature adoption, NPS, NRR, seat utilization values. Metadata includes `licensed_seats`, `active_modules`, `contract_end_date`. | 2-3 min |
| **2** | **Health Scores** | Validates 4 pillars (not 5). Checks pillar names match SaaS definitions. Verifies L1/L2 weights from `saas_premium/default_weights.json`. Validates health thresholds. | 1 min |
| **3** | **Tenant Isolation** | Creates 2 SaaS customers, verifies KPI sets don't leak. Tests that DC2_S customer doesn't see SaaS KPIs and vice versa. | 2 min |
| **4** | **Cleanup** | Deletes SaaS test customer, verifies cascade removes SaaS KPI measurements, signals, scores. | 1 min |
| **5** | **Power-of-1** | Tests 5 SaaS metrics: NRR, GRR, Product Adoption, Expansion Rate, TTFV. Validates economics from `saas_premium/power_of_1_metrics.json`. Verifies ARR-based scaling. | 1 min |
| **6** | **N8N Integration** | Tests webhook payloads contain SaaS terminology. Playbook triggers reference SaaS KPI codes. Skip if N8N not configured. | 1 min |
| **7** | **CSM Daily Actions** | Validates actions reference SaaS playbooks (PB-01 through PB-06). Verifies action labels use SaaS terminology (e.g., "Schedule Touchpoint" not "Schedule QBR"). Priority formula uses SaaS ARR weights. | 1 min |
| **8** | **Context Graph** | Generates 9 CSVs using SaaS story arcs (`arc_adoption_stall`, `arc_expansion_champion`, `arc_silent_churn`, `arc_land_and_expand`). Stakeholders are SaaS roles (VP Engineering, Product Manager, not GPU Engineer). | 3 min |
| **9** | **ROI Simulation** | Uses SaaS Power-of-1 economics. Projects expansion revenue based on seat utilization growth. Validates ROI narrative uses SaaS terminology. | 1 min |
| **10** | **Entitlements** | Verifies SaaS customers get correct feature gates. Tests tier-based access (starter/professional/enterprise) for SaaS features. | 0.5 min |
| **11** | **MCP Server** | Calls all 17 MCP tools with SaaS customer_id. Validates: pillar names are SaaS-specific, KPI codes match SaaS catalog, playbook recommendations are SaaS playbooks, CSM actions use SaaS terminology. | 2 min |
| **12** | **Data Integrity** | Validates SaaS KPI measurements have correct units (%, count, score, days). Checks value ranges against SaaS target definitions. Verifies no DC2_S KPI codes in SaaS customer data. | 1 min |

#### SaaS CSV Generator (`saas_premium_csv_gen.py`)

Generates 6 CSVs with SaaS-specific data distributions:

```python
SAAS_KPI_GENERATORS = {
    'P1-KPI1': {'name': 'DAU', 'base': 72, 'noise': 8, 'unit': '%'},
    'P1-KPI2': {'name': 'Feature Adoption', 'base': 55, 'noise': 10, 'unit': '%'},
    'P1-KPI3': {'name': 'Login Frequency', 'base': 3.2, 'noise': 0.8, 'unit': 'sessions/week'},
    'P1-KPI4': {'name': 'TTFV', 'base': 12, 'noise': 5, 'unit': 'days'},
    'P1-KPI5': {'name': 'Power User Ratio', 'base': 22, 'noise': 6, 'unit': '%'},
    'P1-KPI6': {'name': 'API Integration Depth', 'base': 3, 'noise': 1, 'unit': 'count'},
    'P1-KPI7': {'name': 'Module Penetration', 'base': 65, 'noise': 12, 'unit': '%'},
    'P2-KPI1': {'name': 'NPS', 'base': 42, 'noise': 15, 'unit': 'score'},
    'P2-KPI2': {'name': 'CSAT', 'base': 4.1, 'noise': 0.3, 'unit': 'score'},
    # ... all 24 KPIs
}

SAAS_SIGNAL_TYPES = [
    'login_drop', 'feature_abandonment', 'support_surge',
    'expansion_signal', 'champion_identified', 'exec_sponsor_change',
    'contract_utilization_alert', 'nps_decline', 'competitor_mention',
    'integration_failure', 'training_completion', 'renewal_risk'
]
```

#### SaaS Scenario Config (`vertical_configs/saas_premium.json`)

```json
{
  "vertical": "saas_premium",
  "default_num_accounts": 5,
  "default_industry": "Technology",
  "account_metadata_template": {
    "licensed_seats": [50, 100, 250, 500, 1000],
    "licensed_modules": ["core", "analytics", "integrations", "ai_copilot"],
    "contract_term_months": [12, 24, 36],
    "deployment_type": "cloud"
  },
  "pattern_mix_default": {
    "adoption_stall": 0.20,
    "healthy_growth": 0.40,
    "expansion_ready": 0.25,
    "churn_risk": 0.15
  },
  "expected_pillar_count": 4,
  "expected_kpi_count": 24,
  "power_of_1_metrics": ["NRR", "GRR", "product_adoption", "expansion_rate", "TTFV"],
  "playbook_count": 6,
  "story_arc_count": 4
}
```

### 13.3 MSPPremium Load Test Scenarios (13 scenarios)

| # | Scenario | MSP-Specific Behavior | Est. Time |
|---|----------|----------------------|-----------|
| **1** | **Onboarding** | Creates MSP client with 22 KPIs across 4 pillars. Generates `kpi_measurements.csv` with SLA compliance, MTTR, RPE, client CSAT values. Metadata includes `managed_endpoints`, `sla_tier`, `rmm_tool`, `psa_tool`. | 2-3 min |
| **2** | **Health Scores** | Validates 4 MSP pillars: Service Delivery, Client Satisfaction, Operational Efficiency, Growth. Checks L1/L2 weights from `msp_premium/default_weights.json`. | 1 min |
| **3** | **Tenant Isolation** | Creates MSP + DC2_S + SaaS customers, verifies complete isolation. Tests that MSP-specific KPIs (SLA compliance, RPE) don't appear in other verticals. | 2 min |
| **4** | **Cleanup** | Deletes MSP test customer with full cascade. | 1 min |
| **5** | **Power-of-1** | Tests 5 MSP metrics: Client Retention, Revenue Per Endpoint, Service Expansion, Operational Efficiency, SLA Compliance. Validates MRR-based economics (not ARR). | 1 min |
| **6** | **N8N Integration** | Webhook payloads use MSP terminology ("Managed Client", "Service Review"). Playbook triggers reference MSP KPI codes. | 1 min |
| **7** | **CSM Daily Actions** | Actions reference MSP playbooks (PB-01 through PB-06). Labels use MSP terminology ("SLA Recovery" not "Deployment Acceleration"). Priority uses MSP MRR weights. | 1 min |
| **8** | **Context Graph** | Uses MSP story arcs (`arc_sla_breach_cascade`, `arc_endpoint_explosion`, `arc_client_consolidation`, `arc_automation_transformation`). Stakeholders are MSP roles (Service Desk Lead, NOC Manager, vCIO). | 3 min |
| **9** | **ROI Simulation** | Uses MSP Power-of-1 economics. Projects service expansion revenue based on endpoint growth and cross-sell penetration. | 1 min |
| **10** | **Entitlements** | Verifies MSP customers get correct feature gates. | 0.5 min |
| **11** | **MCP Server** | All 17 MCP tools return MSP-appropriate data. Validates: MSP pillar names, MSP KPI codes, MSP playbook recommendations, MSP terminology in actions and feedback. | 2 min |
| **12** | **Data Integrity** | Validates MSP KPI units (%, hours, $/endpoint, score). Checks SLA compliance ranges (95-100%), MTTR ranges (1-12 hours). Verifies no SaaS or DC2_S KPI codes in MSP data. | 1 min |

#### MSP CSV Generator (`msp_premium_csv_gen.py`)

```python
MSP_KPI_GENERATORS = {
    'P1-KPI1': {'name': 'SLA Compliance', 'base': 98.5, 'noise': 1.2, 'unit': '%'},
    'P1-KPI2': {'name': 'MTTR', 'base': 3.5, 'noise': 1.5, 'unit': 'hours'},
    'P1-KPI3': {'name': 'First Contact Resolution', 'base': 78, 'noise': 8, 'unit': '%'},
    'P1-KPI4': {'name': 'Service Uptime', 'base': 99.92, 'noise': 0.05, 'unit': '%'},
    'P1-KPI5': {'name': 'Ticket Backlog Aging', 'base': 2.1, 'noise': 1.0, 'unit': 'days'},
    'P1-KPI6': {'name': 'Escalation Rate', 'base': 4.2, 'noise': 2.0, 'unit': '%'},
    'P1-KPI7': {'name': 'Proactive Detection', 'base': 55, 'noise': 12, 'unit': '%'},
    'P2-KPI1': {'name': 'Client CSAT', 'base': 4.1, 'noise': 0.4, 'unit': 'score'},
    'P2-KPI2': {'name': 'Client NPS', 'base': 38, 'noise': 12, 'unit': 'score'},
    'P3-KPI1': {'name': 'Revenue Per Endpoint', 'base': 14.5, 'noise': 3.0, 'unit': '$/endpoint'},
    # ... all 22 KPIs
}

MSP_SIGNAL_TYPES = [
    'sla_breach', 'ticket_surge', 'endpoint_growth_spike',
    'client_escalation', 'automation_opportunity', 'tool_underutilization',
    'contract_renewal_approaching', 'competitor_pitch_detected',
    'technician_overload', 'security_incident', 'backup_failure',
    'client_consolidation_rumor'
]
```

#### MSP Scenario Config (`vertical_configs/msp_premium.json`)

```json
{
  "vertical": "msp_premium",
  "default_num_accounts": 8,
  "default_industry": "Multi-Industry",
  "account_metadata_template": {
    "managed_endpoints": [100, 250, 500, 1000, 2500, 5000],
    "managed_servers": [5, 15, 30, 60, 120],
    "sla_tier": ["bronze", "silver", "gold", "platinum"],
    "contract_type": ["managed_services", "co_managed", "break_fix"],
    "rmm_tool": ["ConnectWise", "Datto", "NinjaRMM", "Kaseya"],
    "psa_tool": ["ConnectWise_Manage", "Autotask", "HaloPSA"]
  },
  "pattern_mix_default": {
    "sla_stable": 0.40,
    "growth_phase": 0.25,
    "efficiency_push": 0.20,
    "client_at_risk": 0.15
  },
  "expected_pillar_count": 4,
  "expected_kpi_count": 22,
  "power_of_1_metrics": ["client_retention", "revenue_per_endpoint", "service_expansion", "operational_efficiency", "sla_compliance"],
  "playbook_count": 6,
  "story_arc_count": 4
}
```

### 13.4 Test Runner UI Changes

The Test Runner UI needs a **vertical selector** so the operator can choose which vertical to test:

```
┌──────────────────────────────────────────────────────────┐
│  Test Runner                                    Customer ▼│
│                                                          │
│  Vertical:  [DC2_S ▼]  [SaaS Premium]  [MSP Premium]   │
│                                                          │
│  Scenarios  │ Platform State │ Analytics │ Data Ops │ ⚙  │
├──────────────────────────────────────────────────────────┤
│  □ 1. Onboarding (saas_premium)                         │
│  □ 2. Health Scores (4 pillars, 24 KPIs)                │
│  □ 3. Tenant Isolation (cross-vertical)                 │
│  ...                                                     │
│                                                          │
│  Advanced Options                                        │
│  ├─ Presets: [Quick Demo (3)] [Standard (5)] [Full (10)]│
│  ├─ KPI Configuration (24 SaaS KPIs)                    │
│  │   [Full (24)] [Standard (16)] [Quick Start (8)]      │
│  ├─ Pillar Weights (4 pillars)                          │
│  │   P1: Adoption 30% │ P2: Engagement 25%             │
│  │   P3: Financial 25% │ P4: Expansion 20%              │
│  └─ Journey Pattern Mix                                  │
│       adoption_stall: 20% │ healthy_growth: 40%         │
│       expansion_ready: 25% │ churn_risk: 15%            │
└──────────────────────────────────────────────────────────┘
```

**Frontend changes**:
- Add vertical selector in `DCTestRunner.tsx` header (alongside customer dropdown)
- Load vertical definition via `GET /api/verticals/{slug}/definition`
- `ScenariosTab.tsx`: Dynamically render pillar names, KPI catalog, presets, pattern mix labels from vertical definition
- `SettingsTab.tsx`: No changes needed (feature flags are vertical-agnostic)

### 13.5 CLI Usage Examples

```bash
# SaaS Premium: Quick onboarding test
python3 run_scenario.py --scenario 1 --vertical saas_premium \
    --num-accounts 3 --industry Technology

# SaaS Premium: Full suite with minimal KPI preset
python3 run_scenario.py --scenario all --vertical saas_premium \
    --num-accounts 5 \
    --enabled-kpis '["P1-KPI1","P1-KPI4","P2-KPI1","P2-KPI5","P3-KPI1","P3-KPI2","P4-KPI1","P4-KPI4"]'

# MSP Premium: Full suite
python3 run_scenario.py --scenario all --vertical msp_premium \
    --num-accounts 8 --industry "Multi-Industry"

# Cross-vertical isolation test
python3 run_scenario.py --scenario 3 --vertical saas_premium  # Creates SaaS + DC2_S customers
python3 run_scenario.py --scenario 3 --vertical msp_premium   # Creates MSP + DC2_S customers
```

---

## 15. File Summary

### New Files to Create

| File | Purpose |
|------|---------|
| `backend/vertical_loader_v2.py` | Registry + definition loader |
| `backend/vertical_api.py` | Generic vertical API blueprint |
| `config/verticals/dc2_s/manifest.json` | DC2S vertical manifest |
| `config/verticals/dc2_s/kpi_definitions.json` | DC2S KPIs (extracted from .py) |
| `config/verticals/dc2_s/terminology.json` | DC2S labels (current defaults) |
| `config/verticals/dc2_s/onboarding_tiers.json` | DC2S tiers (Default/Medium/Minimal) |
| `config/verticals/dc2_s/kpi_role_mappings.json` | KPI-to-MCP-role mapping for DC2S |
| `config/verticals/saas_premium/*` | Full SaaSPremium config (11 files including role mappings) |
| `config/verticals/msp_premium/*` | Full MSPPremium config (11 files including role mappings) |
| `load-driver/csv_generators/saas_premium_csv_gen.py` | SaaS synthetic CSV data generator |
| `load-driver/csv_generators/msp_premium_csv_gen.py` | MSP synthetic CSV data generator |
| `load-driver/vertical_configs/saas_premium.json` | SaaS scenario configuration |
| `load-driver/vertical_configs/msp_premium.json` | MSP scenario configuration |
| `migrations/add_generic_vertical_fields.py` | DB migration |

### Files to Modify

| File | Change |
|------|--------|
| `utils/score_calculator.py` | Use registry instead of DC2S_KPIS import |
| `onboarding_api_v2_config_aware.py` | Accept `vertical` param, load from registry |
| `test_runner_api.py` | Pass `--vertical` flag to subprocess |
| `load-driver/run_scenario.py` | Add `--vertical` argument |
| `load-driver/scenarios/scenario_onboarding.py` | Pass vertical to onboarding payload |
| `load-driver/scenarios/scenario_power_of_1.py` | Load metrics from vertical config |
| `load-driver/scenarios/scenario_csm_actions.py` | Validate against vertical's playbooks |
| `load-driver/csv_generator.py` | Dispatch to vertical-specific generator |
| `app_v3_minimal.py` | Register generic vertical blueprint |
| `power_of_1_model.py` | Load metrics from vertical config |
| `mcp_server/cs_pulse_mcp_server.py` | Replace dc2_s hardcodes with registry (6 filters, 3 imports, KPI role mappings) |
| `config/mcp_system_prompt.md` | Template-driven, inject vertical pillar names |
| Frontend: `DCTestRunner.tsx` | Vertical selector, dynamic KPI catalog |
| Frontend: `ScenariosTab.tsx` | Load vertical-specific presets dynamically |

### Files Unchanged

| File | Why |
|------|-----|
| `verticals/dc2_s/api_routes.py` | Backward compatible, stays as-is |
| `verticals/dc2_s/kpi_definitions.py` | Stays as canonical Python source for dc2_s |
| `models.py` (existing columns) | dc2s_* columns kept as deprecated aliases |
| `config/health_thresholds.json` | Already vertical-agnostic |
| `config/csv_schemas.json` | Column format is vertical-neutral |
| `utils/context_graph.py` | Graph model is vertical-agnostic |
