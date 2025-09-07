#!/usr/bin/env python3
"""
Simple script to upload corporate metadata and create companies.
"""

import requests
import json

def upload_corporate_simple():
    """Upload corporate metadata using existing API"""
    
    base_url = "http://localhost:5054"
    headers = {"X-Customer-ID": "6", "X-User-ID": "1"}
    
    print("🏢 Uploading Corporate Metadata")
    print("=" * 40)
    
    # Load corporate metadata
    with open("corporate_metadata.json", "r") as f:
        metadata = json.load(f)
    
    # Create companies via API
    print("\n1️⃣ Creating companies...")
    companies_created = []
    
    for company in metadata["companies"]:
        response = requests.post(
            f"{base_url}/api/accounts",
            headers={**headers, "Content-Type": "application/json"},
            json={
                "account_name": company["company_name"],
                "revenue": company["revenue"],
                "industry": company["industry"],
                "region": company["region"],
                "employee_count": company["employee_count"],
                "contract_value": company["contract_value"]
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            companies_created.append({
                "account_id": result["account_id"],
                "company_name": company["company_name"],
                "revenue": company["revenue"],
                "industry": company["industry"],
                "region": company["region"]
            })
            print(f"   ✅ Created: {company['company_name']} (ID: {result['account_id']})")
        else:
            print(f"   ❌ Failed to create {company['company_name']}: {response.status_code}")
    
    print(f"\n✅ Created {len(companies_created)} companies")
    print(f"   - Total Revenue: ${sum(c['revenue'] for c in companies_created):,}")
    print(f"   - Industries: {len(set(c['industry'] for c in companies_created))}")
    
    return companies_created

if __name__ == "__main__":
    upload_corporate_simple() 