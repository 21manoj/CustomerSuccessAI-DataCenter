# NRR Intelligence Engine — Deployment Guide

## Overview

Three deployment steps that evolve Wizard B from a health-score pattern analyzer
into an NRR (Net Revenue Retention) prediction and attribution engine.

Each step is **independently deployable** and adds incremental value.

---

## Prerequisites (All Steps)

| Requirement | Why | How to Verify |
|-------------|-----|---------------|
| Wizard A has run | Journey data needed for pattern analysis | `trigger_wizard(customer_id, 'a')` |
| Accounts have ARR | Revenue weighting requires `Account.revenue` | `list_accounts(customer_id)` — check `revenue` field |
| Context graph enabled | OUTCOME nodes carry revenue events | `enable_features(customer_id, ['context_graph'])` |
| Context graph data loaded | OUTCOME nodes with `revenue_impact` | `get_graph_summary(customer_id, account_id)` |

---

## Step 1: Pattern-to-NRR Correlation

### What It Does
For each arc pattern (champion_loss, silent_churn, expansion_champion, etc.),
computes the historical NRR impact by joining Account ARR with context graph
OUTCOME revenue nodes.

### Output
```
champion_loss:       NRR = 82%   $4.2M exposed   65% intervention success
silent_churn:        NRR = 91%   $3.1M exposed   78% intervention success
expansion_champion:  NRR = 122%  $5.5M exposed   95% success
steady_performer:    NRR = 102%  $12M exposed
```

### Files Changed
| File | Change |
|------|--------|
| `wizard_b_pattern_analyzer.py` | Added `correlate_nrr_impact()` method + 6 new PatternProfile fields |
| `wizard_b_pattern_db.py` | Exposes `nrr_intelligence` in return dict |

### Deploy
```bash
# 1. Pull code
cd ~/CustomerSuccessAI-DataCenter && git pull origin main

# 2. Build + deploy (standard EC2 recipe)
sudo docker compose -f kpi-dashboard/docker-compose.cspulse.yml build cs-pulse
REGISTRY=$(grep '^REGISTRY=' ~/cspulse/.env | cut -d= -f2 | tr -d '\r')
sudo docker tag kpi-dashboard-cs-pulse "${REGISTRY}/cspulse-platform:latest"
cd ~/cspulse && sudo docker compose \
  -f docker-compose.ec2-registry.yml \
  -f docker-compose.ec2-loaddriver.yml \
  -f docker-compose.ec2-platform-replica.yml \
  up -d --force-recreate cs-pulse
```

### Test
```bash
# Run Wizard B — NRR correlations appear automatically
trigger_wizard(customer_id=429, wizard='b')

# Check results
# The response now includes nrr_intelligence.correlations and nrr_intelligence.forecast
```

### Rollback
Safe — additive only. If correlate_nrr_impact() fails (no ARR data, no outcomes),
Wizard B continues with the original 4 analysis steps. NRR fields default to
`avg_nrr_impact=1.0` (neutral).

---

## Step 2: Portfolio NRR Forecast

### What It Does
Revenue-weighted NRR projection for the entire portfolio, plus what-if simulation:
> "If you execute playbooks on the 5 champion_loss accounts, NRR improves
> from 94% to 102%, protecting $1.2M ARR."

### Output (MCP Tool: `get_nrr_forecast`)
```json
{
  "current_nrr_pct": 94.2,
  "with_interventions_nrr_pct": 102.1,
  "delta_arr": 1200000,
  "at_risk_accounts": 5,
  "pattern_breakdown": [...],
  "top_interventions": [
    {"account_name": "Acme", "arr": 1200000, "pattern": "champion_loss",
     "current_nrr": 82.0, "projected_nrr": 94.5, "projected_save": 150000}
  ]
}
```

### Files Changed
| File | Change |
|------|--------|
| `wizard_b_pattern_analyzer.py` | Added `forecast_portfolio_nrr()` method |
| `cs_pulse_revenue.py` | New `get_nrr_forecast` MCP tool |

### Deploy
Same as Step 1 (included in same build). Step 2 runs automatically when Step 1
produces NRR correlations.

### Test
```bash
# Via MCP tool (Claude.ai or CLI)
get_nrr_forecast(customer_id=429)

# Should return portfolio NRR forecast with pattern breakdown
```

### Dependencies
- **Step 1 must run first** — forecast uses NRR correlations from correlate_nrr_impact()
- Falls back to live calculation if no cached Wizard B results exist (slower but works)

---

## Step 3: NRR Attribution in Reports

### What It Does
Adds NRR correlation table and portfolio forecast to the Wizard B analysis report
(stored in WizardLearning.analysis_report and WizardLearning.learnings JSON blob).

