#!/usr/bin/env python3
"""
Provision New Data Center Customer from Template
================================================

Creates a new customer directory structure by copying from _template
and replacing placeholders with customer-specific values.

Usage:
    python3 provision_dc_customer.py --customer-id 18
    python3 provision_dc_customer.py --customer-id 18 --customer-name "Acme Corp"
    python3 provision_dc_customer.py --customer-id 18 --dry-run
    python3 provision_dc_customer.py --customer-id 18 --force

This will create:
    backend/verticals/customer18-dc2_s/
    
And replace placeholders:
    - {CUSTOMER_ID} → 18
    - {CUSTOMER_NAME} → Acme Corp (or Customer 18)
    - {VERTICAL_SLUG} → dc2_s
    - {ACCOUNT_ID_START} → 18000 (formula: 10000 + customer_id * 1000)
    - customer9 → customer18
    - 90001, 90002, etc. → 18001, 18002, etc. (account ID mapping)

Template Location:
    backend/verticals/_template/
    
Version: 2.0
Updated: January 2026
"""

import argparse
import shutil
import os
import re
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# ============================================================
# CONFIGURATION
# ============================================================

# Base directory (where this script lives) - use absolute path
BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = BASE_DIR / "_template"
VERTICALS_DIR = BASE_DIR

# Template base customer ID (the customer ID used in _template files)
TEMPLATE_CUSTOMER_ID = 9
TEMPLATE_ACCOUNT_ID_START = 90000  # Template uses 90001, 90002, etc.

# Text file extensions to process for placeholder replacement
TEXT_EXTENSIONS = {
    '.py', '.md', '.txt', '.sh', '.sql', '.json', '.yaml', '.yml', '.csv',
    '.html', '.tsx', '.ts', '.jsx', '.js', '.env', '.cfg', '.ini', '.toml',
    '.xml', '.conf', '.properties', '.gitignore'
}

# Extensions/directories to skip entirely
SKIP_EXTENSIONS = {'.pyc', '.pyo', '.pyd', '.so', '.db', '.sqlite', '.lock', '.xlsx', '.xls', '.pdf', '.png', '.jpg', '.jpeg', '.gif', '.ico'}
SKIP_DIRS = {'__pycache__', '.git', '.DS_Store', 'node_modules', '.venv', 'venv', '.idea', '.vscode'}

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def calculate_account_id_start(customer_id: int) -> int:
    """
    Calculate starting account ID using formula: 10000 + customer_id * 1000
    
    Examples:
        Customer 9  → 19000 (accounts 19001-19999)
        Customer 17 → 27000 (accounts 27001-27999)
        Customer 18 → 28000 (accounts 28001-28999)
    """
    return 10000 + customer_id * 1000


def map_account_id(old_account_id: int, old_base: int, new_base: int) -> int:
    """
    Map an account ID from old customer to new customer.
    
    Example: 90001 (base 90000) → 18001 (base 18000)
    """
    offset = old_account_id - old_base
    return new_base + offset


