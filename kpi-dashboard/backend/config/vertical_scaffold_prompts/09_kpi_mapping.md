# Prompt 09: KPI Mapping Config

## Input Variables
- `{VERTICAL_ID}`, `{VERTICAL_NAME}`
- `{KPI_DEFINITIONS}`: Full KPI list from Prompt 01
- `{JOURNEY_DATA_KPIS}`: If known, the journey visualization data points available

## Prompt

```
You are mapping KPI definitions to journey visualization data points
for the {VERTICAL_NAME} vertical. Generate a kpi_mapping_config.json
that defines how each bootstrap KPI maps to available journey data.

CONTEXT:
- Bootstrap KPIs: {KPI_DEFINITIONS}
- Journey data typically has different naming conventions and may not
  cover all KPIs. The mapping defines transformation rules.

GENERATE JSON with these sections:

{
  "mapping_version": "1.0.0",
  "vertical": "{VERTICAL_ID}",

  "kpi_mappings": {
    "P1": {
      "P1-KPI1": {
        "journey_kpi": "...",
        "transformation": "direct|semantic|inverse|partial|composite|weak",
        "confidence": 0.0-1.0,
        "notes": "..."
      },
      ...
    },
    ...
  },

  "journey_kpi_coverage": {
    "fully_covered": ["P1-KPI1", ...],
    "partially_covered": ["P2-KPI3", ...],
    "not_covered": ["P4-KPI5", ...]
  },

  "coverage_summary": {
    "total_bootstrap_kpis": N,
    "fully_mapped": N,
    "partially_mapped": N,
    "unmapped": N,
    "coverage_percentage": N
  },

  "transformation_rules": {
    "direct": "1:1 mapping, same metric different name",
    "semantic": "Same concept, different measurement approach",
    "inverse": "Inverse relationship (e.g., MTTR low = reliability high)",
    "partial": "Journey KPI captures subset of bootstrap KPI",
    "composite": "Multiple journey KPIs combine to form bootstrap KPI",
    "weak": "Loose correlation, used as proxy"
  },

  "default_weights_for_unmapped": 0.0286
}

GUIDELINES:
- Aim for 70-80% coverage (not 100% — some KPIs are ML-derived)
- Direct mappings should have confidence >= 0.9
- Weak mappings should have confidence 0.3-0.5
- Unmapped KPIs get default_weights_for_unmapped (= 1/total_kpis)
```
