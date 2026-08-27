# WS-2 2b — adjudication matrix (v3 — SIGNED with four holds, 2026-08-24)

## v3 — reviewer sign-off and holds

**SIGNED as-is:** cells 4–13, 15–21, cell 22's xfail treatment, both zero-row writers, and the aggregate-honesty conclusion (including the refusal to re-adjudicate heuristics upward). WS-2 engineering (2a/2c/2f/2g) is unblocked for the signed cells.

**Hold 1 — cell 14: SIGNED as `observed`, with two conditions.** (a) `derivation` must distinguish `system.self` (the platform reacting to its own inference — auto-trigger) from `system.external` (a genuinely external logged fact — SoR sync, recorded trigger conditions); (b) **Evidence Density is defined over `system.external` observed only** — otherwise the metric climbs every time we ship more auto-triggers, gaming itself by construction. DB-checked: all 3 rows were orphaned and are now gone — cell 14 is a **pure forward decision**, zero existing rows affected.

**Hold 2 — cells 1–3: HELD.** `asserted` is not determinable at write time — the platform cannot distinguish the load-driver from a human (same API, same credentials class). The tier becomes meaningful only after (i) a `data_origin` field capturing the **authenticated principal** at upload time lands in the write path (added to WS-2 2a's schema list), and (ii) rows start arriving with it. **Interim: csv-path writers stamp `unknown`**, the honest tier for "someone claimed this and we can't say who."

**Hold 3 — orphan deletion: sequence critique accepted.** Right outcome, wrong order — the guard should have been built and verified against the known-dirty state *before* deletion, not after. That's not recoverable (the dirt is gone). What shipped in response: the **join-through-customers guard now exists as tracer's `orphan_scan` probe** — platform-wide, every integer `customer_id`/`account_id` column joined through its parent plus dangling edge endpoints, deterministic zero expectation, runs on every tracer invocation. First live run: 76 table.columns scanned, zero orphans, MATCH. The probe's docstring records the sequencing critique so the next cleanup doesn't repeat it.

**Hold 4 — RESOLVED per reviewer direction (2026-08-24, `74596361b`): stop the writer, mark the residue, let 2c clean it.** The reviewer rejected all three offered options: (b) and (c) collapse into each other until 2c ships (regeneration re-runs the same unchanged writer), and (a) is a half-fix — NULLing confidence without stamping `evidence_tier` produces rows that are neither confidently-wrong nor honestly-labelled, handing unaudited NULL-handling to every downstream reader (the same second-order-trap shape as pillar-names-fixed/mapping-wrong and Growth-deduped/pillar_investments-not). Executed instead: **the close-linker now ABSTAINS** — no RESULTED_IN (typed 1.0) or LED_TO (typed 0.7) heuristic edges written on playbook close; the OUTCOME node (real economics) still writes. This caps the set: the decision was never "what about these 115" but "these 115 plus however many more accumulate." Residue takes (c) **with a marker**: `tests/test_playbook_close_edge_abstention.py` — a static AST guard against the writer's return, plus an `xfail(strict=True)` residue test (item-22 convention) carrying the 115 count, flipping when 2c re-tiers and erroring loudly on an unexpected pass (which also catches a quiet UPDATE).

## v4 — remaining review responses (2026-08-24)

**Hold 3 follow-up — the detector has now been observed detecting.** The reviewer's critique was exact: a probe that has only ever passed against a clean DB manufactures confidence (the VerticalTemplate class — a query that always "succeeded" because it never ran). "Unrecoverable" was overstated: `tracer tests/test_orphan_scan_detects.py` (tracer `78ccadb`) constructs its own dirt — inside single transactions it DROPs the relevant cascade FK, INSERTs a genuinely orphaned row, runs the probe's own fetch/verdict against the uncommitted state, and rolls back. Verified against live EC2: clean-DB → MATCH, planted dangling edge → **MISMATCH**, planted customer-orphan row → **MISMATCH**, rollback leaves zero trace. The probe's stub-ctx design is deliberate (uncommitted dirt is invisible to the auditor's read-only connection; the test validates detection *logic*, while AT-2 read-only enforcement is validated separately).

**Hold 1 follow-up — conditions are now tests, not prose.** `tests/test_evidence_density_contract.py`: dormant (skip) until `utils/evidence_density.py` / `utils/edge_factory.py` exist, binding the moment they do — Evidence Density's observed denominator must exclude `system.self`, and the auto-trigger derivation the factory stamps must live under `system.self`. Conventional module homes are named in the test docstring; building the metric elsewhere without the exports is itself the violation.

