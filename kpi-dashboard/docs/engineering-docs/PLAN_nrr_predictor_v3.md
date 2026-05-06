# PLAN: NRR Predictor v3 — Phase 1 Build Plan

**Status:** A1, A3, A4, A5 + Phase 1/1.5 ship-hold criteria + Q1–Q7 thresholds signed off 2026-05-06; awaiting hosting-model resolution before Block 1 starts
**Branch:** `feature/predictor-v3-phase1` (to be created from `docs/gtm-engineering-reorg`)
**Authored:** 2026-05-06 v1.0; v1.1 amendment 2026-05-06 (A4, A5, Real Customer Track)
**Companion:** `nrr_predictor_v3_design_notes.md` (open questions + hazard data shape)

This document is the canonical execution plan. The companion design notes resolve architecture questions; this document locks the build path, the ship/hold criteria, and the verification gates. Both are required reading before Block 1 starts.

---

## Prior decisions this builds on

Verified consistent with `nrr_predictor_v3_design_notes.md` v3. Any deviation below is explicitly called out, not embedded in implementation choice.

| Decision | Source | Status here |
|---|---|---|
| Discrete-time logistic hazard, monthly panel | Design notes Q4 | Assumed; consistent |
| 3-level hierarchy with fixed segment thresholds per vertical | Design notes Q5 | Assumed; consistent |
| Both `E[NRR \| renewal]` and `E[NRR \| 12mo]` per account | Design notes Q1 | Assumed; consistent |
| CDI templates seeded from public benchmarks | Design notes Q2 | Assumed; **deviation in implementation** — see Architecture Decision A2 |
| Treatment = `PlaybookExecutionV2` for Phase 4 | Design notes Q3 | Assumed; logging audit in Block 1 |
| Portfolio aggregation = independence + range + disclosure | Design notes Q6 | Assumed; consistent |
| Bayesian (`brms`/`pymc`) as v1; `lme4` as week-3 contingency | Design notes "Estimation path" | **Deviation — see Architecture Decision A1** |

---

## Architecture Decisions (locked)

### A1. GLMM-as-v1 (deviation from design notes' Bayesian-as-v1)

**Decision:** Phase 1 v1 uses **frequentist hierarchical GLMM** (`statsmodels.MixedLM` for Python; `lme4::glmer` retained as cross-check). Bayesian (`pymc`/`brms`/`Stan`) is deferred to Phase 2.

**Reasons:**
1. Bayesian tooling onboarding is 6–8 weeks of calendar time without a quant on the team. Phase 1's structural value (replacing the 100% NRR pin, separating prediction from attribution) lands fully without Bayesian.
2. Phase 1 fits on synthetic / manifest-driven data. Proper posteriors over fictional outcomes is sophistication for sophistication's sake. The story *"tenant posterior contracts as data accumulates"* only earns credibility once real-tenant outcomes exist.
3. Bayesian's incremental-updating value compounds with realized data, which Phase 1 does not yet have.

**Phase 2 trigger conditions for migrating to Bayesian (all three required, no exceptions):**
- ≥ 1 real-tenant pilot has accumulated ≥ 30 closed outcomes
- Quant hire / contractor in place for ≥ 4 weeks of focused work
- Phase 1 v1 GLMM has measurable shortcomings on real (non-synthetic) data that proper posteriors would close

If any one trigger doesn't hit, Bayesian stays deferred. No "we should really upgrade" drift.

**Consequences of this decision (must be disclosed wherever the model surfaces):**
- CIs in v1 = bootstrap (1000 resamples). Not posteriors.
- CDI {μ, σ} priors don't plug into a GLMM the way the design notes assume. v1 implements them as informative starting values + ridge/elastic-net penalty terms calibrated against {μ, σ}. **Same intuition; weaker mathematical guarantee.**
- Incremental Bayesian updating is unavailable. Per-tenant recalibration is full refit, quarterly.

### A2. Wizard D (calibrator) + predictor module (inference) — split by concern

