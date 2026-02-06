File: verticals/customer108-DC2_S/scripts/02_load_customer108_data_SMART.py
Add/verify these deletions (in this order):
pythonfrom sqlalchemy import text

CUSTOMER_ID = 108

with engine.begin() as connection:
    print("Deleting existing data...")
    
    # Step 1: Delete deepest children first
    
    # Qualitative signals (FK: account_id)
    result = connection.execute(text("""
        DELETE FROM qualitative_signals 
        WHERE account_id IN (
            SELECT account_id FROM accounts WHERE customer_id = :cid
        )
    """), {"cid": CUSTOMER_ID})
    print(f"   ✅ Deleted {result.rowcount} qualitative signals")
    
    # Products (FK: customer_id OR account_id)
    result = connection.execute(text("""
        DELETE FROM products 
        WHERE customer_id = :cid 
           OR account_id IN (
               SELECT account_id FROM accounts WHERE customer_id = :cid
           )
    """), {"cid": CUSTOMER_ID})
    print(f"   ✅ Deleted {result.rowcount} products")
    
    # KPI measurements (FK: account_id, kpi_code)
    result = connection.execute(text("""
        DELETE FROM kpi_measurements 
        WHERE account_id IN (
            SELECT account_id FROM accounts WHERE customer_id = :cid
        )
    """), {"cid": CUSTOMER_ID})
    print(f"   ✅ Deleted {result.rowcount} kpi_measurements")
    
    # Account profiles (FK: account_id)
    result = connection.execute(text("""
        DELETE FROM account_profiles 
        WHERE account_id IN (
            SELECT account_id FROM accounts WHERE customer_id = :cid
        )
    """), {"cid": CUSTOMER_ID})
    print(f"   ✅ Deleted {result.rowcount} account_profiles")
    
    # Step 2: Delete parent (accounts)
    result = connection.execute(text("""
        DELETE FROM accounts WHERE customer_id = :cid
    """), {"cid": CUSTOMER_ID})
    print(f"   ✅ Deleted {result.rowcount} accounts")
