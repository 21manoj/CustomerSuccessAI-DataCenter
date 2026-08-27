# Three findings to verify before they enter the remediation plan

Taken from live API reads on customer 390 / account 3535 (Titan Hyperscale Labs). Each is stated as a **claim**, the **evidence** behind it, the **check** that would confirm or kill it, and what would **falsify** it. None of these should be added to the plan until the check has been run — that discipline is the only reason the previous four rounds found anything.

---

## F1 · Template narrative mismatch

**Claim.** Wizard A applies arc-template labels to node pairs that bear no semantic relationship to the label. This is a correctness defect, not a provenance one: a mislabeled edge with perfect provenance is still a false statement about the customer's business.

**Evidence.**

```
edge 72090   from: "Support ticket escalated to management"   (support_escalation)
             to:   "Reserved 1,000-GPU cluster utilization fell 65%→22%"  (reserved_cluster_idle)
             label: "Champion departure created engagement gap"
             arc_type: exec_sponsor_change   confidence: 0.85   source_platform: wizard_a
```

Titan has no champion-departure signal anywhere in its data. Three wizard_a edges on this account narrate a champion-loss story onto an incident/escalation/utilisation sequence.

**Root cause hypothesis.** `ARC_TEMPLATES` binds slots by **position** (`signal:1`, `signal:2`), not by meaning. Slot 1 gets the "champion departure" label whether or not the node in slot 1 is a champion departure.

**Check.**
1. Confirm the slot-binding in `arc_edge_generator.generate_edges()` — is `from`/`to` resolved by ordinal index into the account's signal list?
2. Across all accounts, count edges where `properties.arc_type` implies a signal subtype that does not appear anywhere in that account's signals. (For `exec_sponsor_change` / `champion_loss`: no `champion_*` or `*_departure` subtype present.)
3. Check whether `classify_arc()`'s low-health fallback rule assigns a champion arc to accounts with no champion signal — that rule would be the largest single generator of mismatches.

**Falsified if.** Templates resolve slots by matching subtype rather than position, and the Titan case turns out to be a single mis-authored template rather than a structural property.

**If confirmed.** This needs a fit check *before* an arc is applied, plus an abstention path. Tiering the output does not help — the statement is still false.

---

## F2 · No edge supersession on incremental load

**Claim.** When real `signal_edges.csv` data arrives in Month 2+, uploaded edges are inserted **beside** Wizard A's invented edges for the same node pair rather than replacing them. There is no retirement path, so Evidence Density can only improve by dilution, never by retirement.

**Evidence.** Two live edges on the same triple, from different writers, with contradictory labels:

```
72089:  124324 → 124325  LED_TO  conf 0.65  wizard_a         "Routine engagement before departure"
72225:  124324 → 124325  LED_TO  conf 0.85  llm_enrichment   "Critical incident triggered management escalation"
```

Same pattern again at `124326 → 124327` (72091 wizard_a / 72227 llm_enrichment).

**Side effect already observable.** `get_causal_chain` returns nodes 124325, 124327 and 124524 twice each — once per duplicate edge. Any consumer aggregating over a chain double-counts.

**Check.**
1. Read `upsert_edge()`'s conflict key. If it includes `source_platform`, every writer gets its own parallel edge by construction — that confirms the claim without needing a data query.
2. Count duplicated `(from_node_id, to_node_id, edge_type)` triples where `superseded_by IS NULL` across the whole graph, grouped by the set of source_platforms involved.
3. Find an account that has *both* wizard_a edges and genuinely uploaded `signal_edges.csv` rows, and check whether the template edges survived the upload.

**Falsified if.** `upsert_edge()` already deduplicates on `(from, to, type)` and the observed duplicates come from a path that bypasses it — in which case this is the same class of bug as line 362, not a missing feature.

**If confirmed.** Add a supersession rule to WS-2: an arriving `observed` or `asserted` edge sets `superseded_by` on any `inferred` edge for the same triple. Superseded rows stay in the table for audit and drop out of all surfaces and denominators.

---

## F3 · Invariant I3′ has a `csv_import` blind spot

**Claim.** The unearned-confidence clamp fires on `llm_enrichment` writes but trusts `csv_import` unconditionally — including on tier-1 revenue OUTCOMEs with empty evidence.

**Evidence.** The clamp working correctly:

```
node 124521  source_platform: llm_enrichment   confidence: 0.3   tier: 2
  evidence_clamped: true
  reason: "OUTCOME written via llm_enrichment with no properties.evidence and no
           source_ref — confidence clamped from 0.95 to 0.3, tier forced to 2"
```

The same conditions, not clamped:

```
node 124379  "Revenue at Risk — Titan Hyperscale Labs"   revenue_impact: -4,100,000
  source_platform: csv_import   source: "observed"   tier: 1   confidence: 1
  properties: {"evidence": "", "confidence": ""}
```

Empty evidence string, top tier, full confidence, on the largest revenue-bearing node in the account.

**Check.**
1. Read I3′'s trigger condition in `utils/context_graph.py` — is `source_platform` in an allowlist that exempts `csv_import`?
2. Count OUTCOME nodes where `source_platform='csv_import'`, `tier=1`, and `properties.evidence` is null or empty. Sum their `revenue_impact`. That sum is the revenue currently presented as evidence-backed on no evidence.
3. Check whether `_is_narrative_only()` catches these — it tests for missing `revenue_impact`, `source_ref` **and** `properties.evidence`. Node 124379 has a `source_ref` and a `revenue_impact`, so it likely passes the filter on two of three conditions while failing the one that matters.

**Falsified if.** `csv_import` OUTCOMEs are validated at ingestion instead, and the empty evidence string on 124379 is a single bad row rather than the norm.

**If confirmed.** This belongs in WS-2 alongside extending I3′ to edges — extending the clamp to a new object type while leaving the largest hole open on the existing one would be the wrong order of work.

---

## Note on sequencing

F1 is the most serious of the three and the least related to the rest of the plan. It is a **correctness** defect; F2 and F3 are **provenance** defects. If F1 confirms, it likely deserves its own workstream rather than a sub-task, because the remedy (arc fit checking plus an abstention path) has nothing in common with the tiering work.

F3 should be checked first regardless — it is a single read of one function's trigger condition and it directly affects how WS-2's I3′ extension is scoped.
