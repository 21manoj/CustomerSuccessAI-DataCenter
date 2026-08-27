# WS-1.3 — arc_confidence ROI/NRR leak check

**Verdict: CLEARED. The stop condition is NOT triggered.** No ROI, NRR, expansion-forecast, or Power-of-1 path consumes `arc_confidence` (or a value derived from it) as a calibrated multiplicand. WS-1 proceeds.

## What was checked (grep + read of every consumer, 2026-08-22)

Complete consumer list for `arc_confidence` and its two derived copies (arc_detection node `properties.confidence`, TRIGGERED edge `confidence`):

| consumer | what it does with the value | in stop-condition scope? |
|---|---|---|
| `models.py:128` | column definition | no |
| `journey_intelligence_api.py:222` | display passthrough | no |
| `predictor/scripts/explain_arc_for_account.py` | debug display | no |
| `mcp_server/cs_pulse_onboarding.py:2765` | clone copy | no |
| `push_intelligence_subscriber.py:285–489` | **playbook auto-trigger gating** — thresholds (`>= 0.7`) and scaling (`* 0.8`, `* 0.5`) decide auto_approved / pending / rejected; also written into the approval record and a TRIGGERED edge | **no** — decisioning, not dollar math (but see finding 2) |

## The two dollar-math sites that DO multiply confidence into revenue

Both were traced to confirm arc_confidence cannot reach them:

1. `utils/context_graph.py:443` — `revenue_impact * confidence` over **OUTCOME** nodes only. arc_detection nodes are SIGNAL-type.
2. `outcome_roi_engine.py:1672` (timeline builder) — iterates all node types, but the multiplication is gated on `n.revenue_impact`, which **no arc_detection writer ever sets** (both writers — wizard_a_journey_db and push_intelligence's fallback — write properties only).

Wizard B's NRR path uses edge confidence only in `count_trustworthy_causal_edges` — an informational **count** (threshold filter, nothing multiplied), and its provenance filter excludes wizard_a synthetic edges anyway. Wizard C filters by `TRUSTWORTHY_SOURCES` (source strings, not confidence).

## Two findings worth carrying forward (neither triggers the halt)

1. **The historical leak the in-code comment describes is real but past.** `_classify_trajectory_with_confidence` could return >1.0 (crisis: 0.65+0.45=1.10) before the clamp landed. Today's check confirms the *current* consumers don't multiply it into dollars — it does NOT establish what the >1.0 values fed before the clamp existed. That remains a disclosure question for WS-4, not an engineering one; per the standing forward-only rule, the stored values were not touched.
2. **push_intelligence treats arc_confidence as calibrated for *decisions*.** `health < 50 and arc_confidence >= 0.7 → auto_approved` fires a playbook whose PlaybookExecutionV2 cost/revenue rows later enter proof_data ROI. So while no dollar is *multiplied* by arc_confidence, dollars are *spent* on its say-so, and it is a rule-match fit score, not an epistemic estimate. WS-1.1's fix now records `confidence_semantics: 'trajectory_rule_match_score'` on the edge; the auto-trigger threshold itself is push-intelligence config territory and out of WS-1 scope — flagged for the WS-2 adjudication discussion.
