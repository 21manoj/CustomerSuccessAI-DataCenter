# Demo Manifest - Customer 333

## Overview
- **Customer ID:** 333
- **Company:** LoadTest-Johnson PLC
- **Accounts:** 15
- **Time Period:** 12 months
- **Generated:** 2026-03-10 21:20:00

## Data Files
- accounts.csv (6225 bytes)
- kpi_measurements.csv (113660 bytes)
- customers.csv (138 bytes)
- qualitative_signals.csv (62438 bytes)
- products.csv (164 bytes)
- profiles.csv (3936 bytes)

## Journey Patterns
This customer uses **DEMO_MANIFEST** journey patterns.

## Accounts
- **333001**: LoadTest-Johnson PLC - Production
- **333002**: LoadTest-Johnson PLC - Staging
- **333003**: LoadTest-Johnson PLC - Development
- **333004**: LoadTest-Johnson PLC - QA
- **333005**: LoadTest-Johnson PLC - UAT
- **333006**: LoadTest-Johnson PLC - DR
- **333007**: LoadTest-Johnson PLC - Sandbox
- **333008**: LoadTest-Johnson PLC - Integration
- **333009**: LoadTest-Johnson PLC - Performance
- **333010**: LoadTest-Johnson PLC - Lab
- **333011**: LoadTest-Johnson PLC - Account-11
- **333012**: LoadTest-Johnson PLC - Account-12
- **333013**: LoadTest-Johnson PLC - Account-13
- **333014**: LoadTest-Johnson PLC - Account-14
- **333015**: LoadTest-Johnson PLC - Account-15

## KPIs (Config-Aware)
- Total measurements: 2160
- Enabled KPIs: 12
- Months of data: 12

## Next Steps
1. Run data loading: `02_load_customer333_data_SMART.py`
2. Generate embeddings: `03_embed_customer333_OPENAI.py`
3. Generate journeys: Wizard A
