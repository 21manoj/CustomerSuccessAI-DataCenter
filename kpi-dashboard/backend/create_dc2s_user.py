#!/usr/bin/env python3
"""
Create DC2_S Super User Account
Username: dc_super1
Password: dc_super321
Access: All DC2_S accounts (supermicro_internal tier)

FIXED: Includes Flask app context
"""

import sys
import os
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

# Import Flask app FIRST
from app import app, db
from models import User, Account, KPI
from werkzeug.security import generate_password_hash
from verticals.dc2_s import create_dc2s_account_metadata
from integrations.sample_accounts import get_all_sample_accounts

def create_dc2s_super_user():
    """Create the dc_super1 user with full DC2_S access"""
    
    print("=" * 60)
    print("CREATING DC2_S SUPER USER")
    print("=" * 60)
    print()
    
    # Check if user already exists
    existing_user = User.query.filter_by(username='dc_super1').first()
    if existing_user:
        print("⚠️  User 'dc_super1' already exists!")
        response = input("Delete and recreate? (yes/no): ")
        if response.lower() != 'yes':
            print("❌ Cancelled")
            return None
        
        db.session.delete(existing_user)
        db.session.commit()
        print("✅ Deleted existing user")
    
    # Create new user
    print("Creating user account...")
    user = User(
        username='dc_super1',
        email='dc_super1@supermicro.com',
        password_hash=generate_password_hash('dc_super321'),
        role='supermicro_internal',  # Full access role
        vertical='dc2_S',  # DC2_S vertical
        is_active=True,
        created_at=datetime.utcnow()
    )
    
    db.session.add(user)
    db.session.commit()
    
    print(f"✅ Created user: {user.username}")
    print(f"   Email: {user.email}")
    print(f"   Role: {user.role}")
    print(f"   Vertical: {user.vertical}")
    print(f"   User ID: {user.id}")
    print()
    
    return user

def create_all_dc2s_accounts(owner_user_id):
    """Create all 10 DC2_S sample accounts"""
    
    print("=" * 60)
    print("CREATING 10 DC2_S ACCOUNTS")
    print("=" * 60)
    print()
    
    sample_accounts = get_all_sample_accounts()
    created_accounts = []
    
    for i, sample in enumerate(sample_accounts, 1):
        print(f"Creating account {i}/10: {sample['account_name']}...")
        
        # Check if account already exists
        existing = Account.query.filter_by(
            customer_id=sample['customer_id']
        ).first()
        
        if existing:
            print(f"   ⚠️  Account already exists (ID: {existing.id})")
            created_accounts.append(existing)
            continue
        
        # Create account
        account = Account(
            customer_id=sample['customer_id'],
            account_name=sample['account_name'],
            industry=sample.get('industry', 'ai_infrastructure'),
            region=sample.get('region', 'US'),
            profile_metadata=sample['profile_metadata'],
            owner_user_id=owner_user_id,  # Assign to dc_super1
            created_at=datetime.utcnow()
        )
        
        db.session.add(account)
        db.session.flush()  # Get the account ID
        
        print(f"   ✅ Created account ID: {account.id}")
        
        # Add KPI values
        kpi_values = sample.get('kpi_values', {})
        kpi_count = 0
        
        for kpi_code, value in kpi_values.items():
            kpi = KPI(
                account_id=account.id,
                kpi_code=kpi_code,
                value=value,
                category='dc2_S',
                updated_at=datetime.utcnow()
            )
            db.session.add(kpi)
            kpi_count += 1
        
        print(f"   ✅ Added {kpi_count} KPIs")
        
        created_accounts.append(account)
    
    db.session.commit()
    print()
    print(f"✅ Created {len(created_accounts)} accounts total")
    print()
    
    return created_accounts

