#!/usr/bin/env python3
"""
Comprehensive Test Suite - All RAG Query Templates for Qdrant Cloud
Tests ALL query templates from RAGAnalysis.tsx for both SaaS and DC customers
"""

import os
import sys
import requests
import time
from typing import Dict, List, Tuple
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BASE_URL = os.getenv('BACKEND_URL', 'http://localhost:8005')
SAAS_CUSTOMER_ID = 1
DC_CUSTOMER_ID = 5

# All query templates from test_all_rag_templates.py
ALL_QUERY_TEMPLATES = [
    # Revenue Analysis
    {'id': 'revenue-top-accounts', 'category': 'Revenue Analysis', 'title': 'Top Revenue Accounts',
     'query': 'Which accounts have the highest revenue?', 'query_type': 'revenue_analysis'},
    {'id': 'revenue-total', 'category': 'Revenue Analysis', 'title': 'Total Revenue Overview',
     'query': 'What is the total revenue across all accounts?', 'query_type': 'revenue_analysis'},
    {'id': 'revenue-growth', 'category': 'Revenue Analysis', 'title': 'Revenue Growth Analysis',
     'query': 'Show me revenue growth analysis and trends', 'query_type': 'revenue_analysis'},
    {'id': 'revenue-industry', 'category': 'Revenue Analysis', 'title': 'Industry Revenue Breakdown',
     'query': 'How does revenue vary by industry?', 'query_type': 'revenue_analysis'},
    
    # Account Health & Performance
    {'id': 'account-health', 'category': 'Account Health', 'title': 'Account Health Overview',
     'query': 'Show me account health scores and performance', 'query_type': 'account_analysis'},
    {'id': 'account-risk', 'category': 'Account Health', 'title': 'At-Risk Accounts',
     'query': 'Which accounts are at risk of churn?', 'query_type': 'account_analysis'},
    {'id': 'account-performance', 'category': 'Account Health', 'title': 'Account Performance Ranking',
     'query': 'Which accounts are performing best?', 'query_type': 'account_analysis'},
    {'id': 'account-engagement', 'category': 'Account Health', 'title': 'Account Engagement',
     'query': 'Show me account engagement metrics', 'query_type': 'account_analysis'},
    
    # KPI Performance
    {'id': 'kpi-top', 'category': 'KPI Performance', 'title': 'Top Performing KPIs',
     'query': 'What are the top performing KPIs?', 'query_type': 'kpi_analysis'},
    {'id': 'kpi-trends', 'category': 'KPI Performance', 'title': 'KPI Trends',
     'query': 'Show me KPI trends over time', 'query_type': 'kpi_analysis'},
    {'id': 'kpi-category', 'category': 'KPI Performance', 'title': 'KPI by Category',
     'query': 'Analyze KPI performance by category', 'query_type': 'kpi_analysis'},
    {'id': 'kpi-underperforming', 'category': 'KPI Performance', 'title': 'Underperforming KPIs',
     'query': 'Which KPIs are underperforming?', 'query_type': 'kpi_analysis'},
    
    # Trend Analysis
    {'id': 'trend-revenue', 'category': 'Trend Analysis', 'title': 'Revenue Trends',
     'query': 'Show me revenue trends over the last 6 months', 'query_type': 'trend_analysis'},
    {'id': 'trend-engagement', 'category': 'Trend Analysis', 'title': 'Engagement Trends',
     'query': 'Analyze trends in customer engagement', 'query_type': 'trend_analysis'},
    {'id': 'trend-growth', 'category': 'Trend Analysis', 'title': 'Growth Patterns',
     'query': 'What are the growth patterns across accounts?', 'query_type': 'trend_analysis'},
    
    # Risk Analysis
    {'id': 'risk-churn', 'category': 'Risk Analysis', 'title': 'Churn Risk',
     'query': 'Which accounts are at risk of churn?', 'query_type': 'account_analysis'},
    {'id': 'risk-factors', 'category': 'Risk Analysis', 'title': 'Risk Factors',
     'query': 'What are the risk factors for our accounts?', 'query_type': 'account_analysis'},
    {'id': 'risk-identification', 'category': 'Risk Analysis', 'title': 'Risk Identification',
     'query': 'Identify accounts that need immediate attention', 'query_type': 'account_analysis'},
    
    # General Analysis
    {'id': 'general-overview', 'category': 'General', 'title': 'Business Overview',
     'query': 'Give me an overview of our business performance', 'query_type': 'general'},
    {'id': 'general-insights', 'category': 'General', 'title': 'Key Insights',
     'query': 'What are the key insights from our data?', 'query_type': 'general'},
    {'id': 'general-recommendations', 'category': 'General', 'title': 'Recommendations',
     'query': 'What recommendations do you have for improving performance?', 'query_type': 'general'},
    
    # DC-Specific Queries
    {'id': 'dc-performance', 'category': 'DC Specific', 'title': 'Data Center Performance',
     'query': 'What are the data center performance metrics?', 'query_type': 'general'},
    {'id': 'dc-infrastructure', 'category': 'DC Specific', 'title': 'Infrastructure Health',
     'query': 'Show me infrastructure health scores', 'query_type': 'general'},
    {'id': 'dc-capacity', 'category': 'DC Specific', 'title': 'Capacity Issues',
     'query': 'Which data center accounts have capacity issues?', 'query_type': 'general'},
    {'id': 'dc-power', 'category': 'DC Specific', 'title': 'Power Efficiency',
     'query': 'Analyze power efficiency across accounts', 'query_type': 'general'},
    {'id': 'dc-cooling', 'category': 'DC Specific', 'title': 'Cooling Performance',
     'query': 'What are the cooling system performance indicators?', 'query_type': 'general'},
]

