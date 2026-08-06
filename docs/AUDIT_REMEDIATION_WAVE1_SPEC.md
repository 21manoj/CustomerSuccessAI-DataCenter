# Audit Remediation — Wave 1 Spec

**Date:** August 4, 2026
**Source:** `AUDIT_REPORT_E2E_2026-08-03.md` (repo root)
**Decisions (Manoj, Aug 4):** canonical health store = `HealthScore`/`PillarScore` (drain `HealthTrend`); Wizard D = explicit trigger + operator nudge / lazy dashboard trigger (built in Wave 2, decision recorded here).
**Scope:** three workstreams, ~1 week. Each lands as its own test-first branch → EC2/local verification → merge, per the established session pattern.

---

## Workstream A — Account-Health Convergence (audit #18, C-18, C-19, F3, B-2)

### A0. Target architecture

One shared service, one canonical store:

```
utils/account_health.py
    get_account_health(account_id, *, customer_id=None, db_session=None) -> AccountHealth | None
```

- **Canonical store:** `HealthScore` (+ pillar detail from `PillarScore` when present, else `contributing_pillars` JSON) — what the pipeline writes (`process_data_pipeline.py:178-199`) and MCP reads.
- **Base implementation to lift:** `mcp_server/common.py:179 get_precalculated_scores` — it has the correct month-pinned pillar semantics (pillar rows matched to the same `measurement_month` as the health row).
- **Return shape:** dataclass/dict, NOT a tuple (kills the 3-tuple vs 4-tuple arity fork, audit B-2):
  ```
  AccountHealth: health_score float, measurement_month date, pillars dict,
                 source 'health_scores'|'computed', missing bool, missing_reason str|None
  ```
- **Missing-data semantics:** return `None`/`missing=True` with a reason. **Never** a magic default. This removes:
  - Flask's 50.0 proxy + `health_score == 50.0` sentinel (`kpi_api.py:151`, C-19)
  - Ask-AI fallback's silent `0` default (`ask_ai_tools.py:596`)
- **Churned handling:** service exposes `account_status`; callers exclude churned accounts from at-risk aggregates per the invariant in `tests/test_context_graph_invariants.py:631` (fixes the CFO `arr_at_risk` double-count too — audit §4.1).

### A1. Reader migrations (each = one commit, with before/after parity check)

| Reader | Today | Change |
|---|---|---|
| `kpi_api.py:96-170` `/api/accounts` | HealthTrend → 50.0-proxy → DC2SKPI recompute on `==50.0` sentinel | Call service; render explicit "no data" state; delete proxy call + sentinel |
| `ask_ai_tools.py:596-637` `_execute_direct` | Raw HealthScore, default 0, pillars not month-pinned, no churned exclusion | Call service; align churned exclusion with MCP `get_at_risk_accounts` |
| `mcp_server/cs_pulse_mcp_server.py:206` + `mcp_server/common.py:179` | 2 of the 4 `get_precalculated_scores` copies | Both delegate to service (keep thin wrappers for signature compat during transition) |
| `verticals/dc2_s/api_routes.py:180` | 4-tuple copy | Delegate to service; update its ~2 unpack sites (`:572`, `:2666`) |
| `utils/vertical_health.py:202` | 4th copy | Delete; import from service |
| `health_trend_api.py:255-380` (latest score + trigger evaluators) | HealthTrend direct | Call service |
| `health_score_storage.py:261` + `time_series_api.py:44` | HealthTrend direct, **no tenant filter** | Call service **with mandatory `customer_id`** (fixes C-18); reject requests without a session-resolved customer |

### A2. Writer/drain plan (two releases)

- **Release 1 (this wave):** all readers on canonical store. HealthTrend writers (`health_score_rollup_subscriber.py`, `health_score_storage.py`, `rehydration_api.py`) keep writing (dual-write), plus a **divergence logger**: on each service read, if a HealthTrend row exists for the same (account, month) and differs from HealthScore by >0.5 pts, log `health_store_divergence` at WARNING with both values.
- **Release 2 (after ≥1 week of clean divergence logs on the live env):** stop HealthTrend writes, mark model deprecated-read-only, schedule table drop for a later migration. NOT in Wave 1 scope — just leave the logger in.

