# GPU-Rental Neocloud — Target KPI / Taxonomy / Playbook Spec

> **Status:** Design spec (proposal). No code or config changed by this document.
> **Author framing:** written from the seat of a 15-year data-center operator who rents
> NVIDIA GPUs by the hour (to run open-source models) and rents dedicated clusters for
> customer use cases.
> **Companion:** the graded audit (`scratchpad/gpu_neocloud_audit.html`) explains *why*;
> this doc specifies *what to build*.
> **Scope note:** this is the delta against today's `DC2_S` vertical. Every item is tagged
> **KEEP** (already exists, leave it), **RE-WEIGHT** (exists, change its emphasis), or
> **NEW** (doesn't exist yet).

---

## 0. What we are NOT changing (the engine is fine)

These are the hard, well-built parts. This spec assumes they stay exactly as-is:

- The **data pipeline**: upload → validate → config-aware ingest → L1→L4 rollup.
- The **3-tier calibratable weight hierarchy** (`CustomerConfig` → `bootstrap_weights_config.json`
  → catalog defaults) and **Wizard C** learning weights from outcomes.
- The **leading/trailing model**: `kpi_only_score` vs `qual_score` vs `divergence`, and the
  ±8 early-warning verdict.
- The **QSIM signal engine**: multi-source ingest, Claude enrichment, structural+LLM urgency
  fusion, collision/dedup, Tier-1 preemption, review queue, audit.
- The **playbook machinery**: `automation_level` + `human_approval_required` governance,
  arc→playbook auto-trigger, n8n orchestration, Power-of-1 cost bridge + outcome-ROI engine.

**The entire gap is content, not code.** Everything below is a re-weighting + a taxonomy
overlay + KPI/playbook definitions the existing engine can already carry.

---

## 1. Business model this vertical must serve

Two products, one fleet:

1. **On-demand GPU-hours** — fungible, spot-like capacity to run OSS models (inference /
   fine-tune). Revenue = `utilization × realized $/GPU-hr × available GPU-hours`.
2. **Reserved clusters** — committed capacity for a customer use case (training runs,
   dedicated inference). Revenue = contracted TCV; risk = under-ramp and non-renewal.

**The three truths that must drive the health model:**

- **An idle allocated GPU is the money bonfire.** Utilization × realized rate *is* the P&L.
- **Customers grade you on goodput, not uptime.** A cluster that's "up" but throttling or
  dropping InfiniBand links delivers fewer TFLOPs than billed.
- **Power is the binding constraint** before rack space is — and for AI-startup renters,
  *their* fundraising is *your* leading revenue signal.

---

## 2. Target KPI framework

### 2.1 Pillar re-balance

Today's five pillars spend ~30% of health weight on a build-and-resell motion
(P1 Deployment Velocity + P4 Channel & Partner Health). Proposed target: **six pillars**,
re-weighted toward the rental P&L. Channel is dropped; deployment is slimmed to provisioning.

| # | Target pillar | Weight | vs today | Rationale |
|---|---|---|---|---|
| R1 | **Revenue & Unit Economics** | **0.25** | **NEW** | The rental P&L. Nothing models it today. |
| R2 | **Fleet Utilization & Goodput** | **0.22** | RE-WEIGHT (was ~P3 partial) | Utilization × realized rate is the business. |
| R3 | **Reliability & SLA Delivery** | **0.20** | RE-WEIGHT (was P2/P3 partial) | Goodput, interruptions, fabric — not just uptime. |
| R4 | **Power & Facility** | **0.13** | RE-WEIGHT (was ~P2 PUE) | Sellable MW is the constraint; PUE alone is vanity. |
| R5 | **Commercial & Expansion** | **0.15** | RE-WEIGHT (was P5) | Commitment coverage, ramp, silicon-refresh, solvency. |
| R6 | **Provisioning Velocity** | **0.05** | SLIM (was P1 @ 0.15) | Time-to-first-job matters; commissioning boxes doesn't. |
| — | ~~Channel & Partner Health~~ | **0.00** | **DROP (was P4 @ 0.15)** | Direct / self-serve motion; no VAR layer. |

*Weights sum to 1.00. These are illustrative starting points — Wizard C should recalibrate
them against real churn/expansion outcomes once data exists.*

### 2.2 KPIs by pillar

Direction: ↑ = higher-is-better, ↓ = lower-is-better. Cadence is the *needed* measurement
frequency (many rental gauges are telemetry-grade, not monthly).

#### R1 · Revenue & Unit Economics — NEW pillar

| KPI | Unit | Dir | Target | Cadence | Status |
|---|---|---|---|---|---|
| Realized $/GPU-hour | $/gpu-hr | ↑ | ≥ list × 0.9 | daily | NEW |
| Effective-utilization revenue capture | % of billable | ↑ | > 85 | daily | NEW |
| On-demand vs reserved revenue mix | ratio | band | policy target | weekly | NEW |
| Gross margin per cluster/customer | % | ↑ | > 45 | monthly | NEW |
| Discount / rate leakage | % below list | ↓ | < 10 | weekly | NEW |
| Revenue per available MW | $/MW | ↑ | trend ↑ | monthly | NEW |

#### R2 · Fleet Utilization & Goodput — RE-WEIGHT

| KPI | Unit | Dir | Target | Cadence | Status |
|---|---|---|---|---|---|
| GPU Utilization (allocated) | % | ↑ | > 70 | realtime | KEEP (`P3-KPI1`) — raise weight |
| **Effective utilization (goodput)** | % | ↑ | > 90 of allocated | realtime | NEW |
| Idle GPU-hours (allocated-but-idle) | gpu-hr | ↓ | minimize | realtime | NEW |
| Reserved-cluster utilization | % | ↑ | > 60 | daily | NEW |
| Fleet fragmentation / stranded GPUs | count | ↓ | minimize | hourly | NEW |
| Queue depth / time-to-schedule | minutes | ↓ | < 5 | realtime | NEW |
| GPU memory efficiency | % | ↑ | > 80 | daily | KEEP (`P3-KPI5`) |

#### R3 · Reliability & SLA Delivery — RE-WEIGHT

| KPI | Unit | Dir | Target | Cadence | Status |
|---|---|---|---|---|---|
| Training-job completion rate | % | ↑ | > 95 | daily | KEEP (`P3-KPI2`) |
| **Job interruption / preemption rate** | % of jobs | ↓ | < 2 | realtime | NEW |
| **GPU/node failure rate (XID, HBM ECC)** | events/1k gpu-hr | ↓ | < 1 | realtime | NEW |
| **Fabric health (IB/NVLink, RDMA errors)** | error rate | ↓ | near-0 | realtime | NEW |
| Checkpoint-restart frequency | restarts/run | ↓ | minimize | per-run | NEW |
| SLA attainment vs credits owed | % / $ | ↑ / ↓ | ≥ 99.5 / $0 | monthly | NEW |
| MTBF / MTTR | hours | ↑ / ↓ | high / < 4 | monthly | KEEP (`P2-KPI2/7`) |
| Inference latency (P95) | ms | ↓ | < 50 | realtime | KEEP (`P3-KPI3`) |

#### R4 · Power & Facility — RE-WEIGHT

| KPI | Unit | Dir | Target | Cadence | Status |
|---|---|---|---|---|---|
| **Sellable MW / power-capacity utilization** | % of MW | ↑ | band 70–90 | daily | NEW |
| **Stranded power (provisioned-unsellable)** | MW | ↓ | minimize | daily | NEW |
| PUE | ratio | ↓ | < 1.3 | realtime | KEEP (`P2-KPI6`) |
| Cooling / DLC headroom (H100/H200/GB200) | % | ↑ | > 20 | realtime | NEW |
| kW per rack (density) | kW | band | rack spec | daily | NEW |
| Water usage effectiveness (WUE) | L/kWh | ↓ | trend ↓ | monthly | NEW |
| Thermal management score | % | ↑ | > 95 | realtime | KEEP (`P2-KPI5`) |

#### R5 · Commercial & Expansion — RE-WEIGHT

| KPI | Unit | Dir | Target | Cadence | Status |
|---|---|---|---|---|---|
| Reserved commitment coverage / backlog | $ / months | ↑ | trend ↑ | weekly | NEW |
| **Ramp-to-commit** (consumed vs contracted min) | % | ↑ | > 90 | weekly | NEW |
| Compute-hour consumption trend | %Δ | ↑ | > 15 | monthly | KEEP (`P5-KPI4`) |
| Expansion probability (90d) | % | ↑ | > 50 | monthly | KEEP (`P5-KPI7`) |
| Silicon-refresh readiness (H100→H200→GB200) | score | ↑ | — | quarterly | NEW |
| **Customer runway / solvency signal** | months | ↑ | > 12 | monthly | NEW |
| Technical champion engagement | score | ↑ | > 75 | monthly | KEEP (`P5-KPI8`) |
| Multi-cloud diversification (share erosion) | % of spend | ↓ | watch | quarterly | NEW |

#### R6 · Provisioning Velocity — SLIM

| KPI | Unit | Dir | Target | Cadence | Status |
|---|---|---|---|---|---|
| Time-to-first-job | hours | ↓ | < 24 | per-onboard | RE-SCOPE (`P1-KPI1`, days→hours) |
| Provisioning / quota-grant time | hours | ↓ | < 4 | per-onboard | NEW |
| Configuration accuracy | % | ↑ | > 95 | per-onboard | KEEP (`P1-KPI3`) |

**Retired for this model:** `P1` hardware-commissioning / servers-per-day / doc-completeness;
all of `P4` (VAR / channel-conflict / co-sell); `P2-KPI1` RMA-frequency as a *critical driver*
(reframe as an internal cost metric, not a customer-health KPI — a renter hot-swaps and
absorbs the RMA).

---

## 3. Desired signal taxonomy (the `taxonomy_dc2_s.json` overlay)

Today the overlay is **empty**, so the vertical inherits 100% SaaS intents
(`renewal_risk`, `nps_drop_indicator`, `feature_request`…). Below is the desired
rental-native vocabulary. Each subtype lists **polarity**, the **revenue bucket** it maps to,
and whether it should be a **Tier-1** (bypass-fusion, immediate-alert) subtype.

### 3.1 New intent codes (LLM classification vocabulary)

`goodput_complaint`, `reserved_idle_risk`, `commitment_ramp_miss`, `silicon_refresh_interest`,
`reservation_expansion`, `funding_event`, `runway_risk`, `spot_price_pressure`,
`multicloud_diversification`, `byo_cluster_intent`, `power_constraint`, `reliability_sla_breach`.

### 3.2 Signal subtypes by theme

#### A. Goodput & reliability
| Subtype | Polarity | Revenue bucket | Tier-1 |
|---|---|---|---|
| `throughput_below_spec` | negative | at_risk | — |
| `job_preemption_complaint` | negative | at_risk | — |
| `interconnect_bottleneck` | negative | at_risk | — |
| `reliability_sla_breach` | negative | at_risk | **Tier-1** |
| `checkpoint_restart_pain` | negative | at_risk | — |
| `goodput_restored` | positive | protected | — |

#### B. Utilization & consumption
| Subtype | Polarity | Revenue bucket | Tier-1 |
|---|---|---|---|
| `reserved_cluster_idle` | negative | at_risk | **Tier-1** (near renewal) |
| `utilization_ramp` | positive | expansion | — |
| `burst_overflow` | positive | pipeline | — |

#### C. Commercial & commitment
| Subtype | Polarity | Revenue bucket | Tier-1 |
|---|---|---|---|
| `commitment_ramp_miss` | negative | at_risk | — |
| `reservation_expansion_interest` | positive | pipeline | — |
| `silicon_refresh_interest` | positive | pipeline | — |
| `multicloud_diversification` | negative | at_risk | — |
| `byo_cluster_intent` | negative | at_risk | — |
| `reservation_closed` | positive | expansion | — |

#### D. Solvency & funding
| Subtype | Polarity | Revenue bucket | Tier-1 |
|---|---|---|---|
| `funding_raised` | positive | pipeline | — |
| `runway_risk` | negative | at_risk | **Tier-1** |
| `payment_delinquency` | negative | at_risk | **Tier-1** |

#### E. Competitive & pricing
| Subtype | Polarity | Revenue bucket | Tier-1 |
|---|---|---|---|
| `spot_price_pressure` | negative | at_risk | — |
| `competitor_capacity_offer` | negative | at_risk | — |

#### F. Power & facility (internal ops signals)
| Subtype | Polarity | Revenue bucket | Tier-1 |
|---|---|---|---|
| `power_capacity_constraint` | negative | at_risk (blocks expansion) | — |
| `thermal_event` | negative | at_risk | **Tier-1** |

*Fusion note:* the `dc2_s` qual sub-weights already put `product_sentiment` top (0.40) — keep
that; goodput/reliability signals should feed the R2/R3 pillars, solvency/commercial into R5.

---

## 4. Playbooks needed

Keep the two rental-native plays; retire/adapt the vendor plays; add seven. Every new
playbook lists **trigger**, **owner role**, **core actions**, the **Power-of-1 lever** it
should attribute to, and **governance**.

### 4.1 Keep / adapt existing
| ID | Play | Disposition |
|---|---|---|
| `PB-03` | GPU Optimization | **KEEP** — but split "efficiency tuning" from "idle-revenue-risk" (see PB-07). |
| `PB-04` | Capacity Planning | **KEEP** — retarget lever to reserved-commitment coverage. |
| `PB-05` | Health Monitoring | **KEEP** — generic safety net. |
| `PB-01` | Deployment Acceleration | **ADAPT** → "Provisioning Acceleration" (time-to-first-job). |
| `PB-06` | Customer Engagement | **KEEP**. |
| `PB-02` | RMA Prevention | **RETIRE** as a customer play; fold hardware reliability into PB-08. |

### 4.2 New playbooks

**PB-07 · Idle-Reserved-Cluster Rescue** — NEW
- **Trigger:** reserved-cluster utilization < 40% for ≥ N weeks, OR `reserved_cluster_idle`
  signal, especially within 1–2 quarters of renewal.
- **Owner:** CSM + Solutions Engineer.
- **Actions:** usage review → workload-onboarding help → right-size vs renegotiate → exec align.
- **Lever:** reserved-commitment coverage / GRR (protect at-renewal revenue).
- **Governance:** `human_approval_required: true` (commercial decision).

**PB-08 · SLA / Goodput-Breach Recovery** — NEW
- **Trigger:** job-interruption rate spike, fabric-error surge, or `reliability_sla_breach`.
- **Owner:** SRE / Reliability Eng + CSM.
- **Actions:** incident RCA → **proactive credits** → reliability fix → customer comms.
- **Lever:** churn-averted / GRR.
- **Governance:** `automation_level: high`, alert immediate (Tier-1 signal).

**PB-09 · Power & Thermal Headroom** — NEW
- **Trigger:** power-capacity utilization > threshold, rising stranded MW, or `thermal_event`.
- **Owner:** Facility / Capacity Engineering.
- **Actions:** capacity plan → cooling/DLC remediation → allocation rebalance → pre-provision
  for expansion.
- **Lever:** protect **sellable MW** / avoid declined expansion.
- **Governance:** `human_approval_required: true` for capex-bearing steps.

**PB-10 · Silicon-Refresh Upsell** — NEW
- **Trigger:** `silicon_refresh_interest`, OR H100 customer + newer generation available.
- **Owner:** Account Exec + Solutions Engineer.
- **Actions:** migration offer → benchmark proof → commit uplift.
- **Lever:** expansion / NRR.

**PB-11 · Funding-Triggered Expansion** — NEW
- **Trigger:** `funding_raised` signal.
- **Owner:** Account Exec + CSM.
- **Actions:** capacity pre-allocation → commitment upsell → roadmap alignment.
- **Lever:** expansion.

**PB-12 · Runway / Collections Guard** — NEW
- **Trigger:** `runway_risk` or `payment_delinquency`.
- **Owner:** CSM + Finance.
- **Actions:** right-size → prepay/commit restructure → collections workflow.
- **Lever:** protect revenue / reduce bad debt.
- **Governance:** `human_approval_required: true`.

**PB-13 · Competitive Price-Defense** — NEW
- **Trigger:** `spot_price_pressure`, `competitor_capacity_offer`, or `multicloud_diversification`.
- **Owner:** Account Exec + Pricing.
- **Actions:** price/commit response → value reinforcement → technical proof (goodput, fabric).
- **Lever:** churn-averted / retention.

---

## 5. Sense → Reason → Act chain (how it wires together)

The mapping the engine should express (signal → pillar it moves → playbook it triggers):

| Signal (leading) | Moves pillar | Confirmed by KPI (trailing) | Fires playbook |
|---|---|---|---|
| `reserved_cluster_idle` | R2 Utilization | Reserved-cluster utilization ↓ | **PB-07** |
| `reliability_sla_breach` | R3 Reliability | Interruption/failure rate ↑ | **PB-08** |
| `power_capacity_constraint` | R4 Power | Sellable MW ↑ / stranded MW ↑ | **PB-09** |
| `silicon_refresh_interest` | R5 Commercial | Expansion probability ↑ | **PB-10** |
| `funding_raised` | R5 Commercial | Compute-hour trend ↑ | **PB-11** |
| `runway_risk` / delinquency | R1 Revenue | Margin / payment status ↓ | **PB-12** |
| `spot_price_pressure` | R1 Revenue | Realized $/GPU-hr ↓ | **PB-13** |
| `commitment_ramp_miss` | R5 Commercial | Ramp-to-commit ↓ | **PB-07 / PB-04** |

The **divergence** verdict stays the tie-breaker: when a leading signal fires but the trailing
KPI hasn't moved yet (negative divergence beyond −8), that's the early-warning window the
playbook is meant to act inside.

---

## 6. Power-of-1 lever re-base

The dollar model today attributes ROI on SaaS levers (NRR, GRR, `product_adoption`,
`ticket_resolution_time`). For a utilization-driven business it should attribute on:

| Rental lever | What 1 unit is worth | Replaces / augments |
|---|---|---|
| **Utilization uplift** | idle GPU-hours recovered × realized $/GPU-hr | `product_adoption` |
| **Reserved-commitment coverage** | protected/expanded contracted TCV | `NRR` (rental sense) |
| **Goodput / SLA-credit avoided** | credits not owed + churn averted | `GRR` |
| **Power pass-through margin** | sellable-MW protected × margin/MW | NEW |

Keep NRR/GRR/expansion as roll-ups, but **define them in rental terms** (committed-capacity
renewal, not seat retention) so attribution is directionally correct.

---

## 7. Build phasing (reference — see audit for detail)

- **P0 (days, config-only):** re-weight health toward R1/R2 + let Wizard C recalibrate;
  enable `FEATURE_SIGNAL_ENGINE` + fusion so leading/trailing goes live; populate the
  `taxonomy_dc2_s.json` overlay from §3.
- **P1 (weeks):** stand up the R1 pillar + the NEW KPIs in §2.2; ship PB-07…PB-13; re-base
  Power-of-1 per §6.
- **P2 (a quarter):** streaming telemetry ingest for utilization/failure/fabric; reframe
  Wizard D to committed-capacity renewal / backlog; add an external funding/burn feed.

---

## 8. One-line summary

Keep the engine. Re-weight the health model toward **revenue × utilization × goodput × sellable
power**, fill the empty DC taxonomy overlay with rental-native signals, add the seven rescue/
expansion playbooks, and re-base the dollar model on utilization instead of NRR. That is the
whole distance between "watches a hardware reseller" and "watches a GPU-rental floor."

---

## 9. DataCenterV1 — new-vertical creation blueprint

**Decision:** ship this spec as a **NEW vertical `datacenter_v1`**, not as edits to `dc2_s`.
Existing `DC2_S` tenants (NovaStar 358, demo customers) keep their catalog, calibrated
Wizard-C weights, and history untouched; new tenants onboard onto `datacenter_v1`; the two run
side by side and a customer migrates only when chosen.

**Why the architecture makes this cheap (verified in code, read-only):**
`utils/vertical_registry.py` **auto-discovers** verticals by globbing
`config/*_kpi_catalog.json` and states its own design principle — *"DC2_S is not special. Any
vertical can be defined via JSON catalog without Python code."* `ScoreCalculator` resolves
KPIs/weights through `get_kpis(vertical)` / `get_default_pillar_weights(vertical)` — no `dc2_s`
hardcoding in the scoring math — and `utils/vertical_health.py` builds a **generic** health
calculator from any vertical's JSON catalog. Three verticals already ride this
(`dc2s`, `saas_premium`, `healthcare_provider`).

### 9.1 The one knob that MUST be set
`CustomerConfig.vertical = 'datacenter_v1'` for every DataCenterV1 tenant. Every unset path
(`config.vertical or 'dc2_s'`, `get_vertical_for_customer()`) **silently defaults to `dc2_s`** —
a blank vertical scores the tenant on the wrong catalog.

### 9.2 Naming caution
`VERTICAL_ALIASES` in `vertical_registry.py` already maps bare `'datacenter' → 'dc2_s'`. Use
the distinct slug **`datacenter_v1`** (unknown slugs pass through `normalize_vertical`
unchanged). Never register it as bare `datacenter`.

### 9.3 REQUIRED — the vertical won't be correct without these
| # | Artifact | Path | Notes |
|---|---|---|---|
| 1 | Tenant vertical flag | `CustomerConfig.vertical='datacenter_v1'` | §9.1; the only hard gate. |
| 2 | KPI catalog | `config/datacenter_v1_kpi_catalog.json` | Auto-discovered. Encodes §2 pillars + KPIs + `weight_l1`/`weight_l2` + ranges/targets. **This one file = the whole KPI framework** (no Python needed). |
| 3 | Taxonomy overlay | `config/taxonomy_datacenter_v1.json` | §3 subtypes. Without it, inherits base (the same "empty overlay → SaaS vocabulary" gap we're fixing). Merged + boot-validated by `taxonomy_loader.py`. |
| 4 | Playbook definitions | `verticals/datacenter_v1/vertical_config.py` → `PLAYBOOK_CONFIG` | §4 (PB-03/04/05 + PB-07…PB-13). |
| 5 | Playbook evaluator wiring | `playbook_recommendations_api.py` | **Real code-touch to verify:** `_evaluate_dc2s_playbooks` is vertical-specific → DataCenterV1 needs either a generic evaluator or a `datacenter_v1` branch that reads its `PLAYBOOK_CONFIG`. |
| 6 | Dashboard/REST read endpoints | `api_v1_routes.py`, `ask_ai_tools.py` → `verticals.dc2_s.api_routes` | **Real code-touch to verify:** the *scoring* engine is generic (see below), but the READ/dashboard layer still imports `dc2_s`-specific helpers (`get_dc2s_accounts`, `get_dc2s_health_score`, `get_csm_daily_actions`, `get_dc2s_alerts`, `get_team_capacity_api`…). Confirm these resolve correctly for a `datacenter_v1` tenant (they read the vertical-agnostic score tables, but are named/routed for dc2_s). |

> **Scoring is already generic (validated read-only, 2026-08-12).** `utils/vertical_health.py`
> routes **both** `dc2_s` and `saas_premium` through the generic JSON-catalog scorer
> (`_make_generic_calculator`); DC2_S's Python scorer is retired and parity is proven in
> `tests/test_scorer_parity.py` (190 L1 + 8 L2/L3 checks, zero delta). No path falls back to a
> DC2_S `calculate_kpi_health`. So DataCenterV1's KPI scoring works the moment its catalog JSON
> exists — the code-touches above are the playbook evaluator and the dashboard read layer, not
> the scoring math.

### 9.4 OPTIONAL — degrade gracefully if missing, but needed for full fidelity
| Artifact | Path | Effect if omitted |
|---|---|---|
| Enrichment prompt context | `signal_engine/enrichment.py` → `VERTICAL_CONTEXT['datacenter_v1']` + `VALID_INTENTS` additions | LLM enrichment uses a generic prompt; new intents unclassified. |
| Fusion sub-weights | `signal_engine/fusion.py` → `VERTICAL_QUAL_SUBWEIGHTS['datacenter_v1']` + `PILLAR_CONTRIBUTION` | Falls back to default qual sub-weights; signals may map to wrong pillar. |
| Nomenclature | `config/vertical_nomenclature/datacenter_v1.json` | Default labels in UI. |
| Playbook display names | `utils/vertical_playbook_routing.py` | Raw PB-IDs shown. |
| Power-of-1 levers | `config/power_of_1_economics.json` + `playbook_cost_bridge.py` `_PRIMARY_METRIC_MAP` + `outcome_roi_engine.py` `PB_METRIC_MAP` | ROI attributes on SaaS levers (§6 not applied). |
| Arc→playbook map | `config/arc_playbook_map.json` | New PBs won't auto-trigger from arcs (threshold triggers still fire). |
| Tier-1 subtypes | `signal_engine/models.py` `TIER_1_SUBTYPES`; scores in `journey_intelligence_api.py` `SIGNAL_SCORE_MAP` | New critical signals won't preempt/alert immediately. |

### 9.5 DB tables — no new table needed
KPI measurements read/write through the `DC2SKPI` / `dc2s_kpis` table
(`score_calculator.py:487`, `upload_api_v3_improved_duplicates.py`). It is **misnamed but
structurally generic** — keyed by `account_id` + `kpi_code` + `measured_at`, no `customer_id`.
Because a DataCenterV1 tenant's accounts are distinct, its new KPI codes store there in
isolation. Scores/pillars/health use the vertical-agnostic `KPIScore` / `PillarScore` /
`HealthScore` tables. **DataCenterV1 rides all existing tables; zero migrations.** (Cosmetic
cleanup — renaming `dc2s_kpis`→`kpi_measurements` — is out of scope and tracked separately.)

### 9.6 Net shape of the work
- **~80% is drop-in config**: two JSON files (catalog + taxonomy) + a handful of per-vertical
  dict entries. Auto-discovered, hot-reloadable, no schema change.
- **~20% is verified code-touch**: the playbook evaluator (§9.3 #5) and re-basing Power-of-1
  levers (§9.4). Everything else degrades gracefully.
- **0 database migrations.**

### 9.7 Migration & rollout note
1. Land the catalog + taxonomy → onboard one pilot tenant with `vertical='datacenter_v1'`.
2. Let Wizard C calibrate weights against that tenant's outcomes.
3. Run it beside a `dc2_s` tenant for an A/B read on the divergence/early-warning quality.
4. Migrate existing `DC2_S` GPU-rental tenants only after the pilot proves out — flipping
   `CustomerConfig.vertical` re-points them at the new catalog with no data move.
