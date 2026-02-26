# Demo Manifest - Customer 19

## Overview
- **Customer ID:** 19
- **Company:** E2E Test Company Weights 572341
- **Accounts:** 3
- **Time Period:** 12 months
- **Generated:** 2026-02-26 00:26:35

## Data Files
- accounts.csv (1642 bytes)
- kpi_measurements.csv (27499 bytes)
- customers.csv (148 bytes)
- qualitative_signals.csv (11393 bytes)
- products.csv (160 bytes)
- profiles.csv (1116 bytes)

## Journey Patterns
This customer uses **DEMO_MANIFEST** journey patterns.

## Accounts
- **19001**: E2E Test Company Weights 572341 - Production
- **19002**: E2E Test Company Weights 572341 - Staging
- **19003**: E2E Test Company Weights 572341 - Development

## KPIs (Config-Aware)
- Total measurements: 540
- Enabled KPIs: 15
- Months of data: 12

## Next Steps
1. Run data loading: `02_load_customer19_data_SMART.py`
2. Generate embeddings: `03_embed_customer19_OPENAI.py`
3. Generate journeys: Wizard A
