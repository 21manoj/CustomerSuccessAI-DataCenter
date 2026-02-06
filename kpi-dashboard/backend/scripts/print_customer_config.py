#!/usr/bin/env python3
"""
Print CustomerConfig parameters for a customer (e.g. customer 19).
Run from repo root: PYTHONPATH=. python3 kpi-dashboard/backend/scripts/print_customer_config.py [customer_id]
Default customer_id: 19
"""

import sys
import json
from pathlib import Path

# Add backend to path
backend = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend))

def main():
    customer_id = int(sys.argv[1]) if len(sys.argv) > 1 else 19

    from app_v3_minimal import app
    from models import Customer, CustomerConfig

    with app.app_context():
        customer = Customer.query.get(customer_id)
        if not customer:
            print(f"Customer {customer_id} not found.")
            return 1

        config = CustomerConfig.query.filter_by(customer_id=customer_id).first()
        print(f"=== Config for customer_id={customer_id} ({customer.customer_name}) ===\n")

        if not config:
            print("No CustomerConfig row found. Defaults are used (see dc2s_config_api).")
            return 0

        print("customer_configs row:")
        print(f"  config_id: {config.config_id}")
        print(f"  customer_id: {config.customer_id}")
        print(f"  vertical: {config.vertical}")
        print(f"  kpi_upload_mode: {config.kpi_upload_mode}")
        print(f"  config_version: {config.config_version}")
        print(f"  updated_at: {config.updated_at}")
        print(f"  customized_by: {getattr(config, 'customized_by', None)}")

        print("\nDC2_S fields (used when vertical='dc2_s'):")
        print(f"  dc2s_pillar_weights: {json.dumps(config.dc2s_pillar_weights, indent=4) if config.dc2s_pillar_weights else None}")
        enabled = config.dc2s_enabled_kpis
        print(f"  dc2s_enabled_kpis: {len(enabled) if enabled else 0} items" + (f" e.g. {enabled[:5]}..." if enabled and len(enabled) > 5 else f" {enabled}"))
        print(f"  dc2s_kpi_overrides: {json.dumps(config.dc2s_kpi_overrides, indent=4) if config.dc2s_kpi_overrides else None}")
        print(f"  dc2s_kpi_weights: {json.dumps(config.dc2s_kpi_weights, indent=4) if config.dc2s_kpi_weights else None}")
        print(f"  dc2s_kpi_definitions: {len(config.dc2s_kpi_definitions or {})} custom definitions")

        print("\nHealth/weights: When vertical is dc2_s, health and weight scores use dc2s_pillar_weights from this row (config-aware). Fallback to code defaults is logged explicitly.")
        return 0

if __name__ == "__main__":
    sys.exit(main())
