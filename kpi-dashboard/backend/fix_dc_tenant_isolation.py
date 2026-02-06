#!/usr/bin/env python3
"""
Fix Data Center Tenant Isolation Issue

This script:
1. Creates a separate Customer record for Supermicro/Data Center
2. Moves DC user (dc_super1@supermicro.com) to the new customer_id
3. Moves all DC accounts (vertical='dc2_s') to the new customer_id
4. Ensures complete tenant isolation between SaaS and Data Center verticals

CRITICAL: This fixes the security issue where DC users could see SaaS accounts.
"""

import os
from dotenv import load_dotenv
load_dotenv()
import sys
sys.path.insert(0, os.path.dirname(__file__))

from extensions import db
from models import User, Customer, Account, DC2SKPI
from app_v3_minimal import app
from datetime import datetime

def fix_dc_tenant_isolation():
    """Fix tenant isolation for Data Center vertical"""
    
    print()
    print("=" * 70)
    print("FIXING DATA CENTER TENANT ISOLATION")
    print("=" * 70)
    print()
    
    with app.app_context():
        # Step 1: Create or get Supermicro customer
        print("Step 1: Ensuring Supermicro customer exists...")
        supermicro_customer = Customer.query.filter_by(customer_name='Supermicro').first()
        if not supermicro_customer:
            supermicro_customer = Customer(
                customer_name='Supermicro',
                email='admin@supermicro.com',
                domain='supermicro.com',
                created_at=datetime.utcnow()
            )
            db.session.add(supermicro_customer)
            db.session.commit()
            print(f"  ✅ Created Supermicro customer: customer_id={supermicro_customer.customer_id}")
        else:
            print(f"  ✅ Supermicro customer exists: customer_id={supermicro_customer.customer_id}")
        new_customer_id = supermicro_customer.customer_id
        
        # Step 2: Move DC user to new customer_id
        print()
        print("Step 2: Moving DC user to Supermicro customer...")
        dc_user = User.query.filter_by(email='dc_super1@supermicro.com').first()
        if not dc_user:
            print("  ❌ ERROR: DC user not found!")
            return
        
        old_user_customer_id = dc_user.customer_id
        if dc_user.customer_id != new_customer_id:
            print(f"  Moving user from customer_id={old_user_customer_id} to customer_id={new_customer_id}")
            dc_user.customer_id = new_customer_id
            db.session.commit()
            print(f"  ✅ DC user moved to customer_id={new_customer_id}")
        else:
            print(f"  ✅ DC user already has correct customer_id={new_customer_id}")
        
        # Step 3: Move all DC accounts to new customer_id
        print()
        print("Step 3: Moving DC accounts to Supermicro customer...")
        dc_accounts = Account.query.filter_by(vertical='dc2_s').all()
        
        accounts_to_move = [a for a in dc_accounts if a.customer_id != new_customer_id]
        print(f"  Found {len(dc_accounts)} DC accounts")
        print(f"  {len(accounts_to_move)} need to be moved to customer_id={new_customer_id}")
        
        moved_count = 0
        for account in accounts_to_move:
            old_account_customer_id = account.customer_id
            account.customer_id = new_customer_id
            moved_count += 1
            print(f"    Moving account_id={account.account_id} ({account.account_name}) from customer_id={old_account_customer_id} to {new_customer_id}")
        
        if moved_count > 0:
            db.session.commit()
            print(f"  ✅ Moved {moved_count} DC accounts to customer_id={new_customer_id}")
        else:
            print(f"  ✅ All DC accounts already have correct customer_id={new_customer_id}")
        
        # Step 4: Verify isolation
        print()
        print("Step 4: Verifying tenant isolation...")
        
        # Check DC user's customer
        dc_user = User.query.filter_by(email='dc_super1@supermicro.com').first()
        print(f"  DC user customer_id: {dc_user.customer_id}")
        
        # Count accounts for each customer
        for customer in Customer.query.all():
            total_accounts = Account.query.filter_by(customer_id=customer.customer_id).count()
            dc_accounts_count = Account.query.filter_by(customer_id=customer.customer_id, vertical='dc2_s').count()
            saas_accounts_count = Account.query.filter(
                Account.customer_id == customer.customer_id,
                (Account.vertical == 'saas') | (Account.vertical.is_(None))
            ).count()
            print(f"  Customer {customer.customer_id} ({customer.customer_name}): {total_accounts} total ({dc_accounts_count} DC, {saas_accounts_count} SaaS)")
        
        # Final verification
        print()
        print("=" * 70)
        print("VERIFICATION SUMMARY")
        print("=" * 70)
        print()
        print(f"✅ DC user (dc_super1@supermicro.com):")
        print(f"   customer_id: {dc_user.customer_id}")
        print(f"   customer_name: {supermicro_customer.customer_name}")
        print(f"   vertical: {dc_user.vertical}")
        print()
        
        dc_user_accounts = Account.query.filter_by(
            customer_id=dc_user.customer_id,
            vertical='dc2_s'
        ).all()
        print(f"✅ DC accounts visible to DC user: {len(dc_user_accounts)}")
        
        # Verify no SaaS accounts are visible
        saas_accounts_in_dc_customer = Account.query.filter(
            Account.customer_id == dc_user.customer_id,
            (Account.vertical == 'saas') | (Account.vertical.is_(None))
        ).count()
        print(f"✅ SaaS accounts in DC customer (should be 0): {saas_accounts_in_dc_customer}")
        
        if saas_accounts_in_dc_customer == 0:
            print()
            print("✅ TENANT ISOLATION VERIFIED!")
            print("   DC users will only see DC accounts")
        else:
            print()
            print("⚠️  WARNING: SaaS accounts found in DC customer!")
            print("   This indicates incomplete isolation.")
        
        print()
        print("=" * 70)
        print("FIX COMPLETE")
        print("=" * 70)
        print()
        print("Next steps:")
        print("1. Restart the backend server")
        print("2. Log in as dc_super1@supermicro.com / dc_super321")
        print("3. Verify only DC accounts are visible (should see ~12 DC accounts)")
        print()

if __name__ == "__main__":
    fix_dc_tenant_isolation()
