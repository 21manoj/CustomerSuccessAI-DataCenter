# Prompt 05: Vertical Nomenclature (UI Labels)

## Input Variables
- `{VERTICAL_ID}`, `{VERTICAL_NAME}`, `{VERTICAL_SHORT_NAME}` (2-4 chars)
- `{INDUSTRY}`: Industry category
- `{PILLAR_DEFINITIONS}`: P1-P5 names from Prompt 01
- `{PLAYBOOK_DEFINITIONS}`: PB-01 through PB-0N names from Prompt 02

## Prompt

```
You are a UX writer specializing in B2B enterprise software for
{INDUSTRY}. Generate a complete UI nomenclature mapping that translates
generic Customer Success platform terms into industry-specific language
that resonates with {VERTICAL_NAME} practitioners.

DESIGN PRINCIPLES:
1. Use terminology the target buyer already uses in their daily work
2. Avoid CS jargon when an industry-specific term exists
3. Keep labels short (1-3 words for navigation, 2-5 words for descriptions)
4. Status labels should convey urgency appropriate to the industry
5. Tooltips should be educational, not just repeat the label

GENERATE A JSON FILE with these exact sections:

{
  "vertical_id": "{VERTICAL_ID}",
  "vertical_display_name": "{VERTICAL_NAME}",
  "vertical_short_name": "{VERTICAL_SHORT_NAME}",
  "industry": "{INDUSTRY}",

  "entities": {
    // Map generic CS entities to vertical-specific terms
    // customer, customers, account, accounts, user, users,
    // product, products, contract, contracts, renewal,
    // expansion, churn, onboarding
  },

  "navigation": {
    // Map generic nav items to vertical-specific labels
    // main_dashboard, executive_dashboard, account_list,
    // account_details, account_health, product_health,
    // data_integration, analytics, ai_insights, signal_analyst,
    // playbooks, settings, roi_analysis, portfolio_synergy,
    // journey_timeline, revenue_intelligence
  },

  "health_status": {
    // healthy, at_risk, critical (labels)
    // healthy_description, at_risk_description, critical_description
    // Use industry-appropriate severity language
  },

  "pillars": {
    // P1-P5 each with: display_name, short_code (2 chars), description, icon
    // Use the pillar names from KPI definitions
    // Icons: choose from lucide icon names (rocket, shield, cpu, users,
    // dollar-sign, bar-chart, headphones, handshake, trending-up, etc.)
  },

  "playbooks": {
    "section_title": "...",
    "pb_prefix": "PB",
    "labels": { "PB-01": "...", ... }
  },

  "metrics": {
    // arr, mrr, nps, csat, csm, health_score, revenue, ttfv, nrr, grr
    // Use industry-specific names where applicable
  },

  "table_columns": {
    // name, health, region, industry, status, csm, arr, contract_end, last_activity
  },

  "search_placeholders": {
    // account_search, kpi_search, playbook_search
  },

  "empty_states": {
    // no_accounts, no_kpis, no_playbooks, no_signals
  },

  "actions": {
    // add_account, edit_account, view_details, run_playbook,
    // upload_data, export_report, calibrate_weights
  },

  "tooltips": {
    // health_score, expansion_probability, churn_risk, pillar_weight
    // Make these educational and specific to the industry
  }
}

INDUSTRY-SPECIFIC GUIDANCE:
- Data Center: account→Tenant, product→Infrastructure, churn→Decommission Risk
- SaaS: account→Account, product→Product, churn→Churn Risk (standard CS terms)
- Healthcare: account→Provider/Facility, product→Clinical Module, churn→Contract Loss
- FinTech: account→Client, product→Platform, churn→Attrition Risk
- Manufacturing: account→Plant/Facility, product→System, churn→Discontinuation Risk

CRITICAL:
- Every key in every section must have a value (no empty strings)
- Navigation labels should be 1-4 words max
- Tooltip text should be 10-20 words
- Health status descriptions should convey appropriate urgency
```
