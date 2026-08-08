# 08 — Persona Dashboards

**Layer:** Interface

**Status:** ✅ Validated — see [Validation Note](#validation-note) at the bottom.
A spec-only fresh-agent rebuild (2026-08-07) proved two defects with executable
tests — one HIGH (an `envelope(persona=…)` call that would `TypeError` every
dashboard) and one MEDIUM (an ARR accessor that dropped an explicit zero) — both
fixed below.

## Purpose

Present the same canonical health and revenue numbers to four different buyers —
CRO, CFO, VP-CS, CSM — each through the lens that person acts on, without ever
letting the number itself change between them. A CFO asking "where are my CS
dollars going" and a CRO asking "how much revenue is at risk" are looking at one
underlying truth from two angles; if the at-risk figure on the CRO screen and
the at-risk figure on the CFO screen disagree, the product has lost the room.
The other half of the job is the **two-layer indicator model** — the platform's
core differentiator: surface TRAILING health (what the KPIs already say happened)
next to LEADING health (what the qualitative signals say is about to happen), and
never let the second be silenced by the first. The gap between the two layers is
the early warning the client bought; a dashboard that hides a rising signal
because the KPI rollup still looks green has thrown away the whole point.

## Boundary

**Owns:**
- The **persona payload contract**: given a resolved tenant and a persona, an
  assembled dashboard payload that presents the shared canonical metrics through
  that persona's lens (CFO = investment/dollars, CRO = revenue/NRR, VP-CS =
  team/portfolio, CSM = account actions).
- The **two-layer assembly**: a payload that carries a `trailing` block (KPI
  health rollup, health-band exposure, trailing NRR) and a `leading` block
  (open signals, confirmed causal risk, forecast NRR), with the leading block
  **not filtered by** the trailing block (Gotcha 7).
- The **L4 revenue-weighted rollup**: customer-level portfolio health as the
  revenue-weighted average of L3 account health, with explicit, tested handling
  of churned, zero-ARR, and no-data accounts (Gotchas 1, 4, 8).
- The **single-source metric rule**: exactly one compile function per canonical
  metric (`revenue_at_risk`, `revenue_protected`, `expansion_pipeline`, portfolio
  health), called by every persona AND every surface (Flask route, MCP tool,
  in-app assistant) — the thing that keeps the numbers identical across screens
  (Gotchas 3, 5).
- **Envelope stamping** for dashboard payloads (`scope`, `persona`, `mode`,
  `arr_basis`/`arr_basis_value`), reusing Module 07's `envelope()`.

**Explicitly does not own:**
- L1/L2/L3 scoring math — Module 03. This module reads L3 account health and L2
  pillar scores; it never recomputes a KPI or pillar score.
- The context graph, signal nodes, and **revenue aggregation** — Module 04. This
  module calls Module 04's provenance-aware aggregator for the revenue bundle
  and **never sums revenue from nodes or accounts itself** (Gotcha 2).
- Signal extraction from raw text — Module 06. This module reads already-stored
  signals.
- Wizard / Predictor NRR forecasts — Module 05. This module displays
  `wizard_b_nrr` and `predictor_v3_nrr`; it does not compute them.
- Tenant auth + `customer_id` resolution — Module 07 (and the shared auth
  middleware). This module receives an already-resolved `customer_id` and a
  verified persona scope; the CEO cross-customer (PE-portfolio) mode requires
  Module 07's `require_cross_customer_auth`.
- The React components themselves and their copy/labels — Config (client
  presentation). The Engine is the payload-assembly contract; the frontend
  renders it.

## Dependencies

- **Module 01 (Data Model):** `Customer`, `Account` (with `account_status`,
  `revenue`, and `profile_metadata` JSON that may carry `arr` and `assigned_csm`
  — a field in JSON, not a column, see Gotcha 6). An accessor listing **all** of
  a customer's accounts, churned included (partitioning happens here, piece 1).
- **Module 03 (Health Scoring):** `read_scores(account_id) -> (health_L3,
  pillar_scores, status)` where `health_L3` is a float **or `None` when the
  account has no scored data** — `None`, never a sentinel like `50.0` (Gotcha 4).
- **Module 04 (Context Graph):** `aggregate_revenue_with_provenance(customer_id)
  -> {at_risk, protected, expansion, arr_basis, arr_basis_value}` (the assessed,
  deduped, confidence-thresholded revenue bundle — the ONLY source of these
  numbers), and `open_signals(customer_id)` returning unresolved SIGNAL nodes.
- **Module 05 (Wizards):** `wizard_b_nrr(customer_id)` (trailing) and
  `predictor_v3_nrr(customer_id)` (leading).
