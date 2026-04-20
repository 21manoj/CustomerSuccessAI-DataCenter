# CS Pulse — Change Management for AI/ML Models

**Document Version:** 0.1 (Initial Draft)
**Date:** April 20, 2026
**Classification:** Internal — Confidential
**Owner:** Engineering / Product / Compliance
**Status:** Living Document
**Parent:** [AI_GOVERNANCE_FRAMEWORK.md](AI_GOVERNANCE_FRAMEWORK.md)
**Companion:** [MODEL_INVENTORY.md](MODEL_INVENTORY.md)

---

## 1. Purpose

This document defines **how changes to AI/ML models get proposed, reviewed, approved, deployed, and verified** in CS Pulse. It enforces the separation-of-duties principle from the parent framework: *authors ≠ validators ≠ users*.

Every change to a production Tier 1 or Tier 2 model must follow this process. Deviations are compliance findings.

### Scope of "change"

A change is any of the following:

| Change Type | Examples | Typical Tier Affected |
|---|---|---|
| **Weight / threshold change** | Pillar weights, KPI weights, health thresholds (70/50), at-risk boundaries | MOD-002, MOD-011 |
| **Taxonomy change** | New polarity classification, new revenue-bucket entry, retiring a subtype | MOD-008, MOD-014 |
| **Prompt change** | LLM Tier 1 prompt edit, Ask AI system prompt, classification prompt | MOD-007, MOD-015 |
| **Model code change** | Wizard A/B/C algorithm edit, rule-engine logic, scoring formula | MOD-001, MOD-002, MOD-009 |
| **Calibration re-run** | Wizard C recalibration emits new weights for a customer | MOD-002 |
| **Feature flag / entitlement** | Enabling/disabling a model per-customer | All models |
| **New model deployment** | First-time launch (e.g. MOD-003 Renewal Probability when it ships) | Any |
| **Model retirement** | Shutting off a model or replacing it with a successor | Any |
| **Training data change** | Corpus update for future ML models (currently N/A) | Future |

Bug fixes that preserve behavior are out of scope and follow standard engineering change control.

---

## 2. Approval Matrix

Approval authority per tier, derived from [AI_GOVERNANCE_FRAMEWORK.md](AI_GOVERNANCE_FRAMEWORK.md) §5.

| Change Tier | Proposer | Reviewer(s) | Approver(s) | Re-validation Required? |
|---|---|---|---|---|
| **Tier 1 — revenue-touching** | Engineering or Product | **Independent validator** (not the author) + Compliance | **Dual approval**: Engineering Lead + (Product Lead OR Compliance Lead) | **Yes — mandatory before production** |
| **Tier 2 — operational** | Engineering or Product | One reviewer (not the author) | Single approver (Engineering Lead or Product Lead) | Recommended; required if logic change |
| **Tier 3 — information** | Any | Peer review | Single approver | On major version only |

**Separation-of-duties rule:** the author of a change **cannot** be in the approver list for their own change, even if they hold the approver role for other changes.

**Customer-scope exception:** Wizard C recalibration and taxonomy overlays scoped to a single tenant follow a lighter flow (see §5 "Customer-Scope Changes").

---

## 3. Standard Change Workflow

Applies to Tier 1 and Tier 2 changes by default. Sequential — each gate must pass before proceeding.

### Gate 1 — Propose

- Proposer opens a Change Request (CR) in the tracker. CR must include:
  - Affected Model ID (MOD-xxx) per [MODEL_INVENTORY.md](MODEL_INVENTORY.md)
  - Change Tier (1, 2, or 3)
  - Motivation (what problem; what data)
  - Diff (pointer to PR, SQL migration, config patch, or taxonomy JSON diff)
  - Expected impact (which downstream models, customers, or dashboards)
  - Rollback plan
  - Verification plan (how will we confirm success / detect regression)

### Gate 2 — Independent Review

- Reviewer(s) assigned per matrix. Reviewer **must not** be the proposer.
- Reviewer validates:
  - Impact analysis is honest (e.g. weight change flows through Health Score Rollup → every future CFO dashboard)
  - Rollback plan is executable (not "we'll just change it back" — needs specific SQL/command)
  - Tests or verification steps are runnable
  - For Tier 1: independent validator re-runs the model offline on a representative sample, compares outputs vs. current production
