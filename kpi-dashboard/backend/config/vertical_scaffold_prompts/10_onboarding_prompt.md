# Prompt 10: MCP Onboarding Guide Prompt

## Input Variables
- `{VERTICAL_ID}`, `{VERTICAL_NAME}`, `{INDUSTRY_DESCRIPTION}`
- `{KPI_COUNT}`: Total KPIs from Prompt 01
- `{PILLAR_SUMMARY}`: P1-P5 names and KPI counts
- `{CSV_FILES}`: The 8 customer-provided + 3 platform files
- `{NOMENCLATURE}`: Key entity labels from Prompt 05
- `{TYPICAL_SOURCE_SYSTEMS}`: From Prompt 02 integration settings

## Prompt

```
You are writing an MCP (Model Context Protocol) onboarding guide for
CS Pulse's AI assistant that helps onboard {VERTICAL_NAME} customers.
The guide instructs the AI on how to walk a customer through data
preparation and upload.

CONTEXT:
- Vertical: {VERTICAL_NAME} ({VERTICAL_ID})
- {KPI_COUNT} KPIs across 5 pillars: {PILLAR_SUMMARY}
- CSV files: {CSV_FILES}
- Entity terminology: {NOMENCLATURE}
- Common source systems: {TYPICAL_SOURCE_SYSTEMS}

GENERATE A MARKDOWN GUIDE with these sections:

I. OVERVIEW
   - What CS Pulse does for {VERTICAL_NAME} customers
   - The 5-pillar health model (use vertical-specific pillar names)
   - What the customer will get after onboarding

II. DATA PREPARATION
   - 11 CSV file types: 8 customer-provided + 3 auto-generated
   - For each customer-provided file:
     - Purpose (in {VERTICAL_NAME} context)
     - Required columns with descriptions
     - Optional columns
     - Where to get this data (source systems)
     - Common pitfalls

III. ONBOARDING SEQUENCE (4-week plan)
   - Week 1: Foundation data (accounts, products)
   - Week 2: KPI measurements, qualitative signals
   - Week 3: Context graph data (stakeholders, engagement)
   - Week 4: Calibration (Wizard C weight tuning)

IV. SOURCE SYSTEM MAPPING
   - For each of the 8 files, which source systems typically provide the data
   - Example: accounts.csv ← CRM (Salesforce, HubSpot)
   - Example: kpi_measurements.csv ← Monitoring (Datadog, Prometheus, ServiceNow)

V. VALIDATION RULES
   - Required fields that must not be null
   - Date format requirements (ISO 8601)
   - KPI code format (P{n}-KPI{m})
   - Account ID consistency across files

VI. FAQ
   - 5-8 common questions for this vertical's onboarding

TONE:
- Professional but approachable
- Use {VERTICAL_NAME} terminology (from nomenclature)
- Assume the reader is a CS operations person, not a developer
- Include specific examples relevant to {INDUSTRY_DESCRIPTION}

CRITICAL:
- Reference exact CSV file names from the platform
- Reference exact column names from csv_schemas.json
- Use P-format KPI codes only
- Include the 3 auto-generated files with explanation that customer doesn't provide them
```