### Report Additions
```markdown
## NRR Intelligence

### Pattern-to-NRR Correlations
| Pattern | NRR | ARR Exposed | Protected | Lost | Intervention Rate |
|---------|-----|-------------|-----------|------|-------------------|
| champion_loss | 82.0% | $4,200,000 | $280,000 | $756,000 | 65% |
| ...

### Portfolio NRR Forecast
- Current Projected NRR: 94.2%
- With Interventions: 102.1%
- Delta ARR: $1,200,000
- At-Risk Accounts: 5 / 18

### Top Intervention Opportunities
| Account | ARR | Pattern | Current NRR | Projected NRR | Projected Save |
|---------|-----|---------|-------------|---------------|----------------|
| Acme Corp | $1,200,000 | champion_loss | 82.0% | 94.5% | $150,000 |
```

### Files Changed
| File | Change |
|------|--------|
| `wizard_b_pattern_analyzer.py` | Enhanced `_generate_report_text()` and `save_to_database()` |

### Deploy
Same build as Steps 1-2 (all three ship together).

### Test
```bash
# Run full Wizard B
trigger_wizard(customer_id=429, wizard='b')

# The analysis_report in WizardLearning now includes NRR Intelligence sections
# Verify via admin API or DB query
```

---

## Deployment Sequence

All 3 steps ship in a **single deployment** (same commit, same build).
They execute sequentially inside `analyze_patterns()`:

```
Step 1: profile_patterns()      → health statistics (existing)
Step 2: analyze_transitions()   → phase transitions (existing)
Step 3: identify_early_warnings → churn signals (existing)
Step 4: extract_success_factors → expansion factors (existing)
Step 5: correlate_nrr_impact()  → NRR correlations (NEW — Step 1)
Step 6: forecast_portfolio_nrr  → NRR forecast (NEW — Step 2)
Step 7: save_to_database()      → persists all including NRR (NEW — Step 3)
```

### Recommended Test Flow

```
1. Deploy to EC2 (single build)
2. Pick test customer (e.g., 429 — Granite Peak DC2S, 18 accounts)
3. Ensure prereqs:
   - process_data(429)           # loads data + runs Wizard A
   - enable_features(429, ['context_graph'])
4. Run Wizard B:
   - trigger_wizard(429, 'b')    # runs all 6 steps
5. Verify NRR output:
   - Check trigger_wizard response for nrr_intelligence
   - Call get_nrr_forecast(429)
6. Compare with known data:
   - list_accounts(429)          # verify ARR totals
   - get_at_risk_accounts(429)   # verify at-risk count matches forecast
```

---

## Feature Flags

No new feature flags required. NRR intelligence activates automatically when:
1. `customer_id` is set (DB mode, not filesystem mode)
2. Accounts have ARR data (`Account.revenue > 0`)
3. Context graph OUTCOME nodes exist with `revenue_impact`

If any prerequisite is missing, the NRR steps produce empty/neutral results
and Wizard B continues normally with the original 4 analysis steps.

---

## Data Flow Diagram

```
                    ┌─────────────┐
                    │  Wizard A   │
                    │ (Journeys)  │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Wizard B   │
                    │ analyze()   │
                    └──────┬──────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
   ┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐
   │  Account    │ │ ContextNode │ │  JourneyData │
   │  (ARR)     │ │ (OUTCOME    │ │  (patterns)  │
   │            │ │  revenue)   │ │              │
   └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
          │                │                │
          └────────────────┼────────────────┘
                           │
                    ┌──────▼──────┐
                    │  NRR Engine │
                    │ Steps 1-3  │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
       ┌──────▼──────┐ ┌──▼───┐ ┌─────▼─────┐
       │ WizardLearn │ │ MCP  │ │  Analysis  │
       │ (DB cache)  │ │ Tool │ │  Report    │
       └─────────────┘ └──────┘ └───────────┘
```

---

## Monitoring

After deployment, watch for:

| Log Message | Meaning |
|-------------|---------|
| `NRR=XX.X% ARR=$X,XXX` per pattern | Step 1 working — correlations computed |
| `Portfolio NRR: X% → Y% (+$Z)` | Step 2 working — forecast produced |
| `Skipping NRR correlation (no customer_id)` | Expected in filesystem/CLI mode |
| `No journey data for customer X` | Wizard A hasn't run yet |

---

## Connecting to the NRR Pain Story

| NRR Deck Slide | What CS Pulse Now Shows |
|----------------|------------------------|
| "NRR at 5-year low" | `get_nrr_forecast` → current portfolio NRR projection |
| "$500B market cap destruction" | Pattern-to-NRR table → which patterns destroy value |
| "CAC $2 per $1 ARR" | `delta_arr` → revenue saved by retention vs new acquisition cost |
| "Catch signals before churn" | `top_interventions` → exact accounts + playbooks + projected save |
| "Champion departures, budget pressure" | Each maps to an arc with quantified NRR impact |
