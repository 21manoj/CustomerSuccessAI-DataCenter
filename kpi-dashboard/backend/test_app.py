#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app

def test_app():
    """Test if the Flask app is loading correctly"""
    print("=== Testing Flask App ===\n")
    
    print("1. Checking if app loads...")
    print(f"   App name: {app.name}")
    print(f"   App config: {app.config.get('ENV', 'Not set')}")
    
    print("\n2. Checking registered blueprints...")
    for name, blueprint in app.blueprints.items():
        print(f"   - {name}: {blueprint.name}")
        print(f"     URL prefix: {blueprint.url_prefix}")
    
    print("\n3. Checking all app routes...")
    for rule in app.url_map.iter_rules():
        if rule.endpoint.startswith('corporate_api'):
            print(f"   {rule.rule} -> {rule.endpoint}")
    
    print("\n4. Testing corporate_api specifically...")
    if 'corporate_api' in app.blueprints:
        corporate_bp = app.blueprints['corporate_api']
        print(f"   Corporate API blueprint found: {corporate_bp.name}")
    else:
        print("   Corporate API blueprint NOT found!")
    
    print("\n5. Testing with test client...")
    with app.test_client() as client:
        response = client.get('/api/corporate/test')
        print(f"   Test endpoint response: {response.status_code}")
        if response.status_code == 200:
            print(f"   Response data: {response.get_json()}")

if __name__ == "__main__":
    test_app() 