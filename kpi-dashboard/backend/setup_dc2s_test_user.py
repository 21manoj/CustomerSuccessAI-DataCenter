#!/usr/bin/env python3
"""Setup DC2_S Test User - Complete Setup"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash

load_dotenv()

print("=" * 70)
print("DC2_S TEST USER SETUP")
print("=" * 70)

engine = create_engine(os.getenv("DATABASE_URL"))

# Configuration - use same hashing as login (app_v3_minimal / seed_all_data)
HASH_METHOD = "pbkdf2:sha256"
TEST_USERNAME = "dc2s_super"
TEST_EMAIL = "dc2s_super@test.com"
TEST_PASSWORD = "DC2_Super_2024!"  # Change this to something secure
TEST_CUSTOMER_ID = 5  # Use customer_id = 5 for DC2_S vertical

print("\nTest User Configuration:")
print(f"  Username: {TEST_USERNAME}")
print(f"  Email: {TEST_EMAIL}")
print(f"  Password: {TEST_PASSWORD}")
print(f"  Customer ID: {TEST_CUSTOMER_ID}")

with engine.connect() as conn:
    # Step 1: Check if user already exists
    print("\n" + "=" * 70)
    print("STEP 1: Checking for existing user")
    print("=" * 70)
    
    existing = conn.execute(text("""
        SELECT user_id, user_name, email, customer_id
        FROM users
        WHERE user_name = :username OR email = :email
    """), {"username": TEST_USERNAME, "email": TEST_EMAIL}).fetchone()
    
    if existing:
        print(f"\n⚠️  User already exists:")
        print(f"   User ID: {existing.user_id}")
        print(f"   Username: {existing.user_name}")
        print(f"   Email: {existing.email}")
        print(f"   Customer ID: {existing.customer_id}")
        
        # Auto-update existing user (non-interactive) - same hash method as login
        print("\n   Auto-updating existing user (password reset, active=1)...")
        conn.execute(text("""
            UPDATE users
            SET customer_id = :customer_id,
                password_hash = :password,
                active = 1
            WHERE user_id = :user_id
        """), {
            "customer_id": TEST_CUSTOMER_ID,
            "password": generate_password_hash(TEST_PASSWORD, method=HASH_METHOD),
            "user_id": existing.user_id
        })
        conn.commit()
        print("✅ User updated!")
        user_id = existing.user_id
    else:
        # Create new user
        print("\n✅ No existing user found. Creating new user...")
        
        result = conn.execute(text("""
            INSERT INTO users (user_name, email, customer_id, password_hash, active)
            VALUES (:username, :email, :customer_id, :password, 1)
            RETURNING user_id
        """), {
            "username": TEST_USERNAME,
            "email": TEST_EMAIL,
            "customer_id": TEST_CUSTOMER_ID,
            "password": generate_password_hash(TEST_PASSWORD, method=HASH_METHOD)
        })
        
        user_id = result.fetchone()[0]
        conn.commit()
        
        print(f"✅ User created! User ID: {user_id}")
    
    # Step 2: Update DC2_S accounts to use this customer_id
    print("\n" + "=" * 70)
    print("STEP 2: Linking DC2_S accounts to test user")
    print("=" * 70)
    
    # Check current DC2_S accounts
    dc2s_accounts = conn.execute(text("""
        SELECT account_id, account_name, customer_id, vertical
        FROM accounts
        WHERE vertical = 'dc2_s'
        ORDER BY account_id
    """)).fetchall()
    
    if dc2s_accounts:
        print(f"\nFound {len(dc2s_accounts)} DC2_S accounts:")
        for acc in dc2s_accounts:
            print(f"  {acc.account_id}: {acc.account_name} (currently customer_id: {acc.customer_id})")
        
        # Update them to use TEST_CUSTOMER_ID
        result = conn.execute(text("""
            UPDATE accounts
            SET customer_id = :customer_id
            WHERE vertical = 'dc2_s'
        """), {"customer_id": TEST_CUSTOMER_ID})
        
        conn.commit()
        print(f"\n✅ Updated {result.rowcount} DC2_S accounts to customer_id = {TEST_CUSTOMER_ID}")
    else:
        print("\n⚠️  No DC2_S accounts found! They may need to be created first.")
    
    # Step 3: Verify the setup
    print("\n" + "=" * 70)
    print("STEP 3: Verification")
    print("=" * 70)
    
    # Check user
    user = conn.execute(text("""
        SELECT user_id, user_name, email, customer_id
        FROM users
        WHERE user_id = :user_id
    """), {"user_id": user_id}).fetchone()
    
    print(f"\n✅ Test User:")
    print(f"   User ID: {user.user_id}")
    print(f"   Username: {user.user_name}")
    print(f"   Email: {user.email}")
    print(f"   Customer ID: {user.customer_id}")
    
    # Check accounts
    accounts = conn.execute(text("""
        SELECT account_id, account_name, revenue, industry
        FROM accounts
        WHERE customer_id = :customer_id AND vertical = 'dc2_s'
        ORDER BY account_id
    """), {"customer_id": TEST_CUSTOMER_ID}).fetchall()
    
    print(f"\n✅ DC2_S Accounts (visible to this user): {len(accounts)}")
    for acc in accounts:
        print(f"   {acc.account_id}: {acc.account_name} - ${acc.revenue}")
    
    # Check KPIs
    kpi_count = conn.execute(text("""
        SELECT COUNT(*)
        FROM dc2s_kpis k
        JOIN accounts a ON k.account_id = a.account_id
        WHERE a.customer_id = :customer_id
    """), {"customer_id": TEST_CUSTOMER_ID}).fetchone()[0]
    
    print(f"\n✅ DC2_S KPIs: {kpi_count} measurements")
    
    # Check signals
    signal_count = conn.execute(text("""
        SELECT COUNT(*)
        FROM qualitative_signals s
        JOIN accounts a ON s.account_id = a.account_id
        WHERE a.customer_id = :customer_id
    """), {"customer_id": TEST_CUSTOMER_ID}).fetchone()[0]
    
    print(f"✅ Qualitative Signals: {signal_count} interactions")

print("\n" + "=" * 70)
print("SETUP COMPLETE! 🎉")
print("=" * 70)

print(f"""
LOGIN CREDENTIALS:
==================
Username: {TEST_USERNAME}
Password: {TEST_PASSWORD}
Email: {TEST_EMAIL}

