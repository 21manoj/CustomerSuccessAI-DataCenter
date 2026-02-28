# Data Center Vertical Template

This template is used to provision new Data Center customers.

## Template Structure

- `scripts/` - Data loading and processing scripts
- `services/` - Business logic services
- `agents/` - AI agents (Signal Analyst, etc.)
- `api/` - API blueprints
- `data/` - Empty data directory (customer uploads files here)
- `journey/` - Journey visualization data and scripts
- `tests/` - Integration tests

## Placeholders

The following placeholders are replaced during provisioning:

- `283` - Customer ID (e.g., 10)
- `dc2_s` - Vertical slug (e.g., 'dc2_s')
- `293000` - Starting account ID (calculated as 10000 + customer_id * 1000)

## Usage

```bash
python3 provision_dc_customer.py --customer-id 10 --vertical-slug dc2_s
```

## Files to Update After Provisioning

1. Upload data files to `data/` directory
2. Update `scripts/02_load_customer283_data_SMART.py` if needed
3. Run data loading scripts
4. Initialize database schema if needed
