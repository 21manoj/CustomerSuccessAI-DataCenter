# Demo Manifest - Customer 19

## Overview
- **Customer ID:** 19
- **Company:** DC2_S Demo Enterprise
- **Accounts:** 10
- **Time Period:** 12 months
- **Generated:** 2026-01-27 17:37:59

## Data Files
- accounts.csv (1004 bytes)
- kpi_measurements.csv (91445 bytes)
- customers.csv (88 bytes)
- qualitative_signals.csv (31921 bytes)
- products.csv (150 bytes)

## Journey Patterns
This customer uses **DEMO_MANIFEST** journey patterns.

## Accounts
- **19001**: Customer 19 - Production
- **19002**: Customer 19 - Staging
- **19003**: Customer 19 - Development
- **19004**: Customer 19 - QA
- **19005**: Customer 19 - UAT
- **19006**: Customer 19 - DR
- **19007**: Customer 19 - Sandbox
- **19008**: Customer 19 - Integration
- **19009**: Customer 19 - Performance
- **19010**: Customer 19 - Lab

## KPIs (Config-Aware)
- Total measurements: 1800
- Enabled KPIs: 15
- Months of data: 12

## Next Steps
1. Run data loading: `02_load_customer19_data_SMART.py`
2. Generate embeddings: `03_embed_customer19_OPENAI.py`
3. Generate journeys: Wizard A
