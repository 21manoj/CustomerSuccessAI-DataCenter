#!/usr/bin/env python3
"""
Comprehensive frontend authentication migration
Handles all X-Customer-ID patterns
"""

import os
import re
from pathlib import Path

def migrate_file(file_path):
    """Comprehensively migrate a TypeScript file"""
    
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    new_lines = []
    modified = False
    i = 0
    
    while i < len(lines):
        line = lines[i]
        original_line = line
        
        # Skip empty lines and comments
        if line.strip().startswith('//'):
            new_lines.append(line)
            i += 1
            continue
        
        # Pattern 1: Single-line X-Customer-ID header
        if "'X-Customer-ID'" in line or '"X-Customer-ID"' in line:
            # Remove this entire line if it's just the header
            if line.strip().endswith(','):
                # Skip this line entirely
                modified = True
                i += 1
                continue
            else:
                # Remove the X-Customer-ID part only
                line = re.sub(r"['\"]X-Customer-ID['\"]\s*:\s*[^,}]+,?\s*", '', line)
                modified = True
        
        # Pattern 2: Add credentials to fetch if headers exist but no X-Customer-ID
        if 'fetch(' in line and i + 1 < len(lines):
            # Look ahead for headers object
            fetch_block = ''.join(lines[i:min(i+20, len(lines))])
            
            if 'headers:' in fetch_block and 'credentials' not in fetch_block and '/api/' in fetch_block:
                # This fetch call needs credentials
                # Find the closing of the options object
                for j in range(i, min(i+15, len(lines))):
                    if '}' in lines[j] and 'headers:' in ''.join(lines[i:j+1]):
                        # Check if this is the end of the options object
                        if lines[j].strip() in ['});', '})']:
                            # Add credentials before the closing brace
                            indent = len(lines[j]) - len(lines[j].lstrip())
                            new_line = ' ' * (indent - 2) + "credentials: 'include',\n"
                            lines.insert(j, new_line)
                            modified = True
                            break
        
        new_lines.append(line)
        i += 1
    
    if modified:
        with open(file_path, 'w') as f:
            f.writelines(new_lines)
        return True
    
    return False


def remove_all_customer_headers():
    """Remove all X-Customer-ID headers using sed-like approach"""
    
    src_dir = Path('./src')
    files = list(src_dir.rglob('*.tsx')) + list(src_dir.rglob('*.ts'))
    
    print(f"Removing X-Customer-ID from {len(files)} files...")
    
    migrated = 0
    for file_path in files:
        if migrate_file(file_path):
            print(f"  ✅ {file_path.relative_to(src_dir)}")
            migrated += 1
    
    print(f"\n✅ Migrated {migrated} files")
    return migrated


if __name__ == '__main__':
    os.chdir('/Users/manojgupta/kpi-dashboard')
    migrated = remove_all_customer_headers()
    
    # Check for remaining
    print("\n🔍 Checking for remaining X-Customer-ID...")
    os.system("grep -r 'X-Customer-ID' src/ --include='*.tsx' --include='*.ts' | wc -l")

