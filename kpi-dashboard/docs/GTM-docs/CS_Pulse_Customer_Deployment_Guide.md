# CS Pulse — Customer Deployment Guide

**Version:** May 2026 (beta)
**Audience:** Sales Engineering, Customer Success Ops, prospective customer's IT/RevOps lead
**Purpose:** complete shipping checklist for a private/single-tenant CS Pulse instance.

---

## 0. Hosting model — pick one before anything else

| Model | Effort | When to pick |
|---|---|---|
| **A. Single-tenant SaaS** (we host on our infra; isolated DB schema; their subdomain) | 1–2 days | **Default**. Most customers. We retain ops control. |
| **B. Customer-cloud** (their AWS/Azure/GCP account; our IaC) | 1–2 weeks | Regulated buyers (FinServ, Healthcare); data-residency requirements. |
| **C. Air-gapped on-prem** | 4–6+ weeks; requires LLM gateway swap (Bedrock, Azure OpenAI, or self-host) | Government / classified. Push back if possible. |

The rest of this guide assumes A or B.

---

## 1. Application bundle (what ships)

- **Containers**
  - Backend: `kpi-dashboard/Dockerfile.cspulse` (Flask + Wizards + MCP server)
  - Frontend: built React static assets bundled into backend container
  - Load-driver: only if customer wants to refresh demo data (`load-driver/Dockerfile`) — usually skip
- **Compose** — `docker-compose.cspulse.yml`. Single-tenant simplifications:
  - drop `cs-pulse-b` replica (single instance is fine for <5K accounts)
  - point `postgres` at managed RDS / Cloud SQL for SaaS
