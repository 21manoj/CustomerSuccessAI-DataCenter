# CS Pulse — Governance Roadmap & Beta Customer Disclosure

**Document Version:** 2.0
**Date:** April 21, 2026
**Classification:** Shareable with beta customers under NDA
**Owner:** Product / Engineering / Compliance
**Status:** Living Document
**Parent:** [AI_GOVERNANCE_FRAMEWORK.md](AI_GOVERNANCE_FRAMEWORK.md)
**Addendum:** [QUALITATIVE_SIGNAL_GOVERNANCE.md](QUALITATIVE_SIGNAL_GOVERNANCE.md)

## Changes in v2.0 (Apr 21, 2026)

- **MOD-012 Signal Processing Pipeline unblock-criteria now specified** (Phase 1). Previously said "must ship with full governance" without defining what that meant. Now specifies: fixture runs, inter-rater reliability sampling at 10%, provenance completeness ≥95%, PII handling ruleset applied.
- **New Phase 1 item: Manifest qualitative-signal provenance backfill.** Manifests currently seed narrative OUTCOMEs with empty evidence fields. To make demos behave like production, manifests must also seed `qualitative_signals.csv` entries that narrative OUTCOMEs reference via `source_event_id`.
- **Revised narrative-filter strategy.** The `include_narrative=False` defaults shipped Apr 20 are demo-safe (manifest outputs lack provenance) but NOT the right long-term production default. Once qualitative ingestion pipeline lands with provenance, filters come off and confidence markers (via existing `tier` + `confidence` fields) differentiate earned vs scripted narrative.
- **New Phase 1 item: CSM-facing leading-vs-trailing dual-view.** Dashboard widget that shows qualitative signals + quantitative health side-by-side so CSMs can act on leading signals before trailing catches up. This is the product's differentiator; currently invisible in UI.

---

## 1. Purpose

Two audiences, one document:

1. **Internal:** a prioritized roadmap of governance gaps, sequenced by beta/post-beta phases, so engineering investment is deliberate rather than reactive.
2. **Beta customers:** an honest disclosure of what's in place today, what's a known gap, and when each gap is expected to close.

**Investment stance (April 2026):** no further governance engineering investment is committed until beta customers sign. This document makes the gap list transparent so beta customers are choosing CS Pulse with full awareness — not surprised later.

---

## 2. Current Reality — What's In Place Today

As of April 20, 2026, the following governance controls are **shipped and operating:**

| Control | Evidence | Mapped To |
|---|---|---|
| Context Graph Invariants — 13 invariants, 3 layers (pre-commit gate, pytest CI, audit CLI) | [utils/context_graph_invariants.py](../../backend/utils/context_graph_invariants.py), [tests/test_context_graph_invariants.py](../../backend/tests/test_context_graph_invariants.py), [scripts/audit_context_graph.py](../../backend/scripts/audit_context_graph.py) | SOC 2 CC7.2, CC7.3; SR 11-7 ongoing monitoring |
| Pre-commit edge validation gate | `upsert_edge` / `upsert_node` in `utils/context_graph.py` | Data integrity at write time |
| Wizard C calibration audit table | `WeightCalibrationHistory` | SR 11-7 model change log (partial) |
| Playbook lifecycle audit | `PlaybookExecution` table | ROI attribution evidence |
| Multi-tenant isolation | `customer_id` foreign keys; row-level filtering | SOC 2 CC6.1 |
| Password hashing | bcrypt via werkzeug | SOC 2 CC6.1 |
| API key hashing | SHA-256; scope + account restriction | SOC 2 CC6.1 |
| RBAC scaffolding (role, allowed_account_ids, allowed_customer_ids, is_contractor, expires_at) | User model | SOC 2 CC5.2 (partial) |
| Basic activity logging (admin actions, logins) | `activity_logging.py` | SOC 2 CC4.1 (partial) |
| Seven governance documents (this doc + 6 companions) | `docs/governance/` | SR 11-7 documentation; SOC 2 CC3, CC4, CC7, CC8 evidence layer |

---

## 3. Gap Register — Prioritized

All known gaps, sequenced into three phases. **Phase 0 is documentation only** (no engineering cost). **Phases 1 and 2 are blocked behind beta-customer signing.**

### Phase 0 — Pre-Beta (Documentation Only, NOW)

No engineering investment required. Completes the transparency and trust surface.

