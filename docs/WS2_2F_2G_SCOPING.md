# WS-2 2f/2g Scoping — I3′-on-edges + csv_import blind spot, and supersession

**Status (updated 2026-08-27, after a third review round): both blocking
product decisions are now made — §3 Q1-Q4 all RESOLVED** (Q1/Q2 by
investigation, Q3/Q4 by explicit human decision, see §0 and §2.3(c)/§3).
2f's node-side writer-bypass fix is shipped (`fe1e56efd`). Remaining work
is narrower engineering detail (§3 Q5-Q8: schema mechanics, the "every
surface" audit, non-causal edge scope, registry-ID assignment) that the
original review explicitly flagged as safe to leave to the implementer —
this is no longer a "not an approved spec" first draft for 2f-edge/2g's
core semantics, though no code for the edge-side clamp or supersession
itself exists yet. Citations are file:line as of `main` at `e8df3c16d`
(2026-08-27); the decisions above post-date that commit.

**Important correction to the framing this doc was commissioned under:** the
task brief states 2f/2g have "NO further specification anywhere in the repo,
its git history, or the off-repo doc set." That is true of `state-of-play.md`
itself, but two other files in the same off-repo doc set *do* specify them in
concrete, if terse, terms:

- `~/Downloads/cspulse-work-new-by-cc/03-edge-provenance/ws1-ws2-prompts.md`,
  sections `## 2f` and `## 2g` (the actual task prompts these sub-items were
  cut from)
- `~/Downloads/cspulse-work-new-by-cc/03-edge-provenance/verify-three-findings.md`,
  findings **F2** (supersession) and **F3** (the I3′/csv_import blind spot) —
  live-data evidence gathered *before* 2f/2g were written, which is presumably
  why the prompts read as settled rather than exploratory
- `~/Downloads/cspulse-work-new-by-cc/reference-code/cspulse_pipeline_sim.py`
  — a runnable reference implementation of both, in a throwaway SQLite
  harness, `--mode fixed` vs `--mode current`

So this document is not starting from zero. What it adds on top of those three
files: verification against the *current* live codebase (not the reference
sim) of what already exists vs. what's still a gap, a concrete invariant
statement in the I3′ style, and the open questions those source docs leave
unresolved. Section 3 lists what's still genuinely open even after finding
these.

---

## 0. Correction pass (2026-08-27, second review round)

An external review of this document couldn't verify file:line citations
directly but flagged two things as worth confirming before treating this as
buildable. Both were checked against the actual repo (static analysis, no
live DB needed) and are now resolved:

**§2.3(a)'s citation was wrong.** `models.py:26` (`data_origin`) is on
**`Customer`**, not `ContextNode` — confirmed by reading the file. This
doesn't change item 25's usage (it correctly used `Customer.data_origin`,
a per-tenant flag, which is what WS-2 2a actually shipped) but the
sentence in §2.3(a) misattributed the class and should be read as: "2a
shipped a per-tenant `Customer.data_origin` flag — still not a per-row
`ContextEdge` column of any kind."

**§3 Open Question 1 (does `clamp_unearned_confidence()` have a call
site?) is RESOLVED, and the answer changes §1.4's analysis materially.**
It DOES have a call site: `utils/context_graph.py:942`, inside
`upsert_node()` (the sanctioned write helper for every `ContextNode`),
gated only on `node_type == 'OUTCOME'` — confirmed by reading the function
body, not just grepping the name. So the clamp is wired in and does fire
for OUTCOME writes that go through `upsert_node()`.

**But the specific csv_import writer that produces the blind spot doesn't
go through `upsert_node()` at all.** `mcp_server/cs_pulse_onboarding.py`,
lines 1714-1727 (the `outcomes.csv` ingest loop) constructs
`ContextNode(...)` directly and does `_db.session.add(...)` — a raw
bypass that never calls `clamp_unearned_confidence()`. This is the exact
same bug class the WS-1 audit already flagged for edges (`add_edge()` at
`utils/context_graph.py:828`, "a second sanctioned-looking constructor
that skips dedup AND the invariant gate — WS-2 2c should delete or fold
it") — except for nodes, and apparently never flagged before now.

This resolves §1.4's two candidate mechanisms decisively: **mechanism (a)
— no call site for this path — is the confirmed root cause**, not a
guess. Mechanism (b) (the `_has_specific_source_ref()` OR-logic waiving
the evidence check) is real code but currently unreached for this
specific path, since the bypass never gets that far; it becomes a live
risk the moment (a) is fixed and this writer starts routing through
`upsert_node()`, because a csv_import row with a non-empty `source_ref`
but empty `evidence` would then pass the OR-check and dodge the clamp
anyway. **Both fixes are needed, in this order: (1) route the
`outcomes.csv` writer through `upsert_node()` instead of the raw
constructor, (2) then verify (b) doesn't quietly waive evidence for rows
that have some `source_ref` but no real evidence content.**

**On whether §2.3(c)'s tier-ordering question is the same decision as
Hold 1 (cell 14):** checked directly — they are not. Hold 1 assigns a
tier to one specific edge type (`playbook_auto_trigger × TRIGGERED`) and
is fully signed. §2.3(c) asks a different question: once tiers are
assigned matrix-wide, what happens when two edges on the *same triple*
carry tiers that need comparing — including the same tier. F2's own
headline example (`wizard_a` vs `llm_enrichment`) is two `inferred`-tier
edges, so no cross-tier ordering rule — however Hold 1 or any other cell
gets resolved — can adjudicate it; a same-tier tiebreak (recency? a
writer-priority list?) is a genuinely separate, still-unaddressed
decision. Resolving cell 14 doesn't shortcut this one.

---

## 1. 2f — I3′ extension to edges + its csv_import blind spot

### 1.1 What I3 checks today (node-level orphan check — not what 2f extends)

`invariant_i3_no_orphan_revenue_outcomes` —
`kpi-dashboard/backend/utils/context_graph_invariants.py:257-307` — checks
that every `OUTCOME` node with `revenue_impact IS NOT NULL` has at least one
inbound causal edge (`CAUSED_BY`/`INDICATES`/`LED_TO`/`TRIGGERED`/`RESULTED_IN`).
Paired tests: `test_i3_clean` / `test_i3_dirty`,
`kpi-dashboard/backend/tests/test_context_graph_invariants.py:225-245`. This
is a **structural** check (does provenance exist at all) and is registered in
`INVARIANTS_REGISTRY['I3']` (line 1209) — it runs in the standard post-commit
audit sweep.

### 1.2 What "I3′" actually is today — not I3, a different thing with a confusing name

`I3′` is **not** a variant of I3 registered in `INVARIANTS_REGISTRY`. It's a
separate, unregistered **write-time clamp** function,
`clamp_unearned_confidence()` —
`kpi-dashboard/backend/utils/context_graph_invariants.py:1361-1455` (the
`I3' — Unearned-confidence clamp` block, added April 2026). It fires only on
`OUTCOME` node writes and checks a **content** question I3 doesn't ask: does
this node carry actual evidence (`properties.evidence`,
`properties.evidence_list`, or a specific `source_ref`), not just *some*
inbound edge. If neither is present, it downgrades the write in place:
`confidence` capped at 0.3, `tier` forced to 2, and
`properties.evidence_clamped = True` is stamped with a human-readable reason
string (`_has_evidence()` / `_has_specific_source_ref()`, lines 1387–1410).

So I3 and I3′ are complementary but check different things:
- I3 = "does *any* inbound causal edge exist" (structural, post-hoc, node-only)
- I3′ = "does *this specific claim* carry evidence" (content, write-time,
  currently OUTCOME-node-only)

Neither one today looks at **edges** as the object being evidenced. That's
the literal gap "I3′ extension to edges" names.

### 1.3 Where I3′ is wired in, and where it is not

`clamp_unearned_confidence()` is a pure function — it doesn't call itself. I
did not find a call site inside `context_graph_invariants.py`, `edge_factory.py`,
or `upsert_edge()`/`upsert_node()` in `utils/context_graph.py` in this branch
(searched via `grep -rn "clamp_unearned_confidence"` — zero results outside
its own definition and the module docstring cross-reference at
`context_graph_invariants.py:790`). The docstring calls it "the write-time
clamp," implying it's meant to run inside the OUTCOME-node write path, but I
could not confirm an active call site in this codebase snapshot. **This is a
first thing 2f needs to resolve, and I list it as an open question in §3** —
if the clamp genuinely isn't wired to any writer today, "extend I3′ to edges"
has to also mean "wire I3′ itself in," not just "add the edge variant."

*(Caveat: this is a static-grep finding on the current worktree, not a
runtime trace. The clamp could be invoked from a location this search missed,
e.g. a wizard's write path calling it inline without importing under that
exact name via a re-export. Whoever picks up 2f should `grep -rn
"clamp_unearned_confidence\|evidence_clamped"` fresh before assuming either
way.)*

### 1.4 The csv_import blind spot — confirmed, not just inferred

`verify-three-findings.md` F3 (lines 61-99) already ran this check against
live data on customer 390 and found: the clamp's logic (per §1.2 above)
checks `properties.evidence` truthiness, and a `csv_import`-sourced OUTCOME
node ("Revenue at Risk — Titan Hyperscale Labs", `revenue_impact:
-4,100,000`) had `properties: {"evidence": "", "confidence": ""}` — an empty
string, which `_has_evidence()` correctly treats as falsy (line
1392: `isinstance(ev, str) and ev.strip()`) — **so on its own, this row
should already fail the evidence check and get clamped, regardless of
`source_platform`.**

That means F3's phrasing ("the clamp... trusts csv_import unconditionally")
is describing the *symptom*, not yet a confirmed root cause naming
`source_platform` as an allowlist key. Two candidate mechanisms are still
undistinguished, and F3 itself flags this (its own check #1): either (a) the
clamp genuinely isn't being called on the `csv_import` write path at all
(consistent with §1.3's finding that no call site was found for *any* path),
or (b) it is called, but `source_ref` is populated on `csv_import` rows in a
way that satisfies `_has_specific_source_ref()` and short-circuits the
evidence check even though the *evidence* field is empty (line 1436:
`if _has_evidence(properties) or _has_specific_source_ref(source_ref)` — an
OR, so a populated `source_ref` alone passes regardless of evidence content).
F3's own check #3 raises exactly this: node 124379 "has a `source_ref`... so
it likely passes the filter on two of three conditions while failing the one
that matters" — but that's about `_is_narrative_only()`, a different filter
function, not confirmed against `clamp_unearned_confidence` specifically.

**Confirming which mechanism is live is 2f's first concrete task**, ahead of
writing any new invariant — the fix differs materially: (a) is "wire the
clamp into the csv_import write path," (b) is "tighten
`_has_specific_source_ref()` so a `source_ref` alone no longer waives the
evidence requirement," and it's possible both are true simultaneously (no
call site *and* the OR-logic would still let it through if there were one).

### 1.5 What "extending I3′ to edges" concretely means

Applying the same content-evidence test to `ContextEdge` rows that
`clamp_unearned_confidence()` applies to OUTCOME nodes. Concretely: does the
edge carry either (a) `properties.evidence` / `properties.evidence_list`
non-empty, or (b) a source-of-truth pointer analogous to `source_ref` — edges
don't have a `source_ref` column (`models.py:804-868`), so this needs its own
definition, most plausibly `properties.source_ref` or reuse of the
`WS-2 2c` `derivation` string already written by `EdgeFactory`
(`utils/edge_factory.py:64`, `properties['derivation']`). An edge with
`evidence_tier='inferred'` (also currently a `properties` key, not a column —
see §1.6) and no evidence content is exactly the object I3′ was built to
catch, just on the other node/edge distinction.

Two edge-specific wrinkles that don't exist for nodes:
- **Confidence semantics differ.** `EdgeFactory`-written inferred edges
  already have `confidence=None` by design (`edge_factory.py:56`,
  reinforced by the `ContextEdge.confidence` column-default removal at
  `models.py:828-844`, fixed 2026-08-27 per the session log). I3′'s
  node-side clamp *lowers* confidence to 0.3; there's nothing to lower on an
  edge whose confidence is already `None`. The edge-side clamp's
  observable effect would have to be on `evidence_tier`/`tier` (forcing it
  down, or forcing `evidence_tier` to a value like `unknown` per the
  adjudication matrix's Hold 2 vocabulary — `adjudication_matrix.md:9,21`),
  not on confidence.
- **Which edges are in scope.** I3 (node-orphan check) only looks at causal
  edge types when checking for *any* inbound edge. I3′-on-edges plausibly
  should scope similarly — only `CAUSED_BY`/`LED_TO`/`TRIGGERED`/
  `INDICATES`/`RESULTED_IN` edges make an evidentiary claim; `INVOLVES`,
  `BELONGS_TO`, `BENCHMARKED_BY`, `SOURCED_FROM` are structural/associative
  and arguably shouldn't be held to an "evidence" bar at all (this mirrors
  I2's existing exclusion pattern for non-causal edge types,
  `context_graph_invariants.py:198-254`, and `validate_edge_pre_commit`'s
  identical early-return, lines 1280-1281).

### 1.6 Proposed invariant statement

> **I3′-E (proposed id, needs registry approval): every causal-type edge
> (`CAUSED_BY`, `LED_TO`, `TRIGGERED`, `INDICATES`, `RESULTED_IN`) whose
> `evidence_tier` — read from `properties['evidence_tier']`, still not a
> real column (§2.3a) — is `inferred`, `unknown`, OR **absent entirely**
> (decided in §3 Q3: absence is in-scope, not exempted — it's ~100% of the
> live graph today, not a rare case), AND which carries no evidence content
> (`properties.evidence` / `properties.evidence_list` non-empty, OR a
> `derivation` string that resolves to a `system.external` logged fact per
> `edge_factory.py`'s vocabulary), gets its confidence-adjacent claim strength
> downgraded at write time: if `confidence` is not already `None`, clamp it
> the same way I3′ does for nodes (cap at the existing `_UNEARNED_CLAMP_FLOOR
> = 0.3`, reusing the constant at `context_graph_invariants.py:1383` rather
> than inventing a second magic number); unconditionally stamp
> `properties.evidence_clamped = True` with a reason string in the same
> format I3′ already uses for nodes; and this clamp must apply identically
> regardless of `source_platform` — `csv_import` included — closing the
> blind spot in the same pass rather than as a follow-up (this ordering is
> explicit in `ws1-ws2-prompts.md`'s "2f" section: "Extending the clamp to
> edges while leaving the largest hole open on nodes is the wrong order of
> work. Do both.").**

A paired clean/dirty test, following the project's own stated pattern
("new invariants require paired clean+dirty tests," confirmed in this file's
own test suite structure — every `Ix` above has a `test_ix_clean` /
`test_ix_dirty[_variant]` pair, e.g. `test_i3_clean`/`test_i3_dirty` at
lines 225-245, `test_i4_clean`/`test_i4_dirty_toplevel`/
`test_i4_dirty_properties_jsonb` at lines 253-283):

- **Clean case**: construct a `CAUSED_BY` edge via `create_inferred_edge()`
  (or the low-level path) with `extra_properties={'evidence': 'ticket
  #4471 escalation log, timestamped'}`. Assert the clamp does *not* fire —
  `evidence_clamped` absent from `properties`, confidence unchanged (or
  stays `None` if it started `None`).
- **Dirty case (the general gap)**: construct a `LED_TO` edge with
  `evidence_tier='inferred'` and no `evidence`/`evidence_list` key at all.
  Assert the clamp fires: `properties.evidence_clamped == True`, and
  (confidence path) if constructed with a non-`None` confidence such as 0.9,
  assert it's now `<= 0.3`.
- **Dirty case (the specific regression F3 found — must be its own test, not
  folded into the general one)**: construct the edge with
  `source_platform='csv_import'` specifically, and assert the clamp fires
  identically to the `llm_enrichment` case. This is the test that would have
  caught the blind spot — a test that only exercises `llm_enrichment` would
  pass today and still miss `csv_import` entirely, which is exactly what
  happened to the node-level clamp.

---

## 2. 2g — supersession

### 2.1 What's actually already specified — this is not first-principles territory

Contrary to the task brief's premise, "supersession" has a concrete
prior definition in this off-repo doc set, written *before* the
`state-of-play.md` one-liner that named it:

- **`verify-three-findings.md`, finding F2** (lines 35-57) states the claim,
  live evidence, and the proposed rule: *"an arriving `observed` or
  `asserted` edge sets `superseded_by` on any `inferred` edge for the same
  triple. Superseded rows stay in the table for audit and drop out of all
  surfaces and denominators."*
- **`ws1-ws2-prompts.md`, section `## 2g`** (lines 249-256) restates the same
  rule near-verbatim as the actual task prompt, plus the live regression it's
  fixing.
- **`reference-code/cspulse_pipeline_sim.py`** contains a full runnable
  implementation of this rule against a throwaway SQLite schema (not this
  codebase's Postgres schema, but architecturally analogous): a
  `superseded_by INTEGER` column on `context_edges`
  (line 464), and in `stage7_hot_load()` (lines ~957-990), when a new
  `csv_import`/`observed`-tier edge arrives for a `(from_node_id,
  to_node_id, edge_type)` triple that already has a live row
  (`WHERE ... AND superseded_by IS NULL`, line 970), every existing row on
  that triple gets `UPDATE context_edges SET superseded_by=<new_id> WHERE
  edge_id=<old_id>` (line 983) — in `--mode fixed` only; `--mode current`
  deliberately leaves both rows live to demonstrate the bug the rule fixes.

So 2g is not "propose a definition" — it's "implement a rule someone already
specified, decide the handful of details the two source docs leave open, and
verify it against the live schema and live consumers." §2.3 lists exactly
what's still undecided.

### 2.2 Confirmed against the live codebase: the problem F2 describes is real, today

Two independent facts in the current `main` branch corroborate F2 without
needing to re-run the live-data check:

1. **`upsert_edge()`'s dedup key includes `source_platform`.**
   `utils/context_graph.py:969`: *"Deduplicates by (from_node_id,
   to_node_id, edge_type, source_platform)."* F2's own check #1 says
   verifying this "confirms the claim without needing a data query" — and it
   is confirmed. Every writer (`wizard_a`, `llm_enrichment`, `csv_import`,
   etc.) gets its own parallel edge on the same node pair by construction;
   nothing before or after this codebase snapshot's `upsert_edge` collapses
   them.
2. **`get_causal_chain()` has no `superseded_by` (or equivalent) filter.**
   `utils/context_graph.py:120-199` queries
   `ContextEdge.query.filter(ContextEdge.to_node_id == nid, edge_type.in_(...))`
   (and the mirror for downstream) with no exclusion for
   duplicate/contradictory parallel edges on the same triple. This matches
   F2's stated side effect exactly: "`get_causal_chain` returns nodes
   124325, 124327... twice each — once per duplicate edge. Any consumer
   aggregating over a chain double-counts."

### 2.3 What "supersession" needs to mean here, and what's still undecided

Taking F2/2g's rule as the starting point, here is what needs deciding
before it's buildable against *this* codebase (not the reference sim's
throwaway schema):

**(a) Schema: no `superseded_by` column exists today.** `ContextEdge`
(`models.py:804-868`) has no such column, and per this doc's earlier finding
(§1.6 cross-reference), neither `evidence_tier` nor `derivation` are real
columns either — both live inside the `properties` JSON blob via
`edge_factory.py:64`. `state-of-play.md`'s "schema" line-item (the thing
already marked shipped) apparently refers to the `data_origin` column added
to `models.py:26` (on `ContextNode`, per WS-2 2a — confirmed present) — **not**
an `evidence_tier` column on `ContextEdge`, and definitely not
`superseded_by`. This means 2g cannot skip straight to "add a supersession
rule" — it first needs either (i) an actual `superseded_by` column + Alembic
migration (mirroring the reference sim's schema, `cspulse_pipeline_sim.py:464`),
or (ii) a `properties.superseded_by` JSON-blob convention consistent with how
`evidence_tier`/`derivation` are currently stored. A real column is
queryable and indexable (`WHERE superseded_by IS NULL` is the hot-path
predicate on every read); a JSON key is not, without a functional/expression
index. Given that `get_causal_chain` and every other edge-reading function
would need to filter on this on every call, a real column looks like the
right call, but that's exactly the kind of decision this scoping pass should
flag rather than silently pick.

**(b) What counts as "the same triple."** F2/2g both key on `(from_node_id,
to_node_id, edge_type)`. That's stricter than `upsert_edge`'s existing
dedup key by exactly the field that's causing the bug — dropping
`source_platform` from the match key. Worth flagging explicitly: this means
supersession and the existing dedup mechanism disagree by design (dedup
purposely lets different `source_platform`s coexist today; supersession
purposely stops treating that as acceptable once a stronger tier arrives).
That's not a contradiction, but it means 2g isn't just "add a trigger," it's
"add a second matching semantic that overrides the first once a tier
ordering is established" — worth a comment at the call site so a future
reader doesn't `git blame` their way into thinking one of the two is a bug.

**(c) RESOLVED WITH DECISION (2026-08-27).** F2 states the rule as one
direction only (`observed`/`asserted` supersedes `inferred`), which doesn't
even resolve F2's own headline example (`wizard_a` 0.65 vs `llm_enrichment`
0.85, both `inferred`-tier per the signed matrix, cells 4-6 vs 7-10 in
`adjudication_matrix.md:48-54`). Full decision, replacing the open question:

- **Cross-tier: full monotonic ordering** — `observed > asserted > inferred
  > unknown`. A newer edge supersedes an older one on the same triple only
  when it's strictly higher tier. This just fills in the two tiers F2 left
  unaddressed (`asserted` vs `observed`, `unknown`'s bottom position); it
  isn't a new judgment call beyond what F2 already implied.
- **Within `inferred` tier, different writers: an explicit, versioned
  writer-priority list — not confidence, not raw recency.** Not confidence,
  because `wizard_a`'s 0.65 and `llm_enrichment`'s 0.85 aren't established
  as being on the same calibrated scale — ranking by them would compare
  numbers that look comparable but aren't, worse than not comparing at
  all. Not raw recency across writers, because a newer low-effort
  automated pass shouldn't beat an older, more expensive inference just by
  arriving second (recency is a valid tiebreak *within* one writer, not
  across different methodologies). Writer-priority, because two automated
  writers firing on the identical triple is redundant inference, not two
  independent parties disagreeing — a dedup problem, which has a
  principled solution: rank the methods once, apply consistently.
  **First-pass ranking: `llm_enrichment > wizard_a`** (LLM enrichment makes
  a case-specific judgment; template-based inference is generically
  pattern-matched) — this resolves F2's own headline case. **This list is
  a first-class, versioned artifact** that gets a line added every time
  2c's EdgeFactory ships a new inferred-tier writer, not a one-time
  decision baked into merge logic. **Undefined position on the list → no
  supersession, both edges stay live** — fail safe, not fail by guessing.
  The full list beyond this one pair is still an open engineering/product
  task for whoever builds 2g, not something this scoping doc claims to
  have completed.
- **Same writer, same tier, re-fires on the same triple** (e.g. `wizard_a`
  re-fires after a rescore): **recency wins.** Safe — it's the same method
  updating its own prior read, not a contest between methods.
- **`observed`/`asserted` ties do NOT auto-resolve — leave both live.** If
  a CRM sync and a CSM's manual assertion genuinely disagree, that is a
  real disagreement a human should see, not one a priority list should
  hide by silently picking a winner. Deliberately not extending the
  writer-priority pattern here: redundant automated inference and two
  humans/systems making possibly-genuinely-different claims are different
  risk profiles, and treating them the same would suppress real signal.

**(d) Retirement, not deletion — but retired from what, exactly.** Both
source docs agree superseded rows "stay in the table for audit" and "drop
out of every surface and every denominator." Concretely, "every surface"
touches at minimum: `get_causal_chain()` (§2.2), `get_context_graph_mermaid`
and `get_account_graph_summary` (`utils/context_graph.py:740`, and
`mcp_server/cs_pulse_intelligence.py:558` — both already have a display-layer
filter for the unrelated I17 reverse-time-edge issue per
`context_graph_invariants.py:1082-1088`, so there's existing precedent for
"filter at display layer" as a pattern here), and any Evidence Density
denominator computation (not yet shipped per
`adjudication_matrix.md`'s Hold-1-follow-up test file reference,
`tests/test_evidence_density_contract.py`, described there as "dormant
(skip) until `utils/evidence_density.py` / `utils/edge_factory.py` exist" —
`edge_factory.py` now exists, `evidence_density.py` apparently does not yet).
A full "every surface" audit (grep every `ContextEdge.query` call site) is
outside this scoping doc's scope but should be the first concrete step of
implementation, not an afterthought.

**(e) Who writes the supersession, and when.** The reference sim triggers it
inline inside the CSV-ingest write path (`stage7_hot_load`, "when a new edge
arrives"). In this codebase the equivalent write-time hook would most
naturally live inside `upsert_edge()` itself (`utils/context_graph.py:957`)
so every writer gets it for free — consistent with how I1/I2/I17 pre-commit
checks are already centralized there rather than duplicated per-caller. But
`upsert_edge` currently determines *rejection* (I1/I2/I17) and *update-in-place*
(existing dedup key match) — supersession would add a third write-time
behavior (mark a *different, existing* row) that mutates a row other than
the one being written. That's a meaningfully different code shape (an UPDATE
against a prior row keyed by a looser match than the INSERT/UPDATE's own key)
and should be reviewed as such, not tucked in as a one-line addition.

### 2.4 Grounding in how edges are consumed (per the task's request)

I greped `ContextEdge` usage across health scoring and Wizards A-D to confirm
supersession's downstream blast radius:

- **Health scoring** (`utils/vertical_health.py`, `ScoreCalculator`) computes
  scores from KPI rows, not from `ContextEdge` directly — the context graph
  is narrative/evidence layer, not a scoring input. This matches the
  project's own "two-layer indicator model" memory note (LEADING/narrative
  vs TRAILING/KPI, never conflated). **Supersession therefore does not touch
  health scores** — it only affects narrative/evidence-layer consumers:
  `get_causal_chain`, graph visualizations, and (once built) Evidence
  Density. This narrows 2g's blast radius usefully — it's a provenance/UI/
  audit-metric fix, not a revenue-math fix, which lowers the urgency
  relative to (say) I13/I14's revenue-double-counting invariants but raises
  its priority as a "buyer sees contradictory evidence" trust problem.
- **Wizard A** (`wizards/wizard_a_journey_db.py`) is the primary producer of
  `inferred`-tier edges via templates — it is the thing 2g would most often
  supersede, once real signal/edge data (`csv_import`, or a future SoR sync
  producing `observed`) arrives for the same accounts.
- **Playbook close-linker / `playbook_execution`** edges (cells 12-13 in the
  adjudication matrix) are also `inferred`, also plausible supersession
  targets, though per `adjudication_matrix.md` Hold 4 that particular writer
  now **abstains** entirely on heuristic edges (2026-08-24 fix) — so its
  contribution to future supersession volume should shrink going forward,
  not grow.

---

## 3. Not yet answered — open questions for a human before this is buildable

1. **RESOLVED (§0).** `clamp_unearned_confidence()` is called from
   `upsert_node()` (`utils/context_graph.py:942`) — it fires correctly for
   any OUTCOME write that goes through the sanctioned write helper. The
   F3 "blind spot" framing is accurate: it fires everywhere except the one
   writer that bypasses `upsert_node()` (see #2).
2. **RESOLVED (§0).** Mechanism (a) — no call site for this path — is
   confirmed root cause: `mcp_server/cs_pulse_onboarding.py:1714-1727`
   constructs `ContextNode(...)` directly instead of calling
   `upsert_node()`, mirroring the `add_edge()` bypass already flagged for
   edges in the WS-1 audit. Mechanism (b) (the OR-logic waiver) is real
   but currently unreached for this path — it becomes live the moment (a)
   is fixed, so both fixes are needed, in that order.
3. **RESOLVED WITH DECISION (2026-08-27, third review round).** Quantified
   first, then decided — this was upgraded from "open" because the answer
   changes what I3′-E actually protects, not a detail to leave inline.

   **Finding:** `evidence_tier` is not a DB column (confirmed: `models.py`'s
   `ContextEdge` has no such field, only `properties` JSON) and `upsert_edge()`
   itself never reads, defaults, or validates it — it flows through only if
   a caller includes it. Grepping every edge-writing call site (not just
   `edge_factory.py`) found only two writer classes ever stamp it: (a)
   `create_inferred_edge()` (auto-trigger edges — 3 rows per the matrix —
   and the close-linker, which now abstains entirely per Hold 4, so it
   writes nothing new), and (b) the two csv_import writers fixed for Hold 2
   (`fe1e56efd`, `5c3c5a935`), stamping `unknown` on new writes only.
   Every other writer — `wizard_a_journey_db.py:366`, all of
   `llm/tier1_inference.py` (llm_enrichment + llm_inference, the two
   largest edge populations), signal_analyst, urgent_signal_scanner,
   auto_linker — constructs a `properties` dict with `derivation`/
   `inferred_by`/`confidence_semantics` keys but **never** `evidence_tier`.
   Cross-referenced against the matrix's live-tenant edge count (~3,287:
   llm_enrichment 2,002 + wizard_a 709 + playbook_execution 387 +
   csv_import 155 + llm_inference 24 + urgent_signal_scanner 6 +
   signal_analyst 4): **essentially 100% of today's live edge population
   has no `evidence_tier` key at all.** This is the default state of the
   graph, not an edge case.

   **Decision:** treat "no `evidence_tier` key" as within I3′-E's trigger
   set — the same enforcement path as an explicit `inferred`/`unknown` tag,
   not exempted. Exempting untagged edges would make the invariant a
   near-no-op (it would have ~nothing left to check), and would let the
   highest-volume, least-verified writers (`llm_enrichment`, `wizard_a`,
   `llm_inference`) sail through permanently precisely because they never
   opted in to declaring their own epistemic status — recreating the same
   bug class §1.4's node-side fix just closed, on a larger scale. §1.6's
   invariant statement is updated accordingly — no more "however it ends
   up stored" hedge.

   **Rollout is a separate, explicit decision, not folded into the
   semantics above:** given this fires on ~3,287 edges' worth of writers
   going forward (not a handful), ship I3′-E in **shadow/log-only mode
   first** — compute and log what would get clamped without mutating
   `confidence`/`evidence_tier`/stamping `evidence_clamped`, for one deploy
   cycle. Confirm actual volume and check no downstream consumer
   (dashboards, the not-yet-built Evidence Density calc) breaks or looks
   alarming before flipping to enforce.

   **Companion follow-up, tracked separately, not bundled into 2f's PR:**
   the durable fix isn't "the invariant tolerates absent keys" — it's that
   `wizard_a_journey_db.py`, `llm/tier1_inference.py`, `signal_analyst`,
   and `urgent_signal_scanner` should start explicitly stamping
   `evidence_tier='inferred'` at write time, since that is their actual
   epistemic status. Until that lands, "absent key" stays the permanent
   ~100% baseline rather than shrinking as a legacy category.
4. **RESOLVED WITH DECISION (2026-08-27) — see §2.3(c) for the full
   decision.** Cross-tier: full monotonic `observed > asserted > inferred >
   unknown`, strictly-higher-tier-only supersession. Within `inferred`,
   different writers: an explicit versioned writer-priority list (first
   entry: `llm_enrichment > wizard_a`), not confidence or raw recency;
   undefined position on the list means no supersession (fail safe). Same
   writer/same tier re-firing on a triple: recency wins. `observed`/
   `asserted` ties: do not auto-resolve, surface the disagreement instead
   of hiding it. Left explicitly open: the full inferred-tier priority
   list beyond the one evidenced pair is real engineering/product work for
   whoever builds 2g, to be maintained as a living artifact, not decided
   here.
5. **Schema mechanics**: real `superseded_by` column + Alembic migration, or
   a `properties.superseded_by` JSON convention consistent with today's
   `evidence_tier`/`derivation` storage (§2.3a)? This also interacts with
   question 3 — if 2f and 2g both need new/promoted columns on
   `ContextEdge`, they may be more efficient as a single migration than two.
6. **Full "every surface" audit for supersession retirement** (§2.3d) was
   out of scope for this document — it requires enumerating every
   `ContextEdge.query` / raw-SQL edge-read call site, which is a
   half-day-scale grep-and-classify task on its own, not a scoping-doc-scale
   one.
7. **Does 2f's edge-clamp apply to non-causal edge types at all** (`INVOLVES`,
   `BELONGS_TO`, `BENCHMARKED_BY`, `SOURCED_FROM`)? §1.5 proposes scoping to
   causal types only, mirroring I2's existing pattern, but this is a
   judgment call, not a discovered fact, and should be confirmed with
   whoever signed the adjudication matrix (cells 15, 19 in
   `adjudication_matrix.md` are `INVOLVES`/stakeholder-role-match edges
   tiered `inferred` — if those are meant to carry an evidence bar too, the
   causal-only scoping is wrong).
8. **Registry ID collision risk**: this doc proposes `I3′-E` as a
   placeholder id for the edge-side invariant since `I3′` itself was never
   given a registry slot (it's not in `INVARIANTS_REGISTRY`,
   `context_graph_invariants.py:1206-1224`) and `I7` is already documented
   as "lives in tests, not here" (line 1223) — establishing that not every
   named invariant gets a registry entry. Whether the edge-side check should
   get a registry entry (making it visible to `run_all_invariants`'s
   post-commit audit sweep) or stay an unregistered write-time-only function
   like I3′ is itself a decision, not settled by precedent either way.
