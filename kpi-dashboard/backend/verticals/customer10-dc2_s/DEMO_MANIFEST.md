# Demo Manifest - Customer 10

## Overview
- **Customer ID:** 10
- **Company:** LoadTest-Edwards PLC
- **Accounts:** 3
- **Time Period:** 12 months
- **Generated:** 2026-02-25 20:46:03

## Data Files
- accounts.csv (1619 bytes)
- kpi_measurements.csv (27525 bytes)
- customers.csv (87 bytes)
- qualitative_signals.csv (10296 bytes)
- products.csv (160 bytes)
- profiles.csv (1055 bytes)

## Journey Patterns
This customer uses **DEMO_MANIFEST** journey patterns.

## Accounts
- **10001**: LoadTest-Edwards PLC - Production
- **10002**: LoadTest-Edwards PLC - Staging
- **10003**: LoadTest-Edwards PLC - Development

## KPIs (Config-Aware)
- Total measurements: 540
- Enabled KPIs: 15
- Months of data: 12

## Next Steps
1. Run data loading: `02_load_customer10_data_SMART.py`
2. Generate embeddings: `03_embed_customer10_OPENAI.py`
3. Generate journeys: Wizard A
