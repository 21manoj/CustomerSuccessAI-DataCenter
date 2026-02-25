# Demo Manifest - Customer 11

## Overview
- **Customer ID:** 11
- **Company:** LoadTest-Edwards PLC
- **Accounts:** 3
- **Time Period:** 12 months
- **Generated:** 2026-02-25 20:46:39

## Data Files
- accounts.csv (1632 bytes)
- kpi_measurements.csv (27487 bytes)
- customers.csv (87 bytes)
- qualitative_signals.csv (10215 bytes)
- products.csv (160 bytes)
- profiles.csv (1065 bytes)

## Journey Patterns
This customer uses **DEMO_MANIFEST** journey patterns.

## Accounts
- **11001**: LoadTest-Edwards PLC - Production
- **11002**: LoadTest-Edwards PLC - Staging
- **11003**: LoadTest-Edwards PLC - Development

## KPIs (Config-Aware)
- Total measurements: 540
- Enabled KPIs: 15
- Months of data: 12

## Next Steps
1. Run data loading: `02_load_customer11_data_SMART.py`
2. Generate embeddings: `03_embed_customer11_OPENAI.py`
3. Generate journeys: Wizard A