- **Module 07 (MCP Tool Layer):** the `envelope()` helper and, for the CEO
  cross-customer mode, `require_cross_customer_auth`.

### Data Shapes

```
Account (owned by Module 01 — fields this module reads):
  account_id (PK), customer_id (FK, NOT NULL),
  account_status (string, nullable — "churned" is the terminal state; a churned
    account is excluded from BOTH the active-health rollup and the risk tiles,
    reported separately, see Gotcha 1),
  revenue (numeric, nullable), profile_metadata (JSON, nullable — may hold
    "arr" and "assigned_csm"; reading a JSON key as if it were a column raises,
    see Gotcha 6)

Account summary (assembled by this module, per account):
  account_id, health_L3 (float OR None — None = no scored data, NOT 50.0),
  arr (float — profile_metadata.arr or the revenue column, 0.0 if neither),
  status (string), pillar_scores (dict)

L4 rollup result:
  health (float OR None — None when no active account has scored data),
  method ("revenue_weighted" | "simple_unweighted" | "no_scored_accounts"),
  n (active accounts), n_scored, n_zero_arr, n_no_data

Dashboard payload envelope (via Module 07 envelope()):
  scope ("portfolio" for a single customer's aggregated accounts;
         "platform" for the CEO cross-customer PE-portfolio mode),
  persona ("cro" | "cfo" | "vpcs" | "csm" | "ceo"),
  mode ("single_customer" | "portfolio_of_customers"),
  arr_basis, arr_basis_value,
  trailing { portfolio_health (L4 result), exposure_risk, wizard_b_nrr },
  leading  { signals, confirmed_risk, predictor_nrr },
  churn    { churned_count, churned_arr },
  ...persona-specific tiles...
```

**Nullable rule (this module):** `health_L3` (per account) and the L4 `health`
are both legitimately `None` (no scored data / cold-start / all-churned).
`account_status`, `revenue`, and `profile_metadata` are all nullable. Every
rollup and tile must handle `None` without raising AND without substituting a
magic number — an account with no data is `None`, not `50.0` (Gotcha 4). Each
`None` case has its own Acceptance Criterion; the non-null path passing proves
nothing about it.

## Engine vs. Config

**Engine (build once):**
- `partition_accounts` (active vs churned) and the per-account summary assembly.
- `rollup_L4` (revenue-weighted, with the churned/zero-ARR/no-data/method logic).
- The single-source metric compile functions (`revenue_bundle`, `exposure_risk`) and
  the rule that every persona/surface calls them rather than recomputing.
- `build_dashboard` (the two-layer assembly) and `persona_lens` (tile selection
  and labeling that never recomputes a shared metric).
- The executable parity checks (`assert_persona_parity`,
  `assert_surface_parity`) and envelope stamping.

**Config (an FDE fills in per client):**
- Which personas exist and which tiles each shows; tile copy/labels; the React
  components.
- CFO pillar-investment weights and the Power-of-1 ROI parameters; health-band
  thresholds for exposure (these come from Module 03's centralized thresholds —
  the Config here is only which bands map to which tile).
- Whether the client has a CEO PE-portfolio (`portfolio_of_customers`) mode at
  all.

## Build Prompt

