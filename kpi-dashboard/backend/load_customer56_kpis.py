#!/usr/bin/env python3
"""
Load KPI measurements from CSV file for Customer 56 into DC2SKPI table
"""
import pandas as pd
from pathlib import Path
from datetime import datetime
from app_v3_minimal import app
from models import db, Account, DC2SKPI

def load_customer56_kpis():
    """Load KPI measurements from CSV file into database for Customer 56"""
    with app.app_context():
        customer_id = 56
        
        # Verify customer exists
        accounts = Account.query.filter_by(customer_id=customer_id).all()
        if not accounts:
            print(f"❌ No accounts found for customer {customer_id}!")
            return
        
        print(f"✅ Found {len(accounts)} accounts for customer {customer_id}")
        
        # Path to KPI measurements CSV
        base_dir = Path(__file__).parent.parent  # Go up from backend to kpi-dashboard
        csv_path = base_dir / "verticals" / "customer56-dc2_s" / "data" / "kpi_measurements.csv"
        
        if not csv_path.exists():
            print(f"❌ CSV file not found: {csv_path}")
            return
        
        print(f"📂 Reading KPI measurements from: {csv_path}")
        df = pd.read_csv(csv_path)
        print(f"✅ Read {len(df)} KPI measurement rows from CSV")
        
        # Check existing KPIs
        existing = DC2SKPI.query.join(Account).filter(Account.customer_id == customer_id).count()
        print(f"📊 {existing} DC2S KPIs already exist in database")
        
        # Create account lookup
        account_lookup = {acc.account_id: acc for acc in accounts}
        
        kpis_created = 0
        kpis_skipped = 0
        
        for _, row in df.iterrows():
            account_id = int(row['account_id'])
            
            # Verify account exists
            if account_id not in account_lookup:
                print(f"⚠️  Skipping KPI for unknown account_id: {account_id}")
                kpis_skipped += 1
                continue
            
            account = account_lookup[account_id]
            
            # Parse date
            try:
                measured_at = datetime.strptime(row['date'], '%Y-%m-%d')
            except:
                print(f"⚠️  Invalid date format: {row['date']}")
                kpis_skipped += 1
                continue
            
            # Check if KPI already exists (avoid duplicates)
            existing_kpi = DC2SKPI.query.filter_by(
                account_id=account_id,
                kpi_code=row['kpi_code'],
                measured_at=measured_at
            ).first()
            
            if existing_kpi:
                kpis_skipped += 1
                continue
            
            # Create DC2S KPI (model only has: account_id, kpi_code, value, target, pillar, weight, status, measured_at)
            kpi = DC2SKPI(
                account_id=account_id,
                kpi_code=row['kpi_code'],
                pillar=row.get('pillar', '')[:10] if pd.notna(row.get('pillar')) else None,  # Max 10 chars
                value=float(row.get('value', 0)) if pd.notna(row.get('value')) else 0.0,
                target=float(row.get('target', 0)) if pd.notna(row.get('target')) else None,
                weight=None,  # Can be set later if needed
                status=None,  # Can be calculated later
                measured_at=measured_at
            )
            db.session.add(kpi)
            kpis_created += 1
        
        # Commit all changes
        db.session.commit()
        
        print(f"\n✅ Load complete!")
        print(f"   Created: {kpis_created} KPI measurements")
        print(f"   Skipped: {kpis_skipped} (duplicates or invalid)")
        print(f"   Total DC2S KPIs for customer {customer_id}: {DC2SKPI.query.join(Account).filter(Account.customer_id == customer_id).count()}")

if __name__ == '__main__':
    load_customer56_kpis()
