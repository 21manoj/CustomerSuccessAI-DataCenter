# WS-1 and WS-2 — Claude Code prompts

**Reference:** `edge-provenance-plan.md`.

**These are different in kind from the FCI spike.** That was read-only investigation. These modify production write paths and run a schema migration with a backfill across ~10,400 rows. They carry gates, stop conditions, and a review checkpoint that is not optional.

**Order is fixed.** WS-1 blocks WS-2, because quarantining NULL-source rows while a live path is still writing them turns the quarantine into a silent data-loss channel.

**Unresolved from the plan review.** Four blockers were raised against the plan and it is not confirmed they were fixed: line numbers that don't reconcile (240 vs 388; 362 vs 363; 82 for a value computed at 240), `template_plausibility` carrying a blended value its name misdescribes, an exit criterion outside the stated scope, and WS-1.3 lacking a stop condition. All four are handled in the prompts below.

---

## WS-1 — Stop the bleeding

```text
# Task: WS-1 — stop untagged and unreproducible edges from being written

## Context

context_edges is written by at least four paths (arc_edge_generator, llm_tier1_
enrichment, playbook_close_linker, raw-SQL signal_edges ingestion) and nothing
records what warrant any row has. One path — in wizards/wizard_a_journey_db.py —
writes TRIGGERED edges with NO source_platform at all. 724 such rows exist,
spanning 2026-04-09 to 2026-08-12: an active writer, not migration debris.

Separately, ~4,663 llm_enrichment edges carry no reproducible derivation. Their
entire properties payload is {"inferred_by": "llm_tier1_enrichment", "label": "..."}
— no model id, no prompt version, no input node ids, no inference timestamp.

WS-1 stops both. It does NOT introduce evidence_tier or any schema change — that
is WS-2, and it is blocked on this.

## Step 0 — reconcile the line numbers BEFORE editing anything

Prior analysis cites, inconsistently:
  - the trajectory classifier call at :240, and "confirmed source" at :388
  - the ContextEdge constructor at :362, and confidence= at :363
  - Account.arc_confidence assigned at :82, holding a value computed at :240

Open wizards/wizard_a_journey_db.py and state, for the CURRENT revision: the exact
line and enclosing function for each of — the _classify_trajectory_with_confidence
definition, its call site, the ContextEdge constructor, and each of the three fields
the returned value fans into. If they do not match the citations above, report the
correct ones and proceed on yours.

## 1.1 — fix the untagged writer

Route the ContextEdge construction through upsert_edge(), as the sibling path in
arc_edge_generator.py already does. Do NOT just add `source_platform='wizard_a'` to
a raw constructor — the point is that one sanctioned path exists.

Also add structured derivation properties (arc_type, matched pattern) matching what
arc_edge_generator writes. This path currently emits only a free-text label, which
would make it the worst sub-path on Derivation Completeness the moment that metric
ships.

## 1.2 — trace the fan-out, not just the edge

The value from _classify_trajectory_with_confidence() is written into three places:
Account.arc_confidence, the arc_detection node's properties.confidence, and the
TRIGGERED edge's confidence. Fixing only the edge leaves two carrying the same
unaddressed provenance gap.

Determine what that value actually IS. If it originates in a rule-match score rather
than an epistemic estimate, it is being written into fields consumers read as
confidence in a causal claim — the same overloading as the typed 0.80 on template
edges, third instance.

DECISION REQUIRED (do not decide alone): whether Account.arc_confidence and the
node's properties.confidence are in scope. The plan's stated scope is ContextEdge
provenance; these are not ContextEdges. Write the options and the recommendation to
./ws1/scope_decision.md and ask. Default if unanswered: DEFER, with the reason
recorded. Do not let this block 1.1.

## 1.3 — ROI/NRR leak check — SPIKE WITH A STOP CONDITION

An in-code comment documents arc_confidence values >1.0 previously reaching ROI/NRR
math "as garbage". A clamp was added. The clamp fixes the range; it does not
establish that the clamped value stopped being consumed as though calibrated.

Grep every ROI, NRR, expansion-forecast and Power-of-1 call site for arc_confidence
and for anything derived from it.

*** STOP CONDITION ***
If ANY of those paths consumes arc_confidence as a calibrated value, HALT WS-1
immediately. Do not fix it in flight. Write the finding to ./ws1/roi_leak.md and
escalate. That branch means figures previously computed — and possibly shown to
customers — were derived from a value the codebase itself calls garbage. The remedy
is a disclosure decision, not an engineering task, and it must not be made by
whoever happens to be holding the grep.

## 1.4 — write-path inventory (hard deliverable, not a sweep)

Produce ./ws1/edge_write_paths.md: EVERY code path that creates a context_edges row.
ORM and raw SQL. Application code, migrations, ops scripts, seed/demo tooling.

For each: file, function, source_platform set (or not), edge_types emitted, whether
it routes through upsert_edge().

This inventory is the input to WS-2's adjudication matrix. WS-2 cannot start without
it.

## 1.5 — forward LLM derivation logging

In llm/tier1_inference.py, write model_id, prompt_version, input_node_ids and
inferred_at into properties for every edge and node it creates.

FORWARD ONLY. The ~4,663 existing rows cannot be retrofitted — a prompt version that
was never recorded is not recoverable. Do not attempt it. Those rows keep their tier
and permanently lack derivation; that is a disclosure item, not an engineering one.

Ship this in WS-1, not later: every day it slips adds unreproducible edges at the
rate of the largest single source.

## Constraints

- No schema changes. No new columns. That is WS-2.
- No backfill. No quarantine. Both are WS-2 and both are unsafe until 1.1 lands.
- Small, separately revertable commits. One per numbered item.
- A regression test for 1.1: run the wizard path, assert zero edges with NULL
  source_platform.

## Exit criteria

- Zero NEW edges with NULL source_platform (verified by test, not by inspection)
- Line-362-path edges carry structured derivation properties
- Every new LLM-derived edge carries a full derivation payload
- ./ws1/edge_write_paths.md complete and reviewed
- ./ws1/scope_decision.md answered or explicitly deferred with a reason
- 1.3 either cleared, or escalated and WS-1 halted

## Working discipline

Verify each claim against the code before stating it. Show the query or the file
and line behind every number. Where something cannot be determined, say so.
```

