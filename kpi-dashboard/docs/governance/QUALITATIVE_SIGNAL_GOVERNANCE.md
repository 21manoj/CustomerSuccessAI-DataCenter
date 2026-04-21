# CS Pulse — Qualitative Signal Governance (Addendum)

**Document Version:** 1.0
**Date:** April 21, 2026
**Classification:** Internal — Confidential
**Owner:** Engineering / Product / Compliance
**Status:** Cross-cutting Addendum — applies to MODEL_INVENTORY, DRIFT_MONITORING, AUDIT_TRAIL_REQUIREMENTS
**Parent:** [AI_GOVERNANCE_FRAMEWORK.md](AI_GOVERNANCE_FRAMEWORK.md)

---

## 1. Why this addendum exists

CS Pulse's core differentiator is a **two-layer indicator model**:

- **Leading layer (qualitative):** exec commitments, stakeholder moves, champion re-engagement, sentiment shifts, transcript signals — captured via signal_analyst, LLM Tier 1 enrichment, and qualitative_signals ingestion pipelines
- **Trailing layer (quantitative):** KPI measurements rolled up monthly into health scores

The gap between these layers — qualitative signals firing weeks-to-months before KPI rollup absorbs them — is the product's value proposition. A churn_averted outcome fires at a decision point driven by qualitative signal; the KPI catch-up trails by 30-90 days.

**This distinction has governance implications the original framework didn't address.** How you validate a qualitative leading signal is fundamentally different from how you validate a quantitative trailing measurement:

- You don't cross-validate qualitative claims against quantitative deltas (doing so produces false positives — see Apr 21 TechGrid misreading)
- You validate qualitative signals via **causal chain integrity** and **evidence provenance**
- You monitor qualitative model drift via **fixture runs** and **inter-rater reliability**, not via **backtest against actuals**

This addendum formalizes those controls. It does not replace MODEL_INVENTORY / DRIFT_MONITORING / AUDIT_TRAIL_REQUIREMENTS — it adds the qualitative-specific layer to each.

---

## 2. Signal-type classification (applies to MODEL_INVENTORY.md)

Every model in the inventory carries a **signal_type** tag in addition to its tier:

| Signal Type | Definition | Validation approach |
|---|---|---|
| **Quant** | Consumes and produces numeric measurements (KPI rollup, health score, ARR calc) | Backtest against actuals; statistical drift metrics (MAPE, calibration plot); input range validation |
| **Qual-source** | Ingests qualitative data (email, Slack, transcripts, stakeholder notes) and emits structured signals | Provenance chain (raw input → enriched output), inter-rater reliability sampling, PII handling, hallucination rate |
| **Qual-processing** | Takes structured qualitative inputs and classifies / infers (LLM Tier 1, polarity classifier, revenue-bucket classifier, Ask AI RAG) | Fixture run stability, prompt version tracking, output coherence vs input evidence, hallucination sampling |
| **Cross-cutting** | Consumes both qual and quant; produces decisions or classifications that depend on both (Wizard A, Playbook Recommendation, ROI Attribution) | Both sets of controls; additionally — causal chain integrity checks |

### Classification of the 15 models

| ID | Name | Tier | Signal Type |
|---|---|---|---|
| MOD-001 | Wizard B — NRR Forecast | 1 | Cross-cutting (reads OUTCOME nodes of both types) |
| MOD-002 | Wizard C — Weight Calibration | 1 | Quant |
| MOD-003 | Renewal Probability Model | 1 | Cross-cutting |
| MOD-004 | Revenue-at-Risk Calculation | 1 | Cross-cutting |
| MOD-005 | Playbook ROI Attribution | 1 | Cross-cutting |
| MOD-006 | Power-of-1 Scaling | 1 | Quant |
| MOD-007 | LLM Tier 1 Edge Enrichment | 1 | **Qual-processing** |
| MOD-008 | Taxonomy Revenue-Bucket Classifier | 1 | **Qual-processing** |
| MOD-009 | Wizard A — Arc Classification | 2 | Cross-cutting |
| MOD-010 | Playbook Recommendation | 2 | Cross-cutting |
| MOD-011 | Health Score Rollup | 2 | Quant |
| MOD-012 | Signal Processing Pipeline | 2 | **Qual-source** |
| MOD-013 | Stakeholder Mapping | 2 | **Qual-source** |
| MOD-014 | Taxonomy Polarity Classifier | 2 | **Qual-processing** |
| MOD-015 | Ask AI / RAG Chatbot | 3 | **Qual-processing** |

