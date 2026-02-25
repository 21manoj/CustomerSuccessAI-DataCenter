# Demo Manifest - Customer 5

## Overview
- **Customer ID:** 5
- **Company:** LoadTest-Martin, Wright and Rubio
- **Accounts:** 3
- **Time Period:** 12 months
- **Generated:** 2026-02-25 20:16:24

## Data Files
- accounts.csv (1696 bytes)
- kpi_measurements.csv (26957 bytes)
- customers.csv (101 bytes)
- qualitative_signals.csv (11439 bytes)
- products.csv (156 bytes)
- profiles.csv (1090 bytes)

## Journey Patterns
This customer uses **DEMO_MANIFEST** journey patterns.

## Accounts
- **5001**: LoadTest-Martin, Wright and Rubio - Production
- **5002**: LoadTest-Martin, Wright and Rubio - Staging
- **5003**: LoadTest-Martin, Wright and Rubio - Development

## KPIs (Config-Aware)
- Total measurements: 540
- Enabled KPIs: 15
- Months of data: 12

## Next Steps
1. Run data loading: `02_load_customer5_data_SMART.py`
2. Generate embeddings: `03_embed_customer5_OPENAI.py`
3. Generate journeys: Wizard A
