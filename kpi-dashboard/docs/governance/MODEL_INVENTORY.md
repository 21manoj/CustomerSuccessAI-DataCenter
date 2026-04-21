# CS Pulse — AI/ML Model Inventory Register

**Document Version:** 2.0
**Date:** April 21, 2026
**Classification:** Internal — Confidential
**Owner:** Engineering / Compliance
**Status:** Living Register — Update on every model change
**Parent Document:** [AI_GOVERNANCE_FRAMEWORK.md](AI_GOVERNANCE_FRAMEWORK.md)
**Addendum:** [QUALITATIVE_SIGNAL_GOVERNANCE.md](QUALITATIVE_SIGNAL_GOVERNANCE.md) (introduces `signal_type` classification)

## Changes in v2.0 (Apr 21, 2026)

- **Added `signal_type` column** to summary table: Quant / Qual-source / Qual-processing / Cross-cutting. 7 of 15 models are qualitative or cross-cutting.
- **Validation-control implications** per signal_type: Quant models use backtest-vs-actual; Qual-source models require inter-rater reliability + provenance completeness; Qual-processing models require fixture-run stability + hallucination sampling + prompt version tracking; Cross-cutting models need both sets + causal chain integrity.
- **Full controls specification** lives in [QUALITATIVE_SIGNAL_GOVERNANCE.md](QUALITATIVE_SIGNAL_GOVERNANCE.md). This register carries the classification; that doc carries the controls.
- **Rationale:** the original v0.1 (Apr 20) implicitly assumed quant-first validation. The two-layer indicator model (qualitative leading + quantitative trailing) is CS Pulse's core differentiator and requires qual-specific controls that were missing.

---

## 1. Purpose

This register is the **single source of truth** for every AI/ML/statistical model operating in CS Pulse. It is the primary artifact requested under SR 11-7 model risk management, SOC 2 § CC3.4 (risk assessment), and EU AI Act Article 11 (technical documentation for high-risk AI systems).

**Update obligation:** Any new model, retired model, or material change (retraining, prompt rewrite, weight recalibration, threshold shift) must update this register within 5 business days. Drift of the register from reality is itself a compliance finding.

---

## 2. Register Summary

`Signal Type` legend: **Q** = Quant · **QS** = Qual-source · **QP** = Qual-processing · **X** = Cross-cutting. See [QUALITATIVE_SIGNAL_GOVERNANCE.md](QUALITATIVE_SIGNAL_GOVERNANCE.md) §2 for definitions and required controls per type.

| ID | Name | Tier | Signal Type | Status | Method | Owner | Independent Validator | Last Validated | Drift Monitor |
|---|---|---|---|---|---|---|---|---|---|
| MOD-001 | Wizard B — NRR Forecast | 1 | **X** | Production | Pattern + correlation | Eng | **Missing** | Never | **Missing** |
| MOD-002 | Wizard C — Weight Calibration | 1 | **Q** | Production | Correlation-based | Eng | **Missing** | Never | **Missing** |
| MOD-003 | Renewal Probability Model | 1 | **X** | **Spec'd, not shipped** | Sigmoid + 8 features | — | — | — | — |
| MOD-004 | Revenue-at-Risk Calculation | 1 | **X** | Production | Rule-based aggregation | Eng | Layer C audit (partial) | 2026-04-20 | **Missing** |
| MOD-005 | Playbook ROI Attribution | 1 | **X** | Production | Causal heuristic | Eng | **Missing** | Never | **Missing** |
| MOD-006 | Power-of-1 Scaling / Investment Allocation | 1 | **Q** | Production | Heuristic projection | Product | **Missing** | Never | **Missing** |
| MOD-007 | LLM Tier 1 Edge Enrichment | 1 | **QP** | Production | LLM (Claude) with prompt | Eng | Pre-commit gate (Layer A) | 2026-04-20 | **Missing** |
| MOD-008 | Taxonomy Revenue-Bucket Classifier | 1 | **QP** | Production | LLM + human review queue | Curator | Dev review (policy) | 2026-04-20 | **Missing** |
| MOD-009 | Wizard A — Arc Classification | 2 | **X** | Production | Statistical (KPI + trajectory) | Eng | Layer C audit (partial) | 2026-04-20 | **Missing** |
| MOD-010 | Playbook Recommendation Engine | 2 | **X** | Production | Rule-based matching | Product | **Missing** | Never | **Missing** |
| MOD-011 | Health Score Rollup (L1→L4) | 2 | **Q** | Production | Weighted average | Product | CustomerConfig | 2026-04-20 | **Missing** |
| MOD-012 | Signal Processing Pipeline | 2 | **QS** | **Spec'd, not shipped** | Multi-channel ingest + LLM classify | — | — | — | — |
| MOD-013 | Stakeholder Mapping / Champion Detection | 2 | **QS** | Production | Engagement scoring | Eng | **Missing** | Never | **Missing** |
| MOD-014 | Taxonomy Polarity Classifier (signal subtypes) | 2 | **QP** | Production | LLM auto-classify + admin queue | Curator | Admin queue (policy) | 2026-04-20 | **Missing** |
| MOD-015 | Ask AI / RAG Chatbot | 3 | **QP** | Production | Retrieval-augmented LLM | Eng | Output sampling | Ad hoc | **Missing** |

