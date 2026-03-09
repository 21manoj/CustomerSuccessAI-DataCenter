# CS Pulse n8n Workflow Templates

## Three-Ring Architecture

CS Pulse uses a three-ring architecture to cleanly separate platform logic from customer-specific integrations:

### Ring 1 -- CS Pulse (Core Platform)

The CS Pulse backend exposes generic REST endpoints that accept and serve data in a standardized schema. Ring 1 has no knowledge of where data originates or which external systems consume its outputs. Key endpoints include:

- `POST /api/data-ingestion/kpis` -- Ingest KPI data from any source
- `POST /api/data-ingestion/signals` -- Ingest customer signals
- `POST /api/webhooks/playbook-callback` -- Receive execution results from external automation
- `GET /api/kpis/{customer_id}` -- Retrieve KPI data
- `GET /api/health-scores/{customer_id}` -- Retrieve computed health scores

### Ring 2 -- n8n (Customer-Specific Workflow Logic)

n8n sits between external tools (Google Sheets, Jira, Slack, Salesforce, etc.) and CS Pulse. Each customer deploys their own n8n instance (or a shared multi-tenant instance) and imports workflow templates from this directory. n8n handles:

- **Data Ingestion**: Pulling data from customer-specific sources (Google Sheets, CRMs, databases) and pushing it into CS Pulse via the ingestion API.
- **Playbook Actions**: Receiving action triggers from CS Pulse playbooks and executing them in external systems (create Jira tickets, send Slack alerts, update Salesforce records).
- **Credential Management**: Each customer configures their own API keys and OAuth tokens within n8n, keeping secrets out of CS Pulse.

### Ring 3 -- Load Driver (Testing & Simulation)

The Load Driver simulates both Ring 1 consumers and Ring 2 workflows for end-to-end testing. It can generate synthetic data payloads, simulate n8n webhook calls, and validate that the full pipeline works without requiring live external integrations.

## Directory Structure

```
n8n-workflows/
  README.md                              # This file
  templates/
    data-ingestion/
      google-sheets-to-cspulse.json      # Google Sheets -> CS Pulse KPI ingestion
    playbook-actions/
      create-jira-issue.json             # CS Pulse playbook -> Jira issue creation
      send-slack-alert.json              # CS Pulse playbook -> Slack notification
  docs/
    SETUP_GUIDE.md                       # How to import and configure templates
    CREDENTIALS_GUIDE.md                 # Per-provider credential setup
```

## Quick Start

1. Install n8n (self-hosted or cloud): https://n8n.io
2. Import a workflow template (see `docs/SETUP_GUIDE.md`)
3. Configure credentials for your providers (see `docs/CREDENTIALS_GUIDE.md`)
4. Replace placeholder values (`{{CS_PULSE_URL}}`, `{{CS_PULSE_API_KEY}}`, etc.)
5. Activate the workflow and test with sample data

## Placeholder Values

All templates use placeholder strings that must be replaced with your actual configuration:

| Placeholder | Description | Example |
|---|---|---|
| `{{CS_PULSE_URL}}` | Base URL of your CS Pulse instance | `https://cspulse.example.com` |
| `{{CS_PULSE_API_KEY}}` | API key for authenticating with CS Pulse | `csp_k_abc123...` |
| `{{CUSTOMER_ID}}` | Numeric customer ID in CS Pulse | `19` |
| `{{GOOGLE_SHEET_ID}}` | Google Sheet document ID | `1BxiM...` |
| `{{JIRA_PROJECT_KEY}}` | Jira project key for issue creation | `CS` |
| `{{JIRA_BASE_URL}}` | Jira instance URL | `https://company.atlassian.net` |
| `{{SLACK_CHANNEL}}` | Slack channel ID or name | `#cs-alerts` |

## Compatibility

These templates are tested with:

- n8n v1.30+ (self-hosted or n8n Cloud)
- CS Pulse API v1
- Node types from `n8n-nodes-base` (no community nodes required)
