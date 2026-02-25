# Demo Manifest - Customer 8

## Overview
- **Customer ID:** 8
- **Company:** LoadTest-Edwards PLC
- **Accounts:** 3
- **Time Period:** 12 months
- **Generated:** 2026-02-25 20:44:52

## Data Files
- accounts.csv (1658 bytes)
- kpi_measurements.csv (26949 bytes)
- customers.csv (86 bytes)
- qualitative_signals.csv (9969 bytes)
- products.csv (156 bytes)
- profiles.csv (1084 bytes)

## Journey Patterns
This customer uses **DEMO_MANIFEST** journey patterns.

## Accounts
- **8001**: LoadTest-Edwards PLC - Production
- **8002**: LoadTest-Edwards PLC - Staging
- **8003**: LoadTest-Edwards PLC - Development

## KPIs (Config-Aware)
- Total measurements: 540
- Enabled KPIs: 15
- Months of data: 12

## Next Steps
1. Run data loading: `02_load_customer8_data_SMART.py`
2. Generate embeddings: `03_embed_customer8_OPENAI.py`
3. Generate journeys: Wizard A
