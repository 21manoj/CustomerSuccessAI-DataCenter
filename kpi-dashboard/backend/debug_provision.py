#!/usr/bin/env python3
"""Debug provision script to see why files aren't being copied"""

import sys
from pathlib import Path
from verticals.provision_dc_customer import provision_customer, TEMPLATE_DIR, BASE_DIR
import os

print("="*70)
print("PROVISION DEBUG")
print("="*70)

print(f"\nBASE_DIR: {BASE_DIR}")
print(f"BASE_DIR absolute: {BASE_DIR.resolve()}")
print(f"TEMPLATE_DIR: {TEMPLATE_DIR}")
print(f"TEMPLATE_DIR absolute: {TEMPLATE_DIR.resolve()}")
print(f"TEMPLATE_DIR exists: {TEMPLATE_DIR.exists()}")

# Check template structure
if TEMPLATE_DIR.exists():
    print(f"\nTemplate directory contents:")
    for item in sorted(TEMPLATE_DIR.iterdir()):
        if item.is_dir():
            print(f"  📁 {item.name}/")
        else:
            print(f"  📄 {item.name}")
    
    scripts_dir = TEMPLATE_DIR / 'scripts'
    if scripts_dir.exists():
        print(f"\nScripts directory exists: {scripts_dir}")
        py_files = list(scripts_dir.glob('*.py'))
        print(f"Python files in scripts: {len(py_files)}")
        for f in py_files[:5]:
            print(f"  - {f.name}")

# Test provision
print("\n" + "="*70)
print("TESTING PROVISION")
print("="*70)

# Clean up test customer first
test_customer_dir = BASE_DIR / "customer999-dc2_s"
if test_customer_dir.exists():
    import shutil
    shutil.rmtree(test_customer_dir)
    print(f"Cleaned up {test_customer_dir}")

# Run provision
print("\nRunning provision_customer...")
result = provision_customer(
    customer_id=999,
    customer_name="Test Customer 999",
    vertical_slug="dc2_s",
    dry_run=False,
    force=True
)

print(f"\nProvision result: {result}")

# Check what was created
if test_customer_dir.exists():
    print(f"\nCreated directory: {test_customer_dir}")
    print(f"Contents:")
    for item in sorted(test_customer_dir.iterdir()):
        if item.is_dir():
            file_count = len(list(item.rglob('*')))
            print(f"  📁 {item.name}/ ({file_count} items)")
        else:
            print(f"  📄 {item.name}")
    
    scripts_dir = test_customer_dir / 'scripts'
    if scripts_dir.exists():
        print(f"\nScripts directory exists!")
        py_files = list(scripts_dir.glob('*.py'))
        print(f"Python files: {len(py_files)}")
        for f in py_files[:5]:
            print(f"  - {f.name}")
    else:
        print(f"\n❌ Scripts directory does NOT exist!")
else:
    print(f"\n❌ Customer directory was NOT created!")
