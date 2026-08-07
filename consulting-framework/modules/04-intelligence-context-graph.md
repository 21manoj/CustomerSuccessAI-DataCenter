# 04 — Context Graph & Causal Layer

**Layer:** Intelligence

**Status:** ✅ Validated — see [Validation Note](#validation-note) at the bottom.

## Purpose

Give an account's history a *shape*, not just a KPI trend line: a typed graph
of what happened (signals, stakeholder actions, decisions, revenue outcomes)
and how those events caused one another, with a $-impact attached to the
outcomes. This is what lets the product answer "why is this account at risk"
instead of only "this account is at risk" — the causal chain is the
explanation. Module 03 (Health Scoring) tells you the account moved from 70
to 40; this module tells you a champion left, which caused three tickets to
go unresolved, which caused a renewal-risk signal.

## Boundary

**Owns:**
- The graph schema: typed nodes (`SIGNAL`, `STAKEHOLDER`, `DECISION`,
  `OUTCOME`, `EXTERNAL_CONTEXT`, plus the account itself as an implicit root)
  and typed, weighted, temporal edges (`CAUSED_BY`, `INDICATES`, `LED_TO`,
  `CORRELATES_WITH`, `INVOLVES`, `BELONGS_TO`, `BENCHMARKED_BY`,
  `SOURCED_FROM`, `SUPERSEDES`) connecting them.
- The vocabulary taxonomy: which node/edge *subtypes* exist, which subtypes
  are polarity-ambiguous (their sentiment can't be inferred from the subtype
  alone), and which revenue bucket (`lost`/`expansion`/`pipeline`/`at_risk`/
  `protected`) an outcome subtype belongs to — as versioned, validated,
  per-vertical config (base + overlay), not hardcoded lists scattered through
  application code.
- Graph invariants: structural/logical rules the graph must never violate
  (e.g. "an OUTCOME can't cause another OUTCOME directly," "a causal edge
  can't point backwards in time"), checked as an explicit, nameable,
  independently-runnable rule set — not implicit assumptions baked into
  whatever code happens to write the graph.
- Tiered node lifecycle: every node has a storage tier (1=permanent,
  2=decaying, 3=ephemeral) and a decay/expiry model, so the graph doesn't
  grow unbounded with equal-weight ancient trivia forever.
- Arc classification: deriving a single labeled trajectory (e.g.
  `crisis_recovery`, `silent_churn`, `stalled_deployment`) for an account
  from graph-derived features — a compact narrative summary of the graph, not
  the graph itself.

**Explicitly does not own:**
- KPI-based health scoring — Module 03. This module can *reference* health
  score movement as one input to arc classification, but never recomputes or
  stores a health score itself.
- Deciding *when* new SIGNAL/OUTCOME nodes get created from raw uploaded data
  (CSV/API ingestion) — Module 09 (Ingestion Pipeline) parses the source data
  and writes nodes/edges through this module's schema; this module doesn't
  reach out and pull data in.
- Prediction/calibration state built ON TOP of arc classifications (e.g.
  learning which interventions worked for which arc) — Module 05 (Wizards).
  This module produces the arc label; Wizard C/D decide what to do with it.
- LLM-based enrichment (inferring a signal's real sentiment, auto-tagging an
  ambiguous subtype) — that's an Ops-layer concern (Module 09 or a future
  module), which calls into this module's taxonomy to know WHAT the valid
  subtypes/buckets are, but the LLM call itself lives outside this boundary.

## Dependencies

- **Module 01 (Data Model):** needs `Account`/`Customer` for tenant scoping —
  every node and edge carries `customer_id` for isolation (see Gotcha 2).

### Data Shapes

```
ContextNode: node_id (PK), customer_id (FK), account_id (FK), node_type
             (SIGNAL|STAKEHOLDER|DECISION|OUTCOME|EXTERNAL_CONTEXT),
             node_subtype (free-form string, VALIDATED AGAINST THE LOADED
             TAXONOMY AT WRITE TIME — not an enum column, so new subtypes are
             a config change, not a migration, but "not an enum column" does
             NOT mean unvalidated: see the write-time validation rule below),
             source ('customer'=uploaded data, 'system'=derived by this
             platform), tier (1|2|3), properties (JSON, shape varies by
             node_type), revenue_impact (nullable numeric),
             revenue_impact_type (nullable — populated for OUTCOME nodes,
             one of the taxonomy's revenue bucket names), confidence
             (0.0-1.0), occurred_at (required — WHEN the real-world event
             happened, not when it was recorded), created_at (WHEN the row
             was written to the database — server-assigned, never
             caller-supplied; exists precisely so Gotcha 1's distinction is
             checkable, not just conceptual), expires_at (nullable, NULL =
             never expires / tier 1)

ContextEdge: edge_id (PK), customer_id, from_node_id (FK), to_node_id (FK),
             edge_type (one of the 9 listed above), weight (0.0-1.0),
             confidence (0.0-1.0), revenue_impact (nullable — $ impact
             specifically attributable to this causal link, separate from
             either node's own revenue_impact), occurred_at, created_at
             (server-assigned, same reasoning as ContextNode's), properties
             JSON

CAUSAL_EDGE_TYPES = {"CAUSED_BY", "LED_TO"} — this is the fixed subset of the
9 edge types that invariants I1-I3 mean whenever they say "a causal edge."
The other 7 (INDICATES, CORRELATES_WITH, INVOLVES, BELONGS_TO,
BENCHMARKED_BY, SOURCED_FROM, SUPERSEDES) are evidentiary or structural, not
causal, and are OUT OF SCOPE for I1-I3 — an `INDICATES` edge between two
OUTCOME nodes, for example, does NOT trip I1, because it isn't asserting
causation. Do not extend this set without re-deriving which invariants should
now apply to the added type; do not narrow it either, without checking which
currently-caught violations would stop being caught.

Taxonomy files (config/taxonomy_base.json + config/taxonomy_{vertical}.json
overlays): {version, polarity_ambiguous_outcome_subtypes: [...],
polarity_ambiguous_signal_subtypes: [...], positive_signal_subtypes: [...],
negative_signal_subtypes: [...], revenue_buckets: {bucket_name: [subtype,
...]}, auto_recovery_outcome_subtypes: [...]}
```

**Where SIGNAL polarity comes from** (this is not optional background — I4
cannot be implemented without it): a SIGNAL subtype's polarity is looked up
in `positive_signal_subtypes` / `negative_signal_subtypes`, the SAME shape
and merge/validation treatment as `revenue_buckets` gives OUTCOME subtypes —
additive across base+overlay, and a subtype appearing in
`polarity_ambiguous_signal_subtypes` must NEVER also appear in either
definitive list (same contradiction class the overlay validator already
checks for revenue buckets — extend that same check to cover this pair too).
A SIGNAL subtype absent from all three lists (not ambiguous, not positive,
not negative) is a taxonomy gap — treat it the same as "pillar with zero
KPIs" in Module 02: reject the taxonomy at load time rather than let I4
silently skip a subtype nobody classified.

**Write-time subtype validation** (closes a real gap this module's own
invariant framework does not otherwise catch): before persisting any
`ContextNode`, verify its `node_subtype` is a member of the currently-loaded
taxonomy for that customer's vertical (for OUTCOME nodes: appears in some
`revenue_buckets` list, or is polarity-ambiguous; for SIGNAL nodes: appears
in `positive_signal_subtypes`, `negative_signal_subtypes`, or is
polarity-ambiguous). Reject the write otherwise. None of I1-I4 would ever
catch a node written with a made-up subtype — they operate on graph
structure, not vocabulary membership — so this check has to live at the
write boundary, not in the invariant suite.

