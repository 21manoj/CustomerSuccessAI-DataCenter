# Prompt 08: Bootstrap Weights Config

## Input Variables
- `{VERTICAL_ID}`, `{VERTICAL_NAME}`
- `{PILLAR_WEIGHTS_L2}`: From Prompt 01/03 (P1-P5 → weight)
- `{KPI_WEIGHTS_L1}`: From Prompt 01/03 (per-KPI weights)
- `{TOP_10_EFFECTIVE}`: From Prompt 03 (top 10 by effective weight)

## Prompt

```
You are configuring the bootstrap weights for a new {VERTICAL_NAME}
customer onboarding. Generate the bootstrap_weights_config.json that
Wizard C will use as the initial weight configuration before calibration.

CONTEXT:
- Pillar weights (L2): {PILLAR_WEIGHTS_L2}
- KPI weights (L1): {KPI_WEIGHTS_L1}
- Top 10 effective KPIs: {TOP_10_EFFECTIVE}

GENERATE JSON with these exact sections:

{
  "config_version": "2.0.0",
  "vertical": "{VERTICAL_ID}",

  "pillar_weights_L2": {
    "P1": ..., "P2": ..., "P3": ..., "P4": ..., "P5": ...
  },

  "kpi_weights_L1": {
    "P1": { "P1-KPI1": ..., ... },
    "P2": { "P2-KPI1": ..., ... },
    ...
  },

  "effective_weights_top_10": [
    {"kpi": "P5-KPI1", "name": "...", "effective_weight": 0.066, "rank": 1},
    ...
  ],

  "validation_thresholds": {
    "churn_risk_threshold": ...,
    "expansion_probability_min": ...,
    "health_critical_boundary": 50,
    "health_at_risk_boundary": 70
  },

  "learning_parameters": {
    "learning_rate": 0.05,
    "momentum": 0.9,
    "convergence_threshold": 0.85,
    "min_weight": 0.02,
    "max_weight": 0.40,
    "recalibration_window_days": 90
  },

  "metadata": {
    "generated_by": "scaffold_prompt_08",
    "vertical": "{VERTICAL_ID}",
    "kpi_format": "P-format",
    "curated": false
  }
}

CRITICAL:
- pillar_weights_L2 must sum to exactly 1.0
- Each pillar's KPI weights must sum to exactly 1.0
- effective_weight = pillar_weight * kpi_weight (verify math)
- Top 10 must be sorted by effective_weight descending
```