| ID | Gap | Effort | Status |
|---|---|---|---|
| G0.1 | AI Governance Framework umbrella | Complete | ✅ Done |
| G0.2 | Model Inventory register (15 models) | Complete | ✅ Done |
| G0.3 | Change Management workflow doc | Complete | ✅ Done |
| G0.4 | Audit Trail Requirements spec | Complete | ✅ Done |
| G0.5 | Drift Monitoring spec | Complete | ✅ Done |
| G0.6 | SOC 2 plan v1.1 refresh | Complete | ✅ Done |
| G0.7 | RBAC plan v1.1 refresh (Independent Validator + Taxonomy Curator roles) | Complete | ✅ Done |
| G0.8 | Beta Customer Disclosure (this document) | Complete | ✅ Done |
| G0.9 | Model Cards (per-Tier-1 model detail beyond inventory) | 2–3 days | Pending — write before beta kick-off |
| G0.10 | Incident Response plan (AI-specific) | 1–2 days | Pending — write before beta kick-off |

### Phase 1 — Beta Launch Minimum (~4–6 weeks eng after beta signing)

Minimum viable governance to responsibly operate with paying customers. Anything below this line is a precondition for a Tier 1 enterprise contract.

| ID | Gap | Effort | Beta-Customer Impact If Deferred |
|---|---|---|---|
| G1.1 | **MFA on all user accounts** (TOTP or WebAuthn) | 1 week | Procurement gate at any serious enterprise; breach-risk exposure |
| G1.2 | **Encryption at rest** (migrate PostgreSQL to RDS with KMS) | 1–2 weeks | Procurement gate; SOC 2 Type I blocker |
| G1.3 | **Remove default secrets** (SECRET_KEY, POSTGRES_PASSWORD) from docker-compose | 1 day | Credential-rotation risk |
| G1.4 | **Automated backups + tested restore** (RDS snapshots + monthly restore drill) | 1 week | Data loss risk; no RPO commitment possible |
| G1.5 | **LLM fixture runner for MOD-007** | 3–5 days | Silent LLM backend drift could misclassify causal polarity undetected |
| G1.6 | **Prompt version register + `model_version` field on decision rows** | 3–5 days | Cannot reproduce an LLM decision for audit; change management has no unit of record |
| G1.7 | **Vertical-aware taxonomy JSON refactor** — base + per-vertical overlay files (`config/taxonomy_base.json` + `taxonomy_dc2_s.json`, `taxonomy_saas_premium.json`, `taxonomy_healthcare_provider.json`), loaded via same base+overlay pattern as KPI catalogs in `vertical_registry.py`. Includes (a) JSONSchema validator + fail-fast boot (per-file; overlays validate against base for no-conflict), (b) paired pytest fixture requirement enforced by meta-test, (c) LLM prompt allowed-subtype list generated from effective taxonomy at runtime. Overlays are additive — cannot flip polarity on a globally-defined subtype. Foundation for CDI DNA templates (each future vertical = a curated overlay). | 3–5 days (loader + validator + prompt generator; JSON content is small per file) | New manifests trip hardcoded-list surprises; dev-scope iteration bottleneck; blocks CDI productization |
| G1.8 | **Quarantine queue** for Tier 1 taxonomy classifications (revenue-bucket) | 1 week | Policy commitment to "review-first for $$" is unenforceable without the queue |
| G1.9 | **Independent Validator role** live in RBAC + separation-of-duties invariant on approval-event table | 1 week | SOX / SR 11-7 separation-of-duties violated on every Tier 1 change today |
| G1.10 | **Incident Response plan in use** (drill run, runbook exercised) | 1 day + ongoing | First incident with a paying customer has no process to follow |
| G1.11 (v2) | **MOD-012 Signal Processing Pipeline unblock-criteria** — ship with fixture runs (50-150 pairs), inter-rater reliability sampling at 10%, provenance completeness ≥95%, PII handling ruleset v1 applied. Per [QUALITATIVE_SIGNAL_GOVERNANCE.md](QUALITATIVE_SIGNAL_GOVERNANCE.md) §3 + §7 item 1. | 2 weeks | Qual-source model without these controls cannot produce defensible leading-indicator outputs |
| G1.12 (v2) | **Manifest qualitative-signal provenance backfill** — manifests seed `qualitative_signals.csv` entries; narrative OUTCOMEs reference them via `source_event_id`. Demo tenants behave like production tenants on provenance shape. | 1 week | Demo narrative OUTCOMEs currently have empty evidence; buyer AI-DD drill-down surfaces the gap |
| G1.13 (v2) | **Qualitative-decision audit fields live in DB** — prompt_version, base_model_version, reasoning_trace (sampled), evidence_provenance, pii_handling_version, inter_rater_sample_flag. Per [AUDIT_TRAIL_REQUIREMENTS.md](AUDIT_TRAIL_REQUIREMENTS.md) §2.1.1. | 1 week | Without these, qualitative decisions are not reconstructible for regulator replay |
| G1.14 (v2) | **CSM leading-vs-trailing dual-view** — dashboard widget showing qualitative signals + quantitative health side-by-side so CSMs can act on leading signals in the 30-60 day lead window. Surfaces the product's core differentiator; currently invisible in UI. | 1-2 weeks | Product USP (two-layer indicator model) has no dedicated UI surface |

