# Demo Manifest - Customer 3

## Overview
- **Customer ID:** 3
- **Company:** LoadTest-Martin, Wright and Rubio
- **Accounts:** 3
- **Time Period:** 12 months
- **Generated:** 2026-02-25 20:15:20

## Data Files
- accounts.csv (1672 bytes)
- kpi_measurements.csv (26969 bytes)
- customers.csv (101 bytes)
- qualitative_signals.csv (11003 bytes)
- products.csv (156 bytes)
- profiles.csv (1099 bytes)

## Journey Patterns
This customer uses **DEMO_MANIFEST** journey patterns.

## Accounts
- **3001**: LoadTest-Martin, Wright and Rubio - Production
- **3002**: LoadTest-Martin, Wright and Rubio - Staging
- **3003**: LoadTest-Martin, Wright and Rubio - Development

## KPIs (Config-Aware)
- Total measurements: 540
- Enabled KPIs: 15
- Months of data: 12

## Next Steps
1. Run data loading: `02_load_customer3_data_SMART.py`
2. Generate embeddings: `03_embed_customer3_OPENAI.py`
3. Generate journeys: Wizard A
