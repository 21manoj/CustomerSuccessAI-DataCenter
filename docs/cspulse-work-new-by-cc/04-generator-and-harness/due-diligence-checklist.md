# CS Pulse end-to-end due diligence

**Purpose:** walk one tenant from CSV generation to executive dashboard and back, and be able to say for **every number on every surface** where it came from.

**Not a smoke test.** A smoke test asks "did it run." This asks "why is that value what it is." Those find different things.

---

## The three rules

**1. Write the expected value BEFORE you look.**
Every check below has an `expect:` line. Fill in your prediction first, then run it, then record the actual. If you look first, you will rationalise whatever you see — that is how a fabricated 0.80 survived for months.

**2. Pick tracers and follow those exact IDs.**
Do not check aggregates. Before starting, choose and write down:

```
TRACER ACCOUNT   account_id = ________   (pick a mid-health one, not an extreme)
TRACER SIGNAL    signal_ref = ________   (pick one in the middle of its account's sequence)
TRACER KPI       kpi_code   = ________   at measured_at = ________
TRACER OUTCOME   outcome    = ________
```

At every stage, ask: *where is my tracer now, what row represents it, and what changed.*

**3. Every number gets a provenance verdict.**

```
MEASURED     computed from this tenant's data
DERIVED      computed from measured values — name the inputs
BENCHMARK    industry/platform constant, not this tenant
DEFAULT      config fallback
UNAVAILABLE  could not be computed
UNKNOWN      cannot determine  ← this is a finding, log it
```

Any number that lands on UNKNOWN goes in the surprise log.

---

## Stage 0 — Record the environment

Without this the run is not reproducible and the findings are not attributable.

- [ ] Git revision / branch: `________`
- [ ] Database: `________`  (fresh? or existing rows present?)
- [ ] Vertical under test: `________`
- [ ] Generator version + `world_id` + `seed`: `________`
- [ ] Which of the three known fixes are in this build? `get_vertical_config` ☐ `partner_portal` ☐ `get_kpi_catalog` ☐

---

## Stage 1 — Generate the CSVs

- [ ] Files emitted: `accounts.csv` · `kpi_measurements.csv` · `enhanced_qualitative_signals.csv` · `outcomes.csv` · `signal_edges.csv` (held back)
- [ ] `ground_truth.json` emitted · `run_manifest.json` emitted
- [ ] Row count per file — record all five: `________`

**Vertical correctness**
- [ ] Every `signal_type` in the signals CSV exists in **this vertical's** taxonomy overlay
  `expect:` 100% · `actual:` ____
- [ ] No signal type in the CSV belongs only to another vertical
  `expect:` 0 · `actual:` ____
- [ ] Every `kpi_code` in the measurements CSV exists in this vertical's catalog
  `expect:` 100% · `actual:` ____

**Locate your tracers in the raw files**
- [ ] TRACER ACCOUNT appears in `accounts.csv` — record its ARR and renewal_date
- [ ] TRACER SIGNAL appears with its date and type
- [ ] TRACER KPI value at the chosen date: `________`

---

## Stage 2 — Create the tenant

- [ ] `create_customer(vertical=...)` returns a customer_id: `________`
- [ ] DB: `customers` row exists, `vertical` column matches what you passed
- [ ] `data_origin` recorded as synthetic ☐ *(if the field exists yet)*

**The catalog check — this is the one that was broken**
- [ ] `get_kpi_catalog(<new_id>)` — record every pillar name returned
  `expect:` this vertical's names from `list_verticals` · `actual:` ____
- [ ] `total_pillars` matches the vertical's actual count `expect:` ____ `actual:` ____
- [ ] `total_kpis` matches `list_verticals`' `kpi_count` `expect:` ____ `actual:` ____
- [ ] `default_pillar_weights_l2` has the **same number of entries** as `customer_pillar_weights_l2`
  `expect:` equal · `actual:` ____
- [ ] Every pillar code in `tier_enabled_kpis` has a definition in `pillars{}`
  `expect:` yes · `actual:` ____  *(P6 had weight 0.05 and 3 KPIs with no definition)*
