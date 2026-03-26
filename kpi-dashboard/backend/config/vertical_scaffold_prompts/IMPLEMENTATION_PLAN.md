# Vertical Scaffold & Data Generation — Implementation Plan

**Branch**: `feature/vertical-scaffold-nomenclature`
**Created**: 2026-03-15
**Status**: Planning — DO NOT merge until all items verified

---

## Context

We are making CS Pulse a **configuration-driven platform** where new verticals
can be stood up with minimal human intervention. An LLM seeds all domain files
(KPIs, weights, benchmarks, nomenclature, economics) with 95%+ accuracy,
a domain expert curates, and the platform launches.

This plan also covers 6 gaps found during audit of the load driver and
synthetic data generation infrastructure.

---

## Part A — Completed (this branch)

| # | Item | Status |
|---|------|--------|
| A1 | Industry benchmarks: curated seed file per vertical (dc2_s.csv, saas_premium.csv) | ✅ Done |
| A2 | Vertical nomenclature JSON (dc2_s.json, saas_premium.json) + useVerticalLabels() hook | ✅ Done |
| A3 | Backend API: GET/PUT /api/dc2s/config/nomenclature + customer overrides in CustomerConfig | ✅ Done |
| A4 | 10 expert-level LLM scaffold prompts (01–10) + system prompt + README | ✅ Done |
| A5 | Refactored industry_benchmarks from auto-generated → platform-curated seed file | ✅ Done |
| A6 | csv_schemas.json updated: industry_benchmarks moved from auto_generated to platform_curated | ✅ Done |
| A7 | AUTO_GENERATED_CG_FILES reduced to {decisions, signal_edges} (2 instead of 3) | ✅ Done |

---

## Part B — Synthetic Data Generator (Vertical-Aware)

### B1. Config-driven generator (Option B from discussion)

**Goal**: Single generator that reads vertical config and produces correct CSVs.

**Config file**: `config/synthetic_data_profiles/{vertical}.json`

```json
{
  "vertical": "dc2_s",
  "label": "Data Center Infrastructure",
  "kpi_source": "verticals/dc2_s/kpi_definitions.py",
  "catalog_var": "DC2S_KPIS",
  "pillars_var": "DC2S_PILLARS",
  "kpi_count": 38,
  "pillar_count": 5,
  "default_accounts": 10,
  "default_months": 12,
  "account_kpi_profiles": {
    "enterprise": {"pillars": ["P1","P2","P3","P4","P5"], "custom_kpis": 2},
    "mid_market": {"pillars": ["P1","P3","P5"], "custom_kpis": 0},
    "smb": {"pillars": ["P2","P5"], "custom_kpis": 0}
  },
  "industry": "data_center",
  "noise_range": [0.85, 1.15],
  "frequency_aware": true
}
```

**Changes needed**:
- [ ] Create `config/synthetic_data_profiles/dc2_s.json`
- [ ] Create `config/synthetic_data_profiles/saas_premium.json`
- [ ] Refactor `generate_synthetic_customer_data.py` to accept `--vertical` flag
- [ ] Load KPI catalog dynamically from profile config
- [ ] Verify output CSVs match vertical's csv_schemas.json definition

**Risk**: Medium — generator touches 4+ output files, must preserve backward compat for `--customer-id` flag.

---

### B2. Context graph generator (Vertical-Aware)

**Changes needed**:
- [ ] Refactor `generate_context_graph_data.py` to accept `--vertical` flag
- [ ] Story arc manifests: currently DC2S-specific language — need vertical-neutral arc templates or per-vertical arc sets
- [ ] Industry benchmark generation already uses seed file (Part A) — no change needed

**Risk**: Low — story arcs are mostly vertical-neutral (churn, expansion are universal patterns).

---

## Part C — Load Driver Enhancements

### C1. KPI Frequency-Aware Streaming

**Current**: All KPIs generated once/month regardless of defined frequency.
**Goal**: Group KPIs by frequency; emit measurements at correct cadence.

**Frequency mapping** (from kpi_definitions.py):
```
realtime  → daily aggregates (30/month)
daily     → 30 data points/month
weekly    → 4 data points/month
monthly   → 1 data point/month
quarterly → 1 data point/quarter
```

**Changes needed**:
- [ ] `csv_generator.py`: Group KPIs by frequency from catalog
- [ ] `csv_generator.py`: `generate_kpi_csv()` emits multiple rows per month for daily/weekly KPIs
- [ ] New scenario: `scenario_incremental_streaming.py` — simulates 90-day window with frequency-correct uploads
- [ ] `setup_sacme_tacme.py`: `run_incremental_simulation()` uses frequency grouping

