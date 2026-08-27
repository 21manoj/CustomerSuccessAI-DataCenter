# Item 23 — guards-never-fired sweep: gate inventory + firing triage

Phase 1 deliverable (2026-08-24). Every gate gets one of four statuses:
**FIRING** (live or paired-test evidence of exclusion), **DEAD** (no callers),
**NEVER-OBSERVED** (runs, but no evidence it has ever excluded anything —
needs a paired clean+dirty test), **FAIL-OPEN** (admits by default on the
edge case). The standard, per the reviewer: *a test proving it excludes
something — not that it runs, that it fires.*

## Confirmed FIRING (evidence cited)

| gate | where | firing evidence |
|---|---|---|
| I1/I2 pre-commit edge gate (`validate_edge_pre_commit`) | `context_graph_invariants.py:1257`, called from `upsert_edge` | Live rejection logs: `event=pre_commit_rejection` entries Aug 13 for both llm_enrichment and wizard_a producers ("I1: OUTCOME→OUTCOME edge rejected") |
| I3′ unearned-confidence clamp | `context_graph_invariants.py` / `upsert_node` | **179 nodes** carry clamp marks in `properties` on the live DB. (csv_import blind spot remains — 2f — the gate fires, on too narrow a population) |
| `is_trustworthy` / `TRUSTWORTHY_SOURCES` allow-list | `utils/provenance.py:40,76` | Fixed fail-closed `1f1916333`; first live firing observed: `dropped_synthetic` 0→38 (cust 390), 0→24 (400) |
| `count_trustworthy_causal_edges` | `utils/provenance.py` | Same — was structurally unable to fire (read a nonexistent attribute); now fires, see above |
| edge-confidence threshold (`is_trustworthy_edge`, 0.6) | `utils/provenance.py` | Paired unit test fires it (`confidence=0.5 → False`, `test_provenance.py:125,171`). Live `dropped_low_confidence=0` is a data fact (LLM writes 0.65–0.85), not a gate defect |
| pillar-role partner gate | `cs_pulse_admin.py::partner_portal` | Fired live on manufacturing_iot (401) — a vertical it had never seen — plus per-vertical tests |
| key scoping / auth gate | `mcp_server/auth.py` + `api_key_service` | Fired live TODAY: the reviewer's 390-scoped key rejected on 398/400 ("API key does not have access") — an authenticated observation of the gate excluding |
| tenant-cascade FKs | DB constraints | Fired by construction during cleanup (children cascade-deleted); planted-dirt-adjacent proof via functional test (raw DELETE → zero residue) |
| `orphan_scan` probe | tracer | Planted-dirt validation (tracer `78ccadb`): observed MISMATCH on a planted dangling edge and a planted customer-orphan, rollback clean |
| provenance-writers vocabulary guard | `tests/test_provenance_writers.py` | Fired in CI when green-ed (caught 4 legacy literals); guard-list gap (arc_decision_generator missing) fixed `1f1916333` |

## DEAD (no callers — decision needed, not a test)

| gate | where | finding |
|---|---|---|
| **`apply_node_source_filter`** | `utils/provenance.py:113` | **Zero production callers** — only its own unit tests import it. The *canonical* "exclude synthetic from reads" helper is used by nobody; readers roll their own ad-hoc lists instead (e.g. `signal_analyst.py:684` uses `.in_(['observed','customer'])` — which also silently excludes `inferred`, a different policy than the canon). Dead guard **#5**. Decision: adopt it at the reader sites (behavior change — each site's current ad-hoc list differs from the canon) or delete it and bless the ad-hoc lists with per-site tests. Do not leave a sanctioned-looking helper that nothing sanctions. |

## NEVER-OBSERVED (runs, no exclusion evidence — paired tests owed)