- [ ] `get_vertical_config(<vertical>)` returns without exception `expect:` yes · `actual:` ____

**STOP if any of the above fails.** Everything downstream inherits it.

---

## Stage 3 — Upload the CSVs

- [ ] Dry run first (`dry_run=True`) — record any validation errors
- [ ] Real upload

**Row-for-row reconciliation** — record CSV count vs DB count for each:

| table | CSV rows | DB rows | delta | delta explained? |
|---|---|---|---|---|
| accounts | | | | |
| kpi_measurements | | | | |
| qualitative_signals | | | | |
| outcomes | | | | |

- [ ] Any non-zero delta has a stated reason. "Probably dedup" is not a reason.
- [ ] `source_platform` populated on every ingested row `expect:` 100% · `actual:` ____
- [ ] TRACER SIGNAL is findable in `qualitative_signals` by its `signal_ref`

---

## Stage 4 — `process_data()`

Run it once. Then walk the sub-stages in order. **Record `context_nodes` and `context_edges` counts before and after each.**

### 4a · Health scoring

- [ ] Which weights were used — bootstrap or `customer_config`? `________`
- [ ] Number of pillars scored `expect:` vertical's count · `actual:` ____
  *(if the vertical has 6 and only 5 are scored, health is computed on partial weight)*
- [ ] **Hand-compute one pillar for TRACER ACCOUNT.** Take its KPI values, apply L1 weights, apply the L2 weight. Does it match?
  `computed by hand:` ____ `system:` ____ `match?` ____
- [ ] Do the L2 weights sum to 1.0? `actual:` ____
- [ ] TRACER ACCOUNT health score: `________` — and you can explain it

### 4b · Nodes created

- [ ] SIGNAL nodes = signals uploaded? `expect:` equal · `actual:` ____
- [ ] OUTCOME nodes = outcomes uploaded? `expect:` equal · `actual:` ____
- [ ] Any node with NULL `source_platform`? `expect:` 0 · `actual:` ____
- [ ] Any node with NULL `evidence_tier` / `source`? `expect:` 0 · `actual:` ____

**The laundering check**
- [ ] What is `source` on `csv_import` nodes? `actual:` ____
  *A customer upload is an assertion, not an observation. If it says `observed`, log it.*
- [ ] Any tier-1 OUTCOME node with empty `properties.evidence`? `expect:` 0 · `actual:` ____
  *Record the summed `revenue_impact` of any that exist — that is revenue presented as evidence-backed on no evidence.*
- [ ] Find TRACER SIGNAL's node. Record: `node_id`, `source`, `tier`, `confidence`, `source_platform`

### 4c · Wizard A

- [ ] Arc assigned to TRACER ACCOUNT: `________`
- [ ] Which classifier produced it — rule cascade, or trajectory shape? `________`
- [ ] Do the two classifiers agree, and do they even share a vocabulary? `actual:` ____
- [ ] `arc_detection` node's `arc_type` vs the arc on the generated **edges** — same? `expect:` yes · `actual:` ____
- [ ] Edges created: `________`
- [ ] Any edge with NULL `source_platform`? `expect:` 0 · `actual:` ____ *(line 362)*
- [ ] Any edge whose `confidence` is a template constant? `actual:` ____

**The narrative-fit check — do this by eye, it takes five minutes**
- [ ] For each wizard_a edge on TRACER ACCOUNT, print the label and the titles of both endpoint nodes.
  Does the label describe what those two nodes actually are? `pass:` ____ `fail:` ____
  *Record every failure verbatim. "Champion departure created engagement gap" on a GPU utilisation collapse is the shape to look for.*
- [ ] Evidence Density at this point `expect:` 0% (no uploaded edges) · `actual:` ____

### 4d · Wizard B

- [ ] Did it run? Account count vs the ≥5 threshold: `________`
- [ ] Patterns produced: `________`
- [ ] **Is a sample size recorded for each pattern?** `expect:` yes · `actual:` ____
  *A pattern at 100% on n=1 is not a pattern.*
