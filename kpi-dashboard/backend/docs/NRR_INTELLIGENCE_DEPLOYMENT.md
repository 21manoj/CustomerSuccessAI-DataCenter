# NRR Intelligence — Deployment Guide

## Overview

NRR Intelligence adds revenue-weighted Net Revenue Retention forecasting to Wizard B.
It correlates arc patterns (from Wizard A) with account ARR and context graph outcomes
to produce per-pattern NRR impact metrics and portfolio-level NRR projections.

**Feature flag**: `nrr_intelligence` (per-customer, **default ON**)

---

## What It Does

### Step 1: Pattern-to-NRR Correlation (`correlate_nrr_impact`)
For each journey pattern (crisis, stable, proactive_growth, etc.):
- Joins Account ARR + ContextNode OUTCOME revenue
- Computes: avg NRR impact, total ARR exposed, revenue protected/lost/expanded
- Tracks intervention success rate (health improved post-intervention)

### Step 2: Portfolio NRR Forecast (`forecast_portfolio_nrr`)
- Revenue-weighted current NRR across all accounts
- What-if simulation: projected NRR if playbooks executed on at-risk accounts
- Delta ARR: dollar impact of executing vs. not executing interventions
- Top 10 accounts to intervene on, ranked by projected revenue save

---

## Deployment Steps

### Step 1: Deploy Code (EC2 Full Rebuild)

```bash
# On local machine
cd ~/CustomerSuccessAI-DataCenter && git pull origin main

# Build
sudo docker compose -f kpi-dashboard/docker-compose.cspulse.yml build cs-pulse

# Tag and deploy
REGISTRY=$(grep '^REGISTRY=' ~/cspulse/.env | cut -d= -f2 | tr -d '\r')
sudo docker tag kpi-dashboard-cs-pulse "${REGISTRY}/cspulse-platform:latest"
cd ~/cspulse && sudo docker compose \
  -f docker-compose.ec2-registry.yml \
  -f docker-compose.ec2-loaddriver.yml \
  -f docker-compose.ec2-platform-replica.yml \
  up -d --force-recreate cs-pulse
```

### Step 2: Verify Wizard A Has Run

NRR Intelligence requires Wizard A journey data in the DB.

```
# Via MCP
trigger_wizard(customer_id, 'a')
```

Verify: journey_data table should have rows for the customer.

### Step 3: Run Wizard B

```
trigger_wizard(customer_id, 'b')
```

With `nrr_intelligence` default ON, Wizard B will:
1. Run standard 4-stage pattern analysis
2. Run NRR correlation (Step 5)
3. Run portfolio NRR forecast (Step 6)

Results are stored in `wizard_runs.results` JSON under `nrr_intelligence` key.

### Step 4: Query NRR Forecast

```
get_nrr_forecast(customer_id)
```

Returns:
```json
{
  "nrr_forecast": {
    "current_nrr_pct": 94.2,
    "with_interventions_nrr_pct": 102.1,
    "delta_arr": 1240000,
    "at_risk_accounts": 5,
    "total_accounts": 18
  },
  "pattern_correlations": {
    "crisis": {"avg_nrr_pct": 87.3, "arr_exposed": 8200000},
    "stable": {"avg_nrr_pct": 100.0, "arr_exposed": 12400000},
    "proactive_growth": {"avg_nrr_pct": 112.5, "arr_exposed": 5600000}
  }
}
```

---

## Feature Flag Control

### Default: ON (all customers)
No action needed. NRR intelligence runs automatically when Wizard B is triggered.

### To Disable for a Specific Customer
```
# Via MCP — creates toggle row with enabled=True, then manually set to False
# Or via admin API:
POST /api/features/customer-toggle
{
  "customer_id": 424,
  "feature_name": "nrr_intelligence",
  "enabled": false
}
```

### To Re-Enable
```
enable_features(customer_id, ['nrr_intelligence'])
```

---

## Hotfix (Without Full Rebuild)

If you need to deploy the `week_number` fix or NRR code without rebuilding:

```bash
# SSH to EC2
# Fix all copies of wizard_b_pattern_analyzer.py
sudo docker exec cspulse-platform find /app -name "wizard_b_pattern_analyzer.py" -type f \
  -exec sed -i "s/events\[i+1\]\['week_number'\] - events\[i\]\['week_number'\]/events[i+1].get('week_number', events[i+1].get('week', 0)) - events[i].get('week_number', events[i].get('week', 0))/g" {} \;

# Copy updated files
sudo docker cp wizard_b_pattern_analyzer.py cspulse-platform:/app/backend/verticals/_template/journey/wizard_b/
sudo docker cp cs_pulse_intelligence.py cspulse-platform:/app/backend/mcp_server/

# Clear cache and restart
sudo docker exec cspulse-platform find /app -name "__pycache__" -type d -exec rm -rf {} +
sudo docker restart cspulse-platform
```

**Important**: Files under `/app/backend/verticals/` persist via Docker volume.
Files in the image layer (e.g., `mcp_server/`) reset on redeploy — always rebuild for durability.

---

## Dependency Chain

```
process_data() → loads CSVs → Account (ARR) + ContextNode (outcomes)
                            → Wizard A → JourneyData (patterns, health trajectory)

trigger_wizard('b') → reads JourneyData (patterns)
                    → reads Account (ARR — live, not cached)
                    → reads ContextNode (revenue outcomes — live)
                    → Step 5: correlate_nrr_impact()
                    → Step 6: forecast_portfolio_nrr()
                    → stores results in wizard_runs.results

get_nrr_forecast() → reads wizard_runs (latest completed Wizard B run)
                   → returns cached NRR forecast
```

---

## Commits

| Commit | Description |
|--------|-------------|
| `64354af4` | fix(wizard-b): use 'week' key (was 'week_number') |
| `ea386c0b` | feat(wizard-b): gate NRR intelligence behind feature flag |
| `0e5eb890` | feat(mcp): add get_nrr_forecast tool |
| `2fda28d0` | fix(nrr): default feature flag to ON |
