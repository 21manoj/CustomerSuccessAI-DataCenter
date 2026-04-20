# CS Pulse — Audit Trail Requirements

**Document Version:** 0.1 (Initial Draft)
**Date:** April 20, 2026
**Classification:** Internal — Confidential
**Owner:** Engineering / Compliance
**Status:** Living Document
**Parent:** [AI_GOVERNANCE_FRAMEWORK.md](AI_GOVERNANCE_FRAMEWORK.md)
**Companions:** [MODEL_INVENTORY.md](MODEL_INVENTORY.md), [CHANGE_MANAGEMENT.md](CHANGE_MANAGEMENT.md)

---

## 1. Purpose

Audit trails are the **evidence layer** that proves CS Pulse governance controls are functioning. Without them:

- SR 11-7: "show me the history of every weight calibration on this model" — unanswerable
- SOC 2 CC7.2: "when did this classification flip and who approved it" — unanswerable
- EU AI Act Article 12: "provide the automatically generated logs for this high-risk AI system" — unanswerable
- SOX: "demonstrate separation of duties for this financial-input model change" — unanswerable

This document defines **what must be logged, how it's stored, how long it's retained, and who can access it** for every AI/ML model operating in CS Pulse.

### Governing principle

> **If a model produced a number that a human is acting on, the logs must allow a third party to reconstruct how the model arrived at that number — and when.**

---

## 2. What Must Be Logged

Every significant AI/ML event generates an audit record. Five event categories:

### 2.1 Decision Events

Per model output that a human or downstream system acts on.

| Field | Required For | Notes |
|---|---|---|
| `event_id` | All | UUID |
| `timestamp_utc` | All | ms precision |
| `model_id` | All | MOD-xxx per MODEL_INVENTORY |
| `model_version` | All | Code SHA or semver; LLM prompt version for MOD-007/015 |
| `customer_id` + `account_id` | Most | Omit for cross-tenant decisions |
| `actor` | All | User ID, system component, or `"model"` |
| `inputs_hash` | All | SHA256 of canonical input; **never raw inputs** in default log |
| `inputs_snapshot_ref` | Tier 1 | Pointer to short-term input store (see §5) |
| `output` | All | The classification, number, or edge produced |
| `confidence` | Tier 1 / LLM | Model-reported confidence ∈ [0,1] |
| `polarity` + `bucket` | MOD-007, MOD-008, MOD-014 | If classification output |
| `source_platform` | Graph decisions | Already captured in ContextEdge |
| `invariant_violations` | All graph writes | JSON array of invariant IDs violated |

### 2.2 Change Events

Any weight, threshold, taxonomy, prompt, or code change. Covered in [CHANGE_MANAGEMENT.md](CHANGE_MANAGEMENT.md) §8 but the log record lives here.

| Field | Required |
|---|---|
| `cr_id` | Yes |
| `model_id` | Yes |
| `change_type` | Yes (weight / taxonomy / prompt / code / threshold / flag) |
| `before_state` | Yes |
| `after_state` | Yes |
| `proposer_id`, `reviewer_ids`, `approver_ids` | Yes — separation-of-duties evidence |
| `deployment_image_tag` | Yes for code changes |
| `rollback_plan_ref` | Yes |
| `verification_result` | Yes (after Gate 6) |

### 2.3 Approval Events

Separated from change events to make separation-of-duties auditable as a standalone stream.

| Field | Required |
|---|---|
| `cr_id` | Yes |
| `approver_id` | Yes |
| `approval_type` | Review / Primary Approval / Secondary Approval |
| `timestamp_utc` | Yes |
| `justification` | Required for Tier 1 |
| `delegated_from` | If applicable |

### 2.4 Access Events

Who viewed audit logs, who ran audit queries, who exported data.

| Field | Required |
|---|---|
| `user_id` | Yes |
| `query_or_endpoint` | Yes |
| `customer_scope` | Yes — which tenant's data was accessed |
| `row_count_returned` | Yes |
| `export_destination` | If export |

### 2.5 Incident Events

Model misclassification at scale, drift alert, rollback, customer-reported anomaly.

| Field | Required |
|---|---|
| `incident_id` | Yes |
| `model_id` | Yes |
| `detection_source` | Drift monitor / customer report / internal audit |
| `scope` | Customers / rows affected |
| `remediation_cr_id` | If a CR was opened |

---

## 3. Per-Tier Logging Requirements

