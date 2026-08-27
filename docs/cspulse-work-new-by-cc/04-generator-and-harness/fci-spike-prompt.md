# FCI feasibility spike — Claude Code prompt

**Status:** this is the STRATIFIED version. An earlier version in conversation assumed a single vertical — it is superseded and should not be used. Vertical is the largest confounder in the dataset; pooling verticals manufactures spurious edges.

**Sequencing:** do not run this against manifest-generated tenants. Manifests specify `arc_types` as an input, so discovery on manifest data recovers the manifests — a circular result that looks like a triumphant validation and means nothing. Run this only after `synthetic_worldgen_v1` can produce a world whose ground-truth DAG contradicts `ARC_TEMPLATES`, or against genuinely real tenant data.

**What this is:** an investigation that answers two questions — is the signal vocabulary dense enough for causal discovery per vertical, and how far are the current templates from what the data supports. It implements nothing.

---

```text
# Task: FCI feasibility spike — can we learn the causal schema that ARC_TEMPLATES asserts?
# STRATIFIED BY VERTICAL. Read Phase 0.5 before writing any analysis code.

## Context

Wizard A generates ContextEdge rows from a static ARC_TEMPLATES dict. Templates bind
slots by POSITION (signal:1, signal:2), not by meaning, so an arc's label lands on
whatever signal occupies that slot. Confirmed cases exist where a champion-departure
narrative was written onto a GPU-utilisation collapse.

We want to know whether that schema can instead be LEARNED from the account
population using constraint-based causal discovery (PC-stable, FCI).

This spike does not implement anything. It answers whether it is possible, per
vertical, and quantifies how far the templates are from what the data supports.

## Hard constraints

- READ-ONLY against the database. No writes to context_edges, context_nodes,
  accounts, customer_config — not even in a rolled-back transaction.
- Do not modify arc_edge_generator.py, arc_classifier.py, or any wizard code.
- All output to ./fci_spike/. Nothing enters the platform.
- Use a venv; do not install into the production environment.
- If any result contradicts an assumption stated here, STOP and report rather than
  working around it. The assumptions in this prompt are unverified.

## Phase 0 — environment

Confirm `causal-learn` installs. If not, STOP and report — do not hand-roll PC or FCI.
Record the version.

## Phase 0.5 — VERTICAL CENSUS (do this first; it may change everything)

The platform has at least four verticals: datacenter_v1, dc2_s, saas_premium,
healthcare_provider. They have different KPI catalogues, different pillar structures,
and almost certainly different signal-type vocabularies. datacenter_v1 and dc2_s are
BOTH datacenter and still have different pillars — do not merge them.

Produce, for the local DB:
  - customers per vertical, accounts per vertical, accounts with >=2 signals per vertical
  - distinct signal_type count per vertical
  - the overlap matrix: how many signal types are shared between each pair of verticals
  - how many tenants are manifest-generated vs real, if that is recorded at all

CRITICAL: never pool verticals into one analysis matrix. If vertical A's accounts
carry signal types X,Y and vertical B's carry P,Q, then X and Y appear correlated
purely because both are present in A and absent in B. Vertical is the largest
confounder in this dataset. Every subsequent phase runs PER VERTICAL.

Report which verticals have >= 200 accounts with >= 2 signals. Those are the only
ones eligible for discovery. Say plainly which are too small and skip them.

## Phase 1 — feasibility gate, PER ELIGIBLE VERTICAL

Within each eligible vertical:
1. distinct signal_type values
2. per type: how many accounts have at least one (prevalence)
3. per type-pair: how many accounts have BOTH
4. distribution of those pair counts

GATE, evaluated per vertical:
  - how many types appear in >= 15% of that vertical's accounts?
  - how many type-pairs co-occur in >= 30 accounts?

If fewer than ~12 types clear 15% in a vertical, raw types are too sparse there.
Propose an aggregation into 12-20 semantic groups FOR THAT VERTICAL, write it to
./fci_spike/<vertical>/type_grouping.md, and STOP for human review. Do not invent
a grouping and proceed on it. Groupings may differ between verticals — that is fine
and expected.

## Phase 2 — analysis matrix, per vertical

One row per account, one binary column per signal type (or group). Also emit, per
type, the median days from account start to first occurrence — the temporal ordering.

Save ./fci_spike/<vertical>/matrix.csv. Report accounts included, excluded, and why.

## Phase 3 — discovery, per vertical

Using causal-learn:
1. PC-stable, alpha=0.01, chi-square/G-square test, max conditioning set 3, with the
   Phase 2 temporal ordering supplied as background knowledge.
2. FCI, same settings.
3. Bootstrap PC-stable over 200 account resamples; per edge record presence fraction
   and orientation fraction each way.

Save CPDAG, PAG and bootstrap table per vertical.

## Phase 4 — compare to ARC_TEMPLATES

First determine whether ARC_TEMPLATES is universal or vertical-scoped, and say which.
If universal, that is itself a finding to report prominently.

Extract every template edge as (from_type, to_type, edge_type, typed_confidence,
typed_lag_days). For each, classify AGAINST EACH VERTICAL's learned result:
  SUPPORTED | UNSUPPORTED | REVERSED | CONFOUNDED (FCI <-> or o->) | UNTESTABLE

Also compare typed lag_days against the OBSERVED median lag and IQR per vertical.

## Phase 5 — CROSS-VERTICAL COMPARISON

Compare the learned schemas against each other:
  - edges found in EVERY eligible vertical  -> candidate universal CS dynamics
  - edges found in exactly one              -> vertical-specific
  - edges found in one and CONTRADICTED in another -> report loudly; a universal
    template cannot be correct for both

## Phase 6 — report

./fci_spike/FINDINGS.md:
- Phase 0.5 census; which verticals were eligible and which were skipped
- Per-vertical gate numbers and whether aggregation was required
- Per-vertical Phase 4 counts, naming every REVERSED and CONFOUNDED template edge
- Typed-vs-observed lag comparison per vertical
- The Phase 5 universal / vertical-specific / contradictory split
- Learned edges present in no template (what the templates miss)
- What this spike could NOT determine, and why

Report findings only. No implementation recommendations.

## Stop conditions

- causal-learn will not install
- no vertical has >= 200 accounts with >= 2 signals
- a vertical's Phase 1 gate fails (report the grouping proposal, do not proceed)
- any step would require a database write

## Working discipline

Verify each claim against the data before stating it. Show the query behind every
number. Where the data cannot answer something, say so rather than estimating.
```

---

## Notes on why it is built this way

**The Phase 1 gate is the real deliverable.** Customer 390 has 24 signal types across 12 accounts, with 54% appearing in exactly one account. If that sparsity holds at scale, discovery over raw types is impossible and the answer is an aggregation layer — a different project. Better to learn that in a day than after two weeks of implementation.

**Phase 4 is what justifies the remediation.** A count of how many `ARC_TEMPLATES` edges come back UNSUPPORTED, REVERSED or CONFOUNDED is the evidence for the whole programme, and the typed-vs-observed lag comparison gives the concrete "we assert 30 days, the data says 47" that convinces anyone who has not followed the analysis.

**Read-only, stated four times.** Once discovery produces a schema there is a strong pull to write it into `context_edges`. That table still has an untagged writer at `wizards/wizard_a_journey_db.py:362` and no `evidence_tier` column. Adding a fourth edge source before those are fixed makes provenance worse, not better.

**Realistic risk.** After stratifying, no vertical may clear 200 accounts. If so the honest conclusion is "discovery is viable for one vertical only; the rest stay on templates until they have population" — and that is a finding worth having early.