- Reviewer either approves, requests changes, or rejects with reason

### Gate 3 — Approval

- Per approval matrix. Dual approval for Tier 1.
- Approval is recorded in the CR with timestamp + approver identity.
- Approval scope is explicit: "approved for this change, not for future changes in this area."

### Gate 4 — Staged Deployment

- **Staging first.** Change applied to at least one non-production tenant or test customer.
- Smoke-test runs:
  - For weight changes: recompute health scores for a sample; compare delta distribution
  - For taxonomy changes: re-audit a pre-existing customer; violation count must not increase by more than N (defined per CR)
  - For prompt changes: re-run on a canned fixture set; outputs diffed
- Pass criteria defined in the CR's verification plan; failure = rollback before prod.

### Gate 5 — Production Deployment

- Deploy via standard release path (see [feedback_ec2_deploy.md](../../../../.claude/projects/-Users-manojgupta-CustomerSuccessAI-DataCenter/memory/feedback_ec2_deploy.md) — always `scripts/rehydrate-ec2-ecr.sh`; never `docker cp` or local builds)
- Immediate post-deploy: run Layer C audit on the canonical customer (385 or current-canonical); log baseline violation count
- Monitor the next 24h for violation drift

### Gate 6 — Post-Deploy Verification

- 24–48 hours after deploy:
  - Compare audit outputs vs. pre-deploy baseline
  - Compare Tier 1 dashboard headline numbers vs. expected
  - Check for customer-reported anomalies
- Update CR with verification result. Close CR only when verification passes.

### Gate 7 — Register Update

- Update [MODEL_INVENTORY.md](MODEL_INVENTORY.md):
  - "Last Validated" date
  - Change Log entry
  - Any new known limitations discovered during deployment
- Update relevant Model Card if the change affects inputs/outputs/method.

---

## 4. Emergency Change Process

A change is an emergency only if: (a) active data corruption is happening, (b) a customer-visible regression requires immediate fix, or (c) a security issue is being actively exploited.

**Not emergencies:** routine deploys, scheduled recalibrations, forgotten PRs.

### Emergency Workflow

1. **Declare** — proposer posts "AI-EMERGENCY" in the ops channel with one-line impact statement
2. **Single-approver fast path** — Engineering Lead approves verbally; audit trail follows
3. **Deploy** — change applied; minimal smoke test (Layer C audit on canonical customer)
4. **Post-hoc CR** — within 24 hours, full CR retrofit with:
   - What happened
   - What was changed
   - What the standard process would have caught
   - Whether the change should be reverted / refined

**Emergency retrofit rate is a metric:** if >20% of Tier 1 changes in a quarter are emergencies, the standard workflow needs adjustment (too slow) or the team discipline needs adjustment (shortcut culture).

---

## 5. Customer-Scope Changes

Some changes are scoped to a single tenant and don't affect global taxonomy or cross-customer math. Lighter process applies.

### Wizard C Recalibration (per-tenant)

- Customer admin or CS Pulse ops triggers `trigger_wizard('C')` for a customer
- Writes new weights to `CustomerConfig.dc2s_pillar_weights` + `dc2s_kpi_weights`
- Audit row written to `WeightCalibrationHistory`
- **Current state:** no pre-change impact simulation; no approval gate
- **Required enhancement:** preview-before-commit UI; independent approval if weight delta exceeds threshold (e.g. any pillar weight shifts > 20%)
- Re-validation: post-calibration health score distribution sanity check (no mass flip from Healthy → At-Risk without cause)

### Tenant-Scoped Taxonomy Overlay (future)

- If/when per-tenant taxonomy overlay ships: customer admin can add tenant-specific subtypes (polarity classification only; revenue-bucket stays global)
- Approval: tenant admin + CS Pulse curator review (not vendor approval, but visibility)
- Scope limit: cannot override global taxonomy; additive only

### Health Threshold Override (per-customer)

- `GET/PUT /api/dc2s/config/health-thresholds` allows customers to move the 70 / 50 boundaries
- Change is customer-scope and affects only their dashboards
- **Required enhancement:** impact summary ("X accounts would flip from Healthy to At-Risk at the new threshold") before confirmation; audit log entry with who changed what

