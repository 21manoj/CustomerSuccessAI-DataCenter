#!/usr/bin/env python3
"""
CS Pulse DC2_S Schema Alignment Fix
Based on ACTUAL models.py schema (DC2SKPI and QualitativeSignal)
"""

import sys
from pathlib import Path
import re


def fix_generator_kpis(content):
    """Fix KPI measurement column names in generator"""
    changes = []
    
    # Fix 1: measurement_month → measured_at
    if "'measurement_month':" in content or '"measurement_month":' in content:
        content = content.replace("'measurement_month':", "'measured_at':")
        content = content.replace('"measurement_month":', '"measured_at":')
        changes.append("'measurement_month' → 'measured_at'")
    
    # Fix 2: target_value → target
    if "'target_value':" in content or '"target_value":' in content:
        content = content.replace("'target_value':", "'target':")
        content = content.replace('"target_value":', '"target":')
        changes.append("'target_value' → 'target'")
    
    # Fix 3: health_state → status
    if "'health_state':" in content or '"health_state":' in content:
        content = content.replace("'health_state':", "'status':")
        content = content.replace('"health_state":', '"status":')
        changes.append("'health_state' → 'status'")
    
    # Fix 4: Remove unit, threshold_breached columns (commented out for safety)
    # You may need to manually remove these from the generator
    if "'unit':" in content or '"unit":' in content:
        changes.append("⚠️  'unit' column found - consider removing (not in DB)")
    
    if "'threshold_breached':" in content or '"threshold_breached":' in content:
        changes.append("⚠️  'threshold_breached' column found - consider removing (not in DB)")
    
    return content, changes


def fix_generator_signals(content):
    """Fix signal column names in generator"""
    changes = []
    
    # Fix 1: signal_text → content
    if "'signal_text':" in content or '"signal_text":' in content:
        # Be careful to only replace in signal context
        content = re.sub(
            r"('signal_text':|\"signal_text\":)",
            "'content':",
            content
        )
        changes.append("'signal_text' → 'content'")
    
    # Fix 2: Remove customer_id from signals
    # Look for signals.append({ ... 'customer_id': ... })
    if "signals.append({" in content and "'customer_id':" in content:
        changes.append("⚠️  'customer_id' in signals - should be removed (not in DB)")
        # Comment it out rather than delete
        content = re.sub(
            r"(\s+)'customer_id':\s*[^,\n]+,?\n",
            r"\1# 'customer_id': removed - not in qualitative_signals table\n",
            content
        )
    
    # Fix 3: Add signal_id generation if missing
    if "signals.append({" in content and "'signal_id':" not in content:
        changes.append("⚠️  Missing 'signal_id' - must be added (required PK)")
        # Can't auto-fix this - needs manual intervention
    
    return content, changes


def fix_loader_kpis(content):
    """Fix KPI loader column references"""
    changes = []
    
    # Fix 1: row['measurement_month'] → row['measured_at']
    if "row['measurement_month']" in content or 'row["measurement_month"]' in content:
        content = content.replace("row['measurement_month']", "row['measured_at']")
        content = content.replace('row["measurement_month"]', 'row["measured_at"]')
        changes.append("row['measurement_month'] → row['measured_at']")
    
    # Fix 2: row['target_value'] → row['target']
    if "row['target_value']" in content or 'row["target_value"]' in content:
        content = content.replace("row['target_value']", "row['target']")
        content = content.replace('row["target_value"]', 'row["target"]')
        changes.append("row['target_value'] → row['target']")
    
    # Fix 3: row['health_state'] → row['status']
    if "row['health_state']" in content or 'row["health_state"]' in content:
        content = content.replace("row['health_state']", "row['status']")
        content = content.replace('row["health_state"]', 'row["status"]')
        changes.append("row['health_state'] → row['status']")
    
    return content, changes


def fix_loader_signals(content):
    """Fix signal loader column references"""
    changes = []
    
    # Fix 1: row['signal_text'] → row['content']
    # But check for model field assignment
    if "row['signal_text']" in content or 'row["signal_text"]' in content:
        # Change signal_text=row['signal_text'] to content=row['content']
        content = re.sub(
            r"signal_text\s*=\s*row\['signal_text'\]",
            "content=row['content']",
            content
        )
        content = re.sub(
            r'signal_text\s*=\s*row\["signal_text"\]',
            'content=row["content"]',
            content
        )
        changes.append("signal_text=row['signal_text'] → content=row['content']")
    
    # Fix 2: Remove customer_id reads
    if "row['customer_id']" in content:
        changes.append("⚠️  row['customer_id'] found - should be removed (not in CSV/DB)")
    
    # Fix 3: Check for signal_id
    if "signal_id=row['signal_id']" not in content:
        changes.append("⚠️  signal_id assignment missing - must be added")
    
    return content, changes


