# 02 — Vertical & KPI Taxonomy Config

**Layer:** Foundation

**Status:** ✅ Validated — see [Validation Note](#validation-note) at the bottom.

## Purpose

Let an FDE stand up a new client vertical — a completely different business
(logistics, healthcare, whatever the client is) with its own KPIs, pillars,
and weights — **by writing a config file, not code.** This is the module that
makes the difference between "we rebuild the scoring engine per client" and
"we reuse the scoring engine and reconfigure it per client," which is the
entire economic case for a reusable consulting framework. If this module is
weak, every other module's promise of being "config, not code" per client
falls apart, because they all read their KPI/pillar knowledge from here.

## Boundary

**Owns:**
- The KPI catalog file format: a JSON document declaring pillars (with L2
  weights) and KPIs (with pillar assignment, L1 weight, healthy/risk/critical
  ranges, direction).
- Vertical resolution: given a customer, determine which catalog applies, with
  a defined priority order (see Engine section) — this is the single place
  "which vertical is this client on" gets decided; no other module re-derives
  it independently.
- Catalog validation: weights sum correctly, pillar references resolve, KPI
  codes are well-formed — enforced BEFORE a catalog is usable, not discovered
  later as silently wrong scores.
- KPI tiers: named, curated subsets of a full catalog (e.g. a 9-KPI "fast
  onboarding" set vs. the full 40+), for clients who want to start small.

**Explicitly does not own:**
- The rollup math that consumes this catalog (pillar/overall score
  calculation) — that's Module 03. This module's job ends at "here is a
  validated catalog," not "here is a score."
- Outcome/signal *narrative* taxonomy — the causal-graph vocabulary for
  classifying qualitative events (their polarity, revenue-impact bucket) is a
  completely different config surface with its own base+overlay files,
  owned by Module 04 (Context Graph). Don't conflate "KPI taxonomy" with
  "causal-graph taxonomy" — they share the word "taxonomy" and nothing else.
- Any UI or write-API for a human to edit a customer's weight overrides —
  this module defines the validation rule such an API must call before
  persisting anything, but the API/UI itself belongs to Module 08
  (Dashboards) or an admin-console concern outside this library's 11 modules.

## Dependencies

- **Module 01 (Data Model):** needs `CustomerConfig.vertical` (which catalog
  a customer is on) and a JSON column for per-customer weight/KPI overrides.

### Data Shapes

```
KPI catalog file (config/{vertical}_kpi_catalog.json):
{
  "vertical": "logistics_v1",
  "version": "1.0",
  "pillars": {
    "P1": {"name": "...", "weight_l2": 0.25},
    ...  // weight_l2 across all pillars MUST sum to 1.0
  },
  "kpis": {
    "P1-KPI1": {
      "name": "...", "pillar": "P1", "weight_l1": 0.30,
      // weight_l1 across all KPIs WITHIN pillar P1 MUST sum to 1.0
      "higher_is_better": true,
      "ranges": {
        "healthy":  {"min": ..., "max": ...},
        "risk":     {"min": ..., "max": ...},
        "critical": {"min": ..., "max": ...}
      }
    },
    ...
  }
}

KPI tier file (config/{vertical}_kpi_tiers.json — OPTIONAL; a vertical with
no tier file is a fully valid catalog, it simply has no tiers defined):
{
  "default_tier": "starter",
  "tiers": {
    "starter": {"kpi_codes": ["P1-KPI1", "P3-KPI2", ...]},  // subset of the
    "full":    {"kpi_codes": [/* all KPI codes in the catalog */]}
    // a tier is ALWAYS a subset of an existing catalog's kpi codes —
    // it never introduces a KPI the base catalog doesn't already define.
  }
}

Legacy Python module (verticals/{vertical}/kpi_definitions.py — Tier 2 ONLY,
never used for a new vertical, kept solely for pre-existing verticals that
predate the JSON format):
  Must expose exactly two module-level attributes: `PILLARS: dict` and
  `KPIS: dict`, in the identical shape as the JSON catalog's `pillars` and
  `kpis` keys. A module missing either attribute, or whose import raises for
  any reason OTHER than the module/package genuinely not existing, is a
  BROKEN legacy module, not an absent one — see Build Prompt step 1's
  explicit handling of this distinction, which exists specifically because
  the naive way to check "does this module exist" (a bare try/import/except
  ImportError) cannot tell the two cases apart.
```

`load_catalog(vertical)` is responsible for the base catalog only — pillars
and KPIs. If a co-located tier file exists for that vertical, `load_catalog`
also validates it (the tier-subset rule below) as part of the same load call,
so an invalid tier file fails at the same load time as an invalid base
catalog, not later when a tier is first requested. `get_kpis_for_tier` never
performs validation itself — it only filters an already-validated catalog.

Every pillar declared in a catalog's `pillars` dict must have at least one
KPI assigned to it (checked as part of load-time validation, alongside the
weight-sum checks) — a pillar that contributes `weight_l2` to the overall
score but has zero KPIs feeding it is exactly the kind of catalog that looks
valid on inspection but silently produces a wrong score, which is the whole
failure class this module exists to prevent. Reject it at load time, the same
as a bad weight sum.

## Engine vs. Config

**Engine (build once):**
- Vertical resolution with a fixed priority order: (1) per-customer DB
  override (`CustomerConfig`'s override JSON — hot-reloadable, no restart),
  checked at the scoring layer, not here; (2) a JSON catalog file matching
  the customer's vertical name; (3) a legacy Python-module fallback, kept
  only for verticals that predate the JSON format — new verticals should
  never need this tier.
- Vertical auto-discovery: scanning the config directory for
  `*_kpi_catalog.json` files at startup, so a new vertical becomes available
  the moment its file is added — no code change, no registration step,
  no restart-and-hope.
- Catalog validation, run at load time (not just at customer-override-write
  time — see Gotcha 1): pillar `weight_l2` values sum to 1.0 (±0.001), each
  pillar's KPIs' `weight_l1` values sum to 1.0 (±0.001) among themselves, every
  KPI's `pillar` field references a pillar that actually exists in the same
  catalog, and every tier's `kpi_codes` are a subset of the base catalog's
  KPI codes.
- Tier resolution: given a vertical and a tier name (or the vertical's
  configured default), return the filtered KPI set — this is a pure filter
  over the validated base catalog, never a second source of KPI definitions.

**Config (an FDE fills in per client):**
- The catalog file itself: pillars, KPIs, weights, ranges — this is the vast
  majority of what changes per client engagement.
- Tier definitions, if the client wants a phased rollout.
- Which vertical a given customer is assigned to (`CustomerConfig.vertical`).

## Build Prompt

> Build a vertical/KPI taxonomy config module for a new client vertical
> `{VERTICAL_NAME}`. Implement:
>
> 1. **Catalog loader with a fixed 3-tier resolution order**, cached per
>    vertical after first load. Tier 2's existence check is the one place in
>    this whole module where it's easy to accidentally reproduce Gotcha 2
>    (silently conflating "doesn't exist" with "exists but broken") — read
>    the inline comments below, they're not decorative:
>    ```
>    def load_catalog(vertical: str) -> (pillars: dict, kpis: dict):
>        # Tier 1: JSON file at config/{vertical}_kpi_catalog.json
>        if file_exists(json_path):
>            pillars, kpis = validate_and_load(json_path)
>            if tier_file_exists(vertical):
>                validate_tier_file(vertical, kpis)  # same load call, same failure mode
>            return pillars, kpis
>
>        # Tier 2: legacy Python module — ONLY for verticals that predate the
>        # JSON format. Do NOT create new verticals this way.
>        try:
>            module = import_module(f"verticals.{vertical}.kpi_definitions")
>        except ModuleNotFoundError as e:
>            # This EXACT module (or a parent package of it) is what's
>            # missing => the legacy module genuinely doesn't exist => fall
>            # through to Tier 3 (raise "unknown vertical").
>            # Inspect e.name — if it does NOT match the target module or one
>            # of its ancestor packages, this is a DIFFERENT, real import
>            # failure happening INSIDE a module that does exist (e.g. that
>            # module imports some other broken dependency) — re-raise it
>            # loudly. Do not swallow it as "vertical not found."
>            if e.name is not the target module or an ancestor of it:
>                raise
>        else:
>            if not hasattr(module, 'PILLARS') or not hasattr(module, 'KPIS'):
>                raise ValueError(f"Legacy module for {vertical} exists but "
>                                  f"is missing PILLARS/KPIS — broken, not absent")
>            return validate_in_memory(module.PILLARS, module.KPIS)
>
>        raise ValueError(f"Unknown vertical: {vertical}")
>    ```
>    Vertical auto-discovery scans the config directory for
>    `*_kpi_catalog.json` at startup and adds each to the set of known
>    verticals — dropping a new file is sufficient to register a vertical,
>    no code change required.
>
> 2. **Validation that runs at catalog LOAD time, every time, not just when a
>    human edits weights through an admin UI.** This is the most important
>    rule in this prompt: a validator that only fires on the write path used
>    by an existing admin UI does nothing to protect the path an FDE actually
>    uses to onboard a brand-new vertical — dropping a raw JSON file straight
>    into the config directory, which never goes through that UI at all.
>    Wire validation into `load_catalog` itself:
>    - Every pillar referenced by any KPI's `pillar` field must exist in the
>      catalog's `pillars` dict.
>    - Every pillar declared in the catalog must have at least one KPI
>      assigned to it — a pillar with zero KPIs still contributes its
>      `weight_l2` to the overall score with nothing backing it, which is
>      exactly the "looks fine, silently wrong" failure this validation step
>      exists to catch.
>    - `sum(pillar.weight_l2 for pillar in pillars)` must be within 0.001 of
>      1.0.
>    - For each pillar, `sum(kpi.weight_l1 for kpi in that pillar's KPIs)`
>      must be within 0.001 of 1.0.
>    - Every tier's `kpi_codes` must be a subset of the base catalog's KPI
>      codes — reject a tier referencing a KPI code the catalog doesn't
>      define.
>    A catalog failing any of these must raise loudly at load time (refuse to
>    serve a customer on a broken catalog) — never load a partially-invalid
>    catalog and let it silently produce wrong scores downstream in Module 03.
>
> 3. **Tier resolution** as a pure filter: `get_kpis_for_tier(vertical, tier)`
>    returns only the KPI codes listed for that tier, still fully validated
>    (a tier is a view over the base catalog, not a separate one).
>
> Never hardcode a specific vertical's pillar count, KPI codes, or weight
> values anywhere in this module's own logic — if a test or example needs
> concrete numbers, they belong in a sample catalog file, not in the loader
> code itself.

## Acceptance Criteria

- Dropping a new, valid `{new_vertical}_kpi_catalog.json` file into the
  config directory (no code changes, no restart of any registration list)
  makes `load_catalog("{new_vertical}")` succeed and that vertical appear in
  the auto-discovered set — the module's own code contains zero references to
  the new vertical's name.
- A catalog file whose `weight_l2` values sum to 0.97 (not 1.0) fails to
  load, with an error identifying which check failed and by how much — it
  does NOT load successfully and silently produce scores that cap below 100
  even for a fully healthy account.
- A catalog file where a KPI's `pillar` field references a pillar not present
  in that file's `pillars` dict fails to load at THIS module's boundary —
  this module's own job is to never hand such a catalog to anything
  downstream; it does not need to reason about what Module 03's rollup math
  would do with it, only that it must never receive it.
- A catalog file where a declared pillar has zero KPIs assigned to it fails
  to load, with an error naming the empty pillar — same treatment as a bad
  weight sum.
- A tier definition listing a KPI code absent from the base catalog fails to
  load — a tier can never introduce KPI knowledge the base catalog doesn't
  already have.
- A legacy Tier-2 module that exists but is missing `PILLARS`/`KPIS`, or
  whose own internal import fails for a reason other than the target module
  itself being absent, raises an error naming the real problem — it must
  NEVER be reported as "unknown vertical." Prove this isn't just correct by
  inspection: construct a legacy module whose own import chain fails on an
  unrelated missing dependency, and assert `load_catalog` propagates that
  real error rather than swallowing it into a generic not-found.
- `get_kpis_for_tier(vertical, "starter")` returns a strict subset of
  `load_catalog(vertical)`'s KPIs, and every returned KPI's definition is
  byte-for-byte identical to its definition in the full catalog — a tier
  never redefines a KPI, only selects which ones are active.
- **(Module 02's own contract, testable entirely within this module)**
  Calling the loader for the SAME valid catalog twice returns equal results
  without re-reading the file from disk the second time — e.g. deleting the
  underlying file after the first successful load must NOT break the second
  call. (A separate, NOT-this-module's-contract note for whoever builds
  Module 03/the scoring layer: per-customer DB weight overrides must remain
  hot-reloadable without a process restart — but that requirement lives
  entirely outside this module's cache and is not testable from here; do not
  try to prove it as part of this module's test suite.)

## Reference Test Harness

1. **Validation-rejection tests** — one test per validation rule in the Build
   Prompt, each constructing a deliberately-broken catalog (bad weight sum,
   dangling pillar reference, tier referencing an unknown KPI) and asserting
   `load_catalog` raises rather than returns something usable.
2. **Round-trip test** — write a valid catalog file to a temp location, load
   it, assert every field survives intact (weights, ranges, direction flags)
   — catches silent coercion bugs (e.g. a weight read as a string instead of
   a float, which would pass a naive equality check against 1.0 in some
   languages but not others).
3. **Auto-discovery test** — write a new catalog file for an invented
   vertical name the test process has never seen before, and assert it
   appears in the discovered-verticals set without any prior registration.

## Known Gotchas

**1. A validator that's wired to one write path silently does nothing for
another**
*Symptom:* Broken weight configurations (not summing to 1.0, referencing
non-existent pillars) exist undetected in catalog files that were authored by
directly creating/editing a JSON file rather than through an existing admin
UI — the bug isn't caught until someone notices scores behaving strangely
(capping below 100, or a KPI that never seems to move its pillar score at
all).
*Root cause:* A weight-sum validator existed in the origin system, but it was
only called from the customer-override *write* API (an admin UI editing an
existing customer's weights through the database) — never from the
vertical-catalog-*file*-loading path, which is the path an FDE actually uses
to onboard a brand-new vertical by dropping a JSON file into the config
directory. The validator's existence gave false confidence that "weights are
validated" everywhere, when in fact the highest-risk path (a human typing
numbers into a new file from scratch, with no existing values to compare
against) had zero validation.
*Fix:* Validation must run inside the loader itself, on every load, for every
vertical, regardless of how the catalog file was authored. Never assume a
validator "already exists elsewhere in the codebase" covers a new path
without checking exactly where it's actually called from.

**2. Silent import failures degrade a whole feature to a warning with no
loud failure**
*Symptom:* An entire vertical's dedicated API/feature set is unavailable, and
the only evidence is a one-line warning buried in startup logs — e.g.
`"Warning: X API not available: cannot import name 'foo' from 'bar'"` — that
most operators never read, because the process still starts up and reports
healthy.
*Root cause:* A module import wrapped in a broad `try/except ImportError`
(often to keep an optional feature from crashing the whole app if its
dependency is missing) also silently swallows a genuine bug: importing a
function name that was renamed or never existed in the target module, not
just a genuinely-missing optional dependency. The two failure modes look
identical from outside the `except` block, but one is "this optional feature
is unavailable by design" and the other is "this code is broken and no one
noticed." Confirmed live in the origin system: a startup warning references
importing a function name that does not exist anywhere in the target module
— it has apparently never worked, for however long that code path has
existed, with zero loud failure.
*Fix:* Don't let "optional feature, missing dependency" and "broken import,
real bug" share the same catch block and the same log level. If an import
error's message names a specific function/class (an `ImportError`/
`AttributeError` on a known target module you control), treat that
differently — fail loudly in development/CI at minimum — from a bare
"this whole optional package isn't installed" `ModuleNotFoundError`.

**3. "Does this module exist" checks reproduce Gotcha 2 internally, not just
at import call sites**
*Symptom:* Same as Gotcha 2 — a broken legacy Tier-2 vertical module gets
silently reported as "unknown vertical" instead of the real underlying error,
even in code written specifically to be careful about imports.
*Root cause:* This is Gotcha 2's exact failure shape, but appearing INSIDE
this module's own "does a legacy fallback module exist for this vertical"
check, not just at some other caller's import site. `if module_exists(x):`
has essentially one natural implementation — `try: import x; except
ImportError: return False` — and that implementation cannot distinguish
"`x` itself doesn't exist" from "`x` exists but something IT imports doesn't,"
because both raise the same exception type from the same statement. This is
easy to miss precisely because the surrounding code is otherwise careful and
well-intentioned — the bug isn't sloppiness, it's that the naive
implementation of "does X exist" is intrinsically this fragile in Python.
*Fix:* Inspect the exception's own `name` attribute (Python's
`ModuleNotFoundError.name`) and only treat it as "doesn't exist" if the
missing name IS the module you were checking for (or one of its parent
packages) — any other missing name means something that module depends on is
broken, and that failure must propagate, never be silently reinterpreted as
"this vertical doesn't exist." Any time your code asks "does X exist" via a
try/except around an import, ask whether X's own internals could plausibly
import something else that's missing — if yes, this Gotcha applies.

## Provenance

Origin: `kpi-dashboard/backend/utils/vertical_registry.py` (3-tier resolution,
auto-discovery), `kpi-dashboard/backend/utils/generic_scorer.py`
(`load_catalog_from_json`), `kpi-dashboard/backend/utils/config_validator.py`
(`ConfigValidator.validate_pillar_weights`/`validate_kpi_weights` — confirmed
via grep to be called only from `dc2s_config_api.py` and
`utils/score_calculator.py`, never from the catalog-file loading path),
`kpi-dashboard/backend/config/dc2s_kpi_catalog.json` and
`config/saas_kpi_tiers.json` (real catalog/tier structure examples).

Gotcha 2 verified live during this session: the running local server's
startup log shows `⚠️ Warning: SaaS Premium API not available: cannot import
name 'get_catalog' from 'utils.vertical_registry'` — `vertical_registry.py`
has no function named `get_catalog` (only `get_catalog_for_customer`),
confirmed by reading the file directly.

## Validation Note

Validated 2026-08-07: a fresh agent, given only this spec, built a working
loader from scratch for an invented "boutique_hotel_v1" vertical, with 20
tests, all passing.

**This run found a subtler variant of the Module 01/03 failure pattern, worth
naming precisely because it's the more dangerous version:** in both prior
modules, the Build Prompt *textually* contradicted a stated rule elsewhere in
the document — an inspection pass could in principle have caught it by
reading both sections side by side. This time, Gotcha 1 (validator wired to
only one write path) WAS successfully folded directly into the Build Prompt
(no contradiction — confirmed redundant, which is the correct outcome).
But Gotcha 2 (silent import-failure conflation) reappeared anyway, not
because the Build Prompt contradicted it, but because the Build Prompt's Tier
2 pseudocode (`if module_exists(...): ...`) was **underspecified**, and the
one natural way to implement unspecified "does X exist" pseudocode in Python
— a bare `try/except ImportError` — happens to be exactly the anti-pattern
Gotcha 2 describes. No amount of re-reading the two sections side by side
would have caught this; it only surfaces once someone actually implements the
`...`. The agent proved it wasn't theoretical by building the naive version
first, watching it misreport a broken legacy module as "unknown vertical,"
and then fixing it.

**Generalized lesson for this library**: a Build Prompt containing an
ellipsis, a "your choice," or any unresolved pseudocode gap is not a
harmless simplification — it's exactly where a Gotcha can resurface
invisibly, because it was never actually checked against anything. Fully
specifying every code path in the Build Prompt (as this spec now does for
Tier 2) is not over-engineering; it's the only way the cross-check the
template asks for is actually possible to perform.

**What changed as a result:**

1. **Tier 2's contract was fully specified** — exact `PILLARS`/`KPIS`
   module-attribute shape, and explicit `ModuleNotFoundError.name`-based
   handling distinguishing "target module absent" (fall through to Tier 3)
   from "target module present but its own import chain is broken"
   (propagate loudly, never report as unknown vertical). Added as Gotcha 3,
   since it's a real, distinct failure shape from Gotcha 2 even though it's
   the same underlying anti-pattern — it happens inside this module's own
   code, not at an external caller's import site.
2. **`load_catalog`'s relationship to the (optional) tier file was
   underspecified** — fixed by making `load_catalog` responsible for
   discovering and validating a co-located tier file as part of the same
   load call, so a bad tier file fails at the same load time as a bad base
   catalog, and `get_kpis_for_tier` never performs validation itself.
3. **A pillar with zero assigned KPIs had no stated rule** despite being
   exactly the "looks fine, silently wrong" case this module exists to
   prevent. Added as an explicit load-time validation failure, in both the
   Build Prompt's rule list and Acceptance Criteria.
4. **The caching Acceptance Criterion bundled a Module-02 claim with a
   Module-03/scoring-layer claim** ("hot-reloadable DB overrides") that this
   module explicitly disclaims owning, making it partly untestable from
   inside this module alone. Split into a testable Module-02-only bullet plus
   an explicit note for whoever builds the scoring layer, rather than one
   bullet mixing both.
5. **The dangling-pillar AC's rationale clause described a Module 03 symptom**
   ("that KPI silently never contributing to any pillar score") rather than
   this module's own failure mode. Reworded to describe what THIS module
   guarantees (never handing such a catalog downstream at all) rather than
   reasoning about a different module's internals.

**Confirms, and sharpens, the pattern from Modules 01/03**: three-for-three
validated modules have now each surfaced a real Build-Prompt-level defect —
first as direct textual contradiction (01, 03), now as an underspecified gap
that resolves to the anti-pattern by construction (02). Both shapes need the
adversarial rebuild to catch; neither is reliably caught by author
re-reading alone.