**Hold 2 follow-up — `unknown` vs quarantine kept distinct, recorded as a 2c requirement:** `unknown` is a *tier* meaning "we know the path, not the principal" (csv-path interim until `data_origin` lands); quarantine is *exclusion* meaning "nothing can be reconstructed" (the NULL-source rows). They must never share a representation — if they blur, the 49 remaining NULL-source rows stop being distinguishable from the csv path's interim state. 2c's schema work owns the test.

**Status: PROPOSED. Per the WS-2 gate, no backfill/enforcement runs on this until a human signs off.** (Note the standing scope cut: the backfill half of WS-2 is removed — tenant data is disposable — so what this matrix actually governs is the tier every cell's writer stamps on **new** edges, plus quarantine/display decisions. That lowers the stakes of a wrong cell, but the epistemic calls below are still yours to confirm, not mine.)

Cell counts are from the **live EC2 DB, 2026-08-22 evening** (9,369 edges total), not the plan's stale numbers. Vocabulary per the plan: `observed` (a logged system fact) · `asserted` (a human/customer claim, uploaded not observed) · `inferred` (a machine's guess — template, heuristic, or LLM) · quarantine for the un-adjudicable.

## v2 correction — reviewer challenge on the csv_import cells (2026-08-22)

The reviewer asked whether `signal_edges.csv` had ever actually been uploaded by anyone. It hasn't. DB-verified:

- **All 1,819 `csv_import` edges carry `created_by='process_data'` and originated from the load-driver's manifest-generated CSVs.** Zero rows from a human upload, ever. The upload path exists; only synthetic data has ever flowed through it.
- **1,664 of them (91.5%) are orphaned** — their 22 owning customers (April test tenants, cust 276–327) were deleted; the edges survived. The remaining 155 belong to customer 336, a stale eval tenant whose newest edge is June 9.
- Zooming out: **6,082 of all 9,369 edges (60%) are orphaned debris of deleted customers** — including 100% of the NULL bucket (635) and five entire cells (`reconciliation`, `auto_linker`, `lifecycle_linker`, `playbook_auto_trigger`, and effectively `csv_import`). The v1 aggregate percentages below were dominated by this debris.

**What this changes:** cells 1–3 keep `asserted` as the **forward write-time rule** — a row arriving through the upload path is a claim by whoever uploaded it, and the platform cannot verify the uploader's warrant (it also cannot distinguish a human from the load-driver; same API). But the matrix must not imply today's asserted rows are customer claims: **the entire current `asserted` population is synthetic demo data**, and any Evidence Density surface that reports an "asserted" bucket today is measuring the load-driver, not customers.

**Live-tenant graph (excluding orphans), the number that actually matters:** ~3,287 edges — llm_enrichment 2,002 · wizard_a 709 · playbook_execution 387 · csv_import 155 (all on stale tenant 336) · llm_inference 24 · urgent_signal_scanner 6 · signal_analyst 4 · **observed 0**. Freshness: only tenants 398–401 have edges newer than 4 days; 390–393 are 9–10 days old; 333–338/371 are weeks-to-months stale.

