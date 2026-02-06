#!/usr/bin/env python3
"""
Run All Platform E2E Tests

Runs comprehensive platform E2E tests covering:
- Complete platform workflow
- User journey
- All major features
"""

import sys
import os
import subprocess
from datetime import datetime

def run_test(test_file, test_name):
    """Run a test file"""
    print(f"\n{'='*80}")
    print(f"Running: {test_name}")
    print(f"File: {test_file}")
    print('='*80)
    
    try:
        result = subprocess.run(
            [sys.executable, test_file],
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )
        
        return {
            'name': test_name,
            'file': test_file,
            'success': result.returncode == 0,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            'name': test_name,
            'file': test_file,
            'success': False,
            'stdout': '',
            'stderr': 'Test timed out after 10 minutes',
            'returncode': -1
        }
    except Exception as e:
        return {
            'name': test_name,
            'file': test_file,
            'success': False,
            'stdout': '',
            'stderr': str(e),
            'returncode': -1
        }

def main():
    """Run all platform E2E tests"""
    print("="*80)
    print("PLATFORM E2E TEST SUITE")
    print("="*80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tests = [
        ('test_platform_complete_e2e.py', 'Complete Platform Workflow'),
        ('test_platform_user_journey_e2e.py', 'User Journey E2E'),
    ]
    
    results = []
    base_dir = os.path.dirname(__file__)
    
    for test_file, test_name in tests:
        test_path = os.path.join(base_dir, test_file)
        if os.path.exists(test_path):
            result = run_test(test_path, test_name)
            results.append(result)
        else:
            print(f"⚠️  Test file not found: {test_file}")
            results.append({
                'name': test_name,
                'file': test_file,
                'success': False,
                'stdout': '',
                'stderr': 'File not found',
                'returncode': -1
            })
    
    # Summary
    print("\n" + "="*80)
    print("PLATFORM E2E TEST RESULTS SUMMARY")
    print("="*80)
    
    passed = sum(1 for r in results if r['success'])
    failed = len(results) - passed
    
    print(f"\nTotal Tests: {len(results)}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"Success Rate: {(passed/len(results))*100:.1f}%")
    
    print("\n" + "-"*80)
    print("DETAILED RESULTS:")
    print("-"*80)
    
    for result in results:
        status = "✅ PASSED" if result['success'] else "❌ FAILED"
        print(f"\n{status}: {result['name']}")
        if not result['success']:
            if result['stderr']:
                print(f"   Error: {result['stderr'][:300]}...")
            # Extract key output
            if result['stdout']:
                lines = result['stdout'].split('\n')
                summary_lines = [l for l in lines if 'TEST SUMMARY' in l or 'PASSED' in l or 'FAILED' in l]
                if summary_lines:
                    print(f"   Summary:")
                    for line in summary_lines[-5:]:
                        print(f"      {line}")
    
    # Issues
    print("\n" + "="*80)
    print("ISSUES FOUND:")
    print("="*80)
    
    issues = [r for r in results if not r['success']]
    if issues:
        for i, issue in enumerate(issues, 1):
            print(f"\n{i}. {issue['name']}")
            print(f"   File: {issue['file']}")
            if issue['stderr']:
                print(f"   Error: {issue['stderr'][:200]}...")
    else:
        print("\n✅ No issues found - all platform tests passed!")
    
    # Save report
    report_file = f"platform_e2e_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(report_file, 'w') as f:
        f.write(f"# Platform E2E Test Report\n\n")
        f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"## Summary\n\n")
        f.write(f"- Total Tests: {len(results)}\n")
        f.write(f"- ✅ Passed: {passed}\n")
        f.write(f"- ❌ Failed: {failed}\n\n")
        f.write(f"## Detailed Results\n\n")
        for result in results:
            status = "✅ PASSED" if result['success'] else "❌ FAILED"
            f.write(f"### {result['name']}\n\n")
            f.write(f"**Status:** {status}\n\n")
            if not result['success']:
                f.write(f"**Error:**\n```\n{result['stderr']}\n```\n\n")
    
    print(f"\n📄 Full report saved to: {report_file}")
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
