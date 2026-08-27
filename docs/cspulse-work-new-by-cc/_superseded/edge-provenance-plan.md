# Edge Provenance Remediation — Sequenced Plan

**Scope:** `ContextEdge` provenance across the CS Pulse context graph.
**Baseline:** 10,419 edges. 63% machine-inferred (`llm_enrichment` 45%, `wizard_a` 18%). 724 rows with no source, written by a live path. LLM-derived edges carry no reproducible derivation.

---

## The two corrections that reorder the work

**1. Fix the writer before quarantining the NULLs.**
Quarantine was proposed against a fixed legacy set. `wizards/wizard_a_journey_db.py:362` is still writing untagged `TRIGGERED` edges — 724 rows spanning 2026-04-09 to 2026-08-12, roughly six a day. Quarantined edges are by design not surfaced, so quarantining before fixing the writer creates a **silent data-loss channel**: the graph keeps shedding edges into an invisible bucket and the quarantine conceals the bug instead of containing it.

**2. Workstream 3 has no backward half.**
Model id and prompt version cannot be recovered from edges that never recorded them. The 4,663 existing `llm_enrichment` edges keep their tier — they are correctly `inferred` — but permanently lack derivation. The forward half (log it from now on) is cheap and moves into WS-1. The backward half closes as not-possible and is replaced by a disclosure decision.

Do not merge the 724 NULLs and the 4,663 LLM edges into a single "52% unadjudicatable" figure. They are different failures: the NULLs have **no assignable tier**; the LLM edges have a correct tier and **no reproducible derivation**. Evidence Density is unaffected by the second. Overstating this would be the same error the project exists to remove.

---

## WS-1 · Stop the bleeding
**Blocks WS-2. Est. 2–3 days.**

| # | Task | Notes |
|---|---|---|
| 1.1 | Fix `wizards/wizard_a_journey_db.py:362` | Route through `upsert_edge()` as its sibling path already does — not a one-off `source_platform=` assignment |
| 1.2 | Verify what `arc_confidence` actually is at that call site | If it originates in `classify_arc()`'s rule cascade it is a **rule-match score**, being written into a field consumers read as epistemic confidence in a causal claim. Third instance of the same overloading if so |
| 1.3 | Sweep for sibling raw `ContextEdge(...)` constructors | Produce a **complete written inventory of every edge write path**, ORM and raw SQL alike. This inventory is the input to WS-2 and is not optional |
| 1.4 | Forward-only LLM derivation logging in `llm/tier1_inference.py` | Write `model_id`, `prompt_version`, `input_node_ids`, `inferred_at` into `properties`. Ships here, not in a later workstream — every day it slips adds unreproducible edges at the rate of the largest single source |

**Exit criteria**
- Zero new edges written with NULL `source_platform`
- Every new LLM-derived edge carries a full derivation payload
- Write-path inventory complete and reviewed

---

## WS-2 · Make warrant structural
**Blocked by WS-1. Est. 1.5–2 weeks.**

### 2a. Schema

| Field | Shape | Rule |
|---|---|---|
| `evidence_tier` | **Closed** enum, `NOT NULL` — `observed` \| `asserted` \| `inferred` \| `unknown` | The only field any consumer branches on. Stays small deliberately |
| `derivation` | **Open**, conventioned string — `wizard_a.arc_template`, `llm.enrichment.v3`, `linker.lifecycle`, `crm.playbook_exec` | Never branched on. Displayed, logged, audited |
| `confidence` | Existing | **NULL** for inferred edges — not clamped. Nothing was computed, so no number is emitted |
| `template_plausibility` | New, optional | Carries the hand-authored value. Never lands in a field named *confidence* |

A closed enum on `derivation` is what produced the original `template \| llm \| correlation` mis-fit: twelve source values already exist and more will follow. Closed set for what drives behaviour, open set for what drives explanation.

### 2b. The adjudication matrix

Adjudicate **(`source_platform` × `edge_type`)**, not `source_platform` alone. Confirmed in the data — the same source emits different warrants:

```
playbook_execution  →  LED_TO 941 · RESULTED_IN 198
csv_import          →  LED_TO 1086 · TRIGGERED 732 · CAUSED_BY 1
wizard_a            →  LED_TO 1512 · TRIGGERED 193 · CAUSED_BY 144
```

Worked examples for the adjudication:

- `playbook_execution` × `TRIGGERED` — the playbook fired at time T and its condition referenced signal Y. **Observed.**
- `playbook_execution` × `RESULTED_IN` — this execution protected $X of revenue. **Attribution, therefore inferred.**
- `csv_import` × factual claim — "champion departed 2026-03-14." **Asserted.**
- `csv_import` × causal claim — "champion departure caused renewal risk." **Asserted-causal**, still not observed.
- `wizard_a` × `TRIGGERED` (line 362 path) — an edge asserting causation into an *inferred* object (the arc classification). Whatever tier it receives, it is not `observed`.

Only populated cells need adjudicating — roughly 20–25.

### 2c. Enforcement

`EdgeFactory()` as the only sanctioned constructor, with the raw `ContextEdge` init guarded.