- [ ] Any pattern with n < 5? `actual:` ____
- [ ] Where does B's output go — does anything consume it? `________`

### 4e · Signal Analyst / LLM enrichment

- [ ] Nodes created: ____ · Edges created: ____
- [ ] Do LLM-created edges carry `model_id`, `prompt_version`, `input_node_ids`, `inferred_at`?
  `expect:` yes · `actual:` ____
- [ ] Did I3′ clamps fire? How many, and on which `source_platform` values? `________`
- [ ] **Did I3′ fire on any `csv_import` node?** `actual:` ____
  *If it only ever fires on `llm_enrichment`, the largest hole is open.*
- [ ] Duplicate `(from, to, edge_type)` triples now present? `expect:` 0 · `actual:` ____

### 4f · Wizard C

- [ ] Weights before: `________` after: `________`
- [ ] Total drift: `________`
- [ ] Written to `customer_config`? `expect:` yes · `actual:` ____
- [ ] Are the discovered correlations distinguishable, or identical across pillars? `actual:` ____
  *Identical correlations mean the pillars are collinear and C is doing nothing.*
- [ ] Were health scores recomputed after the weight change? `expect:` yes · `actual:` ____

### 4g · Wizard D

- [ ] `calibration_id` / `calibrated_at` written? `actual:` ____
- [ ] **Per-account NRR forecast: how many succeed, how many fail?** `expect:` all succeed · `actual:` ____
  *12/12 failed on customer 390. If any fail, get the specific missing input before continuing.*
- [ ] Portfolio NRR returned, or null? `actual:` ____
- [ ] TRACER ACCOUNT's forecast + its top drivers: `________`
- [ ] Are the drivers labelled as statistical attribution, or as causes? `actual:` ____

### 4h · ROI engine

- [ ] What did it compute, and from what inputs? `________`
- [ ] Does `arc_confidence` reach any ROI/NRR/forecast path? `expect:` no · `actual:` ____
  **STOP and escalate if yes.**

---

## Stage 5 — Executive dashboards

Run CEO, CFO and CRO. For each, work the same four checks.

### The vertical check
- [ ] Every pillar name shown matches this vertical `expect:` yes · `actual:` ____
- [ ] Number of pillars shown matches the vertical's count `actual:` ____
  *(the CFO `pillar_investments` block silently dropped P6)*

### The consistency check
- [ ] **Count every distinct NRR value across all three dashboards.** `expect:` 1 · `actual:` ____
  List them and their sources: `________`
- [ ] **Count every distinct ROI value.** `expect:` 1 · `actual:` ____
  *(390 produced 0%, 427%, 6.7×, 138.6× in one payload)*
- [ ] Do "revenue at risk" figures agree across dashboards? `actual:` ____

### The constant-detector
- [ ] Pick any per-account metric. Divide it by that account's ARR. Repeat for three accounts.
  `ratios:` ____ / ____ / ____
  **Identical ratios mean the metric is a fixed ARR multiple, not an analysis.**
- [ ] Is any per-account figure identical across all accounts regardless of health? `actual:` ____
- [ ] Does any Power-of-1 baseline differ from the tenant's measured value? `actual:` ____

### The double-count check
- [ ] Does any total sum multiple Power-of-1 metrics? `actual:` ____
- [ ] Do those metrics share playbooks? Check `get_playbook_economics` for a playbook appearing under two metric_ids. `actual:` ____

### Provenance sweep
- [ ] Take the **ten most prominent numbers** across the three dashboards. Assign each a verdict.

| # | field | value | verdict | basis |
|---|---|---|---|---|
| 1 | | | | |
| 2 | | | | |
| … | | | | |

- [ ] How many landed on UNKNOWN? `actual:` ____ — each one is a finding.

---

## Stage 6 — Partner portal

- [ ] Does this vertical have a partner pillar? `actual:` ____
- [ ] **If no:** does the portal refuse to serve? `expect:` refuse · `actual:` ____
  *If it serves, record which pillar's data it returned and cross-check the values against `list_accounts` pillar_scores. Matching values under partner labels = confirmed exposure.*
