# Claude-Driven Backtest Harness — Implementation Plan

**Status:** Proposed — for review
**Ship target:** Next sprint (~6h implementation + ~30min smoke test)
**Dependencies:** `PLAN_NRR_Forecast_Backtest.md` (NRRForecastSnapshot/compare/report layer)

---

## Goal

Produce an **independent, Claude-generated** synthetic dataset that mirrors a real customer onboarding — **exactly 4 CSVs** per tenant — and lets us grade CS Pulse's forecasts (NRR + ROI) against ground-truth "organic" 6-month outcomes the customer would achieve WITHOUT our product.

The killer-value sales story this enables:

> *"We predict your organic NRR at 107% over 6 months and your organic ROI at 3.2x. If you adopt CS Pulse with our recommended playbooks, projected NRR is 115% and ROI is 11.8x. Our track record on the organic baseline: ±1.4pp MAPE across 200 backtested scenarios. Trust the baseline anchors trust in the uplift."*

The synthetic dataset doubles as **demo asset** — 20 canned customer scenarios with narratives, quantifiable uplift claims, and traceable accuracy history.

## Scope

Generate + ingest **20 synthetic CS Pulse customers, 10 accounts each** (200 accounts total):

- **4 CSVs per customer** — matches real onboarding (account_details, kpi_measurements, qualitative_signals, outcomes)
- **Sidecar per account** with dual ground-truth branches:
  - **NRR branch** — realized_renewal_date, realized_outcome, realized_nrr_pct
  - **ROI branch** — organic_cs_investment, realized_protected_arr, realized_lost_arr, realized_expanded_arr, realized_organic_roi_pct
- **20 tenant dimension specs** covering KPI tier × vertical × arc phase × health skew × renewal window — the test surface the load-driver's 20 manifests collectively span

## Non-goals

- Not replacing load-driver. Load-driver stays for targeted scenario regression, dev seeding, stress tests. Claude synthetic is for forecast-accuracy backtest + demo scripts.
- Not generating pipeline OUTPUTS (decisions, edges, ROISnapshot, playbook_executions). Pipeline produces those at `process_data` time.
- Not measuring `with_cs_pulse_*` forecast accuracy. That requires real customer adoption — paid beta path, not synthetic.

---

## Architecture

```
┌────────────────────────────────────────────────────────┐
│ scripts/claude_driven_generate_backtest.py             │
│                                                        │
│  TENANT_SPECS (20 dimension-grid cells)                │
│    ↓                                                   │
│  One Claude API call per tenant (20 total)             │
│    ↓                                                   │
│  Per tenant: 10 accounts × (4 CSVs + sidecar)          │
│    ↓                                                   │
│  coverage_audit (verticals, tiers, difficulties)       │
│    ↓                                                   │
│  scripts/datasets/claude_driven_backtest_v1.json       │
└────────────────────────────────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────────┐
│ scripts/claude_driven_ingest_batch.py                  │
│                                                        │
│  Safety gates: DB must be test DB; ≤100 customers      │
│    ↓                                                   │
│  For each of 20 tenants:                               │
│    1. Create Customer + CustomerConfig                 │
│    2. Write 4 CSVs to /tmp from JSON                   │
│    3. Upload via onboarding_api_v2_config_aware        │
│    4. Stash future_truth into profile_metadata         │
│       .synthetic_ground_truth (pipeline never reads)   │
│    5. Call process_data(cust_id):                      │
│       - score_calculator (health from KPIs × weights)  │
│       - Wizard A (arc classification)                  │
│       - MOD-007 LLM Tier 1 (decisions + edges)         │
│       - Wizard B (NRR forecast: organic + w/CS Pulse)  │
│       - outcome_roi_engine (ROI snapshots)             │
└────────────────────────────────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────────┐
│ tests/e2e/test_claude_driven_backtest.py               │
│                                                        │
│  Per tenant, compare pipeline outputs vs sidecar:      │
│    - Wizard B organic NRR forecast  vs  realized NRR   │
│    - ROI engine organic projection  vs  realized ROI   │
│    - With-CS-Pulse projection math (sanity, not MAPE)  │
│    - I17 violations = 0                                │
│                                                        │
│  Persists MAPE + coverage stats to                     │
│    scripts/datasets/claude_driven_backtest_v1_results  │
│    .json                                               │
└────────────────────────────────────────────────────────┘
```

## File manifest

| File | Purpose | LOC |
|---|---|---:|
| `kpi-dashboard/PLAN_Claude_Driven_Backtest_Harness.md` | This doc | ~250 |
| `scripts/claude_driven_generate_backtest.py` | Claude API driver + coverage audit | ~350 |
| `scripts/claude_driven_ingest_batch.py` | JSON → CSVs → upload → sidecar → process_data | ~300 |
| `kpi-dashboard/backend/tests/e2e/test_claude_driven_backtest.py` | MAPE + invariants + ROI probes | ~400 |
| `scripts/datasets/claude_driven_backtest_v1.json` | Generated dataset (committed) | — |
| `scripts/datasets/claude_driven_backtest_v1_results.json` | Test-run MAPE + stats (committed) | — |

## What each file produces / consumes

**`claude_driven_generate_backtest.py`**
- Input: `ANTHROPIC_API_KEY` env var; (optional) `--tenants N`
- Per-tenant: 1 Claude call with TENANT_SPECS[i] + SYSTEM_PROMPT + user prompt
- Output: one JSON file with all 20 tenants' data + per-account 4-CSV rows + sidecar
- Cost: ~$2 for 200 accounts. Runtime ~3 min.

