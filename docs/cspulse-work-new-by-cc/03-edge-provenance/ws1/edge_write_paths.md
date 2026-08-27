# WS-1.4 — context_edges write-path inventory

Every code path that creates a `context_edges` row, as of 2026-08-22 (post WS-1.1 fixes). This is the input to WS-2's adjudication matrix.

Legend: **via upsert_edge** = routes through the sanctioned constructor (`utils/context_graph.py:upsert_edge`, which enforces the I1/I2/I4 pre-commit invariant gate and dedup-by-(from,to,type,source_platform)). Raw = direct `ContextEdge(...)` constructor or raw SQL, bypassing the gate.

## Application writers

| # | file:line | function | source_platform | edge_types | via upsert_edge |
|---|---|---|---|---|---|
| 1 | `wizards/wizard_a_journey_db.py:366` | journey builder (arc-detection link) | `wizard_a` | TRIGGERED | ✅ **fixed in WS-1.1** — was raw, NO source_platform (the 724-NULL-row writer) |
| 2 | `utils/arc_edge_generator.py:418` | `generate_edges` | `wizard_a` | LED_TO, TRIGGERED, CAUSED_BY (template topology) | ✅ (since Apr 2026) |
| 3 | `llm/tier1_inference.py` ×6 sites | `_write_simple_edges`, `_write_explicit_edges` (+2 fallback) | `llm_inference` / `llm_enrichment` | LED_TO, TRIGGERED, CAUSED_BY, AMPLIFIED, INDICATES | ✅ — and carries full derivation payload (model_id, prompt sha, inferred_at, input_refs) as of WS-1.5 |
| 4 | `context_graph_api.py:634,750,765` | `graph_ingest` (REST ingest API) | caller-supplied (validated) | caller-supplied | ✅ |
| 5 | `onboarding_api_v2_config_aware.py:~693` | stakeholder→decision linker | `onboarding_provision` | INVOLVES | ✅ **fixed in WS-1.1 sweep** — was raw, NO source_platform (newly found) |
| 6 | `mcp_server/cs_pulse_onboarding.py:~1609` | `_process_data_impl` (stakeholder role-match linker) | `process_data` | INVOLVES | ✅ **fixed in WS-1.1 sweep** — was raw, NO source_platform (newly found) |
| 7 | `mcp_server/cs_pulse_onboarding.py:1969` | `_process_data_impl` (signal_edges.csv rows) | from CSV row, default `csv_import` | from CSV row, default LED_TO | ❌ raw constructor |
| 8 | `mcp_server/cs_pulse_onboarding.py:2865` | `clone_customer` | copied from source edge | copied | ❌ raw (faithful copy — reasonable) |
| 9 | `push_intelligence_subscriber.py:203` | `_link_stakeholders_to_decision` | `playbook_auto_trigger` | INVOLVES | ❌ raw |
| 10 | `push_intelligence_subscriber.py:~484` | `evaluate_playbook_trigger_for_account` | `playbook_auto_trigger` | TRIGGERED | ❌ raw — confidence = **arc_confidence** (see roi_leak.md) |
| 11 | `utils/signal_analyst.py:215,233,489,525,552` | `check_and_analyze`, `analyze_on_signal` | `signal_analyst` | LED_TO (+ others) | ❌ raw ×5 |
| 12 | `utils/playbook_lifecycle.py:481,512` | `_write_context_graph_outcome` | `playbook_execution` | RESULTED_IN (+1) | ❌ raw ×2 |
| 13 | `utils/urgent_signal_scanner.py:223,247` | `scan_for_urgent_signals` | `urgent_signal_scanner` | LED_TO | ❌ raw ×2 |
| 14 | `utils/context_graph.py:828` | `add_edge` helper ("does NOT deduplicate") | caller-supplied | caller-supplied | ❌ by design — a second sanctioned-looking constructor that bypasses the invariant gate; check its callers before WS-2 |

## Raw SQL writers (bypass ORM entirely — the reason WS-2's control must be a DB constraint)

| # | file:line | function/context | source_platform |
|---|---|---|---|
| 15 | `onboarding_api_v2_config_aware.py:1532` | signal_edges CSV ingestion (raw INSERT) | column included in INSERT |
| 16 | `backup_restore_api.py:501` | tenant restore (column-faithful INSERT) | copied from backup |

## Notes for WS-2

- Every writer **now sets source_platform** — WS-1's "zero new NULL-source edges" exit criterion holds at the source level (guard test: `tests/test_wizard_a_edge_provenance.py`; the two newly-found linkers are covered by their upsert_edge routing, which defaults source_platform rather than allowing NULL).
- Rows 9–14: tagged but unrouted — they skip the I1/I2/I4 gate. Migrating them to upsert_edge is WS-2 2c's EdgeFactory work, not WS-1.
- Row 14 (`add_edge`) is a latent trap: a helper that looks sanctioned but skips dedup AND the gate. WS-2 2c should either delete it or fold it into upsert_edge.
- Rows 15–16 are why the NOT NULL constraint (WS-2 2c) is the actual control; the Python factory is ergonomics.
- distinct source_platform values across writers: `wizard_a`, `llm_inference`, `llm_enrichment`, `csv_import`, `process_data`, `onboarding_provision`, `playbook_auto_trigger`, `signal_analyst`, `playbook_execution`, `urgent_signal_scanner`, + caller-supplied via ingest API + restore copies. That's 10+ known values → confirms the plan's "closed enum on derivation would mis-fit" warning.
