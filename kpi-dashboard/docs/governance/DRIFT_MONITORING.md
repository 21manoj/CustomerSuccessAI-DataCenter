# CS Pulse — Drift Monitoring

**Document Version:** 0.1 (Initial Draft)
**Date:** April 20, 2026
**Classification:** Internal — Confidential
**Owner:** Engineering / Compliance
**Status:** Living Document
**Parent:** [AI_GOVERNANCE_FRAMEWORK.md](AI_GOVERNANCE_FRAMEWORK.md)
**Companions:** [MODEL_INVENTORY.md](MODEL_INVENTORY.md), [CHANGE_MANAGEMENT.md](CHANGE_MANAGEMENT.md), [AUDIT_TRAIL_REQUIREMENTS.md](AUDIT_TRAIL_REQUIREMENTS.md)

---

## 1. Purpose

Models decay. Inputs shift, customer composition changes, LLM providers update their backends, playbook templates evolve. A model that was correct six months ago can be silently wrong today — and the worst failure mode is "the number still looks plausible."

Drift monitoring is the **operational feedback layer**: it detects quality degradation **before customers notice**, surfaces it as an incident, and feeds remediation through [CHANGE_MANAGEMENT.md](CHANGE_MANAGEMENT.md).

### Governing principle

> **Every Tier 1 model must have at least one quantitative signal that can differentiate "working" from "drifting." If no such signal exists, the model cannot be trusted in production.**

---

## 2. Three Types of Drift

Important to distinguish, because each has different metrics and different fixes.

| Type | What Shifts | Example in CS Pulse | Fix Pattern |
|---|---|---|---|
| **Data drift** | Input distribution changes | A new customer vertical sends signals we haven't seen before; CSV column mix shifts | Extend input handling; recalibrate |
| **Concept drift** | Relationship between inputs and correct output changes | Champion departures used to predict churn in 90 days; for a new customer cohort, the lag is 180 days | Model retrain or logic update |
| **Output drift** | Model outputs shift even if inputs and logic are stable | LLM provider updates a backend model; same prompt returns different polarity classification | Prompt pin or version guard |

Output drift on LLM-backed models (MOD-007, MOD-008, MOD-014, MOD-015) is the **stealthiest** failure mode — no code change, no input change, but yesterday's edges classify differently than today's.

---

## 3. Drift Metrics Per Tier 1 Model

Minimum one quantitative signal per model. Missing signals = gap.

### MOD-001 — Wizard B (NRR Forecast)

- **Primary signal:** **Forecast backtest vs. actual.** For each cohort of accounts, compare the NRR forecast produced N months ago against actual NRR realized at renewal.
- **Secondary:** variance of forecast vs. sibling models (are forecasts consistent across customers of similar size / vertical?)
- **Measurement cadence:** Monthly
- **Alert threshold:** MAPE > 15% or systematic bias (sign-correlated error) on rolling 3-month window
- **Current state:** not implemented. No backtest infrastructure. Critical gap.

### MOD-002 — Wizard C (Weight Calibration)

- **Primary signal:** **Weight delta distribution across successive calibrations.** If one customer's pillar weight shifts >20% between Wizard C runs without corresponding business change, the correlation calc is unstable.
- **Secondary:** post-calibration health score distribution. Mass flips (>10% of accounts changing health tier) suggest over-fitting to a narrow outcome sample.
- **Cadence:** Per-calibration + monthly portfolio view
- **Alert threshold:** pillar-weight delta >20% on any single calibration; or health-tier flip rate >10% of accounts
- **Current state:** `WeightCalibrationHistory` captures raw deltas; no analysis layer. Gap.

### MOD-003 — Renewal Probability Model (not yet shipped)

- **Required signals before launch:** Brier score against realized renewal outcomes; calibration plot (predicted 70% should result in 70% renewal rate); feature-importance drift
- **Gating:** cannot ship to Tier 1 production without backtest infrastructure

### MOD-004 — Revenue-at-Risk

- **Primary signal:** **Reconciliation vs. CRM truth.** Monthly: compare CS Pulse revenue-at-risk total against CRM-derived at-risk ARR (independent source). Variance should be explainable.
- **Secondary:** audit-violation density — if I3 (orphan OUTCOMEs) or I11 (bucket mismap) trend upward, revenue-at-risk is drifting
- **Cadence:** Monthly reconciliation; weekly audit-density scan
- **Alert threshold:** |CS Pulse – CRM| > 10% of total portfolio ARR; or invariant violation increase >20% WoW
- **Current state:** Layer C audit exists and can run on cadence; reconciliation vs. CRM does not exist. Gap.

### MOD-005 — Playbook ROI Attribution

