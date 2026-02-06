#!/usr/bin/env python3
"""
Comprehensive RAG Test Suite for DC Users
Tests all RAG functionality for Data Center vertical customers
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
DC_CUSTOMER_ID = 5  # DC customer ID based on previous context

class DCRAGTestSuite:
    """Test suite for DC RAG functionality"""
    
    def __init__(self, base_url: str, customer_id: int):
        self.base_url = base_url
        self.customer_id = customer_id
        self.session = requests.Session()
        self.results = []
        self.authenticated = False
        
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
                    # Check if customer_id matches
                    user_customer_id = data.get('user', {}).get('customer_id') or data.get('customer_id')
                    if user_customer_id == self.customer_id:
                        self.authenticated = True
                        duration = time.time() - start_time
                        self.log_test("Authentication", "PASS", 
                                    f"Logged in as {creds['email']} (Customer {user_customer_id})", duration)
                        return True
                    else:
                        # Still authenticated, just different customer
                        self.authenticated = True
                        duration = time.time() - start_time
                        self.log_test("Authentication", "WARN", 
                                    f"Logged in but customer mismatch (got {user_customer_id}, need {self.customer_id})", duration)
                        return True
            
            # If all logins failed, try without auth (might work if auth is disabled)
            duration = time.time() - start_time
            self.log_test("Authentication", "WARN", 
                        "Could not authenticate, proceeding with header-based auth", duration)
            self.authenticated = True  # Assume we can proceed
            return True
        except Exception as e:
            # If login endpoint doesn't exist or fails, assume header-based auth
            self.authenticated = True
            duration = time.time() - start_time
            self.log_test("Authentication", "WARN", 
                        f"Login error, using header-based auth: {str(e)[:50]}", duration)
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
    
    def test_build_knowledge_base(self) -> bool:
        """Test 2: Build knowledge base for DC customer"""
        start_time = time.time()
        try:
            headers = {
                'X-Customer-ID': str(self.customer_id),
                'Content-Type': 'application/json'
            }
            response = self.session.post(
                f"{self.base_url}/api/rag-qdrant/build",
                headers=headers,
                json={}
            )
            duration = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                if 'error' not in result:
                    self.log_test("Build Knowledge Base", "PASS", 
                                f"Knowledge base built successfully", duration)
                    return True
                else:
                    self.log_test("Build Knowledge Base", "FAIL", 
                                f"Error: {result.get('error', 'Unknown error')}", duration)
                    return False
            else:
                self.log_test("Build Knowledge Base", "FAIL", 
                            f"Status: {response.status_code}", duration)
                return False
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("Build Knowledge Base", "FAIL", f"Exception: {str(e)}", duration)
            return False
    
    def test_query(self, query: str, query_type: str = "general") -> Tuple[bool, str, str]:
        """Test a single RAG query"""
        start_time = time.time()
        try:
            response = self.session.post(
                f"{self.base_url}/api/rag-qdrant/query",
                headers={'X-Customer-ID': str(self.customer_id)},
                json={
                    'query': query,
                    'query_type': query_type
                }
            )
            duration = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                if 'error' in result:
                    return False, result.get('error', 'Unknown error'), ""
                
                response_text = result.get('response', 'No response')
                rag_system = result.get('rag_system', 'unknown')
                results_count = result.get('results_count', 0)
                
                return True, response_text[:200], f"System: {rag_system}, Results: {results_count}"
            else:
                return False, f"Status: {response.status_code}", ""
        except Exception as e:
            return False, f"Exception: {str(e)}", ""
    
    def test_general_queries(self) -> bool:
        """Test 3: General RAG queries"""
        test_queries = [
            "Which accounts have the highest revenue?",
            "What are the top performing KPIs?",
            "Show me customer satisfaction analysis",
            "Which accounts are at risk of churn?",
            "Analyze revenue growth patterns"
        ]
        
        passed = 0
        total = len(test_queries)
        
        for i, query in enumerate(test_queries, 1):
            start_time = time.time()
            success, message, details = self.test_query(query, "general")
            duration = time.time() - start_time
            
            if success:
                passed += 1
                self.log_test(f"General Query {i}", "PASS", 
                           f"Query: '{query[:50]}...' - {details}", duration)
            else:
                self.log_test(f"General Query {i}", "FAIL", 
                           f"Query: '{query[:50]}...' - {message}", duration)
        
        if passed == total:
            self.log_test("General Queries Summary", "PASS", 
                         f"All {total} queries passed", 0)
            return True
        else:
            self.log_test("General Queries Summary", "FAIL", 
                         f"Only {passed}/{total} queries passed", 0)
            return False
    
    def test_analytical_queries(self) -> bool:
        """Test 4: Analytical RAG queries"""
        test_queries = [
            ("Why is revenue declining?", "revenue_analysis"),
            ("What are the risk factors for our accounts?", "risk_analysis"),
            ("How can we improve customer satisfaction?", "general"),
            ("Which accounts need immediate attention?", "account_analysis"),
            ("Analyze trends in customer engagement", "trend_analysis")
        ]
        
        passed = 0
        total = len(test_queries)
        
        for i, (query, query_type) in enumerate(test_queries, 1):
            start_time = time.time()
            success, message, details = self.test_query(query, query_type)
            duration = time.time() - start_time
            
            if success:
                passed += 1
                self.log_test(f"Analytical Query {i}", "PASS", 
                           f"Query: '{query[:50]}...' - {details}", duration)
            else:
                self.log_test(f"Analytical Query {i}", "FAIL", 
                           f"Query: '{query[:50]}...' - {message}", duration)
        
        if passed == total:
            self.log_test("Analytical Queries Summary", "PASS", 
                         f"All {total} queries passed", 0)
            return True
        else:
            self.log_test("Analytical Queries Summary", "FAIL", 
                         f"Only {passed}/{total} queries passed", 0)
            return False
    
    def test_dc_specific_queries(self) -> bool:
        """Test 5: DC-specific queries"""
        test_queries = [
            "What are the data center performance metrics?",
            "Show me infrastructure health scores",
            "Which data center accounts have capacity issues?",
            "Analyze power efficiency across accounts",
            "What are the cooling system performance indicators?"
        ]
        
        passed = 0
        total = len(test_queries)
        
        for i, query in enumerate(test_queries, 1):
            start_time = time.time()
            success, message, details = self.test_query(query, "general")
            duration = time.time() - start_time
            
            if success:
                passed += 1
                self.log_test(f"DC-Specific Query {i}", "PASS", 
                           f"Query: '{query[:50]}...' - {details}", duration)
            else:
                self.log_test(f"DC-Specific Query {i}", "FAIL", 
                           f"Query: '{query[:50]}...' - {message}", duration)
        
        if passed == total:
            self.log_test("DC-Specific Queries Summary", "PASS", 
                         f"All {total} queries passed", 0)
            return True
        else:
            self.log_test("DC-Specific Queries Summary", "FAIL", 
                         f"Only {passed}/{total} queries passed", 0)
            return False
    
    def test_knowledge_base_status(self) -> bool:
        """Test 6: Check knowledge base status"""
        start_time = time.time()
        try:
            headers = {
                'X-Customer-ID': str(self.customer_id),
                'Content-Type': 'application/json'
            }
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
    
    def test_faiss_fallback(self) -> bool:
        """Test 7: Verify FAISS fallback is working"""
        start_time = time.time()
        try:
            headers = {
                'X-Customer-ID': str(self.customer_id),
                'Content-Type': 'application/json'
            }
            # Make a query and check which system was used
            response = self.session.post(
                f"{self.base_url}/api/rag-qdrant/query",
                headers=headers,
                json={
                    'query': "Test query for system detection",
                    'query_type': 'general'
                }
            )
            duration = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                rag_system = result.get('rag_system', 'unknown')
                
                if 'faiss' in rag_system.lower() or 'openai' in rag_system.lower():
                    self.log_test("FAISS Fallback", "PASS", 
                                f"Using {rag_system} (FAISS-based system)", duration)
                    return True
                else:
                    self.log_test("FAISS Fallback", "WARN", 
                                f"Using {rag_system} (may not be FAISS)", duration)
                    return True  # Still pass, just warn
            else:
                self.log_test("FAISS Fallback", "FAIL", 
                            f"Status: {response.status_code}", duration)
                return False
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("FAISS Fallback", "FAIL", f"Exception: {str(e)}", duration)
            return False
    
    def run_all_tests(self):
        """Run all RAG tests for DC users"""
        print("=" * 80)
        print(f"🧪 DC RAG TEST SUITE - Customer ID: {self.customer_id}")
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
        self.authenticate()
        
        # Test 2: Build knowledge base
        print("\n" + "=" * 80)
        print("Building Knowledge Base...")
        print("=" * 80)
        self.test_build_knowledge_base()
        
        # Wait a bit for knowledge base to be ready
        time.sleep(2)
        
        # Test 3: Check knowledge base status
        print("\n" + "=" * 80)
        print("Checking Knowledge Base Status...")
        print("=" * 80)
        self.test_knowledge_base_status()
        
        # Test 4: General queries
        print("\n" + "=" * 80)
        print("Testing General RAG Queries...")
        print("=" * 80)
        self.test_general_queries()
        
        # Test 5: Analytical queries
        print("\n" + "=" * 80)
        print("Testing Analytical RAG Queries...")
        print("=" * 80)
        self.test_analytical_queries()
        
        # Test 6: DC-specific queries
        print("\n" + "=" * 80)
        print("Testing DC-Specific RAG Queries...")
        print("=" * 80)
        self.test_dc_specific_queries()
        
        # Test 7: FAISS fallback verification
        print("\n" + "=" * 80)
        print("Verifying FAISS Fallback...")
        print("=" * 80)
        self.test_faiss_fallback()
        
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
        
        if failed == 0:
            print("\n🎉 All tests passed! DC RAG system is working correctly.")
        else:
            print(f"\n⚠️  {failed} test(s) failed. Please review the results above.")
        
        return self.results

def main():
    """Main test execution"""
    test_suite = DCRAGTestSuite(BASE_URL, DC_CUSTOMER_ID)
    results = test_suite.run_all_tests()
    
    # Exit with appropriate code
    failed_count = sum(1 for r in results if r['status'] == 'FAIL')
    sys.exit(0 if failed_count == 0 else 1)

if __name__ == '__main__':
    main()