**Decision 3 — RESOLVED AND EXECUTED (2026-08-24, user-approved).** The user approved deleting all stale pre-390 customers (except ID 1) *and* the orphan cleanup. Executed with a full pg_dump backup first (`~/backups/cs_pulse_pre-delete-20260824-181143.sql.gz` on EBS + a local copy): tenants 333–338 + 371 fully removed (190 accounts, 30,568 KPI rows, 3,540 nodes, 3,190 health scores, 21 tables touched), then orphan cleanup removed 5,447 edges + 8,312 nodes belonging to already-deleted customers. **Post-state: 944 edges total, 0 orphans, 49 NULL-source rows remaining** — those 49 belong to LIVE tenants (pre-WS-1-fix wizard_a rows written without customer_id on 390–393; v2's "all 635 orphaned" claim was an artifact of the NULL-customer_id join and is corrected here). They self-heal when those tenants re-run Wizard A, or fall to WS-2 2e quarantine. Live tenants verified untouched (390: 12 accts/168 edges, 393: 12/188, 401: 2/16; logins 200; tracer 3/3 MATCH). **Still open from this decision: fixing the root cause — customer deletion doesn't cascade to context graph tables.** The v1/v2 cell counts above are now historical; re-enumerate against the 944-edge graph before stamping tiers in 2c.

## The matrix

| # | source_platform × edge_type | rows | proposed tier | justification (one line) |
|---|---|---|---|---|
| 1 | csv_import × LED_TO | 1,086 | **asserted** | human-uploaded causal claim (signal_edges.csv); uploaded, not observed — plan's worked example |
| 2 | csv_import × TRIGGERED | 732 | **asserted** | same — a human asserting causation doesn't make it observed |
| 3 | csv_import × CAUSED_BY | 1 | **asserted** | same |
| 4 | wizard_a × LED_TO | 1,327 | **inferred** | arc-template topology fill (narrative scaffolding) |
| 5 | wizard_a × TRIGGERED | 204 | **inferred** | asserts causation into an inferred object (the arc classification) — plan's worked example |
| 6 | wizard_a × CAUSED_BY | 132 | **inferred** | template fill, same as #4 |
| 7 | llm_enrichment × LED_TO | 1,665 | **inferred** | LLM causal claim over real signals |
| 8 | llm_enrichment × TRIGGERED | 1,302 | **inferred** | same |
| 9 | llm_enrichment × CAUSED_BY | 851 | **inferred** | same |
| 10 | llm_enrichment × AMPLIFIED | 205 | **inferred** | same |
| 11 | llm_inference × LED_TO | 91 | **inferred** | LLM full-inference mode — both endpoints AND the edge are LLM-invented; strictly weaker than llm_enrichment, distinction carried in `derivation` (llm.inference vs llm.enrichment), not a fourth tier |
| 12 | playbook_execution × RESULTED_IN | 179 | **inferred** | ⚠️ worse than the plan's example knew: not just "protected $X is an attribution" — the DECISION side is picked as *the account's most recent decision node*, a recency heuristic, stamped with a **typed confidence=1.0** (worst overloading instance found to date) |
| 13 | playbook_execution × LED_TO | 805 | **inferred** | close-linker attaches the **3 most recent** prior signals at a typed 0.7 — recency heuristic, not a logged trigger condition |
| 14 | playbook_auto_trigger × TRIGGERED | 3 | **observed** ← the one genuinely debatable cell | the system verifiably fired playbook X because arc-detection Y crossed its threshold — a logged system action (plan's worked example for a trigger). Counter-argument: the *from*-node is itself an inferred arc, so this "observes" a reaction to a guess. I propose observed-the-event; the from-node's own tier carries the guess. **Flag for explicit reviewer decision.** |
| 15 | playbook_auto_trigger × INVOLVES | 9 | **inferred** | stakeholder role-match heuristic (typed 0.8) |
| 16 | signal_analyst × LED_TO | 3 | **inferred** | runtime agent analysis over real signals |
| 17 | signal_analyst × TRIGGERED | 1 | **inferred** | same |
| 18 | urgent_signal_scanner × LED_TO | 48 | **inferred** | heuristic scanner linkage |
| 19 | auto_linker × LED_TO | 15 | **inferred** | recency+polarity heuristic (typed 0.7/0.75) |
| 20 | lifecycle_linker × LED_TO | 15 | **inferred** | defunct one-off repair script (`lifecycle_edge_fix`, code no longer exists) — adjudicate by what it did (heuristic linking), conservatively |
| 21 | reconciliation × LED_TO | 60 | **inferred** | defunct one-off repair script (`cg_reconcile`), same reasoning |
| 22 | NULL × TRIGGERED | 635 | **quarantine** | never recorded a source; cannot be reconstructed (WS-2 2e). Down from 724 — re-run tenants self-heal via wizard_a's stale-node cleanup (see WS-1 notes); never default to observed |

New writers with 0 rows yet (from WS-1 fixes) — tiers for their first rows:
| — | onboarding_provision × INVOLVES | 0 | **inferred** | role-match heuristic (typed 0.8, `confidence_semantics` recorded) |
| — | process_data × INVOLVES | 0 | **inferred** | same |

## Aggregate picture the reviewer should see before signing

Whole table (v1 numbers, debris included): observed 3 (0.03%) · asserted 1,819 (19.4%) · inferred 6,912 (73.8%) · quarantine 635 (6.8%).

**Live tenants only (the honest denominator, per the v2 correction): observed 0 · asserted 155 (4.7%, all synthetic, all on one stale eval tenant) · inferred ~3,132 (95.3%) · quarantine 0.**

- Under this matrix, **nothing in the live graph is "observed," and nothing in it was asserted by a human.** That is the honest state, and it is exactly what Evidence Density will report the day it ships. If that is commercially unacceptable, the fix is generating genuinely-logged edges (playbook trigger conditions recorded at fire time, SoR sync events) — not re-adjudicating heuristics upward.
- F3's finding (empty-evidence tier-1 revenue nodes from csv_import) means "asserted" must not be conflated with "verified" on any surface, whenever real uploads do start arriving.

## Two decisions folded in for explicit sign-off (not silently resolved)

1. **Cell 14** (playbook_auto_trigger × TRIGGERED): observed-the-event vs. inferred-because-the-cause-is-a-guess. Proposed: observed. 3 rows today, but the auto-trigger pipeline will grow it.
2. **Cell 12/13's typed constants**: adjudicating them `inferred` is necessary but not sufficient — WS-2 2a's rule "confidence NULL for inferred edges" will null out the fake 1.0/0.7 on **new** rows. Existing rows keep them until/unless the disposable-data stance says re-run instead.