- **Primary signal:** **Success-rate trend per playbook type.** If PB-05 Emergency Retention drops from 83% success to 60% over 3 months, either the model is drifting or the world is changing — both require action.
- **Secondary:** Attribution variance. Do playbooks with similar pre-conditions get similar ROI claims? Wide variance = classification instability.
- **Cadence:** Monthly
- **Alert threshold:** absolute success-rate drop > 15 percentage points; or 90th-percentile attribution > 3x median
- **Current state:** ROI engine produces the rates; no trend analysis or alerting. Gap.

### MOD-006 — Power-of-1 Scaling

- **Primary signal:** **Projection stability.** Re-running the same inputs at the same ARR level should yield near-identical projections. Drift indicates either upstream model drift (MOD-005 ROI) or heuristic-constant change.
- **Secondary:** Forecast vs. realized — when a customer scales CS investment, did realized ROI match projected?
- **Cadence:** Quarterly (investment decisions move slowly)
- **Alert threshold:** same-input projection change > 10%; realized-vs-projected > 30% variance
- **Current state:** no baseline captured. Gap.

### MOD-007 — LLM Tier 1 Edge Enrichment

Most vulnerable to output drift — LLM backend changes under us.

- **Primary signal:** **Canned-fixture output stability.** Maintain a fixture set of ~100 signal/outcome pairs with known-good polarity classifications. Run through the prompt on every prompt change AND on a weekly cadence to catch silent LLM-backend drift.
- **Secondary signals:**
  - Pre-commit rejection rate (edges rejected by gate as % of edges produced). Sudden jump = prompt drift.
  - Layer C violation rate on newly-enriched customers vs. baseline
  - Confidence distribution — bimodal drift (more "very confident" + more "very unsure" and fewer middle) suggests backend change
- **Cadence:** Weekly fixture run; daily rejection-rate check
- **Alert threshold:** any fixture misclassification is investigated; rejection-rate change > 5pp WoW
- **Current state:** pre-commit gate logs exist; fixture run not built. Priority gap — this is where backend drift would bite first.

### MOD-008 — Taxonomy Revenue-Bucket Classifier

- **Primary signal:** **Quarantine queue depth.** If the queue grows and nobody drains it, classifications don't happen and downstream revenue math silently incomplete.
- **Secondary:** post-approval accuracy — of bucket assignments approved in the last quarter, how many were corrected later? Correction rate = classifier quality signal.
- **Cadence:** Daily queue-depth check; quarterly accuracy review
- **Alert threshold:** queue depth > N (set per ops capacity); correction rate > 10%
- **Current state:** quarantine infrastructure not yet implemented. Gap.

---

## 4. Drift Metrics Per Tier 2 Model

Lighter cadence, lighter metrics.

| Model | Primary Drift Signal | Cadence | Alert Threshold |
|---|---|---|---|
| **MOD-009 Wizard A (Arc Classification)** | Classification confidence distribution + manual-override rate | Quarterly | Override rate > 20% |
| **MOD-010 Playbook Recommendation** | Recommendation-to-execution conversion rate | Quarterly | < 30% conversion |
| **MOD-011 Health Score Rollup** | Distribution stability of health tiers across portfolio | Monthly | Tier distribution shift > 10pp |
| **MOD-012 Signal Processing Pipeline** (pre-launch) | Input volume + classification balance | Daily post-launch | — |
| **MOD-013 Stakeholder Mapping** | Champion detection reversal rate | Quarterly | Reversal > 15% |
| **MOD-014 Taxonomy Polarity (signals)** | Auto-classified entries aging past 30-day review SLA | Weekly | Any entry > 30 days unreviewed |

---

## 5. Drift Metrics for Tier 3

| MOD-015 Ask AI | Hallucination sampling + user thumbs-down rate | Weekly sample; continuous thumbs tracking | Hallucination rate >5% or thumbs-down trend up |

---

## 6. Sampling Strategy

Not everything can be monitored at 100%. Per [AUDIT_TRAIL_REQUIREMENTS.md](AUDIT_TRAIL_REQUIREMENTS.md) §3, Tier 1 decisions are fully logged — drift monitoring works over the full log. Tier 2 decisions are sampled at ≥10%.

### Fixture sets (for LLM-backed models)

Maintain canned fixture sets per LLM-backed model (MOD-007, MOD-008, MOD-014, MOD-015). Each fixture:

- **Input:** specific signal/outcome/prompt pair
- **Expected output:** human-curated, reviewed, locked
- **Coverage:** spans common cases + edge cases + adversarial cases
- **Size:** 50–150 fixtures per model — enough to detect shift, small enough to re-run weekly

Fixture runs are the **primary defense against silent LLM backend drift** — everything else detects drift after it has already affected customer data.

### Shadow runs

