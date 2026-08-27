# Vertical-coupling audit — customer-visible business flow

**Scope:** customer 390 (NovaGrid GPU Cloud, `datacenter_v1`, 12 accounts, $50M ARR). Read-only calls, live endpoints, 2026-08-21.

**Verification key:** ✅ verified from live API · 📄 from tool docstrings/platform docs · ⚠️ inferred, needs code confirmation

---

## Finding 1 — Customer 390 is served another vertical's pillar structure ✅

Three endpoints disagree about what this customer's pillars are.

| source | P1 | P2 | P3 | P4 | P5 | P6 | count |
|---|---|---|---|---|---|---|---|
| `list_verticals` (datacenter_v1) | Revenue & Unit Economics | Fleet Utilization & Goodput | Reliability & SLA Delivery | **Power & Facility** | Commercial & Expansion | Provisioning Velocity | 6 |
| `list_accounts(390)` `pillar_labels` | *identical to above* | | | | | | 6 |
| `get_kpi_catalog(390)` | Deployment Velocity | Operational Stability | AI Workload Performance | **Channel & Partner Health** | Expansion Readiness | — | **5** |
| `get_cfo_dashboard_summary(390)` `pillar_investments` | Deployment Velocity | Operational Stability | AI Workload Performance | **Channel & Partner Health** | Expansion Readiness | — | **5** |

The bottom two rows are **`dc2_s`'s pillar set**, verbatim, per `list_verticals`:

> `dc2_s` — *Deployment Velocity, Operational Stability, AI Workload Performance, Channel & Partner Health, Expansion Readiness*

`get_kpi_catalog(390)` reports `"vertical": "datacenter_v1"` in its own response while returning dc2_s content. The fallback does not announce itself.

**Internal inconsistency inside that one response confirms the customer really has six pillars:**

```
default_pillar_weights_l2   : P1..P5            (5 entries — dc2_s shape)
customer_pillar_weights_l2  : P1..P6, P6 = 0.05 (6 entries — datacenter_v1 shape)
pillars{}                   : P1..P5 defined    (no P6 definition)
tier_enabled_kpis           : 38 codes, including P6-KPI1/2/3
total_kpis reported         : 35
list_verticals kpi_count    : 38
```

So P6 carries 5% of the L2 weight and three enabled KPIs, and has **no definition in the catalog being served**. Any L2 rollup using this catalog either drops P6 — computing health on 95% of the intended weight — or fails.

**Likely root cause** ⚠️: `datacenter_v1`'s config does not load, and the code falls back to the DC2S defaults that `get_kpi_catalog`'s own docstring names as the `customer_id=0` default, without changing the reported vertical. Supporting evidence: `get_vertical_config('datacenter_v1')` **throws** — `name '_get_playbook_config' is not defined` — a Python NameError from a tool documented as *"Discovery tool — no authentication required… when explaining what a vertical supports to a prospect."* A prospect-facing endpoint is returning a stack-trace-class error.

---

## Finding 2 — The partner portal exposes facility data as partner metrics ✅

`partner_portal`'s docstring hardcodes the pillar and its meaning:

> *"Partner-scoped portal for **P4 (Channel & Partner Health)** operations… All responses are scoped to P4 pillar only — no revenue, ARR, or other pillar data exposed."*

Called against customer 390 (`partner_id=1`, `action=scorecard`), it returns P4 scores for all 12 accounts under `P4-KPI1..6` labelled Partner Engagement Score, VAR Performance Rating, Joint QBR Frequency, Channel Conflict Score, Co-selling Opportunities, Partner NPS.

**Those scores are this customer's real P4 pillar scores — which `list_accounts` labels *Power & Facility*.** Cross-checked:

| account | `list_accounts` P4 (*Power & Facility*) | `partner_portal` `p4_score` |
|---|---|---|
| Titan Hyperscale Labs | 10.7 | **10.7** |
| Orion Models | 15.7 | **15.7** |
| Pacific Dataworks | 87.4 | **87.4** |
| Apex Compute | 88.7 | **88.7** |

Exact matches across every account checked.

**Two distinct harms:**

1. **Data exposure.** A channel partner receives the customer's power, cooling and facility pillar data — operational detail with no partner relevance, which the customer never consented to share with a partner. The documented isolation guarantee ("no… other pillar data exposed") is defeated precisely because P4 does not mean *partner* in this vertical.
2. **Semantic corruption.** Every number is mislabelled. The partner is told their *Partner NPS* is 28.75 when that value describes Titan's facility performance. There is no reading of that scorecard that is correct.