How detailed the audit trail must be, by model tier.

| Capability | Tier 1 | Tier 2 | Tier 3 |
|---|---|---|---|
| Decision events logged | **Every decision** | Sampled (≥10%) + all outlier decisions | Session-level |
| Input snapshot retained | Yes (short-term) | Hashed only | Hashed only |
| Change events | Full §2.2 schema | Full §2.2 schema | §2.2 minus verification_result |
| Approval events | **Dual-approver chain** | Single approver | Logged, no gate |
| Access events | Yes | Yes | Sampled |
| Incident events | Mandatory | Mandatory | Best-effort |
| Immutability guarantee | **Append-only, hash-chained** | Append-only | Standard write-once |
| Retention | 7 years | 3 years | 1 year |

**Append-only + hash-chained** for Tier 1 means: each new audit row includes a hash of the prior row in its chain, making silent tampering detectable. Standard append-only (Tier 2) relies on DB roles + backup integrity.

---

## 4. What's Already in Place vs. Missing

Honest inventory against the requirements above.

### 4.1 In Place

| Audit Surface | Covers | Source |
|---|---|---|
| `ContextNode` + `ContextEdge` | Graph decisions — source_platform, created_by, created_at, confidence, properties JSONB | [models.py](../../backend/models.py) |
| `HealthScore` history | Health rollup decision snapshots | models.py |
| `DC2SKPI` measurements | KPI input snapshots with timestamps | models.py |
| `WeightCalibrationHistory` | Wizard C calibration events | models.py |
| `PlaybookExecution` lifecycle | Playbook triggered/closed events | models.py |
| `SignalHistory` | Signal emission events | models.py |
| Application logs (stdout) | Operational actions, invariant warnings | Docker stdout → EC2 logs |
| Git + PR history | Code changes | GitHub |
| Docker image tags | Deployment artifacts | ECR |

### 4.2 Missing (Gap List)

| Missing | Blocks |
|---|---|
| **Prompt version register** for MOD-007 and MOD-015 | Reproducing an LLM decision — which prompt was active when? |
| **Model version field in decision-producing rows** | Same — can't tie a decision to its model version without SHA on row |
| **Approval event table** — separate from change event | Dual-approval auditability per SOX separation-of-duties |
| **Access event logging** | SOC 2 CC6.1 (logical access) — who read what |
| **Input snapshot store (short-term)** for Tier 1 decisions | Replay: "rerun this MOD-001 forecast with its original inputs" |
| **Hash-chain on Tier 1 audit tables** | Tamper detection |
| **User-action audit** for admin UI changes (threshold overrides, feature toggles) | Evidence that a customer admin changed something |
| **LLM request/response capture** for MOD-007 | Debugging misclassification; regulator request |
| **Audit query UI** | Accessing audit data today requires SQL — no role-gated UI |
| **Export audit trail** | Regulators / customers will request exports |

---

## 5. Storage & Retention

### 5.1 Storage Classes

Three storage tiers — hot, warm, cold — based on access frequency and size.

| Class | What Lives Here | Access Pattern | Cost |
|---|---|---|---|
| **Hot (Postgres tables)** | Decision events of last 90 days; active change events; all approval events | Online queries, dashboards | High per GB |
| **Warm (S3, queryable)** | Decision events 90 days–2 years; archived input snapshots | Ad-hoc queries via Athena | Low per GB |
| **Cold (S3 Glacier)** | Anything older than 2 years for Tier 1 | Rare — retrieval in hours | Very low per GB |

### 5.2 Retention (reaffirming [CHANGE_MANAGEMENT.md](CHANGE_MANAGEMENT.md) §8)

- **Tier 1:** 7 years (SOX-aligned for financial-input models)
- **Tier 2:** 3 years
- **Tier 3:** 1 year
- **Access logs:** match the tier of the accessed data
- **Incident logs:** 7 years regardless of originating tier

### 5.3 PII Handling

Audit logs are operational data but can contain PII (stakeholder names, emails, account metadata).

Rules:
- **Never log:** raw auth tokens, passwords, SSN/IDs, credit card data (already enforced at application layer)
- **Log hashed, not raw:** user emails for actor tracking — store hash + reversible lookup in a PII store gated separately
- **Mask in query UI:** stakeholder names, emails appear masked in default views; unmask requires a distinct role + rationale
- **Tenant isolation:** customer A's audit logs are never visible to customer B under any query

