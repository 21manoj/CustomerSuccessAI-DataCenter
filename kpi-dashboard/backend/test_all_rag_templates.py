#!/usr/bin/env python3
"""
Comprehensive test script for all RAG query templates.
Tests each template query to ensure they return valid responses.
"""

import sys
import os
import requests
import json
from typing import Dict, List, Tuple

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Base URL for the backend
BASE_URL = "http://127.0.0.1:5059"

# All query templates from RAGAnalysis.tsx
QUERY_TEMPLATES = [
    # Revenue Analysis
    {
        'id': 'revenue-top-accounts',
        'category': 'Revenue Analysis',
        'title': 'Top Revenue Accounts',
        'query': 'Which accounts have the highest revenue?',
        'query_type': 'revenue_analysis'
    },
    {
        'id': 'revenue-total',
        'category': 'Revenue Analysis',
        'title': 'Total Revenue Overview',
        'query': 'What is the total revenue across all accounts?',
        'query_type': 'revenue_analysis'
    },
    {
        'id': 'revenue-growth',
        'category': 'Revenue Analysis',
        'title': 'Revenue Growth Analysis',
        'query': 'Show me revenue growth analysis and trends',
        'query_type': 'revenue_analysis'
    },
    {
        'id': 'revenue-industry',
        'category': 'Revenue Analysis',
        'title': 'Industry Revenue Breakdown',
        'query': 'How does revenue vary by industry?',
        'query_type': 'revenue_analysis'
    },
    
    # Account Health & Performance
    {
        'id': 'account-health',
        'category': 'Account Health',
        'title': 'Account Health Overview',
        'query': 'Show me account health scores and performance',
        'query_type': 'account_analysis'
    },
    {
        'id': 'account-risk',
        'category': 'Account Health',
        'title': 'At-Risk Accounts',
        'query': 'Which accounts are at risk of churn?',
        'query_type': 'account_analysis'
    },
    {
        'id': 'account-performance',
        'category': 'Account Health',
        'title': 'Account Performance Ranking',
        'query': 'Which accounts are performing best?',
        'query_type': 'account_analysis'
    },
    {
        'id': 'account-engagement',
        'category': 'Account Health',
        'title': 'Account Engagement Analysis',
        'query': 'Show me account engagement analysis',
        'query_type': 'account_analysis'
    },
    
    # KPI Performance
    {
        'id': 'kpi-top-performing',
        'category': 'KPI Performance',
        'title': 'Top Performing KPIs',
        'query': 'What are the top performing KPIs?',
        'query_type': 'kpi_analysis'
    },
    {
        'id': 'kpi-customer-satisfaction',
        'category': 'KPI Performance',
        'title': 'Customer Satisfaction Analysis',
        'query': 'Show me customer satisfaction analysis',
        'query_type': 'kpi_analysis'
    },
    {
        'id': 'kpi-categories',
        'category': 'KPI Performance',
        'title': 'KPI Category Performance',
        'query': 'How are different KPI categories performing?',
        'query_type': 'kpi_analysis'
    },
    {
        'id': 'kpi-trends',
        'category': 'KPI Performance',
        'title': 'KPI Trends & Patterns',
        'query': 'What are the key trends in our KPI performance?',
        'query_type': 'kpi_analysis'
    },
    
    # Industry & Regional Analysis
    {
        'id': 'industry-analysis',
        'category': 'Industry Analysis',
        'title': 'Industry Performance',
        'query': 'How do we perform across different industries?',
        'query_type': 'general'
    },
    {
        'id': 'regional-analysis',
        'category': 'Regional Analysis',
        'title': 'Regional Performance',
        'query': 'Show me regional performance analysis',
        'query_type': 'general'
    },
    
    # Historical Trend Analysis
    {
        'id': 'historical-trends',
        'category': 'Historical Analysis',
        'title': 'Overall Trend Analysis',
        'query': 'Show me trends across all KPIs and accounts over time',
        'query_type': 'trend_analysis'
    },
    {
        'id': 'kpi-trends-historical',
        'category': 'Historical Analysis',
        'title': 'KPI Trend Analysis',
        'query': 'Show me historical trends in Time to First Value over time',
        'query_type': 'trend_analysis'
    },
    {
        'id': 'account-trends-historical',
        'category': 'Historical Analysis',
        'title': 'Account Performance Trends',
        'query': 'Show me how account performance has changed over time',
        'query_type': 'trend_analysis'
    },
    {
        'id': 'health-evolution',
        'category': 'Historical Analysis',
        'title': 'Health Score Evolution',
        'query': 'How have health scores evolved over time?',
        'query_type': 'trend_analysis'
    },
    {
        'id': 'temporal-patterns',
        'category': 'Historical Analysis',
        'title': 'Temporal Patterns',
        'query': 'What temporal patterns and seasonality do you see in the data?',
        'query_type': 'temporal_analysis'
    },
    {
        'id': 'predictive-insights',
        'category': 'Historical Analysis',
        'title': 'Predictive Insights',
        'query': 'What predictions can you make based on historical trends?',
        'query_type': 'trend_analysis'
    },
    
    # Monthly Revenue Analysis
    {
        'id': 'monthly-revenue',
        'category': 'Monthly Revenue Analysis',
        'title': 'Monthly Revenue Breakdown',
        'query': 'Which accounts have the highest revenue across last 4 months? please provide month details as well?',
        'query_type': 'revenue_analysis'
    },
    {
        'id': 'revenue-trends',
        'category': 'Monthly Revenue Analysis',
        'title': 'Revenue Trends & Patterns',
        'query': 'Analyze revenue trends and patterns over the last 6 months',
        'query_type': 'trend_analysis'
    },
    {
        'id': 'top-accounts-monthly',
        'category': 'Monthly Revenue Analysis',
        'title': 'Top Accounts by Month',
        'query': 'Which accounts performed best each month? Show monthly rankings',
        'query_type': 'account_analysis'
    },
    
    # Strategic Insights
    {
        'id': 'strategic-insights',
        'category': 'Strategic Insights',
        'title': 'Strategic Recommendations',
        'query': 'What strategic recommendations do you have for improving our business?',
        'query_type': 'general'
    },
    {
        'id': 'growth-opportunities',
        'category': 'Strategic Insights',
        'title': 'Growth Opportunities',
        'query': 'What growth opportunities do you see in our data?',
        'query_type': 'general'
    },
    
    # Multi-Product Queries (added based on recent work)
    {
        'id': 'multi-product-accounts',
        'category': 'Product Analysis',
        'title': 'Multi-Product Accounts',
        'query': 'Which accounts use more than 1 product?',
        'query_type': 'account_analysis'
    }
]

