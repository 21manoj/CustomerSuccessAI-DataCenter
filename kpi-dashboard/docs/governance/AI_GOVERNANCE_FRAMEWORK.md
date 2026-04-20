# CS Pulse — AI Governance Framework

**Document Version:** 0.1 (Initial Draft)
**Date:** April 20, 2026
**Classification:** Internal — Confidential
**Owner:** Engineering / Product / Compliance
**Status:** Umbrella Framework — Living Document

---

## 1. Purpose

CS Pulse is an AI-native platform whose outputs directly influence CRO/CFO decisions about revenue, renewal risk, and investment allocation. Enterprise and regulated-industry buyers (banking, healthcare, insurance) will require documented AI governance as a procurement gate.

This document is the **umbrella framework**. It does not duplicate existing artifacts — it maps every AI/ML decision point in the platform to the governance controls, responsible roles, and regulatory frameworks that apply.

### Principle

> **Authors ≠ Validators ≠ Users.**
> Whoever builds a model cannot be the sole approver. Users consume outputs; they do not modify model behavior.
> Customers pick (from curated DNA templates). Curators author (with approval queues). Validators audit (via invariants + drift monitors).

---

## 2. Three-Role Model

| Role | Responsibility | Who (CS Pulse) |
|---|---|---|
| **Model Owner / Author** | Designs, implements, prompt-engineers, curates inputs | CS Pulse Engineering + Domain Curators |
| **Validator / Reviewer** | Independent testing: bias, drift, accuracy, polarity. Signs off before changes reach production. | CS Pulse QA + Compliance; customer's risk team for on-prem deployments |
| **Consumer / User** | Uses outputs, flags anomalies, escalates | End-users: CSM, VP CS, CRO, CFO |

**Separation of duties is enforced by:**
- Role-based access in RBAC ([RBAC_SSO_Implementation_Plan.md](RBAC_SSO_Implementation_Plan.md))
- Change approval workflows in admin UI (per decision point)
- Audit trail in ContextEdge + application logs
- Independent validator role must exist before SOC 2 Type II ([SOC2_Compliance_Plan.md](SOC2_Compliance_Plan.md) §6)

---

## 3. Decision Point Inventory — Tier Classification

Each AI/ML decision point in CS Pulse is tiered by blast radius. Tier determines required controls.

### Tier 1 — Revenue & Financial Impact (Highest Control)

Direct claim on money, attribution, or forecast. SR 11-7-equivalent model risk management applies.

