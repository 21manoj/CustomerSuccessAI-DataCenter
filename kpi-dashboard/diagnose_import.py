#!/usr/bin/env python3
"""
DC2_S Import Diagnostic Script
Run this to identify import issues
"""

import os
import sys

def check_environment():
    """Check Python environment and directory structure"""
    print("=" * 60)
    print("DC2_S IMPORT DIAGNOSTIC")
    print("=" * 60)
    print()
    
    # 1. Current directory
    print("1. Current Directory:")
    print(f"   {os.getcwd()}")
    print()
    
    # 2. Python version
    print("2. Python Version:")
    print(f"   {sys.version}")
    print()
    
    # 3. Python path
    print("3. Python Path:")
    for i, p in enumerate(sys.path[:5], 1):
        print(f"   {i}. {p}")
    print()
    
    # 4. Check for backend directory
    print("4. Directory Structure:")
    if os.path.exists('backend'):
        print("   ✅ backend/ exists")
        
        if os.path.exists('backend/verticals'):
            print("   ✅ backend/verticals/ exists")
            
            if os.path.exists('backend/verticals/__init__.py'):
                print("   ✅ backend/verticals/__init__.py exists")
            else:
                print("   ❌ backend/verticals/__init__.py MISSING")
                print("      Run: touch backend/verticals/__init__.py")
            
            if os.path.exists('backend/verticals/dc2_s'):
                print("   ✅ backend/verticals/dc2_s/ exists")
                
                # Check for files
                required_files = [
                    '__init__.py',
                    'kpi_definitions.py',
                    'pillar_weights.py',
                    'vertical_config.py',
                    'metadata_schema.py'
                ]
                
                print("\n5. Required Files:")
                all_present = True
                for file in required_files:
                    path = f'backend/verticals/dc2_s/{file}'
                    if os.path.exists(path):
                        size = os.path.getsize(path)
                        print(f"   ✅ {file} ({size:,} bytes)")
                    else:
                        print(f"   ❌ {file} MISSING")
                        all_present = False
                
                if not all_present:
                    print("\n   ERROR: Some files are missing!")
                    print("   Make sure you copied all 5 files to backend/verticals/dc2_s/")
                    return False
                    
            else:
                print("   ❌ backend/verticals/dc2_s/ MISSING")
                print("      Run: mkdir -p backend/verticals/dc2_s")
                return False
        else:
            print("   ❌ backend/verticals/ MISSING")
            print("      Run: mkdir -p backend/verticals/dc2_s")
            return False
    else:
        print("   ❌ backend/ MISSING")
        print("      Are you in the right directory?")
        print("      You should be in: /path/to/kpi-dashboard/")
        return False
    
    print()
    return True

def test_imports():
    """Test various import scenarios"""
    print("=" * 60)
    print("IMPORT TESTS")
    print("=" * 60)
    print()
    
    # Add backend to path
    backend_path = os.path.join(os.getcwd(), 'backend')
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
        print(f"Added to sys.path: {backend_path}")
        print()
    
    tests = [
        ("Import verticals package", "import verticals"),
        ("Import dc2_s package", "from verticals import dc2_s"),
        ("Import kpi_definitions module", "from verticals.dc2_s import kpi_definitions"),
        ("Import DC2S_KPIS", "from verticals.dc2_s.kpi_definitions import DC2S_KPIS"),
        ("Import from __init__", "from verticals.dc2_s import DC2S_KPIS"),
        ("Count KPIs", "from verticals.dc2_s import DC2S_KPIS; print(f'  Found {len(DC2S_KPIS)} KPIs')")
    ]
    
    for i, (description, code) in enumerate(tests, 1):
        print(f"Test {i}: {description}")
        try:
            exec(code)
            print("   ✅ SUCCESS")
        except Exception as e:
            print(f"   ❌ FAILED: {type(e).__name__}: {e}")
            if i < len(tests):
                print("   Stopping tests (fix this error first)")
                return False
        print()
    
    return True

def main():
    """Run all diagnostics"""
    
    # Check environment
    if not check_environment():
        print()
        print("=" * 60)
        print("FIX THE ISSUES ABOVE AND RUN THIS SCRIPT AGAIN")
        print("=" * 60)
        return 1
    
    # Test imports
    if not test_imports():
        print()
        print("=" * 60)
        print("FIX THE IMPORT ERRORS ABOVE")
        print("=" * 60)
        return 1
    
    # Success!
    print("=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("=" * 60)
    print()
    print("Your DC2_S vertical is correctly installed!")
    print()
    print("Next steps:")
    print("1. Try: python3 -c \"from verticals.dc2_s import DC2S_KPIS; print(f'Loaded {len(DC2S_KPIS)} KPIs')\"")
    print("2. Create your first DC2_S account (see WEEK1_INTEGRATION_GUIDE.md)")
    print()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