**Risk**: Medium — changes CSV row count significantly, downstream tests may need adjustment.

---

### C2. Custom KPI Testing

**Current**: CUSTOM-* KPI API exists but is never tested by load driver.
**Goal**: New scenario that exercises the full custom KPI lifecycle.

**Changes needed**:
- [ ] New scenario: `scenario_custom_kpis.py`
  1. Creates customer via onboarding
  2. Adds 2 CUSTOM-* KPIs via `POST /api/dc2s/config/custom-kpi`
  3. Uploads kpi_measurements.csv with standard + custom KPI data
  4. Triggers `process-data`
  5. Verifies custom KPIs appear in health scores
  6. Deletes one custom KPI, re-processes, verifies removal
- [ ] `csv_generator.py`: Accept optional `custom_kpis` list parameter

**Risk**: Low — additive scenario, doesn't change existing tests.

---

### C3. Per-Account KPI Variation Testing

**Current**: All accounts get identical KPI sets.
**Goal**: Test accounts with different KPI coverage within same customer.

**Architecture decision needed**:
- Option 1: **Data-driven** — accounts simply have different measurements, scoring handles it (current arch supports this)
- Option 2: **Config-driven** — add `Account.enabled_kpi_overrides` field for per-account filtering

**Recommendation**: Option 1 first (no schema change). Score calculator already renormalizes weights when KPIs are missing.

**Changes needed**:
- [ ] New scenario: `scenario_mixed_kpi_coverage.py`
  1. Customer with 3 accounts
  2. Account 1 (enterprise): all 38 KPIs + 2 custom
  3. Account 2 (mid-market): P1 + P3 + P5 only (23 KPIs)
  4. Account 3 (smb): P2 + P5 only (16 KPIs)
  5. Verify: all 3 get valid L3 health scores
  6. Verify: L4 portfolio score correctly revenue-weights across different-sized sets
- [ ] Verify score_calculator weight renormalization is correct for partial pillar coverage

**Risk**: Low — additive scenario. Score calculator may have edge cases with missing entire pillars.

---

### C4. Vertical-Aware Load Driver

**Current**: Hardcoded to DC2S.
**Goal**: `--vertical` flag drives KPI catalog, CSV schemas, and scenario selection.

**Changes needed**:
- [ ] `csv_generator.py`: Accept `--vertical` flag, load catalog via `catalog_loader.py`
- [ ] `catalog_loader.py`: Support multiple catalog files (`dc2s_kpi_catalog.json`, `saas_premium_kpi_catalog.json`)
- [ ] `client.py`: No change needed (vertical-agnostic)
- [ ] `setup_sacme_tacme.py`: Accept `--vertical` flag, use vertical-specific company names/domains

**Risk**: Medium — touches core load driver infrastructure.

---

## Part D — Demo Manifest → Story Arc Migration

### D1. Deprecate Demo Manifests

**Current**: Two parallel data generation paths — demo manifests (3 simple patterns) and story arcs (8 rich narratives).
**Goal**: Unify under story arcs.

**Phase 1 (now)**: Both coexist. No changes.
**Phase 2 (next sprint)**:
- [ ] Map demo manifest patterns to story arcs:
  - `improving` → `arc_crisis_recovery`, `arc_stalled_deployment`
  - `stable_healthy` → `arc_land_and_expand`, `arc_seasonal_surge`
  - `declining` → `arc_silent_churn`, `arc_competitive_displacement`
- [ ] `generate_synthetic_customer_data.py`: Replace `--journey-patterns DEMO_MANIFEST` with `--story-arc` / `--health-aware`
- [ ] Story arcs drive KPI trajectories (phase plot points → KPI values)
- [ ] DEMO_MANIFEST.md generation deprecated

**Phase 3 (later)**:
- [ ] Remove DEMO_MANIFEST code paths entirely
- [ ] Story arc ID stored in customer metadata (replaces journey pattern label)

**Risk**: Medium — story arcs produce richer data but may break existing demo workflows.

---

## Part E — Scaffold Generator Script

### E1. `scripts/scaffold_vertical.py`

**Goal**: Single command to create a new vertical end-to-end.

```bash
python scripts/scaffold_vertical.py \
  --name "managed_services" \
  --label "Managed Services" \
  --industry "IT managed services" \
  --description "MSP customers managing IT infrastructure for SMBs" \
  --buyer-persona "VP of Service Delivery" \
  --llm-provider anthropic \
  --auto-curate false
```

