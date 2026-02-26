# Demo Manifest - Customer 20

## Overview
- **Customer ID:** 20
- **Company:** E2E Test Company Accounts 596603
- **Accounts:** 5
- **Time Period:** 12 months
- **Generated:** 2026-02-26 00:27:00

## Data Files
- accounts.csv (2430 bytes)
- kpi_measurements.csv (45936 bytes)
- customers.csv (149 bytes)
- qualitative_signals.csv (18910 bytes)
- products.csv (160 bytes)
- profiles.csv (1607 bytes)

## Journey Patterns
This customer uses **DEMO_MANIFEST** journey patterns.

## Accounts
- **20001**: E2E Test Company Accounts 596603 - Production
- **20002**: E2E Test Company Accounts 596603 - Staging
- **20003**: E2E Test Company Accounts 596603 - Development
- **20004**: E2E Test Company Accounts 596603 - QA
- **20005**: E2E Test Company Accounts 596603 - UAT

## KPIs (Config-Aware)
- Total measurements: 900
- Enabled KPIs: 15
- Months of data: 12

## Next Steps
1. Run data loading: `02_load_customer20_data_SMART.py`
2. Generate embeddings: `03_embed_customer20_OPENAI.py`
3. Generate journeys: Wizard A
