# Demo Manifest - Customer 649382

## Overview
- **Customer ID:** 649382
- **Company:** E2E Test Company Idempotent 1772065649
- **Accounts:** 3
- **Time Period:** 12 months
- **Generated:** 2026-02-26 00:27:54

## Data Files
- accounts.csv (1733 bytes)
- kpi_measurements.csv (29653 bytes)
- customers.csv (159 bytes)
- qualitative_signals.csv (13563 bytes)
- products.csv (176 bytes)
- profiles.csv (1158 bytes)

## Journey Patterns
This customer uses **DEMO_MANIFEST** journey patterns.

## Accounts
- **649382001**: E2E Test Company Idempotent 1772065649 - Production
- **649382002**: E2E Test Company Idempotent 1772065649 - Staging
- **649382003**: E2E Test Company Idempotent 1772065649 - Development

## KPIs (Config-Aware)
- Total measurements: 540
- Enabled KPIs: 15
- Months of data: 12

## Next Steps
1. Run data loading: `02_load_customer649382_data_SMART.py`
2. Generate embeddings: `03_embed_customer649382_OPENAI.py`
3. Generate journeys: Wizard A
