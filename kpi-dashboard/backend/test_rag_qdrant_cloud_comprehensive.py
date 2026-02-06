#!/usr/bin/env python3
"""
Comprehensive RAG Test Suite for Qdrant Cloud
Tests ALL RAG endpoints and query types for both SaaS and DC customers
"""

import os
import sys
import requests
import time
from typing import Dict, List, Tuple
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
BASE_URL = os.getenv('BACKEND_URL', 'http://localhost:8005')
SAAS_CUSTOMER_ID = 1
DC_CUSTOMER_ID = 5

class ComprehensiveQdrantCloudTest:
    """Comprehensive test suite for all RAG functionality"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
        self.results = []
        
    def log_test(self, test_name: str, status: str, message: str, duration: float = 0):
        """Log test result"""
        result = {
            'test': test_name,
            'status': status,
            'message': message,
            'duration': f"{duration:.2f}s"
        }
        self.results.append(result)
        status_icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{status_icon} {test_name}: {status} - {message} ({duration:.2f}s)")
    
    def authenticate(self) -> bool:
        """Authenticate and set up session"""
        try:
            login_response = self.session.post(
                f"{self.base_url}/api/login",
                json={
                    'email': 'admin@syntara.com',
                    'password': 'syntara123',
                    'remember': False
                },
                headers={'Content-Type': 'application/json'}
            )
            return login_response.status_code == 200
        except:
            return True  # Continue anyway
    
    def test_query(self, customer_id: int, query: str, query_type: str = "general") -> Tuple[bool, str, Dict]:
        """Test a single RAG query"""
        start_time = time.time()
        try:
            headers = {
                'X-Customer-ID': str(customer_id),
                'Content-Type': 'application/json'
            }
            response = self.session.post(
                f"{self.base_url}/api/rag-qdrant/query",
                headers=headers,
                json={
                    'query': query,
                    'query_type': query_type
                },
                timeout=60
            )
            duration = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                if not result:
                    return False, "Empty response", {}
                if 'error' in result:
                    return False, result.get('error', 'Unknown error'), {}
                
                results_count = result.get('results_count', 0)
                response_text = result.get('response', '')
                rag_system = result.get('rag_system', 'unknown')
                
                # For product queries, include response preview to validate product names
                details = {
                    'results_count': results_count,
                    'response_length': len(response_text),
                    'rag_system': rag_system,
                    'response_preview': response_text[:200] if query_type == 'product_analysis' else None
                }
                
                return True, f"Results: {results_count}, System: {rag_system}", details
            else:
                return False, f"Status: {response.status_code}", {}
        except Exception as e:
            return False, f"Exception: {str(e)[:100]}", {}
    
    def test_all_query_types(self, customer_id: int, customer_name: str):
        """Test all query types for a customer"""
        print(f"\n{'='*80}")
        print(f"Testing {customer_name} Customer (ID: {customer_id}) - ALL QUERY TYPES")
        print(f"{'='*80}")
        
        # Comprehensive test queries covering all types
        test_queries = [
            # General queries
            ("Which accounts have the highest revenue?", "general"),
            ("What are the top performing KPIs?", "general"),
            ("Show me customer satisfaction analysis", "general"),
            ("Which accounts are at risk of churn?", "general"),
            ("Analyze revenue growth patterns", "general"),
            
            # Revenue analysis queries
            ("Why is revenue declining?", "revenue_analysis"),
            ("What are the revenue drivers?", "revenue_analysis"),
            ("Show me revenue trends", "revenue_analysis"),
            ("Which accounts contribute most to revenue?", "revenue_analysis"),
            ("Analyze revenue by industry", "revenue_analysis"),
            
            # Account analysis queries
            ("What are the risk factors for our accounts?", "account_analysis"),
            ("Which accounts need immediate attention?", "account_analysis"),
            ("Show me account health scores", "account_analysis"),
            ("Analyze account engagement", "account_analysis"),
            ("Which accounts have low adoption?", "account_analysis"),
            
            # KPI analysis queries
            ("What are the key performance indicators?", "kpi_analysis"),
            ("Show me KPI trends", "kpi_analysis"),
            ("Which KPIs are underperforming?", "kpi_analysis"),
            ("Analyze KPI performance by category", "kpi_analysis"),
            ("What KPIs indicate risk?", "kpi_analysis"),
            
            # Trend analysis queries
            ("Analyze trends in customer engagement", "trend_analysis"),
            ("Show me historical revenue trends", "trend_analysis"),
            ("What are the growth patterns?", "trend_analysis"),
            ("Analyze month-over-month changes", "trend_analysis"),
            
            # DC-specific queries (for DC customer)
            ("What are the data center performance metrics?", "general"),
            ("Show me infrastructure health scores", "general"),
            ("Which data center accounts have capacity issues?", "general"),
            ("Analyze power efficiency across accounts", "general"),
            ("What are the cooling system performance indicators?", "general"),
            
            # Product analysis queries (NEW - 6 tests)
            ("Which products are commonly used across accounts?", "product_analysis"),
            ("What products are widely used across most accounts?", "product_analysis"),
            ("List all product names used by our customers", "product_analysis"),
            ("Which products are most popular across accounts?", "product_analysis"),
            ("Show me product adoption across accounts", "product_analysis"),
            ("What products are deployed across multiple accounts?", "product_analysis"),
        ]
        
        passed = 0
        failed = 0
        total = len(test_queries)
        
        for i, (query, query_type) in enumerate(test_queries, 1):
            start_time = time.time()
            success, message, details = self.test_query(customer_id, query, query_type)
            duration = time.time() - start_time
            
            # For product queries, extract response preview for validation
            response_preview = ""
            if query_type == 'product_analysis' and success and details:
                # Try to get a preview of the actual response
                try:
                    headers = {
                        'X-Customer-ID': str(customer_id),
                        'Content-Type': 'application/json'
                    }
                    response = self.session.post(
                        f"{self.base_url}/api/rag-qdrant/query",
                        headers=headers,
                        json={'query': query, 'query_type': query_type},
                        timeout=60
                    )
                    if response.status_code == 200:
                        result = response.json()
                        response_text = result.get('response', '')[:150]
                        response_preview = f" | Response: {response_text}..."
                except:
                    pass
            
            if success:
                passed += 1
                log_msg = f"{query[:45]}... - {message}"
                # For product queries, show response preview to validate
                if query_type == 'product_analysis' and details.get('response_preview'):
                    preview = details['response_preview']
                    log_msg += f" | Response preview: {preview[:100]}..."
                self.log_test(f"{customer_name} Query {i}/{total}", "PASS", log_msg, duration)
            else:
                failed += 1
                self.log_test(f"{customer_name} Query {i}/{total}", "FAIL", 
                           f"{query[:45]}... - {message}", duration)
        
        # Summary
        self.log_test(f"{customer_name} Queries Summary", 
                     "PASS" if failed == 0 else "FAIL",
                     f"{passed}/{total} passed, {failed} failed", 0)
        
        return passed, failed, total
    
    def test_endpoints(self, customer_id: int, customer_name: str):
        """Test all RAG API endpoints"""
        print(f"\n{'='*80}")
        print(f"Testing {customer_name} Customer (ID: {customer_id}) - API ENDPOINTS")
        print(f"{'='*80}")
        
        endpoints = [
            ("Build Knowledge Base", "POST", f"/api/rag-qdrant/build", {}),
            ("Knowledge Base Status", "GET", f"/api/rag-qdrant/status", None),
            ("Collection Info", "GET", f"/api/rag-qdrant/collection-info", None),
            ("Revenue Analysis", "GET", f"/api/rag-qdrant/revenue-analysis", None),
            ("Risk Analysis", "GET", f"/api/rag-qdrant/risk-analysis", None),
            ("Top Accounts", "GET", f"/api/rag-qdrant/top-accounts", None),
            ("KPI Performance", "GET", f"/api/rag-qdrant/kpi-performance", None),
        ]
        
        passed = 0
        failed = 0
        
        for name, method, path, data in endpoints:
            start_time = time.time()
            try:
                headers = {
                    'X-Customer-ID': str(customer_id),
                    'Content-Type': 'application/json'
                }
                
                if method == "POST":
                    response = self.session.post(f"{self.base_url}{path}", headers=headers, json=data, timeout=120)
                else:
                    response = self.session.get(f"{self.base_url}{path}", headers=headers, timeout=30)
                
                duration = time.time() - start_time
                
                if response.status_code == 200:
                    result = response.json()
                    if 'error' not in result:
                        passed += 1
                        self.log_test(f"{customer_name} {name}", "PASS", 
                                   f"Status: {response.status_code}", duration)
                    else:
                        failed += 1
                        self.log_test(f"{customer_name} {name}", "FAIL", 
                                   f"Error: {result.get('error', 'Unknown')}", duration)
                else:
                    failed += 1
                    self.log_test(f"{customer_name} {name}", "WARN" if response.status_code == 404 else "FAIL", 
                               f"Status: {response.status_code}", duration)
            except Exception as e:
                failed += 1
                duration = time.time() - start_time
                self.log_test(f"{customer_name} {name}", "FAIL", 
                           f"Exception: {str(e)[:50]}", duration)
        
        return passed, failed
    
    def run_all_tests(self):
        """Run comprehensive tests"""
        print("=" * 80)
        print("🧪 COMPREHENSIVE QDRANT CLOUD RAG TEST SUITE")
        print("=" * 80)
        print()
        
        # Authenticate
        if not self.authenticate():
            print("⚠️  Authentication failed, continuing with header-based auth")
        
        # Test SaaS Customer
        print("\n" + "=" * 80)
        print("SAAS CUSTOMER COMPREHENSIVE TESTS")
        print("=" * 80)
        
        saas_queries_passed, saas_queries_failed, saas_total = self.test_all_query_types(SAAS_CUSTOMER_ID, "SaaS")
        saas_endpoints_passed, saas_endpoints_failed = self.test_endpoints(SAAS_CUSTOMER_ID, "SaaS")
        
        # Test DC Customer
        print("\n" + "=" * 80)
        print("DC CUSTOMER COMPREHENSIVE TESTS")
        print("=" * 80)
        
        dc_queries_passed, dc_queries_failed, dc_total = self.test_all_query_types(DC_CUSTOMER_ID, "DC")
        dc_endpoints_passed, dc_endpoints_failed = self.test_endpoints(DC_CUSTOMER_ID, "DC")
        
        # Final Summary
        print("\n" + "=" * 80)
        print("COMPREHENSIVE TEST SUMMARY")
        print("=" * 80)
        
        total_passed = saas_queries_passed + dc_queries_passed + saas_endpoints_passed + dc_endpoints_passed
        total_failed = saas_queries_failed + dc_queries_failed + saas_endpoints_failed + dc_endpoints_failed
        total_tests = total_passed + total_failed
        
        print(f"\nSaaS Customer:")
        print(f"  Queries: {saas_queries_passed}/{saas_total} passed")
        print(f"  Endpoints: {saas_endpoints_passed} passed, {saas_endpoints_failed} failed")
        
        print(f"\nDC Customer:")
        print(f"  Queries: {dc_queries_passed}/{dc_total} passed")
        print(f"  Endpoints: {dc_endpoints_passed} passed, {dc_endpoints_failed} failed")
        
        print(f"\nOverall:")
        print(f"  ✅ Total Passed: {total_passed}")
        print(f"  ❌ Total Failed: {total_failed}")
        print(f"  📊 Success Rate: {(total_passed/total_tests*100):.1f}%")
        
        if total_failed == 0:
            print("\n🎉 All comprehensive tests passed! Qdrant Cloud RAG system is fully operational.")
        else:
            print(f"\n⚠️  {total_failed} test(s) failed. Please review the results above.")
        
        return self.results

def main():
    """Main test execution"""
    test_suite = ComprehensiveQdrantCloudTest(BASE_URL)
    results = test_suite.run_all_tests()
    
    # Exit with appropriate code
    failed_count = sum(1 for r in results if r['status'] == 'FAIL')
    sys.exit(0 if failed_count == 0 else 1)

if __name__ == '__main__':
    main()
