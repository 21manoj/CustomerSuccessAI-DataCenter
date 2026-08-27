# Node-level evidence gap — v2, post-review (2026-08-24 evening)

v1's headline ("$457M / 360 nodes / 100%") is retracted per review: it summed a
real quantity with a category error and gave the total a precision neither half
supports — the audit's own defect, in the headline of the document diagnosing
it. **Two numbers, never their sum:**

## Number 1 — $203.7M of customer-uploaded revenue mistiered as observed
**257 OUTCOME nodes · source='observed' · tier=1 · confidence=1.00 (all 257) ·
evidence='' · csv_import.** Real money, false label: the dollars came from
customer CSVs; only the observed/tier-1/confidence-1 claim is fabricated.
Reaches the CFO/CRO/CEO headline aggregators (all OUTCOME-constrained, none
source-filtered — verified in `aggregate_revenue_across_accounts`,
`aggregate_revenue_with_provenance`, `get_revenue_at_risk`). Reviewer
independently confirmed tenant 390's $24.6M share from the CFO payload.

**⚠ Correction 3 executed — tenant 391 must not anchor this figure.** 391 is a
live demo tenant (Aug 13, 6 accounts), not load residue — but its pop-1 sum is
**$95.7M against $35.9M total tenant ARR: revenue-at-risk 2.7× the ARR it
could possibly threaten.** New data-quality finding (generator emits outcome
dollars unscaled to account ARR); 391 excluded from any anchoring; the robust
per-tenant range is $0.7M–$24.6M.

**Residue decision (recorded, not yet executed): re-tier to the Hold-2
interim, waiver taken** — correcting a label that was never true isn't the
migration the forward-only stance was written to prevent. Lands with 2a-N1
(which defines the interim representation for nodes) rather than as a naive
UPDATE inventing vocabulary ad hoc.

## Number 2 — 103 fabricated decision nodes carrying invented dollars — NOW RESOLVED
Not a money quantity: `revenue_impact` has no defined semantics on a DECISION
node, and the population was internally inflated — **22 of 103 rows repeated
an amount already counted in the same account** (the reviewer's Pacific
example — the same $5.2M on phase 2 and phase 3 of one arc — was systematic,
present on 7 of 8 tenants). Summing it measured nothing.

**Correction 2 confirmed and executed: falsely evidenced, not unevidenced.**
`evidence` was empty but `properties.evidence_refs` was populated on **103 of
103** — invented citations ("Reference call: similar customer achieved…")
that survive exactly the audit a reviewer would run. Fabricated corroboration
doesn't look like a gap; it looks like diligence.

**Also confirmed: the sign error.** The writer typed every positive figure
`at_risk` unconditionally — $5.2M expansion narratives filed as risk.

**Resolution (reviewer verdict "delete or regenerate; marking is the wrong
verb" — executed 2026-08-24, `1f1916333`):** writer fixed first
(source='synthetic', tier 2, no revenue_impact — manifest figure kept as
`proposed_value` which nothing sums, citations renamed `narrative_refs`,
typed 0.85 → NULL, writer added to the provenance guard list); Wizard A
re-run on all 8 tenants regenerated what templates still emit (side effect:
the last 49 NULL-source edges self-healed → **0 platform-wide**); the 119
legacy nodes the generator's early-return skipped were deleted, edges
cascading. **Post-state: 0 non-OUTCOME revenue nodes, 0 fabricated
evidence_refs, 0 legacy literals, platform-wide.**

## Correction 1 executed — reachability shown per population, not asserted
- **Pop 1 renders on the headline aggregators** (OUTCOME-constrained queries
  admit them; no source filter exists there).
- **Pop 2 never reached the headlines** (reviewer's $10.67M all-OUTCOME sample
  was correct) — but **did render on the ROI timeline**, whose revenue sum was
  the one aggregation missing the node_type constraint: **$20.8M fabricated
  at_risk on tenant 400, $27.7M on 398** (390 showed zero only because its
  data predates the 6-month window). Story-arc's per-decision
  `projected_impact` also displayed the figures. Timeline constrained to
  OUTCOME in `1f1916333`; before/after: 400 $20.84M → −$1.94M, 398 $27.73M →
  $3.19M, CFO control unchanged to the dollar ($10,670,000).

## The gate, empirically settled — reviewer right, mechanism different
`TRUSTWORTHY_SOURCES` was already an allow-list (v1's deny-list claim was
wrong). But the reviewer's "never excluded template fabrication" was **true
anyway**: `count_trustworthy_causal_edges` read `edge.source` — **an attribute
ContextEdge does not have** — so getattr returned None, `normalize(None)` →
`'observed'`, and every edge was admitted. `dropped_synthetic` was
structurally ALWAYS ZERO; the pre-existing unit test encoded the fail-open as
intended behavior ("null → trust"). Fixed: `normalize` fail-closed (None stays
None, untrusted), the counter reads `source_platform` per the signed matrix,
tests updated to the fail-closed contract. **First firing ever observed,
live: dropped_synthetic 0 → 38 (cust 390), 0 → 24 (400).**

## Escalation — the guards-never-fired sweep (numbered work item)
Four confirmed members of the class, all found incidentally:
1. `VerticalTemplate` query — always excepts, silently
2. `is_reference`/`reference_for` — same shape
3. `count_trustworthy_causal_edges` — reads a nonexistent attribute; gate
   structurally cannot fire (empirically confirmed above)
4. `orphan_scan` — was a detector never observed detecting (now validated by
   planted dirt, tracer `78ccadb`)

**Work item (state-of-play backlog): every filter, allow/deny list, and
validation branch gets a test proving it excludes something** — not that it
runs, that it *fires*. On current evidence this sweep out-yields 2a.
