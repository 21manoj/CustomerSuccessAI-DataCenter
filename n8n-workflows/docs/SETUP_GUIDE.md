# n8n Setup Guide for CS Pulse

This guide walks through importing the CS Pulse workflow templates into your n8n instance, configuring credentials, and testing the connection.

## Prerequisites

- A running n8n instance (self-hosted v1.30+ or n8n Cloud)
- Access to your CS Pulse instance with an API key
- Credentials for the external services you plan to integrate (Google Sheets, Jira, Slack)

## Step 1: Install n8n

### Option A: Docker (Recommended for Self-Hosted)

```bash
docker run -d \
  --name n8n \
  -p 5678:5678 \
  -v n8n_data:/home/node/.n8n \
  -e N8N_SECURE_COOKIE=false \
  n8nio/n8n:latest
```

Access n8n at `http://localhost:5678`.

### Option B: npm

```bash
npm install -g n8n
n8n start
```

### Option C: n8n Cloud

Sign up at https://n8n.io/cloud and follow the onboarding wizard. No local installation required.

## Step 2: Import Workflow Templates

### Via the n8n UI

1. Open your n8n instance in a browser.
2. Click the **"+"** button to create a new workflow (or go to **Workflows** > **Add Workflow**).
3. Click the **three-dot menu** (top-right) and select **Import from File**.
4. Select the JSON template file from `n8n-workflows/templates/`:
   - `data-ingestion/google-sheets-to-cspulse.json`
   - `playbook-actions/create-jira-issue.json`
   - `playbook-actions/send-slack-alert.json`
5. The workflow will load with all nodes and connections pre-configured.
6. Repeat for each template you need.

### Via the n8n CLI

```bash
# Import a single workflow
n8n import:workflow --input=templates/data-ingestion/google-sheets-to-cspulse.json

# Import all templates at once
for f in templates/**/*.json; do
  n8n import:workflow --input="$f"
done
```

### Via the n8n API

```bash
curl -X POST "http://localhost:5678/api/v1/workflows" \
  -H "Content-Type: application/json" \
  -H "X-N8N-API-KEY: your-n8n-api-key" \
  -d @templates/data-ingestion/google-sheets-to-cspulse.json
```

## Step 3: Configure Credentials

After importing, each workflow will show credential placeholders that need to be filled in.

### CS Pulse API Key

All templates require a CS Pulse API key configured as an HTTP Header Auth credential:

1. Go to **Settings** > **Credentials** > **Add Credential**.
2. Search for **Header Auth**.
3. Set:
   - **Name**: `CS Pulse API Key`
   - **Header Name**: `X-API-Key`
   - **Header Value**: Your CS Pulse API key (e.g., `csp_k_abc123...`)
4. Save the credential.
5. In each workflow, click on the HTTP Request nodes and select the `CS Pulse API Key` credential.

### Provider-Specific Credentials

See `CREDENTIALS_GUIDE.md` for detailed setup instructions for each provider:

- Google Sheets (OAuth2 or Service Account)
- Jira (API Token)
- Slack (Bot Token)

## Step 4: Replace Placeholder Values

Open each workflow and replace the placeholder values in node parameters:

| Placeholder | Where to Find It |
|---|---|
| `{{CS_PULSE_URL}}` | Your CS Pulse instance URL (e.g., `https://cspulse.example.com`) |
| `{{CS_PULSE_API_KEY}}` | Already configured in the credential (Step 3) |
| `{{CUSTOMER_ID}}` | Your numeric customer ID in CS Pulse |
| `{{GOOGLE_SHEET_ID}}` | The ID from your Google Sheet URL: `docs.google.com/spreadsheets/d/{THIS_PART}/edit` |
| `{{JIRA_PROJECT_KEY}}` | Your Jira project key (e.g., `CS`, `SUP`) |
| `{{JIRA_BASE_URL}}` | Your Jira instance URL (e.g., `https://company.atlassian.net`) |
| `{{SLACK_CHANNEL}}` | Slack channel ID or name (e.g., `#cs-alerts` or `C04ABCDEF12`) |

**Tip**: You can also use n8n environment variables instead of hardcoding values. Set them in your n8n configuration:

```bash
# In your n8n environment (.env or docker-compose)
N8N_VARIABLE_CS_PULSE_URL=https://cspulse.example.com
N8N_VARIABLE_JIRA_PROJECT_KEY=CS
N8N_VARIABLE_SLACK_CHANNEL=#cs-alerts
```

Then reference them in workflows with `$env.CS_PULSE_URL`.

## Step 5: Test the Connection

### Test Data Ingestion (Google Sheets)

1. Open the `Google Sheets to CS Pulse` workflow.
2. Click **Execute Workflow** (manual trigger) to run once.
3. Check the output of each node:
   - **Google Sheets Trigger**: Should show rows from your sheet.
   - **Transform to KPI Schema**: Should show properly mapped KPI objects.
   - **POST to CS Pulse**: Should return a `200` with an ingestion summary.
4. Verify in CS Pulse that the KPI data appears for the correct customer.

### Test Playbook Actions (Jira / Slack)

Since playbook actions are triggered by webhooks, test them with curl:

**Jira Issue Creation:**

```bash
curl -X POST "http://your-n8n-host:5678/webhook/cspulse-jira-action" \
  -H "Content-Type: application/json" \
  -d '{
    "action_id": "test-001",
    "playbook_id": "pb-churn-risk",
    "customer_id": 19,
    "customer_name": "Acme Corp",
    "action_type": "create_jira_issue",
    "parameters": {
      "summary": "[Test] CS Pulse churn risk alert for Acme Corp",
      "description": "Health score dropped below threshold. Immediate attention required.",
      "issue_type": "Task",
      "priority": "High",
      "labels": ["cs-pulse", "churn-risk"]
    },
    "callback_url": "http://localhost:5000/api/webhooks/playbook-callback",
    "triggered_by": "manual-test",
    "triggered_at": "2026-03-03T10:00:00Z"
  }'
```

**Slack Alert:**

```bash
curl -X POST "http://your-n8n-host:5678/webhook/cspulse-slack-alert" \
  -H "Content-Type: application/json" \
  -d '{
    "action_id": "test-002",
    "playbook_id": "pb-health-alert",
    "customer_id": 19,
    "customer_name": "Acme Corp",
    "action_type": "send_slack_alert",
    "parameters": {
      "channel": "#cs-alerts",
      "severity": "warning",
      "title": "Health Score Drop: Acme Corp",
      "message": "Health score dropped from 82 to 65 in the past 7 days.",
      "health_score": 65,
      "kpi_details": [
        {"name": "NPS", "value": 32, "trend": "declining"},
        {"name": "Support Tickets", "value": 15, "unit": "open", "trend": "increasing"}
      ]
    },
    "callback_url": "http://localhost:5000/api/webhooks/playbook-callback",
    "triggered_by": "manual-test",
    "triggered_at": "2026-03-03T10:00:00Z"
  }'
```

## Step 6: Activate Workflows

Once testing is successful:

1. Open each workflow in the n8n editor.
2. Toggle the **Active** switch (top-right) to **ON**.
3. The workflow will now execute automatically based on its trigger:
   - **Google Sheets**: Polls on the configured schedule (default: every hour).
   - **Jira / Slack**: Listens for incoming webhook requests from CS Pulse.

## Troubleshooting

### Common Issues

| Problem | Solution |
|---|---|
| "Could not find credential" | Re-create the credential in Settings > Credentials and re-link it in the node |
| Google Sheets trigger returns empty | Ensure the sheet name matches exactly and the service account has read access |
| HTTP Request returns 401 | Verify your CS Pulse API key is correct and the credential header name is `X-API-Key` |
| HTTP Request returns 404 | Check that `{{CS_PULSE_URL}}` is replaced with the correct base URL (no trailing slash) |
| Slack message not sent | Verify the bot has been added to the target channel (`/invite @your-bot-name`) |
| Jira issue not created | Verify the API token user has create-issue permissions in the target project |
| Webhook not receiving requests | Ensure the n8n instance is accessible from CS Pulse (check firewall/network rules) |

### Viewing Execution Logs

1. Go to **Executions** in the n8n sidebar.
2. Click on any execution to see the data flowing through each node.
3. Failed executions are highlighted in red with error details.

### Getting Help

- n8n Documentation: https://docs.n8n.io
- CS Pulse API Reference: Check your CS Pulse instance at `/api/docs`
- Community Support: https://community.n8n.io
