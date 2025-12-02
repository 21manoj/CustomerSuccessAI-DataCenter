#!/usr/bin/env python3
"""
Restore Database from Backup

This script restores the database from a backup file, ensuring:
1. All customer data is preserved
2. User-customer relationships are correct
3. Accounts and KPIs are properly linked
4. No data loss occurs
"""

import os
import sys
import shutil
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKUP_PATH = os.path.join(os.path.dirname(BASE_DIR), 'instance', 'kpi_dashboard.db.v4backup')
CURRENT_DB = os.path.join(BASE_DIR, 'instance', 'kpi_dashboard.db')
BACKUP_CURRENT = os.path.join(BASE_DIR, 'instance', f'kpi_dashboard.db.backup.{int(datetime.now().timestamp())}')

def main():
    print("\n" + "="*70)
    print("DATABASE RESTORATION FROM BACKUP")
    print("="*70)
    
    # Check if backup exists
    if not os.path.exists(BACKUP_PATH):
        print(f"\n❌ Backup file not found: {BACKUP_PATH}")
        print("\nAvailable backups:")
        for root, dirs, files in os.walk(os.path.dirname(BASE_DIR)):
            for file in files:
                if 'backup' in file.lower() or 'v4backup' in file.lower():
                    print(f"  - {os.path.join(root, file)}")
        return False
    
    # Backup current database first
    if os.path.exists(CURRENT_DB):
        print(f"\n📦 Backing up current database...")
        shutil.copy2(CURRENT_DB, BACKUP_CURRENT)
        print(f"   ✅ Current DB backed up to: {BACKUP_CURRENT}")
    
    # Restore from backup
    print(f"\n🔄 Restoring from backup: {BACKUP_PATH}")
    try:
        shutil.copy2(BACKUP_PATH, CURRENT_DB)
        print(f"   ✅ Database restored successfully!")
        
        # Verify restoration
        import sqlite3
        conn = sqlite3.connect(CURRENT_DB)
        cursor = conn.cursor()
        
        # Check customers
        cursor.execute("SELECT COUNT(*) FROM customers")
        customer_count = cursor.fetchone()[0]
        print(f"\n📊 Verification:")
        print(f"   Customers: {customer_count}")
        
        # Check users
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        print(f"   Users: {user_count}")
        
        # Check accounts
        cursor.execute("SELECT COUNT(*) FROM accounts")
        account_count = cursor.fetchone()[0]
        print(f"   Accounts: {account_count}")
        
        # Check KPIs
        cursor.execute("SELECT COUNT(*) FROM kpis")
        kpi_count = cursor.fetchone()[0]
        print(f"   KPIs: {kpi_count}")
        
        # Check customer-account distribution
        cursor.execute("""
            SELECT c.customer_id, c.customer_name, COUNT(a.account_id) as account_count
            FROM customers c
            LEFT JOIN accounts a ON c.customer_id = a.customer_id
            GROUP BY c.customer_id, c.customer_name
            ORDER BY c.customer_id
        """)
        print(f"\n📋 Customer-Account Distribution:")
        for row in cursor.fetchall():
            print(f"   Customer {row[0]} ({row[1]}): {row[2]} accounts")
        
        # Check user-customer relationships
        cursor.execute("""
            SELECT u.user_id, u.email, u.customer_id, c.customer_name
            FROM users u
            LEFT JOIN customers c ON u.customer_id = c.customer_id
            ORDER BY u.user_id
        """)
        print(f"\n👥 User-Customer Relationships:")
        for row in cursor.fetchall():
            print(f"   User {row[0]} ({row[1]}): Customer {row[2]} ({row[3]})")
        
        conn.close()
        
        print(f"\n✅ Database restoration complete!")
        print(f"\n⚠️  IMPORTANT: Restart your Flask server to use the restored database.")
        print(f"   Current DB location: {CURRENT_DB}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error during restoration: {e}")
        # Restore from backup if restoration failed
        if os.path.exists(BACKUP_CURRENT):
            print(f"\n🔄 Restoring original database from backup...")
            shutil.copy2(BACKUP_CURRENT, CURRENT_DB)
            print(f"   ✅ Original database restored")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