`occurred_at` vs. `created_at` matters: a signal can be entered into the
system today describing something that happened two weeks ago (a backfilled
CSV, a delayed integration sync). Causal-ordering checks (Gotcha 1) MUST use
`occurred_at`, never `created_at` — using the wrong one is a silent,
undetectable-by-symptom bug until an invariant check catches it.

## Engine vs. Config

**Engine (build once):**
- The node/edge schema and its tenant-isolation contract (every node/edge
  carries `customer_id`, every query filters by it).
- The taxonomy loader: base file + per-vertical overlay, additive merge
  (overlay can ADD subtypes/buckets, never silently reassign a subtype base
  already placed in a bucket), full validation at BOOT time — fail loudly
  before serving any traffic on a corrupt taxonomy, not lazily on first use.
  This is the module's strongest existing pattern; see Gotcha 3 for why it's
  worth copying deliberately into every other config-loading module in this
  library, not just admiring here.
- The invariant framework: each invariant is an independently-callable,
  independently-testable function taking a `customer_id` and returning a
  list of structured violations (never a boolean) — so a violation carries
  enough detail (which nodes, which edge, what rule, why) to actually act on,
  not just "something's wrong somewhere."
- Tiered decay: a scheduled/on-read process that ages `tier=2` node weights
  down over time and prunes `tier=3` nodes past `expires_at` — `tier=1` nodes
  never decay or expire.
