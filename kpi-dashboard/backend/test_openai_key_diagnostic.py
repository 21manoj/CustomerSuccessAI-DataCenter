#!/usr/bin/env python3
"""
Diagnostic script to test OpenAI API key stored in database
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask
from extensions import db
from models import CustomerConfig, Customer
from openai_key_utils import get_openai_api_key, has_openai_api_key
from security_utils import decrypt_credential
import openai

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'instance', 'kpi_dashboard.db')

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

def test_openai_key(customer_id=1):
    """Test OpenAI API key for a customer"""
    print("\n" + "="*70)
    print("OPENAI API KEY DIAGNOSTIC TEST")
    print("="*70)
    
    with app.app_context():
        # Get customer info
        customer = Customer.query.filter_by(customer_id=customer_id).first()
        if not customer:
            print(f"❌ Customer ID {customer_id} not found!")
            return False
        
        print(f"\n✅ Customer: {customer.customer_name} (ID: {customer_id})")
        
        # Check if key exists
        print("\n📋 Step 1: Checking if key exists in database...")
        has_key = has_openai_api_key(customer_id)
        print(f"   Has key: {has_key}")
        
        if not has_key:
            print("❌ No API key found in database!")
            return False
        
        # Get config
        config = CustomerConfig.query.filter_by(customer_id=customer_id).first()
        if not config:
            print("❌ CustomerConfig not found!")
            return False
        
        print(f"   Config exists: ✅")
        print(f"   Encrypted key exists: {bool(config.openai_api_key_encrypted)}")
        if config.openai_api_key_updated_at:
            print(f"   Key updated at: {config.openai_api_key_updated_at}")
        
        # Try to decrypt
        print("\n🔓 Step 2: Testing decryption...")
        try:
            if config.openai_api_key_encrypted:
                decrypted_key = decrypt_credential(config.openai_api_key_encrypted)
                if decrypted_key:
                    print(f"   ✅ Decryption successful")
                    print(f"   Key preview: {decrypted_key[:20]}...{decrypted_key[-10:]}")
                    print(f"   Key length: {len(decrypted_key)} characters")
                    print(f"   Key format: {'✅ Valid (starts with sk-)' if decrypted_key.startswith('sk-') else '❌ Invalid format'}")
                else:
                    print("   ❌ Decryption returned None/empty")
                    return False
            else:
                print("   ❌ No encrypted key in database")
                return False
        except Exception as e:
            print(f"   ❌ Decryption failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # Test using get_openai_api_key utility
        print("\n🔑 Step 3: Testing get_openai_api_key() utility...")
        try:
            retrieved_key = get_openai_api_key(customer_id)
            if retrieved_key:
                print(f"   ✅ Key retrieved successfully")
                print(f"   Key preview: {retrieved_key[:20]}...{retrieved_key[-10:]}")
                if retrieved_key == decrypted_key:
                    print("   ✅ Retrieved key matches decrypted key")
                else:
                    print("   ⚠️  Retrieved key does NOT match decrypted key!")
            else:
                print("   ❌ get_openai_api_key() returned None")
                return False
        except Exception as e:
            print(f"   ❌ Failed to retrieve key: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # Test OpenAI API call
        print("\n🌐 Step 4: Testing OpenAI API call...")
        try:
            client = openai.OpenAI(api_key=retrieved_key)
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "user", "content": "Say 'API key test successful' if you can read this."}
                ],
                max_tokens=20
            )
            result = response.choices[0].message.content
            print(f"   ✅ OpenAI API call successful!")
            print(f"   Response: {result}")
            return True
        except openai.AuthenticationError as e:
            print(f"   ❌ Authentication failed: {e}")
            print(f"   This means the API key is invalid or expired.")
            return False
        except openai.APIError as e:
            print(f"   ❌ OpenAI API error: {e}")
            return False
        except Exception as e:
            print(f"   ❌ Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    customer_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    success = test_openai_key(customer_id)
    
    print("\n" + "="*70)
    if success:
        print("✅ ALL TESTS PASSED - OpenAI API key is working correctly!")
    else:
        print("❌ TESTS FAILED - Check the errors above")
    print("="*70 + "\n")
    
    sys.exit(0 if success else 1)