NEXT STEPS:
===========
1. Login to your UI with these credentials
2. You should now see all 10 DC2_S accounts (1001-1010)
3. These accounts have:
   - ✅ KPI data (132 measurements)
   - ✅ Qualitative signals (960 interactions) [if loaded]
   - ✅ Vector embeddings in Qdrant [if created]

4. You can now:
   - View accounts in UI
   - Test Signal Analyst from UI
   - Demo the complete system with rich data
   - Keep this separate from your production SaaS data

TESTING SIGNAL ANALYST:
=======================
From command line (works immediately):
  python3 signal_analyst_flexible.py 1007

From UI (after login):
  - Navigate to account 1007 (Legacy Manufacturing)
  - Click "Analyze" or "Get Insights"
  - See AI-powered recommendations

SECURITY NOTE:
==============
This is a TEST USER for demonstration purposes.
- Change the password to something secure
- Don't use in production
- Consider adding role/permissions if needed
""")

# Save credentials to file
credentials_file = os.path.join(os.path.dirname(__file__), "DC2S_TEST_USER_CREDENTIALS.txt")
with open(credentials_file, "w") as f:
    f.write("DC2_S TEST USER CREDENTIALS\n")
    f.write("=" * 50 + "\n\n")
    f.write(f"Username: {TEST_USERNAME}\n")
    f.write(f"Password: {TEST_PASSWORD}\n")
    f.write(f"Email: {TEST_EMAIL}\n")
    f.write(f"Customer ID: {TEST_CUSTOMER_ID}\n")
    f.write(f"\nLogin URL: http://localhost:5059/login\n")
    f.write(f"\nAccounts visible: DC2_S vertical accounts (370-381)\n")

print(f"\n✅ Credentials saved to: {credentials_file}")