def replace_placeholders(
    content: str, 
    customer_id: int, 
    customer_name: str,
    vertical_slug: str, 
    account_id_start: int
) -> Tuple[str, int]:
    """
    Replace placeholders in file content.
    Returns (modified_content, replacement_count)
    """
    replacement_count = 0
    result = content
    
    # Standard placeholder replacements
    standard_replacements = {
        '{CUSTOMER_ID}': str(customer_id),
        '{CUSTOMER_NAME}': customer_name,
        '{VERTICAL_SLUG}': vertical_slug,
        '{ACCOUNT_ID_START}': str(account_id_start),
        '{ACCOUNT_ID_END}': str(account_id_start + 999),
        '{TIMESTAMP}': datetime.now().isoformat(),
    }
    
    for placeholder, value in standard_replacements.items():
        if placeholder in result:
            replacement_count += result.count(placeholder)
            result = result.replace(placeholder, value)
    
    # Replace template customer references (customer9 → customerN)
    template_customer_patterns = [
        (f'customer{TEMPLATE_CUSTOMER_ID}', f'customer{customer_id}'),
        (f'Customer {TEMPLATE_CUSTOMER_ID}', f'Customer {customer_id}'),
        (f'CUSTOMER {TEMPLATE_CUSTOMER_ID}', f'CUSTOMER {customer_id}'),
        (f'CUSTOMER{TEMPLATE_CUSTOMER_ID}', f'CUSTOMER{customer_id}'),
        (f'customer_{TEMPLATE_CUSTOMER_ID}', f'customer_{customer_id}'),
    ]
    
    for old, new in template_customer_patterns:
        if old in result:
            replacement_count += result.count(old)
            result = result.replace(old, new)
    
    # Replace account IDs (90001 → 18001, 90002 → 18002, etc.)
    # Use regex to find all account IDs in the template range
    account_id_pattern = re.compile(r'\b(9000[1-9]|900[1-9]\d|90[1-9]\d{2}|9[1-9]\d{3})\b')
    
    def replace_account_id(match):
        old_id = int(match.group(1))
        # Only replace if it's in the template account range (90001-90999)
        if TEMPLATE_ACCOUNT_ID_START < old_id <= TEMPLATE_ACCOUNT_ID_START + 999:
            new_id = map_account_id(old_id, TEMPLATE_ACCOUNT_ID_START, account_id_start)
            return str(new_id)
        return match.group(0)
    
    new_result, count = account_id_pattern.subn(replace_account_id, result)
    if count > 0:
        replacement_count += count
        result = new_result
    
    return result, replacement_count


def should_process_file(file_path: Path) -> bool:
    """Check if file should be processed (skip binary files, etc.)"""
    
    # Skip binary/compiled files
    if file_path.suffix.lower() in SKIP_EXTENSIONS:
        return False
    
    # Skip specific directories
    if any(skip_dir in file_path.parts for skip_dir in SKIP_DIRS):
        return False
    
    # Allow specific hidden files
    allowed_hidden = {'.gitignore', '.env', '.env.example', '.editorconfig'}
    
    # Skip other hidden files/dirs
    for part in file_path.parts:
        if part.startswith('.') and part not in allowed_hidden:
            return False
    
    return True


def is_text_file(file_path: Path) -> bool:
    """Check if file should be processed as text (for placeholder replacement)"""
    return file_path.suffix.lower() in TEXT_EXTENSIONS or file_path.name in {'.gitignore', '.env', '.env.example'}


def copy_and_replace_file(
    src: Path, 
    dst: Path, 
    customer_id: int, 
    customer_name: str,
    vertical_slug: str, 
    account_id_start: int,
    dry_run: bool = False
) -> Tuple[bool, int]:
    """
    Copy file and replace placeholders.
    Returns (success, replacement_count)
    """
    if dry_run:
        # In dry-run mode, just check if file has replacements
        if is_text_file(src):
            try:
                content = src.read_text(encoding='utf-8', errors='ignore')
                _, count = replace_placeholders(content, customer_id, customer_name, vertical_slug, account_id_start)
                return True, count
            except:
                return True, 0
        return True, 0
    
    # Create destination directory if needed
    dst.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        if is_text_file(src):
            # Text file - replace placeholders
            content = src.read_text(encoding='utf-8', errors='ignore')
            content, count = replace_placeholders(content, customer_id, customer_name, vertical_slug, account_id_start)
            dst.write_text(content, encoding='utf-8')
            return True, count
        else:
            # Binary file - copy as-is
            shutil.copy2(src, dst)
            return True, 0
    except Exception as e:
        logger.warning(f"Could not process {src.name}: {e}")
        # Fallback to binary copy
        try:
            shutil.copy2(src, dst)
            return True, 0
        except Exception as e2:
            logger.error(f"Error copying {src.name}: {e2}")
            return False, 0


def validate_template() -> Tuple[bool, List[str]]:
    """
    Validate that _template directory exists and has expected structure.
    Returns (is_valid, list_of_issues)
    """
    issues = []
    
    if not TEMPLATE_DIR.exists():
        issues.append(f"Template directory not found: {TEMPLATE_DIR}")
        return False, issues
    
    # Check for expected directories
    expected_dirs = ['data', 'scripts', 'services']
    for dir_name in expected_dirs:
        if not (TEMPLATE_DIR / dir_name).exists():
            issues.append(f"Missing expected directory: _template/{dir_name}/")
    
    # Check for at least some files
    file_count = sum(1 for _ in TEMPLATE_DIR.rglob('*') if _.is_file())
    if file_count < 5:
        issues.append(f"Template has very few files ({file_count}). Is it complete?")
    
    return len(issues) == 0, issues