**Signal-type distribution:** 3 Quant · 2 Qual-source · 4 Qual-processing · 6 Cross-cutting. Qualitative + cross-cutting together = **12 of 15 models**, which is the scope the Qualitative Signal Governance addendum addresses.

**Bold "Missing"** = compliance gap requiring remediation before SR 11-7 / SOC 2 Type II audit.

---

## 3. Tier 1 Model Cards (Detailed)

### MOD-001 — Wizard B (NRR Forecast + Pattern Analysis)

- **Purpose:** Forecast Net Revenue Retention; detect success/failure patterns across accounts to feed CFO dashboard
- **Inputs:** HealthScore history, DC2SKPI measurements, ContextNode (OUTCOME subtypes), account ARR
- **Outputs:** NRR projection (12-month), per-account renewal probability proxy, pattern classification
- **Method:** Pattern analysis + correlation; does NOT use LLM
- **Source:** [backend/wizards/wizard_b_pattern_db.py](../../backend/wizards/wizard_b_pattern_db.py)
- **Trigger:** Called from `trigger_wizard` MCP tool; run on ingest
- **Dependencies Fed:** MOD-004 (Revenue-at-Risk), MOD-006 (Power-of-1), CFO/CRO dashboards
- **Dependencies Consumed:** OUTCOME nodes from MOD-007, MOD-008
- **Known Limitations:**
  - Assumes OUTCOME taxonomy is correctly classified — garbage-in if MOD-007 mis-infers polarity
  - Pattern detection is backward-looking; does not adapt to new arc types without retraining
  - No uncertainty quantification on NRR forecast
- **SR 11-7 Risk Class:** High (directly forecasts revenue)
- **EU AI Act Risk:** Limited Risk (not decision-making on natural persons)
- **Open Gaps:** Independent validator; monthly backtest vs. actuals; uncertainty bounds

---

### MOD-002 — Wizard C (Weight Calibration)

- **Purpose:** Recalibrate KPI and pillar weights per customer based on observed health↔outcome correlation
- **Inputs:** Split of accounts into successful (health≥70) vs unsuccessful (health<50); per-KPI correlation coefficients
- **Outputs:** `dc2s_pillar_weights` + `dc2s_kpi_weights` stored on CustomerConfig; audit row in WeightCalibrationHistory
- **Method:** `base_weight * (0.5 + correlation)`, normalized per pillar to sum=1.0
- **Source:** [backend/wizards/wizard_c_weight_calibrator_db.py](../../backend/wizards/wizard_c_weight_calibrator_db.py)
- **Trigger:** Manual via `trigger_wizard`; also triggered by CDI template selection
- **Dependencies Fed:** MOD-011 (Health Score Rollup) — every recalibration changes every future health score
- **Dependencies Consumed:** HealthScore, DC2SKPI, OUTCOME nodes
- **Known Limitations:**
  - Correlation ≠ causation; can amplify spurious signals at low N
  - No regularization against extreme weight shifts between calibrations
  - Customer admin can trigger without impact-simulation preview
- **SR 11-7 Risk Class:** High (changes every downstream health classification)
- **EU AI Act Risk:** Limited Risk
- **Open Gaps:** Pre-change impact simulation; independent approval gate on weight deltas > X%; audit review cadence

---

