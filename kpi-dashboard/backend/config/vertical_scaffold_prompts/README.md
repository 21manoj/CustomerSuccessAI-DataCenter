# Vertical Scaffold Prompts

Expert-level prompts for LLM-seeded vertical configuration files.
Each prompt is designed to produce 95%+ accurate output that requires
minimal human curation.

## Usage

1. Replace `{PLACEHOLDERS}` with actual values
2. Feed to Claude/GPT-4 with the system prompt from `_system_prompt.md`
3. Review output, mark `curated: true` after expert sign-off
4. Place generated files in the correct directories

## Files Generated (10 LLM-dependent)

| # | Prompt File | Output | Directory |
|---|------------|--------|-----------|
| 1 | `01_kpi_definitions.md` | `kpi_definitions.py` | `verticals/{vertical}/` |
| 2 | `02_vertical_config.md` | `vertical_config.py` | `verticals/{vertical}/` |
| 3 | `03_pillar_weights.md` | `pillar_weights.py` | `verticals/{vertical}/` |
| 4 | `04_metadata_schema.md` | `metadata_schema.py` | `verticals/{vertical}/` |
| 5 | `05_nomenclature.md` | `{vertical}.json` | `config/vertical_nomenclature/` |
| 6 | `06_industry_benchmarks.md` | `{vertical}.csv` | `config/industry_benchmarks/` |
| 7 | `07_power_of_1_economics.md` | `{vertical}_power_of_1_economics.json` | `config/` |
| 8 | `08_bootstrap_weights.md` | `bootstrap_weights_config.json` | `verticals/_template_{vertical}/journey/config/` |
| 9 | `09_kpi_mapping.md` | `kpi_mapping_config.json` | `verticals/_template_{vertical}/journey/config/` |
| 10 | `10_onboarding_prompt.md` | `onboarding_{vertical}_prompt.md` | `mcp_server/` |