**Phase 1 total eng estimate (v2):** ~9-10 weeks with one engineer focused; ~5 weeks parallelized across two. v1 estimate was ~6 weeks; v2 adds ~3-4 weeks for the qualitative-specific controls that were under-specified in v1.

### Phase 2 — Beta to GA (~3–4 months post-Phase 1)

Controls required before exiting beta / signing larger enterprise contracts.

| ID | Gap | Effort | Trigger |
|---|---|---|---|
| G2.1 | NRR forecast backtest infrastructure for MOD-001 | 2 weeks | Any customer asking "how accurate is your forecast" |
| G2.2 | CRM reconciliation pipeline for MOD-004 revenue-at-risk | 2 weeks | Finance-side integration required |
| G2.3 | Change-approval workflow UI (CR template, dual-approval gate for Tier 1) | 2–3 weeks | Scale beyond 2 engineers making changes |
| G2.4 | Preview-before-commit UI for Wizard C recalibration | 1 week | First customer admin given calibration authority |
| G2.5 | Access event logging + RBAC-gated audit query UI | 2 weeks | SOC 2 Type I audit engagement |
| G2.6 | Input snapshot store for Tier 1 decisions (replay capability) | 2 weeks | First regulator / auditor replay request |
| G2.7 | LLM request/response capture (PII-safe) for MOD-007, MOD-015 | 2 weeks | First customer asks to see what their data looks like to Claude |
| G2.8 | Hash-chain on Tier 1 audit tables (tamper-evidence) | 1–2 weeks | Type II readiness |
| G2.9 | Counterfactual baseline for MOD-005 playbook ROI | 3+ weeks | First CFO asks "what would have happened without the playbook" |
| G2.10 | Customer-facing transparency page (`/settings/taxonomy-health`) | 1 week | EU AI Act Article 13 obligation |
| G2.11 | SSO/SAML (planned per RBAC plan) | 3 weeks | First enterprise with IdP requirement |
| G2.12 | Drift alerting pipeline (metric → PagerDuty / ops channel) | 1 week | Operational maturity |
| G2.13 | Immutable backup with S3 Object Lock | 1 week | Long-term retention integrity |
| G2.14 | Field-level PII encryption (email, phone, stakeholder names) | 3 weeks | Healthcare / regulated verticals |

### Phase 3 — Enterprise Maturity (post-GA)

Controls required for heavily regulated verticals (banking, insurance, healthcare).

| ID | Gap | Trigger |
|---|---|---|
| G3.1 | Uncertainty bounds on MOD-001 NRR forecast and MOD-006 Power-of-1 | First CFO push-back on point-estimate forecasts |
| G3.2 | Shadow-run framework for safe pre-deploy drift check | Operational maturity |
| G3.3 | Hallucination sampling for MOD-015 Ask AI | Safety incident or customer complaint |
| G3.4 | Full EU AI Act risk classification per Tier 1 model + Article 11 technical documentation | First EU customer |
| G3.5 | NIST AI RMF formal mapping | First federal / fed-adjacent customer |
| G3.6 | ISO 42001 AI Management System alignment | Forward-looking enterprise RFP |
| G3.7 | SCIM auto-provisioning | Large-customer IT requirement |
| G3.8 | Pen test + OWASP scanning + Dependabot | SOC 2 Type II engagement |
| G3.9 | Privacy policy, data retention, DSR (GDPR/CCPA) | First EU / California consumer-facing data |
| G3.10 | Cross-region DR | Enterprise SLA (99.95%+) |

---

## 4. Beta Customer Disclosure

> This section is intentionally written to be shared (under NDA or MSA) with beta customers so they engage with CS Pulse knowing exactly what they're buying.

### What you're getting today

- **A working AI-native CS platform** with causal context graph, health scoring, playbooks, NRR forecasting, and revenue-at-risk intelligence across CRO / CFO / VP CS / CSM personas.
- **A documented governance framework** — the doc set in `docs/governance/` — mapped to SR 11-7, SOC 2, EU AI Act, and NIST AI RMF requirements. We wrote these before enterprise procurement asks for them.
- **Operating data-quality controls** — the Layer A/B/C invariant validator is in production and catches causal-chain integrity issues at write time, at ingest, and via an auditable CLI.

