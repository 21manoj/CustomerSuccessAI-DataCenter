#!/usr/bin/env python3
"""
Wizard A - Journey Generator Wrapper
====================================

Wraps journey_pattern_generator.py to handle multiple accounts.
Your original script stays unchanged!

Usage:
    python wizard_journey_generator.py \
        --accounts 50 \
        --start-id 293000 \
        --pattern-mix '{"crisis":0.2,"churn":0.15,"stable":0.4,"expansion":0.25}' \
        --output-dir outputs/wizard_runs/run_001
"""

import sys
import os
import json
import argparse
import random
from datetime import datetime
from pathlib import Path

# Import from your existing Phase 1 script
# Adjust path based on where journey_pattern_generator.py is located
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../scripts/phase1'))

try:
    from journey_pattern_generator import (
        JourneyPatternGenerator,
        export_journey_to_json,
        export_journey_to_csv,
        generate_journey_report
    )
except ImportError as e:
    print(f"❌ Error importing journey_pattern_generator.py")
    print(f"   Make sure the path is correct in sys.path.insert()")
    print(f"   Error: {e}")
    sys.exit(1)


def select_pattern_from_mix(pattern_mix):
    """
    Select pattern based on probability distribution
    
    Args:
        pattern_mix: Dict like {"crisis": 0.2, "churn": 0.15, "stable": 0.4, "expansion": 0.25}
    
    Returns:
        Pattern type string
    """
    rand = random.random()
    cumulative = 0.0
    
    # Normalize if doesn't sum to 1.0
    total = sum(pattern_mix.values())
    normalized = {k: v/total for k, v in pattern_mix.items()}
    
    for pattern, prob in normalized.items():
        cumulative += prob
        if rand < cumulative:
            return pattern
    
    # Fallback to expansion (stable pattern)
    return 'expansion'


def map_pattern_to_generator(pattern, generator):
    """
    Map user-friendly pattern names to generator methods
    
    Checks which methods actually exist in the generator and maps accordingly.
    
    Patterns:
        - crisis: Crisis-recovery journey (crisis_recovery)
        - churn: Ignored churn journey (ignored_churn)
        - stable: Maps to available method (proactive_growth if exists, else crisis_recovery)
        - expansion: Maps to available method (proactive_growth if exists, else crisis_recovery)
    """
    # Check what methods the generator actually has
    has_proactive_growth = hasattr(generator, 'generate_proactive_growth_journey')
    has_crisis_recovery = hasattr(generator, 'generate_crisis_recovery_journey')
    has_ignored_churn = hasattr(generator, 'generate_ignored_churn_journey')
    
    # Base mapping
    mapping = {
        'crisis': 'crisis_recovery' if has_crisis_recovery else None,
        'churn': 'ignored_churn' if has_ignored_churn else None,
    }
    
    # For stable and expansion, use proactive_growth if available, else use crisis_recovery
    if has_proactive_growth:
        mapping['stable'] = 'proactive_growth'
        mapping['expansion'] = 'proactive_growth'
    elif has_crisis_recovery:
        # Fallback to crisis_recovery for stable/expansion if proactive_growth doesn't exist
        mapping['stable'] = 'crisis_recovery'
        mapping['expansion'] = 'crisis_recovery'
        print(f"⚠️  Warning: 'proactive_growth' method not found, using 'crisis_recovery' for stable/expansion patterns")
    
    return mapping.get(pattern, 'crisis_recovery' if has_crisis_recovery else None)


