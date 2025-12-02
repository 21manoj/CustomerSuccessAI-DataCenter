#!/usr/bin/env python3
"""Test RAG query for multi-product accounts"""

import requests
import json

BASE_URL = "http://localhost:5059"

def login():
    """Login and get session"""
    session = requests.Session()
    response = session.post(
        f"{BASE_URL}/api/login",
        json={"email": "admin@example.com", "password": "admin123"},
        headers={"Content-Type": "application/json"}
    )
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code}")
        return None, None
    
    data = response.json()
    customer_id = data.get('user', {}).get('customer_id')
    print(f"✅ Logged in as: {data.get('user', {}).get('email')}")
    print(f"   Customer ID: {customer_id}")
    return session, customer_id

def test_product_query(session, customer_id):
    """Test RAG query about multi-product accounts"""
    query = "which accounts use more than 1 product?"
    
    print(f"\n{'='*70}")
    print(f"Testing RAG Query: {query}")
    print(f"{'='*70}\n")
    
    response = session.post(
        f"{BASE_URL}/api/direct-rag/query",
        json={
            "query": query,
            "query_type": "general",
            "conversation_history": []
        },
        headers={
            "X-Customer-ID": str(customer_id),
            "Content-Type": "application/json"
        },
        timeout=30
    )
    
    if response.status_code == 200:
        data = response.json()
        answer = data.get('answer', 'No answer')
        print(f"✅ Response received:")
        print(f"\n{answer}\n")
        return True
    else:
        print(f"❌ Query failed: {response.status_code}")
        print(response.text[:500])
        return False

if __name__ == "__main__":
    session, customer_id = login()
    if session:
        test_product_query(session, customer_id)


