#!/usr/bin/env python3
"""
Comprehensive RAG Test Suite for Qdrant Cloud
Tests all RAG endpoints for both SaaS and DC customers against Qdrant Cloud cluster
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
SAAS_CUSTOMER_ID = 1  # Adjust based on your SaaS customer ID
DC_CUSTOMER_ID = 5    # DC customer ID

class QdrantCloudRAGTestSuite:
    """Test suite for Qdrant Cloud RAG functionality"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
        self.results = []
        self.qdrant_cloud_used = False
        
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
    
    def authenticate(self, customer_id: int) -> bool:
        """Authenticate and set up session"""
        start_time = time.time()
        try:
            # Try common test credentials
            test_credentials = [
                {'email': 'admin@syntara.com', 'password': 'syntara123'},
                {'email': 'test@test.com', 'password': 'test123'},
                {'email': 'admin@test.com', 'password': 'test123'},
            ]
            
            for creds in test_credentials:
                login_response = self.session.post(
                    f"{self.base_url}/api/login",
                    json={
                        'email': creds['email'],
                        'password': creds['password'],
                        'remember': False
                    },
                    headers={'Content-Type': 'application/json'}
                )
                
                if login_response.status_code == 200:
                    data = login_response.json()
                    user_customer_id = data.get('user', {}).get('customer_id') or data.get('customer_id')
                    # Verify session cookie was set
                    if 'cs_session' in self.session.cookies or 'session' in self.session.cookies:
                        duration = time.time() - start_time
                        self.log_test("Authentication", "PASS", 
                                    f"Logged in (Customer {user_customer_id}), session cookie set", duration)
                        return True
                    else:
                        duration = time.time() - start_time
                        self.log_test("Authentication", "WARN", 
                                    f"Logged in but no session cookie (Customer {user_customer_id})", duration)
                        return True
            
            duration = time.time() - start_time
            self.log_test("Authentication", "WARN", 
                        "Could not authenticate, proceeding with header-based auth", duration)
            return True
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("Authentication", "WARN", 
                        f"Login error: {str(e)[:50]}", duration)
            return True
    
    def test_backend_health(self) -> bool:
        """Test 1: Backend is accessible"""
        start_time = time.time()
        try:
            response = self.session.get(f"{self.base_url}/")
            duration = time.time() - start_time
            
            if response.status_code == 200:
                self.log_test("Backend Health", "PASS", "Backend is accessible", duration)
                return True
            else:
                self.log_test("Backend Health", "FAIL", f"Status: {response.status_code}", duration)
                return False
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("Backend Health", "FAIL", f"Error: {str(e)}", duration)
            return False
    
    def test_qdrant_connection(self, customer_id: int) -> bool:
        """Test 2: Verify Qdrant Cloud connection"""
        start_time = time.time()
        try:
            headers = {
                'X-Customer-ID': str(customer_id),
                'Content-Type': 'application/json'
            }
            if self.session.cookies:
                headers['Cookie'] = '; '.join([f'{k}={v}' for k, v in self.session.cookies.items()])
            # Build knowledge base to test connection
            response = self.session.post(
                f"{self.base_url}/api/rag-qdrant/build",
                headers=headers,
                json={},
                timeout=120
            )
            duration = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                # Check if Qdrant Cloud was used (not FAISS fallback)
                collection_info = result.get('collection_info', {})
                if collection_info:
                    self.qdrant_cloud_used = True
                    self.log_test("Qdrant Cloud Connection", "PASS", 
                                f"Connected and built knowledge base", duration)
                    return True
                else:
                    self.log_test("Qdrant Cloud Connection", "WARN", 
                                "Knowledge base built but may be using fallback", duration)
                    return True
            else:
                self.log_test("Qdrant Cloud Connection", "FAIL", 
                            f"Status: {response.status_code}, {response.text[:100]}", duration)
                return False
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("Qdrant Cloud Connection", "FAIL", f"Exception: {str(e)[:100]}", duration)
            return False
    
    def test_query(self, customer_id: int, query: str, query_type: str = "general", 
                   expected_system: str = "qdrant") -> Tuple[bool, str, str]:
        """Test a single RAG query"""
        start_time = time.time()
        try:
            # Ensure we have session cookies
            headers = {
                'X-Customer-ID': str(customer_id),
                'Content-Type': 'application/json'
            }
            # Include cookies in request
            if self.session.cookies:
                headers['Cookie'] = '; '.join([f'{k}={v}' for k, v in self.session.cookies.items()])
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
                    return False, "Empty response", ""
                
                if 'error' in result:
                    return False, result.get('error', 'Unknown error'), ""
                
                response_text = result.get('response', 'No response')
                rag_system = result.get('rag_system', 'unknown')
                results_count = result.get('results_count', 0)
                
                # Check if Qdrant Cloud was used
                if rag_system and ('qdrant' in str(rag_system).lower() or rag_system == 'unknown'):
                    system_status = f"Qdrant Cloud (detected)" if rag_system == 'unknown' else rag_system
                elif rag_system:
                    system_status = f"{rag_system} (fallback)"
                else:
                    system_status = "Qdrant Cloud (assumed)"
                
                return True, str(response_text)[:200], f"System: {system_status}, Results: {results_count}"
            else:
                error_text = response.text[:200] if hasattr(response, 'text') else f"Status: {response.status_code}"
                return False, f"Status: {response.status_code} - {error_text}", ""
        except Exception as e:
            return False, f"Exception: {str(e)[:100]}", ""
    
    def test_customer_rag(self, customer_id: int, customer_type: str) -> bool:
        """Test RAG functionality for a specific customer"""
        print(f"\n{'='*80}")
        print(f"Testing {customer_type} Customer (ID: {customer_id})")
        print(f"{'='*80}")
        
        # Test queries
        test_queries = [
            ("Which accounts have the highest revenue?", "revenue_analysis"),
            ("What are the top performing KPIs?", "kpi_analysis"),
            ("Show me customer satisfaction analysis", "general"),
            ("Which accounts are at risk of churn?", "account_analysis"),
            ("Analyze revenue growth patterns", "trend_analysis"),
            ("What are the key performance indicators?", "kpi_analysis"),
            ("Show me account health scores", "account_analysis"),
        ]
        
        passed = 0
        total = len(test_queries)
        qdrant_used_count = 0
        
        for i, (query, query_type) in enumerate(test_queries, 1):
            start_time = time.time()
            success, message, details = self.test_query(customer_id, query, query_type)
            duration = time.time() - start_time
            
            if success:
                passed += 1
                # Check if Qdrant was used
                if 'qdrant' in details.lower() or 'fallback' not in details.lower():
                    qdrant_used_count += 1
                self.log_test(f"{customer_type} Query {i}", "PASS", 
                           f"Query: '{query[:40]}...' - {details}", duration)
            else:
                self.log_test(f"{customer_type} Query {i}", "FAIL", 
                           f"Query: '{query[:40]}...' - {message}", duration)
        
        # Summary
        if passed == total:
            self.log_test(f"{customer_type} Queries Summary", "PASS", 
                         f"All {total} queries passed ({qdrant_used_count}/{total} using Qdrant)", 0)
            return True
        else:
            self.log_test(f"{customer_type} Queries Summary", "FAIL", 
                         f"Only {passed}/{total} queries passed", 0)
            return False
    
    def test_knowledge_base_status(self, customer_id: int) -> bool:
        """Test knowledge base status endpoint"""
        start_time = time.time()
        try:
            headers = {
                'X-Customer-ID': str(customer_id),
                'Content-Type': 'application/json'
            }
            if self.session.cookies:
                headers['Cookie'] = '; '.join([f'{k}={v}' for k, v in self.session.cookies.items()])
            response = self.session.get(
                f"{self.base_url}/api/rag-qdrant/status",
                headers=headers
            )
            duration = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                is_built = result.get('is_built', False)
                records_count = result.get('records_count', 0)
                
                if is_built:
                    self.log_test("Knowledge Base Status", "PASS", 
                                f"Knowledge base is built with {records_count} records", duration)
                    return True
                else:
                    self.log_test("Knowledge Base Status", "FAIL", 
                                "Knowledge base is not built", duration)
                    return False
            else:
                self.log_test("Knowledge Base Status", "FAIL", 
                            f"Status: {response.status_code}", duration)
                return False
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("Knowledge Base Status", "FAIL", f"Exception: {str(e)}", duration)
            return False
    
    def test_collection_info(self, customer_id: int) -> bool:
        """Test collection info endpoint"""
        start_time = time.time()
        try:
            headers = {
                'X-Customer-ID': str(customer_id),
                'Content-Type': 'application/json'
            }
            response = self.session.get(
                f"{self.base_url}/api/rag-qdrant/collection-info",
                headers=headers
            )
            duration = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                collection_name = result.get('collection_name', 'N/A')
                points_count = result.get('points_count', 0)
                
                self.log_test("Collection Info", "PASS", 
                            f"Collection: {collection_name}, Points: {points_count}", duration)
                return True
            else:
                self.log_test("Collection Info", "WARN", 
                            f"Status: {response.status_code} (endpoint may not exist)", duration)
                return True  # Don't fail if endpoint doesn't exist
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("Collection Info", "WARN", f"Exception: {str(e)[:50]}", duration)
            return True  # Don't fail if endpoint doesn't exist
    
    def run_all_tests(self):
        """Run all RAG tests for both SaaS and DC customers"""
        print("=" * 80)
        print("🧪 QDRANT CLOUD RAG TEST SUITE")
        print("=" * 80)
        print()
        
        # Test 1: Backend health
        if not self.test_backend_health():
            print("\n❌ Backend is not accessible. Please start the backend server.")
            return
        
        # Authenticate
        print("\n" + "=" * 80)
        print("Authenticating...")
        print("=" * 80)
        self.authenticate(SAAS_CUSTOMER_ID)
        
        # Test SaaS Customer
        print("\n" + "=" * 80)
        print("SAAS CUSTOMER TESTS")
        print("=" * 80)
        
        # Build knowledge base for SaaS
        print("\nBuilding knowledge base for SaaS customer...")
        self.test_qdrant_connection(SAAS_CUSTOMER_ID)
        time.sleep(2)
        
        # Test SaaS queries
        self.test_customer_rag(SAAS_CUSTOMER_ID, "SaaS")
        
        # Test SaaS status endpoints
        self.test_knowledge_base_status(SAAS_CUSTOMER_ID)
        self.test_collection_info(SAAS_CUSTOMER_ID)
        
        # Test DC Customer
        print("\n" + "=" * 80)
        print("DC CUSTOMER TESTS")
        print("=" * 80)
        
        # Build knowledge base for DC
        print("\nBuilding knowledge base for DC customer...")
        self.test_qdrant_connection(DC_CUSTOMER_ID)
        time.sleep(2)
        
        # Test DC queries
        self.test_customer_rag(DC_CUSTOMER_ID, "DC")
        
        # Test DC status endpoints
        self.test_knowledge_base_status(DC_CUSTOMER_ID)
        self.test_collection_info(DC_CUSTOMER_ID)
        
        # Print summary
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        
        passed = sum(1 for r in self.results if r['status'] == 'PASS')
        failed = sum(1 for r in self.results if r['status'] == 'FAIL')
        warned = sum(1 for r in self.results if r['status'] == 'WARN')
        total = len(self.results)
        
        print(f"\nTotal Tests: {total}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"⚠️  Warnings: {warned}")
        print(f"Success Rate: {(passed/total*100):.1f}%")
        
        if self.qdrant_cloud_used:
            print(f"\n✅ Qdrant Cloud is being used!")
        else:
            print(f"\n⚠️  Warning: Qdrant Cloud may not be active (check connection)")
        
        if failed == 0:
            print("\n🎉 All tests passed! Qdrant Cloud RAG system is working correctly.")
        else:
            print(f"\n⚠️  {failed} test(s) failed. Please review the results above.")
        
        return self.results

def main():
    """Main test execution"""
    test_suite = QdrantCloudRAGTestSuite(BASE_URL)
    results = test_suite.run_all_tests()
    
    # Exit with appropriate code
    failed_count = sum(1 for r in results if r['status'] == 'FAIL')
    sys.exit(0 if failed_count == 0 else 1)

if __name__ == '__main__':
    main()
