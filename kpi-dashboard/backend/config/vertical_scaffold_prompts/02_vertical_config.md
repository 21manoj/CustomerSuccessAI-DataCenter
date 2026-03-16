# Prompt 02: Vertical Config (Playbooks, Tiers, Phases)

## Input Variables
- `{VERTICAL_ID}`, `{VERTICAL_NAME}`, `{INDUSTRY_DESCRIPTION}`
- `{KPI_DEFINITIONS}`: Output from Prompt 01 (paste the full pillar + KPI list)
- `{TYPICAL_CUSTOMER_JOURNEY}`: Description of the typical customer lifecycle in this industry

## Prompt

```
You are a Customer Success operations expert for {INDUSTRY_DESCRIPTION}.
Generate a complete vertical configuration file including playbooks,
partner tiers, customer lifecycle phases, and alert thresholds.

CONTEXT:
- Vertical: {VERTICAL_NAME} ({VERTICAL_ID})
- KPI definitions (use these exact codes for triggers): {KPI_DEFINITIONS}
- Typical customer journey: {TYPICAL_CUSTOMER_JOURNEY}

GENERATE THE FOLLOWING SECTIONS:

1. PLAYBOOK_CONFIG (6-8 playbooks):
   For each playbook (PB-01 through PB-0N):
   - name: Action-oriented name (e.g., "Deployment Acceleration", not "Deploy")
   - description: One sentence
   - trigger_kpis: List of KPI codes that trigger this playbook
   - trigger_conditions: Dict of KPI code → threshold value
   - trigger_logic: "OR" (any condition) or "AND" (all conditions)
   - duration_range: [min_days, max_days]
   - requires_human_approval: true for high-risk playbooks (expansion, contract changes)
   - sub_components: List of 4-5 concrete actions/steps
   - expected_outcome: What success looks like
   - linked_metrics: Which Power-of-1 metrics this playbook improves

   PLAYBOOK DESIGN RULES:
   - Each pillar should have at least 1 playbook triggered by its KPIs
   - P5 (revenue) playbooks should require human approval
   - Include 1 "health monitoring" playbook triggered by overall health score
   - Include 1 "engagement" playbook for relationship maintenance
   - Duration should be realistic for the industry

2. PARTNER_TIERS (3-4 tiers):
   - tier_name, access_level, max_accounts, features_list
   - Example: Internal, Partner, VAR, Strategic

3. CUSTOMER_PHASES (3-5 lifecycle phases):
   - phase_name, description, duration_range, health_expectations
   - Must cover: initial deployment → steady state → expansion → renewal
   - Phase names should use industry-specific language

4. ALERT_THRESHOLDS:
   - priority_levels: P1 (critical), P2 (high), P3 (medium), P4 (info)
   - For each: name, description, response_time_hours, escalation_path
   - KPI-specific alerts: which KPI breaches trigger which priority

5. INTEGRATION_SETTINGS:
   - common_source_systems: List of 5-8 systems this vertical typically integrates with
   - data_refresh_frequency: How often data is typically refreshed
   - api_rate_limits: Default rate limits

OUTPUT FORMAT:
Python file with PLAYBOOK_CONFIG dict, PARTNER_TIERS dict, CUSTOMER_PHASES dict,
ALERT_CONFIG dict, INTEGRATION_SETTINGS dict. Follow the exact structure used in
verticals/dc2_s/vertical_config.py.

CRITICAL:
- All trigger_kpis must reference valid KPI codes from the definitions above
- Trigger thresholds must be realistic (not 0 or 100)
- Sub-components must be specific actionable steps, not vague directives
```