- **Postgres** — managed for SaaS / customer-cloud; container only for on-prem
- **Reverse proxy / TLS** — Cloudfront or ALB → nginx with their cert
- **SES / SMTP relay** — required for magic-link login emails (today's only auth path)

---

## 2. Per-customer artifacts to mint

| Artifact | Location | Notes |
|---|---|---|
| `CustomerConfig` row | DB | vertical, KPI tier (Starter 9 / Predictive 11 / Full 43), feature toggles, weight overrides |
| `verticals/customer{id}-{vertical}/` tree | Filesystem (or DB once migration completes) | bootstrap_weights_config.json, journey/config/, KPI catalog override |
| Magic-link admin user | DB | First admin email + `allowed_account_ids` |
| Story arc manifests | `config/story_arcs/` | Generic 8-arc set ships; customer can extend |
| Initial 4-CSV upload | `data/{customer_id}/` | accounts, kpi_measurements, qualitative_signals, outcomes |
| Wizard A/B/C calibration runs | DB | Run after first CSV ingest. Wizard C requires ≥10 closed outcomes — schedule for week 4+ |

---

## 3. Config & secrets to provision

- **Anthropic API key** — today: shared platform key, costs attributed per-tenant via `llm_usage_log`. Per-customer BYOK is a backlog item; surface in the contract if relevant.
- **JWT signing key** — per-tenant, generated at provision
- **DB credentials** — per-tenant DB user with schema-scoped grants
- **Feature flags** (set per tenant, all toggleable from `FeatureTogglePanel.tsx`):
  - `CONTEXT_GRAPH=true` (default — the differentiator)
  - `FEATURE_SIGNAL_ENGINE=false` until DPA signed (gates live email/Slack channels)
  - `FEATURE_WITH_LLM=true` (default-on for 4-CSV mode, off for 11-CSV)
  - `FEATURE_AI_GOVERNANCE=true` (model inventory + audit trail)
  - Sub-toggles: story_arcs, signal_edges, stakeholder_tracking, decision_lifecycle, outcome_economics, industry_benchmarks

---

## 4. Documentation pack (already in `GTM-docs/` and `engineering-docs/`)

**Customer-facing:**
- `CS_Pulse_GTM_2Pager.docx` / `.md` — 3-page buyer overview with Three Layers of Intelligence (`node docs/GTM-docs/generate_gtm_2pager.js`)
- `CS_Pulse_GTM_2Pager_Infographic.pptx` / `.html` — glossy infographic; HTML is 2-page PDF; persona **workspace** screenshots in `screens/`
- `Signal_Ingestion_Guide.md` — 3 channels (CRM CSV, email, Slack)
- `qualitative_signals_template.csv` + `outcomes_template.csv` — 4-CSV upload templates
- `CS_Pulse_User_Guide_Sandalwood_419.docx`
- `CS_Pulse_CSM_Tutorial.pptx`, `CS_Pulse_VP_CS_Tutorial.pptx`
- `CS_Pulse_Integration_Framework_KT.docx`

**Engineering (deliver to their IT):**
- `SOC2_Compliance_Plan.md`
- `RBAC_SSO_Implementation_Plan.md`
- `HA_Scaling_Robustness_Plan.md`
- `Wizards_A_B_Technical_Overview.md`

**Governance pack** (`docs/governance/` — ships unmodified):
- AI_GOVERNANCE_FRAMEWORK
- MODEL_INVENTORY (15 models)
- CHANGE_MANAGEMENT
- AUDIT_TRAIL_REQUIREMENTS
- DRIFT_MONITORING
- GOVERNANCE_ROADMAP (beta disclosure)

---

## 5. Customer admin & governance layer (per-tenant control plane)

Without these wired, every config change becomes a support ticket.

### 5a. Admin UI surfaces (already shipped)

| Component | Path | Purpose |
|---|---|---|
| `AdminDashboard.tsx` | `/admin` | Top-level admin landing — gates by RBAC role |
| `FeatureTogglePanel.tsx` | `/admin/features` | Customer admin toggles CONTEXT_GRAPH sub-features, Signal Engine, governance flags |
| `AccountHealthReset.tsx` | `/admin/health-reset` | Reset health score after data-quality issue or post-incident |
| `WeightOverridePanel.tsx` | `/admin/weights/override` | Manual L1/L2 weight override (audit-trailed) |
| `WizardCWeights.tsx` | `/admin/weights/wizard-c` | View Wizard C calibration history; accept/reject runs |
| `WizardBInsights.tsx` | `/admin/wizard-b` | NRR forecast review, with/without CS Pulse comparison |
| `SettingsPage.tsx` + `ApiKeysTab.tsx` | `/settings` | Health threshold boundaries, API key management |

### 5b. Admin MCP tools (governance-facing)

- `get_llm_cost_summary` — per-tenant LLM spend (daily/monthly)
- `enable_features` — programmatic toggle of CONTEXT_GRAPH sub-features
- `configure_customer_kpis` — switch between Starter 9 / Predictive 11 / Full 43 tiers
- `trigger_wizard` — manual run of A/B/C (Wizard C is admin-gated; do not auto-fire on every CSV refresh)
- `get_csv_templates` — self-service download of 4-CSV templates

### 5c. Governance artifacts owned per-tenant by the customer admin

- **Model approval gate** (MOD-002) — every new prompt-template goes through admin review before production reads
- **Prompt register** (MOD-007) — admin-visible list of every Anthropic prompt + version pinning
- **Audit trail** — Wizard C calibration runs, weight overrides, threshold changes, feature toggle flips all logged with user_id + reason; admin can export
- **Drift monitoring dashboard** — Wizard B forecast accuracy back-tested weekly; admin gets red-flag if accuracy drops
- **PII redaction config** — when Signal Engine flips on, admin reviews redaction allowlist for their domain (≥95% test coverage required)
- **Beta disclosure consent log** — admin re-acknowledges beta status + known limitations every 90 days

### 5d. RBAC roles to provision per tenant

Per `engineering-docs/RBAC_SSO_Implementation_Plan.md`:

| Role | Scope |
|---|---|
| **Customer Admin** | All admin UI + governance toggles + user management. Typically VP CS or RevOps lead. |
| **VP CS** | Read all + accept Wizard B/C runs; no feature toggles. |
| **CSM Lead** | Read portfolio + assign accounts. |
| **CSM** | Read assigned accounts only (`allowed_account_ids` filter). |
| **CFO/CRO viewer** | Read CFO/CRO dashboards only; no operational tools. |

### 5e. SSO / auth handoff

- Magic-link is the bootstrap path — works on day 1 with just an email
- Enterprise: Okta / Azure AD SAML/OIDC via `RBAC_SSO_Implementation_Plan.md` — wired but per-tenant config required (entity ID, ACS URL, cert exchange)
- Per-customer JWT signing key (see §3)

### 5f. Known gaps in admin layer — disclose to buyer

| Gap | Impact | Effort to close |
|---|---|---|
| Playbook template editor UI | Admin can browse/launch/track playbooks but can't author templates (hardcoded in `src/lib/playbooks.ts`) | ~3–5 days |
| Customer-edited taxonomy | By design — admin picks via CDI DNA template, doesn't author. Surface as a feature, not a gap. | n/a |
| Per-tenant LLM model selection | Admin can't choose Haiku vs Sonnet per workload — platform-wide today | ~1–2 days |
| Bulk user CSV import | Admin invites users one-by-one via magic-link | ~1 day |

---

## 6. Operational handoff items

- **Backup**: `scripts/ec2-host-cron-pg-backup-to-s3.sh` — point at customer S3 bucket
- **Upgrade path**: ECR pull pattern via `scripts/rehydrate-ec2-ecr.sh`
- **Monitoring**: container logs → CloudWatch / their logging stack; LLM cost dashboard via `get_llm_cost_summary`
- **Magic-link operational note**: raw token only in container stdout, never in DB. 15-minute expiry, single-use.

---

## 7. Pre-contract gates (don't sign until these are on the books)

1. **Beta disclosure signed** — required by governance roadmap; 6 of 15 models have known limitations
2. **Data Processing Addendum (DPA)** — required before `FEATURE_SIGNAL_ENGINE=true`
3. **MOD-003 (renewal probability) + MOD-012 (signal pipeline) hard-blocked** — set buyer expectation
4. **Beta SLA**: weekly model drift checks, monthly audit trail review (MOD-013)
5. **Per-customer Anthropic BYOK** — backlog item; ~half-day to ship if buyer asks

---

## 8. Day 0–30 onboarding sequence

| Day | Step |
|---|---|
| 0 | Provision tenant. DPA + beta disclosure signed. Admin user provisioned via magic-link. |
| 1 | Customer exports 12 months CRM activity → 4 CSVs → upload via wizard. Wizard A (arc detection) auto-runs. |
| 2–3 | Wizard B (NRR forecast baseline) auto-runs. Admin reviews CFO/CRO dashboards. |
| 7 | Optional: enable Channel 2 (email forwarding) if DPA signed. |
| 14 | First admin governance review — accept/reject Wizard B back-test, review LLM cost. |
| 30 | Wizard C calibration first eligible run (≥10 closed outcomes). Admin accepts or rejects new weights. |

---

## 9. Shipping gaps to clear in parallel with the contract

| Gap | Severity | Effort |
|---|---|---|
| Per-customer BYOK column + caller refactor | Medium (sales exposure) | ~half day |
| Verticals filesystem→DB migration completion | Medium (deploy ergonomics) | ~2–3 days |
| Single-tenant docker-compose simplification (no replicas) | Low | 1 day |
| Customer-cloud Terraform module | High *if Option B* | 1–2 weeks |
| LLM gateway alternative (Bedrock/Azure) | High *if Option C* | 4+ weeks |

---

## What to deliver to the buyer

A bundle containing:
1. This guide
2. `Customer_Admin_Provisioning_Runbook.md` (sibling doc — operational checklist)
3. `Signal_Ingestion_Guide.md` + 2 CSV templates
4. `governance/` pack (7 docs)
5. `RBAC_SSO_Implementation_Plan.md`, `SOC2_Compliance_Plan.md`
6. Tenant URL + admin magic-link email + 30-day onboarding calendar invite