---

## WS-2 — Make warrant structural

```text
# Task: WS-2 — persist evidence tier at write time and retire fabricated edges

## Precondition — verify before starting

WS-1 must be complete. Specifically:
  - zero new edges written with NULL source_platform
  - ./ws1/edge_write_paths.md exists and is reviewed
  - WS-1.3 cleared (not escalated)

If any is unmet, STOP. Quarantining NULL-source rows while a writer is still live
creates a silent data-loss channel: the graph sheds rows into a bucket that is by
design not surfaced, and the quarantine conceals the bug instead of containing it.

## 2a — schema

  evidence_tier   CLOSED enum, NOT NULL: observed | asserted | inferred | unknown
                  The ONLY field consumers branch on. Keep it small deliberately.

  derivation      OPEN, conventioned string: wizard_a.arc_template,
                  wizard_a.trajectory_pattern, llm.enrichment.v3, linker.lifecycle,
                  crm.playbook_exec. Never branched on — displayed, logged, audited.

  confidence      NULL for inferred edges. Not clamped. Nothing was computed, so no
                  number is emitted. Expect this to break downstream sorts and
                  aggregates — that is intended, and it breaks loudly at dev time.

  template_base   The hand-authored plausibility value. NOTE: do NOT name this
                  template_plausibility if it will also carry the trajectory
                  classifier's value — that one is base + a computed delta, so the
                  name would misdescribe it. Either give the two sources separate
                  fields, or name it neutrally and record which in `derivation`.

A closed enum on `derivation` is what produced the original template|llm|correlation
mis-fit. Twelve source values already exist and more will follow. Closed set for
what drives behaviour; open set for what drives explanation.

## 2b — the adjudication matrix — REQUIRES HUMAN REVIEW

Adjudicate (source_platform × edge_type), NOT source_platform alone. Confirmed in
the data — one source emits different warrants:

  playbook_execution  ->  LED_TO 941 · RESULTED_IN 198
  csv_import          ->  LED_TO 1086 · TRIGGERED 732 · CAUSED_BY 1
  wizard_a            ->  LED_TO 1512 · TRIGGERED 193 · CAUSED_BY 144

Worked examples:
  playbook_execution × TRIGGERED  -> OBSERVED. The playbook fired at T, its condition
                                     referenced signal Y. A logged system action.
  playbook_execution × RESULTED_IN-> INFERRED. "protected $X" is an attribution.
  csv_import × factual claim      -> ASSERTED. A human uploaded it; not observed.
  csv_import × causal claim       -> ASSERTED. Still not observed.
  wizard_a × TRIGGERED            -> INFERRED. Asserts causation into an inferred
                                     object (the arc classification itself).

Enumerate every populated cell using ./ws1/edge_write_paths.md. Roughly 20-25.

*** GATE ***
Write the proposed matrix to ./ws2/adjudication_matrix.md with a one-line
justification per cell, and STOP for human review. These are epistemic judgments
with customer-facing consequences; they are not an engineering call. Do not backfill
on an unreviewed matrix.

## 2c — enforcement

EdgeFactory() as the sanctioned constructor, raw ContextEdge init guarded.

BUT: the Python factory is necessary and NOT sufficient. At least one ingestion path
(signal_edges.csv) writes raw SQL and bypasses the ORM entirely. The NOT NULL
DATABASE CONSTRAINT is the actual control — the only mechanism that governs every
writer regardless of language or layer. Ship the constraint. Treat the factory as
ergonomics.

## 2d — backfill, with a dry run

1. DRY RUN first: compute the tier every existing row WOULD receive, write the
   distribution and a sample diff to ./ws2/backfill_preview.md. Do not commit.
2. Human review of the preview.
3. Then backfill.

source_platform stays untouched, so tier is always re-derivable — that is the
rollback path. State it explicitly in the PR.

## 2e — quarantine

The 724 NULL-source rows: excluded from Evidence Density denominators and from
get_causal_chain traversal by default, reachable only behind an explicit audit flag.

They cannot be adjudicated — a row that never recorded its source cannot have one
reconstructed. Quarantine rather than tier, and never default unknown to observed.
That single fallback would be the most damaging line of code available in this
change.

## 2f — extend Invariant I3' to edges, AND close its csv_import blind spot

I3' currently clamps unearned confidence on OUTCOME nodes written via llm_enrichment.
It is working and self-documenting — the clamp reason string is a good model.

It does NOT fire on csv_import. Live example: a node titled "Revenue at Risk" with
revenue_impact -4,100,000, source_platform csv_import, source "observed", tier 1,
confidence 1, and properties {"evidence": "", "confidence": ""} — empty evidence, top
tier, on the largest revenue-bearing node in that account.

Extending the clamp to edges while leaving the largest hole open on nodes is the
wrong order of work. Do both.

## 2g — supersession

When an observed or asserted edge arrives for a (from_node_id, to_node_id, edge_type)
triple that already carries an inferred edge, set superseded_by on the inferred one.
Superseded rows stay in the table for audit and drop out of every surface and every
denominator.

Without this the graph accumulates contradictory parallel claims — confirmed live:
two LED_TO edges between the same node pair, one wizard_a at 0.65, one llm_enrichment
at 0.85, with contradictory labels, both active. get_causal_chain returns that node
pair twice, so anything aggregating over a chain double-counts.

## Exit criteria

- NOT NULL constraint live; no unguarded constructor remains in ANY language
- Adjudication matrix reviewed and signed off before backfill ran
- Backfill complete; every live edge carries a tier; rollback path documented
- Quarantine populated and excluded from all reported denominators
- I3' extended to edges AND firing on csv_import nodes
- Supersession implemented with a test

## Constraints

- Backfill is reversible via source_platform. Verify that claim, don't assume it.
- Expect NULL-confidence breakage downstream. Budget for it; do not paper over it
  by writing a placeholder number.
- No surface changes — Mermaid, causal chain output and metrics are WS-3.
```

---

## Sequencing across all four

```
WS-1  ████                                     2-3 days   unblocked now
worldgen  ████████████                         parallel   no dependency
WS-2       ░░░░████████████████                blocked by WS-1
FCI spike                    ░░░░░░░░████      blocked by worldgen
```

WS-3 (surfaces and metrics) follows WS-2. WS-4 (disclosure) runs alongside everything and gates only external communication.
