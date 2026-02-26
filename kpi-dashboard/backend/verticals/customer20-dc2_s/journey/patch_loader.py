#!/usr/bin/env python3
"""
Quick patcher for load_journey_data_phase4.py
Fixes the load_journey_account function to work with actual JSON structure
"""

import sys

# The fixed function
FIXED_FUNCTION = '''def load_journey_account(session, journey_data):
    """Load account metadata into journey_accounts table"""
    
    account_sql = text("""
        INSERT INTO journey_accounts (
            account_name, external_account_id, pattern_type, description,
            arr, start_date, end_date, total_weeks, total_events,
            starting_health, ending_health, health_change,
            final_outcome, outcome_arr_impact, total_csm_investment
        ) VALUES (
            :account_name, :external_account_id, :pattern_type, :description,
            :arr, :start_date, :end_date, :total_weeks, :total_events,
            :starting_health, :ending_health, :health_change,
            :final_outcome, :arr_impact, :csm_investment
        )
        RETURNING journey_account_id
    """)
    
    # Extract data from actual JSON structure
    events = journey_data.get('events', [])
    summary = journey_data.get('summary', {})
    
    # Parse financial impact string to extract ARR impact
    financial_impact = summary.get('financial_impact', '')
    arr_impact = 0
    if 'expansion' in financial_impact.lower():
        # Extract percentage if present (e.g., "40% ARR expansion")
        import re
        match = re.search(r'(\\d+)%', financial_impact)
        if match:
            arr_impact = int(match.group(1))
    elif 'churn' in financial_impact.lower() or 'lost' in financial_impact.lower():
        arr_impact = -100  # Churn
    
    # Get CSM investment from summary
    csm_investment = summary.get('total_csm_investment', 0)
    
    # Calculate health change
    starting_health = journey_data.get('starting_health', 0)
    ending_health = journey_data.get('ending_health', 0)
    health_change = ending_health - starting_health
    
    # Determine final outcome based on health change and financial impact
    if arr_impact > 0:
        final_outcome = 'expansion'
    elif arr_impact < 0:
        final_outcome = 'churn'
    elif health_change > 20:
        final_outcome = 'growth'
    elif health_change < -20:
        final_outcome = 'declined'
    else:
        final_outcome = 'stable'
    
    # Execute insert
    result = session.execute(account_sql, {
        'account_name': journey_data.get('account_name', ''),
        'external_account_id': journey_data.get('account_id', ''),
        'pattern_type': journey_data.get('pattern_type', ''),
        'description': journey_data.get('pattern_type', '').replace('_', ' ').title(),
        'arr': None,  # Not available in this JSON structure
        'start_date': datetime.strptime(journey_data.get('start_date', '2024-01-01'), '%Y-%m-%d'),
        'end_date': datetime.strptime(journey_data.get('end_date', '2024-12-31'), '%Y-%m-%d'),
        'total_weeks': journey_data.get('total_weeks', 0),
        'total_events': len(events),
        'starting_health': starting_health,
        'ending_health': ending_health,
        'health_change': health_change,
        'final_outcome': final_outcome,
        'arr_impact': arr_impact,
        'csm_investment': csm_investment
    })
    
    journey_account_id = result.scalar()
    return journey_account_id
'''

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 patch_loader.py <path_to_load_journey_data_phase4.py>")
        sys.exit(1)
    
    filepath = sys.argv[1]
    
    # Read the file
    with open(filepath, 'r') as f:
        lines = f.readlines()
    
    # Find the function
    start_idx = None
    end_idx = None
    
    for i, line in enumerate(lines):
        if line.strip().startswith('def load_journey_account('):
            start_idx = i
        elif start_idx is not None and line.strip().startswith('def ') and i > start_idx:
            end_idx = i
            break
    
    if start_idx is None:
        print("❌ Could not find load_journey_account function")
        sys.exit(1)
    
    if end_idx is None:
        print("❌ Could not find end of function")
        sys.exit(1)
    
    print(f"✅ Found function at lines {start_idx+1} to {end_idx}")
    
    # Backup
    backup_path = filepath + '.backup'
    with open(backup_path, 'w') as f:
        f.writelines(lines)
    print(f"✅ Created backup: {backup_path}")
    
    # Replace function
    new_lines = lines[:start_idx] + [FIXED_FUNCTION + '\n\n'] + lines[end_idx:]
    
    with open(filepath, 'w') as f:
        f.writelines(new_lines)
    
    print(f"✅ Patched {filepath}")
    print("\nYou can now re-run the load script!")

if __name__ == '__main__':
    main()
