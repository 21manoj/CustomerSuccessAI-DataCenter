# Demo Manifest - Customer 2

## Overview
- **Customer ID:** 2
- **Company:** LoadTest-Martin, Wright and Rubio
- **Accounts:** 3
- **Time Period:** 12 months
- **Generated:** 2026-02-25 20:14:49

## Data Files
- accounts.csv (1707 bytes)
- kpi_measurements.csv (26987 bytes)
- customers.csv (101 bytes)
- qualitative_signals.csv (11459 bytes)
- products.csv (156 bytes)
- profiles.csv (1140 bytes)

## Journey Patterns
This customer uses **DEMO_MANIFEST** journey patterns.

## Accounts
- **2001**: LoadTest-Martin, Wright and Rubio - Production
- **2002**: LoadTest-Martin, Wright and Rubio - Staging
- **2003**: LoadTest-Martin, Wright and Rubio - Development

## KPIs (Config-Aware)
- Total measurements: 540
- Enabled KPIs: 15
- Months of data: 12

## Next Steps
1. Run data loading: `02_load_customer2_data_SMART.py`
2. Generate embeddings: `03_embed_customer2_OPENAI.py`
3. Generate journeys: Wizard A