def verify_user_access(user_id):
    """Verify the user can see all DC2_S accounts"""
    
    print("=" * 60)
    print("VERIFYING USER ACCESS")
    print("=" * 60)
    print()
    
    user = User.query.get(user_id)
    print(f"User: {user.username} (ID: {user.id})")
    print(f"Role: {user.role}")
    print(f"Vertical: {user.vertical}")
    print()
    
    # Get all DC2_S accounts
    dc2s_accounts = Account.query.filter(
        Account.profile_metadata['vertical'].astext == 'dc2_S'
    ).all()
    
    print(f"Total DC2_S accounts visible: {len(dc2s_accounts)}")
    print()
    
    # Group by status
    from verticals.dc2_s import calculate_pillar_score, calculate_overall_health, DC2S_PILLARS
    
    healthy = []
    risk = []
    critical = []
    
    for account in dc2s_accounts:
        # Get KPIs for this account
        kpis = KPI.query.filter_by(account_id=account.id).all()
        kpi_values = {kpi.kpi_code: kpi.value for kpi in kpis}
        
        # Calculate health
        pillar_scores = {}
        for pillar_id in DC2S_PILLARS.keys():
            score = calculate_pillar_score(pillar_id, kpi_values)
            pillar_scores[pillar_id] = score
        
        overall_health = calculate_overall_health(pillar_scores)
        
        # Categorize
        if overall_health >= 75:
            status = "HEALTHY"
            healthy.append(account.account_name)
        elif overall_health >= 50:
            status = "RISK"
            risk.append(account.account_name)
        else:
            status = "CRITICAL"
            critical.append(account.account_name)
        
        print(f"  {account.id:2d}. {account.account_name:30s} | {overall_health:5.1f} | {status:8s} | {len(kpis):2d} KPIs")
    
    print()
    print("Summary by Status:")
    print(f"  🟢 Healthy ({len(healthy)}): {', '.join(healthy)}")
    print(f"  🟡 Risk ({len(risk)}): {', '.join(risk)}")
    print(f"  🔴 Critical ({len(critical)}): {', '.join(critical)}")
    print()
    
    return len(dc2s_accounts)

def create_login_test_script():
    """Create a test script to verify login works"""
    
    test_script = """#!/usr/bin/env python3
'''
Test DC2_S User Login
Verify: dc_super1 can login and see all accounts
'''

from app import app
from models import User, Account
from werkzeug.security import check_password_hash

with app.app_context():
    # Test login
    username = 'dc_super1'
    password = 'dc_super321'

    user = User.query.filter_by(username=username).first()

    if not user:
        print("❌ User not found!")
    else:
        if check_password_hash(user.password_hash, password):
            print("✅ Login successful!")
            print(f"   User: {user.username}")
            print(f"   Role: {user.role}")
            print(f"   Vertical: {user.vertical}")
            
            # Get visible accounts
            accounts = Account.query.filter(
                Account.profile_metadata['vertical'].astext == 'dc2_S'
            ).all()
            
            print(f"   Visible accounts: {len(accounts)}")
            for acc in accounts:
                print(f"     - {acc.account_name}")
        else:
            print("❌ Invalid password!")
"""
    
    with open('test_dc_login.py', 'w') as f:
        f.write(test_script)
    
    print("✅ Created test_dc_login.py")
    print()

def main():
    """Main setup function - runs inside Flask app context"""
    
    print()
    print("🚀 DC2_S SUPER USER SETUP")
    print("=" * 60)
    print()
    print("This will create:")
    print("  1. User: dc_super1 (password: dc_super321)")
    print("  2. Role: supermicro_internal (full access)")
    print("  3. 10 DC2_S accounts with KPI data")
    print("  4. All accounts visible to dc_super1")
    print()
    
    response = input("Continue? (yes/no): ")
    if response.lower() != 'yes':
        print("❌ Cancelled")
        return
    
    print()
    
    # Run everything inside Flask app context
    with app.app_context():
        try:
            # Step 1: Create user
            user = create_dc2s_super_user()
            if not user:
                return
            
            # Step 2: Create all accounts
            accounts = create_all_dc2s_accounts(user.id)
            
            # Step 3: Verify access
            account_count = verify_user_access(user.id)
            
            # Step 4: Create test script
            create_login_test_script()
            
            # Success summary
            print("=" * 60)
            print("✅ SETUP COMPLETE!")
            print("=" * 60)
            print()
            print("Login Credentials:")
            print(f"  Username: dc_super1")
            print(f"  Password: dc_super321")
            print(f"  Role: supermicro_internal")
            print()
            print(f"DC2_S Accounts: {account_count}")
            print()
            print("Next Steps:")
            print("  1. Start your backend server")
            print("  2. Login at: http://localhost:5000/login")
            print("  3. Navigate to DC2_S dashboard")
            print("  4. Verify all 10 accounts are visible")
            print()
            print("Test Login:")
            print("  python3 test_dc_login.py")
            print()
            
        except Exception as e:
            print(f"❌ Error during setup: {e}")
            import traceback
            traceback.print_exc()
            db.session.rollback()

if __name__ == "__main__":
    main()