- Arc classification: a deterministic feature-extraction + rule-cascade
  function producing `(arc_type, confidence, phase)` from an account's graph
  — never a black-box model an FDE can't inspect or explain to a client.

**Config (an FDE fills in per client):**
- `taxonomy_base.json` + a per-vertical overlay: which subtypes exist, which
  are polarity-ambiguous, which revenue bucket each definitive-polarity
  outcome subtype belongs to.
- The set of canonical arc types meaningful for this client's business (the
  origin system uses 8; a different vertical may need a different set).

## Build Prompt

> Build the context graph & causal layer for `{VERTICAL_NAME}`. Implement
> five pieces:
>
> 1. **Schema** — `ContextNode`/`ContextEdge` tables matching Data Shapes
>    exactly. Every node and edge carries `customer_id`; every read function
>    in this module takes `customer_id` as a required parameter and filters
>    by it — there is no "read by node_id alone, trust the caller" path
>    anywhere in this module (same rule as Module 01's access-control
>    contract, applied here to graph reads specifically).
>
> 2. **Taxonomy loader**, modeled EXACTLY on this pattern (it is the
>    strongest validation pattern in the whole reference system — copy its
>    shape deliberately, don't reinvent a weaker version):
>    ```
>    def load_base() -> dict:
>        data = read_json("taxonomy_base.json")
>        validate_structure(data)  # required keys, no dup entries, subtype
>                                   # names match ^[a-z_]+$
>        return data
>
>    def load_overlay(vertical) -> dict | None:
>        path = f"taxonomy_{vertical}.json"
>        if not exists(path): return None
>        data = read_json(path)
>        validate_structure(data, is_overlay=True)  # must declare
>                                   # "extends": "base" and its own vertical
>        return data
>
>    def get_taxonomy(vertical=None) -> Taxonomy:
>        base = load_base()
>        overlay = load_overlay(vertical) if vertical else None
>        if overlay:
>            validate_overlay_vs_base(overlay, base)  # overlay may ADD
>                # subtypes/buckets; it may NEVER move a subtype base already
>                # placed in bucket X into a different bucket Y, and it may
>                # NEVER mark a subtype "polarity-ambiguous" that base already
>                # gave a definitive bucket to — both are base/overlay
>                # CONTRADICTIONS, not extensions, and must raise.
>        return merge(base, overlay)  # additive union, cached per-vertical
>
>    def validate_all_at_boot() -> list[str]:
>        # Load base + EVERY overlay file found on disk, validating each.
>        # Call this from application startup, unconditionally, and let it
>        # raise — an invalid taxonomy file must prevent the app from
>        # serving ANY traffic, not just traffic for the broken vertical.
>        # Return the list of verified filenames for the startup log.
>    ```
>
> 3. **Invariant framework** — each invariant is a function named
>    `invariant_i{N}_{description}(customer_id) -> list[Violation]` using
>    THESE exact IDs (i1-i4 — do not import a different numbering from
>    anywhere else; if you've seen a reference system with 17 invariants
>    numbered differently, that numbering is irrelevant here, this module
>    only requires these four):
>    - `invariant_i1_no_outcome_to_outcome`: no edge in `CAUSAL_EDGE_TYPES`
>      from an OUTCOME node to another OUTCOME node (a realized result can't
>      directly cause another realized result without an intervening
>      SIGNAL/DECISION).
>    - `invariant_i2_no_reverse_time_causal`: no edge in `CAUSAL_EDGE_TYPES`
>      where `to_node.occurred_at < from_node.occurred_at` (an effect cannot
>      occur before its cause — use `occurred_at`, never `created_at`, see
>      Gotcha 1).
>    - `invariant_i3_no_orphan_revenue_outcomes`: every OUTCOME node carrying
>      a non-null `revenue_impact` has at least one inbound edge in
>      `CAUSAL_EDGE_TYPES` (a $-impact claim with zero supporting evidence in
>      the graph is not audit-defensible).
>    - `invariant_i4_polarity_consistency`: for every edge in
>      `CAUSAL_EDGE_TYPES` from a SIGNAL to an OUTCOME, look up the SIGNAL's
>      polarity (`positive_signal_subtypes`/`negative_signal_subtypes`/
>      ambiguous) and the OUTCOME's polarity (its revenue bucket's
>      polarity — `lost`/`at_risk` are negative, `expansion`/`protected` are
>      positive, `pipeline` is neutral/skip); flag a positive→negative or
>      negative→positive pairing. Skip entirely (do not flag, do not log as
>      skipped) if either side is polarity-ambiguous or neutral.
>    `Violation` carries `invariant_id`, `severity`, `account_id`,
>    `node_ids`, `edge_ids`, and a human-readable `message` naming the actual
>    nodes/edge involved (never just "invariant i3 failed somewhere for this
>    customer" — that's useless for an operator trying to fix real data).
>
> 4. **Tiered decay** — a function run on a schedule (or lazily, on read —
>    your choice, but state which one you picked and why, since it changes
>    the freshness/cost tradeoff) that: for every `tier=2` node, reduces
>    `weight_decay` by a fixed `DECAY_RATE_PER_DAY` (pick a concrete default,
>    e.g. `0.02`, i.e. a tier-2 node reaches zero influence after ~50 days
>    with no reinforcing activity) since `occurred_at`, floored at 0; for
>    every `tier=3` node past its `expires_at`, deletes it (or soft-deletes,
>    your choice — state which); `tier=1` nodes are never touched by this
>    function at all — assert that explicitly in a test, don't just assume
>    the loop skips them because nothing decrements tier=1.
>
> 5. **Arc classification** — a pure function, with the feature extraction
>    and scoring given as literal pseudocode, not prose (a rollup-math-style
>    gap here reproduces the exact defect Module 03 already found and fixed
>    once in this library — don't reintroduce it in this module):
>    ```
>    def extract_features(account_id, customer_id) -> dict:
>        nodes = get_nodes(account_id, customer_id, occurred_within_days=180)
>        return {
>            "signal_count": count(n for n in nodes if n.node_type == "SIGNAL"),
>            "negative_signal_ratio": count(negative signals) / max(1, signal_count),
>            "outcome_revenue_net": sum(signed revenue_impact across OUTCOME
>                nodes, positive-bucket amounts positive, negative-bucket
>                amounts negative, pipeline/ambiguous excluded),
>            "max_causal_chain_depth": longest path length through
>                CAUSAL_EDGE_TYPES edges ending at any OUTCOME node,
>            "days_since_last_signal": (today - max(n.occurred_at for n in
>                nodes if n.node_type == "SIGNAL")) or None if zero signals,
>        }
>
>    ARC_RULES = [  # evaluated IN ORDER, first match wins — this ordering
>                    # IS the rule cascade; changing the order changes results
>        ("silent_churn", lambda f: f["days_since_last_signal"] is not None
>            and f["days_since_last_signal"] > 60 and f["outcome_revenue_net"] < 0),
>        ("crisis_recovery", lambda f: f["negative_signal_ratio"] > 0.6
>            and f["outcome_revenue_net"] > 0),
>        ("stalled_deployment", lambda f: f["max_causal_chain_depth"] == 0
>            and f["signal_count"] > 0),
>        # ... one lambda per client-defined canonical arc type, in priority
>        # order; the LAST rule in the list must be a catch-all (lambda f: True)
>        # mapping to a "stable"/"insufficient_data" arc — classification
>        # must never fail to return SOME arc_type.
>    ]
>
>    def classify_arc(account_id, customer_id) -> tuple[str, float, str]:
>        f = extract_features(account_id, customer_id)
>        for arc_type, rule in ARC_RULES:
>            if rule(f):
>                # Confidence = fraction of this rule's OWN conditions that
>                # are true by a wide margin, not just barely true — e.g. for
>                # crisis_recovery's two conditions, score each condition's
>                # margin past its threshold (0.0 at the threshold, 1.0 if
>                # doubled past it, capped at 1.0) and average them. A rule
>                # that barely fired (values just past the threshold) must
>                # score LOWER confidence than one that fired with margin —
>                # this is what makes confidence informative rather than a
>                # constant per matched rule.
>                confidence = score_margin(f, rule)
>                phase = "intervention" if f["days_since_last_signal"] is
>                    not None and f["days_since_last_signal"] < 14 else "baseline"
>                return arc_type, confidence, phase
>        return "insufficient_data", 0.0, "baseline"  # unreachable if the
>            # catch-all rule above is present, but never omit this — a
>            # missing catch-all is exactly how classification silently
>            # returns None/crashes on a real account that matches nothing
>    ```
>    An FDE customizing this for a new vertical replaces `ARC_RULES`' lambdas
>    and thresholds — the `extract_features`/`classify_arc` scaffolding
>    itself is Engine, not Config.

## Acceptance Criteria

- Inserting a `CAUSED_BY` edge from an OUTCOME node to another OUTCOME node
  is either rejected at write time or flagged by
  `invariant_i1_no_outcome_to_outcome` when the invariant suite runs — pick
  one enforcement point and be consistent about which layer owns it, but the
  condition must never go undetected in a graph that's otherwise passing all
  checks.
- A causal edge where the target node's `occurred_at` predates the source
  node's `occurred_at` is flagged by the reverse-time invariant. Constructing
  the same scenario using `created_at` timestamps that are correctly ordered
  (i.e. the records were entered into the system in a sensible order, but
  describe events that happened in the wrong real-world order) must STILL be
  flagged — the check reads `occurred_at`, full stop.
- A taxonomy overlay that attempts to move a base-defined subtype into a
  different revenue bucket fails `validate_overlay_vs_base` at load time,
  before the taxonomy is ever served to any request.
- A taxonomy overlay that marks a subtype "polarity-ambiguous" when base
  already gave it a definitive revenue bucket also fails at load time, for
  the same reason (these are the same class of contradiction, not two
  unrelated rules).
- `validate_all_at_boot()` raises if ANY taxonomy file on disk is invalid —
  including a vertical's overlay that no current customer is even using yet.
  A broken file for an unused vertical must still block startup; "nobody's
  using it yet" is not a reason to let corrupt config exist.
- An edge between a positive-subtype SIGNAL and a negative-subtype OUTCOME is
  flagged by the polarity-consistency invariant — UNLESS either subtype is in
  the taxonomy's polarity-ambiguous set, in which case that specific edge is
  silently skipped by this check (not flagged, not specially logged as
  "skipped" — genuinely a no-op for this rule, since polarity-ambiguous
  subtypes take their sign from other signals, not this check).
- Attempting to write a `ContextNode` whose `node_subtype` is not a member of
  the loaded taxonomy (not in any revenue bucket, not in either signal
  polarity list, not in the ambiguous lists) is rejected at write time — this
  must be tested separately from the invariant suite, since none of i1-i4
  operate on vocabulary membership at all, only graph structure.
  Constructing an OUTCOME node with a real, valid subtype but then a SIGNAL
  node with a typo'd/invented subtype must be caught the same way — the
  check applies per-node, not per-graph.
- Two accounts with the SAME matched arc rule but different margins past that
  rule's thresholds (e.g. both match `crisis_recovery`, one with
  `negative_signal_ratio=0.62` just past the 0.6 threshold, the other with
  `0.95`) receive DIFFERENT confidence scores, with the larger-margin account
  scoring higher — confidence must track how strongly a rule matched, not
  just whether some rule matched at all. (A constant confidence-per-rule
  implementation, or one that varies only by which rule matched, fails this
  criterion even though it "isn't a constant" in the trivial sense.)
- After running tiered decay once, a `tier=2` node's `weight_decay` is
  strictly lower than before, a `tier=3` node past `expires_at` is gone (or
  marked deleted, per whichever choice was made), and a `tier=1` node's
  `weight_decay` is UNCHANGED — construct one node of each tier with
  identical `occurred_at`/`expires_at` values and assert all three outcomes
  from a single decay run, so tier=1's exemption is proven, not assumed.

## Reference Test Harness

1. **Invariant unit tests, one deliberately-broken fixture graph per
   invariant** — construct the minimal graph that should trip each rule,
   assert the violation fires with the correct `invariant_id` and names the
   correct nodes; construct a passing variant of the same shape and assert
   it does NOT fire (both directions matter — an invariant that never fires
   is as useless as one with false positives).
2. **Taxonomy contradiction tests** — one test per base/overlay contradiction
   type (bucket-reassignment, ambiguous-vs-definitive), each with an overlay
   fixture engineered to trip exactly that rule.
3. **Live smoke test** — run a synthetic multi-phase account through the
   pipeline (see Module 11) and run the full invariant suite against the
   resulting graph. A synthetic dataset engineered to be realistic will
   still often trip `invariant_i3_no_orphan_revenue_outcomes` and
   `invariant_i2_no_reverse_time_causal` at low volume — that's not
   automatically a bug in this module; it's frequently a generation-order bug
   in whatever produced the synthetic data (e.g. an LLM-enriched causal edge
   computed from unordered source events). Confirmed directly this session,
   in the origin reference system (which uses a different, larger invariant
   numbering scheme than this module's four — the specific IDs don't
   transfer, only the lesson does): a synthetic multi-phase test customer's
   graph tripped 16 violations, the large majority an orphan-revenue-outcome
   equivalent and one a reverse-time-causal equivalent, purely from
   generation-order artifacts in the test data generator, not a bug in the
   invariant checks themselves — investigate the DATA before assuming the
   CHECK is wrong.
4. **Decay test** — one node per tier, identical timestamps, single decay run,
   assert all three post-conditions from the tiered-decay Acceptance
   Criterion in one test (not three separate tests each checking only one
   tier — the point is proving tier=1's exemption in the SAME run where
   tier=2/3 actually change, so there's no chance the exemption is just an
   artifact of never having anything to decay).

## Known Gotchas

**1. `occurred_at` vs. `created_at` — using the wrong one breaks causal
ordering checks silently**
*Symptom:* A reverse-time-causality invariant either misses real violations
or flags false ones, and it's not obvious why from reading the invariant's
own logic, which looks correct.
*Root cause:* Two different timestamps exist on every node: when the
real-world event happened (`occurred_at`) and when the record was written to
the database (`created_at`). Backfilled data (a CSV upload describing last
month's events, an integration syncing historical records) makes these
diverge routinely, not as an edge case. A check that accidentally uses
`created_at` for causal ordering will pass or fail based on *upload order*,
which has nothing to do with real causality.
*Fix:* Every causal-ordering check reads `occurred_at`, never `created_at`.
Grep for this specifically when reviewing any new invariant — it's an easy
one-word mistake with no immediate symptom.

**2. Cross-tenant graph leakage through a node-ID-only read**
*Symptom:* A graph traversal or lookup function, given just a `node_id`,
returns data belonging to a different customer than the caller's context —
same failure family as Module 01's access-control Gotcha, but recurring here
because graph traversal code (walk from this node to its neighbors) is
naturally written in terms of node IDs, and it's easy to forget to re-check
tenant ownership at each hop.
*Root cause:* A multi-hop traversal function checks the STARTING node's
`customer_id` but not every node it walks to along the way — if edges or
node IDs are ever guessable/sequential, a crafted traversal could walk into
another tenant's subgraph.
*Fix:* Either scope every traversal query itself to `customer_id` (the graph
database/query layer enforces it structurally, not the traversal logic), or
explicitly re-check `customer_id` at every node visited during a multi-hop
walk — never assume the starting node's tenant check covers the whole walk.

**3. Structural checks don't catch vocabulary drift — validate node/edge data
against the taxonomy at write time too, not just the taxonomy file itself**
*Symptom:* A node gets written with a typo'd or invented `node_subtype`
(`"chrun_risk"` instead of `"churn_risk"`, or a subtype nobody ever added to
either taxonomy file) and nothing catches it — not the taxonomy loader
(which only validates the taxonomy FILES), not any of i1-i4 (which only
check graph STRUCTURE, never vocabulary membership). The node sits in the
graph indefinitely, silently excluded from every taxonomy-driven
classification (polarity checks skip it, revenue-bucket lookups return
nothing for it) without ever raising an error anywhere.
*Root cause:* Validating a config file's internal consistency (what this
module's taxonomy loader does well) and validating that DATA written against
that config actually conforms to it are two different checks, easy to build
one of and assume it covers the other.
*Fix:* The write-time subtype validation rule in Data Shapes above closes
this specifically — every `ContextNode` write checks its `node_subtype`
against the currently-loaded taxonomy before persisting, independent of and
in addition to the taxonomy file's own load-time validation.

## Provenance

Origin: `kpi-dashboard/backend/models.py` (`ContextNode`, `ContextEdge`
classes), `kpi-dashboard/backend/utils/taxonomy_loader.py` (base+overlay,
`validate_all_at_boot` — confirmed wired into `app_v3_minimal.py` startup via
grep), `kpi-dashboard/backend/utils/context_graph_invariants.py` (origin
system has 17 invariants under its own I1-I17 numbering — this module's
i1-i4 are a deliberately reduced minimum set with THEIR OWN numbering, not a
1:1 mapping to the origin system's; do not assume `invariant_i2` here means
the same rule as "I2" in the origin system), `kpi-dashboard/backend/utils/
context_graph.py` (traversal/query helpers), `kpi-dashboard/backend/utils/
arc_classifier.py` (`classify_arc`, feature extraction, phase detection).

Reference Test Harness's live-smoke-test finding (16 violations, the large
majority an orphan-revenue-outcome-type rule and one a reverse-time-causal
rule, in the origin system's own numbering) observed directly in this
session's server logs while running the Phoenix multi-phase test customer
(customer 355) through the pipeline on 2026-08-07 — real output, not a
constructed example.

## Validation Note

Validated 2026-08-07 (second attempt — the first agent correctly refused to
fabricate a spec after a tooling mistake left it unable to locate the
not-yet-committed file; retried with a corrected file path). A fresh agent
built a working implementation from scratch for an invented "regional
utility co-op" vertical. 28/28 tests pass.

**Two real, distinct defects found — both closed:**

1. **Tiered decay was promised as owned, built-once Engine logic in Boundary
   and Engine sections, but appeared in ZERO of Build Prompt, Acceptance
   Criteria, or Reference Test Harness** — an agent following the
   (deliberately self-contained) Build Prompt literally would never have
   built it, despite two other sections committing to it. This is the
   Module 01/03 contradiction shape, but manifesting as a whole deliverable
   silently dropped rather than a specific instruction textually conflicting
   with another. **Fixed**: added as Build Prompt piece 4 with full
   pseudocode, plus a dedicated Acceptance Criterion and Reference Test
   Harness item proving the tier=1 exemption in the same test run where
   tier=2/3 actually change (not three separate tests that could each pass
   vacuously).
2. **Arc classification was 100% prose, zero pseudocode** — "a deterministic
   feature-extraction + rule-cascade... confidence must be genuinely
   informative... not a constant," with no feature formulas, no scoring
   function, no phase definition. This is the EXACT defect Module 03's own
   Validation Note already documented finding and fixing once
   ("Rollup math was prose, not pseudocode... forcing the agent to invent
   defensible-but-arbitrary answers") — it reappeared, unfixed, in the very
   next module written after that lesson was recorded. The agent had to
   invent an entire scoring/confidence/phase scheme from scratch; a
   different implementer would very plausibly invent an incompatible one.
   **Fixed**: rewrote as literal pseudocode (`extract_features`,
   `ARC_RULES` as an ordered list of `(arc_type, predicate)` pairs with a
   mandatory catch-all, a margin-based confidence calculation), and
   tightened the confidence Acceptance Criterion so a constant-per-matched-
   rule implementation (which technically "isn't a constant" but doesn't
   track match strength either) no longer passes.

**Smaller gaps also closed**, each found by the validation run actually
trying to implement the spec rather than just reading it: `CAUSAL_EDGE_TYPES`
was never defined against the 9 edge types (I1-I3 all said "causal edge"
with no anchor) — now an explicit named set. SIGNAL polarity had no defined
source — the taxonomy schema gave OUTCOME polarity via `revenue_buckets` but
never gave SIGNAL subtypes an equivalent; added
`positive_signal_subtypes`/`negative_signal_subtypes` with the same
base/overlay contradiction-checking treatment. `created_at` was referenced
by Gotcha 1 but never declared in Data Shapes — added to both node and edge
shapes. A real, not just spec-level, gap: nothing validated that a written
node's `node_subtype` is actually a member of the taxonomy — the taxonomy
loader validates taxonomy FILES, but nothing validated DATA against them.
Added as an explicit write-time check (Data Shapes + new Acceptance
Criterion + new Gotcha 3, replacing an earlier Gotcha 3 that the validation
correctly flagged as pure meta-commentary for library authors with zero
FDE-facing implementation content). Also fixed an invariant-numbering
inconsistency where the Build Prompt asked for `invariant_i2_...` while
Reference Test Harness referenced the origin system's own different "I17" —
now both consistently use this module's own i1-i4 numbering, with an
explicit note in Provenance that the origin system's 17-invariant numbering
does NOT map 1:1 onto this module's four.

**Pattern confirmed a fourth time, in its rarest form yet**: this is the
first validated module where the SAME specific defect shape (prose instead
of pseudocode for a scoring/confidence function) recurred verbatim after
already being found and fixed in an earlier module. The lesson from Module
02 — "fully specify every code path, an ellipsis is a specific risk" — was
apparently not enough on its own to prevent the SAME author from writing
unspecified prose again one module later for a different function. Treat
this as evidence that the adversarial rebuild step cannot be skipped or
abbreviated for any module going forward on the assumption that "the author
already learned this lesson" — evidently that assumption doesn't hold
module-to-module even for the same author.