def fix_script(script_path, script_type):
    """Fix a script (generator or loader)"""
    print(f"\n{'='*70}")
    print(f"FIXING: {script_path}")
    print(f"Type: {script_type}")
    print(f"{'='*70}")
    
    if not script_path.exists():
        print(f"❌ File not found: {script_path}")
        return False
    
    with open(script_path, 'r') as f:
        content = f.read()
    
    original_content = content
    all_changes = []
    
    # Apply fixes based on script type
    if script_type == 'generator':
        content, kpi_changes = fix_generator_kpis(content)
        all_changes.extend(kpi_changes)
        
        content, signal_changes = fix_generator_signals(content)
        all_changes.extend(signal_changes)
        
    elif script_type == 'loader':
        content, kpi_changes = fix_loader_kpis(content)
        all_changes.extend(kpi_changes)
        
        content, signal_changes = fix_loader_signals(content)
        all_changes.extend(signal_changes)
    
    if content != original_content:
        # Backup original
        backup_path = script_path.with_suffix('.py.backup_dc2s')
        with open(backup_path, 'w') as f:
            f.write(original_content)
        print(f"✅ Created backup: {backup_path.name}")
        
        # Write fixed version
        with open(script_path, 'w') as f:
            f.write(content)
        
        print(f"✅ Applied {len(all_changes)} fixes:")
        for change in all_changes:
            print(f"   {change}")
        
        return True
    else:
        print(f"ℹ️  No changes needed")
        return True


def main():
    """Run DC2_S schema alignment fix"""
    print("\n" + "="*70)
    print("CS PULSE DC2_S SCHEMA ALIGNMENT FIX")
    print("Based on actual models.py (DC2SKPI, QualitativeSignal)")
    print("="*70)
    print("\nThis script will fix:")
    print("1. KPI columns: measurement_month→measured_at, target_value→target, health_state→status")
    print("2. Signal columns: signal_text→content, remove customer_id, add signal_id")
    print("\nBackups will be created before any changes.")
    
    input("\nPress Enter to continue...")
    
    results = {}
    
    # Fix generator
    generator_path = Path('backend/scripts/generate_synthetic_customer_data.py')
    if generator_path.exists():
        results['generator'] = fix_script(generator_path, 'generator')
    else:
        print(f"\n⚠️  Generator not found: {generator_path}")
    
    # Fix loader template
    loader_template = Path('backend/verticals/_template/scripts/02_load_customer9_data_SMART.py')
    if loader_template.exists():
        results['loader_template'] = fix_script(loader_template, 'loader')
    
    # Fix Customer 19 loader
    loader_19 = Path('backend/verticals/customer19-dc2_s/scripts/02_load_customer19_data_SMART.py')
    if loader_19.exists():
        results['loader_19'] = fix_script(loader_19, 'loader')
    
    # Summary
    print(f"\n{'='*70}")
    print(f"FIX SUMMARY")
    print(f"{'='*70}")
    
    for component, success in results.items():
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"{status}: {component}")
    
    all_pass = all(results.values())
    
    if all_pass:
        print(f"\n🎉 Schema alignment fixes applied!")
        print(f"\n⚠️  IMPORTANT MANUAL STEPS:")
        print(f"\n1. In generator, ADD signal_id generation:")
        print(f"   signal_id = f'sig_{{account_id}}_{{signal_index:04d}}'")
        print(f"\n2. In generator, REMOVE customer_id from signals.append({{...}})")
        print(f"\n3. In generator, REMOVE 'unit' and 'threshold_breached' from KPIs")
        print(f"\n4. Verify date format is 'YYYY-MM-DD' (not 'YYYY-MM')")
        print(f"\n5. Delete old CSVs and regenerate:")
        print(f"   rm -rf backend/verticals/customer19-dc2_s/data/*.csv")
        print(f"   # Then call /api/onboarding/complete")
        print(f"\n6. Re-run test: python3 test_e2e_customer19.py")
        return 0
    else:
        print(f"\n⚠️  Some fixes failed - review output above")
        return 1


if __name__ == '__main__':
    sys.exit(main())
