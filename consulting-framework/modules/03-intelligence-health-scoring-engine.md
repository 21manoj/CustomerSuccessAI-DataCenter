# 03 — Health Scoring Engine

**Layer:** Intelligence

**Status:** ✅ Validated pilot — see [Validation Note](#validation-note) at the bottom.

## Purpose

Turn raw per-KPI measurements into a single, trustworthy 0–100 health number per
account, with a transparent breakdown of what drove it. This is the trailing
("what already happened") half of the platform's two-layer health model — every
dashboard, every prediction wizard, and every "is this account okay" answer an
agent gives ultimately reads from this module. If two surfaces of the product ever
disagree about an account's health score, this module is where that got broken.

## Boundary

**Owns:**
- L1 rollup: KPI values → pillar score (weighted average, config-driven).
- L2 rollup: pillar scores → overall account health score (weighted average,
  config-driven).
- The canonical read path — one function every other module calls, never a
  bespoke query against the scores table.
- Weight resolution order (per-customer override → code default) and explicit
  logging of which source won.
- Health status classification (healthy/at-risk/critical) against centralized
  thresholds.
- Missing-data semantics: an account with no scored data returns an explicit
  "missing" result, never a fabricated number.

**Explicitly does not own:**
- Parsing/ingesting raw KPI CSVs or API payloads into per-KPI rows — that's
  Module 09 (Ingestion Pipeline). This module assumes clean, already-stored KPI
  rows exist.
- Defining *which* KPIs exist, their pillars, weights, or healthy/risk/critical
  ranges — that's Module 02 (Vertical & KPI Taxonomy Config). This module only
  consumes that config; it never hardcodes a KPI list.
- L4 rollup (account → customer, revenue-weighted across accounts) — that's a
  read-time aggregation owned by Module 08 (Dashboards), built on top of this
  module's per-account output.
- Causal reasoning about *why* a score moved — that's Module 04 (Context Graph)
  and Module 05 (Wizards).

## Dependencies

- **Module 01 (Data Model):** needs `Account`, `Customer`, `HealthScore`,
  `PillarScore`, `CustomerConfig` tables to exist, with `HealthScore` /
  `PillarScore` both keyed on `(account_id, measurement_month)` — the
  month-pinning is load-bearing (see Gotcha 3).
- **Module 02 (Vertical Taxonomy Config):** needs a KPI catalog exposing, per
  KPI: `pillar`, `weight_l1` (weight within its pillar), `higher_is_better`, and
  `ranges.healthy` / `ranges.risk` / `ranges.critical` bands; and per pillar:
  `weight_l2` (weight within the overall score). The engine treats this catalog
  as opaque config — it must never special-case a KPI code or pillar name in
  engine logic.

### Data Shapes

The engine only needs these fields — pseudocode, not the real schema (an FDE
without direct database access should still be able to implement against this):

```
Account:      account_id, customer_id
HealthScore:  account_id, measurement_month (date, first-of-month, comparable
              and sortable), health_score (0-100), health_status,
              contributing_pillars (dict: pillar_code -> score)
PillarScore:  account_id, measurement_month, pillar_code, pillar_score  (used
              only if contributing_pillars isn't stored inline on HealthScore)
CustomerConfig: customer_id, vertical, pillar_weight_overrides (dict or null)
```

"Latest" health score for an account = max `measurement_month`; if two rows
somehow share a month, prefer the one with the later write timestamp.
`measurement_month` values must be directly comparable (e.g. `date` objects or
zero-padded `"YYYY-MM"` strings) — do not use a format that sorts incorrectly
(`"2026-9"` before `"2026-10"` as strings, for example).

## Engine vs. Config

**Engine (build once):**
- `calculate_pillar_score(pillar, kpi_values)` — weighted-average rollup, KPI
  values normalized against their healthy range before weighting.
- `calculate_overall_health(pillar_scores)` — weighted-average of pillar scores
  using L2 weights.
- `get_kpi_status(kpi_code, value)` — classifies a *single* KPI value as
  healthy/risk/critical against its own `ranges` bands. This is the only engine
  function that reads the `risk`/`critical` ranges — the pillar rollup above
  only ever reads `ranges.healthy` for normalization. Keep this distinction
  explicit: it's easy to assume `risk`/`critical` feed the rollup math when
  they don't.
- `get_account_health(account_id, customer_id=None)` — canonical single-account
  read: tenant-checked when `customer_id` given, returns a dataclass (never a
  tuple), pillars pinned to the same `measurement_month` as the overall score.
- Weight resolution: per-customer override (DB) → code bootstrap default, with
  the source always logged.
- Threshold classification against a single config file, never inline numeric
  literals.
- The "immutable scores" write contract: an (account, month) that already has a
  `HealthScore` row is never silently recalculated on a normal reprocessing run
  — only an explicit `full_recalc` mode rewrites history.

**Config (an FDE fills in per client):**
- The KPI catalog JSON (Module 02's output): which KPIs, their pillars, L1/L2
  weights, and healthy/risk/critical ranges.
- `health_thresholds.json`: the healthy/at-risk/critical score cut points (this
  system uses 70 / 50, but that's a client decision, not an engine constant).
- Optional per-customer weight overrides, stored in `CustomerConfig`, letting one
  client's Pillar 3 matter more than another's without touching engine code.

## Build Prompt

> Build a health-scoring engine module for `{VERTICAL_NAME}` with the following
> contract. Do not invent KPI-specific logic in this module — every KPI-specific
> detail (which KPIs exist, their weights, their healthy ranges) must come from a
> single JSON config file you load at import time, structured as:
> `{"pillars": {"P1": {"weight_l2": 0.15, ...}, ...}, "kpis": {"KPI-CODE":
> {"pillar": "P1", "weight_l1": 0.3, "higher_is_better": true, "ranges":
> {"healthy": {"min": X, "max": Y}, "risk": {...}, "critical": {...}}}, ...}}`.
>
> Implement three layers:
>
> 1. **Rollup math** — pseudocode, not just prose, because the normalization
>    formula and its edge cases are exactly where implementations silently
>    diverge:
>    ```
>    def normalize(kpi_def, value):
>        h = kpi_def.ranges.healthy
>        if kpi_def.higher_is_better:
>            if h.max <= 0: return 0
>            return clamp(100 * value / h.max, 0, 100)
>        else:
>            if value <= 0: return 100   # zero/negative = best possible for lower-is-better
>            if h.min <= 0: return 0
>            return clamp(100 * h.min / value, 0, 100)
>
>    def calculate_pillar_score(pillar, kpi_values: dict) -> float:
>        # Only KPIs present in kpi_values contribute. Renormalize over the
>        # weight actually present — do NOT zero-fill absent KPIs into the
>        # average (that silently penalizes accounts with partial data instead
>        # of just working with what's there).
>        present = [(kpi, normalize(kpi_def, v)) for kpi, v in kpi_values.items()
>                   if kpi_def.pillar == pillar]
>        if not present: return 0
>        total_weight = sum(kpi_def.weight_l1 for kpi, _ in present)
>        if total_weight == 0: return 0
>        return sum(score * kpi_def.weight_l1 for kpi, score in present) / total_weight
>
>    def calculate_overall_health(pillar_scores: dict) -> float:
>        # Same renormalize-over-present-weight rule at the pillar level.
>        if not pillar_scores: return 0
>        total_weight = sum(pillar_weight_l2(p) for p in pillar_scores)
>        if total_weight == 0: return 0
>        return sum(score * pillar_weight_l2(p) for p, score in pillar_scores.items()) / total_weight
>    ```
>    `ranges.risk` / `ranges.critical` are NOT read by this rollup math — they
>    belong to `get_kpi_status()` (single-KPI classification), a separate
>    function. Don't conflate the two.
>
> 2. **Canonical read service** — a single function
>    `get_account_health(account_id, customer_id=None) -> AccountHealth` where
>    `AccountHealth` is a dataclass (NOT a tuple — tuples create an arity fork
>    the moment two callers need slightly different data) with fields:
>    `account_id`, `health_score: float | None`, `health_status: str | None`,
>    `measurement_month`, `pillars: dict`, `missing: bool`, `missing_reason:
>    str | None`. When `customer_id` is passed, verify the account actually
>    belongs to that customer before returning anything — return
>    `missing=True, missing_reason="not_found_or_wrong_tenant"` otherwise. When
>    there's no scored data at all, return `missing=True,
>    missing_reason="no_health_scores"` — **never** default `health_score` to a
>    sentinel value like 50 or 0. The `pillars` dict must come from the SAME
>    `measurement_month` as the overall score row — do not independently query
>    "latest pillar row per pillar," which can silently mix months.
>
> 3. **Weight resolution** — a function that, given a `customer_id`, returns
>    active L2 pillar weights: check for a per-customer override in the DB
>    config table first; if present and non-empty, use it — full stop. If
>    absent or empty, fall back to the code-level bootstrap weights from the
>    config JSON. **Do not gate the override check on a vertical-name match**
>    (e.g. "only apply the override if `customer.vertical == 'this-module's-
>    vertical'`) — that check is the exact anti-pattern in Gotcha 4 below and
>    silently drops every override for any client onboarded on a vertical this
>    module wasn't originally written against, with no error anywhere. Gate
>    only on "does a non-empty override exist for this customer," nothing else.
>    Log at INFO level which source was used and why — this log line is what
>    makes weight-related score discrepancies debuggable later.
>
> Write scores idempotently: an `(account_id, measurement_month)` pair that
> already has a stored score is skipped on normal reprocessing runs — detect
> new data to score by finding KPI rows whose `(account_id, month)` isn't
> already in the scored set (a set-difference over what's already written vs.
> what KPI data exists, not a timestamp comparison — this makes idempotency a
> property of this module alone, not dependent on Module 09's freshness
> detection). Only an explicit "full recalc" mode is allowed to overwrite
> existing rows, and it is scoped to whatever `(account, month)` pairs the
> caller passes in for that run — it is never an implicit "recalculate
> everything for this customer" unless the caller explicitly asks for that
> scope.
>
> Note: Module 09 (Ingestion Pipeline) is separately responsible for deciding
> *whether new data exists to load at all* before this module ever sees it —
> if that upstream freshness check is itself broken (see Gotcha 5, which is a
> Module 09 bug, not a Module 03 one), this module's own idempotency logic
> above is never even reached. Don't assume this module's correctness
> guarantees Module 09's.
>
> Centralize the healthy/at-risk/critical cut points in one config file loaded
> once; every classification call goes through it. Do not hardcode threshold
> numbers anywhere else in this module or its callers.

## Acceptance Criteria

- Given a KPI catalog with pillars whose `weight_l2` values sum to 1.0, and an
  account with values for every KPI where at least two pillars score
  *differently*, `calculate_overall_health` returns a value within
  `[min(pillar_scores), max(pillar_scores)]` inclusive — a weighted average of
  a single pillar, or of pillars that all score identically, legitimately
  equals that value rather than falling strictly inside a range, so don't test
  for strict inequality.
- Given `kpi_values` missing an entire pillar's KPIs, `calculate_pillar_score`
  for that pillar returns `0`, not an exception, not `None`. Given a pillar
  with *some but not all* of its KPIs present, the pillar score is the
  `weight_l1`-weighted average renormalized over the weight actually present
  (see Build Prompt pseudocode) — it must NOT zero-fill the missing KPIs into
  the average, which would silently penalize accounts with partial data.
- `get_account_health(account_id, customer_id=X)` for an account that exists but
  belongs to customer `Y != X` returns `missing=True,
  missing_reason="not_found_or_wrong_tenant"` — never that account's real score.
- `get_account_health` for an account with zero `HealthScore` rows returns
  `missing=True, missing_reason="no_health_scores"` — the caller must be able to
  distinguish "no data" from "score is literally zero."
- `AccountHealth.pillars` for a given call always share `measurement_month` with
  `AccountHealth.health_score` — assert this holds even when a newer pillar
  row exists for a *different, later* month than the account's current overall
  score (the newer pillar row must NOT leak into the older overall score's
  breakdown; it becomes visible only once that later month has its own
  overall score computed and becomes "latest").
- **Idempotency** (this module's own contract, independent of Module 09):
  given a fixed set of already-scored `(account, month)` pairs and a KPI
  dataset with no rows outside that set, running the scoring step writes zero
  new `HealthScore` rows. Given the same starting state plus KPI rows for a
  `(account, month)` pair NOT yet in the scored set — regardless of whether
  that month is chronologically later or same-day — running the scoring step
  writes exactly one new row per new pair, in that same run. Test this via the
  KPI-row-set-difference mechanism directly; do not route this test through a
  file-timestamp check, which is Module 09's concern (Gotcha 5).
- Weight resolution logs its source (customer-override vs. bootstrap-default)
  every time it's called with a customer_id, at a level visible in normal
  operational logs.

## Reference Test Harness

The origin system verifies this module two ways — replicate both:

1. **Unit-level rollup math** — a test file asserting the pillar/overall rollup
   functions against hand-computed expected values for a few representative
   `kpi_values` inputs (including all-missing and all-healthy edge cases).
2. **Cross-surface parity, on real data** — after any load or reload, read the
   same account's health through every surface that exposes it (direct service
   call, any API/tool wrapper, any agent-facing fallback) and assert they all
   return the identical number. This catches drift bugs (multiple independently
   -written copies of the same read logic silently diverging) that unit tests on
   the canonical function alone cannot catch — the bug is never in the canonical
   function, it's in a surface that stopped calling it.

A good smoke test for the whole module: run a synthetic multi-phase dataset
(baseline period, then an "intervention" period with materially different KPI
values for the same accounts) through the pipeline twice, and confirm the
health score actually changes between phases. A pipeline that reports success
but leaves scores frozen at baseline values has silently broken — this can be
a bug in this module's own idempotency logic (wrongly treating the new month
as already-scored) or in Module 09's upstream freshness check never handing
this module the new data at all (Gotcha 5). Test both modules' contribution to
this failure mode separately — don't let a passing end-to-end smoke test stand
in for verifying each module's contract in isolation.

## Known Gotchas

**1. Missing-data sentinel anti-pattern**
*Symptom:* Different parts of the product show different numbers for an account
with no data — 50.0 in one place, 0 in another, blank in a third.
*Root cause:* Multiple independent read paths each invented their own "no data"
default instead of an explicit missing-data signal. 50.0 is especially dangerous
because it silently lands exactly on a healthy/at-risk boundary and gets treated
as real, middling health.
*Fix:* Missing data must be a distinct field (`missing: bool` +
`missing_reason`), never a numeric default. Every caller must handle
`missing=True` explicitly rather than trusting the score field.

**2. Tuple return values create an arity fork**
*Symptom:* Adding a field to what the scoring read function returns breaks some
callers because they unpack a fixed-length tuple.
*Root cause:* Early copies of the read function returned `(score, status,
pillars)`; a later copy needed the measurement month too and returned a
4-tuple, forking behavior by call site.
*Fix:* Return a dataclass/object from day one. If you must support legacy tuple
callers during a migration, wrap the canonical function in a thin shim that
unpacks the dataclass — never let the tuple shape be the source of truth.

**3. Month-pinning: pillar breakdown must match the overall score's month**
*Symptom:* An account's pillar breakdown doesn't sum/weight to its displayed
overall score, and it's not obvious why.
*Root cause:* Fetching "the latest row per pillar" independently, rather than
"pillar rows for the same `measurement_month` as the overall score row," lets
pillars from different months get shown together if they were updated at
different times.
*Fix:* Always scope the pillar query to the overall score row's own
`measurement_month`.

**4. Weight-hierarchy vertical gate silently drops customer overrides for new
verticals**
*Symptom:* A customer configures custom pillar weights; they're silently
ignored, and generic bootstrap defaults are used instead — with no visible
error.
*Root cause:* The weight-resolution function's "does this customer have a
DB override" check was gated on `vertical == "<original-vertical-name>"`. Any
client onboarded on a newer vertical added later fails that gate and falls
through to bootstrap defaults, forever, even with a fully populated override
config in the DB.
*Fix:* When you add a new vertical, you MUST extend this gate (or better,
remove the vertical-name check entirely and gate only on "does a non-empty
override config exist for this customer"). Test every new vertical's weight
resolution explicitly — this bug produces no error, no exception, and no log
line unless you specifically check for the "FALLBACK: using code default"
message.

**5. Incremental reload silently no-ops off a non-UTC host** _(owned by Module
09 — Ingestion Pipeline, not this module; kept here as a cross-reference
because it determines whether this module ever sees fresh data)_
*Symptom:* A pipeline run reports success, but health scores for accounts don't
change even though genuinely new KPI data was uploaded (e.g. a second, later
phase of data for the same accounts). No error anywhere in the logs.
*Root cause:* The "is there new data to reprocess" check compared a data file's
on-disk modification time (converted to **local wall-clock time**) against a
database "last written" timestamp (stored in **UTC**). On any host whose local
timezone trails UTC — true for essentially every US timezone — same-day
comparisons evaluate "file is newer" as false, and the entire reload step is
skipped. A UTC-clocked host (most cloud containers) never exposes this, which
is exactly why it can hide for a long time and then break the moment someone
runs the same pipeline from a laptop.
*Fix:* Convert both sides of a timestamp comparison to the same clock (UTC)
before comparing — never mix `datetime.now()`/local `fromtimestamp()` against a
UTC-stored value.

**6. Hardcoded threshold literals scattered across the codebase**
*Symptom:* Changing the healthy/at-risk cutoff (e.g. from 70/50 to something
else) requires hunting down dozens of call sites, and some get missed, leaving
the product internally inconsistent about what "healthy" means.
*Root cause:* Threshold numbers were copy-pasted as inline literals instead of
read from one config source.
*Fix:* One threshold config file, loaded once, with a single classification
function every caller uses. Grep for the literal numbers periodically as a
regression check — new code has a way of reintroducing inline literals.

**7. Cross-tenant leakage in a history reader**
*Symptom:* An account's health history endpoint can, under the wrong caller,
return the wrong tenant's data for an `account_id` that isn't scoped correctly.
*Root cause:* A read path took `account_id` alone, with no `customer_id`
verification, on the (false) assumption that account IDs are only ever looked
up by a caller who already knows they belong to the right tenant.
*Fix:* Any read path that crosses a trust boundary (an API, an agent tool, an
export) MUST require and verify `customer_id` alongside `account_id`. Internal
service-to-service calls within an already-tenant-scoped request may skip this,
but document that assumption explicitly at the call site.

## Provenance

Origin: `kpi-dashboard/backend/utils/account_health.py`,
`kpi-dashboard/backend/verticals/dc2_s/kpi_definitions.py`,
`kpi-dashboard/backend/verticals/dc2_s/pillar_weights.py`,
`kpi-dashboard/backend/mcp_server/process_data_pipeline.py`
(`calculate_health_scores`), `kpi-dashboard/backend/utils/health_thresholds.py`.

Spec authored 2026-08-07, grounded directly against the above files at that
commit, plus the two real incidents this session that produced Gotchas 4–5
(the SaaS-Premium-vertical weight-fallback finding, and the UTC mtime
comparison bug found and fixed live, commit `b833d05d8`).

## Validation Note

Validated 2026-08-07: a fresh agent, given ONLY this spec (explicitly forbidden
from reading any origin-system file), built a working engine for an invented
vertical from scratch, with a 16-test suite covering every acceptance criterion,
all passing.

**What worked without any changes:** the missing-data semantics (Gotcha 1), the
dataclass-not-tuple requirement (Gotcha 2), and the month-pinning rule
(Gotcha 3) were all reproduced correctly from the spec alone — the agent called
out Gotcha 3 specifically as "the mental model that made [the acceptance
criterion] make sense as a product bug, not just a test to satisfy." That's the
target outcome for this whole exercise.

**What the validation run found broken, and what changed as a result:**

1. **The Build Prompt's weight-resolution wording directly contradicted
   Gotcha 4** — it told the agent to gate the override check on a
   vertical-name match, which is the exact anti-pattern the Gotcha exists to
   warn against. The agent caught the contradiction and resolved it correctly
   by following the Gotcha, but flagged — correctly — that this only worked
   because the agent happened to read both sections; an agent given the Build
   Prompt in isolation would have reproduced the original production bug
   verbatim. **Fixed**: rewrote the Build Prompt's weight-resolution step to
   state the correct behavior directly, and added a rule to
   `MODULE_TEMPLATE.md` that Known Gotchas must never be the only place a
   Build Prompt's own error gets corrected.
2. **Rollup math was prose, not pseudocode** — normalization formula, the
   zero/negative-value edge case for lower-is-better KPIs, and whether
   partial-pillar data zero-fills or renormalizes were all unspecified,
   forcing the agent to invent defensible-but-arbitrary answers. **Fixed**:
   Build Prompt now includes literal pseudocode with those edge cases pinned
   down.
3. **`ranges.risk`/`ranges.critical` were required in the config schema but
   never consumed anywhere in the original spec** — the agent correctly
   noticed dead config surface area. **Fixed**: added `get_kpi_status()` as an
   explicit third engine function (single-KPI classification, the actual
   consumer of those ranges) to both Boundary/Engine list and the Build
   Prompt, and clarified the pillar rollup only ever reads `ranges.healthy`.
4. **AC1 was unprovable as literally worded** ("strictly between") — a
   weighted average of one pillar, or of equal-scoring pillars, legitimately
   equals rather than strictly falls inside the range. **Fixed**: reworded to
   an inclusive-bounds criterion with the edge case named explicitly.
5. **No schema/data-shape reference** — without `models.py`, the agent had to
   guess the tenancy FK direction and `measurement_month`'s type/ordering
   semantics. **Fixed**: added a "Data Shapes" subsection under Dependencies
   with pseudocode field lists, per the agent's suggestion.
6. **Gotcha 5 was misfiled** — it's a bug in Module 09's data-freshness
   detection, not in this module's own (correctly-designed) idempotency
   mechanism, and this module's own Boundary section already disclaims
   ingestion. **Fixed**: marked Gotcha 5 explicitly as Module-09-owned, kept
   here only as a cross-reference, and split the smoke-test guidance so a
   frozen-scores failure gets root-caused to the right module instead of
   assumed to be this one.

**Template-level change:** `MODULE_TEMPLATE.md` needs an explicit rule (added
below) that a Build Prompt and its Gotchas section are a single unit — never
hand an agent one without the other, and any Gotcha that exists specifically to
correct the Build Prompt's own wording is a spec bug, not a valid gotcha, and
must be fixed in the prompt directly.
