# CS Pulse — workstream handover

**Read `00-start-here/state-of-play.md` first.** It is verified against live endpoints (customer 390, 2026-08-22) and is the only document needed to re-enter the work. Everything else is detail for one track.

---

## Folders

| folder | what's in it | status |
|---|---|---|
| `00-start-here/` | current verified state, four tracks, one next action each | **read first — reassessed 2026-08-22** |
| `01-provenance-rendering/` | *(no document — the plan lives in state-of-play, track A)* | display treatment decided and shipped (`ProvenanceTierBadge`); composite-site wiring and the TS-type flip are next |
| `02-vertical-registry/` | registry architecture + the original audit | **DONE.** All six items (a-c, e-f) shipped, tested, deployed, on `main`; (d) is a deliberately-paused ratchet, tracked as backlog not incompleteness |
| `03-edge-provenance/` | WS-1 / WS-2 prompts, verification brief, current-vs-target diagram, `ws1/` deliverables | **WS-1 complete** (deployed, live-verified, 1.3 cleared); WS-2 unblocked, gated on adjudication-matrix human review |
| `04-generator-and-harness/` | generator refactor, ground-truth spec, tracer app, due-diligence checklist, FCI spike | **`tracer` (the audit harness half) is built, tested, and has already found real bugs live** — the generator-refactor half is untouched |
| `reference-code/` | runnable teaching code + the generated demo CSVs | reference only — not production code |
| `_superseded/` | **do not execute** — kept for provenance only | superseded |

---

## Suggested order — revised 2026-08-22 (evening)

Track B is closed. A and the Track D generator refactor can run in parallel next. C is independent of both and still unblocked.

**Done, not "next":** Track B — round-trip identity test (`tests/test_kpi_count_round_trip_identity.py`) and no-silent-substitution guard (`tests/test_catalog_no_silent_substitution.py`, plus a real fix in `load_catalog_from_json()`) both shipped, deployed to EC2, tracer-verified, merged to `main`. See `state-of-play.md`, Track B section.

**1 · Track A — provenance rendering** *(smallest net-new work, most CFO-visible)*
Decide display treatment first — it gates the render layer. Then wire `most_conservative()` into composite sites, then flip TS types one interface at a time in tier-diversity order. Details in `state-of-play.md`.

**2 · Track D — generator refactor** → `04-generator-and-harness/fix-load-generator-prompt.md`
The audit-harness half of this track (`tracer`) is done — see `state-of-play.md`. What's left is the generator: archive golden CSVs and write the byte-identical demo-profile test **before changing anything**. If the generator isn't deterministic today, stop and fix that first.

**3 · Track C — edge provenance** → `03-edge-provenance/ws1-ws2-prompts.md`
Start at WS-1 Step 0 (reconcile the line numbers). WS-1.3 has a **stop condition** — honour it.

**Already done, not "then":** `04-generator-and-harness/tracer-app-prompt.md` — the audit harness. Both AT-4 and AT-5 have fired against live data this session; AT-6 (`tracer diff`, same build → zero changes) also confirmed. Remaining gap is only the generator's `via_truth` mode, which needs the Track D generator refactor above first.

---

## Blocked / sequencing notes

- **`fci-spike-prompt.md` is blocked on the generator.** Manifests take `arc_types` as an input, so discovery run against manifest-generated tenants recovers the manifests — a circular result that looks like a successful validation. Do not run it until a world exists whose DAG contradicts `ARC_TEMPLATES`.
- **`_superseded/synthetic-worldgen-prompt.md`** said to build a second generator alongside the existing one. Replaced by `fix-load-generator-prompt.md`, which refactors in place. Its *architecture* section was right; its *non-goals* section contradicted it.
- **`_superseded/edge-provenance-plan.md`** is the earlier planning document. `ws1-ws2-prompts.md` supersedes it, with WS-2's backfill half removed since the tenant data is disposable.

---

## Terminology

**"Migration" means data only.** Everything in the registry refactor, and most of what remains in WS-2, is authoring and deleting code — no rows move, no rollback plan needed. Keeping those words apart stops the next scoping conversation from budgeting migration risk against a refactor.

---

## What each track is protecting against

Every defect found in this work is the same shape: **a value presented as something it isn't.** A typed constant shown as computed confidence. A benchmark default shown as this customer's NRR. Another vertical's config shown under this vertical's name. A fixed ARR multiple shown as account-level ROI. Gross Revenue Retention shown as Power & Facility impact.

The four tracks are four places that pattern lives. Conformance tests are what stop it recurring — Track B's are written now (round-trip identity, no-silent-substitution, role-gate, catalog-shape); A and C still need theirs.
