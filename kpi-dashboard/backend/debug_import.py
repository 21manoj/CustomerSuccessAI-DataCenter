#!/usr/bin/env python3
"""
Debug script to find the exact import issue
Run from backend directory
"""

import os
import sys

print("=" * 70)
print("DETAILED IMPORT DEBUG")
print("=" * 70)
print()

# 1. Current working directory
print("1. Current Directory:")
print(f"   {os.getcwd()}")
print()

# 2. Check if verticals directory exists
print("2. Checking verticals directory:")
if os.path.exists('verticals'):
    print("   ✅ verticals/ exists")
    
    if os.path.exists('verticals/__init__.py'):
        print("   ✅ verticals/__init__.py exists")
        size = os.path.getsize('verticals/__init__.py')
        print(f"      Size: {size} bytes")
    else:
        print("   ❌ verticals/__init__.py MISSING")
    
    if os.path.exists('verticals/dc2_s'):
        print("   ✅ verticals/dc2_s/ exists")
        
        # List files
        files = os.listdir('verticals/dc2_s')
        print(f"      Files: {files}")
        
        if '__init__.py' in files:
            print("   ✅ verticals/dc2_s/__init__.py exists")
            size = os.path.getsize('verticals/dc2_s/__init__.py')
            print(f"      Size: {size} bytes")
        else:
            print("   ❌ verticals/dc2_s/__init__.py MISSING")
    else:
        print("   ❌ verticals/dc2_s/ MISSING")
else:
    print("   ❌ verticals/ MISSING")
    print("   ERROR: You're not in the backend directory!")
    sys.exit(1)

print()

# 3. Check Python can see verticals as a module
print("3. Testing if Python can find verticals:")
try:
    import verticals
    print(f"   ✅ import verticals succeeded")
    print(f"      Location: {verticals.__file__}")
except ImportError as e:
    print(f"   ❌ import verticals failed: {e}")
    print()
    print("   Trying to add current dir to path...")
    sys.path.insert(0, os.getcwd())
    try:
        import verticals
        print(f"   ✅ NOW it works after adding to path")
        print(f"      Location: {verticals.__file__}")
    except ImportError as e2:
        print(f"   ❌ Still failed: {e2}")

print()

# 4. Check Python path
print("4. Python sys.path:")
for i, p in enumerate(sys.path[:8], 1):
    marker = "  👈 backend dir" if p == os.getcwd() else ""
    print(f"   {i}. {p}{marker}")

print()

# 5. Try direct import of kpi_definitions
print("5. Testing direct file import:")
try:
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "kpi_definitions",
        "verticals/dc2_s/kpi_definitions.py"
    )
    kpi_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(kpi_module)
    print(f"   ✅ Direct import works")
    print(f"      Found {len(kpi_module.DC2S_KPIS)} KPIs")
except Exception as e:
    print(f"   ❌ Direct import failed: {e}")

print()

# 6. Check for __pycache__ issues
print("6. Checking for cache issues:")
pycache_dirs = []
for root, dirs, files in os.walk('verticals'):
    if '__pycache__' in dirs:
        pycache_dirs.append(os.path.join(root, '__pycache__'))

if pycache_dirs:
    print(f"   ⚠️  Found {len(pycache_dirs)} __pycache__ directories:")
    for d in pycache_dirs:
        print(f"      {d}")
    print("   Consider deleting these: find verticals -name '__pycache__' -type d -exec rm -rf {} +")
else:
    print("   ✅ No __pycache__ directories found")

print()

# 7. Final import test
print("7. Final import test:")
print("   Attempting: from verticals.dc2_s import DC2S_KPIS")
try:
    from verticals.dc2_s import DC2S_KPIS
    print(f"   ✅✅✅ SUCCESS! Loaded {len(DC2S_KPIS)} KPIs")
except ImportError as e:
    print(f"   ❌ Failed: {e}")
    print()
    print("   DIAGNOSIS:")
    print("   The verticals directory exists and has __init__.py")
    print("   But Python still can't import it as a package")
    print()
    print("   SOLUTION: Add current directory to PYTHONPATH")
    print("   Run this command:")
    print("   export PYTHONPATH=\"$(pwd):$PYTHONPATH\"")
    print("   Then try the import again")
except Exception as e:
    print(f"   ❌ Other error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 70)
