#!/usr/bin/env python3
"""
Simple test to verify the rollup function
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import KPI, Account
from corporate_api import get_corporate_rollup
from flask import request

def test_rollup_function():
    """Test the rollup function directly"""
    with app.app_context():
        # Mock request headers
        class MockRequest:
            def __init__(self):
                self.headers = {'X-Customer-ID': '6'}
        
        # Replace the request object
        import flask
        flask.request = MockRequest()
        
        # Call the function
        response = get_corporate_rollup()
        
        # Check the response
        data = response.get_json()
        print("Response keys:", list(data.keys()))
        print("Health scores present:", 'health_scores' in data)
        if 'health_scores' in data:
            print("Health scores:", data['health_scores'])

if __name__ == "__main__":
    test_rollup_function() 