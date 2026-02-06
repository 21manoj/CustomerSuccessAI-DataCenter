# Customer 5 Data Directory

Upload your data files here. Required files:

## Required Files

1. **accounts.csv** - Account list with customer_id = 5
2. **kpi_definitions_complete_33_corrected.csv** - KPI metadata
3. **kpi_measurements.csv** - KPI time series data
4. **qualitative_signals.csv** - Engagement signals
5. **account_health_history.csv** - Health score history
6. **playbook_executions.csv** - Playbook execution history

## Optional Files

- partner_definitions.csv
- account_profiles.csv
- expansion_readiness_scores.csv
- products.csv
- account_products.csv

## Usage

After uploading files, run:
```bash
cd /Users/manojgupta/CustomerSuccessAI-DataCenter/kpi-dashboard/backend/agents/../verticals/customer5-dc2_s/scripts
python3 02_load_customer5_data_SMART.py
```

See customer9-dc2_s/data/ for example file formats.
