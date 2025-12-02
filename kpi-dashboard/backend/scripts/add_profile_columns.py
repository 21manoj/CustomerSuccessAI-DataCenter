#!/usr/bin/env python3
"""
Add external_account_id and profile_metadata columns to accounts table.
"""

import os
import sys
import sqlite3

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app_v3_minimal import app

def add_profile_columns():
    """Add external_account_id and profile_metadata columns if they don't exist."""
    db_path = app.config.get('SQLALCHEMY_DATABASE_URI', '').replace('sqlite:///', '')
    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if columns exist
        cursor.execute("PRAGMA table_info(accounts)")
        columns = {row[1]: row for row in cursor.fetchall()}
        
        if 'external_account_id' not in columns:
            print("➕ Adding external_account_id column...")
            cursor.execute("ALTER TABLE accounts ADD COLUMN external_account_id VARCHAR(255)")
            print("   ✅ Added external_account_id")
        else:
            print("   ✅ external_account_id already exists")
        
        if 'profile_metadata' not in columns:
            print("➕ Adding profile_metadata column...")
            cursor.execute("ALTER TABLE accounts ADD COLUMN profile_metadata TEXT")
            print("   ✅ Added profile_metadata")
        else:
            print("   ✅ profile_metadata already exists")
        
        # Create index
        try:
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_accounts_customer_external_id ON accounts(customer_id, external_account_id)")
            print("   ✅ Index created/verified")
        except Exception as e:
            print(f"   ⚠️  Index creation: {e}")
        
        conn.commit()
        print("\n✅ Database schema updated successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    with app.app_context():
        add_profile_columns()