### What's not yet in place (honest gap list)

We have documented 30+ governance gaps in the roadmap above. The ones beta customers should be most aware of:

| Gap | What It Means For You | When We Plan To Close It |
|---|---|---|
| No MFA | Today your users log in with email + password. Not yet enterprise-grade. | Phase 1 (first 6 weeks post-signing) |
| No encryption at rest | Database is not yet encrypted. We run on AWS which provides physical/network controls, but disk-level encryption is pending. | Phase 1 |
| No independent validator role | Today the same person who tunes a model can approve their own changes. SOX separation-of-duties is not enforced. | Phase 1 |
| No SSO/SAML | Your users cannot yet sign in via Okta/Azure AD/Google Workspace. | Phase 2 |
| No formal drift monitoring on NRR forecast | Our NRR forecasts are not yet backtested against realized outcomes. We will be honest about forecast accuracy as data accrues. | Phase 2 |
| No SOC 2 certification | Type I targeted October 2026; Type II targeted June 2027. | Phase 2 → Phase 3 |
| No formal incident response plan exercised | We have a plan draft; we have not yet run a drill. | Phase 1 |
| No customer-facing transparency page | You cannot yet self-serve view "what taxonomy is active on my tenant." Today, ask your CS Pulse contact. | Phase 2 |

### Why we're telling you this

Three reasons:

1. **Enterprise procurement will ask.** Better you hear the gaps from us first than discover them in a security review.
2. **We will not silently defer.** Every gap above has a phase assigned. If we slip a phase, you will be told, not surprised.
3. **Beta pricing reflects beta risk.** The commercial arrangement explicitly recognizes that beta customers are operating ahead of full governance. When a gap closes, the risk-adjustment ends.

### What we commit to during your beta

- **Monthly governance update** — a one-page report on which gaps closed, which shifted, any incidents and their handling
- **Quarterly review** — a joint session with your security / compliance team on the state of the register
- **Immediate disclosure** — if a gap above translates into a customer-visible incident, you hear from us within 24 hours
- **No silent model changes** — any Tier 1 model change (NRR, revenue-at-risk, ROI attribution, weight calibration) is logged and visible on request during this period

### What you can do to help

- Tell us which gaps matter most to **your** procurement / security team. The roadmap above is our sequencing; your priorities may shift it.
- Request the monthly governance report. If you don't request it, we'll still produce it, but we'd rather know who's reading it.
- Flag any incident you believe we should have caught. Post-mortem visibility closes gaps faster than roadmaps.

---

## 5. Internal Operating Discipline

Even in "no further investment until beta" mode, three behaviors must hold:

1. **No new Tier 1 model ships without governance in place.** MOD-003 (Renewal Probability Model) and MOD-012 (Signal Processing Pipeline) are spec'd but **blocked from production launch** until the Phase 1 controls for their tier are operational. Shipping them today creates regulatory liability.
2. **Every hotfix touching Tier 1 logic gets a post-hoc CR retrofit within 24 hours.** Per [CHANGE_MANAGEMENT.md](CHANGE_MANAGEMENT.md) §4 emergency process.
3. **The audit CLI (Layer C) runs on the canonical demo customer (385) on every deploy.** If violation count increases, the deploy is rolled back before sales demos resume.

These are discipline commitments, not engineering investments — they cost only attention.

---

## 6. Phase Gate Criteria

Criteria that signal "ready to move from Phase N to Phase N+1":

| Transition | Signal |
|---|---|
| Phase 0 → Phase 1 | First beta customer signed + contract language incorporating this disclosure |
| Phase 1 → Phase 2 | All Phase 1 items shipped; zero audit violations on Tier 1 canonical customer for 2 consecutive months; no incident requiring emergency CR in prior month |
| Phase 2 → Phase 3 | SOC 2 Type I passed; at least one enterprise customer in production with no open procurement conditions on governance |

---

## Change Log

| Date | Version | Change | Author |
|---|---|---|---|
| 2026-04-20 | 0.1 | Initial roadmap + beta disclosure | Product / Engineering |
| 2026-04-21 | 2.0 | Added Phase 1 items G1.11-G1.14 covering qualitative-specific controls (MOD-012 unblock-criteria, manifest provenance backfill, qualitative audit fields, CSM dual-view). Phase 1 estimate bumped from ~6 to ~9-10 weeks. Prompted by the two-layer indicator model being named as the core product differentiator. | Product / Engineering |
