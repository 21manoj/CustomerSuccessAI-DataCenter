#!/usr/bin/env python3
"""
Comprehensive End-to-End Test Suite for KPI Dashboard
Tests the complete system workflow from data upload to RAG analysis
"""

import os
import sys
import json
import time
import requests
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class E2ETestSuite:
    def __init__(self, base_url="http://localhost:3000"):
        self.base_url = base_url
        self.customer_id = 6
        self.test_results = []
        self.session = requests.Session()
        self.session.headers.update({
            'X-Customer-ID': str(self.customer_id),
            'Content-Type': 'application/json'
        })
    
    def log_test(self, test_name, status, message="", duration=0):
        """Log test result"""
        result = {
            'test': test_name,
            'status': status,
            'message': message,
            'duration': duration,
            'timestamp': datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status_icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{status_icon} {test_name}: {message} ({duration:.2f}s)")
    
    def test_backend_health(self):
        """Test 1: Backend health check"""
        start_time = time.time()
        try:
            response = self.session.get(f"{self.base_url}/api/health")
            duration = time.time() - start_time
            
            if response.status_code == 200:
                self.log_test("Backend Health", "PASS", "Backend is running", duration)
                return True
            else:
                self.log_test("Backend Health", "FAIL", f"Status: {response.status_code}", duration)
                return False
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("Backend Health", "FAIL", f"Error: {str(e)}", duration)
            return False
    
    def test_database_connectivity(self):
        """Test 2: Database connectivity and data"""
        start_time = time.time()
        try:
            # Test accounts endpoint
            response = self.session.get(f"{self.base_url}/api/accounts")
            duration = time.time() - start_time
            
            if response.status_code == 200:
                accounts = response.json()
                if len(accounts) > 0:
                    self.log_test("Database Connectivity", "PASS", f"Found {len(accounts)} accounts", duration)
                    return True
                else:
                    self.log_test("Database Connectivity", "FAIL", "No accounts found", duration)
                    return False
            else:
                self.log_test("Database Connectivity", "FAIL", f"Status: {response.status_code}", duration)
                return False
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("Database Connectivity", "FAIL", f"Error: {str(e)}", duration)
            return False
    
    def test_kpi_data_integrity(self):
        """Test 3: KPI data integrity"""
        start_time = time.time()
        try:
            # Test KPI uploads endpoint
            response = self.session.get(f"{self.base_url}/api/kpi-uploads")
            duration = time.time() - start_time
            
            if response.status_code == 200:
                uploads = response.json()
                if len(uploads) > 0:
                    # Check data structure
                    upload = uploads[0]
                    required_fields = ['upload_id', 'customer_id', 'uploaded_at', 'file_name']
                    missing_fields = [field for field in required_fields if field not in upload]
                    
                    if not missing_fields:
                        self.log_test("KPI Data Integrity", "PASS", f"Found {len(uploads)} uploads with valid structure", duration)
                        return True
                    else:
                        self.log_test("KPI Data Integrity", "FAIL", f"Missing fields: {missing_fields}", duration)
                        return False
                else:
                    self.log_test("KPI Data Integrity", "FAIL", "No KPI uploads found", duration)
                    return False
            else:
                self.log_test("KPI Data Integrity", "FAIL", f"Status: {response.status_code}", duration)
                return False
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("KPI Data Integrity", "FAIL", f"Error: {str(e)}", duration)
            return False
    
    def test_health_score_calculation(self):
        """Test 4: Health score calculation"""
        start_time = time.time()
        try:
            response = self.session.get(f"{self.base_url}/api/health-scores")
            duration = time.time() - start_time
            
            if response.status_code == 200:
                health_data = response.json()
                if 'accounts' in health_data and len(health_data['accounts']) > 0:
                    # Check if health scores are calculated
                    account = health_data['accounts'][0]
                    if 'health_score' in account and account['health_score'] is not None:
                        self.log_test("Health Score Calculation", "PASS", f"Health scores calculated for {len(health_data['accounts'])} accounts", duration)
                        return True
                    else:
                        self.log_test("Health Score Calculation", "FAIL", "Health scores not calculated", duration)
                        return False
                else:
                    self.log_test("Health Score Calculation", "FAIL", "No account health data found", duration)
                    return False
            else:
                self.log_test("Health Score Calculation", "FAIL", f"Status: {response.status_code}", duration)
                return False
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("Health Score Calculation", "FAIL", f"Error: {str(e)}", duration)
            return False
    
    def test_rag_knowledge_base_build(self):
        """Test 5: RAG knowledge base building"""
        start_time = time.time()
        try:
            # Build knowledge base
            response = self.session.post(f"{self.base_url}/api/rag-qdrant/build")
            duration = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                if result.get('status') == 'success':
                    self.log_test("RAG Knowledge Base Build", "PASS", "Knowledge base built successfully", duration)
                    return True
                else:
                    self.log_test("RAG Knowledge Base Build", "FAIL", f"Build failed: {result.get('message', 'Unknown error')}", duration)
                    return False
            else:
                self.log_test("RAG Knowledge Base Build", "FAIL", f"Status: {response.status_code}", duration)
                return False
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("RAG Knowledge Base Build", "FAIL", f"Error: {str(e)}", duration)
            return False
    
    def test_rag_query_execution(self):
        """Test 6: RAG query execution"""
        start_time = time.time()
        try:
            # Test various query types
            test_queries = [
                {
                    "query": "Which accounts have the highest revenue?",
                    "query_type": "general"
                },
                {
                    "query": "Show me customer satisfaction scores",
                    "query_type": "kpi_analysis"
                },
                {
                    "query": "What are the top performing accounts?",
                    "query_type": "account_analysis"
                }
            ]
            
            successful_queries = 0
            for query_data in test_queries:
                response = self.session.post(f"{self.base_url}/api/rag-qdrant/query", json=query_data)
                
                if response.status_code == 200:
                    result = response.json()
                    if 'error' not in result and result.get('results_count', 0) > 0:
                        successful_queries += 1
            
            duration = time.time() - start_time
            
            if successful_queries == len(test_queries):
                self.log_test("RAG Query Execution", "PASS", f"All {len(test_queries)} queries executed successfully", duration)
                return True
            else:
                self.log_test("RAG Query Execution", "FAIL", f"Only {successful_queries}/{len(test_queries)} queries successful", duration)
                return False
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("RAG Query Execution", "FAIL", f"Error: {str(e)}", duration)
            return False
    
    def test_temporal_analysis(self):
        """Test 7: Temporal analysis capabilities"""
        start_time = time.time()
        try:
            # Test temporal query
            query_data = {
                "query": "Show me revenue trends for the last 4 months",
                "query_type": "temporal_analysis"
            }
            
            response = self.session.post(f"{self.base_url}/api/rag-qdrant/query", json=query_data)
            duration = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                if 'error' not in result and result.get('results_count', 0) > 0:
                    # Check if temporal data is present
                    has_temporal_data = any(
                        res.get('metadata', {}).get('type') == 'temporal_revenue' 
                        for res in result.get('relevant_results', [])
                    )
                    
                    if has_temporal_data:
                        self.log_test("Temporal Analysis", "PASS", "Temporal data found in results", duration)
                        return True
                    else:
                        self.log_test("Temporal Analysis", "FAIL", "No temporal data found", duration)
                        return False
                else:
                    self.log_test("Temporal Analysis", "FAIL", "Query returned no results", duration)
                    return False
            else:
                self.log_test("Temporal Analysis", "FAIL", f"Status: {response.status_code}", duration)
                return False
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("Temporal Analysis", "FAIL", f"Error: {str(e)}", duration)
            return False
    
    def test_api_endpoints(self):
        """Test 8: Critical API endpoints"""
        start_time = time.time()
        try:
            critical_endpoints = [
                "/api/accounts",
                "/api/kpi-uploads", 
                "/api/health-scores",
                "/api/rag-qdrant/status",
                "/api/corporate/health-summary"
            ]
            
            successful_endpoints = 0
            for endpoint in critical_endpoints:
                response = self.session.get(f"{self.base_url}{endpoint}")
                if response.status_code == 200:
                    successful_endpoints += 1
            
            duration = time.time() - start_time
            
            if successful_endpoints == len(critical_endpoints):
                self.log_test("API Endpoints", "PASS", f"All {len(critical_endpoints)} critical endpoints responding", duration)
                return True
            else:
                self.log_test("API Endpoints", "FAIL", f"Only {successful_endpoints}/{len(critical_endpoints)} endpoints responding", duration)
                return False
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("API Endpoints", "FAIL", f"Error: {str(e)}", duration)
            return False
    
    def test_data_consistency(self):
        """Test 9: Data consistency across endpoints"""
        start_time = time.time()
        try:
            # Get accounts from different endpoints
            accounts_response = self.session.get(f"{self.base_url}/api/accounts")
            health_response = self.session.get(f"{self.base_url}/api/health-scores")
            
            duration = time.time() - start_time
            
            if accounts_response.status_code == 200 and health_response.status_code == 200:
                accounts_data = accounts_response.json()
                health_data = health_response.json()
                
                accounts_count = len(accounts_data)
                health_accounts_count = len(health_data.get('accounts', []))
                
                if accounts_count == health_accounts_count:
                    self.log_test("Data Consistency", "PASS", f"Account counts match: {accounts_count}", duration)
                    return True
                else:
                    self.log_test("Data Consistency", "FAIL", f"Account count mismatch: {accounts_count} vs {health_accounts_count}", duration)
                    return False
            else:
                self.log_test("Data Consistency", "FAIL", "Failed to fetch data from endpoints", duration)
                return False
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("Data Consistency", "FAIL", f"Error: {str(e)}", duration)
            return False
    
    def test_performance_benchmarks(self):
        """Test 10: Performance benchmarks"""
        start_time = time.time()
        try:
            # Test RAG query performance
            query_data = {
                "query": "Which accounts have the highest revenue?",
                "query_type": "general"
            }
            
            response_start = time.time()
            response = self.session.post(f"{self.base_url}/api/rag-qdrant/query", json=query_data)
            response_time = time.time() - response_start
            
            duration = time.time() - start_time
            
            if response.status_code == 200 and response_time < 5.0:  # Should respond within 5 seconds
                self.log_test("Performance Benchmarks", "PASS", f"RAG query responded in {response_time:.2f}s", duration)
                return True
            else:
                self.log_test("Performance Benchmarks", "FAIL", f"RAG query took {response_time:.2f}s (too slow)", duration)
                return False
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("Performance Benchmarks", "FAIL", f"Error: {str(e)}", duration)
            return False
    
    def run_all_tests(self):
        """Run all end-to-end tests"""
        print("🚀 Starting Comprehensive End-to-End Test Suite")
        print("=" * 70)
        print(f"Testing against: {self.base_url}")
        print(f"Customer ID: {self.customer_id}")
        print("=" * 70)
        
        tests = [
            ("Backend Health", self.test_backend_health),
            ("Database Connectivity", self.test_database_connectivity),
            ("KPI Data Integrity", self.test_kpi_data_integrity),
            ("Health Score Calculation", self.test_health_score_calculation),
            ("RAG Knowledge Base Build", self.test_rag_knowledge_base_build),
            ("RAG Query Execution", self.test_rag_query_execution),
            ("Temporal Analysis", self.test_temporal_analysis),
            ("API Endpoints", self.test_api_endpoints),
            ("Data Consistency", self.test_data_consistency),
            ("Performance Benchmarks", self.test_performance_benchmarks)
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test_name, test_func in tests:
            print(f"\n🧪 Running: {test_name}")
            try:
                if test_func():
                    passed_tests += 1
            except Exception as e:
                self.log_test(test_name, "ERROR", f"Unexpected error: {str(e)}", 0)
        
        # Summary
        print("\n" + "=" * 70)
        print("📊 TEST SUMMARY")
        print("=" * 70)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        # Detailed results
        print("\n📋 DETAILED RESULTS")
        print("-" * 70)
        for result in self.test_results:
            status_icon = "✅" if result['status'] == "PASS" else "❌" if result['status'] == "FAIL" else "⚠️"
            print(f"{status_icon} {result['test']}: {result['message']} ({result['duration']:.2f}s)")
        
        # Save results to file
        self.save_test_results()
        
        return passed_tests == total_tests
    
    def save_test_results(self):
        """Save test results to JSON file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"e2e_test_results_{timestamp}.json"
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'base_url': self.base_url,
            'customer_id': self.customer_id,
            'total_tests': len(self.test_results),
            'passed_tests': len([r for r in self.test_results if r['status'] == 'PASS']),
            'failed_tests': len([r for r in self.test_results if r['status'] == 'FAIL']),
            'error_tests': len([r for r in self.test_results if r['status'] == 'ERROR']),
            'test_results': self.test_results
        }
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n💾 Test results saved to: {filename}")

def main():
    """Main test execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run E2E tests for KPI Dashboard')
    parser.add_argument('--url', default='http://localhost:3000', help='Base URL for testing')
    parser.add_argument('--customer-id', type=int, default=6, help='Customer ID for testing')
    
    args = parser.parse_args()
    
    # Create test suite
    test_suite = E2ETestSuite(base_url=args.url)
    test_suite.customer_id = args.customer_id
    test_suite.session.headers.update({'X-Customer-ID': str(args.customer_id)})
    
    # Run tests
    success = test_suite.run_all_tests()
    
    if success:
        print("\n🎉 All tests passed! System is working correctly.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Check the detailed results above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
