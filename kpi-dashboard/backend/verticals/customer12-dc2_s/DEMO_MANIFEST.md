# Demo Manifest - Customer 12

## Overview
- **Customer ID:** 12
- **Company:** LoadTest-Perry, Rice and Bates
- **Accounts:** 3
- **Time Period:** 12 months
- **Generated:** 2026-02-25 20:48:39

## Data Files
- accounts.csv (1673 bytes)
- kpi_measurements.csv (27476 bytes)
- customers.csv (99 bytes)
- qualitative_signals.csv (11490 bytes)
- products.csv (160 bytes)
- profiles.csv (1120 bytes)

## Journey Patterns
This customer uses **DEMO_MANIFEST** journey patterns.

## Accounts
- **12001**: LoadTest-Perry, Rice and Bates - Production
- **12002**: LoadTest-Perry, Rice and Bates - Staging
- **12003**: LoadTest-Perry, Rice and Bates - Development

## KPIs (Config-Aware)
- Total measurements: 540
- Enabled KPIs: 15
- Months of data: 12

## Next Steps
1. Run data loading: `02_load_customer12_data_SMART.py`
2. Generate embeddings: `03_embed_customer12_OPENAI.py`
3. Generate journeys: Wizard A