| Decision Point | Owner | Validator | Current Controls | Gaps |
|---|---|---|---|---|
| **Wizard B (NRR Forecast + Pattern Analysis)** | Eng | — (same person) | ContextNode audit trail | Independent validator; drift monitor |
| **Wizard C (Weight Calibration)** | Eng | — | WeightCalibrationHistory table | Pre-change impact simulation; independent approval |
| **Renewal Probability Model** (spec'd) | — | — | Not yet shipped | Full governance before launch |
| **Revenue-at-Risk Calculation** | Eng | Layer C audit | Invariants I3/I11/I13/I14 | Monthly drift report |
| **Playbook ROI Attribution** | Eng | — | Playbook lifecycle table | Causal traceability doc per PB |
| **Power-of-1 Scaling / Investment Allocation** | Product | — | Read-only output | Assumptions & bounds documentation |
| **LLM Tier 1 Edge Enrichment (polarity/causal)** | Eng | Pre-commit gate | [Context Graph Invariants](../../../../.claude/projects/-Users-manojgupta-CustomerSuccessAI-DataCenter/memory/context_graph_invariants.md) Layer A/B/C | Prompt version control; output sampling for drift |
| **Taxonomy Revenue-Bucket Classification** | Curator | Dev review | Quarantine-before-use (per policy) | Admin UI approval queue |

### Tier 2 — Operational Decisions (Standard Control)

Influences CSM prioritization, playbook selection, or classification used downstream. Should have three-role separation; drift monitoring acceptable monthly.

| Decision Point | Owner | Validator | Current Controls | Gaps |
|---|---|---|---|---|
| **Wizard A (Arc Classification)** | Eng | Layer C audit | Pre-commit gate I1/I2 | Classification confidence threshold; misclass review |
| **Playbook Recommendation Engine** | Product | — | Catalog-driven | Audit log of why each PB was recommended |
| **Health Score Thresholds + Pillar Weights** | Product | CustomerConfig | Centralized in health_thresholds.json | Change approval workflow |
| **Signal Processing Pipeline** (email/Slack/transcript) | Eng | — | Not yet shipped | Full 3-role from day 1 |
| **Stakeholder Mapping / Champion Detection** | Eng | — | Manual curation | Confidence scoring; override audit |
| **Taxonomy Polarity Classification (signal subtypes)** | Curator | Admin queue | Silent auto-classify with audit-visible flag | 30-day review SLA enforcement |

### Tier 3 — Information Surface (Light Control)

Read-only, summarization, or retrieval. Governance focus: PII, output quality, logging.

| Decision Point | Controls Required |
|---|---|
| **Ask AI / RAG Chatbot** | PII filter on input/output; session logging; hallucination sampling |
| **Journey Timeline Generation** | Source traceability to ContextNode IDs |
| **Context Graph Mermaid Rendering** | Display-only; no governance concern beyond CSS/accessibility |
| **CSM Scorecard / Capacity Display** | Data-source attribution |

---

## 4. Regulatory Framework Mapping

How CS Pulse controls map to external frameworks buyers will reference.

| Framework | Applies To | CS Pulse Coverage |
|---|---|---|
| **SR 11-7 (Fed/OCC Model Risk Management)** | US banking customers — all Tier 1 decision points | Partial. Model inventory missing; independent validator missing. |
| **SOC 2 Type II** | All enterprise customers | In progress — see [SOC2_Compliance_Plan.md](SOC2_Compliance_Plan.md) |
| **EU AI Act (Article 6, 9, 14 — High-Risk AI Systems)** | EU customers; any use in employment/credit decisions | Gap — risk classification per Tier 1 model needed |
| **NIST AI RMF** | US federal / enterprise voluntary | Aligned structurally; formal mapping doc needed |
| **ISO 42001 (AI Management System)** | Forward-looking enterprise buyers | Not yet addressed |
| **SOX (Separation of Duties)** | Any customer where CS Pulse outputs feed revenue-recognition inputs | Requires author ≠ approver; not yet enforced in tooling |
| **HIPAA** | Healthcare customers (e.g. Relay Healthcare) | Out of scope for this doc; covered in data-handling policy |
| **FINRA** | Brokerage-adjacent use cases | Deferred |

---

## 5. Controls Required Per Tier

| Control | Tier 1 | Tier 2 | Tier 3 |
|---|---|---|---|
| Model Card (inputs, outputs, assumptions, limitations) | **Required** | Required | Recommended |
| Model Inventory Register entry | **Required** | Required | Optional |
| Independent Validator sign-off before production | **Required** | Recommended | Not required |
| Change Management Approval Workflow | **Required** (dual approval) | Required (single approver) | Logged |
| Drift Monitoring | **Monthly** | Quarterly | None |
| Audit Trail of Output | **Per decision** | Per session | Session-level |
| PII / Privacy Review | Required | Required | **Required** |
| Public-facing Transparency (customer-visible) | Required | Recommended | Optional |
| Re-validation on Retraining / Prompt Change | **Mandatory before prod** | Recommended | On major version |

---

## 6. Related Documents

**In-scope — referenced here, authored separately:**
- [SOC2_Compliance_Plan.md](SOC2_Compliance_Plan.md) — security + controls framework
- [RBAC_SSO_Implementation_Plan.md](RBAC_SSO_Implementation_Plan.md) — role enforcement in code
- [HA_Scaling_Robustness_Plan.md](HA_Scaling_Robustness_Plan.md) — availability controls
- Context Graph Invariants (Layer A/B/C) — production data-quality validator ([source code](../backend/utils/context_graph_invariants.py))

**To author (identified gaps):**
- `MODEL_INVENTORY.md` — the SR 11-7 register; one row per Tier 1 & Tier 2 model
- `MODEL_CARDS/` — one card per Wizard A/B/C, LLM Tier 1, Taxonomy Classifier, Renewal Probability Model
- `CHANGE_MANAGEMENT.md` — approval workflow for weight/taxonomy/prompt changes
- `AUDIT_TRAIL_REQUIREMENTS.md` — what is logged, retention, access controls
- `DRIFT_MONITORING.md` — metrics per model, thresholds, alert paths
- `INCIDENT_RESPONSE_AI.md` — what happens when a model misclassifies at scale

---

## 7. Open Gaps (April 2026)

**Critical for enterprise/regulated-vertical sales:**
1. **No independent validator role** — today Author = Validator for all Wizards
2. **No Model Inventory register** — regulators will ask for this on day one of due diligence
3. **No drift monitoring** on Tier 1 models (NRR forecast accuracy, revenue-at-risk calibration)
4. **No change-approval workflow UI** for weight/taxonomy/prompt changes (today: code commit = approval)
5. **Prompt version control** for LLM Tier 1 not formalized (prompts live in Python source)

**Important but not blocking:**
6. No EU AI Act risk classification per Tier 1 model
7. No formal NIST AI RMF mapping document
8. No customer-facing transparency page for Tier 1 outputs (planned per `/settings/taxonomy-health` design)

---

## 8. Ownership & Review Cadence

- **Framework Owner:** TBD (recommend a cross-functional triad: Eng Lead + Product Lead + Compliance Lead)
- **Review Cadence:** Quarterly; immediate review on material changes (new Tier 1 model, new regulatory requirement, major incident)
- **Change Log:** maintained at bottom of this document

---

## Change Log

| Date | Version | Change | Author |
|---|---|---|---|
| 2026-04-20 | 0.1 | Initial umbrella draft | Engineering |