- [ ] **If yes:** do the KPI names shown match this vertical's actual P-whatever KPI names? `actual:` ____
- [ ] Any revenue or ARR present in the response? `expect:` none · `actual:` ____
- [ ] Does `action=impact` accept metric_ids that don't exist in this vertical? `actual:` ____

---

## Stage 7 — Create intervention data

- [ ] `get_playbook_recommendations` for TRACER ACCOUNT: `________`
- [ ] `execute_playbook` → record `execution_id`: `________`

**What appeared in the DB?**
- [ ] Execution row created ☐ · OUTCOME node created ☐ · Edges created ☐ (how many: ____)
- [ ] `source_platform` on each new row: `________`
- [ ] `evidence_tier` on each new edge: `________`
  *A `TRIGGERED` edge from a logged execution should be `observed`. An edge to a revenue outcome is an attribution — `inferred`.*

- [ ] `close_playbook` with an outcome
- [ ] `revenue_protected` — was it supplied, or auto-computed? `________`
- [ ] If auto-computed: from what? Record the churn-probability delta and the ARR used. Can you reproduce the number by hand? `actual:` ____
- [ ] Full intervention cost recorded, or CSM labour only? `actual:` ____

**Effect on the dashboards**
- [ ] Re-run the CFO dashboard. Which numbers moved? `________`
- [ ] Did `realized_roi` move? `expect:` yes · `actual:` ____
  *(390 showed 8 executions, $331k spent, realized_roi 0)*
- [ ] Is the movement proportional to what you did? `actual:` ____

---

## Stage 8 — Hot load

- [ ] Upload `signal_edges.csv`
- [ ] Edges added: ____
- [ ] **Duplicate `(from, to, edge_type)` triples created?** `expect:` 0 · `actual:` ____
- [ ] Did any template edge get `superseded_by` set? `expect:` yes for colliding pairs · `actual:` ____
- [ ] Evidence Density before: ____ after: ____ — is the change explained by retirement or only by dilution?
- [ ] Does `get_causal_chain` return any node twice? `expect:` no · `actual:` ____

---

## Stage 9 — Full recheck

Re-run every Stage 5 check.

- [ ] Anything change that should not have? `________`
- [ ] Anything stay the same that should have moved? `________`
- [ ] Re-run the Stage 2 catalog check — still correct after a full pipeline pass? `actual:` ____

---

## Stage 10 — Score against ground truth

Only if the tenant came from `synthetic_worldgen_v1`.

- [ ] Structure: adjacency precision / recall vs `true_dag`: ____ / ____
- [ ] Confounded pairs: did PC assert a direct cause? did FCI mark it? `________`
- [ ] Coverage: system's estimate vs true `observation_rate`: ____ vs ____
- [ ] Abstention: did accounts in `with_no_arc` receive no arc? `expect:` yes · `actual:` ____
- [ ] Template classification vs `template_disagreements`: ____

---

## Surprise log

**The most valuable artifact of this exercise.** Anything you did not predict — a field you couldn't explain, a count that didn't reconcile, a value that appeared from nowhere.

| # | stage | what surprised you | expected | actual | followed up? |
|---|---|---|---|---|---|
| 1 | | | | | |
| 2 | | | | | |

Every finding in this session's audit started as an entry that would have gone here.

---

## Stop conditions

Halt the run and escalate rather than working around:

1. `get_kpi_catalog` returns another vertical's pillars — everything downstream is invalid
2. `arc_confidence` reaches any ROI/NRR/forecast path
3. The partner portal serves a vertical with no partner pillar
4. Health scores computed on a partial pillar set
5. Any row count delta you cannot explain

---

## What "passed" means

Not "nothing broke." It means:

- Every number on every dashboard has a verdict, and none is UNKNOWN
- You hand-computed at least one health score and it matched
- You can name the source of every context edge
- CSV row counts reconcile to DB row counts, exactly, with any delta explained
- The surprise log is empty on a **second** run through

The second-run condition matters. First runs always surprise. A clean second pass means you actually understand the system rather than having explained away the first one.