`action=impact` accepts `metric_id` ∈ {partner_engagement, var_performance, qbr_frequency, channel_conflict, co_selling, partner_nps} — none of which exist in `datacenter_v1`.

---

## Finding 3 — The organising defect: binding by position, not role

Findings 1 and 2 are the same bug as `ARC_TEMPLATES` binding template slots by ordinal (`signal:1`, `signal:2`) rather than by meaning.

**Pillar index is stable across verticals. Pillar meaning is not.** Any code that says `P4` and means *partner* is correct in `dc2_s` and `saas_premium` and wrong in `datacenter_v1`. The same trap exists for revenue: it is **P1** in `datacenter_v1` and **P5** in `saas_premium`, so any hardcoded "exclude the revenue pillar" rule is wrong in one of them.

**The fix is a pillar-role registry per vertical:**

```json
"pillar_roles": {
  "revenue":     "P1",
  "reliability": "P3",
  "capacity":    "P4",
  "partner":     null,        // datacenter_v1 has no partner pillar
  "expansion":   "P5"
}
```

`partner_portal` then asks for `pillar_roles.partner` and, getting `null`, **refuses to serve a partner portal for this vertical** — which is the correct behaviour — instead of serving facility data under partner labels.

---

## Finding 4 — Per-account ROI on the CFO dashboard is arithmetic, not analysis ✅

Every one of the 12 accounts returns `roi_pct: 427`, `source: "benchmark"`, `playbook_runs: 0`.

It is identical by construction:

```
impact     = ARR × 0.0349250   (Titan 8.2M→286,385 · Pacific 12.5M→436,562.5 · Nova 0.9M→31,432.5)
investment = ARR × 0.0066224   (Titan→54,303.68   · Pacific→82,780)
roi_pct    = impact/investment − 1 = 427%  for every account, always
```

Both figures are fixed multiples of ARR, so ROI cannot vary with health, arc, playbook history or anything else. Titan at health 14.7 and Stellar at 89.2 show the same 427%.

---

## Finding 5 — Four NRR values and four ROI values in one payload ✅

From a single `get_cfo_dashboard_summary(390)` response:

| field | value | basis |
|---|---|---|
| `historical_actuals.historical_nrr_pct_ttm` | 100 | computed — but from `arr_churned: 0, arr_contracted: 0, arr_expanded: 0` |
| `predictor_v3_portfolio_nrr` | **null** | all 12 per-account predictions fail |
| `power_of_1_metrics` NRR `baseline` | 105 | benchmark constant, `estimated: true` |
| `nrr_current` / `nrr_projection` | 106 | headline figure |
| `nrr_with_intervention` | 114.9 | — |
| `wizard_b_nrr.with_cs_pulse_nrr_pct` | 100 | counterfactual, delta 0 |

And ROI:

| field | value |
|---|---|
| `roi_pct` (top level) | 0 |
| `roi_multiple` | 0 |
| per-account `roi_pct` | 427 |
| `layered_story.blended_roi` | 6.7 |
| `nrr_waterfall.roi_x` | 138.6 |
| `proof_data.realized_roi` | 0 |

A CFO reading this dashboard can be shown 0%, 427%, 6.7×, or 138.6× depending on which panel renders.

**Note the honest half:** `proof_data` reports 8 executions, 7 resolved, `revenue_protected: 0`, `revenue_expanded: 0`, `health_delta: null`, total cost $331,120 — i.e. **$331k spent, zero measured return**. That is the only figure in the payload computed from what actually happened, and it is the one the headline numbers contradict.

---

## Finding 6 — Power-of-1 double-counting is live in the CFO layered story ✅

`layered_story` → *"Growth (Po1 1%)"* → **value: 1,746,250**.

That is the exact sum of all six Power-of-1 metrics (306,250 + 525,000 + 500,000 + 190,000 + 125,000 + 100,000 = 1,746,250) — and those metrics share playbooks. From `get_playbook_economics`: **PB-04** sits under both NRR and expansion_rate, **PB-02** under both GRR and ticket_resolution_time, **PB-01** under both TTFV and product_adoption.

The same intervention's benefit is counted twice and presented to a CFO as one growth number.

---

## Finding 7 — Provenance marking exists but is inconsistent ✅

Worth crediting: the payload does carry provenance in places — `source: "benchmark"`, `estimated: true`, `roi_is_modeled: false`, `revenue_risk_label: "Confirmed Risk (Context Graph)"`, and a full `context_graph_provenance` block with sample nodes and a named engine.

The problem is that it is applied to the *supporting* fields and absent from the *headline* fields. `nrr_current: 106` carries no marker. `efficiency_score: 64` carries `source: "benchmark"` but is rendered as a score. The dashboard is one payload mixing measured values, benchmark constants, and another vertical's defaults, with no consistent field telling them apart.

