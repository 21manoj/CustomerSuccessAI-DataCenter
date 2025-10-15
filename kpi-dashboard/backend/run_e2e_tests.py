#!/usr/bin/env python3
"""
Simple E2E Test Runner
Runs the comprehensive test suite with proper setup
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def check_services_running():
    """Check if required services are running"""
    print("🔍 Checking if services are running...")
    
    # Check if Docker containers are running
    try:
        result = subprocess.run(['docker', 'ps', '--format', 'table {{.Names}}\t{{.Status}}'], 
                              capture_output=True, text=True)
        if 'kpi-dashboard-backend' in result.stdout and 'kpi-dashboard-frontend' in result.stdout:
            print("✅ Docker containers are running")
            return True
        else:
            print("❌ Docker containers not running")
            return False
    except Exception as e:
        print(f"❌ Error checking Docker: {e}")
        return False

def wait_for_services(max_wait=60):
    """Wait for services to be ready"""
    print("⏳ Waiting for services to be ready...")
    
    import requests
    
    for i in range(max_wait):
        try:
            response = requests.get("http://localhost:3000/api/health", timeout=5)
            if response.status_code == 200:
                print("✅ Services are ready!")
                return True
        except:
            pass
        
        print(f"   Waiting... ({i+1}/{max_wait})")
        time.sleep(1)
    
    print("❌ Services not ready after maximum wait time")
    return False

def run_e2e_tests():
    """Run the E2E test suite"""
    print("🚀 Starting E2E Test Suite")
    print("=" * 50)
    
    # Check if services are running
    if not check_services_running():
        print("\n💡 To start services, run:")
        print("   docker-compose up -d")
        print("   ./run_e2e_tests.py")
        return False
    
    # Wait for services to be ready
    if not wait_for_services():
        return False
    
    # Run the comprehensive test suite
    print("\n🧪 Running comprehensive E2E tests...")
    try:
        result = subprocess.run([
            sys.executable, 'test_e2e_comprehensive.py',
            '--url', 'http://localhost:3000',
            '--customer-id', '6'
        ], cwd=Path(__file__).parent)
        
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return False

def main():
    """Main function"""
    print("🎯 KPI Dashboard E2E Test Runner")
    print("=" * 50)
    
    # Change to backend directory
    backend_dir = Path(__file__).parent
    os.chdir(backend_dir)
    
    # Run tests
    success = run_e2e_tests()
    
    if success:
        print("\n🎉 All E2E tests passed!")
        return 0
    else:
        print("\n❌ E2E tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