**7 of 15 models are qualitative or cross-cutting.** That's the scale of coverage this addendum adds.

---

## 3. Qualitative-specific validation controls (applies to DRIFT_MONITORING.md)

In addition to the standard drift controls per Tier (see DRIFT_MONITORING §3-5), qualitative and qual-processing models require:

### 3.1 Fixture-run stability (for Qual-processing models)

Canned input/expected-output fixture sets, run on a cadence (weekly minimum for Tier 1, monthly for Tier 2-3). Primary defense against silent LLM backend drift and prompt-change regressions.

- **MOD-007 fixtures:** 50-150 signal/outcome pairs with known polarity classifications. Diff output on every fixture run.
- **MOD-008 fixtures:** taxonomy subtype → revenue bucket classifications. Regression-test on every prompt change.
- **MOD-014 fixtures:** signal subtype polarity classifications.
- **MOD-015 fixtures:** question/expected-answer-shape pairs for hallucination detection.

### 3.2 Inter-rater reliability sampling (for Qual-source models)

For models that ingest unstructured qualitative data and emit structured signals, sample N% of outputs (typically 5-10%) for human review. Compute agreement rate with the automated classification.

- **MOD-012 (signal ingestion)** — sample 10% of enriched signals, human-reviewer tags intent/urgency/sentiment, compare to automated output
- **MOD-013 (stakeholder mapping)** — sample 10% of champion/detractor classifications, validate against known relationships

Alert thresholds: agreement rate < 80% on any weekly cohort → investigate prompt or classifier drift.

### 3.3 Provenance completeness (for ALL qualitative outputs)

Every qualitative OUTCOME or inferred signal must be traceable to its originating evidence:

- `source_event_id` points at a specific raw signal (email_id, slack_ts, transcript_segment_id, stakeholder_event_id) — NOT a generic subtype label
- `properties.evidence` populated with the raw text or reference
- `properties.reasoning` (for Qual-processing) includes the LLM/classifier reasoning trace

**Drift metric:** `provenance_completeness = (outputs with full provenance) / (total outputs)`. Weekly. Alert if <95% on Tier 1 paths.

### 3.4 Hallucination rate (for Qual-processing LLM outputs)

Sample N% of LLM outputs per week; human-reviewer tags whether the output invents details not present in the input or contradicts the input.

- **MOD-007** — sample 5% of edge classifications; tag hallucination rate
- **MOD-015** — sample 5% of Ask AI responses; tag factual correctness

Alert threshold: >5% hallucination rate on any weekly cohort.

### 3.5 Prompt version tracking (for Qual-processing LLM models)

Every LLM output logs the `prompt_version` used. On prompt change, regression-test against fixture set before promotion. Rollback plan: revert to prior prompt version.

---

## 4. Qualitative-decision audit fields (applies to AUDIT_TRAIL_REQUIREMENTS.md §2.1)

In addition to the standard decision-event fields, qualitative decisions (Qual-source and Qual-processing models) require:

| Field | Required for | Notes |
|---|---|---|
| `prompt_version` | All Qual-processing LLM outputs | Enables reproducibility across prompt changes |
| `model_version` (base LLM) | All Qual-processing LLM outputs | Captures backend model changes (claude-opus-4 → claude-opus-4.1 etc.) |
| `reasoning_trace` (optional, sampled) | Sampled Tier 1 Qual-processing outputs | LLM chain-of-thought if captured; not all outputs need this but sampled audit requires it |
| `evidence_provenance` | All Qual-source outputs | Raw input reference (email_id / slack_ts / transcript_id); allows reconstruction |
| `inter_rater_sample_flag` | Outputs selected for the weekly inter-rater review cohort | Enables review workflow |
| `pii_handling_version` | All Qual-source inputs | If PII was redacted/hashed, which version of the redaction ruleset was applied |

**PII note:** Qualitative inputs often contain PII (names, emails, contract terms). The audit trail stores `pii_handling_version` + redacted representation, not raw. Raw retention follows separate PII retention policy (typically 30 days then hash-only).

---

## 5. Cross-cutting models — dual-validation requirement

Models tagged Cross-cutting (MOD-001, 003, 004, 005, 009, 010) must validate both layers:

