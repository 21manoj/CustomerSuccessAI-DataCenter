#!/usr/bin/env python3
"""
Wizard A - Wrapper Test Script
===============================

Test the wrapper scripts independently before Wizard A integration.

Tests:
1. Generate 5 accounts
2. Generate KPIs for those accounts
3. Generate milestones
4. Verify outputs

Usage:
    python test_wrappers.py
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime

# Test configuration
TEST_ACCOUNTS = 5
TEST_START_ID = 29001  # Use 90xxx range to avoid conflicts
TEST_PATTERN_MIX = {
    "crisis": 0.2,
    "churn": 0.2,
    "stable": 0.3,
    "expansion": 0.3
}


def run_command(cmd, description, timeout=300):
    """Run a command and report results"""
    
    print()
    print("="*70)
    print(f"RUNNING: {description}")
    print("="*70)
    print(f"Command: {' '.join(cmd)}")
    print()
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        print(result.stdout)
        
        if result.returncode != 0:
            print(f"❌ ERROR:")
            print(result.stderr)
            return False
        
        print(f"✅ SUCCESS: {description}")
        return True
        
    except subprocess.TimeoutExpired:
        print(f"❌ TIMEOUT after {timeout} seconds")
        return False
    except Exception as e:
        print(f"❌ EXCEPTION: {e}")
        return False


def verify_files(directory, expected_patterns):
    """Verify expected files were created"""
    
    print()
    print("="*70)
    print(f"VERIFYING FILES IN: {directory}")
    print("="*70)
    
    if not os.path.exists(directory):
        print(f"❌ Directory not found: {directory}")
        return False
    
    all_good = True
    
    for pattern in expected_patterns:
        files = list(Path(directory).glob(pattern))
        
        if files:
            print(f"✅ Found {len(files)} files matching: {pattern}")
            for f in files[:3]:  # Show first 3
                print(f"   - {f.name}")
            if len(files) > 3:
                print(f"   ... and {len(files) - 3} more")
        else:
            print(f"❌ No files found matching: {pattern}")
            all_good = False
    
    return all_good


def main():
    print("="*70)
    print("WIZARD A - WRAPPER TEST SUITE")
    print("="*70)
    print(f"Testing with {TEST_ACCOUNTS} accounts (IDs {TEST_START_ID}-{TEST_START_ID + TEST_ACCOUNTS - 1})")
    print(f"Pattern mix: {TEST_PATTERN_MIX}")
    print()
    
    # Setup test directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    test_dir = f"test_run_{timestamp}"
    output_dir = os.path.join(test_dir, "data")
    processed_dir = os.path.join(test_dir, "processed")
    
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(processed_dir, exist_ok=True)
    
    print(f"📁 Test directory: {test_dir}")
    print()
    
    # Test counters
    tests_passed = 0
    tests_failed = 0
    
    # ========================================================================
    # TEST 1: Journey Generator Wrapper
    # ========================================================================
    
    if run_command(
        cmd=[
            'python3', 'wizard_journey_generator.py',
            '--accounts', str(TEST_ACCOUNTS),
            '--start-id', str(TEST_START_ID),
            '--pattern-mix', json.dumps(TEST_PATTERN_MIX),
            '--output-dir', output_dir
        ],
        description='Test 1: Journey Generator Wrapper',
        timeout=300
    ):
        tests_passed += 1
        
        # Verify journey files
        if verify_files(output_dir, [
            'account_*_journey.json',
            'account_*_events.csv',
            'account_*_report.md'
        ]):
            print(f"✅ Journey files verified")
        else:
            print(f"⚠️  Some journey files missing")
            tests_failed += 1
    else:
        tests_failed += 1
    
    # ========================================================================
    # TEST 2: KPI Generator Wrapper
    # ========================================================================
    
    if run_command(
        cmd=[
            'python3', 'wizard_kpi_generator.py',
            '--input-dir', output_dir,
            '--output-dir', output_dir
        ],
        description='Test 2: KPI Generator Wrapper',
        timeout=300
    ):
        tests_passed += 1
        
        # Verify KPI files
        if verify_files(output_dir, [
            'account_*_kpis.csv',
            'all_accounts_kpis.csv',
            'kpi_metadata.json'
        ]):
            print(f"✅ KPI files verified")
        else:
            print(f"⚠️  Some KPI files missing")
            tests_failed += 1
    else:
        tests_failed += 1
    
    # ========================================================================
    # TEST 3: Milestone Generator Wrapper
    # ========================================================================
    
    if run_command(
        cmd=[
            'python3', 'wizard_milestone_generator.py',
            '--data-dir', output_dir,
            '--output-dir', processed_dir
        ],
        description='Test 3: Milestone Generator Wrapper',
        timeout=300
    ):
        tests_passed += 1
        
        # Verify milestone files
        if verify_files(processed_dir, [
            'account_*_milestones.csv',
            'all_accounts_milestones.csv'
        ]):
            print(f"✅ Milestone files verified")
        else:
            print(f"⚠️  Some milestone files missing")
            tests_failed += 1
    else:
        tests_failed += 1
    
    # ========================================================================
    # SUMMARY
    # ========================================================================
    
    print()
    print("="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Tests Passed: {tests_passed}")
    print(f"Tests Failed: {tests_failed}")
    print()
    
    if tests_failed == 0:
        print("✅ ALL TESTS PASSED!")
        print()
        print("Next steps:")
        print("1. Review generated files in: " + test_dir)
        print("2. If everything looks good, integrate with Wizard A")
        print("3. Test with larger datasets (10, 20, 50 accounts)")
        print()
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        print()
        print("Troubleshooting:")
        print("1. Check that all scripts are in the correct location")
        print("2. Verify sys.path.insert() paths in wrapper scripts")
        print("3. Ensure journey_pattern_generator.py is accessible")
        print("4. Review error messages above")
        print()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
