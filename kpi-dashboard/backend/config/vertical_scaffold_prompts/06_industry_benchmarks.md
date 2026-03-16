# Prompt 06: Industry Benchmarks

## Input Variables
- `{VERTICAL_ID}`, `{VERTICAL_NAME}`, `{INDUSTRY_DESCRIPTION}`
- `{KPI_LIST}`: Full list of KPIs with codes, names, units, and polarity from Prompt 01

## Prompt

(This is the same prompt used for dc2_s and saas_premium benchmarks.
See the inline prompt at the top of this codebase's conversation history.)

```
You are a {INDUSTRY_DESCRIPTION} analyst with deep expertise in
operational benchmarking. Generate realistic industry benchmark data
for all KPIs in the {VERTICAL_NAME} vertical.

OUTPUT FORMAT:
CSV with columns:
  kpi_code, kpi_name, pillar, pillar_name, unit, p25, p50, p75, p90,
  source, methodology, last_updated, curated

WHERE:
- p25 = bottom quartile (struggling operators)
- p50 = median (typical operator)
- p75 = top quartile (well-run operations)
- p90 = elite (best-in-class)
- source = industry report, survey, or research body
- methodology = how the benchmark was derived
- last_updated = current quarter (e.g., 2026-Q1)
- curated = false (set to true after expert review)

KPI LIST:
{KPI_LIST}

POLARITY RULES:
- For "lower is better" KPIs: p25 > p50 > p75 > p90
- For "higher is better" KPIs: p25 < p50 < p75 < p90

SOURCE GUIDELINES:
- Use credible industry research firms relevant to this vertical
- Where no public benchmark exists, use "CS Pulse estimate based on
  aggregated customer data" and "Platform-derived percentile from
  anonymized deployments"
- Values must be realistic and internally consistent
- Include realistic variance — don't cluster all percentages at 90-99%
```
