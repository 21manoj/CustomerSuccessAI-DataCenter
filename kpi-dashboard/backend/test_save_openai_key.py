#!/usr/bin/env python3
"""
Test saving OpenAI API key via the API endpoint
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask
from extensions import db
from models import CustomerConfig, Customer
from openai_key_utils import set_openai_api_key, get_openai_api_key, has_openai_api_key

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'instance', 'kpi_dashboard.db')

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

def test_save_key(customer_id=1, test_key="sk-test-key-12345"):
    """Test saving an OpenAI API key"""
    print("\n" + "="*70)
    print("TEST: Saving OpenAI API Key")
    print("="*70)
    
    with app.app_context():
        # Get customer
        customer = Customer.query.filter_by(customer_id=customer_id).first()
        if not customer:
            print(f"❌ Customer ID {customer_id} not found!")
            return False
        
        print(f"\n✅ Customer: {customer.customer_name} (ID: {customer_id})")
        
        # Check before
        print("\n📋 Before save:")
        had_key_before = has_openai_api_key(customer_id)
        print(f"   Has key: {had_key_before}")
        
        # Try to save
        print(f"\n💾 Saving test key...")
        try:
            success = set_openai_api_key(customer_id, test_key)
            if success:
                print("   ✅ Save returned True")
            else:
                print("   ❌ Save returned False")
                return False
        except Exception as e:
            print(f"   ❌ Save failed with exception: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # Check after
        print("\n📋 After save:")
        has_key_after = has_openai_api_key(customer_id)
        print(f"   Has key: {has_key_after}")
        
        if not has_key_after:
            print("   ❌ Key still not found after save!")
            return False
        
        # Try to retrieve
        print("\n🔑 Retrieving key...")
        try:
            retrieved_key = get_openai_api_key(customer_id)
            if retrieved_key:
                print(f"   ✅ Key retrieved: {retrieved_key[:20]}...")
                if retrieved_key == test_key:
                    print("   ✅ Retrieved key matches saved key!")
                else:
                    print(f"   ⚠️  Retrieved key does NOT match! Expected: {test_key[:20]}..., Got: {retrieved_key[:20]}...")
            else:
                print("   ❌ Failed to retrieve key")
                return False
        except Exception as e:
            print(f"   ❌ Retrieval failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        return True

if __name__ == "__main__":
    customer_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    success = test_save_key(customer_id)
    
    print("\n" + "="*70)
    if success:
        print("✅ TEST PASSED - Key save/retrieve works correctly!")
    else:
        print("❌ TEST FAILED - Check errors above")
    print("="*70 + "\n")
    
    sys.exit(0 if success else 1)

