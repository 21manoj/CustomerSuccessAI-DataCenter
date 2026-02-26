# Demo Manifest - Customer 24

## Overview
- **Customer ID:** 24
- **Company:** LoadTest-Donovan, Morrow and Gillespie
- **Accounts:** 3
- **Time Period:** 12 months
- **Generated:** 2026-02-26 00:33:11

## Data Files
- accounts.csv (1702 bytes)
- kpi_measurements.csv (27560 bytes)
- customers.csv (157 bytes)
- qualitative_signals.csv (12164 bytes)
- products.csv (160 bytes)
- profiles.csv (1118 bytes)

## Journey Patterns
This customer uses **DEMO_MANIFEST** journey patterns.

## Accounts
- **24001**: LoadTest-Donovan, Morrow and Gillespie - Production
- **24002**: LoadTest-Donovan, Morrow and Gillespie - Staging
- **24003**: LoadTest-Donovan, Morrow and Gillespie - Development

## KPIs (Config-Aware)
- Total measurements: 540
- Enabled KPIs: 15
- Months of data: 12

## Next Steps
1. Run data loading: `02_load_customer24_data_SMART.py`
2. Generate embeddings: `03_embed_customer24_OPENAI.py`
3. Generate journeys: Wizard A