### MOD-003 — Renewal Probability Model (SPEC'D, NOT SHIPPED)

- **Purpose:** Replace 3-bucket renewal probability lookup (90/65/35%) with per-account sigmoid model
- **Inputs (planned):** Health, trend, champion status, arc state, signal recency, engagement, pillar floor (8 features)
- **Outputs (planned):** Per-account renewal probability ∈ [0,1]
- **Method:** Sigmoid with cold-start coefficients; Wizard C calibratable
- **Spec:** [memory/spec_renewal_probability_model.md](../../../../.claude/projects/-Users-manojgupta-CustomerSuccessAI-DataCenter/memory/spec_renewal_probability_model.md)
- **Gating Requirement:** **Full governance (independent validator, drift monitor, model card, change approval) must be in place BEFORE production launch.** This is a Tier 1 model — shipping it without governance creates a regulatory liability.
- **SR 11-7 Risk Class:** High
- **EU AI Act Risk:** Limited-to-High Risk depending on whether it drives pricing/credit decisions

---

### MOD-004 — Revenue-at-Risk Calculation

- **Purpose:** Aggregate $ value of accounts with health < threshold; feeds CRO/CFO dashboard headline number
- **Inputs:** Account ARR, HealthScore, account_status, ContextNode OUTCOME subtypes with revenue_impact
- **Outputs:** $ at-risk total, breakdown by urgency bucket, by CSM
- **Method:** Rule-based aggregation over filtered nodes
- **Source:** [backend/utils/context_graph.py](../../backend/utils/context_graph.py) `get_revenue_at_risk`
- **Dependencies Fed:** CFO/CRO dashboards, NRR forecast comparisons
- **Dependencies Consumed:** HealthScore, ContextNode, ContextEdge
- **Known Limitations:** Sensitive to I3 (orphan OUTCOMEs) and I11 (bucket-map drift) — Layer C audit flags but does not block
- **SR 11-7 Risk Class:** High
- **Open Gaps:** Reconciliation report vs. CRM source-of-truth revenue

---

### MOD-005 — Playbook ROI Attribution

- **Purpose:** Attribute $ saved / expanded to specific playbook runs; generates CRO/CFO proof points
- **Inputs:** PlaybookExecution lifecycle rows, HealthScore at triggered_at and closed_at, OUTCOME nodes linked via CAUSED_BY edges
- **Outputs:** Per-playbook ROI multiple, revenue protected/expanded $, success rate
- **Method:** Causal heuristic — attributes revenue delta between triggered_at and closed_at within confidence bounds
- **Source:** [backend/outcome_roi_engine.py](../../backend/outcome_roi_engine.py)
- **Known Limitations:**
  - Attribution confidence capped to prevent inflation
  - Assumes playbook lifecycle rows are complete — silent under-attribution if lifecycle not recorded
  - No counterfactual ("what would have happened without the playbook")
- **SR 11-7 Risk Class:** High (directly feeds financial proof claims)
- **Open Gaps:** Counterfactual baseline; attribution methodology doc; independent review per playbook type

---

### MOD-006 — Power-of-1 Scaling / Investment Allocation

- **Purpose:** Project CS investment ROI at various scaling scenarios (1%, 2.5% of ARR) for CRO/CFO budget conversations
- **Inputs:** Portfolio ARR, current CS spend, historical playbook ROI (from MOD-005)
- **Outputs:** Scenario projections ($ invested → $ protected/expanded → ROI multiple)
- **Method:** Heuristic projection based on historical ratios + scaling assumptions
- **Source:** [backend/mcp_server](../../backend/mcp_server) `calculate_power_of_1` tool
- **Known Limitations:**
  - Linear scaling assumption may break at extreme investment levels
  - Assumes historical ROI is repeatable (survivorship bias risk)
  - No uncertainty bounds on projections
- **SR 11-7 Risk Class:** High (drives investment decisions)
- **Open Gaps:** Assumptions doc; bound-sensitivity analysis; versioned scenario templates

---

### MOD-007 — LLM Tier 1 Edge Enrichment

