#!/usr/bin/env python3
"""
Migrate frontend from header-based to cookie-based authentication
"""

import os
import re
from pathlib import Path

def migrate_tsx_file(file_path):
    """Migrate a single TypeScript/TSX file"""
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    original_content = content
    changes = []
    
    # Pattern 1: Remove X-Customer-ID header from fetch calls
    # Match: 'X-Customer-ID': sessionStorage.getItem('customer_id')
    pattern1 = re.compile(r"['\"]X-Customer-ID['\"]\s*:\s*sessionStorage\.getItem\(['\"]customer_id['\"]\)\s*,?\s*\n?", re.MULTILINE)
    if pattern1.search(content):
        content = pattern1.sub('', content)
        changes.append("Removed X-Customer-ID header")
    
    # Pattern 2: Remove X-User-ID header
    pattern2 = re.compile(r"['\"]X-User-ID['\"]\s*:\s*sessionStorage\.getItem\(['\"]user_id['\"]\)\s*,?\s*\n?", re.MULTILINE)
    if pattern2.search(content):
        content = pattern2.sub('', content)
        changes.append("Removed X-User-ID header")
    
    # Pattern 3: Add credentials: 'include' to fetch calls that don't have it
    # Find fetch calls
    fetch_pattern = re.compile(r"fetch\((.*?)\{(.*?)\}", re.DOTALL)
    
    def add_credentials(match):
        url_part = match.group(1)
        options_part = match.group(2)
        
        # Check if credentials already exists
        if 'credentials' in options_part:
            return match.group(0)  # No change needed
        
        # Check if this is an API call
        if '/api/' not in url_part and '/api/' not in options_part:
            return match.group(0)  # Not an API call
        
        # Add credentials: 'include'
        # Find the end of the options object
        options_cleaned = options_part.rstrip()
        if options_cleaned.endswith(','):
            new_options = options_part + "\n      credentials: 'include'"
        else:
            new_options = options_part + ",\n      credentials: 'include'"
        
        return f"fetch({url_part}{{{new_options}}}"
    
    new_content = fetch_pattern.sub(add_credentials, content)
    if new_content != content:
        content = new_content
        changes.append("Added credentials: 'include' to fetch calls")
    
    # Pattern 4: Remove empty headers objects
    # Match: headers: { }
    pattern4 = re.compile(r"headers:\s*\{\s*\},?\s*\n?", re.MULTILINE)
    if pattern4.search(content):
        content = pattern4.sub('', content)
        changes.append("Removed empty headers objects")
    
    # Pattern 5: Clean up trailing commas in objects
    pattern5 = re.compile(r",\s*\n\s*\}", re.MULTILINE)
    content = pattern5.sub('\n    }', content)
    
    # Save if changes were made
    if content != original_content:
        with open(file_path, 'w') as f:
            f.write(content)
        return True, changes
    
    return False, []


def find_frontend_files():
    """Find all frontend TypeScript/TSX files"""
    src_dir = Path('../src')
    if not src_dir.exists():
        src_dir = Path('./src')
    
    files = []
    for ext in ['*.tsx', '*.ts']:
        files.extend(src_dir.rglob(ext))
    
    return files


def main():
    """Main migration function"""
    print("=" * 70)
    print("FRONTEND AUTHENTICATION MIGRATION")
    print("=" * 70)
    
    files = find_frontend_files()
    
    print(f"\nFound {len(files)} TypeScript files:")
    for f in files:
        print(f"  • {f}")
    
    print("\n" + "=" * 70)
    response = input("Proceed with migration? (yes/no): ")
    
    if response.lower() != 'yes':
        print("Migration cancelled.")
        return
    
    print("\n🔧 Migrating frontend files...")
    
    migrated_count = 0
    total_changes = 0
    
    for file_path in files:
        modified, changes = migrate_tsx_file(file_path)
        
        if modified:
            migrated_count += 1
            total_changes += len(changes)
            print(f"\n✅ Migrated: {file_path.name}")
            for change in changes:
                print(f"   • {change}")
        else:
            print(f"   ⏭  No changes: {file_path.name}")
    
    print("\n" + "=" * 70)
    print(f"✅ FRONTEND MIGRATION COMPLETE")
    print("=" * 70)
    print(f"  Files migrated: {migrated_count}/{len(files)}")
    print(f"  Total changes: {total_changes}")
    
    print("\n📋 Next steps:")
    print("  1. Review changes manually")
    print("  2. Test login/logout in browser")
    print("  3. Rebuild frontend: npm run build")
    print("  4. Check for remaining issues:")
    print("     grep -r 'X-Customer-ID' src/")


if __name__ == '__main__':
    main()

