# Prompt 03: Pillar Weights (L1/L2 Weight Management)

## Input Variables
- `{VERTICAL_ID}`, `{VERTICAL_NAME}`
- `{PILLAR_DEFINITIONS}`: P1-P5 names, descriptions, and initial weight_l2 from Prompt 01
- `{KPI_DEFINITIONS}`: Full KPI list with weight_l1 values from Prompt 01

## Prompt

```
You are a data scientist specializing in customer health scoring models
for {VERTICAL_NAME}. Generate a pillar weights management module that
defines the initial weight configuration and learning parameters.

CONTEXT:
- Pillars: {PILLAR_DEFINITIONS}
- KPIs: {KPI_DEFINITIONS}

GENERATE:

1. DEFAULT_PILLAR_WEIGHTS_L2:
   - Dict of P1-P5 → float (must sum to 1.0)
   - Revenue/growth pillar should have highest weight (0.25-0.30)
   - Operational pillars should not exceed 0.20 each
   - Justify each weight with a one-line comment

2. DEFAULT_KPI_WEIGHTS_L1:
   - Dict of P{n} → {KPI_code: weight} (within-pillar weights must sum to 1.0)
   - Highest-weighted KPIs should be the strongest business predictors
   - ML-derived KPIs (churn probability, expansion probability) should have
     higher weights (0.15-0.22) than operational KPIs (0.08-0.12)

3. LEARNING_PARAMETERS:
   - learning_rate: 0.05 (conservative — don't shift weights too fast)
   - momentum: 0.9
   - convergence_threshold: 0.85
   - min_weight: 0.02 (no KPI should be zeroed out)
   - max_weight: 0.40 (no single KPI dominates)
   - recalibration_window_days: 90

4. VALIDATION_THRESHOLDS:
   - churn_risk_threshold: Score below which account is flagged
   - expansion_probability_min: Score above which expansion is likely
   - health_critical_boundary: 50 (fixed per platform standard)
   - health_at_risk_boundary: 70 (fixed per platform standard)

5. EFFECTIVE_WEIGHTS_TOP_10:
   - Pre-computed list of top 10 KPIs by effective weight
     (effective_weight = pillar_weight_L2 * kpi_weight_L1)
   - Format: [{kpi: "P5-KPI1", name: "...", effective_weight: 0.066, rank: 1}, ...]

OUTPUT FORMAT:
Python module matching verticals/dc2_s/pillar_weights.py structure.

CRITICAL:
- All weights must be mathematically valid (sum to 1.0 within each group)
- Effective weights should show a clear power-law distribution (top KPI ~3x bottom KPI)
- Learning parameters should be conservative for enterprise deployments
```