> Build the persona-dashboard payload layer. Six numbered pieces. Every helper
> is either defined below OR is a named dependency hook whose contract
> Dependencies states — `module01_accounts_for_customer`, `module03_read_scores`,
> `module04_aggregate_revenue_with_provenance`, `module04_open_signals`,
> `module05_wizard_b_nrr`, `module05_predictor_v3_nrr`, and `envelope` (Module
> 07). There are no *undefined* helpers of this module's own. This layer computes
> no KPI, pillar, or revenue number itself — it reads L3 health, reads the
> revenue bundle, and arranges them; any arithmetic here is aggregation across
> accounts, never re-derivation of a delegated number.
>
> Origin references to follow, not reinvent:
> `kpi-dashboard/backend/executive_dashboard_api.py` (CRO `:658`, CFO `:1051`,
> CEO `:1661`), `kpi-dashboard/backend/customer_performance_summary_api.py:301`
> (the L4 formula), `kpi-dashboard/backend/utils/context_graph.py:575`
> (`aggregate_revenue_with_provenance`), `kpi-dashboard/backend/utils/
> executive_dashboard_mcp.py` (the one-compile-fn-per-surface pattern),
> `docs/KT_dashboard_data_lineage_and_evals.md` (the two-layer model + parity
> invariants).
>
> 1. **Account partition + per-account summary.** List ALL accounts (churned
>    included), read L3 health from Module 03 (a float or `None`), resolve ARR,
>    and split churned out. `health_L3` stays `None` when unscored — do not
>    substitute a number (Gotcha 4):
>    ```
>    def account_arr(acct) -> float:
>        meta = acct.profile_metadata if isinstance(acct.profile_metadata, dict) else {}
>        arr = meta.get("arr")
>        if arr is not None:              # profile_metadata.arr wins when the key
>            return float(arr)            # is present, including an explicit 0
>        return float(acct.revenue or 0)  # else the revenue column, else 0.0
>
>    def assigned_csm(acct):
>        # assigned_csm is a KEY in the profile_metadata JSON, not a column —
>        # reading acct.assigned_csm raises AttributeError (Gotcha 6).
>        meta = acct.profile_metadata if isinstance(acct.profile_metadata, dict) else {}
>        return meta.get("assigned_csm")
>
>    def partition_accounts(customer_id):
>        active, churned = [], []
>        for acct in module01_accounts_for_customer(customer_id):   # ALL statuses
>            health_L3, pillars, status = module03_read_scores(acct.account_id)
>            row = {"account_id": acct.account_id, "health_L3": health_L3,
>                   "arr": account_arr(acct), "status": acct.account_status,
>                   "pillars": pillars}
>            if (acct.account_status or "").lower() == "churned":
>                churned.append(row)
>            else:
>                active.append(row)
>        return active, churned
>    ```
>
> 2. **L4 revenue-weighted rollup.** Churned already excluded (piece 1). Skip
>    no-data accounts (health `None`) rather than counting them as any value;
>    label the method; return `None` health when nothing is scored:
>    ```
>    def rollup_L4(active_summaries) -> dict:
>        scored = [a for a in active_summaries if a["health_L3"] is not None]
>        n_no_data = len(active_summaries) - len(scored)
>        if not scored:
>            return {"health": None, "method": "no_scored_accounts",
>                    "n": len(active_summaries), "n_scored": 0,
>                    "n_zero_arr": 0, "n_no_data": n_no_data}
>        total_arr = sum(a["arr"] for a in scored)
>        n_zero_arr = sum(1 for a in scored if not a["arr"])
>        if total_arr > 0:
>            health = sum(a["health_L3"] * a["arr"] for a in scored) / total_arr
>            method = "revenue_weighted"
>        else:
>            # every scored account has zero ARR — weighting is undefined, so a
>            # simple mean is the honest fallback, but it is a DIFFERENT number,
>            # so the `method` field below labels it to distinguish it from weighted.
>            health = sum(a["health_L3"] for a in scored) / len(scored)
>            method = "simple_unweighted"
>        return {"health": round(health, 1), "method": method,
>                "n": len(active_summaries), "n_scored": len(scored),
>                "n_zero_arr": n_zero_arr, "n_no_data": n_no_data}
>    ```
>    `n_zero_arr` is surfaced because a zero-ARR account contributes zero weight
>    and is otherwise invisible in a revenue-weighted mean (Gotcha 8).
>
> 3. **Single-source metric compile functions.** These are the ONLY producers of
>    their numbers; every persona and every surface reads from here. Computing
>    any of them a second way is how two personas drift (Gotcha 5) and how three
>    surfaces drift (Gotcha 3):
>    ```
>    def revenue_bundle(customer_id) -> dict:
>        # Module 04 owns the aggregation (provenance, dedup, confidence gate).
>        # This layer does not sum revenue from nodes or from account ARR (Gotcha 2).
>        prov = module04_aggregate_revenue_with_provenance(customer_id)
>        return {"revenue_at_risk": prov["at_risk"],
>                "revenue_protected": prov["protected"],
>                "expansion_pipeline": prov["expansion"],
>                "arr_basis": prov["arr_basis"],
>                "arr_basis_value": prov["arr_basis_value"]}
>
>    HEALTH_BANDS = [("critical", 0, 50), ("at_risk", 50, 70)]  # Config: from Module 03 thresholds
>    def exposure_risk(active_summaries) -> dict:
>        # TRAILING exposure = health-band membership × ARR, over ACTIVE accounts
>        # only (churned excluded — Gotcha 1). This is distinct from the LEADING
>        # confirmed-risk number in the revenue bundle; the two are not summed.
>        out = {band: 0.0 for band, _, _ in HEALTH_BANDS}
>        for a in active_summaries:
>            if a["health_L3"] is None:
>                continue
>            for band, lo, hi in HEALTH_BANDS:
>                if lo <= a["health_L3"] < hi:
>                    out[band] += a["arr"]
>        return out
>    ```
>
> 4. **The two-layer assembly.** `leading` is built from signals and forecasts
>    and is NOT filtered by `trailing` health — an account with a green KPI
>    rollup and a rising signal still shows the signal (Gotcha 7). The gap
>    between layers is presented as both NRR lenses side by side, not as one
>    subtracted from the other:
>    ```
>    def build_layers(customer_id, active_summaries):
>        trailing = {
>            "portfolio_health": rollup_L4(active_summaries),   # piece 2
>            "exposure_risk":    exposure_risk(active_summaries),  # piece 3
>            "wizard_b_nrr":     module05_wizard_b_nrr(customer_id),   # trailing
>        }
>        leading = {
>            "signals":        module04_open_signals(customer_id),   # unfiltered by health
>            "confirmed_risk": revenue_bundle(customer_id)["revenue_at_risk"],  # causal
>            "predictor_nrr":  module05_predictor_v3_nrr(customer_id),  # leading forecast
>        }
>        return trailing, leading
>    ```
>
> 5. **Persona lens + assembly.** `persona_lens` selects and labels tiles and may
>    add persona-only content (CFO investment allocation, CRO story arcs) — but
>    it reads every shared metric from `bundle`/`trailing`/`leading` and
>    recomputes none of them. The whole payload is stamped with Module 07's
>    `envelope()`:
>    ```
>    def scope_for(mode) -> str:
>        return "platform" if mode == "portfolio_of_customers" else "portfolio"
>
>    def build_dashboard(customer_id, persona, mode="single_customer") -> dict:
>        active, churned = partition_accounts(customer_id)
>        trailing, leading = build_layers(customer_id, active)
>        bundle = revenue_bundle(customer_id)          # single source
>        churn = {"churned_count": len(churned),
>                 "churned_arr": sum(a["arr"] for a in churned)}
>        tiles = persona_lens(persona, trailing, leading, bundle, churn, active, churned)
>        payload = {"trailing": trailing, "leading": leading, "churn": churn,
>                   "mode": mode, "persona": persona, **tiles}
>            # persona is carried INSIDE payload — Module 07's envelope
>            # (scope, payload, arr_basis=, arr_basis_value=) has no persona param
>        return envelope(scope_for(mode), payload,
>                        arr_basis=bundle["arr_basis"],
>                        arr_basis_value=bundle["arr_basis_value"])
>
>    def persona_lens(persona, trailing, leading, bundle, churn, active, churned):
>        shared = {"revenue_at_risk": bundle["revenue_at_risk"],
>                  "revenue_protected": bundle["revenue_protected"],
>                  "expansion_pipeline": bundle["expansion_pipeline"]}
>        if persona in ("cro", "cfo", "ceo"):
>            return shared            # CRO/CFO/CEO share the revenue bundle verbatim
>        if persona == "vpcs":
>            return {"portfolio_health": trailing["portfolio_health"], **shared}
>        if persona == "csm":
>            return {"accounts": active, **shared}   # CSM works the account list
>        raise ValueError(f"unknown persona: {persona}")
>    ```
>    Module 07's shipped `envelope(scope, payload, arr_basis=, arr_basis_value=)`
>    has no `persona` parameter, so `persona` is carried inside `payload` — it
>    still surfaces at the top level because `envelope` returns
>    `{"scope": scope, **payload}`. This keeps Module 08 decoupled from Module
>    07's already-validated signature; passing `persona=` to `envelope` would
>    raise `TypeError` and take down every dashboard (the exact crash this note
>    prevents).
>
> 6. **Parity — persona and surface.** Two executable checks. Persona parity: the
>    shared bundle metrics are identical across CRO/CFO/CEO (they read the same
>    `bundle`). Surface parity: the MCP tool and the Flask route return the same
>    payload for the same `(customer_id, persona)` because both call
>    `build_dashboard` — not two reimplementations:
>    ```
>    SHARED_METRICS = ("revenue_at_risk", "revenue_protected", "expansion_pipeline")
>
>    def assert_persona_parity(customer_id):
>        payloads = {p: build_dashboard(customer_id, p) for p in ("cro", "cfo", "ceo")}
>        for m in SHARED_METRICS:
>            vals = {p: payloads[p][m] for p in payloads}
>            if len(set(vals.values())) > 1:
>                raise AssertionError(f"persona parity drift on {m}: {vals}")
>
>    def assert_surface_parity(customer_id, persona, mcp_call, flask_call):
>        # Both surfaces must route through build_dashboard. Compare the metrics
>        # that matter, not incidental ordering.
>        a, b = mcp_call(customer_id, persona), flask_call(customer_id, persona)
>        for m in SHARED_METRICS:
>            if a[m] != b[m]:
>                raise AssertionError(f"surface parity drift on {m}: mcp={a[m]} flask={b[m]}")
>    ```