def provision_customer(
    customer_id: int, 
    customer_name: Optional[str] = None,
    vertical_slug: str = 'dc2_s',
    dry_run: bool = False,
    force: bool = False
) -> bool:
    """
    Provision new customer directory from template.
    
    Args:
        customer_id: Unique customer identifier
        customer_name: Human-readable customer name (optional)
        vertical_slug: Vertical identifier (default: dc2_s)
        dry_run: If True, show what would happen without making changes
        force: If True, skip confirmation prompts
    
    Returns:
        True if successful, False otherwise
    """
    
    # Validate template
    is_valid, issues = validate_template()
    if not is_valid:
        for issue in issues:
            logger.error(issue)
        return False
    
    if issues:  # Warnings
        for issue in issues:
            logger.warning(issue)
    
    # Calculate values
    account_id_start = calculate_account_id_start(customer_id)
    customer_name = customer_name or f"Customer {customer_id}"
    customer_dir_name = f"customer{customer_id}-{vertical_slug}"
    customer_dir = VERTICALS_DIR / customer_dir_name
    
    # Check for existing directory
    if customer_dir.exists():
        file_count = sum(1 for _ in customer_dir.rglob('*') if _.is_file())
        
        if dry_run:
            print(f"⚠️  [DRY-RUN] Directory exists: {customer_dir_name}/ ({file_count} files)")
            print(f"   Would need to delete and recreate")
            return True
        
        print(f"⚠️  Customer directory already exists: {customer_dir_name}/ ({file_count} files)")
        
        if not force:
            response = input("Delete and recreate? (yes/no): ")
            if response.lower() != 'yes':
                print("Aborted.")
                return False
        
        shutil.rmtree(customer_dir)
        print(f"   ✅ Deleted existing directory")
    
    # Print header
    mode = "[DRY-RUN] " if dry_run else ""
    print()
    print("=" * 80)
    print(f"{mode}PROVISIONING CUSTOMER {customer_id} ({vertical_slug})")
    print("=" * 80)
    print()
    print(f"  Template:         {TEMPLATE_DIR}")
    print(f"  Destination:      {customer_dir}")
    print(f"  Customer ID:      {customer_id}")
    print(f"  Customer Name:    {customer_name}")
    print(f"  Vertical:         {vertical_slug}")
    print(f"  Account ID Range: {account_id_start + 1} - {account_id_start + 999}")
    print()
    
    # Copy directory structure
    print(f"📁 {'Analyzing' if dry_run else 'Copying'} directory structure...")
    
    stats = {
        'files_total': 0,
        'files_copied': 0,
        'files_with_replacements': 0,
        'total_replacements': 0,
        'errors': 0,
        'skipped': 0
    }
    
    for root, dirs, files in os.walk(TEMPLATE_DIR):
        # Filter out directories to skip
        dirs[:] = [d for d in dirs if should_process_file(Path(root) / d)]
        
        for file in files:
            src_file = Path(root) / file
            stats['files_total'] += 1
            
            if not should_process_file(src_file):
                stats['skipped'] += 1
                continue
            
            # Calculate relative path
            rel_path = src_file.relative_to(TEMPLATE_DIR)
            
            # Replace customer9 in filename/path with customer{N}
            rel_path_str = str(rel_path)
            if f'customer{TEMPLATE_CUSTOMER_ID}' in rel_path_str:
                rel_path_str = rel_path_str.replace(f'customer{TEMPLATE_CUSTOMER_ID}', f'customer{customer_id}')
                rel_path = Path(rel_path_str)
            
            dst_file = customer_dir / rel_path
            
            # Copy and replace
            success, replacement_count = copy_and_replace_file(
                src_file, dst_file, 
                customer_id, customer_name, vertical_slug, account_id_start,
                dry_run=dry_run
            )
            
            if success:
                stats['files_copied'] += 1
                if replacement_count > 0:
                    stats['files_with_replacements'] += 1
                    stats['total_replacements'] += replacement_count
            else:
                stats['errors'] += 1
    
    # Print stats
    action = "Would copy" if dry_run else "Copied"
    print(f"   ✅ {action} {stats['files_copied']} files")
    print(f"   ✅ {stats['files_with_replacements']} files with placeholder replacements")
    print(f"   ✅ {stats['total_replacements']} total replacements made")
    if stats['skipped'] > 0:
        print(f"   ⏭️  Skipped {stats['skipped']} files (binary/cache)")
    if stats['errors'] > 0:
        print(f"   ❌ {stats['errors']} errors")
    print()
    
    # Summary
    print("=" * 80)
    status = "PREVIEW COMPLETE" if dry_run else "PROVISIONING COMPLETE!"
    print(f"✅ {status}")
    print("=" * 80)
    print()
    
    if not dry_run:
        print(f"Created: {customer_dir_name}/")
        print()
        print("📋 Next Steps:")
        print(f"  1. Upload 5 input CSV files to {customer_dir_name}/data/")
        print(f"     - accounts.csv")
        print(f"     - kpi_measurements.csv (or kpis.csv)")
        print(f"     - qualitative_signals.csv (or signals.csv)")
        print(f"     - products.csv")
        print(f"     - profiles.csv (or account_profiles.csv)")
        print()
        print(f"  2. Load data:")
        print(f"     cd {customer_dir_name}/scripts")
        print(f"     python3 02_load_customer{customer_id}_data_SMART.py")
        print()
        print(f"  3. Create embeddings:")
        print(f"     python3 03_embed_customer{customer_id}_OPENAI.py")
        print()
        print(f"  4. Generate journey data (Wizard A):")
        print(f"     cd ../journey/wizard_a")
        print(f"     python3 wizard_a_journey_generator.py")
        print()
        print(f"  5. Create user in database:")
        print(f"     python3 create_customer{customer_id}_user.py")
        print()
    else:
        print("To provision for real, run without --dry-run flag")
    
    # Log to file
    log_file = VERTICALS_DIR / "provisioning.log"
    with open(log_file, 'a') as f:
        f.write(f"{datetime.now().isoformat()} | ")
        f.write(f"{'DRY-RUN' if dry_run else 'PROVISIONED'} | ")
        f.write(f"customer_id={customer_id} | ")
        f.write(f"customer_name={customer_name} | ")
        f.write(f"vertical={vertical_slug} | ")
        f.write(f"files={stats['files_copied']} | ")
        f.write(f"replacements={stats['total_replacements']}\n")
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description='Provision new Data Center customer from _template',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview what would happen (recommended first step)
  python3 provision_dc_customer.py --customer-id 18 --dry-run
  
  # Provision with default settings
  python3 provision_dc_customer.py --customer-id 18
  
  # Provision with custom name
  python3 provision_dc_customer.py --customer-id 18 --customer-name "Acme Corp"
  
  # Force overwrite existing (for CI/CD)
  python3 provision_dc_customer.py --customer-id 18 --force

