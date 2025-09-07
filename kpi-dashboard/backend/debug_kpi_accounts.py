#!/usr/bin/env python3

import requests
import json

def debug_kpi_accounts():
    """Debug script to check KPI account assignments"""
    base_url = "http://localhost:5054"
    headers = {"X-Customer-ID": "6", "X-User-ID": "1"}
    
    print("=== Debugging KPI Account Assignments ===\n")
    
    # 1. Check all accounts
    print("1. Checking all accounts...")
    response = requests.get(f"{base_url}/api/accounts", headers=headers)
    if response.status_code == 200:
        accounts = response.json()
        print(f"   Found {len(accounts)} accounts")
        for account in accounts[:5]:  # Show first 5
            print(f"   - {account['account_name']} (ID: {account['account_id']})")
    else:
        print(f"   Failed to get accounts: {response.status_code}")
    
    # 2. Check KPIs for a specific account
    print("\n2. Checking KPIs for account 16 (TechCorp Solutions)...")
    response = requests.get(f"{base_url}/api/accounts/16/kpis", headers=headers)
    if response.status_code == 200:
        kpis = response.json()
        print(f"   Found {len(kpis)} KPIs")
        if kpis:
            print(f"   First KPI: {kpis[0]}")
            # Check if account_id is in the response
            if 'account_id' in kpis[0]:
                print(f"   ✅ account_id is present: {kpis[0]['account_id']}")
            else:
                print(f"   ❌ account_id is missing from response")
    else:
        print(f"   Failed to get KPIs: {response.status_code}")
    
    # 3. Check uploads
    print("\n3. Checking uploads...")
    response = requests.get(f"{base_url}/api/uploads", headers=headers)
    if response.status_code == 200:
        uploads = response.json()
        print(f"   Found {len(uploads)} uploads")
        for upload in uploads[:3]:  # Show first 3
            print(f"   - {upload['original_filename']} (ID: {upload['upload_id']})")
    else:
        print(f"   Failed to get uploads: {response.status_code}")
    
    # 4. Test PATCH endpoint
    print("\n4. Testing PATCH endpoint...")
    test_data = {"account_id": 16}
    response = requests.patch(
        f"{base_url}/api/kpi/12163",
        headers={**headers, "Content-Type": "application/json"},
        json=test_data
    )
    if response.status_code == 200:
        print(f"   ✅ PATCH successful: {response.json()}")
    else:
        print(f"   ❌ PATCH failed: {response.status_code} - {response.text}")
    
    # 5. Check corporate rollup
    print("\n5. Checking corporate rollup...")
    response = requests.get(f"{base_url}/api/corporate/rollup", headers=headers)
    if response.status_code == 200:
        rollup = response.json()
        print(f"   Companies loaded: {rollup.get('companies_loaded', 0)}")
        print(f"   Total KPIs: {rollup.get('total_kpis', 0)}")
        print(f"   Rollup KPIs: {len(rollup.get('rollup_kpis', []))}")
    else:
        print(f"   Failed to get rollup: {response.status_code}")

if __name__ == "__main__":
    debug_kpi_accounts() 