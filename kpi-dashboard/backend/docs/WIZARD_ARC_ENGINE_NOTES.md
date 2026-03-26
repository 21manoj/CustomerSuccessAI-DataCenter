# Wizard Arc + Predictive Engine — Branch Notes

**Branch:** `feature/wizard-arc-predictive-engine`
**Priority:** MUST SHIP before external customer graduation
**Deadline:** Minimum 2 weeks from 2026-03-25 → **Target: 2026-04-08**

---

## Why This Is a Hard Gate

Today the context graph (causal chains, edges, revenue-at-risk) only works because
the **load driver pre-computes everything** — arc types, RefRegistry, edge topology —
before data enters the system.

Real external customers will upload raw CSVs from Salesforce/Gainsight/Zendesk.
Those CSVs have no `signal_edges.csv`, no arc assignment, no edge topology.
Without this branch, **every external customer gets nodes but zero edges** —
the context graph is empty, causal chains don't exist, revenue-at-risk is $0.

The CRO/CFO demo value proposition collapses without causal chains.

---

## What Must Be Done (Sprint 1 — Hard requirement)

| File | Status |
|---|---|
| `utils/arc_classifier.py` | Stub — build first |
| `utils/arc_edge_generator.py` | Stub — build second |
| `wizards/wizard_a_journey_db.py` | Rewrite — calls arc_classifier + arc_edge_generator |
| `models.py` | Add `arc_type`, `arc_phase`, `arc_confidence` to `Account` |
| `onboarding_api_v2_config_aware.py` | Call Wizard A after `ingest_context_graph_csvs()` |
| `mcp_server/cs_pulse_onboarding.py` | `_process_data_impl()` calls `run_wizard_a()` at Path 2 exit |

**Validation gate:** Upload `granite_peak_dc2s.json` with `signal_edges.csv` stripped →
process-data → Wizard A must regenerate equivalent edges → node/edge counts match full run.

---

## What Can Slip to Sprint 2 (Nice-to-have by graduation)

| File | Status |
|---|---|
| `utils/kpi_feature_extractor.py` | Stub — Sprint 2 |
| `utils/peer_matcher.py` | Stub — Sprint 2 |
| `utils/changepoint_detector.py` | Stub — Sprint 2 |
| `utils/churn_probability.py` | Stub — Sprint 2 |
| `wizards/wizard_b_pattern_db.py` | Rewrite — Sprint 2 |

Sprint 2 adds the 60-day churn signal. Valuable but not a hard gate for first external customer.

---

## Full plan reference

See `feature/actions-pipeline-push`: `backend/docs/ACTIONS_PIPELINE_PLAN.md`