def login(session: requests.Session) -> Tuple[bool, int]:
    """Login and return (success, customer_id)"""
    login_data = {
        'email': 'admin@example.com',
        'password': 'admin123'
    }
    
    try:
        response = session.post(
            f"{BASE_URL}/api/login",
            json=login_data,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            data = response.json()
            customer_id = data.get('customer_id', 1)
            print(f"✅ Login successful (customer_id: {customer_id})")
            return True, customer_id
        else:
            print(f"❌ Login failed: {response.status_code} - {response.text}")
            return False, 0
    except Exception as e:
        print(f"❌ Login error: {e}")
        return False, 0

def check_knowledge_base(session: requests.Session, customer_id: int) -> bool:
    """Check if knowledge base is built"""
    try:
        response = session.get(
            f"{BASE_URL}/api/direct-rag/status",
            headers={
                'X-Customer-ID': str(customer_id),
                'Content-Type': 'application/json'
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            is_built = data.get('is_built', False)
            if is_built:
                print(f"✅ Knowledge base is built")
            else:
                print(f"⚠️  Knowledge base is NOT built")
            return is_built
        else:
            print(f"⚠️  Could not check knowledge base status: {response.status_code}")
            return False
    except Exception as e:
        print(f"⚠️  Error checking knowledge base: {e}")
        return False

def build_knowledge_base(session: requests.Session, customer_id: int) -> bool:
    """Build the knowledge base - Note: direct-rag doesn't require building"""
    print("\n⚠️  Note: direct-rag API doesn't require building (it builds on-the-fly)")
    return True

def test_query(session: requests.Session, customer_id: int, template: Dict) -> Tuple[bool, str]:
    """Test a single query template"""
    query = template['query']
    query_type = template.get('query_type', 'general')
    
    try:
        response = session.post(
            f"{BASE_URL}/api/direct-rag/query",
            json={
                'query': query,
                'query_type': query_type,
                'conversation_history': []
            },
            headers={
                'X-Customer-ID': str(customer_id),
                'Content-Type': 'application/json'
            },
            timeout=30  # 30 second timeout
        )
        
        if response.status_code != 200:
            return False, f"HTTP {response.status_code}: {response.text[:200]}"
        
        data = response.json()
        
        # Check for errors
        if 'error' in data:
            return False, f"Error: {data['error']}"
        
        # Check for answer/response
        answer = data.get('answer') or data.get('response', '')
        if not answer or answer.strip() == '':
            return False, "Empty response"
        
        # Check if response is too short (might indicate a problem)
        if len(answer.strip()) < 20:
            return False, f"Response too short: '{answer[:50]}'"
        
        # Check for common error patterns
        error_patterns = [
            "i don't have",
            "i cannot",
            "i'm unable",
            "no data available",
            "no information",
            "not available"
        ]
        answer_lower = answer.lower()
        if any(pattern in answer_lower for pattern in error_patterns):
            # This might be a valid response, but log it
            return True, f"⚠️  Response may indicate missing data: {answer[:100]}"
        
        return True, answer[:200] + "..." if len(answer) > 200 else answer
        
    except requests.exceptions.Timeout:
        return False, "Request timeout (30s)"
    except Exception as e:
        return False, f"Exception: {str(e)}"

def main():
    """Run all template tests"""
    print("=" * 80)
    print("RAG QUERY TEMPLATES TEST SUITE")
    print("=" * 80)
    
    # Create session for cookie persistence
    session = requests.Session()
    
    # Login
    print("\n[1/4] Logging in...")
    success, customer_id = login(session)
    if not success:
        print("❌ Cannot proceed without login")
        return 1
    
    # Check knowledge base
    print("\n[2/4] Checking knowledge base status...")
    is_built = check_knowledge_base(session, customer_id)
    
    if not is_built:
        print("\n[2.5/4] Building knowledge base...")
        if not build_knowledge_base(session, customer_id):
            print("❌ Cannot proceed without knowledge base")
            return 1
    
    # Test all templates
    print("\n[3/4] Testing all query templates...")
    print("=" * 80)
    
    results = {
        'passed': [],
        'failed': [],
        'warnings': []
    }
    
    for i, template in enumerate(QUERY_TEMPLATES, 1):
        print(f"\n[{i}/{len(QUERY_TEMPLATES)}] Testing: {template['title']}")
        print(f"   Category: {template['category']}")
        print(f"   Query: {template['query']}")
        
        success, message = test_query(session, customer_id, template)
        
        if success:
            if "⚠️" in message:
                results['warnings'].append((template, message))
                print(f"   ⚠️  WARNING: {message}")
            else:
                results['passed'].append((template, message))
                print(f"   ✅ PASSED: {message}")
        else:
            results['failed'].append((template, message))
            print(f"   ❌ FAILED: {message}")
    
    # Summary
    print("\n" + "=" * 80)
    print("[4/4] TEST SUMMARY")
    print("=" * 80)
    print(f"\n✅ Passed: {len(results['passed'])}/{len(QUERY_TEMPLATES)}")
    print(f"⚠️  Warnings: {len(results['warnings'])}/{len(QUERY_TEMPLATES)}")
    print(f"❌ Failed: {len(results['failed'])}/{len(QUERY_TEMPLATES)}")
    
    if results['failed']:
        print("\n❌ FAILED QUERIES:")
        for template, error in results['failed']:
            print(f"   - {template['title']} ({template['category']})")
            print(f"     Query: {template['query']}")
            print(f"     Error: {error}\n")
    
    if results['warnings']:
        print("\n⚠️  QUERIES WITH WARNINGS:")
        for template, warning in results['warnings']:
            print(f"   - {template['title']} ({template['category']})")
            print(f"     Query: {template['query']}")
            print(f"     Warning: {warning}\n")
    
    # Return exit code
    if results['failed']:
        return 1
    elif results['warnings']:
        return 0  # Warnings are acceptable
    else:
        return 0

if __name__ == '__main__':
    sys.exit(main())

