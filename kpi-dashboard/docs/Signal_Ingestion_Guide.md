# How to get signals into CS Pulse

**Version:** May 2026 — pre-paid-pilot
**Audience:** prospective customer evaluating CS Pulse, no Signal Engine 3rd-party generator on hand

CS Pulse separates **what your customers are doing** (KPIs from product/CRM) from **what your customers are saying** (signals from email, support tickets, meeting notes, NPS surveys). The "saying" layer is what makes our health scoring better than a metrics-only platform — but it requires a way to feed us that narrative content.

This guide covers three channels for getting signals into CS Pulse, in order of fastest time-to-value.

---

## Channel 1 — CRM activity export (Day 1, no integration)

**When to use:** you have a CRM (Salesforce, HubSpot, Gainsight, Zendesk, ChurnZero) where your CSMs already log calls, emails, tasks, and meeting notes. Export 6-12 months of activity history and drop it into our CSV importer.

**What you send us:** one CSV file per customer tenant, format below.

**Coverage:** 80%+ of buyers have this on day one. Gives baseline narrative density per account immediately.

**Effort on your side:** 1-2 hours to build the CRM report and export. We provide the schema; your admin runs the SOQL/HubSpot equivalent.

### Schema — `qualitative_signals.csv`

| Column | Required | Type | Example | Notes |
|---|---|---|---|---|
| `signal_id` | yes | string (max 50) | `sfdc_00T6F00001ABcDe` | Tenant-unique. CRM record ID is fine. |
| `account_id` or `source_account_id` | yes | int / string | `1001` | Must match a value in your `accounts.csv`. Either your internal account ID or `source_account_id` (we'll resolve via account-name fallback). |
| `signal_date` | yes | YYYY-MM-DD | `2026-04-12` | When the activity actually happened (not when logged). |
| `signal_type` | yes | enum string | `email`, `meeting`, `support_ticket`, `nps_survey`, `qbr`, `escalation`, `champion_change` | Free-form OK; we'll classify into our taxonomy at ingest. Suggested values map to common CRM activity types. |
| `content` | yes | text | `"Champion confirmed expansion budget for next FY. Wants 2× capacity by Q3."` | The actual narrative content. Subject + body concatenated for emails; meeting notes verbatim; ticket description for support. **Max 4000 chars per row** — we summarize on the way in. |
| `sentiment` | optional | enum | `positive`, `neutral`, `negative` | If you have it. We compute it via LLM if missing. |
| `sentiment_score` | optional | float [0.0, 1.0] | `0.85` | Same — optional, computed on ingest if missing. |
| `stakeholder_email` | optional | email | `champion@bigco.com` | Helps us link the signal to a STAKEHOLDER node and detect champion changes. |
| `stakeholder_role` | optional | string | `Champion`, `Exec Sponsor`, `End User`, `Procurement` | Best-effort — improves stakeholder map accuracy. |
| `csm_email` | optional | email | `csm@yourcompany.com` | Author of the activity, if logged. Helps with capacity planning. |
| `linked_signal_id` | optional | string | `sfdc_00T6F00001QRsTu` | If this activity is a reply/follow-up to another, reference its ID. We chain related signals automatically. |

**Tip:** if you have outcome events (renewal closed, expansion deal won, churn happened), put them in a separate `outcomes.csv` (we have a separate template). That feeds NRR forecasting.

### Salesforce SOQL example

```sql
SELECT
  Id AS signal_id,
  AccountId AS source_account_id,
  ActivityDate AS signal_date,
  CASE
    WHEN Type = 'Call' THEN 'meeting'
    WHEN Type = 'Email' THEN 'email'
    WHEN Subject LIKE '%QBR%' THEN 'qbr'
    WHEN Subject LIKE '%escalat%' THEN 'escalation'
    ELSE 'meeting'
  END AS signal_type,
  CONCAT(Subject, '\n\n', NULLIF(Description, '')) AS content,
  Owner.Email AS csm_email,
  Who.Email AS stakeholder_email,
  Who.Title AS stakeholder_role
FROM Task
WHERE ActivityDate >= LAST_N_MONTHS:12
  AND AccountId IN ('list of pilot account IDs')
ORDER BY ActivityDate DESC
```

Export as CSV → upload via the CS Pulse onboarding wizard (Step 2: Optional Data → Qualitative Signals).

### HubSpot equivalent

Engagement API: `engagements/v1/engagements/paged?since=...` filtered to types `EMAIL`, `MEETING`, `CALL`, `NOTE`. Map `engagement.timestamp` → `signal_date`, `metadata.subject + metadata.body` → `content`.

### Gainsight Timeline export

Activities table → CSV. Map `Activity Date` → `signal_date`, `Activity Type` → `signal_type`, `Notes` → `content`.

---

## Channel 2 — Email forwarding (3-day setup, live signals)

**When to use:** you want a continuous live signal stream and don't have a CRM (or your CRM's activity hygiene is poor). Most common pick after the initial CRM-CSV bootstrap.

