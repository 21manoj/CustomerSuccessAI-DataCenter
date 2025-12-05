#!/usr/bin/env python3
"""Verify customer profile data was imported correctly."""

import os
import sys
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app_v3_minimal import app
from extensions import db
from models import Account, Customer

def verify_profile_data():
    """Check imported profile data."""
    with app.app_context():
        customer = Customer.query.filter_by(customer_name='Test Company').first()
        if not customer:
            print("❌ Customer not found")
            return
        
        accounts = Account.query.filter_by(customer_id=customer.customer_id).all()
        print(f"\n📊 Profile Data Summary for Test Company ({len(accounts)} accounts):\n")
        
        # Count accounts with profile metadata
        with_profile = sum(1 for a in accounts if a.profile_metadata)
        with_external_id = sum(1 for a in accounts if a.external_account_id)
        
        print(f"✅ Accounts with profile_metadata: {with_profile}/{len(accounts)}")
        print(f"✅ Accounts with external_account_id: {with_external_id}/{len(accounts)}\n")
        
        # Show sample account details
        sample = None
        for acc in accounts:
            if acc.profile_metadata:
                sample = acc
                break
        
        if sample:
            print(f"📝 Sample Account: {sample.account_name}")
            print(f"   External ID: {sample.external_account_id}")
            if sample.profile_metadata:
                profile = sample.profile_metadata
                print(f"   Account Tier: {profile.get('account_tier', 'N/A')}")
                print(f"   Assigned CSM: {profile.get('assigned_csm', 'N/A')}")
                print(f"   Lifecycle Stage: {profile.get('engagement', {}).get('lifecycle_stage', 'N/A')}")
                print(f"   Onboarding Status: {profile.get('engagement', {}).get('onboarding_status', 'N/A')}")
                champions = profile.get('champions', [])
                if champions:
                    champ = champions[0]
                    print(f"   Primary Champion: {champ.get('primary_champion_name', 'N/A')}")
                print(f"   ARR: {profile.get('arr', 'N/A')}")
                print(f"   MRR: {profile.get('mrr', 'N/A')}")
        
        # Statistics
        tiers = {}
        csms = {}
        lifecycle_stages = {}
        
        for acc in accounts:
            if acc.profile_metadata:
                tier = acc.profile_metadata.get('account_tier', 'N/A')
                tiers[tier] = tiers.get(tier, 0) + 1
                
                csm = acc.profile_metadata.get('assigned_csm', 'N/A')
                csms[csm] = csms.get(csm, 0) + 1
                
                lifecycle = acc.profile_metadata.get('engagement', {}).get('lifecycle_stage', 'N/A')
                lifecycle_stages[lifecycle] = lifecycle_stages.get(lifecycle, 0) + 1
        
        print(f"\n📈 Distribution by Account Tier:")
        for tier, count in sorted(tiers.items()):
            print(f"   {tier}: {count}")
        
        print(f"\n👥 Distribution by CSM:")
        for csm, count in sorted(csms.items()):
            print(f"   {csm}: {count}")
        
        print(f"\n🔄 Distribution by Lifecycle Stage:")
        for stage, count in sorted(lifecycle_stages.items()):
            print(f"   {stage}: {count}")


if __name__ == '__main__':
    verify_profile_data()