For MOD-001, MOD-004, MOD-005: periodically run the *new* version of a model in shadow against production inputs, without writing results. Compare shadow output to production output. Divergence = drift or genuine improvement — investigate.

---

## 7. Alerting & Escalation

### Alert levels

| Level | Meaning | Response SLA |
|---|---|---|
| **P1 — Critical drift** | Customer-visible outputs likely wrong right now | Within 4 hours |
| **P2 — Significant drift** | Trend concerning, not yet customer-visible | Within 2 business days |
| **P3 — Watch** | Anomaly worth tracking; individual metric excursion | Next review cycle |

### Routing

- Tier 1 drift alerts → on-call + ML/Model Owner + Compliance Lead
- Tier 2 → Model Owner + Product Lead
- Tier 3 → Product Lead; Tier 1 only if PII / safety implication

### Incident flow

Every P1/P2 drift alert opens an incident event per [AUDIT_TRAIL_REQUIREMENTS.md](AUDIT_TRAIL_REQUIREMENTS.md) §2.5 and enters [CHANGE_MANAGEMENT.md](CHANGE_MANAGEMENT.md) workflow for remediation (emergency CR if P1, standard CR if P2).

---

## 8. Connection to Change Management

Drift is the input signal to the change process. The loop:

```
  Drift monitor → Incident event → Change Request → Review/Approve → Deploy
         ↑                                                              │
         └──────────── Post-deploy verification (§Gate 6) ──────────────┘
```

**Post-deploy verification** (Gate 6 of change workflow) explicitly re-checks the drift metric that triggered the change. If the metric hasn't returned to baseline, the change is ineffective — do not close the CR.

This coupling is what turns drift monitoring from a dashboard into an operational discipline.

---

## 9. Tooling

### What exists today

| Capability | Where | Covers |
|---|---|---|
| Layer C invariant audit | `scripts/audit_context_graph.py` | I3/I11/I13/I14 trends — usable drift signal for MOD-004 |
| Application logs | EC2 stdout | Pre-commit rejection rates — parseable for MOD-007 drift |
| Health score history | `HealthScore` table | MOD-011 distribution drift computable |
| Weight calibration history | `WeightCalibrationHistory` | MOD-002 delta analysis computable |

### What's missing

| Gap | Blocks |
|---|---|
| Backtest infrastructure for MOD-001 forecast vs. actual NRR | Entire Tier 1 forecasting quality claim |
| CRM reconciliation pipeline for MOD-004 | Revenue-at-risk drift detection |
| LLM fixture runner for MOD-007/008/014/015 | Silent LLM backend drift detection |
| Shadow-run infrastructure | Safe pre-deploy drift check |
| Alerting pipeline (metric → PagerDuty / ops channel) | All alert-driven response |
| Drift dashboards per model | Weekly operational review |

---

## 10. Prioritized Roadmap

Sequenced by "what fails first if unaddressed."

1. **LLM fixture runner for MOD-007** — silent backend drift here cascades through every downstream Tier 1 model. Highest immediate risk.
2. **Layer C audit on cadence + alerting wiring** — already have the audit; wire output to alerts and tenant baseline comparisons.
3. **NRR backtest infrastructure (MOD-001)** — CFO forecast claim is unvalidated without it.
4. **CRM reconciliation pipeline (MOD-004)** — enables monthly revenue-at-risk truth check; also surfaces other data issues.
5. **Playbook success-rate trend monitor (MOD-005)** — ROI stories driving enterprise sales need drift-proofing.
6. **Quarantine queue depth monitor (MOD-008)** — cheap to build; high blast-radius if queue stagnates.
7. **Wizard C weight-delta analysis (MOD-002)** — needed before opening recalibration to customer admins.
8. **Shadow-run framework** — force-multiplier for subsequent changes; lower priority than above.

**Commercially:** items 1–4 are the minimum set to credibly claim "CS Pulse has drift monitoring" in enterprise procurement conversations. Do not stretch that claim beyond what's actually shipped.

---

## 11. Open Items

- Define specific fixture-set content for MOD-007 (which signal/outcome pairs, adversarial cases)
- Decide alerting destination (PagerDuty / ops channel / email) — depends on ops model
- Who owns drift monitoring operationally — Model Owner, or a dedicated SRE-equivalent role?
- Customer-visible drift communication — do customers see "this metric is under review" when a Tier 1 model is in drift state?
- Coupling with SOC 2 CC7.2 (continuous monitoring) — formal mapping pending

---

## Change Log

| Date | Version | Change | Author |
|---|---|---|---|
| 2026-04-20 | 0.1 | Initial draft — three drift types, per-model metrics, fixture strategy, change-management coupling, prioritized roadmap | Engineering |
