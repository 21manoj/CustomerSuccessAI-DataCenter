#!/usr/bin/env python3
"""
Test score calculator with Customer 9 data
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_v3_minimal import app
from utils.score_calculator import calculate_customer_scores
from datetime import date

def test_score_calculator():
    with app.app_context():
        print("="*70)
        print("TESTING SCORE CALCULATOR - CUSTOMER 9")
        print("="*70)
        print()
        
        # Calculate scores for December 2024
        measurement_month = date(2024, 12, 1)
        
        print(f"Calculating scores for: {measurement_month.strftime('%B %Y')}")
        print()
        
        results = calculate_customer_scores(customer_id=9, measurement_month=measurement_month)
        
        print()
        print("="*70)
        print("RESULTS SUMMARY")
        print("="*70)
        print(f"Total accounts processed: {len(results)}")
        
        successful = [aid for aid, r in results.items() if r and 'error' not in r]
        failed = [aid for aid, r in results.items() if not r or 'error' in r]
        
        print(f"Successful: {len(successful)}")
        print(f"Failed: {len(failed)}")
        
        if successful:
            print()
            print("✅ Successful Accounts:")
            for account_id in successful[:5]:  # Show first 5
                result = results[account_id]
                if result and result.get('health_score'):
                    health = result['health_score']
                    print(f"  Account {account_id}: Health = {health['health_score']:.1f} ({health['health_status']})")
                    if health.get('trend'):
                        print(f"    Trend: {health['trend']}")
        
        if failed:
            print()
            print("❌ Failed Accounts:")
            for account_id in failed[:5]:  # Show first 5
                error = results[account_id].get('error', 'Unknown error') if results[account_id] else 'No result'
                print(f"  Account {account_id}: {error}")

if __name__ == '__main__':
    test_score_calculator()