**Workflow**:
1. Read system prompt from `config/vertical_scaffold_prompts/_system_prompt.md`
2. For each of the 10 LLM-dependent files:
   a. Read prompt template from `config/vertical_scaffold_prompts/NN_*.md`
   b. Inject vertical-specific context (name, industry, description, buyer persona)
   c. Call LLM API with system + user prompt
   d. Parse structured output (Python dict / JSON / CSV)
   e. Write to `verticals/{vertical}/` or `config/` as appropriate
   f. Mark as `curated: false`
3. Generate 9 boilerplate files (deterministic, no LLM needed)
4. Register vertical in `vertical_mapper.py`
5. Generate KPI catalog JSON from kpi_definitions.py
6. Print summary: "19 files created. 10 need expert curation."

**Changes needed**:
- [ ] Create `scripts/scaffold_vertical.py`
- [ ] Create `config/synthetic_data_profiles/` template
- [ ] Add Anthropic SDK dependency (or use existing if present)
- [ ] Test with `managed_services` vertical as proof of concept

**Risk**: High — this is the capstone. All other parts must work first.

---

## Execution Order (Recommended)

```
Sprint 1 (Current):
  ✅ Part A — Done (nomenclature, benchmarks, prompts)

Sprint 2:
  B1 — Config-driven synthetic data profiles
  C4 — Vertical-aware load driver (--vertical flag)

Sprint 3:
  C1 — Frequency-aware streaming
  C2 — Custom KPI scenario
  C3 — Mixed KPI coverage scenario

Sprint 4:
  B2 — Vertical-aware context graph generator
  D1 — Demo manifest → story arc migration (Phase 2)

Sprint 5:
  E1 — Scaffold generator script (capstone)
  D1 — Demo manifest cleanup (Phase 3)
```

---

## Files Impacted (Full List)

### Existing Files (Modify)
| File | Parts |
|------|-------|
| `backend/scripts/generate_synthetic_customer_data.py` | B1, D1 |
| `backend/scripts/generate_context_graph_data.py` | B2 |
| `load-driver/csv_generator.py` | C1, C2, C3, C4 |
| `load-driver/catalog_loader.py` | C4 |
| `load-driver/setup_sacme_tacme.py` | C1, C4 |
| `backend/utils/score_calculator.py` | C3 (verify edge cases) |
| `backend/verticals/dc2_s/api_routes.py` | C2 (verify custom KPI scoring) |

### New Files (Create)
| File | Part |
|------|------|
| `config/synthetic_data_profiles/dc2_s.json` | B1 |
| `config/synthetic_data_profiles/saas_premium.json` | B1 |
| `load-driver/scenarios/scenario_incremental_streaming.py` | C1 |
| `load-driver/scenarios/scenario_custom_kpis.py` | C2 |
| `load-driver/scenarios/scenario_mixed_kpi_coverage.py` | C3 |
| `scripts/scaffold_vertical.py` | E1 |

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-15 | Industry benchmarks = curated seed file, not auto-generated | Avoid circular trap of using own KPI targets as "benchmarks" |
| 2026-03-15 | Ship with curated=false ON by default | Better than no benchmarks; transparency via admin badge |
| 2026-03-15 | Per-account KPI variation via data (not config) first | Score calculator already handles missing KPIs; no schema change needed |
| 2026-03-15 | Story arcs supersede demo manifests | Story arcs are strictly richer; demo patterns map cleanly to arcs |
| 2026-03-15 | All 10 LLM-dependent files use expert prompts | 95%+ accuracy target; humans curate only edge cases |
| 2026-03-15 | kpi_definitions.py is LLM-seedable (not a hard human blocker) | With expert prompts + industry context, LLM produces production-ready KPIs |

---

## Risk Summary

| Risk | Severity | Mitigation |
|------|----------|------------|
| Frequency-aware streaming changes CSV row counts | Medium | Add row count assertions to existing tests |
| Scaffold generator LLM output quality | Medium | Expert prompts + curated flag + human review |
| Story arc migration breaks existing demos | Medium | Phase 2 keeps both paths; deprecate in Phase 3 |
| Per-account KPI edge cases in score calculator | Low | Score calculator already renormalizes; add targeted tests |
| Load driver --vertical flag touches core infrastructure | Medium | Feature flag: default to dc2_s if no flag given |
