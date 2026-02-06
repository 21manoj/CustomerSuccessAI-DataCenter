#!/usr/bin/env python3
"""
cleanup_dc_imports.py
Removes remaining _dc import statements and any missed _dc files
Run AFTER cleanup_dc_files.py: python cleanup_dc_imports.py
"""

import os
import re
from datetime import datetime

class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'

def remove_dc_imports_from_file(file_path):
    """Remove _dc import statements from a file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        original_lines = len(lines)
        modified = False
        new_lines = []
        removed_imports = []
        
        for line in lines:
            # Check if line imports something with _dc
            if re.search(r'(from|import).*_dc', line):
                removed_imports.append(line.strip())
                # Comment out the line instead of removing (safer)
                new_lines.append(f"# REMOVED BY CLEANUP: {line}")
                modified = True
            else:
                new_lines.append(line)
        
        if modified:
            # Create backup
            backup_path = f"{file_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            
            # Write cleaned file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            
            return True, removed_imports, backup_path
        
        return False, [], None
    
    except Exception as e:
        print(f"{Colors.RED}Error processing {file_path}: {e}{Colors.NC}")
        return False, [], None

def find_remaining_dc_files():
    """Find any _dc files that weren't in the original cleanup list"""
    dc_files = []
    for root, dirs, files in os.walk("backend"):
        dirs[:] = [d for d in dirs if d != '__pycache__']
        for file in files:
            if '_dc' in file and file.endswith('.py'):
                dc_files.append(os.path.join(root, file))
    return dc_files

def main():
    print("🧹 Phase 2: Cleaning up _dc imports and missed files...")
    print()
    
    if not os.path.isdir("backend"):
        print(f"{Colors.RED}❌ Error: Must run from project root{Colors.NC}")
        return 1
    
    # Step 1: Find remaining _dc files
    print(f"{Colors.YELLOW}📂 Searching for remaining _dc files...{Colors.NC}")
    remaining_dc_files = find_remaining_dc_files()
    
    if remaining_dc_files:
        print(f"{Colors.RED}⚠️  Found {len(remaining_dc_files)} _dc files that weren't removed:{Colors.NC}")
        for file in remaining_dc_files:
            print(f"  - {file}")
        print()
        
        choice = input(f"{Colors.YELLOW}Delete these files? (y/n): {Colors.NC}").strip().lower()
        if choice == 'y':
            for file in remaining_dc_files:
                try:
                    os.remove(file)
                    print(f"{Colors.GREEN}✅ Removed: {file}{Colors.NC}")
                except Exception as e:
                    print(f"{Colors.RED}❌ Error removing {file}: {e}{Colors.NC}")
        print()
    else:
        print(f"{Colors.GREEN}✅ No remaining _dc files found{Colors.NC}")
        print()
    
    # Step 2: Clean up import statements
    print(f"{Colors.YELLOW}🔍 Searching for _dc imports...{Colors.NC}")
    print()
    
    files_to_clean = []
    for root, dirs, files in os.walk("backend"):
        dirs[:] = [d for d in dirs if d != '__pycache__']
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if re.search(r'(from|import).*_dc', content):
                            files_to_clean.append(file_path)
                except Exception:
                    pass
    
    if files_to_clean:
        print(f"{Colors.YELLOW}Found _dc imports in {len(files_to_clean)} files:{Colors.NC}")
        for file in files_to_clean:
            print(f"  - {file}")
        print()
        
        choice = input(f"{Colors.YELLOW}Clean these imports? (y/n): {Colors.NC}").strip().lower()
        if choice != 'y':
            print("Cleanup cancelled.")
            return 0
        
        print()
        total_cleaned = 0
        total_imports_removed = 0
        
        for file_path in files_to_clean:
            modified, removed_imports, backup_path = remove_dc_imports_from_file(file_path)
            if modified:
                total_cleaned += 1
                total_imports_removed += len(removed_imports)
                print(f"{Colors.GREEN}✅ Cleaned: {file_path}{Colors.NC}")
                print(f"   Removed {len(removed_imports)} import(s):")
                for imp in removed_imports:
                    print(f"   - {imp}")
                if backup_path:
                    print(f"   Backup: {backup_path}")
                print()
        
        print("═══════════════════════════════════════════")
        print(f"{Colors.GREEN}✨ Import Cleanup Complete!{Colors.NC}")
        print("═══════════════════════════════════════════")
        print(f"Files cleaned: {Colors.GREEN}{total_cleaned}{Colors.NC}")
        print(f"Imports removed: {Colors.GREEN}{total_imports_removed}{Colors.NC}")
        print()
        
    else:
        print(f"{Colors.GREEN}✅ No _dc imports found!{Colors.NC}")
        print()
    
    # Step 3: Final verification
    print(f"{Colors.BLUE}🔍 Final verification...{Colors.NC}")
    
    final_dc_files = find_remaining_dc_files()
    final_dc_imports = []
    
    for root, dirs, files in os.walk("backend"):
        dirs[:] = [d for d in dirs if d != '__pycache__']
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        for line_num, line in enumerate(f, 1):
                            if re.search(r'(from|import).*_dc', line) and not line.strip().startswith('#'):
                                final_dc_imports.append((file_path, line_num, line.strip()))
                except Exception:
                    pass
    
    if final_dc_files:
        print(f"{Colors.RED}⚠️  Still found {len(final_dc_files)} _dc files{Colors.NC}")
    else:
        print(f"{Colors.GREEN}✅ No _dc files remaining{Colors.NC}")
    
    if final_dc_imports:
        print(f"{Colors.RED}⚠️  Still found {len(final_dc_imports)} _dc imports (uncommented){Colors.NC}")
        for file, line_num, line in final_dc_imports[:5]:  # Show first 5
            print(f"   {file}:{line_num} - {line}")
    else:
        print(f"{Colors.GREEN}✅ No _dc imports remaining{Colors.NC}")
    
    print()
    print(f"{Colors.GREEN}🎉 Cleanup complete!{Colors.NC}")
    print()
    print("📋 Next steps:")
    print("1. Test your application: python backend/app.py")
    print("2. Check for any runtime errors")
    print("3. Review commented-out imports in .backup files if needed")
    print("4. Remove .backup files once everything works")
    
    return 0

if __name__ == "__main__":
    exit(main())
