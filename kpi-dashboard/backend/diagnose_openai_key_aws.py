#!/usr/bin/env python3
"""
Diagnose OpenAI API key issue on AWS
Check if key is saved, encryption working, etc.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask
from extensions import db
from models import CustomerConfig, Customer
from openai_key_utils import get_openai_api_key, has_openai_api_key
from security_utils import decrypt_credential

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'instance', 'kpi_dashboard.db')

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

def diagnose(customer_id=1):
    """Diagnose OpenAI API key issues"""
    print("\n" + "="*70)
    print("OPENAI API KEY DIAGNOSIS")
    print("="*70)
    
    with app.app_context():
        # Check customer
        customer = Customer.query.filter_by(customer_id=customer_id).first()
        if not customer:
            print(f"❌ Customer ID {customer_id} not found!")
            return
        
        print(f"\n✅ Customer: {customer.customer_name} (ID: {customer_id})")
        
        # Check ENCRYPTION_KEY environment variable
        print("\n🔐 Step 1: Checking ENCRYPTION_KEY environment variable...")
        encryption_key = os.getenv('ENCRYPTION_KEY')
        if encryption_key:
            print(f"   ✅ ENCRYPTION_KEY is set (length: {len(encryption_key)})")
        else:
            print("   ❌ ENCRYPTION_KEY is NOT set!")
            print("   💡 This is the problem! The backend needs ENCRYPTION_KEY to encrypt/decrypt keys.")
            return
        
        # Check CustomerConfig
        print("\n📋 Step 2: Checking CustomerConfig...")
        config = CustomerConfig.query.filter_by(customer_id=customer_id).first()
        if not config:
            print("   ❌ CustomerConfig does not exist!")
            print("   💡 This will be created when you save the key.")
        else:
            print("   ✅ CustomerConfig exists")
            print(f"   Has encrypted key: {bool(config.openai_api_key_encrypted)}")
            if config.openai_api_key_encrypted:
                print(f"   Encrypted key length: {len(config.openai_api_key_encrypted)}")
                print(f"   Key updated at: {config.openai_api_key_updated_at}")
                
                # Try to decrypt
                print("\n🔓 Step 3: Testing decryption...")
                try:
                    decrypted = decrypt_credential(config.openai_api_key_encrypted)
                    if decrypted:
                        print(f"   ✅ Decryption successful!")
                        print(f"   Key preview: {decrypted[:20]}...{decrypted[-10:]}")
                        print(f"   Key format: {'✅ Valid (starts with sk-)' if decrypted.startswith('sk-') else '❌ Invalid format'}")
                    else:
                        print("   ❌ Decryption returned None/empty")
                except Exception as e:
                    print(f"   ❌ Decryption failed: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print("   ⚠️  No encrypted key stored")
        
        # Test has_openai_api_key
        print("\n🔍 Step 4: Testing has_openai_api_key()...")
        has_key = has_openai_api_key(customer_id)
        print(f"   Result: {has_key}")
        
        # Test get_openai_api_key
        print("\n🔑 Step 5: Testing get_openai_api_key()...")
        try:
            retrieved_key = get_openai_api_key(customer_id)
            if retrieved_key:
                print(f"   ✅ Key retrieved successfully")
                print(f"   Key preview: {retrieved_key[:20]}...{retrieved_key[-10:]}")
            else:
                print("   ❌ get_openai_api_key() returned None")
                print("   💡 This means the key is not configured or cannot be retrieved")
        except Exception as e:
            print(f"   ❌ get_openai_api_key() failed: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n" + "="*70)
        print("DIAGNOSIS COMPLETE")
        print("="*70)

if __name__ == "__main__":
    customer_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    diagnose(customer_id)

