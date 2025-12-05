#!/usr/bin/env python3
"""Check if profile_metadata is being returned by the accounts API."""

import os
import sys
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app_v3_minimal import app
from extensions import db
from models import Account, Customer

def check_profile_in_api():
    """Check profile data in accounts."""
    with app.app_context():
        customer = Customer.query.filter_by(customer_name='Test Company').first()
        if not customer:
            print("❌ Customer not found")
            return
        
        customer_id = customer.customer_id
        accounts = Account.query.filter_by(customer_id=customer_id).limit(3).all()
        
        print(f"📊 Checking {len(accounts)} sample accounts:\n")
        
        for acc in accounts:
            print(f"Account: {acc.account_name} (ID: {acc.account_id})")
            print(f"  external_account_id: {acc.external_account_id}")
            print(f"  profile_metadata type: {type(acc.profile_metadata)}")
            print(f"  profile_metadata: {json.dumps(acc.profile_metadata, indent=2) if acc.profile_metadata else 'None'}")
            
            # Check what the API would return
            profile_metadata = acc.profile_metadata or {}
            engagement = profile_metadata.get('engagement', {})
            champions = profile_metadata.get('champions', [])
            primary_champion = champions[0] if champions else {}
            
            print(f"\n  Extracted fields:")
            print(f"    account_tier: {profile_metadata.get('account_tier', '')}")
            print(f"    assigned_csm: {profile_metadata.get('assigned_csm', '')}")
            print(f"    csm_manager: {profile_metadata.get('csm_manager', '')}")
            print(f"    products_used: {profile_metadata.get('products_used', '')}")
            print(f"    lifecycle_stage: {engagement.get('lifecycle_stage', '')}")
            print(f"    primary_champion: {primary_champion.get('primary_champion_name', '')}")
            print("\n" + "-" * 60 + "\n")


if __name__ == '__main__':
    check_profile_in_api()