- **Quant side:** backtest against actuals (e.g. NRR forecast accuracy, revenue_at_risk vs CRM reconciliation)
- **Qual side:** causal chain integrity (every revenue OUTCOME traces to a DECISION traces to a SIGNAL; no orphans; no reverse-time edges)

**The Apr 21 lesson (canonical): do NOT invalidate a qualitative leading signal by diffing against a quantitative trailing measurement taken within 30 days of the signal.** The trailing layer has 30-90 day measurement lag; the qualitative signal fires on decision points. Comparing them directly produces false positives. The correct validation path is causal chain integrity — follow the signal → decision → outcome graph, not the numeric delta.

Documented in TechGrid case study: Feb 26 champion re-engagement (qualitative signal) → Mar 28 $50K renewal secured (outcome). Mar health score (28.3) vs Feb (27.9) = +0.4 numeric delta — **this is not a contradiction of the narrative, it's the expected trailing-layer lag.** The causal chain is intact; the two-layer model is working.

---

## 6. Anti-patterns — what NOT to do

- **Do NOT use KPI-delta comparisons as a validation check for qualitative OUTCOMEs.** The layers have different lag characteristics; cross-validating them produces false positives.
- **Do NOT filter qualitative OUTCOMEs from CSM-facing surfaces as a default.** Filters shipped Apr 20 (mermaid narrative filter, summary filter) are DEMO-safe because manifest-seeded OUTCOMEs lack evidence; they are NOT the right production default. When provenance is populated, the qualitative layer is first-class and should be visible.
- **Do NOT ship a new Qual-source or Qual-processing model without fixture run, inter-rater reliability, and provenance-completeness controls.** This is a Phase-1-gate requirement.
- **Do NOT use the same drift metric for Quant and Qual models.** Backtest-vs-actual applies to Quant; fixture-run-stability applies to Qual-processing; inter-rater-reliability applies to Qual-source.
- **Do NOT retain raw qualitative inputs longer than necessary.** PII retention policy (30 days raw, then hashed) applies to signal_analyst inputs, Ask AI session logs, etc.

---

## 7. Open items — what this addendum flags as pending

1. **MOD-012 Signal Processing Pipeline must ship with qual-specific controls.** Current governance doc says "must ship with full governance"; this addendum makes the "full governance" concrete: fixture runs, inter-rater reliability sampling, provenance completeness monitoring, PII handling.
2. **Manifest simulation of qualitative signals.** Manifests currently seed narrative OUTCOMEs with empty evidence fields. To make demos behave like production, manifests should also seed qualitative_signals.csv entries that the narrative OUTCOMEs can reference via source_event_id. Otherwise demo and production diverge in provenance structure.
3. **Retroactive provenance backfill.** Existing narrative OUTCOMEs on customer 385/387 lack evidence. Backfill decision: populate retroactively from manifest template metadata, OR mark as `provenance_unverified: true` so audit tooling can distinguish them from real production outputs.
4. **CSM-facing surface for leading vs trailing.** Not in current dashboard inventory. CSMs need a view that shows both layers side-by-side so they can act on leading signals before trailing catches up.

---

## 8. Summary — what changes, what doesn't

**Unchanged:**
- Three-role separation of duties (author/validator/user)
- Tier classification by revenue blast radius
- Regulatory mapping (SR 11-7, SOC 2, EU AI Act, NIST)
- Change management 7-gate workflow
- RBAC role structure

**Changed / extended:**
- MODEL_INVENTORY gains `signal_type` column per model
- DRIFT_MONITORING adds §3.1-3.5 qual-specific controls
- AUDIT_TRAIL_REQUIREMENTS §2.1 adds qualitative-decision fields
- GOVERNANCE_ROADMAP Phase 1 MOD-012 unblock-criteria specified

**This addendum exists because:** the original framework (drafted Apr 20) was implicitly quant-first. The Apr 21 recognition that CS Pulse's differentiator is the two-layer model forced this recalibration. All downstream buyers / regulators doing AI-DD on governance should see this addendum alongside the framework — it's the layer that makes the framework honest about what the product actually does.

## Change Log

| Date | Version | Change | Author |
|---|---|---|---|
| 2026-04-21 | 1.0 | Initial draft — signal-type classification, qual-specific controls, dual-validation requirement for cross-cutting models | Engineering / Product |
