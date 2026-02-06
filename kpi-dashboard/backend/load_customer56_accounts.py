#!/usr/bin/env python3
"""
Load accounts from CSV file for Customer 56
"""
import pandas as pd
from pathlib import Path
from app_v3_minimal import app
from models import db, Account, Customer, User

def load_customer56_accounts():
    """Load accounts from CSV file into database for Customer 56"""
    with app.app_context():
        customer_id = 56
        
        # Verify customer exists
        customer = Customer.query.filter_by(customer_id=customer_id).first()
        if not customer:
            print(f"❌ Customer {customer_id} not found!")
            return
        
        print(f"✅ Found customer: {customer.customer_name} (ID: {customer_id})")
        
        # Get user for this customer
        user = User.query.filter_by(customer_id=customer_id).first()
        if not user:
            print(f"❌ No user found for customer {customer_id}!")
            return
        
        # Path to accounts CSV (verticals is at kpi-dashboard root, not backend)
        base_dir = Path(__file__).parent.parent  # Go up from backend to kpi-dashboard
        csv_path = base_dir / "verticals" / "customer56-dc2_s" / "data" / "accounts.csv"
        
        if not csv_path.exists():
            print(f"❌ CSV file not found: {csv_path}")
            return
        
        print(f"📂 Reading accounts from: {csv_path}")
        df = pd.read_csv(csv_path)
        print(f"✅ Read {len(df)} accounts from CSV")
        
        # Check existing accounts
        existing = Account.query.filter_by(customer_id=customer_id).count()
        print(f"📊 {existing} accounts already exist in database")
        
        accounts_created = 0
        accounts_updated = 0
        
        for _, row in df.iterrows():
            account_id = int(row['account_id'])
            account_name = row['account_name']
            
            # Check if account already exists
            account = Account.query.filter_by(
                customer_id=customer_id,
                account_id=account_id
            ).first()
            
            if account:
                # Update existing account
                account.account_name = account_name
                account.revenue = float(row.get('revenue', 0))
                account.industry = row.get('industry', 'Unknown')
                account.region = row.get('region', 'Unknown')
                account.account_status = row.get('account_status', 'active')
                account.vertical = 'dc2_s'  # Set vertical
                accounts_updated += 1
            else:
                # Create new account
                account = Account(
                    customer_id=customer_id,
                    account_id=account_id,  # Use the account_id from CSV
                    account_name=account_name,
                    revenue=float(row.get('revenue', 0)),
                    industry=row.get('industry', 'Unknown'),
                    region=row.get('region', 'Unknown'),
                    account_status=row.get('account_status', 'active'),
                    vertical='dc2_s'
                )
                db.session.add(account)
                accounts_created += 1
        
        # Commit all changes
        db.session.commit()
        
        print(f"\n✅ Load complete!")
        print(f"   Created: {accounts_created} accounts")
        print(f"   Updated: {accounts_updated} accounts")
        print(f"   Total accounts for customer {customer_id}: {Account.query.filter_by(customer_id=customer_id).count()}")

if __name__ == '__main__':
    load_customer56_accounts()
