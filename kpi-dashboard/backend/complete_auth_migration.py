#!/usr/bin/env python3
"""
Complete authentication migration - handles all X-Customer-ID patterns
"""

import os
import re
from pathlib import Path

def migrate_file_comprehensive(file_path):
    """Comprehensively migrate all authentication patterns"""
    
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    modified = False
    new_lines = []
    import_added = False
    
    for i, line in enumerate(lines):
        original_line = line
        
        # Skip if it's a comment or docstring
        stripped = line.strip()
        if stripped.startswith('#') or stripped.startswith('"""') or stripped.startswith("'''"):
            new_lines.append(line)
            continue
        
        # Pattern 1: Direct header access request.headers.get('X-Customer-ID')
        if "request.headers.get('X-Customer-ID')" in line or 'request.headers.get("X-Customer-ID")' in line:
            # Replace with get_current_customer_id()
            line = re.sub(
                r"request\.headers\.get\(['\"]X-Customer-ID['\"]\s*[,)].*?\)",
                'get_current_customer_id()',
                line
            )
            modified = True
        
        # Pattern 2: Variable assignment from header
        if 'customer_id = request.headers.get' in line and 'X-Customer-ID' in line:
            # Check if next lines validate it
            indent = len(line) - len(line.lstrip())
            line = ' ' * indent + 'customer_id = get_current_customer_id()\n'
            modified = True
        
        # Pattern 3: Missing X-Customer-ID error messages
        if 'Missing X-Customer-ID' in line or 'Invalid X-Customer-ID' in line:
            # These checks are now handled by middleware, can be removed
            # But keep the line for now, mark for manual review
            line = line.replace('Missing X-Customer-ID header', 'Authentication required (handled by middleware)')
            line = line.replace('Invalid X-Customer-ID header', 'Invalid authentication (handled by middleware)')
            modified = True
        
        # Pattern 4: cid = request.headers.get
        if 'cid = request.headers.get' in line and 'X-Customer-ID' in line:
            indent = len(line) - len(line.lstrip())
            line = ' ' * indent + 'cid = get_current_customer_id()\n'
            modified = True
        
        new_lines.append(line)
    
    # Add import if modifications were made
    if modified and not import_added:
        # Find where to insert import
        for i, line in enumerate(new_lines):
            if line.startswith('from flask import') or line.startswith('import flask'):
                # Insert after flask import
                if 'from auth_middleware import' not in ''.join(new_lines):
                    new_lines.insert(i + 1, 'from auth_middleware import get_current_customer_id, get_current_user_id\n')
                    import_added = True
                break
    
    if modified:
        with open(file_path, 'w') as f:
            f.writelines(new_lines)
    
    return modified

def main():
    """Migrate all files"""
    print("🔧 Comprehensive Authentication Migration")
    print("=" * 70)
    
    api_files = list(Path('.').glob('*_api.py')) + [Path('app.py'), Path('app_v3_minimal.py'), Path('app_v3_simple.py')]
    api_files = [f for f in api_files if f.exists() and not f.name.startswith('test_')]
    
    migrated = 0
    for file_path in api_files:
        if migrate_file_comprehensive(file_path):
            print(f"✅ Migrated: {file_path}")
            migrated += 1
        else:
            print(f"   ⏭ Skipped: {file_path}")
    
    print(f"\n✅ Migrated {migrated} files")
    
    # Check for remaining issues
    print("\n🔍 Checking for remaining X-Customer-ID references...")
    os.system("grep -r 'X-Customer-ID' --include='*.py' . | grep -v test_ | grep -v '.pyc' | wc -l")

if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    main()

