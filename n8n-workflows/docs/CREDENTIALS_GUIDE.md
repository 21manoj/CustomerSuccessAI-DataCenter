# Credentials Setup Guide

This guide covers how to create and configure credentials for each provider used by the CS Pulse n8n workflow templates.

## Table of Contents

- [CS Pulse API Key](#cs-pulse-api-key)
- [Google Sheets (Service Account)](#google-sheets-service-account)
- [Google Sheets (OAuth2)](#google-sheets-oauth2)
- [Jira API Token](#jira-api-token)
- [Slack Bot Token](#slack-bot-token)

---

## CS Pulse API Key

All workflow templates authenticate with CS Pulse using an API key passed as an HTTP header.

### Generate the API Key

1. Log into your CS Pulse instance as an admin.
2. Navigate to **Settings** > **API Keys**.
3. Click **Generate New Key**.
4. Give it a descriptive name (e.g., `n8n-integration`).
5. Copy the key -- it will only be shown once.

### Configure in n8n

1. Go to **Settings** > **Credentials** > **Add Credential**.
2. Search for **Header Auth** and select it.
3. Configure:
   - **Credential Name**: `CS Pulse API Key`
   - **Name** (header name): `X-API-Key`
   - **Value** (header value): `csp_k_your_api_key_here`
4. Click **Save**.

### Security Notes

- API keys should have the minimum necessary permissions.
- Rotate keys periodically (recommended: every 90 days).
- Use separate keys for each n8n instance or environment (dev, staging, production).

---

## Google Sheets (Service Account)

Service accounts are recommended for server-to-server access. They do not require user interaction for authentication.

### Create a Service Account

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Select your project (or create a new one).
3. Navigate to **APIs & Services** > **Credentials**.
4. Click **Create Credentials** > **Service Account**.
5. Fill in:
   - **Name**: `n8n-cspulse-sheets`
   - **Description**: `Service account for n8n to read Google Sheets for CS Pulse`
6. Click **Create and Continue**.
7. Grant the role **Viewer** (or skip if granting sheet-level access only).
8. Click **Done**.

### Generate a Key

1. Click on the service account you just created.
2. Go to the **Keys** tab.
3. Click **Add Key** > **Create new key**.
4. Select **JSON** format.
5. Download the key file. Keep it secure.

### Enable the Google Sheets API

1. Go to **APIs & Services** > **Library**.
2. Search for **Google Sheets API**.
3. Click **Enable**.

### Share Your Sheet with the Service Account

1. Open the Google Sheet you want to read.
2. Click **Share**.
3. Paste the service account email (e.g., `n8n-cspulse-sheets@your-project.iam.gserviceaccount.com`).
4. Grant **Viewer** access.
5. Click **Send**.

### Configure in n8n

1. Go to **Settings** > **Credentials** > **Add Credential**.
2. Search for **Google Sheets API** (select the **Service Account** variant).
3. Configure:
   - **Credential Name**: `Google Sheets Service Account`
   - **Service Account Email**: The email from the service account
   - **Private Key**: Paste the `private_key` value from the JSON key file (including the `-----BEGIN PRIVATE KEY-----` and `-----END PRIVATE KEY-----` markers)
4. Click **Save**.

---

## Google Sheets (OAuth2)

OAuth2 is an alternative if you prefer to authenticate as a user rather than a service account.

### Create OAuth2 Credentials

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Navigate to **APIs & Services** > **Credentials**.
3. Click **Create Credentials** > **OAuth client ID**.
4. Select **Web application**.
5. Set:
   - **Name**: `n8n CS Pulse`
   - **Authorized redirect URIs**: `https://your-n8n-host/rest/oauth2-credential/callback`
6. Click **Create**.
7. Copy the **Client ID** and **Client Secret**.

### Enable the Google Sheets API

(Same as service account -- see above.)

### Configure in n8n

1. Go to **Settings** > **Credentials** > **Add Credential**.
2. Search for **Google Sheets OAuth2 API**.
3. Configure:
   - **Credential Name**: `Google Sheets Account`
   - **Client ID**: From the OAuth2 credential
   - **Client Secret**: From the OAuth2 credential
4. Click **Sign in with Google** and authorize access.
5. Click **Save**.

---

## Jira API Token

Jira Cloud uses API tokens for authentication (basic auth with email + token).

### Generate an API Token

1. Log into your Atlassian account at https://id.atlassian.com/manage-profile/security/api-tokens.
2. Click **Create API token**.
3. Set a **Label** (e.g., `n8n-cspulse`).
4. Click **Create**.
5. Copy the token -- it will only be shown once.

### Required Permissions

The Atlassian account used for the API token must have:

- **Browse Project** permission on the target project
- **Create Issue** permission on the target project
- **Edit Issue** permission (if workflows need to update issues later)

### Configure in n8n

1. Go to **Settings** > **Credentials** > **Add Credential**.
2. Search for **Jira Software Cloud API**.
3. Configure:
   - **Credential Name**: `Jira Account`
   - **Email**: The email associated with your Atlassian account
   - **API Token**: The token you generated
   - **Domain**: Your Jira domain (e.g., `company` from `company.atlassian.net`)
4. Click **Save**.

### Verify the Connection

Test from the command line:

```bash
curl -u "your-email@company.com:your-api-token" \
  "https://company.atlassian.net/rest/api/3/project/CS"
```

You should receive project details in JSON format.

---

## Slack Bot Token

CS Pulse playbooks send alerts via a Slack bot. You need to create a Slack app and install it in your workspace.

### Create a Slack App

1. Go to https://api.slack.com/apps.
2. Click **Create New App** > **From scratch**.
3. Set:
   - **App Name**: `CS Pulse Alerts`
   - **Workspace**: Select your target workspace
4. Click **Create App**.

### Configure Bot Permissions

1. In the app settings, go to **OAuth & Permissions**.
2. Under **Scopes** > **Bot Token Scopes**, add:
   - `chat:write` -- Send messages
   - `chat:write.public` -- Send to channels without being a member
   - `channels:read` -- List public channels (optional, for channel discovery)
3. Scroll up and click **Install to Workspace**.
4. Authorize the app.
5. Copy the **Bot User OAuth Token** (starts with `xoxb-`).

### Invite the Bot to Channels

For private channels, you must invite the bot:

```
/invite @CS Pulse Alerts
```

For public channels, the `chat:write.public` scope allows posting without an invite.

### Configure in n8n

1. Go to **Settings** > **Credentials** > **Add Credential**.
2. Search for **Slack API**.
3. Configure:
   - **Credential Name**: `Slack Bot Token`
   - **Access Token**: The `xoxb-` token from the Slack app
4. Click **Save**.

### Verify the Connection

Test from the command line:

```bash
curl -X POST "https://slack.com/api/chat.postMessage" \
  -H "Authorization: Bearer xoxb-your-token" \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "#cs-alerts",
    "text": "CS Pulse connection test - if you see this, the integration is working."
  }'
```

---

## Environment Variables (Optional)

Instead of hardcoding values in workflows, you can set n8n environment variables. This is especially useful for multi-environment setups (dev/staging/prod).

### Docker Compose Example

```yaml
services:
  n8n:
    image: n8nio/n8n:latest
    environment:
      - N8N_VARIABLE_CS_PULSE_URL=https://cspulse.example.com
      - N8N_VARIABLE_CUSTOMER_ID=19
      - N8N_VARIABLE_JIRA_PROJECT_KEY=CS
      - N8N_VARIABLE_JIRA_BASE_URL=https://company.atlassian.net
      - N8N_VARIABLE_SLACK_CHANNEL=#cs-alerts
```

### Referencing in Workflows

In any n8n expression field, use:

```
{{ $env.CS_PULSE_URL }}
{{ $env.CUSTOMER_ID }}
{{ $env.JIRA_PROJECT_KEY }}
```

The workflow templates are already configured to fall back to environment variables when placeholders are not replaced.

---

## Credential Rotation

| Provider | Rotation Frequency | How to Rotate |
|---|---|---|
| CS Pulse API Key | Every 90 days | Generate new key in CS Pulse, update n8n credential, deactivate old key |
| Google Service Account Key | Every 365 days | Generate new JSON key in GCP Console, update n8n credential, delete old key |
| Jira API Token | Every 90 days | Create new token in Atlassian, update n8n credential, revoke old token |
| Slack Bot Token | Only if compromised | Regenerate in Slack app settings, update n8n credential |

## Troubleshooting Credentials

| Symptom | Likely Cause | Fix |
|---|---|---|
| "Invalid credentials" in n8n | Token expired or mistyped | Re-enter the credential value |
| Google Sheets returns 403 | Sheet not shared with service account | Share the sheet with the service account email |
| Jira returns 401 | Wrong email/token combination | Verify email matches the Atlassian account that owns the token |
| Slack returns `channel_not_found` | Bot not in private channel | Invite the bot with `/invite @CS Pulse Alerts` |
| Slack returns `not_in_channel` | Missing `chat:write.public` scope | Add the scope and reinstall the app |