Account ID Formula:
  account_id_start = 10000 + customer_id * 1000
  
  Customer 17 → accounts 27001-27999
  Customer 18 → accounts 28001-28999
  Customer 19 → accounts 29001-29999
        """
    )
    
    parser.add_argument(
        '--customer-id',
        type=int,
        required=True,
        help='Customer ID (e.g., 18). Must be unique.'
    )
    parser.add_argument(
        '--customer-name',
        type=str,
        default=None,
        help='Customer name (e.g., "Acme Corp"). Defaults to "Customer N".'
    )
    parser.add_argument(
        '--vertical-slug',
        type=str,
        default='dc2_s',
        help='Vertical slug (default: dc2_s)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview what would happen without making changes'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Skip confirmation prompts (for automation)'
    )
    
    args = parser.parse_args()
    
    # Validate customer ID
    if args.customer_id < 1:
        print("❌ Error: Customer ID must be positive")
        exit(1)
    
    if args.customer_id > 9999:
        print("❌ Error: Customer ID must be less than 10000 (account ID overflow)")
        exit(1)
    
    success = provision_customer(
        customer_id=args.customer_id,
        customer_name=args.customer_name,
        vertical_slug=args.vertical_slug,
        dry_run=args.dry_run,
        force=args.force
    )
    
    exit(0 if success else 1)


if __name__ == "__main__":
    main()