---

## 6. Tooling & Enforcement

Change management lives across multiple systems today. This is the inventory, honest about what's missing.

| Concern | Current Tool | Gap |
|---|---|---|
| Code change tracking | Git + PR reviews | No model-specific CR template; PR checklist doesn't flag Tier 1 changes |
| Weight change audit | `WeightCalibrationHistory` table | No pre-change preview; no approval gate |
| Taxonomy change audit | To be built per `policy_taxonomy_runtime_auto_fix.md` | Admin UI + approval queue not shipped |
| Prompt change audit | **None — prompts live in Python source** | No prompt version register; no approval workflow |
| Feature flag audit | `feature_toggles.py` + per-customer DB | No change log |
| Deployment audit | Docker image tags + ECR push log | No link from image tag → CR |
| Customer-visible change notice | None | No "your platform changed X" notification path |

**Top-priority tooling gaps (in order of blast radius):**
1. Prompt version register for MOD-007 / MOD-015 (LLM prompts)
2. Approval gate UI for Wizard C recalibration (currently one-click, no preview)
3. Taxonomy approval queue UI (blocks MOD-008 from silent mis-bucketing)
4. CR template with Model ID / Tier / Rollback fields

---

## 7. Rollback Procedures

Every CR must specify a rollback. Generic patterns:

| Change Type | Rollback Pattern |
|---|---|
| Weight change | Restore prior weights from `WeightCalibrationHistory` or `bootstrap_weights_config.json`; recompute health for affected customers |
| Taxonomy change (JSON) | Revert JSON file, redeploy, re-audit; if auto-classified entries introduced, re-quarantine |
| Prompt change | Revert to prior prompt version; re-run on fixture set; no data backfill needed (LLM is stateless on its side) |
| Model code change | Standard git revert + redeploy via `rehydrate-ec2-ecr.sh` |
| Threshold change | Restore prior threshold value in `health_thresholds.json` + `CustomerConfig`; re-classify accounts |

**Data vs. code rollback:** code revert is always cleaner than data rollback. For Tier 1 changes that write data (weight calibrations, taxonomy approvals), rollback may leave an audit trail of corrections rather than truly reverse state. This is expected and preferred — auditors want to see the correction, not silent undo.

---

## 8. Audit Requirements

Every change emits the following audit artifacts:

- **CR record** in the tracker, indefinite retention
- **Git commit** with message referencing the CR
- **Approval record** — timestamps + approver identities
- **Deployment record** — image tag, time, actor
- **Post-deploy verification result** — tied back to CR

**Retention:** 7 years for Tier 1 change records (matches SOX retention for material financial inputs). 3 years for Tier 2. 1 year for Tier 3.

See [AUDIT_TRAIL_REQUIREMENTS.md](AUDIT_TRAIL_REQUIREMENTS.md) (to be written) for full logging spec.

---

## 9. Metrics

Track and report quarterly:

- **% of Tier 1 changes following standard workflow** (target: 100%)
- **% emergency changes** (target: <20% of Tier 1 changes in any quarter)
- **Average time from proposal to production** (track, don't target — too short suggests rushed review)
- **Regression rate** — % of Tier 1 changes that required rollback or hotfix within 7 days (target: <5%)
- **Audit-finding rate** — % of Tier 1 changes missing CR, missing approval record, or missing verification result (target: 0%)

---

## 10. Open Items

1. CR template — needs to exist in the tracker with Model ID / Tier / Rollback / Verification fields
2. Prompt version register — needed before MOD-007 change-control is real
3. Wizard C preview-before-commit UI — blocks legitimate change-management for MOD-002
4. Taxonomy approval queue UI — blocks MOD-008 governance
5. Customer-visible change notice path — required for EU AI Act Article 13 transparency obligations
6. Training data change control — not in scope today (no ML training), but reserve a section for when MOD-003 ships

---

## Change Log

| Date | Version | Change | Author |
|---|---|---|---|
| 2026-04-20 | 0.1 | Initial draft — approval matrix, 7-gate workflow, emergency process, customer-scope exceptions, tooling gap inventory | Engineering |