**How it works:** we provision a unique email address per tenant — `signals-{tenant}@cspulse.io`. You set a forwarding rule in your email system: every email sent to/from any customer-success-relevant email gets a BCC to that address. Our SendGrid inbound parse webhook receives the email, the Signal Engine worker LLM-enriches it (sentiment, urgency, intent, escalation probability), and writes a ContextNode SIGNAL in the right tenant's graph.

**Effort on your side:** create one Outlook/Gmail forwarding rule per CSM, or one shared rule on a customer-success distribution list. ~30 minutes.

**Effort on our side:** 3 days to wire up the SendGrid endpoint + webhook + LLM enrichment + governance gates (PII redaction, allowlist, rate-limit). Tracked as MOD-012 in our governance roadmap.

**Note:** the inbound email pipeline is built but gated behind `FEATURE_SIGNAL_ENGINE=true`. We turn it on per-tenant after the customer signs the data-processing addendum.

---

## Channel 3 — Slack / Teams / Zoom (5-day setup, real-time)

**When to use:** you want to log signals at the moment they happen, not at end-of-day when CSMs do CRM hygiene.

**Slack:** `/cs-pulse-flag <account-name> <message>` slash command in your customer-success Slack workspace. POST goes to our webhook → enriched signal in <2s.

**Teams:** bot equivalent — same `/cs-pulse-flag` command, same enrichment.

**Zoom:** post-meeting transcript upload (manual or via Zoom App marketplace integration). Transcript → LLM extracts signal-worthy moments → SIGNAL nodes.

**Effort on your side:** 1 hour for Slack/Teams app install + workspace approval. For Zoom, optional but recommended: enable Cloud Recording with Audio Transcript.

**Effort on our side:** 5 days for all three channels (slash command + Teams bot + Zoom transcript ingestion).

---

## What happens after the signal lands

Regardless of which channel: every raw signal is processed through the same pipeline:

1. **Account match** — signal is linked to an account via stakeholder email, account_id, or fuzzy account-name match.
2. **LLM enrichment** (Claude Haiku) — extracts:
   - `signal_type` (refined into our 30+ standard types)
   - `sentiment` and `sentiment_score`
   - `urgency_score` (0.0-1.0)
   - `escalation_probability` (0.0-1.0)
   - `intent_signals` (e.g., expansion_intent, churn_risk, satisfaction_high)
   - `stakeholder_roles` (champion, blocker, executive_sponsor, end_user)
   - `revenue_impact` estimate (per-account ARR × sentiment-derived multiplier)
3. **Provenance tag** — `source='inferred'`, `source_platform='qsim'` so downstream Wizard B/C can filter quality.
4. **Causal-graph link** — Tier 1 LLM connects the new SIGNAL to existing DECISION/OUTCOME nodes via causal edges where relevant.
5. **Wizard A/B/C** — health scores, NRR forecast, weight calibration all consume the new signal automatically.

---

## Governance / privacy

Live signal channels (email forwarding, Slack, transcript) require PII redaction (≥95% test coverage), per-customer audit trail, and the `FEATURE_SIGNAL_ENGINE=true` toggle is signed off by your customer admin before activation. CRM-CSV upload doesn't require any of this — your data, your export, your control.

For details see [docs/governance/](governance/) → MOD-012 Signal Processing Pipeline.

---

## TL;DR for tomorrow's call

> Day 1: export 12 months of CRM activity → CSV → upload. Done.
>
> Day 8: pick one of {email forwarding, Slack, Zoom transcript} for live updates. We wire it in 3-5 days.
>
> Day 30: Signal Engine has 200+ signals per account, NRR forecast confidence is back-tested, and you stop relying on CSV refreshes.