## Acceptance Criteria

- **L4 is revenue-weighted, churned-excluded.** Two active accounts (health 80 @
  $900k, health 40 @ $100k) and one churned account (health 10 @ $5M) →
  `portfolio_health.health == 76.0` (`(80·900k + 40·100k)/1,000k`), `method ==
  "revenue_weighted"`, and the churned $5M/health-10 does **not** move it.
  `churn.churned_arr == 5,000,000` and `churn.churned_count == 1` are reported
  separately. Assert the churned account changes neither `portfolio_health` nor
  `exposure_risk`.
- **Zero-ARR active account is counted, not hidden (Gotcha 8).** Add a third
  active account health 20 @ $0 to the case above: `portfolio_health.health`
  stays `76.0` (zero weight), but `n_zero_arr == 1` and `n_scored == 3`. Assert
  the zero-ARR account is visible in the counts even though it moved no weight.
- **All-zero-ARR active accounts → labeled simple mean.** Every active account
  has ARR 0: `method == "simple_unweighted"`, `health` is the plain mean, and
  the label is present so it is not read as weighted.
- **No-data account is `None`, never `50.0` (Gotcha 4).** An active account with
  `health_L3 = None` is excluded from the weighted sum, counted in `n_no_data`,
  and never contributes a `50.0`. A portfolio where a real account genuinely
  scores exactly `50.0` is treated as scored (contributes 50), not as missing —
  assert the `50.0`-real and `None`-missing cases produce different rollups.
