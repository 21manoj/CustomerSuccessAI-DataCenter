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

## Sprint 1 Validation — Manifest-as-External-Data Simulation

We have no real external customer data yet. Manifests solve this: generate CSVs,
strip `signal_edges.csv` (what a real customer won't have), feed through the normal
onboarding path, let Wizard A reconstruct edges, compare against ground truth.

### The 5-Step Test Harness

```bash
# Step 1 — Generate CSVs offline (deterministic, seed-controlled)
python3 cs_pulse_driver.py --manifest manifests/granite_peak_dc2s.json \
  --generate-only /tmp/test_external/ --seed 42

# Step 2 — Strip signal_edges.csv (simulates real customer upload — they won't have this)
rm /tmp/test_external/signal_edges.csv
# Remaining 9 CSVs = exactly what Salesforce/Gainsight/Zendesk would produce

# Step 3 — Upload 9 CSVs via normal onboarding API
#   accounts, kpi_measurements, qualitative_signals, stakeholders,
#   engagement_events, profiles, products, decisions, outcomes

# Step 4 — Trigger process-data → Wizard A runs automatically
#   arc_classifier     → assigns arc type from signals + health slope
#   arc_edge_generator → builds ContextEdge rows from real DB node IDs

# Step 5 — Compare vs ground truth
#   Full run (with signal_edges.csv):       N edges per account  (ground truth)
#   Wizard A reconstruction (without it):   M edges per account
#   Goal: M ≈ N — same edge types, valid temporal ordering, similar counts
```

### Why This Is Solid

- **Deterministic**: `--seed 42` = same CSVs every run, reproducible failures
- **Ground truth exists**: original `signal_edges.csv` gives exact expected edges
- **No external risk**: runs on EC2 against live DB, zero real customer data needed
- **Multiple arc types**: 4 manifests exercise every arc pattern end-to-end
- **Fast iteration**: strip + re-upload + re-run takes ~60 seconds per manifest

### Test Matrix (4 manifests = 4 full E2E validation runs)

| Manifest | Vertical | Arc types covered | Accounts |
|---|---|---|---|
| `granite_peak_dc2s.json` | DC2_S | crisis_recovery, budget_pressure, steady_performer | 18 |
| `alpine_saas_partners.json` | SaaS Premium | stable, land_and_expand, engagement_decline | 18 |
| `dr1_ai_dc2s.json` | DC2_S | champion_loss, infrastructure_decay | 10 |
| `mount_peak_saas.json` | SaaS Premium | mixed arc types | 10 |

### Acceptance Criteria (Sprint 1 gate — all 4 must pass before merge)

- [ ] `granite_peak_dc2s` — Wizard A produces ≥ 3 edges/account (ground truth = 4)
- [ ] `alpine_saas_partners` — Wizard A produces ≥ 2 edges/account
- [ ] `dr1_ai_dc2s` — champion_loss arc correctly classified for accounts with stakeholder departure signal
- [ ] `mount_peak_saas` — zero temporal violations in reconstructed edges
- [ ] All 4 — zero unresolved refs in backend WARNING logs (`signal_edges: unresolved ref`)
- [ ] All 4 — `arc_type` correctly written to `Account.arc_type` in DB post process-data

### Results Written To

`kpi-dashboard/FEATURE_BUILD_RESULTS_20260325.md` — Sprint 1 section

Per-manifest validation table format:
```
| Account | arc_type assigned | edges ground truth | edges Wizard A | match % |
```

---

## Full plan reference

See `feature/actions-pipeline-push`: `backend/docs/ACTIONS_PIPELINE_PLAN.md`
