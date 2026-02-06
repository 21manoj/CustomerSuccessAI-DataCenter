#!/usr/bin/env python3
"""
Run Wizard A for Customer 56 to generate journey data for all accounts
"""
import sys
import os
from pathlib import Path

# Add paths
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'verticals', 'customer56-dc2_s', 'journey', 'wizard_a'))

from app_v3_minimal import app
from models import Account

def run_wizard_a_for_customer56():
    """Run Wizard A to generate journey data for Customer 56 accounts"""
    
    with app.app_context():
        customer_id = 56
        
        # Get all accounts for Customer 56
        accounts = Account.query.filter_by(customer_id=customer_id).all()
        
        if not accounts:
            print(f"❌ No accounts found for customer {customer_id}")
            return
        
        print(f"✅ Found {len(accounts)} accounts for customer {customer_id}")
        print(f"   Account IDs: {[a.account_id for a in accounts]}")
        
        # Import Wizard A generator
        try:
            from wizard_journey_generator import generate_accounts_batch
        except ImportError as e:
            print(f"❌ Error importing wizard_journey_generator: {e}")
            print(f"   Make sure Wizard A files exist in verticals/customer56-dc2_s/journey/wizard_a/")
            return
        
        # Set up output directory
        customer_dir = Path(__file__).parent / "verticals" / "customer56-dc2_s" / "journey" / "data"
        customer_dir.mkdir(parents=True, exist_ok=True)
        
        # Pattern mix for journey generation
        pattern_mix = {
            'crisis': 0.20,
            'churn': 0.15,
            'stable': 0.40,
            'expansion': 0.25
        }
        
        # Start ID is the first account ID
        start_id = accounts[0].account_id
        num_accounts = len(accounts)
        
        print(f"\n🚀 Running Wizard A for Customer {customer_id}")
        print(f"   Accounts: {num_accounts}")
        print(f"   Start ID: {start_id}")
        print(f"   Pattern Mix: {pattern_mix}")
        print(f"   Output: {customer_dir}")
        print()
        
        # Generate journey data
        try:
            generated_journeys = generate_accounts_batch(
                num_accounts=num_accounts,
                pattern_mix=pattern_mix,
                start_id=start_id,
                output_dir=str(customer_dir),
                progress_callback=lambda current, total: print(f"   Progress: {current}/{total} ({current*100//total}%)")
            )
            
            print(f"\n✅ Wizard A completed successfully!")
            print(f"   Generated {len(generated_journeys)} journey files")
            print(f"   Files saved to: {customer_dir}")
            print(f"\n📋 Next steps:")
            print(f"   1. Journey JSON files are in: {customer_dir}")
            print(f"   2. You can now view journeys in the portal")
            print(f"   3. Journey API will serve these files at /api/journey/<account_id>")
            
        except Exception as e:
            print(f"\n❌ Error running Wizard A: {e}")
            import traceback
            traceback.print_exc()
            return

if __name__ == '__main__':
    run_wizard_a_for_customer56()