---

## Surface-by-surface status

| surface | vertical-scoped today? | severity | note |
|---|---|---|---|
| `partner_portal` | ❌ hardcoded P4 | **critical** | Finding 2 — data exposure |
| `get_kpi_catalog` | ❌ silently falls back to dc2_s | **critical** | Finding 1 — mislabels its own output |
| `get_vertical_config` | ❌ **throws NameError** | **high** | prospect-facing, returns an error |
| CFO dashboard `pillar_investments` | ❌ dc2_s names, P6 dropped | **high** | Finding 1 |
| Power-of-1 metric set | ❌ SaaS-shaped (NRR/GRR/adoption/expansion/tickets/TTFV) | **high** | no GPU utilisation, goodput, commit ramp, PUE |
| NRR / GRR definition | ❌ single SaaS model | **high** | consumption vs subscription — separate issue |
| `ARC_TEMPLATES` + arc vocabulary | ❌ universal | **high** | prior analysis |
| Signal taxonomy | ⚠️ appears vertical-flavoured in data | medium | needs code check — is it config or hardcoded? |
| Playbook catalog | ⚠️ partly (PB-03 "GPU Optimization" is DC-specific; PB-DC-* naming suggests otherwise) | medium | |
| Playbook economics constants (`csm_rate: 95`, `effort_multiplier: 1.4`, sub-component hours) | ❌ platform-wide | medium | CSM cost differs by vertical and geography |
| Health thresholds (<50 / 50-69 / 70+) | ❌ platform-wide | medium | 📄 docs say per-customer configurable; no vertical default |
| CSV schemas | ✅ `get_csv_templates(vertical)` | ok | genuinely parameterised |
| Pillar/KPI weights | ✅ per-customer via Wizard C | ok | |
| Node/edge type vocabulary | ✅ universal by design | ok | correctly universal |

---

## What belongs in the vertical-gen scaffold

The current scaffold generates KPI definitions, pillar weights, benchmarks, Power-of-1 economics and nomenclature. It also needs to emit:

1. **`pillar_roles` registry** — the fix for Findings 1–3. Maps semantic role → pillar index, with `null` where the vertical has no such pillar.
2. **Signal-type taxonomy** — vertical-specific vocabulary, with the 3-category grouping that the discovery work will need.
3. **Arc vocabulary + templates** — `champion_loss` means something different in SaaS, DC and healthcare.
4. **Arc classification rules** — they reference signal types, so they inherit the taxonomy.
5. **Outcome type vocabulary** — `capacity_constraint` and `renewal_uncertainty` are already appearing as DC-specific subtypes.
6. **Retention model composition** — committed retention / volume / effective rate / commit utilisation / unfilled demand, weighted per vertical. Not one NRR formula.
7. **Power-of-1 metric set** — per vertical. For DC: GPU utilisation, goodput, PUE, commit ramp — not product adoption.
8. **Playbook catalog and economics constants** — including `csm_rate` and `effort_multiplier`.
9. **Health threshold defaults.**
10. **Dashboard metric selection** — which figures each persona sees.

**And a structural guard:** a test that fails if any served config's reported vertical does not match the config actually loaded. Finding 1 exists because a fallback was silent. The same class of control as the `NOT NULL` constraint — make the mismatch impossible to ship, not merely discouraged.

---

## Priority

1. **`partner_portal` P4** — data exposure. Gate it on `pillar_roles.partner` and have it refuse where that is null. Until then, consider disabling the portal for `datacenter_v1` tenants.
2. **`get_kpi_catalog` silent fallback** — everything downstream inherits it, including health scoring and the CFO dashboard.
3. **`get_vertical_config` NameError** — prospect-facing, trivially reproducible.
4. **Per-account ROI 427%** — a fixed ARR multiple presented as an account-level analysis.
5. **NRR/ROI figure reconciliation** — six NRR values and six ROI values across one payload.
6. **Power-of-1 double-count** in `layered_story`.
7. **Retention model decomposition** — the larger design work.

Items 1–4 are bugs with clear fixes. Items 5–7 are design.

---

## Not yet checked

- Whether the signal taxonomy is config-driven or hardcoded (needs code, not API)
- CEO and CRO dashboards (same fields likely; not yet called)
- Whether `saas_premium` (customer 333) exhibits the same catalog fallback — if it does not, that isolates the fault to `datacenter_v1`'s config specifically
- Onboarding, integration health, webhook triggers
- Whether any of these figures have been shown externally