class AllRAGTemplatesTest:
    """Test all RAG query templates"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
        self.results = []
        
    def authenticate(self) -> bool:
        """Authenticate"""
        try:
            login = self.session.post(f"{self.base_url}/api/login",
                json={'email': 'admin@syntara.com', 'password': 'syntara123'})
            return login.status_code == 200
        except:
            return True
    
    def test_query(self, customer_id: int, template: Dict) -> Tuple[bool, str, float]:
        """Test a single query template"""
        start_time = time.time()
        try:
            response = self.session.post(
                f"{self.base_url}/api/rag-qdrant/query",
                headers={'X-Customer-ID': str(customer_id), 'Content-Type': 'application/json'},
                json={'query': template['query'], 'query_type': template['query_type']},
                timeout=60
            )
            duration = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                if result and 'response' in result and 'error' not in result:
                    return True, f"{result.get('results_count', 0)} results", duration
                else:
                    return False, result.get('error', 'Empty response') if result else 'Empty response', duration
            else:
                return False, f"Status {response.status_code}", duration
        except Exception as e:
            duration = time.time() - start_time
            return False, str(e)[:50], duration
    
    def test_customer_templates(self, customer_id: int, customer_name: str):
        """Test all templates for a customer"""
        print(f"\n{'='*80}")
        print(f"Testing {customer_name} Customer (ID: {customer_id})")
        print(f"{len(ALL_QUERY_TEMPLATES)} Query Templates")
        print(f"{'='*80}")
        
        # Group by category
        by_category = {}
        for template in ALL_QUERY_TEMPLATES:
            cat = template['category']
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(template)
        
        total_passed = 0
        total_failed = 0
        
        for category, templates in by_category.items():
            print(f"\n📂 {category} ({len(templates)} queries)")
            print("-" * 80)
            
            for i, template in enumerate(templates, 1):
                success, message, duration = self.test_query(customer_id, template)
                
                if success:
                    total_passed += 1
                    print(f"  ✅ [{i}/{len(templates)}] {template['title']} - {message} ({duration:.1f}s)")
                else:
                    total_failed += 1
                    print(f"  ❌ [{i}/{len(templates)}] {template['title']} - {message} ({duration:.1f}s)")
        
        print(f"\n{customer_name} Summary: {total_passed} passed, {total_failed} failed")
        return total_passed, total_failed
    
    def run_all_tests(self):
        """Run all tests"""
        print("=" * 80)
        print("🧪 COMPREHENSIVE RAG TEMPLATES TEST - QDRANT CLOUD")
        print("=" * 80)
        print(f"Total Templates: {len(ALL_QUERY_TEMPLATES)}")
        print()
        
        if not self.authenticate():
            print("⚠️  Authentication failed, continuing...")
        
        # Test SaaS
        saas_passed, saas_failed = self.test_customer_templates(SAAS_CUSTOMER_ID, "SaaS")
        
        # Test DC
        dc_passed, dc_failed = self.test_customer_templates(DC_CUSTOMER_ID, "DC")
        
        # Summary
        print(f"\n{'='*80}")
        print("FINAL SUMMARY")
        print(f"{'='*80}")
        print(f"\nSaaS Customer: {saas_passed} passed, {saas_failed} failed")
        print(f"DC Customer: {dc_passed} passed, {dc_failed} failed")
        print(f"\nTotal: {saas_passed + dc_passed} passed, {saas_failed + dc_failed} failed")
        print(f"Success Rate: {((saas_passed + dc_passed) / (saas_passed + saas_failed + dc_passed + dc_failed) * 100):.1f}%")
        
        if saas_failed == 0 and dc_failed == 0:
            print("\n🎉 All query templates passed!")
        else:
            print(f"\n⚠️  {saas_failed + dc_failed} template(s) failed")

def main():
    test_suite = AllRAGTemplatesTest(BASE_URL)
    test_suite.run_all_tests()

if __name__ == '__main__':
    main()
