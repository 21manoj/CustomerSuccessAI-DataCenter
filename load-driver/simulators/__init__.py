"""
Simulators for CS Pulse load testing (Ring 3)

These simulate external dependencies (Google Sheets, n8n) so the full
data-ingestion and playbook pipeline can be tested without real integrations.

Modules:
  google_sheets_simulator  - Generates realistic KPI/signal/contact data
  n8n_webhook_simulator    - Simulates n8n pushing data via webhooks
  n8n_callback_simulator   - Simulates n8n returning playbook execution results
"""