**Decision:** the predictor is delivered as **two artifacts, not one**:

| Concern | Artifact | Frequency |
|---|---|---|
| Calibration (fit GLMM, update CDI templates, refit per-tenant coefficients) | `backend/wizards/wizard_d_predictor_calibrator.py` | Quarterly batch + admin-trigger via `trigger_wizard` MCP tool |
| Inference (per-account forward NRR, on demand) | `backend/predictor/` module | Per-request + monthly batch cache refresh |

Same pattern is reserved for Wizard E (Phase 4 attribution): `wizards/wizard_e_attribution_calibrator.py` + `backend/attribution/`.

### A3. Wizard B coexistence

**Hard rule:** never render Wizard B's `forecast_portfolio_nrr()` output and predictor v3 output on the same dashboard screen.

- **Phase 1:** predictor v3 ships behind `FEATURE_PREDICTOR_V3_UI=false`. When flipped to `true` per tenant, dashboard **swaps**: hides Wizard B's forecast tile + revenue waterfall, renders predictor v3 output. Top interventions + renewals at risk continue to come from Wizard B in Phase 1.
- **Phase 1.5 (after first real-customer structural validation):** `forecast_portfolio_nrr()` deprecated. Wizard B retained only for feature extraction (health slope, volatility, recovery indicator) feeding the predictor.
- **Phase 4:** Wizard E lands; `cs_pulse_delta_pct` reintroduced with real counterfactual attribution.

**Audit step in Block 5:** grep all dashboard files for `portfolio_nrr_forecast`, `current_nrr_pct`, `with_interventions_nrr_pct`. Every reference is either replaced with a predictor v3 call or gated by `!FEATURE_PREDICTOR_V3_UI`. No silent dual rendering.

### A4. Wizard B cleanup deliverable (staged removal, contractual)

To prevent two NRR implementations coexisting indefinitely (which is the realistic failure mode if cleanup stays aspirational), Phase 1.5 sign-off triggers a **scheduled cleanup PR**, not a "we'll get to it."

**Trigger:** Phase 1.5 ship/hold criteria pass on first real-customer pilot.

**Deliverable:** single PR titled `cleanup(wizard-b): remove forecast/attribution code superseded by predictor v3`.

**Specific deletions from `backend/verticals/_template/journey/wizard_b/wizard_b_pattern_analyzer.py`:**

| Method / constant | Replaced by |
|---|---|
| `forecast_portfolio_nrr()` (~640 lines) | `predictor/inference.py` |
| `_organic_retention()` | (gone — was attribution logic) |
| `_continuous_renewal_projection()` (v2 feature-flagged variant) | (gone — replaced by hazard model) |
| `_churn_prob(h)` lookup table | hazard-model coefficients |
| `0.85` deceleration constant | calibrated extrapolation parameter |
| `ATTRIBUTION_FACTOR = 0.50` | (moves to Wizard E in Phase 4) |
| Pattern-level NRR table population in `correlate_nrr_impact()` | (gone — was the 100%/100% noise the reviewer flagged) |
| Top interventions ranking | `predictor/inference.py` |
| Renewals at risk ranking | `predictor/inference.py` |

**Net deletion target:** ~900 lines from a ~1500-line file. Wizard B drops to ~600 lines.

**What stays in Wizard B (steady state):** `profile_patterns()`, `analyze_transitions()`, `identify_early_warnings()`, `extract_success_factors()`. Feature extractor only. No NRR math.

**Acceptance criteria for the cleanup PR:**
- Every method/constant in the table above is gone
- Wizard B file size reduced by ≥ 800 lines
- No production caller still references the deleted symbols (grep-verified across all `backend/`, `src/`, MCP tools)
- Wizard B unit tests pass on the reduced surface
- A regression test confirms the predictor v3 endpoint produces equivalent or better output on the customer-393 + first-real-customer tenants

**Owner:** same as Phase 1 build owner.

**Due:** within **1 sprint** (2 weeks) of Phase 1.5 sign-off.