- **Purpose:** Infer causal polarity and edge relationships (LED_TO, CAUSED_BY) where CSV input is sparse (3/4-CSV mode)
- **Inputs:** Signal subtype, outcome subtype, account context, narrative text where available
- **Outputs:** ContextEdge rows with `source_platform='llm_enrichment'`, confidence score ∈ [0,1]
- **Method:** LLM (Claude) call with structured prompt
- **Source:** [backend/mcp_server/tier1_inference.py](../../backend/mcp_server/tier1_inference.py) (and associated prompt)
- **Trigger:** `should_run()` gate — default ON for 4-CSV, OFF for 11-CSV (see [policy_llm_tier1_auto_enable.md](../../../../.claude/projects/-Users-manojgupta-CustomerSuccessAI-DataCenter/memory/policy_llm_tier1_auto_enable.md))
- **Validators in place:**
  - Pre-commit gate rejects I1 (OUTCOME→OUTCOME), I2 (polarity mismatch), clamps I4 confidence
  - Layer C audit flags post-ingest
- **Known Limitations:**
  - Prompt lives in Python source — no formal version control per prompt
  - No systematic output sampling to detect drift
  - Silent auto-classify for polarity (per policy) means misclassifications can accumulate until 30-day review
- **SR 11-7 Risk Class:** High (every downstream Tier 1 model depends on correct polarity)
- **EU AI Act Risk:** Limited Risk (output is a classification, not an autonomous decision)
- **Open Gaps:** Prompt version register; monthly output sampling; prompt change approval workflow

---

### MOD-008 — Taxonomy Revenue-Bucket Classifier

- **Purpose:** Map `revenue_impact_type` tag to canonical bucket (protected / lost / expansion / at_risk)
- **Inputs:** Subtype, revenue_impact_type tag, sample edge context
- **Outputs:** Bucket assignment stored in taxonomy JSON (planned) or rejected to quarantine queue
- **Method:** Per policy — **quarantine + dev review, never silent auto-classify**. LLM may suggest; human approves.
- **Policy:** [policy_taxonomy_runtime_auto_fix.md](../../../../.claude/projects/-Users-manojgupta-CustomerSuccessAI-DataCenter/memory/policy_taxonomy_runtime_auto_fix.md)
- **Source (planned):** admin UI + MCP tools (see `AI_GOVERNANCE_FRAMEWORK.md` §3)
- **Dependencies Fed:** MOD-004, MOD-005, MOD-006 (all revenue math)
- **Known Limitations:** Rests on completeness of `REVENUE_BUCKET_MAP` — misses become I11 warnings, then quarantine
- **SR 11-7 Risk Class:** High (directly affects bucketing of every revenue claim)
- **Open Gaps:** Admin UI; approval queue; dual-approver requirement

---

## 4. Tier 2 Model Cards (Abbreviated)

### MOD-009 — Wizard A (Arc Classification)

- **Purpose:** Classify account into story arc (Silent Churn, Competitive Displacement, Expansion Ready, etc.)
- **Method:** Statistical — KPI trajectory + signal patterns matched against arc definitions
- **Source:** [backend/wizards/wizard_a_journey_db.py](../../backend/wizards/wizard_a_journey_db.py)
- **Validators:** Pre-commit gate (for edges it writes); Layer C audit
- **Gaps:** Classification confidence threshold not enforced; misclassification review queue missing

### MOD-010 — Playbook Recommendation Engine

- **Purpose:** Recommend playbook (PB-01…PB-06) for a given account given health, arc, and signal state
- **Method:** Rule-based matching against playbook preconditions
- **Gaps:** No audit log of recommendation reasoning; no A/B comparison across rule variants

### MOD-011 — Health Score Rollup (L1→L2→L3→L4)

- **Purpose:** Combine KPIs → pillars → account → customer revenue-weighted health
- **Method:** Weighted average per memory (L4 is revenue-weighted)
- **Source:** [backend/utils/score_calculator.py](../../backend/utils/score_calculator.py)
- **Validators:** Weight hierarchy enforced (CustomerConfig → bootstrap_weights_config.json → kpi_definitions.py)
- **Gaps:** Change approval workflow on pillar weight shifts; per-customer drift vs. portfolio

### MOD-012 — Signal Processing Pipeline (NOT SHIPPED)

- **Purpose:** Ingest signals from email (SendGrid), Slack webhook, transcript upload; classify and link to accounts
- **Gating Requirement:** Full three-role governance from day one of launch — infrastructure exists, governance must precede launch
- **Spec:** [spec_signal_processing_pipeline.md](../../../../.claude/projects/-Users-manojgupta-CustomerSuccessAI-DataCenter/memory/spec_signal_processing_pipeline.md)

