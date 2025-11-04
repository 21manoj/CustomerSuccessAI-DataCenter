#!/usr/bin/env python3
"""
Migrate API files from header-based to session-based authentication
"""

import os
import re
from pathlib import Path

def migrate_api_file(file_path):
    """Migrate a single API file"""
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    original_content = content
    changes = []
    
    # Pattern 1: Replace get_customer_id() function definition
    pattern1 = re.compile(
        r"def get_customer_id\(\):.*?return request\.headers\.get\('X-Customer-ID'.*?\)",
        re.DOTALL
    )
    if pattern1.search(content):
        content = pattern1.sub('', content)
        changes.append("Removed get_customer_id() function")
    
    # Pattern 2: Add import for get_current_customer_id at top of file
    if 'from auth_middleware import' not in content and 'get_current_customer_id' not in content:
        # Find the imports section
        import_match = re.search(r'(from flask import.*?\n)', content)
        if import_match:
            insert_pos = import_match.end()
            content = (content[:insert_pos] + 
                      'from auth_middleware import get_current_customer_id, get_current_user_id\n' +
                      content[insert_pos:])
            changes.append("Added auth_middleware import")
    
    # Pattern 3: Replace get_customer_id() calls with get_current_customer_id()
    content = content.replace('get_customer_id()', 'get_current_customer_id()')
    if 'get_customer_id()' in original_content:
        changes.append("Replaced get_customer_id() calls")
    
    # Pattern 4: Replace direct header access
    pattern4 = re.compile(r"request\.headers\.get\(['\"]X-Customer-ID['\"]\s*,\s*type=int\s*(,\s*default=\d+)?\)")
    if pattern4.search(content):
        content = pattern4.sub('get_current_customer_id()', content)
        changes.append("Replaced X-Customer-ID header access")
    
    # Pattern 5: Replace X-User-ID header access
    pattern5 = re.compile(r"request\.headers\.get\(['\"]X-User-ID['\"]\s*,\s*type=int\s*(,\s*default=\d+)?\)")
    if pattern5.search(content):
        content = pattern5.sub('get_current_user_id()', content)
        changes.append("Replaced X-User-ID header access")
    
    # Only save if changes were made
    if content != original_content:
        with open(file_path, 'w') as f:
            f.write(content)
        return True, changes
    
    return False, []


def find_api_files():
    """Find all API files that need migration"""
    backend_dir = Path('.')
    api_files = []
    
    for file_path in backend_dir.glob('*_api.py'):
        api_files.append(file_path)
    
    # Also check app files
    for app_file in ['app.py', 'app_v3_minimal.py', 'app_v3_simple.py']:
        if Path(app_file).exists():
            api_files.append(Path(app_file))
    
    return api_files


def main():
    """Main migration function"""
    print("=" * 70)
    print("API AUTHENTICATION MIGRATION SCRIPT")
    print("=" * 70)
    
    api_files = find_api_files()
    
    print(f"\nFound {len(api_files)} API files to migrate:")
    for f in api_files:
        print(f"  • {f}")
    
    print("\n" + "=" * 70)
    response = input("Proceed with migration? (yes/no): ")
    
    if response.lower() != 'yes':
        print("Migration cancelled.")
        return
    
    print("\n🔧 Migrating API files...")
    
    migrated_count = 0
    total_changes = 0
    
    for file_path in api_files:
        modified, changes = migrate_api_file(file_path)
        
        if modified:
            migrated_count += 1
            total_changes += len(changes)
            print(f"\n✅ Migrated: {file_path}")
            for change in changes:
                print(f"   • {change}")
        else:
            print(f"   ⏭  Skipped: {file_path} (no changes needed)")
    
    print("\n" + "=" * 70)
    print(f"✅ MIGRATION COMPLETE")
    print("=" * 70)
    print(f"  Files migrated: {migrated_count}/{len(api_files)}")
    print(f"  Total changes: {total_changes}")
    print("\n⚠️  IMPORTANT:")
    print("  1. Review all changes manually")
    print("  2. Test each API endpoint")
    print("  3. Check for any remaining X-Customer-ID references")
    print("  4. Run: grep -r 'X-Customer-ID' backend/")


if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    main()