| gate | where | note |
|---|---|---|
| `ConfigValidator.validate_*` family | `utils/config_validator.py`, called from `dc2s_config_api` | Called on config save; no test proves a bad config is rejected end-to-end |
| `validate_arc` / `validate_all_arcs` | `utils/story_arc_loader.py` | Called at arc load; no test proves a malformed arc is refused rather than warn-and-loaded |
| `_ALLOWED_TOP_KEYS` taxonomy gate | `utils/taxonomy_loader.py:40` | Unknown-key detection; verify it rejects (or at least surfaces) rather than ignores |
| `_check_prerequisites` LLM gate policy | `llm/tier1_inference.py:37` | The 4-CSV/11-CSV default-on/off policy + kill switch; policy tests may exist — verify each branch excludes |
| `_check_mcp_enabled` feature gate | `mcp_server/*` | Fires when the toggle is off; needs one paired test |
| ad-hoc reader source lists | `signal_analyst.py:684` (+ any others) | Each needs either adoption of the canon or its own paired test; note the observed/customer list predates normalize() canonicalization |

## FAIL-OPEN register (found by this sweep's lens, tracked separately)

| site | behavior | status |
|---|---|---|
| `normalize(None) → 'observed'` | NULL trusted by default | **FIXED** `1f1916333` (fail-closed) |
| `is_trustworthy_edge(conf=None) → True` | NULL confidence passes the threshold gate | **KEEP, documented**: deliberate, and load-bearing for WS-2 2c (inferred edges will carry confidence=NULL meaning "no number emitted", which is not "low confidence"). The provenance gate (gate 1) is what excludes them when warranted. Revisit only if 2c changes the semantics. |
| `getattr(e, 'source', None)` on edges | read a nonexistent attribute | **FIXED** `1f1916333` (reads `source_platform`) |

## Phase 2 (next): write the paired tests for the NEVER-OBSERVED table, and take
the `apply_node_source_filter` adopt-vs-delete decision to the owner. The
dead-guard tally after this sweep: 5 confirmed (`VerticalTemplate`,
`is_reference`, `count_trustworthy_causal_edges`, `orphan_scan`-pre-validation,
`apply_node_source_filter`), of which 4 are now fixed/validated and 1 awaits
the adopt-vs-delete call.

## Sweep yield — first live defect (2026-08-24)

The reviewer's stop-and-flag on inconsistent 398 enforcement was correct, and
this is exactly the class item 23 hunts. A **28-tool enforcement matrix**
(390-scoped key vs `customer_id=398`, behavior-class only, payloads discarded):

- **1 LEAK — `get_kpi_catalog`**: returned 398's catalog to the 390 key. Gated
  with `require_read_key` (for parameterless discovery tools) despite taking a
  `customer_id`. **FIXED `5782e7afa`** — new `require_scoped_read`; matrix
  re-run **0 LEAK / 22 SCOPED**; discovery + in-scope paths verified intact.
- 21 SCOPED_REJECT — gate working (incl. `get_cfo_dashboard_summary`,
  matching the reviewer).
- 6 "ERROR" — false alarms: account-level tools that failed arg validation
  (harness didn't pass `account_id`) *before* any scope check. Not a scoping
  signal; a probe artifact — but note it means arg-validation runs before
  auth on those tools, worth its own look.

Reviewer cross-check reconciled: they saw `get_onboarding_ttfv_status(398)`
return data (server-level key, in scope) while `get_cfo_dashboard_summary(398)`
rejected (390 key) — a two-different-keys artifact, NOT a second leak. Under
one key (390), `get_onboarding_ttfv_status` correctly rejects. The only tool
that leaked under *either* key was `get_kpi_catalog`.

Dead/leaking-guard tally now **6**: VerticalTemplate, is_reference,
count_trustworthy_causal_edges, pre-validation orphan_scan,
apply_node_source_filter (dead), get_kpi_catalog scope gate (leaking) — 5
fixed/validated, 1 (apply_node_source_filter) awaiting the adopt-vs-delete call.