- **Cold-start / all-churned → `health: None`.** No active scored accounts →
  `portfolio_health.health is None` and `method == "no_scored_accounts"`, and
  `build_dashboard` returns a valid enveloped payload (does not raise).
- **Leading layer is not filtered by trailing (Gotcha 7).** An account with L3
  health 85 (healthy, trailing) that has an open signal still appears in
  `leading.signals`. Assert that raising every account's health above threshold
  leaves `leading.signals` unchanged — signals are queried independent of KPI
  state.
- **Revenue comes from the bundle, never summed here (Gotcha 2).** Stub
  `module04_aggregate_revenue_with_provenance` to return a known `at_risk`, and
  assert `revenue_at_risk` on every persona equals that value — not the sum of
  at-risk accounts' ARR. Assert the module contains no code path that sums
  account ARR into `revenue_at_risk`.
- **Persona parity (Gotcha 5).** `assert_persona_parity` passes; then stub one
  persona to recompute `revenue_at_risk` a second way (e.g. from exposure) and
  assert the check RAISES, naming the drifted metric. A parity test that cannot
  detect a divergence is worthless — prove it bites.
- **Surface parity (Gotcha 3).** `assert_surface_parity` passes when both
  surfaces call `build_dashboard`; then point the "MCP" surface at a second,
  slightly different implementation and assert it RAISES. This is the executable
  form of "one compile function per metric."
- **`assigned_csm` read from JSON, not a column (Gotcha 6).** An account whose
  `profile_metadata = {"assigned_csm": "Dana"}` and which has no `assigned_csm`
  attribute yields `assigned_csm(acct) == "Dana"`; an account with
  `profile_metadata = None` yields `None` and does not raise.
- **Envelope + scope.** Every persona payload carries `scope` (`portfolio` for
  single-customer, `platform` for `portfolio_of_customers`), `persona`, `mode`,
  and `arr_basis`/`arr_basis_value`. A CEO `portfolio_of_customers` payload
  scopes `platform`. `persona` is carried inside `payload` (Module 07's
  `envelope` has no `persona` param) and surfaces at the top level — assert
  `build_dashboard` binds against the real Module-07 `envelope(scope, payload,
  arr_basis=, arr_basis_value=)` signature without raising `TypeError`, and that
  `persona` appears in the returned payload.
- **ARR resolution precedence.** `account_arr` returns `profile_metadata.arr`
  when present, else the `revenue` column, else `0.0`; assert all three,
  including `profile_metadata = None`.

## Reference Test Harness

1. **L4 rollup matrix** — a fixture builder for accounts (health incl. `None`,
   ARR incl. `0`, status incl. `churned`) driving: revenue-weighted normal,
   churned-excluded, zero-ARR-counted, all-zero-ARR simple-mean, `None`-vs-real
   `50.0`, and cold-start `None`. Each asserts the number AND the `method`/counts.
