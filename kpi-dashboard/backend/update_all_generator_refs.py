#!/usr/bin/env python3
"""
Automatically update generator references
"""

import re
import os

TEST_FILES = [
    "test_onboarding_complete_e2e_api_v2.py",
    "test_customer19_e2e_onboarding.py",
    "test_onboarding_complete_e2e_api.py",
    "test_onboarding_complete_e2e.py",
    "test_onboarding_e2e_new_customer.py",
]

def update_file(filepath):
    """Update generator references in a file"""
    
    if not os.path.exists(filepath):
        print(f"⚠️  {filepath} not found")
        return False
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Backup
    with open(f"{filepath}.backup", 'w') as f:
        f.write(content)
    
    # Replace import
    content = re.sub(
        r'from generate_synthetic_customer_data import EnhancedSyntheticDataGenerator',
        'import subprocess\nimport os',
        content
    )
    
    # Add note for manual update
    if 'EnhancedSyntheticDataGenerator' in content:
        print(f"⚠️  {filepath}: Manual update needed for r calls")
    
    # Write back
    with open(filepath, 'w') as f:
        f.write(content)
    
    print(f"✅ {filepath} updated (imports)")
    return True

def main():
    print("Updating generator references...\n")
    
    for test_file in TEST_FILES:
        update_file(test_file)
    
    print("\n" + "="*70)
    print("NEXT STEPS:")
    print("="*70)
    print("1. Review each test file")
    print("2. Find: generator = EnhancedSyntheticDataGenerator(...)")
    print("3. Replace with subprocess.run(['python3', 'scripts/generate_synthetic_dc2s_data.py', ...])")
    print("4. Test each file individually")
    print()

if __name__ == '__main__':
    main()
