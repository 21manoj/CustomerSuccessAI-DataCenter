# Demo Manifest - Customer 102

## Overview
- **Customer ID:** 102
- **Company:** E2E UI Test Customer
- **Accounts:** 5
- **Time Period:** 12 months
- **Generated:** 2026-01-28 11:54:18

## Data Files
- accounts.csv (2434 bytes)
- kpi_measurements.csv (46797 bytes)
- customers.csv (88 bytes)
- qualitative_signals.csv (17245 bytes)
- products.csv (164 bytes)
- profiles.csv (1550 bytes)

## Journey Patterns
This customer uses **DEMO_MANIFEST** journey patterns.

## Accounts
- **102001**: E2E UI Test Customer - Production
- **102002**: E2E UI Test Customer - Staging
- **102003**: E2E UI Test Customer - Development
- **102004**: E2E UI Test Customer - QA
- **102005**: E2E UI Test Customer - UAT

## KPIs (Config-Aware)
- Total measurements: 900
- Enabled KPIs: 15
- Months of data: 12

## Next Steps
1. Run data loading: `02_load_customer102_data_SMART.py`
2. Generate embeddings: `03_embed_customer102_OPENAI.py`
3. Generate journeys: Wizard A
