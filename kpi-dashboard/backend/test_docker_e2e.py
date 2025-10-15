#!/usr/bin/env python3
"""
Docker-based E2E Test Suite
Tests the system using Docker containers
"""

import os
import sys
import time
import requests
import json
from datetime import datetime

class DockerE2ETestSuite:
    def __init__(self):
        self.backend_url = "http://localhost:5059"
        self.frontend_url = "http://localhost:3000"
        self.customer_id = 6
        self.test_results = []
    
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
    
    def test_docker_containers(self):
        """Test 1: Docker containers are running"""
        start_time = time.time()
        try:
            import subprocess
            result = subprocess.run(['docker', 'ps', '--format', '{{.Names}}'], 
                                  capture_output=True, text=True)
            containers = result.stdout.strip().split('\n')
            
            duration = time.time() - start_time
            
            required_containers = ['kpi-dashboard-backend', 'kpi-dashboard-frontend']
            running_containers = [c for c in containers if c in required_containers]
            
            if len(running_containers) == len(required_containers):
                self.log_test("Docker Containers", "PASS", f"All containers running: {running_containers}", duration)
                return True
            else:
                self.log_test("Docker Containers", "FAIL", f"Missing containers. Running: {running_containers}", duration)
                return False
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("Docker Containers", "FAIL", f"Error: {str(e)}", duration)
            return False
    
    def test_backend_health(self):
        """Test 2: Backend health check"""
        start_time = time.time()
        try:
            response = requests.get(f"{self.backend_url}/", timeout=10)
            duration = time.time() - start_time
            
            if response.status_code == 200 and "KPI Dashboard Backend is running" in response.text:
                self.log_test("Backend Health", "PASS", "Backend is running", duration)
                return True
            else:
                self.log_test("Backend Health", "FAIL", f"Status: {response.status_code}", duration)
                return False
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("Backend Health", "FAIL", f"Error: {str(e)}", duration)
            return False
    
    def test_frontend_health(self):
        """Test 3: Frontend health check"""
        start_time = time.time()
        try:
            response = requests.get(f"{self.frontend_url}/", timeout=10)
            duration = time.time() - start_time
            
            if response.status_code == 200 and "html" in response.text.lower():
                self.log_test("Frontend Health", "PASS", "Frontend is serving content", duration)
                return True
            else:
                self.log_test("Frontend Health", "FAIL", f"Status: {response.status_code}", duration)
                return False
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("Frontend Health", "FAIL", f"Error: {str(e)}", duration)
            return False
    
    def test_api_endpoints(self):
        """Test 4: API endpoints through frontend proxy"""
        start_time = time.time()
        try:
            headers = {'X-Customer-ID': str(self.customer_id)}
            
            endpoints = [
                "/api/accounts",
                "/api/kpi-uploads",
                "/api/health-scores"
            ]
            
            successful_endpoints = 0
            for endpoint in endpoints:
                try:
                    response = requests.get(f"{self.frontend_url}{endpoint}", 
                                          headers=headers, timeout=10)
                    if response.status_code == 200:
                        successful_endpoints += 1
                except:
                    pass
            
            duration = time.time() - start_time
            
            if successful_endpoints == len(endpoints):
                self.log_test("API Endpoints", "PASS", f"All {len(endpoints)} endpoints responding", duration)
                return True
            else:
                self.log_test("API Endpoints", "FAIL", f"Only {successful_endpoints}/{len(endpoints)} endpoints responding", duration)
                return False
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("API Endpoints", "FAIL", f"Error: {str(e)}", duration)
            return False
    
    def test_rag_system(self):
        """Test 5: RAG system functionality"""
        start_time = time.time()
        try:
            headers = {'X-Customer-ID': str(self.customer_id), 'Content-Type': 'application/json'}
            
            # Build knowledge base
            build_response = requests.post(f"{self.frontend_url}/api/rag-qdrant/build", 
                                        headers=headers, timeout=30)
            
            if build_response.status_code != 200:
                duration = time.time() - start_time
                self.log_test("RAG System", "FAIL", f"Knowledge base build failed: {build_response.status_code}", duration)
                return False
            
            # Test query
            query_data = {
                "query": "Which accounts have the highest revenue?",
                "query_type": "general"
            }
            
            query_response = requests.post(f"{self.frontend_url}/api/rag-qdrant/query", 
                                        json=query_data, headers=headers, timeout=30)
            
            duration = time.time() - start_time
            
            if query_response.status_code == 200:
                result = query_response.json()
                if 'error' not in result and result.get('results_count', 0) > 0:
                    self.log_test("RAG System", "PASS", f"RAG query successful with {result.get('results_count', 0)} results", duration)
                    return True
                else:
                    self.log_test("RAG System", "FAIL", "RAG query returned no results", duration)
                    return False
            else:
                self.log_test("RAG System", "FAIL", f"RAG query failed: {query_response.status_code}", duration)
                return False
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("RAG System", "FAIL", f"Error: {str(e)}", duration)
            return False
    
    def test_database_persistence(self):
        """Test 6: Database persistence"""
        start_time = time.time()
        try:
            headers = {'X-Customer-ID': str(self.customer_id)}
            
            # Get accounts
            response = requests.get(f"{self.frontend_url}/api/accounts", headers=headers, timeout=10)
            duration = time.time() - start_time
            
            if response.status_code == 200:
                accounts = response.json()
                if len(accounts) > 0:
                    # Check if we have expected data structure
                    account = accounts[0]
                    required_fields = ['account_id', 'account_name', 'revenue', 'industry']
                    missing_fields = [field for field in required_fields if field not in account]
                    
                    if not missing_fields:
                        self.log_test("Database Persistence", "PASS", f"Database contains {len(accounts)} accounts with valid structure", duration)
                        return True
                    else:
                        self.log_test("Database Persistence", "FAIL", f"Missing fields: {missing_fields}", duration)
                        return False
                else:
                    self.log_test("Database Persistence", "FAIL", "No accounts found in database", duration)
                    return False
            else:
                self.log_test("Database Persistence", "FAIL", f"Status: {response.status_code}", duration)
                return False
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("Database Persistence", "FAIL", f"Error: {str(e)}", duration)
            return False
    
    def run_all_tests(self):
        """Run all Docker E2E tests"""
        print("🐳 Starting Docker E2E Test Suite")
        print("=" * 50)
        print(f"Backend URL: {self.backend_url}")
        print(f"Frontend URL: {self.frontend_url}")
        print(f"Customer ID: {self.customer_id}")
        print("=" * 50)
        
        tests = [
            ("Docker Containers", self.test_docker_containers),
            ("Backend Health", self.test_backend_health),
            ("Frontend Health", self.test_frontend_health),
            ("API Endpoints", self.test_api_endpoints),
            ("RAG System", self.test_rag_system),
            ("Database Persistence", self.test_database_persistence)
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
        print("\n" + "=" * 50)
        print("📊 DOCKER E2E TEST SUMMARY")
        print("=" * 50)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        # Detailed results
        print("\n📋 DETAILED RESULTS")
        print("-" * 50)
        for result in self.test_results:
            status_icon = "✅" if result['status'] == "PASS" else "❌" if result['status'] == "FAIL" else "⚠️"
            print(f"{status_icon} {result['test']}: {result['message']} ({result['duration']:.2f}s)")
        
        # Save results
        self.save_test_results()
        
        return passed_tests == total_tests
    
    def save_test_results(self):
        """Save test results to JSON file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"docker_e2e_test_results_{timestamp}.json"
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'backend_url': self.backend_url,
            'frontend_url': self.frontend_url,
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
    test_suite = DockerE2ETestSuite()
    success = test_suite.run_all_tests()
    
    if success:
        print("\n🎉 All Docker E2E tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some Docker E2E tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