**`claude_driven_ingest_batch.py`**
- Input: JSON dataset from generator; `DATABASE_URL` (must be test DB)
- Per-tenant: create customer → write 4 CSVs → upload via `process_csv_upload` → stash sidecar → `_process_data_impl(cust_id)`
- Output: 20 customer_ids, printed as `export SYNTHETIC_CUSTOMER_IDS=...` for pytest convenience
- Cost: ~$4 of MOD-007 LLM Tier 1 spend (pipeline fires for each in 4-CSV mode)
- Runtime: ~25 min (process_data × 20)

**`test_claude_driven_backtest.py`**
- Input: `SYNTHETIC_CUSTOMER_IDS` env var; `DATABASE_URL` at test DB
- Reads pipeline outputs + sidecar per account; computes MAPE + invariants + ROI accuracy
- Output: pytest pass/fail + results JSON with per-customer + portfolio MAPE

## Dual-metric sidecar schema

```jsonc
"future_truth": {
  "scenario": "organic_no_cs_pulse_intervention",
  "difficulty": "EASY" | "MEDIUM" | "HARD",
  "narrative": "1-sentence explanation of the organic outcome",

  // NRR branch — Wizard B's without_cs_pulse_nrr_pct compared here
  "realized_renewal_date": "2026-10-15",
  "realized_nrr_outcome": "renewed_flat|renewed_expansion|contracted|churned|non_renewal_event",
  "realized_arr_change_usd": -250000,
  "realized_nrr_pct_for_account": 80,
  "is_nrr_forecastable_from_history": true,

  // ROI branch — outcome_roi_engine's without_cs_pulse_roi compared here
  "organic_cs_investment_usd_annual": 25000,
  "realized_protected_arr_usd": 350000,
  "realized_expanded_arr_usd": 50000,
  "realized_lost_arr_usd": 250000,
  "realized_organic_net_impact_usd": 150000,
  "realized_organic_roi_pct": 1200,
  "is_roi_forecastable_from_history": true
}
```

The synthetic ground truth + pipeline prediction pairing lets us compute:

| Metric | Source | Computed as |
|---|---|---|
| Organic NRR MAPE | Wizard B `without_cs_pulse_nrr_pct` vs sidecar `realized_nrr_pct` | `abs(pred − actual)` in percentage points |
| Organic ROI MAPE | ROI engine organic projection vs sidecar `realized_organic_roi_pct` | `abs(pred − actual) / actual × 100` |
| With-CS-Pulse sanity | Wizard B `with_cs_pulse_nrr_pct` ≥ organic, uplift < 15pp | assert bounds |
| I17 violations | `run_invariant('I17', cust_id)` | assert == 0 |

## Sign-off checklist before merging

- [ ] `claude_driven_generate_backtest.py --tenants 2` produces valid JSON in <1 min for 2 tenants
- [ ] `coverage_audit.failures == []` on a full 20-tenant run
- [ ] `claude_driven_ingest_batch.py --purge` cleanly removes synthetic tenants
- [ ] Ingest has `assert "cs_pulse_test" in db_url` safety guard
- [ ] Ingest has `assert Customer.query.count() < 100` safety guard
- [ ] First E2E run completes in <30 min
- [ ] Organic NRR portfolio MAPE on synthetic dataset reports < 5pp
- [ ] Per-difficulty breakdown in results: EASY < 2pp MAPE, HARD < 15pp MAPE
- [ ] `test_with_cs_pulse_uplift_non_negative` asserts: projected ≥ organic
- [ ] `test_i17_zero_violations` asserts invariant gate held on all 20 tenants
- [ ] Dataset JSON committed to `scripts/datasets/claude_driven_backtest_v1.json`
- [ ] Results JSON committed to `scripts/datasets/claude_driven_backtest_v1_results.json`

When all 11 check, the harness is shippable.

## What this does NOT prove

- **Real customer adoption outcomes** — requires paid beta + real CRM data (the Rank-1 option from the prior conversation)
- **With-CS-Pulse uplift accuracy** — math projection given attribution rates; synthetic can't validate because no real adoption data exists for comparison
- **Claude's theory of CS matches reality** — generalizable-beyond-training-distribution check requires real data

These are honest gaps. Cite them in `MODEL_INVENTORY.md` under MOD-001 open-gaps section when shipping.

## Complementarity with load-driver

| Job | Tool |
|---|---|
| Targeted arc-regression test | **load-driver manifest** |
| New-onboarding-wizard UI test | **load-driver** |
| Dev-DB seeding for fast iteration | **load-driver** |
| Stress / scale tests (30+ accounts) | **load-driver** |
| Forecast-accuracy MAPE measurement | **Claude synthetic** |
| Canned demo customer scripts (20 stories) | **Claude synthetic** |
| Model-generalization probes | **Claude synthetic** |

Both stay. Different answers to different questions.

## Operations

- **Initial run:** generate → ingest → tests → commit dataset + results. Establishes v1 MAPE baseline.
- **Per Wizard B model bump:** regenerate only if arc_label taxonomy changed; otherwise re-ingest existing JSON + re-run tests to get new results vs unchanged dataset.
- **Quarterly:** full regeneration to avoid Claude-output drift from sampling variance.
- **Storage:** dataset + results JSONs committed to git (~2MB compressed) — become historical record for governance dashboards.