def generate_accounts_batch(num_accounts, pattern_mix, start_id, output_dir, progress_callback=None):
    """
    Generate multiple accounts with pattern distribution
    
    Args:
        num_accounts: Number of accounts to generate (e.g., 50)
        pattern_mix: Dict of pattern probabilities (e.g., {"crisis": 0.2, "churn": 0.15, ...})
        start_id: Starting account ID (e.g., 293000)
        output_dir: Output directory for files
        progress_callback: Optional function(current, total) for progress updates
    
    Returns:
        List of generated journey data
    """
    
    print("="*70)
    print("WIZARD A - JOURNEY GENERATOR")
    print("="*70)
    print(f"Accounts: {num_accounts}")
    print(f"Starting ID: {start_id}")
    print(f"Pattern Mix: {pattern_mix}")
    print(f"Output: {output_dir}")
    print()
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize generator
    generator = JourneyPatternGenerator()
    
    # Track statistics
    pattern_counts = {p: 0 for p in pattern_mix.keys()}
    generated_journeys = []
    
    # Generate each account
    for i in range(num_accounts):
        account_id = start_id + i
        
        # Select pattern for this account
        pattern = select_pattern_from_mix(pattern_mix)
        pattern_counts[pattern] += 1
        
        # Map to generator method (pass generator to check available methods)
        generator_method = map_pattern_to_generator(pattern, generator)
        
        if generator_method is None:
            print(f"❌ Error: No suitable generator method found for pattern '{pattern}'")
            print(f"   Available methods: {[m for m in dir(generator) if m.startswith('generate_') and m.endswith('_journey')]}")
            continue
        
        # Generate journey based on pattern
        if generator_method == 'crisis_recovery':
            journey = generator.generate_crisis_recovery_journey(
                account_id=str(account_id),
                account_name=f"Account {account_id}",
                start_date=datetime(2024, 1, 1),
                total_weeks=52
            )
        elif generator_method == 'ignored_churn':
            journey = generator.generate_ignored_churn_journey(
                account_id=str(account_id),
                account_name=f"Account {account_id}",
                start_date=datetime(2024, 1, 1),
                total_weeks=52
            )
        elif generator_method == 'proactive_growth':
            journey = generator.generate_proactive_growth_journey(
                account_id=str(account_id),
                account_name=f"Account {account_id}",
                start_date=datetime(2024, 1, 1),
                total_weeks=52
            )
        else:
            print(f"⚠️  Warning: Unknown generator method '{generator_method}', skipping account {account_id}")
            continue
        
        # Export files
        journey_file = os.path.join(output_dir, f"account_{account_id}_journey.json")
        events_file = os.path.join(output_dir, f"account_{account_id}_events.csv")
        report_file = os.path.join(output_dir, f"account_{account_id}_report.md")
        
        export_journey_to_json(journey, journey_file)
        export_journey_to_csv(journey, events_file)
        generate_journey_report(journey, report_file)
        
        generated_journeys.append(journey)
        
        # Progress update
        progress = ((i + 1) / num_accounts) * 100
        print(f"✅ [{i+1:3d}/{num_accounts}] Account {account_id} ({pattern:10s}) - "
              f"Health: {journey.starting_health:.1f}→{journey.ending_health:.1f}, "
              f"Events: {len(journey.events)}")
        
        if progress_callback:
            progress_callback(i + 1, num_accounts)
    
    print()
    print("="*70)
    print("✅ JOURNEY GENERATION COMPLETE!")
    print("="*70)
    print(f"Total accounts: {num_accounts}")
    print(f"Output directory: {output_dir}")
    print()
    print("Pattern distribution:")
    for pattern, count in pattern_counts.items():
        percentage = (count / num_accounts) * 100
        print(f"  {pattern:10s}: {count:3d} accounts ({percentage:5.1f}%)")
    print()
    
    return generated_journeys


def main():
    parser = argparse.ArgumentParser(
        description='Generate multiple customer journey accounts for Wizard A'
    )
    parser.add_argument('--accounts', type=int, required=True,
                       help='Number of accounts to generate (e.g., 50)')
    parser.add_argument('--start-id', type=int, default=293000,
                       help='Starting account ID (default: 293000)')
    parser.add_argument('--pattern-mix', type=str, required=True,
                       help='JSON string with pattern probabilities (e.g., {"crisis":0.2,"churn":0.15,"stable":0.4,"expansion":0.25})')
    parser.add_argument('--output-dir', required=True,
                       help='Output directory for generated files')
    
    args = parser.parse_args()
    
    # Parse pattern mix
    try:
        pattern_mix = json.loads(args.pattern_mix)
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing pattern-mix JSON: {e}")
        example_json = '{"crisis":0.2,"churn":0.15,"stable":0.4,"expansion":0.25}'
        print(f"   Example: --pattern-mix '{example_json}'")
        sys.exit(1)
    
    # Validate pattern mix
    valid_patterns = ['crisis', 'churn', 'stable', 'expansion']
    for pattern in pattern_mix.keys():
        if pattern not in valid_patterns:
            print(f"❌ Invalid pattern: {pattern}")
            print(f"   Valid patterns: {', '.join(valid_patterns)}")
            sys.exit(1)
    
    # Generate accounts
    try:
        generate_accounts_batch(
            num_accounts=args.accounts,
            pattern_mix=pattern_mix,
            start_id=args.start_id,
            output_dir=args.output_dir
        )
    except Exception as e:
        print(f"❌ Error during generation: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
