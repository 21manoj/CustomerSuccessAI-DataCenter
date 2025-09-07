#!/usr/bin/env python3
"""
Script to clean all data for customer 6 and start fresh.
"""

import requests
import json

def clean_data():
    """Clean all data for customer 6"""
    base_url = "http://localhost:5054"
    headers = {"X-Customer-ID": "6", "Content-Type": "application/json"}
    
    print("🧹 Cleaning all data for Customer 6...")
    
    # Get current status
    response = requests.get(f"{base_url}/api/data/status", headers=headers)
    if response.status_code == 200:
        status = response.json()
        print(f"📊 Current Status:")
        print(f"   - KPIs: {status['total_kpis']}")
        print(f"   - Uploads: {status['total_uploads']}")
        print(f"   - Accounts: {status['total_accounts']}")
    
    # Clear all data
    response = requests.post(f"{base_url}/api/data/clear", headers=headers)
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Data cleared successfully!")
        print(f"   - KPIs deleted: {result['deleted']['kpis']}")
        print(f"   - Uploads deleted: {result['deleted']['uploads']}")
        print(f"   - Accounts deleted: {result['deleted']['accounts']}")
        print(f"   - Config deleted: {result['deleted']['config']}")
    else:
        print(f"❌ Failed to clear data: {response.status_code}")
        return False
    
    # Verify cleanup
    response = requests.get(f"{base_url}/api/data/status", headers=headers)
    if response.status_code == 200:
        status = response.json()
        print(f"📊 After cleanup:")
        print(f"   - KPIs: {status['total_kpis']}")
        print(f"   - Uploads: {status['total_uploads']}")
        print(f"   - Accounts: {status['total_accounts']}")
        
        if status['total_kpis'] == 0 and status['total_uploads'] == 0 and status['total_accounts'] == 0:
            print("🎉 All data cleaned successfully!")
            return True
        else:
            print("⚠️  Some data still remains")
            return False
    else:
        print(f"❌ Failed to verify cleanup: {response.status_code}")
        return False

if __name__ == "__main__":
    clean_data() 