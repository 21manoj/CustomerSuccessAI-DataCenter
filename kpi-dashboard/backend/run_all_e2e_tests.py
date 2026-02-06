#!/usr/bin/env python3
"""
Run All E2E Tests and Generate Report

Runs all critical E2E tests and generates a comprehensive report
"""

import sys
import os
import subprocess
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

def run_test(test_file):
    """Run a test file and return results"""
    print(f"\n{'='*80}")
    print(f"Running: {test_file}")
    print('='*80)
    
    try:
        result = subprocess.run(
            [sys.executable, test_file],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        return {
            'file': test_file,
            'success': result.returncode == 0,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            'file': test_file,
            'success': False,
            'stdout': '',
            'stderr': 'Test timed out after 5 minutes',
            'returncode': -1
        }
    except Exception as e:
        return {
            'file': test_file,
            'success': False,
            'stdout': '',
            'stderr': str(e),
            'returncode': -1
        }

def main():
    """Run all E2E tests"""
    print("="*80)
    print("E2E TEST SUITE - Complete User to Playbook Flow")
    print("="*80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # List of tests to run
    tests = [
        'test_signal_kpi_association_e2e.py',
        'test_reasoning_generation_e2e.py',
        'test_outcome_reconciliation_e2e.py',
        'test_pre_playbook_validation_e2e.py',
        'test_complete_user_to_playbook_e2e.py'
    ]
    
    results = []
    
    for test_file in tests:
        test_path = os.path.join(os.path.dirname(__file__), test_file)
        if os.path.exists(test_path):
            result = run_test(test_path)
            results.append(result)
        else:
            print(f"⚠️  Test file not found: {test_file}")
            results.append({
                'file': test_file,
                'success': False,
                'stdout': '',
                'stderr': 'File not found',
                'returncode': -1
            })
    
    # Generate report
    print("\n" + "="*80)
    print("TEST RESULTS SUMMARY")
    print("="*80)
    
    passed = sum(1 for r in results if r['success'])
    failed = len(results) - passed
    
    print(f"\nTotal Tests: {len(results)}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    
    print("\n" + "-"*80)
    print("DETAILED RESULTS:")
    print("-"*80)
    
    for result in results:
        status = "✅ PASSED" if result['success'] else "❌ FAILED"
        print(f"\n{status}: {result['file']}")
        if not result['success']:
            if result['stderr']:
                print(f"   Error: {result['stderr'][:200]}...")
            if result['stdout']:
                # Extract last few lines of output
                lines = result['stdout'].split('\n')
                last_lines = [l for l in lines[-10:] if l.strip()]
                if last_lines:
                    print(f"   Last output:")
                    for line in last_lines[-5:]:
                        print(f"      {line}")
    
    # Issues summary
    print("\n" + "="*80)
    print("ISSUES FOUND:")
    print("="*80)
    
    issues = []
    for result in results:
        if not result['success']:
            issues.append({
                'test': result['file'],
                'error': result['stderr'][:200] if result['stderr'] else 'Unknown error'
            })
    
    if issues:
        for i, issue in enumerate(issues, 1):
            print(f"\n{i}. {issue['test']}")
            print(f"   Error: {issue['error']}")
    else:
        print("\n✅ No issues found - all tests passed!")
    
    # Save report
    report_file = f"e2e_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(report_file, 'w') as f:
        f.write(f"# E2E Test Report\n\n")
        f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"## Summary\n\n")
        f.write(f"- Total Tests: {len(results)}\n")
        f.write(f"- ✅ Passed: {passed}\n")
        f.write(f"- ❌ Failed: {failed}\n\n")
        f.write(f"## Detailed Results\n\n")
        for result in results:
            status = "✅ PASSED" if result['success'] else "❌ FAILED"
            f.write(f"### {result['file']}\n\n")
            f.write(f"**Status:** {status}\n\n")
            if not result['success']:
                f.write(f"**Error:**\n```\n{result['stderr']}\n```\n\n")
    
    print(f"\n📄 Full report saved to: {report_file}")
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