> **The Python factory is necessary but not sufficient.** At least one ingestion path (`signal_edges.csv`) writes via raw SQL and bypasses the ORM entirely. **The `NOT NULL` database constraint is the actual control** — it is the only mechanism that governs every writer regardless of language or layer. Ship the constraint; treat the factory as ergonomics.

### 2d. Backfill and quarantine

- Backfill existing rows through the adjudication matrix
- Quarantine the 724 NULL-source rows — excluded from Evidence Density denominators and from `get_causal_chain` traversal by default, reachable only under an explicit audit flag
- Extend Invariant I3′ (unearned-confidence clamp + `event=unearned_confidence_clamp` log) from nodes to edges

**Exit criteria**
- `NOT NULL` constraint live; no unguarded constructor call sites remain in any language
- Backfill complete; every edge carries a tier
- Quarantine populated and excluded from all reported denominators

---

## WS-3 · Surface it
**Blocked by WS-2. Est. ~1 week.**

| Surface | Change |
|---|---|
| `get_context_graph_mermaid` | **Always show, never hide.** Dashed + gray for inferred, with `(inferred)` in the label **text** so it survives a screenshot. Graph-level banner: *"0 observed edges — all 23 template-inferred."* Do **not** port `_is_narrative_only`'s default-hide: hiding a node is additive, hiding an edge is topological — suppressing edges on a template-only graph renders disconnected nodes |
| `get_causal_chain` | `evidence_tier` per hop; a **pre-composed `assertion` string** so the honest phrasing is the data rather than a request to the model; top-level `chain_warrant: partially_inferred` |
| `get_graph_summary` | **Evidence Density** (observed ÷ total causal edges) and **Derivation Completeness** (inferred edges carrying a reproducible derivation), plus the full tier split |
| `get_platform_instructions` | One provenance line, in the style of the existing revenue rules — explicitly belt-and-braces, **not** the control. A prompt-layer guardrail is the weakest tier available and IMDA's May 2026 update ranks structural and rule-based controls above it |

### The two metrics

**Evidence Density** answers *how much of this graph is observed*. **Derivation Completeness** answers *whether the inferred remainder is defensible* — currently ~0% for `llm_enrichment`, ~100% for `wizard_a`, since a template id points to a specific reproducible line.

Two numbers, two distinct failures. The second also gives WS-1.4 a target that visibly moves, and it stops Wizard A being miscast as the sole villain — on derivation completeness the templates are the good citizen.

### Regression guard

Golden case: provision a customer with zero uploaded signal edges, then assert `evidence_density == 0` **and** that no surface renders an unmarked causal edge. This is what keeps the fix from silently reverting under two quarters of feature work.

---

## WS-4 · Disclosure decision
**No dependencies. Not an engineering task — product / leadership owns it.**

The 4,663 `llm_enrichment` edges keep their tier and permanently lack derivation. Tier-level honesty survives; edge-level defensibility does not. If an auditor points at a specific edge and asks how it was derived, the answer for 45% of the graph is *we cannot tell you*.

Decide, before anyone quotes a number externally:

1. How this is stated to customers and auditors
2. Whether Evidence Density is published per-account or portfolio-only — 711 of 746 accounts are **mixed**, so no one can eyeball the ratio for any given account
3. Whether the white paper reports the pre-remediation baseline (recommended — the audit is the story, and an unflattering number that a vendor published about itself is the cheapest credibility available)

---

## Still unverified

In the spirit of the exercise — assumptions this plan rests on that nobody has checked yet:

- **Write paths outside this codebase.** Migrations, ops scripts, and the raw-SQL CSV ingestion. The DB constraint covers them; the inventory in WS-1.3 is what confirms there are no others
- **Downstream NULL-tolerance.** Anything that sorts, filters, or aggregates on `confidence` will meet NULL for the first time. Expected to break loudly at dev time — that is the intent, but it should be budgeted
- **Per-account density on the accounts that actually demo.** Aurora GPU Cloud (393) and Titan Hyperscale Labs live on EC2 and were not reachable during the audit. Not a design input — nothing here changes based on it — but it *is* demo-readiness, and it should be checked deliberately from a stable path as part of WS-3's regression work, not via an ad-hoc security-group change
- **Whether `TRIGGERED` from line 362 should exist at all**, independent of how it is tiered

---

## Sequence

```
WS-1  Stop the bleeding        ██████                    (2–3 days)
WS-2  Make warrant structural        ████████████████    (1.5–2 wks)
WS-3  Surface it                                 ██████  (~1 wk)
WS-4  Disclosure decision      ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓  (parallel)
```

WS-1 blocks WS-2 because quarantine is unsafe while the writer is live. WS-2 blocks WS-3 because there is nothing to surface without a tier. WS-4 runs alongside and gates only external communication.

---

## A note on the estimate's history

Half a day → a day and a half → four workstreams. Every expansion came from a check rather than a reconsideration: query the source distribution, and the problem is 2.5× larger than the component under discussion; check whether LLM edges log derivation, and they don't; check whether the NULLs are legacy, and they aren't.

That pattern is the white paper. The story is not *we found a bug* — it is *every time we checked instead of assuming, the problem was larger and more specific than the assumption.*
