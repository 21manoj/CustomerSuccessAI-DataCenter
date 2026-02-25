# Demo Manifest - Customer 9

## Overview
- **Customer ID:** 9
- **Company:** LoadTest-Edwards PLC
- **Accounts:** 3
- **Time Period:** 12 months
- **Generated:** 2026-02-25 20:45:27

## Data Files
- accounts.csv (1645 bytes)
- kpi_measurements.csv (26954 bytes)
- customers.csv (86 bytes)
- qualitative_signals.csv (10205 bytes)
- products.csv (156 bytes)
- profiles.csv (1064 bytes)

## Journey Patterns
This customer uses **DEMO_MANIFEST** journey patterns.

## Accounts
- **9001**: LoadTest-Edwards PLC - Production
- **9002**: LoadTest-Edwards PLC - Staging
- **9003**: LoadTest-Edwards PLC - Development

## KPIs (Config-Aware)
- Total measurements: 540
- Enabled KPIs: 15
- Months of data: 12

## Next Steps
1. Run data loading: `02_load_customer9_data_SMART.py`
2. Generate embeddings: `03_embed_customer9_OPENAI.py`
3. Generate journeys: Wizard A