### MOD-013 — Stakeholder Mapping / Champion Detection

- **Purpose:** Identify champion, decision-maker, detractor roles from engagement patterns
- **Method:** Engagement scoring + manual curation
- **Gaps:** Confidence scoring; audit trail of override actions

### MOD-014 — Taxonomy Polarity Classifier (signal subtypes)

- **Purpose:** Classify new signal subtypes as positive / negative / polarity-ambiguous
- **Method:** Silent LLM auto-classify + admin queue for promotion (per policy)
- **Policy:** [policy_taxonomy_runtime_auto_fix.md](../../../../.claude/projects/-Users-manojgupta-CustomerSuccessAI-DataCenter/memory/policy_taxonomy_runtime_auto_fix.md)
- **Gaps:** 30-day review SLA enforcement; admin UI

---

## 5. Tier 3 Model Entry

### MOD-015 — Ask AI / RAG Chatbot

- **Purpose:** Answer natural-language questions about accounts, portfolio, signals using retrieval-augmented LLM
- **Method:** MCP tool-calling + RAG over ContextGraph
- **Controls:** PII filter (planned); session logging (partial); output-source traceability (via MCP tool IDs)
- **Gaps:** Systematic hallucination sampling; prompt version control; output retention policy

---

## 6. Inter-Model Dependency Graph

```
                   ┌────────────────────────┐
                   │  MOD-007 LLM Tier 1    │
                   │  Edge Enrichment       │
                   └───────────┬────────────┘
                               │ polarity / edges
                               ▼
     ┌─────────────────────────────────────────────────┐
     │  MOD-008 Taxonomy Revenue-Bucket Classifier     │
     └───────────────────┬─────────────────────────────┘
                         │ classified outcomes
        ┌────────────────┼────────────────────┐
        ▼                ▼                    ▼
 ┌────────────┐  ┌────────────┐     ┌─────────────────┐
 │ MOD-001    │  │ MOD-002    │     │ MOD-004         │
 │ Wizard B   │  │ Wizard C   │     │ Revenue-at-Risk │
 │ NRR        │  │ Weight Cal │     └────────┬────────┘
 └─────┬──────┘  └─────┬──────┘              │
       │ forecast     │ new weights          │
       │              ▼                      │
       │       ┌─────────────┐               │
       │       │ MOD-011     │               │
       │       │ Health Roll │               │
       │       └─────┬───────┘               │
       │             │ health                │
       ▼             ▼                       ▼
  ┌────────────────────────────────────────────┐
  │ MOD-005 Playbook ROI + MOD-006 Power-of-1 │
  │ → CFO/CRO Dashboards                       │
  └────────────────────────────────────────────┘
```

**Cascade risk:** a misclassification in MOD-007 or MOD-008 propagates through every Tier 1 model downstream. This is why the pre-commit gate + Layer C invariants are the single most important control in the system — they sit at the top of the cascade.

---

## 7. Consolidated Gap List (for Remediation Planning)

Sorted by blast radius, not by ease-of-fix.

1. **No independent validator role** for any Wizard or ROI engine — author ≠ validator is a SOX / SR 11-7 baseline
2. **No drift monitoring** on any Tier 1 model — NRR forecast accuracy vs. actuals never measured
3. **No prompt version register** for MOD-007 (LLM Tier 1) — prompts rot in source code
4. **No change-approval workflow UI** for weight or taxonomy changes — code commit = approval
5. **Renewal Probability Model (MOD-003) must not ship** until governance framework applies
6. **Signal Processing Pipeline (MOD-012) must not ship** until governance framework applies
7. **No counterfactual baseline** for MOD-005 (Playbook ROI) — attribution assumed causal
8. **No reconciliation** between MOD-004 (CS Pulse revenue-at-risk) and CRM source-of-truth
9. **No uncertainty bounds** on MOD-001 or MOD-006 projections
10. **Ask AI (MOD-015) has no hallucination sampling** — outputs may be factually wrong without detection

---

## Change Log

| Date | Version | Change | Author |
|---|---|---|---|
| 2026-04-20 | 0.1 | Initial register covering 15 models (8 Tier 1, 6 Tier 2, 1 Tier 3) | Engineering |
