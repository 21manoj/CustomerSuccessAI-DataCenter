#!/usr/bin/env python3
"""
Milestone Generator for Phase 4
================================

Generates training milestone labels from journey data.
These milestones are the ground truth for training Signal Analyst.

Usage:
    python generate_milestones_phase4.py
"""

import json
import csv
import os
import argparse
from datetime import datetime, timedelta


# ============================================================================
# MILESTONE DEFINITIONS
# ============================================================================

MILESTONE_TYPES = {
    # Expansion milestones
    "expansion_capacity_alert": "System capacity approaching limits (>85%)",
    "expansion_inquiry": "Customer inquires about expansion options",
    "expansion_quote_sent": "Sales team sends expansion quote",
    "expansion_budget_approved": "CFO/Finance approves expansion budget",
    "expansion_decision_approved": "Customer approves expansion",
    "expansion_contract_signed": "Expansion contract signed",
    
    # Churn milestones
    "churn_early_warning": "First churn risk signals detected",
    "churn_risk_elevated": "Churn risk escalated to at-risk status",
    "churn_escalation": "Account escalated to leadership/war room",
    "churn_intervention": "Active intervention (executive engagement)",
    "churn_decision": "Customer decides to churn",
    "churn_contract_terminated": "Contract officially terminated",
    
    # Recovery milestones
    "crisis_detected": "Crisis event detected (outage, major issue)",
    "recovery_initiated": "Recovery plan initiated",
    "recovery_milestone": "Significant recovery progress",
    "recovery_complete": "Account fully recovered",
    
    # Health milestones
    "health_critical": "Health score drops below 50",
    "health_at_risk": "Health score drops to 50-70 range",
    "health_good": "Health score returns to 70-85 range",
    "health_excellent": "Health score reaches 85+ range",
    
    # Business review milestones
    "qbr_positive": "Quarterly Business Review with positive sentiment",
    "qbr_negative": "QBR with concerns or negative sentiment",
    "executive_engagement": "C-suite executive engagement"
}


# ============================================================================
# MILESTONE EXTRACTION FUNCTIONS
# ============================================================================

