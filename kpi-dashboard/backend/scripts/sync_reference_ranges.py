#!/usr/bin/env python3
"""
Synchronize system KPI reference ranges with health_score_config and seed a tenant's overrides.

Actions:
- Upsert system defaults (customer_id = NULL) to exactly match KPI_REFERENCE_RANGES
- Optionally seed a specific customer with fresh overrides copied from system defaults
"""
import argparse
from typing import Dict, Any

from app_v3_minimal import app
from extensions import db
from models import KPIReferenceRange, Customer
from health_score_config import KPI_REFERENCE_RANGES


def upsert_system_defaults():
    """Upsert system (global) KPI reference ranges to align with KPI_REFERENCE_RANGES."""
    # Build lookup of existing system defaults
    existing: Dict[str, KPIReferenceRange] = {
        r.kpi_name: r
        for r in KPIReferenceRange.query.filter_by(customer_id=None).all()
    }

    # Upsert/update all defined KPIs
    for kpi_name, cfg in KPI_REFERENCE_RANGES.items():
        ranges: Dict[str, Any] = cfg["ranges"]
        unit = cfg.get("unit", "")
        hib = bool(cfg.get("higher_is_better", True))

        # Normalize by color keys (low/medium/high) → red/yellow/green mapping is handled in API
        low = ranges.get("low") or ranges.get("critical") or ranges.get("red") or {}
        medium = ranges.get("medium") or ranges.get("risk") or ranges.get("yellow") or {}
        high = ranges.get("high") or ranges.get("healthy") or ranges.get("green") or {}

        if kpi_name in existing:
            r = existing[kpi_name]
            r.unit = unit
            r.higher_is_better = hib
            r.critical_min = low.get("min", r.critical_min)
            r.critical_max = low.get("max", r.critical_max)
            r.risk_min = medium.get("min", r.risk_min)
            r.risk_max = medium.get("max", r.risk_max)
            r.healthy_min = high.get("min", r.healthy_min)
            r.healthy_max = high.get("max", r.healthy_max)
            r.critical_range = f"{r.critical_min}-{r.critical_max} {unit}"
            r.risk_range = f"{r.risk_min}-{r.risk_max} {unit}"
            r.healthy_range = f"{r.healthy_min}-{r.healthy_max} {unit}"
        else:
            r = KPIReferenceRange(
                customer_id=None,
                kpi_name=kpi_name,
                unit=unit,
                higher_is_better=hib,
                critical_min=low.get("min", 0),
                critical_max=low.get("max", 0),
                risk_min=medium.get("min", 0),
                risk_max=medium.get("max", 0),
                healthy_min=high.get("min", 0),
                healthy_max=high.get("max", 0),
                critical_range=f"{low.get('min',0)}-{low.get('max',0)} {unit}",
                risk_range=f"{medium.get('min',0)}-{medium.get('max',0)} {unit}",
                healthy_range=f"{high.get('min',0)}-{high.get('max',0)} {unit}",
            )
            db.session.add(r)

    # Remove any system defaults no longer in config
    to_delete = [
        r for name, r in existing.items() if name not in KPI_REFERENCE_RANGES
    ]
    for r in to_delete:
        db.session.delete(r)


def seed_customer_overrides(customer_id: int):
    """Replace a customer's overrides with copies of current system defaults."""
    # delete existing overrides for this customer
    KPIReferenceRange.query.where(KPIReferenceRange.customer_id == customer_id).delete()

    system_defaults = KPIReferenceRange.query.filter_by(customer_id=None).all()
    for ref in system_defaults:
        db.session.add(
            KPIReferenceRange(
                customer_id=customer_id,
                kpi_name=ref.kpi_name,
                unit=ref.unit,
                higher_is_better=ref.higher_is_better,
                critical_min=ref.critical_min,
                critical_max=ref.critical_max,
                risk_min=ref.risk_min,
                risk_max=ref.risk_max,
                healthy_min=ref.healthy_min,
                healthy_max=ref.healthy_max,
                critical_range=ref.critical_range,
                risk_range=ref.risk_range,
                healthy_range=ref.healthy_range,
                description=ref.description,
            )
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--customer", help="Customer name to seed overrides for (optional)")
    args = parser.parse_args()

    with app.app_context():
        # 1) Upsert system defaults
        upsert_system_defaults()
        db.session.commit()
        system_total = KPIReferenceRange.query.filter_by(customer_id=None).count()
        print(f"✅ System defaults synced: {system_total} KPIs")

        # 2) Optionally seed a specific tenant
        if args.customer:
            cust = Customer.query.filter(Customer.customer_name == args.customer).first()
            if not cust:
                print(f"❌ Customer '{args.customer}' not found")
                return
            seed_customer_overrides(cust.customer_id)
            db.session.commit()
            tenant_total = KPIReferenceRange.query.filter_by(customer_id=cust.customer_id).count()
            print(f"✅ Seeded customer '{cust.customer_name}' (id={cust.customer_id}) with {tenant_total} KPI overrides")


if __name__ == "__main__":
    main()


