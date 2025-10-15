#!/usr/bin/env python3
"""
Master Test Runner
Executes all test suites for the KPI Dashboard system
"""

import os
import sys
import subprocess
import time
import argparse
from pathlib import Path
from test_config import get_test_config, validate_test_environment

class MasterTestRunner:
    def __init__(self):
        self.config = get_test_config()
        self.test_results = {}
        self.start_time = time.time()
    
    def run_test_suite(self, test_name, test_file, args=None):
        """Run a specific test suite"""
        print(f"\n🧪 Running {test_name}...")
        print("=" * 60)
        
        start_time = time.time()
        
        try:
            cmd = [sys.executable, test_file]
            if args:
                cmd.extend(args)
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            duration = time.time() - start_time
            
            if result.returncode == 0:
                print(f"✅ {test_name} PASSED ({duration:.2f}s)")
                self.test_results[test_name] = {
                    'status': 'PASS',
                    'duration': duration,
                    'output': result.stdout
                }
                return True
            else:
                print(f"❌ {test_name} FAILED ({duration:.2f}s)")
                print(f"Error: {result.stderr}")
                self.test_results[test_name] = {
                    'status': 'FAIL',
                    'duration': duration,
                    'output': result.stdout,
                    'error': result.stderr
                }
                return False
                
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            print(f"⏰ {test_name} TIMEOUT ({duration:.2f}s)")
            self.test_results[test_name] = {
                'status': 'TIMEOUT',
                'duration': duration,
                'error': 'Test timed out after 5 minutes'
            }
            return False
        except Exception as e:
            duration = time.time() - start_time
            print(f"💥 {test_name} ERROR ({duration:.2f}s): {str(e)}")
            self.test_results[test_name] = {
                'status': 'ERROR',
                'duration': duration,
                'error': str(e)
            }
            return False
    
    def check_prerequisites(self):
        """Check if prerequisites are met"""
        print("🔍 Checking prerequisites...")
        
        # Validate configuration
        errors = validate_test_environment(self.config)
        if errors:
            print("❌ Configuration errors found:")
            for error in errors:
                print(f"   - {error}")
            return False
        
        # Check if Docker is running
        try:
            result = subprocess.run(['docker', 'ps'], capture_output=True, text=True)
            if result.returncode != 0:
                print("❌ Docker is not running")
                return False
        except FileNotFoundError:
            print("❌ Docker is not installed")
            return False
        
        # Check if containers are running
        try:
            result = subprocess.run(['docker', 'ps', '--format', '{{.Names}}'], 
                                  capture_output=True, text=True)
            containers = result.stdout.strip().split('\n')
            
            required_containers = ['kpi-dashboard-backend', 'kpi-dashboard-frontend']
            missing_containers = [c for c in required_containers if c not in containers]
            
            if missing_containers:
                print(f"❌ Missing containers: {missing_containers}")
                print("💡 Start containers with: docker-compose up -d")
                return False
        except Exception as e:
            print(f"❌ Error checking containers: {e}")
            return False
        
        print("✅ Prerequisites met")
        return True
    
    def run_individual_tests(self):
        """Run individual component tests"""
        print("\n🔬 Running Individual Component Tests")
        print("=" * 60)
        
        individual_tests = [
            ("Flask App Test", "test_app.py"),
            ("Health Scores Test", "test_health_scores.py"),
            ("RAG Comprehensive Test", "test_rag_comprehensive.py"),
            ("Qdrant RAG Test", "test_qdrant_rag.py"),
            ("OpenAI RAG Test", "test_openai_rag.py"),
            ("Corporate Health Test", "test_corporate_health.py"),
            ("Financial Simple Test", "test_financial_simple.py")
        ]
        
        passed = 0
        total = len(individual_tests)
        
        for test_name, test_file in individual_tests:
            if os.path.exists(test_file):
                if self.run_test_suite(test_name, test_file):
                    passed += 1
            else:
                print(f"⚠️  {test_name}: Test file not found ({test_file})")
        
        print(f"\n📊 Individual Tests: {passed}/{total} passed")
        return passed == total
    
    def run_e2e_tests(self):
        """Run end-to-end tests"""
        print("\n🌐 Running End-to-End Tests")
        print("=" * 60)
        
        e2e_tests = [
            ("Comprehensive E2E", "test_e2e_comprehensive.py", [
                "--url", self.config.frontend_url,
                "--customer-id", str(self.config.customer_id)
            ]),
            ("Docker E2E", "test_docker_e2e.py")
        ]
        
        passed = 0
        total = len(e2e_tests)
        
        for test_name, test_file, args in e2e_tests:
            if os.path.exists(test_file):
                if self.run_test_suite(test_name, test_file, args):
                    passed += 1
            else:
                print(f"⚠️  {test_name}: Test file not found ({test_file})")
        
        print(f"\n📊 E2E Tests: {passed}/{total} passed")
        return passed == total
    
    def run_performance_tests(self):
        """Run performance tests"""
        print("\n⚡ Running Performance Tests")
        print("=" * 60)
        
        # This would include load testing, memory usage, etc.
        # For now, we'll use the performance benchmarks in the E2E tests
        print("ℹ️  Performance tests are included in E2E test suite")
        return True
    
    def generate_report(self):
        """Generate comprehensive test report"""
        total_duration = time.time() - self.start_time
        
        print("\n" + "=" * 80)
        print("📊 COMPREHENSIVE TEST REPORT")
        print("=" * 80)
        
        # Summary
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results.values() if r['status'] == 'PASS'])
        failed_tests = len([r for r in self.test_results.values() if r['status'] == 'FAIL'])
        error_tests = len([r for r in self.test_results.values() if r['status'] == 'ERROR'])
        timeout_tests = len([r for r in self.test_results.values() if r['status'] == 'TIMEOUT'])
        
        print(f"Total Test Suites: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Errors: {error_tests}")
        print(f"Timeouts: {timeout_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        print(f"Total Duration: {total_duration:.2f}s")
        
        # Detailed results
        print("\n📋 DETAILED RESULTS")
        print("-" * 80)
        for test_name, result in self.test_results.items():
            status_icon = {
                'PASS': '✅',
                'FAIL': '❌', 
                'ERROR': '💥',
                'TIMEOUT': '⏰'
            }.get(result['status'], '❓')
            
            print(f"{status_icon} {test_name}: {result['status']} ({result['duration']:.2f}s)")
            
            if result['status'] != 'PASS' and 'error' in result:
                print(f"   Error: {result['error']}")
        
        # Save report to file
        self.save_report()
        
        return passed_tests == total_tests
    
    def save_report(self):
        """Save test report to file"""
        import json
        from datetime import datetime
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"comprehensive_test_report_{timestamp}.json"
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'config': {
                'backend_url': self.config.backend_url,
                'frontend_url': self.config.frontend_url,
                'customer_id': self.config.customer_id
            },
            'summary': {
                'total_tests': len(self.test_results),
                'passed_tests': len([r for r in self.test_results.values() if r['status'] == 'PASS']),
                'failed_tests': len([r for r in self.test_results.values() if r['status'] == 'FAIL']),
                'error_tests': len([r for r in self.test_results.values() if r['status'] == 'ERROR']),
                'timeout_tests': len([r for r in self.test_results.values() if r['status'] == 'TIMEOUT']),
                'total_duration': time.time() - self.start_time
            },
            'test_results': self.test_results
        }
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n💾 Test report saved to: {filename}")
    
    def run_all(self, skip_individual=False, skip_e2e=False, skip_performance=False):
        """Run all test suites"""
        print("🚀 KPI Dashboard Comprehensive Test Suite")
        print("=" * 80)
        print(f"Backend URL: {self.config.backend_url}")
        print(f"Frontend URL: {self.config.frontend_url}")
        print(f"Customer ID: {self.config.customer_id}")
        print("=" * 80)
        
        # Check prerequisites
        if not self.check_prerequisites():
            print("\n❌ Prerequisites not met. Please fix the issues above.")
            return False
        
        # Run test suites
        if not skip_individual:
            self.run_individual_tests()
        
        if not skip_e2e:
            self.run_e2e_tests()
        
        if not skip_performance:
            self.run_performance_tests()
        
        # Generate report
        success = self.generate_report()
        
        if success:
            print("\n🎉 All tests passed! System is working correctly.")
        else:
            print("\n❌ Some tests failed. Check the detailed results above.")
        
        return success

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Run comprehensive tests for KPI Dashboard')
    parser.add_argument('--skip-individual', action='store_true', help='Skip individual component tests')
    parser.add_argument('--skip-e2e', action='store_true', help='Skip end-to-end tests')
    parser.add_argument('--skip-performance', action='store_true', help='Skip performance tests')
    parser.add_argument('--backend-url', default='http://localhost:5059', help='Backend URL')
    parser.add_argument('--frontend-url', default='http://localhost:3000', help='Frontend URL')
    parser.add_argument('--customer-id', type=int, default=6, help='Customer ID')
    
    args = parser.parse_args()
    
    # Set environment variables
    os.environ['TEST_BACKEND_URL'] = args.backend_url
    os.environ['TEST_FRONTEND_URL'] = args.frontend_url
    os.environ['TEST_CUSTOMER_ID'] = str(args.customer_id)
    
    # Run tests
    runner = MasterTestRunner()
    success = runner.run_all(
        skip_individual=args.skip_individual,
        skip_e2e=args.skip_e2e,
        skip_performance=args.skip_performance
    )
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