def extract_milestones_from_journey(journey_data, kpis_file):
    """Extract milestone events from journey data"""
    
    milestones = []
    account_id = journey_data['account_id']
    pattern_type = journey_data['pattern_type']
    events = journey_data['events']
    
    # Load KPI data for context
    kpi_data = {}
    with open(kpis_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            week = int(row['week_number'])
            kpi_data[week] = row
    
    # Pattern-specific milestone extraction
    if pattern_type == 'crisis_recovery':
        milestones.extend(extract_crisis_recovery_milestones(account_id, events, kpi_data))
    elif pattern_type == 'ignored_churn':
        milestones.extend(extract_churn_milestones(account_id, events, kpi_data))
    elif pattern_type == 'proactive_growth':
        milestones.extend(extract_expansion_milestones(account_id, events, kpi_data))
    
    return milestones


def extract_crisis_recovery_milestones(account_id, events, kpi_data):
    """Extract milestones from crisis-recovery journey"""
    
    milestones = []
    
    for event in events:
        week = event['week_number']
        date = event['date']
        event_type = event['event_type']
        phase = event['phase']
        health = event.get('health_score_after', 0)
        
        # Crisis detection
        if event_type == 'outage' and phase == 'crisis':
            milestones.append({
                'week_number': week,
                'milestone_date': date,
                'milestone_type': 'crisis_detected',
                'milestone_outcome': 'crisis_active',
                'leading_indicators': [
                    f"Major outage event: {event.get('description', '')}",
                    f"Health dropped to {health}",
                    f"Phase: {phase}"
                ],
                'arr_impact': 0,  # No immediate ARR impact
                'confidence_at_time': 0.95,
                'primary_drivers': [
                    {'driver': 'Production outage', 'weight': 0.70},
                    {'driver': 'Health score drop', 'weight': 0.30}
                ],
                'signal_breakdown': {
                    'event_type': event_type,
                    'sentiment': event.get('sentiment_value', 0),
                    'health_impact': event.get('health_impact', 0)
                }
            })
        
        # Recovery initiated (war room convened)
        if event.get('csm_action_type') == 'war_room':
            milestones.append({
                'week_number': week,
                'milestone_date': date,
                'milestone_type': 'recovery_initiated',
                'milestone_outcome': 'war_room_active',
                'leading_indicators': [
                    "War room convened",
                    f"CSM investment: ${event.get('csm_action_cost', 0):,.0f}",
                    f"Response time: {event.get('csm_response_time_hours', 0)} hours"
                ],
                'arr_impact': 0,
                'confidence_at_time': 0.80,
                'primary_drivers': [
                    {'driver': 'CSM intervention', 'weight': 0.60},
                    {'driver': 'Executive engagement', 'weight': 0.40}
                ]
            })
        
        # Recovery milestone (health improving)
        if phase == 'recovery' and health > 70:
            week_kpis = kpi_data.get(week, {})
            milestones.append({
                'week_number': week,
                'milestone_date': date,
                'milestone_type': 'recovery_milestone',
                'milestone_outcome': 'recovery_progressing',
                'leading_indicators': [
                    f"Health recovered to {health}",
                    f"GPU utilization: {week_kpis.get('P2', 'N/A')}%",
                    f"System uptime: {week_kpis.get('R1', 'N/A')}%"
                ],
                'arr_impact': 0,
                'confidence_at_time': 0.75
            })
        
        # Recovery complete
        if phase == 'recovered' and health > 85:
            milestones.append({
                'week_number': week,
                'milestone_date': date,
                'milestone_type': 'recovery_complete',
                'milestone_outcome': 'recovered',
                'leading_indicators': [
                    f"Health fully recovered to {health}",
                    "Stable operations restored",
                    "Customer confidence restored"
                ],
                'arr_impact': 0,
                'confidence_at_time': 0.90
            })
        
        # Expansion (after recovery)
        if event_type == 'qbr' and 'expansion' in event.get('description', '').lower() and phase == 'recovered':
            milestones.append({
                'week_number': week,
                'milestone_date': date,
                'milestone_type': 'expansion_inquiry',
                'milestone_outcome': 'exploring',
                'leading_indicators': [
                    "Customer discussing expansion in QBR",
                    f"Health score: {health}",
                    "Post-crisis trust restored"
                ],
                'arr_impact': 400000,  # Expected expansion
                'confidence_at_time': 0.70
            })
    
    return milestones


def extract_churn_milestones(account_id, events, kpi_data):
    """Extract milestones from ignored-churn journey"""
    
    milestones = []
    
    for event in events:
        week = event['week_number']
        date = event['date']
        event_type = event['event_type']
        phase = event['phase']
        health = event.get('health_score_after', 0)
        
        # Early warning (week 1-4)
        if week <= 4 and phase == 'at_risk':
            week_kpis = kpi_data.get(week, {})
            milestones.append({
                'week_number': week,
                'milestone_date': date,
                'milestone_type': 'churn_early_warning',
                'milestone_outcome': 'at_risk',
                'leading_indicators': [
                    f"Low GPU utilization: {week_kpis.get('P2', 'N/A')}%",
                    f"Negative workload growth: {week_kpis.get('S2', 'N/A')}%",
                    f"Low NPS: {week_kpis.get('B2', 'N/A')}",
                    f"Health: {health}"
                ],
                'arr_impact': 0,
                'confidence_at_time': 0.60,
                'primary_drivers': [
                    {'driver': 'Low product adoption', 'weight': 0.40},
                    {'driver': 'Poor customer sentiment', 'weight': 0.35},
                    {'driver': 'Declining usage', 'weight': 0.25}
                ]
            })
            break  # Only add one early warning
        
        # Risk elevated (week 5-8)
        if week in [5, 6, 7, 8] and health < 60:
            milestones.append({
                'week_number': week,
                'milestone_date': date,
                'milestone_type': 'churn_risk_elevated',
                'milestone_outcome': 'critical_risk',
                'leading_indicators': [
                    f"Health dropped to {health}",
                    "No CSM engagement",
                    "Competitive threats emerging"
                ],
                'arr_impact': 0,
                'confidence_at_time': 0.75
            })
            break
        
        # Escalation (too late)
        if event.get('csm_action_type') == 'escalation' and week >= 10:
            milestones.append({
                'week_number': week,
                'milestone_date': date,
                'milestone_type': 'churn_escalation',
                'milestone_outcome': 'escalated_too_late',
                'leading_indicators': [
                    "Late escalation attempt",
                    f"Health: {health}",
                    "Customer already decided"
                ],
                'arr_impact': 0,
                'confidence_at_time': 0.85
            })
        
        # Churn decision
        if phase == 'churning' and week >= 15:
            milestones.append({
                'week_number': week,
                'milestone_date': date,
                'milestone_type': 'churn_decision',
                'milestone_outcome': 'churning',
                'leading_indicators': [
                    "Customer decided to churn",
                    f"Final health: {health}",
                    "Migration to competitor planned"
                ],
                'arr_impact': -3800000,
                'confidence_at_time': 0.95,
                'primary_drivers': [
                    {'driver': 'Lack of engagement', 'weight': 0.40},
                    {'driver': 'Low adoption', 'weight': 0.35},
                    {'driver': 'Competitive pressure', 'weight': 0.25}
                ]
            })
            break
    
    # Churn finalized (last week)
    if events:
        last_event = events[-1]
        milestones.append({
            'week_number': last_event['week_number'],
            'milestone_date': last_event['date'],
            'milestone_type': 'churn_contract_terminated',
            'milestone_outcome': 'churned',
            'leading_indicators': [
                "Contract terminated",
                "Customer migrated to AWS",
                f"Final health: {last_event.get('health_score_after', 0)}"
            ],
            'arr_impact': -3800000,
            'confidence_at_time': 1.0
        })
    
    return milestones


def extract_expansion_milestones(account_id, events, kpi_data):
    """Extract milestones from proactive-growth journey"""
    
    milestones = []
    
    for event in events:
        week = event['week_number']
        date = event['date']
        event_type = event['event_type']
        phase = event['phase']
        health = event.get('health_score_after', 0)
        week_kpis = kpi_data.get(week, {})
        
        # Capacity alert (week 7-9)
        if week in [7, 8, 9] and float(week_kpis.get('S1', 0)) > 85:
            milestones.append({
                'week_number': week,
                'milestone_date': date,
                'milestone_type': 'expansion_capacity_alert',
                'milestone_outcome': 'capacity_constrained',
                'leading_indicators': [
                    f"Capacity utilization: {week_kpis.get('S1', 'N/A')}%",
                    f"GPU utilization: {week_kpis.get('P2', 'N/A')}%",
                    f"Expansion readiness: {week_kpis.get('S7', 'N/A')}",
                    f"Health: {health}"
                ],
                'arr_impact': 0,
                'confidence_at_time': 0.85,
                'primary_drivers': [
                    {'driver': 'Capacity constraints', 'weight': 0.45},
                    {'driver': 'High utilization', 'weight': 0.35},
                    {'driver': 'Growth trajectory', 'weight': 0.20}
                ],
                'signal_breakdown': {
                    'S1_capacity': float(week_kpis.get('S1', 0)),
                    'P2_gpu': float(week_kpis.get('P2', 0)),
                    'S7_expansion_readiness': float(week_kpis.get('S7', 0))
                }
            })
            break
        
        # Expansion inquiry (QBR or executive engagement)
        if event_type in ['qbr', 'executive_engagement'] and 'expansion' in event.get('description', '').lower():
            milestones.append({
                'week_number': week,
                'milestone_date': date,
                'milestone_type': 'expansion_inquiry',
                'milestone_outcome': 'customer_interested',
                'leading_indicators': [
                    f"Customer discussed expansion: {event.get('description', '')}",
                    f"Executive engagement: {week_kpis.get('B6', 'N/A')}",
                    f"Health: {health}"
                ],
                'arr_impact': 0,
                'confidence_at_time': 0.75
            })
        
        # Budget approved
        if 'budget' in event.get('description', '').lower() and 'approved' in event.get('description', '').lower():
            milestones.append({
                'week_number': week,
                'milestone_date': date,
                'milestone_type': 'expansion_budget_approved',
                'milestone_outcome': 'budget_secured',
                'leading_indicators': [
                    "CFO approved expansion budget",
                    f"Executive engagement: {week_kpis.get('B6', 'N/A')}",
                    f"Strategic alignment: {week_kpis.get('B5', 'N/A')}"
                ],
                'arr_impact': 5000000,  # Expected expansion
                'confidence_at_time': 0.90,
                'primary_drivers': [
                    {'driver': 'Executive buy-in', 'weight': 0.45},
                    {'driver': 'Business value demonstrated', 'weight': 0.35},
                    {'driver': 'Budget available', 'weight': 0.20}
                ]
            })
        
        # Expansion approved
        if event_type == 'expansion_approved':
            milestones.append({
                'week_number': week,
                'milestone_date': date,
                'milestone_type': 'expansion_decision_approved',
                'milestone_outcome': 'approved',
                'leading_indicators': [
                    "Customer approved expansion",
                    f"Capacity: {week_kpis.get('S1', 'N/A')}%",
                    f"Health: {health}"
                ],
                'arr_impact': 5000000,
                'confidence_at_time': 0.95
            })
        
        # Expansion signed
        if event_type == 'expansion_signed':
            milestones.append({
                'week_number': week,
                'milestone_date': date,
                'milestone_type': 'expansion_contract_signed',
                'milestone_outcome': 'signed',
                'leading_indicators': [
                    "Expansion contract signed",
                    f"New ARR: +$5M",
                    f"Health: {health}"
                ],
                'arr_impact': 5000000,
                'confidence_at_time': 1.0,
                'primary_drivers': [
                    {'driver': 'Proactive engagement', 'weight': 0.40},
                    {'driver': 'Capacity planning', 'weight': 0.35},
                    {'driver': 'Executive sponsorship', 'weight': 0.25}
                ]
            })
    
    return milestones


# ============================================================================
# EXPORT FUNCTIONS
# ============================================================================

def save_milestones_to_csv(milestones, account_id, output_file):
    """Save milestones to CSV"""
    
    fieldnames = [
        'account_id', 'week_number', 'milestone_date', 'milestone_type',
        'milestone_outcome', 'leading_indicators', 'arr_impact',
        'confidence_at_time', 'primary_drivers', 'signal_breakdown'
    ]
    
    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for milestone in milestones:
            row = {
                'account_id': account_id,
                'week_number': milestone['week_number'],
                'milestone_date': milestone['milestone_date'],
                'milestone_type': milestone['milestone_type'],
                'milestone_outcome': milestone['milestone_outcome'],
                'leading_indicators': json.dumps(milestone.get('leading_indicators', [])),
                'arr_impact': milestone.get('arr_impact', 0),
                'confidence_at_time': milestone.get('confidence_at_time', 0),
                'primary_drivers': json.dumps(milestone.get('primary_drivers', [])),
                'signal_breakdown': json.dumps(milestone.get('signal_breakdown', {}))
            }
            writer.writerow(row)


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Generate milestones for all accounts"""
    
    parser = argparse.ArgumentParser(description='Generate milestone training labels')
    parser.add_argument('--data-dir', default='data/raw', 
                       help='Directory containing phase1/phase2/phase3 subdirectories (default: data/raw)')
    parser.add_argument('--output-dir', default='data/processed',
                       help='Directory for output milestone CSVs (default: data/processed)')
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    print("="*70)
    print("MILESTONE GENERATION - Phase 4")
    print("="*70)
    print(f"📁 Data directory: {args.data_dir}")
    print(f"📁 Output directory: {args.output_dir}")
    print()
    
    accounts = ['10007', '{ACCOUNT_ID_START+2}', '336000']
    all_milestones = []
    
    for account_id in accounts:
        print(f"📍 Generating milestones for Account {account_id}...")
        
        # Find journey file in phase subdirectories
        journey_file = None
        for phase_dir in ['phase1', 'phase2']:
            potential_path = os.path.join(args.data_dir, phase_dir, f'account_{account_id}_journey.json')
            if os.path.exists(potential_path):
                journey_file = potential_path
                break
        
        if not journey_file:
            print(f"   ⚠️  Could not find journey file for Account {account_id}, skipping...")
            continue
        
        # Load journey data
        with open(journey_file, 'r') as f:
            journey_data = json.load(f)
        
        # KPI file is in phase3 or combined file
        kpis_file = os.path.join(args.data_dir, 'phase3', 'all_accounts_kpis.csv')
        
        # Extract milestones
        milestones = extract_milestones_from_journey(journey_data, kpis_file)
        
        print(f"   ✅ Generated {len(milestones)} milestones")
        
        # Save individual file
        output_file = os.path.join(args.output_dir, f'account_{account_id}_milestones.csv')
        save_milestones_to_csv(milestones, account_id, output_file)
        print(f"   💾 Saved to {output_file}")
        
        all_milestones.extend([{**m, 'account_id': account_id} for m in milestones])
        print()
    
    # Save combined file
    print("💾 Saving combined milestones file...")
    
    combined_file = os.path.join(args.output_dir, 'all_accounts_milestones.csv')
    with open(combined_file, 'w', newline='') as f:
        fieldnames = [
            'account_id', 'week_number', 'milestone_date', 'milestone_type',
            'milestone_outcome', 'leading_indicators', 'arr_impact',
            'confidence_at_time', 'primary_drivers', 'signal_breakdown'
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for milestone in all_milestones:
            row = {
                'account_id': milestone['account_id'],
                'week_number': milestone['week_number'],
                'milestone_date': milestone['milestone_date'],
                'milestone_type': milestone['milestone_type'],
                'milestone_outcome': milestone['milestone_outcome'],
                'leading_indicators': json.dumps(milestone.get('leading_indicators', [])),
                'arr_impact': milestone.get('arr_impact', 0),
                'confidence_at_time': milestone.get('confidence_at_time', 0),
                'primary_drivers': json.dumps(milestone.get('primary_drivers', [])),
                'signal_breakdown': json.dumps(milestone.get('signal_breakdown', {}))
            }
            writer.writerow(row)
    
    print(f"   ✅ Saved {combined_file} ({len(all_milestones)} total milestones)")
    print()
    print("="*70)
    print("✅ MILESTONE GENERATION COMPLETE!")
    print("="*70)
    print(f"Total milestones: {len(all_milestones)}")
    print(f"Output directory: {args.output_dir}")
    print()
    print("Milestone breakdown by type:")
    milestone_counts = {}
    for m in all_milestones:
        mtype = m['milestone_type']
        milestone_counts[mtype] = milestone_counts.get(mtype, 0) + 1
    
    for mtype, count in sorted(milestone_counts.items()):
        print(f"  {mtype:40s}: {count}")


if __name__ == "__main__":
    main()
