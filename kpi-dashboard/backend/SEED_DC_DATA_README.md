# Data Center Seed Data Guide

This guide explains how to seed the database with Data Center tenant data and KPI history.

## Overview

The seed script creates:
- **100 DC tenant profiles** (20 Enterprise, 40 Mid-Market, 30 SMB, 10 Transactional)
- **6 months of KPI history** for all 31 DC KPIs
- **Realistic health states** to trigger playbooks (expansion, at-risk, critical)
- **Account records** mapped to tenants
- **KPI records** with proper formatting and categorization

## Prerequisites

1. **Database Setup**: Ensure your database is initialized and migrations are run
2. **Generator Script**: The `generate_seed_data.py` script should be available
   - Location: `~/Downloads/dc_seed_data/generate_seed_data.py`
   - Or run it first to generate CSV files

## Usage

### Option 1: Direct Generation (Recommended)

Run the seed script directly. It will:
1. Import the generator script
2. Generate tenant profiles
3. Create database records

```bash
cd kpi-dashboard/backend
python3 seed_dc_data.py
```

### Option 2: Use Existing Customer

If you want to use an existing customer:

```bash
# Use first existing customer
python3 seed_dc_data.py --use-existing-customer

# Use specific customer ID
python3 seed_dc_data.py --customer-id 1
```

### Option 3: Load from CSV

If you've already generated CSV files:

```bash
# First, generate CSV files
cd ~/Downloads/dc_seed_data
python3 generate_seed_data.py

# Then load from CSV
cd ../../kpi-dashboard/backend
python3 seed_dc_data.py --from-csv
```

## What Gets Created

### Accounts (100)
- Account names from generated tenant profiles
- Revenue from ARR (Annual Recurring Revenue)
- Industry assignments
- Region set to "Global"

### KPIs (18,600 total)
- 31 KPIs per tenant
- 6 months of monthly data
- Properly formatted values with units
- Categorized by 5 pillars:
  - Infrastructure & Performance (11 KPIs)
  - Service Delivery (6 KPIs)
  - Customer Sentiment (3 KPIs)
  - Business Outcomes (6 KPIs)
  - Relationship Strength (5 KPIs)

### KPI Uploads
- One upload per tenant per month
- Version numbers 1-6 for 6 months
- Original filenames: `{TenantName}_DC_KPIs_Month_{N}.csv`

## Health Distribution

The seed data includes varied health states:
- **15 Expansion Ready** - High utilization, growing (triggers expansion playbooks)
- **35 Stable Healthy** - Normal operations
- **30 At-Risk** - Some issues (triggers intervention playbooks)
- **20 Critical/Churn** - Severe problems (triggers churn prevention)

## Login Credentials

After seeding, you can login with:
- **Email**: `dc-admin@example.com`
- **Password**: `dc123`

## Data Structure

### Tenant Segments
- **Enterprise** (20): Large customers, 6-20 racks, premium SLAs
- **Mid-Market** (40): Medium customers, 2-8 racks, enhanced SLAs
- **SMB** (30): Small customers, 0.5-3 racks, standard SLAs
- **Transactional** (10): Spot/burst capacity, minimal infrastructure

### KPI Values
Values are generated based on:
- Tenant health category
- Segment characteristics
- Realistic correlations (e.g., high utilization → expansion opportunity)
- Trends (growing, stable, declining)

## Troubleshooting

### Import Error
If you get an import error for `generate_seed_data.py`:
1. Ensure the file exists at `~/Downloads/dc_seed_data/generate_seed_data.py`
2. Or use `--from-csv` option after generating CSV files

### Database Connection
If database connection fails:
1. Check `.env` file has correct `DATABASE_URL`
2. Ensure database is running
3. Run migrations if needed

### Memory Issues
If you encounter memory issues with large datasets:
- The script commits in batches (every 10 tenants)
- Consider seeding in smaller chunks

## Next Steps

After seeding:
1. **Login** to the DC dashboard at `/dc-dashboard`
2. **View tenants** in the Tenant List
3. **Check health scores** for different segments
4. **Test playbooks** - should trigger for at-risk and critical tenants
5. **View KPI trends** over 6 months

## Files Generated

If using CSV option, these files are created:
- `tenants.csv` - Tenant master data
- `kpi_history.csv` - All KPI measurements
- `summary_stats.json` - Generation statistics

## Customization

To modify the seed data:
1. Edit `generate_seed_data.py` to change:
   - Number of tenants
   - Health distribution
   - Date ranges
   - KPI value generation logic
2. Re-run the seed script