2. **Two-layer independence** — assert `leading.signals` is invariant to
   trailing health: run once, raise all account health above threshold, run
   again, assert identical signal set. A mutation check: add a
   `if account.health >= 70: drop signal` filter and assert this test flips.
3. **Parity pair** — `assert_persona_parity` and `assert_surface_parity`, each
   with a mutation (recompute a metric a second way / point a surface at a second
   impl) proving the assertion raises. A parity check that never fails is
   indistinguishable from no check.
4. **Revenue-source containment** — stub the Module 04 aggregator; assert every
   persona's `revenue_at_risk` equals the stub and that no code path sums account
   ARR into it (source inspection + a fixture where summed-ARR ≠ assessed-risk,
   asserting the assessed number wins).
5. **Nullable/JSON suite** — `health_L3=None`, `profile_metadata=None`,
   `account_status=None`, and `assigned_csm` as a JSON key: each asserts no raise
   and the correct default.

## Known Gotchas

**1. Churned accounts double-counted as risk, and counted inconsistently between
tiles**
*Symptom:* A portfolio shows already-churned ARR as "at risk"; CSMs plan
interventions on customers that already left; and the portfolio health number
and the at-risk number disagree about whether churned accounts count.
*Root cause:* Churn is a terminal state, not a health state, but the account
list feeding the dashboard returns every account regardless of status. In the
origin system the fix was applied in ONE place (the at-risk/exposure tile) and
not another (the L4 health rollup), so churned accounts drag portfolio health
down while being correctly excluded from risk — an internal contradiction.
*Fix:* Partition churned out ONCE (piece 1) and feed only active accounts to
both the L4 rollup and the exposure tile; report churned as a separate
`churned_count`/`churned_arr`. Test that a churned account moves neither number.
Cited: the at-risk exclusion tombstone `executive_dashboard_api.py:1288-1294`
("Wave 1 Workstream A, Aug 4 2026: exclude churned accounts — this tile
previously double-counted already-churned ARR as at risk"); the drift is called
out in `AUDIT_REPORT_E2E_2026-08-03.md:91` ("CFO copy has no churned-account
exclusion"); the L4-still-includes-churned inconsistency is at
`customer_performance_summary_api.py:301` reading `_get_customer_accounts()`
which returns all statuses (`executive_dashboard_api.py:118-128`).

**2. Summing revenue from nodes or account ARR instead of the assessed bundle**
*Symptom:* Revenue-at-Risk on the dashboard doesn't match the number the MCP
tool or the Ask-AI assistant reports; the dashboard's figure is the naive sum of
at-risk accounts' ARR, which is both larger and differently defined.
*Root cause:* "Revenue at risk" is a provenance-aware, deduped,
confidence-thresholded aggregation over the causal graph — NOT the sum of ARR of
accounts below a health line. Recomputing it by summing accounts produces a
plausible, wrong number.
*Fix:* Call Module 04's `aggregate_revenue_with_provenance` and read
`revenue_at_risk` from the bundle; never sum node or account ARR into it. Cited:
`ask_ai_endpoint.py:284-290` ("CRITICAL REVENUE CONSISTENCY: Revenue-at-Risk is
the context-graph assessed number … NOT the summed ARR of critical/at-risk
accounts"); the aggregator at `utils/context_graph.py:575`.

**3. The same metric implemented per surface drifts (UI vs MCP vs Ask AI)**
*Symptom:* The React dashboard, the MCP tool, and the in-app assistant give three
different dollar answers for the same tenant and metric; a demo where the screen
and the assistant disagree in front of the buyer.
*Root cause:* Each surface reimplemented the metric's assembly. The origin
audit found "4-5 account-health read paths over 2 parallel score stores … 2
drifted NRR waterfall implementations (different dollar answers UI vs Claude.ai)."
*Fix:* One compile function per metric; the Flask route and the MCP tool both
call it. In the origin system the MCP wrapper invokes the SAME Flask handler in a
`test_request_context` rather than duplicating logic. Guard with
`assert_surface_parity`. Cited: `utils/executive_dashboard_mcp.py:32-58`
(one handler, two surfaces); `AUDIT_REPORT_E2E_2026-08-03.md:14,134`.

**4. Using a real score value (`50.0`) as the "no data" sentinel**
*Symptom:* An account that genuinely scores 50 is treated as having no data (or
vice versa), and the "missing" default differs by surface — `50.0` on one, `0`
on another, a computed value on a third — so the same account reads three ways.
*Root cause:* Overloading an in-range score as a missing-data marker. `50` is a
legal health score (the at-risk boundary), so `health == 50.0` cannot also mean
"absent" without collision.
*Fix:* Represent no-data as `None` end to end; exclude `None` from the rollup and
count it (`n_no_data`); let a real `50.0` be a scored value. Test the
`None`-missing and `50.0`-real cases produce different rollups. Cited: audit
finding C-19, `AUDIT_REPORT_E2E_2026-08-03.md:45`, `kpi_api.py:151`
(`health_score == 50.0` used as a no-data sentinel).

**5. A metric computed independently for two personas drifts between them**
*Symptom:* CRO and CFO screens show different revenue-at-risk / protected /
expansion, even though they are by definition the same portfolio number.
*Root cause:* Each persona endpoint computed the bundle its own way.
*Fix:* Both personas read the identical `revenue_bundle`; `persona_lens`
recomputes nothing. Assert cross-persona equality with `assert_persona_parity`
and prove it bites via a mutation. Cited: the parity invariant is stated as a
hard rule in `docs/KT_dashboard_data_lineage_and_evals.md:218` ("If they differ,
it's a bug"); both personas route through `_revenue_bundle_from_context_graph()`
→ `aggregate_revenue_with_provenance` (`executive_dashboard_api.py:267`).

**6. Reading a JSON-metadata key as if it were a column crashes the endpoint**
*Symptom:* A whole persona dashboard 500s with `AttributeError` the moment it
tries to show a field like `assigned_csm`.
*Root cause:* Some per-account attributes (`assigned_csm`, `arr`) live inside the
`profile_metadata` JSON, not as ORM columns. `account.assigned_csm` raises;
`account.profile_metadata.get("assigned_csm")` works.
*Fix:* Read metadata fields through a null-safe accessor on the JSON dict, never
as an attribute. Cited: `executive_dashboard_api.py:721-727` and the fix commit
`b207b047f` ("fix(executive-api): read assigned_csm from profile_metadata, not
Account column (#28)"); PR #23 introduced the column mis-attribution that crashed
`/api/executive/cro-dashboard`.

**7. Filtering the leading (signal) layer by the trailing (KPI) layer throws
away the early warning**
*Symptom:* A rising churn signal on an account whose KPIs still look green never
surfaces, because the dashboard only shows signals for accounts already flagged
unhealthy — so the system only "warns" once it is already too late, defeating the
product's core claim.
*Root cause:* Treating signals as a detail of the health view rather than an
independent layer, and gating the signal query on a health threshold.
*Fix:* Build `leading` from the signal/graph data directly, unfiltered by L3
health; present the two layers side by side and the gap as competing NRR lenses,
not one minus the other. Test signal-set invariance to health. Cited: the origin
signal surfaces query SIGNAL nodes with no health gate
(`SignalTimelineView.tsx:241-259`, `executive_dashboard_api.py:277-343`); the
two-layer intent in `docs/KT_dashboard_data_lineage_and_evals.md:64-71`. (Note:
the only legitimate "narrative filter" in the origin —
`context_graph.py:642 get_account_graph_summary(include_narrative=False)` —
filters narrative-only OUTCOME nodes for count-parity between two tools; it does
NOT filter signals by health, and must not be repurposed to.)

**8. Zero-ARR accounts vanish from a revenue-weighted mean without a trace**
*Symptom:* An account is "in" the portfolio but contributes nothing to portfolio
health and appears in no total, so a real account silently has no effect and
nobody notices it was dropped.
*Root cause:* In a revenue-weighted average, a zero-ARR account has zero weight —
mathematically correct, but indistinguishable from "not there" unless counted.
And when EVERY account is zero-ARR, `total_revenue == 0` forces a fallback to a
simple mean, which is a different number with the same name.
*Fix:* Surface `n_zero_arr`, and label the method (`revenue_weighted` vs
`simple_unweighted`) so a reader knows which number they are looking at. Test the
zero-ARR-counted and all-zero-ARR-labeled cases. Cited:
`customer_performance_summary_api.py:301-306` (the `total_revenue > 0` branch and
its simple-mean fallback), and the origin exposing both `avg_health_score` and
`avg_health_score_simple` (`executive_dashboard_api.py:1011-1012`).

## Provenance

Origin files: `kpi-dashboard/backend/executive_dashboard_api.py` (CRO
`cro_dashboard()` `:658`, CFO `:1051`, CEO `:1661`; revenue-weighted L4 inline at
`:710,730`; churned-exclusion tombstone `:1288-1294`; `assigned_csm` fix
`:721-727`; two-layer split — confirmed vs exposure `:1000-1005`, NRR lenses
`:1024-1032`); `kpi-dashboard/backend/customer_performance_summary_api.py:301-306`
(the canonical L4 formula + simple-mean fallback), `:156-167` (L3 pillar-weighted);
`kpi-dashboard/backend/utils/score_calculator.py` (L1–L3);
`kpi-dashboard/backend/utils/context_graph.py:575`
(`aggregate_revenue_with_provenance`), `:642` (narrative filter, NOT a health
filter); `kpi-dashboard/backend/utils/executive_dashboard_mcp.py:32-58` (one
handler across Flask + MCP surfaces); `kpi-dashboard/backend/mcp_server/
cs_pulse_executive.py:20,43,61` (persona MCP tools);
`kpi-dashboard/backend/auth_middleware.py:232` (`get_current_customer_id`
tenant scoping); frontends `src/components/dashboard/{CRODashboard,CFODashboard,
VPCSDashboard,CEODashboard}.tsx` and `src/components/csm/CSMCockpit.tsx`;
`src/components/dashboard/SignalTimelineView.tsx` (leading-layer surface).
Best references: `docs/KT_dashboard_data_lineage_and_evals.md` (two-layer model
§0/§3/§7, parity invariant `:218`) and `AUDIT_REPORT_E2E_2026-08-03.md` (drift
findings, C-18/C-19). Commit provenance: `b207b047f` (`assigned_csm` fix #28),
`241473604` (account-health convergence, C-18/C-19).

Authored 2026-08-07 against HEAD `a0cc9210d`, and validated the same day (see
Validation Note).

## Validation Note

Validated 2026-08-07. A fresh agent, given ONLY this spec in isolation, built a
self-contained implementation (fake `Account`, fake Module 01/03/04/05 hooks, and
two reconstructed Module 07 `envelope()` variants) and wrote pytest tests that
execute the spec's literal pseudocode. Result: **17 passed (12 acceptance
criteria + 5 defect/guard proofs)**, and **two real defects** — each demonstrated
by a test that runs the spec-as-written and then the corrected version.

Encouragingly, the spec's hardest-fought invariants held up under proof — churned
exclusion moved neither `portfolio_health` nor `exposure_risk`; a zero-ARR active
account was counted (`n_zero_arr`) yet moved no weight; all-zero-ARR fell back to
a LABELED `simple_unweighted` mean; a real `50.0` stayed scored while `None` was
excluded and counted; the leading signal set was invariant to trailing health;
`revenue_at_risk` came only from the Module-04 bundle (no ARR summation path
existed); and both parity checks bit when a metric was recomputed. The two
defects were elsewhere:

- **Defect 1 — HIGH (shape a).** `build_dashboard` called `envelope(...,
  persona=persona, ...)`, but the `envelope()` signature the spec itself
  documents (Dependencies, Data Shapes, and the piece-5 note) — matching Module
  07's already-shipped `envelope(scope, payload, arr_basis=, arr_basis_value=)`
  — has no `persona` parameter. On the real contract, every persona dashboard
  raises `TypeError` and produces no payload at all — Gotcha 6's "whole dashboard
  crashes" reached through the envelope contract. The spec's two halves disagreed
  on whether `envelope` takes `persona`. *Fixed:* `persona` is now carried inside
  `payload` (surfacing at top level via `envelope`'s `{"scope": scope,
  **payload}`), the `persona=` kwarg is dropped, and the piece-5 note + the
  "Envelope + scope" AC were rewritten to bind against Module 07's real signature
  — no change to the shipped Module 07 required.
- **Defect 2 — MEDIUM (shape d).** `account_arr` used `if arr:` — falsy on an
  explicit `profile_metadata={"arr": 0}` — so it fell through to the `revenue`
  column and returned a non-zero ARR the metadata had explicitly set to zero.
  That account was then mis-weighted into the L4 mean and, crucially, NOT counted
  in `n_zero_arr` — reintroducing Gotcha 8's "zero-ARR account vanishes without a
  trace" through the accessor. *Fixed:* `if arr is not None:` (an explicit 0 now
  wins), comment reworded.

No shape-(c) missing deliverable (every Boundary "Owns" / Engine bullet maps to a
Build Prompt piece); a trivial `_revenue_bundle` vs `revenue_bundle` naming drift
was aligned. **Library-level note:** the recurring pattern held again — the loud,
well-defended risks (churned, zero-ARR weighting, None-vs-50.0, signal
independence) were all handled correctly, while the defects hid in a
cross-module contract mismatch and a truthiness edge on `0`. Shape (a) — a Build
Prompt line contradicting the spec's own stated contract — has now appeared in a
majority of modules; a call into a dependency (here `envelope`) is a standing
red flag to check the call against the documented signature.