**Enforcement:** if not merged within 2 weeks of Phase 1.5 sign-off, becomes a **P0 cleanup that blocks all other Wizard B work** until done. No exceptions.

### A5. Two-profile SaaS segmentation (SaaS-Enterprise vs SaaS-SMB)

The original SaaS thresholds in design notes Q5 (`mid_market < $5M ≤ enterprise < $50M ≤ strategic`) assume a whale-portfolio shape. They break for high-volume / SMB-heavy SaaS portfolios where median account ARR is well below $250K — almost every account would fall below the mid_market floor.

**Decision:** SaaS verticals are sub-classified at tenant onboarding by portfolio shape, with two threshold ladders:

| Profile | Trigger (auto-detected at onboarding) | Segment thresholds |
|---|---|---|
| **SaaS-Enterprise** | Median account ARR ≥ $250K | `mid_market < $5M ≤ enterprise < $50M ≤ strategic` |
| **SaaS-SMB** | Median account ARR < $250K | `smb < $25K ≤ mid_market < $250K ≤ enterprise` |

**Auto-detection rule:**
```python
median_arr = np.median([a.revenue for a in accounts if a.account_status == 'active'])
profile = 'saas_enterprise' if median_arr >= 250_000 else 'saas_smb'
```

Stored on `CustomerConfig` as `saas_profile` (new column; nullable for non-SaaS verticals).

**Re-evaluation rule:** profile locked for 12 months at onboarding; earlier re-evaluation triggered if median ARR shifts by > 50% (e.g., a strategic-account upmarket move fundamentally changes the shape).