### A3. Tests (required before merge, per paired clean/dirty convention)

1. **Cross-surface parity:** same seeded account → `/api/accounts`, MCP `get_account_health`, Ask-AI `_execute_direct` all return the identical health number and pillar set.
2. **Missing-data:** account with zero KPI rows → all three surfaces report explicit missing (no 50, no 0).
3. **Score-exactly-50:** account legitimately scoring 50.0 → NOT treated as missing, NOT recomputed.
4. **Tenant isolation:** `time_series_api` request for another tenant's account_id → 403/404, never data (dirty test for C-18).
5. **Churned exclusion:** churned account excluded from at-risk ARR on both CFO tile and MCP tool.

### A4. Explicitly out of scope for Wave 1

L4 persistence, `bootstrap_weights_config.json` tier unification (the two-scoring-stacks issue, audit §3 stage 4), the noop-0.0 scorer fallback — these are real but separable; folding them in doubles the blast radius. Log as Wave-2+ candidates.

---

## Workstream B — MCP Auth Pass (audit #15, C-10)

### B1. Rule

Every `@mcp.tool` that reads tenant data requires `_require_auth(customer_id)`; every tool that **writes** or crosses tenants requires it with no exceptions. Pattern already exists in `mcp_server/auth.py` — this is application, not invention.

### B2. The 21 tools, triaged

- **Write paths (do first, no debate):** `trigger_wizard`, `upload_csv`, `process_data`, `execute_playbook`, `close_playbook`, `clone_customer`.
- **Admin-scope decision needed per tool:** `create_customer` (likely requires an *admin* API key rather than tenant key — it creates the tenant), `get_portfolio_cross_customer_comparison` (cross-tenant by design → admin key only).
- **Read paths:** remaining 13 from the audit's list — add standard tenant auth.

### B3. Tests

Per tool: unauthenticated call → rejected; wrong-tenant key → rejected; correct key → succeeds. One parametrized test over the tool list, not 21 hand-written tests.

### B4. Compatibility note

Claude.ai connector currently pins `X-Customer-ID` per the existing setup — verify the connector's key flow still passes after enforcement **before** merging (test against local MCP HTTP transport; EC2 is stopped).

---

## Workstream C — Fix the Drift Auditor (audit §4.2 "why the audit missed it")

`scripts/audit_flask_mcp_drift.py` — two structural fixes so Wave 1's convergence work *stays* converged:

1. **Kill the 9-file allowlist** (`:114-121`): glob `backend/**/*_api.py` + `backend/verticals/*/api_routes.py` + `signal_engine/ingest_api.py`. Keep an explicit skip-list (with reasons) instead of an include-list.
2. **Parse `return jsonify({...})`** via AST (today only bare `return {...}` literals are read; everything else becomes `return_unknown=True` and silently passes). Also compare one level of nested keys.
3. Re-run → triage every new finding into: fix now (if trivial), allowlist-with-reason, or backlog. Expected: the audit's A-1..A-7 pairs all surface — allowlist them referencing the audit report rather than fixing all in Wave 1.
4. Wire into CI if a CI harness exists; otherwise add to the pre-demo checklist alongside the demo-alignment playbook.

---

## Recorded for Wave 2 (decision made, build later)

**Wizard D trigger design** (decision: explicit + nudge / lazy dashboard trigger — never silent auto-run):
1. Fix `trigger_wizard` to accept `'d'` (`cs_pulse_onboarding.py:2272` — currently the fully-written 'd' branch at `:2320-2335` is unreachable dead code).
2. `process_data` result gains `calibration_needed: bool` (true when no active tenant `PredictorCalibration`).
3. CRO/CFO dashboard payloads gain `calibration_status`; frontend shows a nudge banner ("Predictions are running on pooled priors — run calibration").
4. Optional lazy path: dashboard endpoint may trigger Wizard D once when calibration is absent (observed runtime ~0.3s), guarded by an attempted-at timestamp so it never loops. Nudge is primary; lazy is fallback.

---

## Sequencing within the week

Day 1: C (auditor) — it's the guard for everything after. Day 1-2: B (auth). Day 2-5: A (convergence), reader-by-reader with parity tests green at each step. Divergence logger runs from Day 5 onward.