See [SOC2_Compliance_Plan.md](../SOC2_Compliance_Plan.md) §6 for LLM-specific PII considerations. Those rules apply recursively to audit logs that contain LLM inputs/outputs.

---

## 6. Access Controls

Audit logs are sensitive. Four access patterns:

| Pattern | Who | Scope | Controls |
|---|---|---|---|
| **Customer self-audit** | Customer admin | Their tenant only | RBAC role; tenant_id filter enforced at query layer |
| **CS Pulse operational** | Engineering, Support | Any tenant, PII masked by default | SSO + role; every query access-logged per §2.4 |
| **CS Pulse compliance** | Compliance team | Any tenant, PII available on rationale | SSO + role; access-logged with rationale field |
| **External auditor** | Auditor (e.g. SOC 2) | Scoped per engagement | Time-bound credentials; read-only; access-logged |

**Never direct DB access for audit queries** — always through a query layer that enforces RBAC + access logging. Direct DB access bypasses the §2.4 access-event stream.

---

## 7. Queryable Reports

Audit data must support these standard reports (to be built in the audit query UI):

### Tier 1 / SR 11-7 required

- **Model lifecycle report** — all events for a given MOD-xxx in a date range
- **Change chain for a decision** — given a decision event, show the model version at that time and every change to that model since inception
- **Approval chain** — all approvals by a user, or all approvals for a model
- **Independent-validator coverage** — % of Tier 1 changes with valid independent-validator sign-off (should be 100%)
- **Segregation-of-duties report** — any change where proposer = approver (should be 0)

### SOC 2 / operational

- **Access log report** — who viewed what customer's data, when
- **Incident timeline** — all events related to an incident
- **PII access audit** — who unmasked PII and why

### Customer-visible

- **Tenant activity report** — "what changed in your CS Pulse in the last 30 days" — exportable
- **My calibration history** — customer admin view of their Wizard C runs

---

## 8. Immutability & Integrity

Tier 1 audit data must be tamper-evident.

**Requirements:**
- Append-only table design — no UPDATE, no DELETE
- Corrections happen as new rows with `correction_of=<prior_event_id>` — never in-place edits
- Hash chain on Tier 1 tables: each new row stores `prev_row_hash` + `this_row_hash`; integrity verifier can replay and detect breaks
- Daily backup to immutable S3 bucket (Object Lock, compliance mode)
- Yearly integrity verification run; result itself becomes an audit event

**What this enables:**
- "Show me every weight-calibration event in order, with proof nothing was removed between events 47 and 48"
- "Prove no one changed this decision record after the fact"

**Current state:** none of the above is implemented. All gap until formally built.

---

## 9. Integration with Other Governance Docs

This document defines the **evidence schema**. Other docs depend on it:

- **[CHANGE_MANAGEMENT.md](CHANGE_MANAGEMENT.md)** Gate 3 writes §2.3 approval events; Gate 5 writes §2.2 change events; Gate 6 writes verification_result
- **[DRIFT_MONITORING.md](DRIFT_MONITORING.md)** (next) reads decision events §2.1 for drift computation; writes §2.5 incident events on alert
- **[MODEL_INVENTORY.md](MODEL_INVENTORY.md)** "Last Validated" field updates from Gate 7 register update (itself an audit event)

If any of these other flows skip their audit-write step, the evidence layer has a hole and compliance cannot be demonstrated.

---

## 10. Open Items — Implementation Order

Sequenced by enablement: later items depend on earlier ones.

1. **Prompt version register + model_version field on decision rows** — blocks reproducibility for LLM models
2. **Separate approval_events table + hash-chain on Tier 1 audit tables** — blocks separation-of-duties and tamper-evidence claims
3. **Access event logging + RBAC-gated audit query UI** — blocks SOC 2 CC6.1 evidence
4. **Input snapshot store** for Tier 1 decisions — blocks Tier 1 replay
5. **LLM request/response capture** (PII-safe) for MOD-007, MOD-015 — blocks LLM-specific debugging
6. **User-action audit** for admin UI changes — blocks customer-admin accountability
7. **Immutable backup with Object Lock** — blocks long-term retention integrity
8. **Audit export** for regulators and customers — blocks formal audit engagements

---

## Change Log

| Date | Version | Change | Author |
|---|---|---|---|
| 2026-04-20 | 0.1 | Initial draft — 5 event categories, per-tier requirements, honest gap list, implementation sequence | Engineering |
