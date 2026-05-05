# Customer Admin Provisioning Runbook

**Version:** May 2026 (beta)
**Audience:** Sales Engineering / Customer Success Ops who provisions a new tenant
**Purpose:** step-by-step operational checklist to stand up the per-tenant admin & governance layer.
**Prereq:** tenant DB + container deployed per [`CS_Pulse_Customer_Deployment_Guide.md`](CS_Pulse_Customer_Deployment_Guide.md).

---

## Pre-flight

Before you start, collect from the customer:

- [ ] Tenant subdomain (e.g. `acme.cspulse.io`)
- [ ] Vertical (`dc2_s`, `saas_premium`, `healthcare_provider`, …)
- [ ] KPI tier (Starter 9 / Predictive 11 / Full 43)
- [ ] Customer Admin email (the one human who owns governance)
- [ ] VP CS email + CSM emails + dashboard-viewer emails
- [ ] SSO mode: magic-link only (default) OR SAML/OIDC (entity ID, ACS URL, cert)
- [ ] Anthropic key mode: platform key (default) OR BYOK
- [ ] DPA signed? (gates Signal Engine)
- [ ] Beta disclosure acknowledged?

---

## Step 1 — Provision tenant config

```sql
INSERT INTO customer_config (
  customer_id, customer_name, vertical, kpi_tier,
  feature_context_graph, feature_signal_engine,
  feature_with_llm, feature_ai_governance,
  health_threshold_at_risk, health_threshold_healthy
) VALUES (
  :customer_id, :customer_name, :vertical, 'predictive_11',
  TRUE, FALSE,        -- signal_engine OFF until DPA signed
  TRUE, TRUE,
  50, 70              -- defaults; admin can change via SettingsPage
);
```

Then provision the per-customer verticals tree:

```bash
docker exec cs-pulse-app \
  python -m verticals.bootstrap \
  --customer-id 401 \
  --vertical dc2_s \
  --kpi-tier predictive_11
```

This creates `verticals/customer401-dc2_s/` with `bootstrap_weights_config.json` + `journey/config/`. Verify via `ls`.

---

## Step 2 — Provision Customer Admin user

```python
# in container shell
from models import db, User
from utils.user_provisioning import create_admin_user

create_admin_user(
    customer_id=401,
    email='admin@acme.com',
    role='customer_admin',
    allowed_account_ids='*',   # admin sees all
)
db.session.commit()
```

Then trigger magic-link send:

```bash
curl -X POST https://acme.cspulse.io/api/auth/magic-link \
  -d '{"email":"admin@acme.com"}'
```

**The raw token appears only in `docker logs cs-pulse-app | grep "MAGIC LINK"`** — never in DB. Copy it from logs and email it to the admin via your normal channels.

---

## Step 3 — Provision other roles

Bulk CSV import isn't shipped yet (backlog ~1 day). For now, repeat Step 2 with role values:

| Role | Scope |
|---|---|
| `vp_cs` | Read all + accept Wizard B/C; no feature toggles |
| `csm_lead` | Read portfolio + assign accounts |
| `csm` | Read assigned only (set `allowed_account_ids='12,34,56'`) |
| `cfo_viewer` / `cro_viewer` | Dashboard read-only |

---

## Step 4 — Verify admin UI is reachable

Customer Admin logs in via magic-link → should land on `/dc-dashboard`.

Walk through with them:

- [ ] `/admin` — admin dashboard renders, role-gated tiles visible
- [ ] `/admin/features` — `FeatureTogglePanel` shows all sub-toggles
- [ ] `/admin/health-reset` — `AccountHealthReset` listing accounts
- [ ] `/admin/weights/override` — `WeightOverridePanel` showing current L1/L2 weights from `bootstrap_weights_config.json`
- [ ] `/admin/weights/wizard-c` — `WizardCWeights` empty (no calibration runs yet — expected at week 4+)
- [ ] `/admin/wizard-b` — `WizardBInsights` empty (need first CSV upload)
- [ ] `/settings` — `SettingsPage` with health thresholds 50/70 editable; `ApiKeysTab` visible

---

## Step 5 — First CSV upload

Send the customer the 4-CSV templates (already in their tenant at `/onboarding`):

- `accounts.csv`
- `kpi_measurements.csv`
- `qualitative_signals.csv` ([template](qualitative_signals_template.csv))
- `outcomes.csv` ([template](outcomes_template.csv))

After upload, verify `_process_data_impl` ran:

```sql
SELECT customer_id, COUNT(*) FROM dc2s_kpi WHERE customer_id = 401 GROUP BY customer_id;
SELECT customer_id, COUNT(*) FROM context_node WHERE customer_id = 401 GROUP BY customer_id;
SELECT customer_id, COUNT(*) FROM health_score WHERE customer_id = 401 GROUP BY customer_id;
```

Wizard A and Wizard B run automatically. Wizard C does **not** auto-run — it's admin-triggered (per [policy](../../../.claude/projects/-Users-manojgupta-CustomerSuccessAI-DataCenter/memory/policy_wizard_c_decoupled_from_process_data.md)).

---

## Step 6 — Configure governance artifacts

### 6a. Audit trail
Verify `audit_log` table is receiving entries:

```sql
SELECT event_type, COUNT(*)
FROM audit_log
WHERE customer_id = 401
GROUP BY event_type
ORDER BY 2 DESC;
```

Expected event types after first day: `feature_toggle_change`, `csv_upload`, `wizard_a_run`, `wizard_b_run`, `health_score_recalc`.

### 6b. Beta disclosure consent

Insert the consent record:

```sql
INSERT INTO governance_consent (
  customer_id, consent_type, signed_by_email, signed_at, expires_at
) VALUES (
  401, 'beta_disclosure', 'admin@acme.com', NOW(), NOW() + INTERVAL '90 days'
);
```

Schedule reminder for day 80 (admin re-acknowledges).

### 6c. Drift monitoring
No setup needed — runs automatically in background. Admin sees results at `/admin/wizard-b` after week 1.

### 6d. PII redaction (only if `FEATURE_SIGNAL_ENGINE=true`)
- [ ] Walk admin through redaction allowlist for their domain
- [ ] Run redaction test suite — must hit ≥95% coverage
- [ ] DPA must be signed; verify in `governance_consent`

---

## Step 7 — Schedule the 30-day onboarding cadence

| Day | Touchpoint | Owner |
|---|---|---|
| 1 | First CSV upload + Wizards A/B baseline | Customer Admin + SE |
| 7 | Channel 2 (email forwarding) decision — ON/OFF | Customer Admin |
| 14 | Governance review #1 — Wizard B back-test, LLM cost review | Customer Admin |
| 30 | Wizard C calibration first run (≥10 closed outcomes) | Customer Admin (admin-trigger) |
| 80 | Beta disclosure renewal reminder | SE |
| 90 | Beta disclosure re-acknowledgement deadline | Customer Admin |

---

## Step 8 — Handoff package

Email the admin a final wrap-up containing:
1. Tenant URL + magic-link login process
2. Link to [User Guide](CS_Pulse_User_Guide_Sandalwood_419.docx) + [VP CS Tutorial](CS_Pulse_VP_CS_Tutorial.pptx) + [CSM Tutorial](CS_Pulse_CSM_Tutorial.pptx)
3. Link to [Signal Ingestion Guide](Signal_Ingestion_Guide.md) for live channel decision
4. Governance pack (`docs/governance/`)
5. Day 14 + Day 30 calendar invites for governance review
6. Support escalation contact

---

## Failure modes — what to check when something looks wrong

| Symptom | Most likely cause | Fix |
|---|---|---|
| Admin can't log in | Magic-link expired (15 min) | Re-trigger Step 2; pull from `docker logs` |
| `/admin/features` 403s | Role not set to `customer_admin` | Re-run user provisioning with correct role |
| Health scores look wrong | Bootstrap weights not loaded | Verify `verticals/customer{id}-{vertical}/journey/config/bootstrap_weights_config.json` exists |
| Wizard B shows identical with-vs-without lines | Need ≥3 closed outcomes for amplifier to engage | Wait for more data, or seed via load-driver |
| LLM cost dashboard empty | Tracking helper not wired on a caller | Grep for `record_usage()` calls; see [feedback memory](../../../.claude/projects/-Users-manojgupta-CustomerSuccessAI-DataCenter/memory/feedback_llm_call_sites_must_track.md) |
| Drift dashboard empty | Need ≥1 week of forecasts to back-test | Expected; surfaces at week 2 |

---

## Sign-off checklist (use this for the contract close)

- [ ] Tenant provisioned (Step 1)
- [ ] Customer Admin logged in successfully (Step 2)
- [ ] All other roles provisioned (Step 3)
- [ ] Admin UI walkthrough completed (Step 4)
- [ ] First CSV upload successful + Wizards A/B ran (Step 5)
- [ ] Audit trail receiving events (Step 6a)
- [ ] Beta disclosure signed + recorded (Step 6b)
- [ ] DPA signed (if Signal Engine ON; Step 6d)
- [ ] 30-day cadence scheduled (Step 7)
- [ ] Handoff email sent (Step 8)