**CDI templates per profile:** the public-benchmark seed (per A1's CDI-as-informative-priors implementation) lives at `config/cdi_seed_public_benchmarks.json` keyed by `(vertical, profile)`. Two SaaS entries: `saas_enterprise` and `saas_smb`. Phase 1 ships both; cold-start tenants pick by their auto-detected profile.

**Anchoring:**
- Customer 393 (Mount Pike, $6.7M avg ARR) → `saas_enterprise`
- New first-real-customer (~$20K avg ARR, 500 accounts) → `saas_smb`

**Implication for Phase 1 build:** panel construction in Block 1 segments accounts using profile-appropriate thresholds. The hierarchical model in Block 2 fits separate `β_{s,t,v}` for the two profiles, treating them as effectively different verticals at the CDI template level.

---

## Phase 1 Ship/Hold Criteria (LOCKED — do not edit post-facto)

Phase 1 fits on synthetic / manifest data. **Quantitative metrics on synthetic data measure fit-to-fiction, not predictive validity.** Acceptance is structural.

### Pass requires ALL of:

| # | Criterion | Pass condition |
|---|---|---|
| P1 | Model convergence | No singular fit warnings; no separation issues; coefficient SEs finite for all hazard terms |
| P2 | Decomposition validity | For every account: `p_churn ∈ [0,1]`; `p_churn + p_survive = 1` (within float epsilon); `expected_nrr.point ∈ [0, 1.30]`; `e_contract_pct ∈ [0, 1]`; `e_expand_pct ∈ [0, 1]` |
| P3 | Sanity check at G3 (expanded) | 5/5 named accounts (Zermatt, Bernina, Pilatus, Matterhorn, Denali) pass directional gut-check by reviewer |
| P4 | Term-decomposition coherence | Across all 30 customer-393 accounts: high-health accounts have low `p_churn`; high-slope-down accounts have higher `p_churn`; expansion-arc accounts have non-trivial `e_expand_pct`; the decomposition tells a story consistent with each account's known state |

### Hold required if ANY of:

- Any P1–P4 criterion fails
- Backfill produces impossible values (negative probabilities; NRR > 130% or < 0% for any account; CI lower > CI upper)
- Sanity check fails on ≥ 1 named account → diagnose feature/segment/arc misspec, fix, re-run; **never "ship anyway"**

### Informational only (measured + reported, NOT gating in Phase 1):

- Backfilled MAPE on historical horizon (recorded with `synthetic_data=true` flag)
- 90% CI coverage rate
- Per sub-model AUC / Spearman / Brier
- All recorded to `scripts/datasets/predictor_v3_phase1_backtest.json` for later Phase 1.5 comparison

**No middle band on Phase 1.** Synthetic data doesn't allow a "MAPE 22% is borderline" judgment — MAPE on fiction isn't meaningful.

---

## Phase 1.5 Ship/Hold Criteria (LOCKED now — applied at first real-customer pilot)

These criteria are written here, locked, before any real data exists. Motivated reasoning ("oh 22% is fine because…") cannot be retroactively applied.

### Phase 1.5 pass requires ALL of:

| # | Criterion | Threshold |
|---|---|---|
| Q1 | ARR-weighted portfolio MAPE on first real customer's quarterly backfill | ≤ 18% |
| Q2 | Per-account median APE | ≤ 25% |
| Q3 | 90% CI coverage rate on backfilled predictions | ≥ 85% |
| Q4 | Churn-hazard AUC on held-out tenant data | ≥ 0.70 |
| Q5 | Contraction GLM Spearman correlation (predicted contraction% vs realized, on accounts that survived to renewal) | ≥ 0.50 |
| Q6 | Expansion two-part: Brier on `P(expansion event)` | ≤ 0.20 |
| Q7 | Expansion two-part: MAPE on `E[size \| event]` | ≤ 25% |

### Phase 1.5 ship/hold rules:

| Outcome | Decision |
|---|---|
| All Q1–Q7 met | Ship |
| Any one Q fails by ≤ 10% margin | Discuss with buyer-equivalent reviewer; pre-decided meaning is "show output, get reaction, decide" |
| Any one Q fails by > 10% margin | Hold; diagnose; refit |

---

## API Contract (locked, per M3 from review)

```json
{
  "account_id": 3834,
  "tenant_id": 393,
  "horizon": "renewal",
  "horizon_months": 1,
  "expected_nrr": {
    "point":    0.92,
    "lower_90": 0.81,
    "upper_90": 1.02,
    "ci_method": "bootstrap_1000"
  },
  "term_decomposition": {
    "p_churn_at_horizon":           0.08,
    "p_survive_at_horizon":         0.92,
    "e_contract_pct_given_survive": 0.03,
    "e_expand_pct_given_survive":   0.01,
    "top_drivers": [
      {"covariate": "health_slope_3mo",                    "contribution": -0.04},
      {"covariate": "days_to_renewal_band",                "contribution": -0.02},
      {"covariate": "arc_type=competitive_displacement",   "contribution": -0.01}
    ]
  },
  "prediction_method": "calibrated",
  "calibration_id": 17,
  "calibrated_at": "2026-05-06T10:00:00Z",
  "feature_flags": {"predictor_v3_active": true}
}
```

**Units:**
- All probabilities in `[0, 1]`
- All ratios (NRR, contraction%, expansion%) in `[0, 1]` or `[0, 1.30]` for `expected_nrr.point`
- UI multiplies by 100 for display
- No mixed units in the contract

**Identity (enforced by assertion in test suite):**
```
expected_nrr.point = 1 − p_churn_at_horizon
                       + p_survive_at_horizon × (e_expand_pct − e_contract_pct)
```

**`prediction_method` values:**
- `"calibrated"` — fit using ≥ 3 months of panel data for this account
- `"cold_start"` — < 3 months panel; falls back to segment baseline + 2× CI inflation

**Endpoint:** `GET /api/v1/predictor/account/<id>/nrr-forecast?horizon=renewal|12mo`

---

## File Layout

```
backend/
├── wizards/
│   └── wizard_d_predictor_calibrator.py     # offline GLMM fit; trigger_wizard registered as wizard='d'
├── predictor/
│   ├── __init__.py
│   ├── panel.py                              # (account, month) panel construction
│   ├── features.py                           # health_slope_3mo, volatility, days_to_renewal_band, …
│   ├── inference.py                          # apply calibrated coefs → expected NRR + bootstrap CI
│   ├── cdi_seed.py                           # public-benchmark seed loader; informative starting values
│   ├── api.py                                # Flask blueprint /api/v1/predictor/*
│   └── tests/
│       ├── test_panel.py
│       ├── test_features.py
│       ├── test_inference.py
│       ├── test_identity.py                  # enforces NRR identity invariant
│       └── test_kill_switch.py
└── models.py                                 # + PredictorCalibration table

config/
└── cdi_seed_public_benchmarks.json           # placeholder values for G2 review

migrations/
└── add_predictor_calibrations_table.py
```

---

## Performance Budget (locked, per M5 from review)

| Operation | Budget |
|---|---|
| Per-account inference (cache miss) | < 100ms |
| Per-account inference (cache hit) | < 10ms |
| Portfolio rollup, 30–100 accounts | < 2s |
| Monthly batch, all accounts × all tenants | < 5 min |
| Dashboard load, portfolio view | < 2s |
| Dashboard load, account drill-down | < 500ms |

Performance test included in Block 4 acceptance harness.

---

## Rollback Design (locked, per M6 from review)

Two independent feature flags:

| Flag | Scope | Effect when false |
|---|---|---|
| `FEATURE_PREDICTOR_V3_UI` | UI-level | Dashboard renders Wizard B legacy NRR; predictor output hidden |
| `FEATURE_PREDICTOR_API` | API-level kill switch | `/api/v1/predictor/*` returns `503` with `{"error": "predictor_disabled", "fallback": "wizard_b_legacy"}` |

**Combined behavior matrix:**

| `_API` | `_UI` | Behavior |
|---|---|---|
| true | true | Predictor v3 active end-to-end |
| true | false | Predictor API serves; UI ignores. Use for soak testing without user exposure. |
| false | true | UI calls API, gets 503, falls back to rendering Wizard B legacy NRR with a small "fallback active" badge. **Demo doesn't break.** |
| false | false | Wizard B legacy everywhere |

Both flags admin-toggleable in < 60s via `/admin/features`. Both audit-logged.

Acceptance harness (Block 4) includes a kill-switch test: pull `FEATURE_PREDICTOR_API`, verify dashboard renders Wizard B fallback within 5s of cache invalidation.

---

## Cold-Start Policy (locked, per M2 from review)

**Tenant-level cold start:** handled by CDI hierarchical priors (per design notes Q2).

**Account-level cold start (new addition):**

```python
if account.tenure_in_panel < 3:
    return predict_using_segment_baseline(
        account.segment, account.tenant_id,
        ci_inflation_factor=2.0
    )
```

API response carries `prediction_method: "cold_start"`. UI renders cold-start predictions with a visible "Insufficient history — wide CI" disclaimer.

Cold-start logic = segment-mean coefficients applied to current covariates + 2× bootstrap CI width.

---

## Phasing & Verification Gates

| Block | Days | Deliverable | Gates within block |
|---|---|---|---|
| **0** | 1 | This document, signed off | — |
| **1** | 3 | Panel construction, audit, CDI seed structure with placeholders, API contract documented | G1 (panel review) → G1.5 (data quality report) → G2 (CDI seed values) → G4 (API contract approval) |
| **2** | 5 | GLMM fit + diagnostics + sanity report | G3 (5-account sanity check, expanded to 30+ min) |
| **3** | 3 | API endpoint live; CFO/CRO dashboard surface behind `FEATURE_PREDICTOR_V3_UI=false` | G5 (dashboard surface screenshot approval) |
| **4** | 2 | Acceptance harness (structural + informational metrics + perf test + kill-switch test) | — |
| **5** | 1 | Deploy + verify + Wizard B coexistence audit | G7 (production go/no-go) |

**Total:** ~15 days focused work; 3 weeks calendar.

### Gate details

| Gate | When | What user reviews | Time |
|---|---|---|---|
| **G1** | Block 1 day 1 | One SQL file + 10 sample panel rows | 5 min |
| **G1.5** | Block 1 day 2 | Panel quality report: % missing months, censoring rates, outcome counts. **Hard fail** if any account >40% missing or any segment×tenant has <3 accounts. | 10 min |
| **G2** | Block 1 day 3 | CDI seed values from public benchmarks; confirm vintage and provenance | 10 min |
| **G3** | Mid-Block 2 | 5 named accounts, predicted NRR + CI + decomposition + top drivers per account; 5/5 directional gut-check required | 30+ min |
| **G4** | Start of Block 3 | API JSON contract — already in this doc; confirm if anything changes | 5 min |
| **G5** | Mid-Block 3 | Dashboard surface screenshot (CFO column layout) | 10 min |
| **G7** | End of Block 5 | Production deploy verification + Wizard B coexistence audit | 5 min |

**Total user time across 3 weeks:** ~75 minutes in 5–10 / 30 min slots.

---

## Real Customer Track (parallel to Phase 1 build)

A real customer is targeted for onboarding within 1 week of this document landing. They're the calibration cohort that converts Phase 1 acceptance from structural-only to structural + quantitative. This section captures their onboarding plan and how their data integrates into the predictor v3 build.

### Customer profile (placeholder — pending confirmation)

| Field | Value |
|---|---|
| `customer_id` | TBD (assigned at provisioning) |
| `vertical` | `saas_premium` |
| `saas_profile` (per A5) | `saas_smb` (auto-detected from $20K avg ARR) |
| Account count | 500 |
| Total ARR | $10M |
| Average ARR / account | $20K |
| Panel history available | 18 months |
| Outcome density | "Historical data available" — pending verification of definitive lifecycle subtypes in `outcomes.csv` |
| Hosting model | TBD — Option A (single-tenant SaaS on our cloud) or Option B (customer-cloud); critical clarification needed before provisioning |
| Beta disclosure + DPA | Yes — both will be signed |
| Healthcare? | No (AI-1 stays deferred) |
| Predictor v3 expectation | Lands on legacy Wizard B for first 3 weeks; migrates to predictor v3 when it ships (confirmed acceptable) |

### Disclosure language for the customer (week 1)

> *"Today's dashboard shows realized NRR — a backward-looking ledger from definitive lifecycle outcomes (churn, contraction, expansion, new logo). Forward-looking expected NRR per account, with confidence intervals and term decomposition (predictor v3), is shipping in approximately 3 weeks. You'll be the first tenant migrated when it ships. Until then, you have signals, arcs, KPI health, playbook execution, and narrative analytics — not predictive NRR. The Wizard B legacy NRR currently shown is the realized number, not a forecast."*

This is an honest position. It defends against AI-DD reviewers who would catch any pretense that the day-1 NRR figure is predictive.

### Phase 1 ↔ Phase 1.5 collapse condition

Phase 1 acceptance is locked as structural-only because synthetic data invalidates quantitative gates. **However:** if the real customer's data lands before Block 4 with sufficient outcome density, Phase 1.5 quantitative gates Q1–Q7 apply at Block 4 instead of being deferred.

**Sufficient outcome density** means: ≥ 30 closed lifecycle outcomes (definitive: `churn_lost`, `contraction`, `expansion_closed`, `new_logo`) across the customer's panel. Estimated: 500 accounts × 18 months at 5%/year churn alone = ~37 churn events; expansion + contraction add more. **Likely met.**

If met: Phase 1 acceptance = structural P1–P4 **plus** quantitative Q1–Q7. If not met: structural-only as documented; Q1–Q7 stay deferred to a later Phase 1.5 milestone when outcomes accumulate.

### Onboarding micro-plan (executes when Option A vs B is confirmed)

Conditional on `hosting_model = Option_A` (single-tenant SaaS on our cloud). If Option B, this track delays 1–2 weeks for IaC work and is split into a separate provisioning plan.

| Day | Action | Owner |
|---|---|---|
| Day 1 | Confirm hosting model, customer name, primary admin email. If Option A: provision tenant on EC2 per [`Customer_Admin_Provisioning_Runbook.md`](../GTM-docs/Customer_Admin_Provisioning_Runbook.md). Set `vertical='saas_premium'`, `saas_profile='saas_smb'`. Provision admin user. Issue magic-link. | Claude (with greenlight) |
| Day 2 | Send 4-CSV templates + [`Signal_Ingestion_Guide.md`](../GTM-docs/Signal_Ingestion_Guide.md). **Walk customer through `outcomes.csv` definitive-vs-narrative subtype distinction explicitly** — this gates whether Phase 1.5 quantitative gates apply. Beta disclosure + DPA signing track started in parallel (legal). | Claude + customer |
| Day 3 | Customer prepares data export. | Customer |
| Day 4 | First CSV upload. Wizard A/B/C run. **Smoke test all 5 dashboards (CFO/CRO/VP CS/CSM/Journey Intel) with 500 accounts.** Flag UI scaling issues immediately. | Claude |
| Day 5 | Fix any UI scaling issues found at Day 4. Customer trains on dashboards. | Claude + customer |
| Day 6–7 | Customer in steady state on legacy Wizard B. Their panel rows accumulating in DB for predictor v3 fit. | Customer |

Concurrently from Day 1: **Block 1 of predictor v3 build runs in parallel**, panel construction extends to include this tenant (multi-tenant from day one).

### Risks specific to this customer

| Risk | Severity | Mitigation |
|---|---|---|
| **UI scaling** — dashboards designed for ~30–100 accounts; 500 accounts may break tile rendering, drill-down lists, or load times | Medium | Day 4 smoke test catches it. ~half-day fix if pagination/virtualization needed. Add to Block 5 verification. |
| **Outcome subtype misuse** — customer populates `outcomes.csv` with narrative subtypes (`revenue_protected`, `churn_averted`) instead of definitive lifecycle subtypes (`churn_lost`, `expansion_closed`). NRR calculation pins at 100%; Phase 1.5 quantitative gates can't apply. | High | Day 2 walkthrough is explicit about this distinction. Review their first upload before Wizard B runs. |
| **Their internal NRR ledger ≠ our calculated NRR** — they likely already track NRR. Any divergence on day 1 will be challenged. | High | Position predictor v3 as forward-looking expected NRR with CI, not as a backward-ledger restatement. Their accounting NRR is not our target — it's the input to backfill validation. |
| **Wizard C calibration mismatch** — today auto-runs against HealthScore-derived success/fail. Should run against ContextNode OUTCOMEs once real outcomes exist. | Medium | Tier-2 redesign on backlog (per [Wizard C roadmap memo](../../../.claude/projects/-Users-manojgupta-CustomerSuccessAI-DataCenter/memory/roadmap_wizard_c_learn_from_context_graph.md)). Disclosure: "today's KPI weights are HealthScore-correlated; Wizard C v2 will retrain against your closed outcomes once accumulated." |
| **Hosting model = Option B (customer-cloud)** — would slip onboarding by 1–2 weeks for IaC. | High if confirmed | Confirm before Day 1. If B, the predictor v3 build still runs on schedule using customer 393 + the new tenant when it lands; UI migration to predictor v3 just slips for them by however long Option B provisioning takes. |

### Open questions for the customer (still pending answers)

1. **Hosting model — Option A or B?** Critical for Day-1 provisioning. Greenlight is for plan amendments only; Day-1 provisioning blocked until this resolves.
2. **Customer name + primary admin email.** Required for tenant provisioning.
3. **Expected upload day in the week.** Drives whether their data lands before Block 1 day 3 (panel construction includes them) or later (Block 1 stays customer-393 only; their panel adds when data lands).
4. **`qualitative_signals.csv` available?** Optional but valuable. If not, predictor v3 panel has gaps in some covariates for this tenant; mitigation is to use Wizard B's pattern features only for them.

These are tracked here, not in the AI-1/2/3 list, because they're customer-specific and resolve via the customer relationship rather than internal team decisions.

---

## What is NOT in scope for Phase 1

Explicit deferrals so they don't drift in:

| Feature | Deferred to | Reason |
|---|---|---|
| Bayesian hierarchical model with proper posteriors | Phase 2 (data + hire gated) | See Architecture Decision A1 |
| Counterfactual attribution / `cs_pulse_delta_pct` | Phase 4 (Wizard E) | Requires ≥ 50 closed outcomes per tenant + clean treatment timestamps |
| Cross-tenant empirical-Bayes refit of CDI templates | Phase 2 | Requires ≥ 5 mature tenants per vertical |
| Vertical-invariant covariate layer above CDI | Phase 1.5 | Optional enhancement; not on critical path |
| Healthcare segment thresholds | First healthcare prospect | Per AI-1 below |
| Joint estimation across sub-models 1/2/3 | Phase 2 (Bayesian) | Frequentist GLMM does sub-models independently |
| Portfolio covariance estimation | Phase 2 (≥ 2 yrs tenant data) | Insufficient panel length in Phase 1 |
| Concurrent-playbook handling in attribution | Phase 4 (month 9) | Per design notes Q3 |

---

## Open Action Items (inherited from design notes v3)

| # | Item | Owner | Due |
|---|---|---|---|
| AI-1 | Healthcare segment thresholds — placeholder from public benchmarks for v0; lock at first healthcare prospect | Manoj (placeholder); first healthcare prospect (lock) | Pre-Phase-1 (placeholder); data-gated (lock) |
| AI-2 | Benchmark→coefficient translation step (~2-day exercise to convert public-benchmark NRR distributions into informative GLMM starting values + ridge penalty calibration). **Folded into Block 1.** | Phase 1 build owner (Claude with G2 verification) | Block 1, before Block 2 starts |
| AI-3 | Reconcile Phase 1 estimate between docs | Manoj | Closed by this document |

---

## Sign-off

This document is the contract for Phase 1 execution. Once signed off:
- Architecture Decisions A1–A3 are locked. Changing them requires a new revision of this document.
- Phase 1 and Phase 1.5 ship/hold criteria are locked. Cannot be edited post-facto without a new revision.
- API contract is locked. Schema changes require a versioned `/api/v2/predictor/*` namespace.
- Verification gates G1–G7 are commitments to pause; the executor cannot proceed past a gate without approval.

| Role | Name | Date | Status |
|---|---|---|---|
| Architect | Manoj Gupta | 2026-05-06 | Signed: A1, A3, A4, A5, Phase 1 P1–P4, Phase 1.5 Q1–Q7. **Pending:** A2 (no objection raised — assumed accepted on commit); customer hosting-model resolution before Block 1 starts. |
| Executor | Claude (Opus 4.7) | 2026-05-06 | Authored v1.0; amended v1.1 |

---

## Revision history

| Date | Version | Author | Change |
|---|---|---|---|
| 2026-05-06 | v1.0 | Claude | Initial authored. Incorporates: design notes v3 (Q1-Q6, acceptance tests, hazard data shape); execution plan v1 (autonomy/gate structure); reviewer feedback round 4 (3 priority issues + 6 missing items + meta-pattern observation). |
| 2026-05-06 | v1.1 | Claude | Amendments after Manoj sign-off on A1 + Phase 1/1.5 criteria + Q1-Q7: added **A4** (Wizard B cleanup as contractual deliverable, single-PR with specific deletion list, P0 enforcement if not merged within 2 weeks of Phase 1.5 sign-off); added **A5** (two-profile SaaS segmentation: SaaS-Enterprise vs SaaS-SMB by median ARR auto-detection, separate threshold ladders, separate CDI templates); added **Real Customer Track** section (placeholder profile for first real-customer pilot — saas_smb, 500 accounts, $10M ARR, 18 months panel; disclosure language; Phase 1 ↔ Phase 1.5 collapse condition; day-by-day onboarding micro-plan conditional on Option A confirmation; tenant-specific risks; 4 open customer questions). |
