#!/usr/bin/env python3
"""
Phase 4: Data Loading Script
============================

Loads all generated journey data into PostgreSQL:
- 3 accounts from journey patterns
- 187 events
- 3,220 KPI data points
- 92 weekly health snapshots

Usage:
    python load_journey_data_phase4.py --db-url postgresql://user:pass@localhost/dbname
"""

import json
import csv
import argparse
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


# ============================================================================
# DATA LOADING FUNCTIONS
# ============================================================================

def load_journey_account(session, journey_data):
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
        match = re.search(r'(\d+)%', financial_impact)
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


def load_journey_events(session, journey_account_id, events):
    """Load events for a journey account"""
    
    event_sql = text("""
        INSERT INTO journey_events (
            journey_account_id, week_number, event_date, event_type,
            description, phase, sentiment_level, sentiment_value,
            health_score_before, health_score_after, health_impact,
            csm_action_type, csm_response_time_hours, csm_action_cost,
            csm_action_description
        ) VALUES (
            :journey_account_id, :week_number, :event_date, :event_type,
            :description, :phase, :sentiment_level, :sentiment_value,
            :health_before, :health_after, :health_impact,
            :csm_action_type, :csm_response_hours, :csm_cost,
            :csm_description
        )
    """)
    
    for event in events:
        session.execute(event_sql, {
            'journey_account_id': journey_account_id,
            'week_number': event['week_number'],
            'event_date': datetime.strptime(event['date'], '%Y-%m-%d'),
            'event_type': event['event_type'],
            'description': event['description'],
            'phase': event['phase'],
            'sentiment_level': event.get('sentiment_level', ''),
            'sentiment_value': event.get('sentiment_value', 0),
            'health_before': event.get('health_score_before', 0),
            'health_after': event.get('health_score_after', 0),
            'health_impact': event.get('health_impact', 0),
            'csm_action_type': event.get('csm_action_type', ''),
            'csm_response_hours': event.get('csm_response_time_hours'),
            'csm_cost': event.get('csm_action_cost'),
            'csm_description': event.get('csm_action_description', '')
        })


def load_journey_kpis(session, journey_account_id, kpis_file):
    """Load KPIs from CSV file"""
    
    kpi_sql = text("""
        INSERT INTO journey_kpis (
            journey_account_id, week_number, measurement_date,
            kpi_code, kpi_name, category, value, unit,
            health_score, phase
        ) VALUES (
            :journey_account_id, :week_number, :measurement_date,
            :kpi_code, :kpi_name, :category, :value, :unit,
            :health_score, :phase
        )
    """)
    
    # KPI name mapping (from Phase 3)
    kpi_names = {
        'P1': 'Workload Running', 'P2': 'GPU Utilization', 'P3': 'Active Users',
        'P4': 'Training Jobs Completed', 'P5': 'Inference Requests', 'P6': 'Model Accuracy',
        'P7': 'Data Processing Throughput', 'P8': 'API Response Time',
        'C1': 'Cost per Training Job', 'C2': 'Cost per 1M Inferences', 'C3': 'Idle GPU Time',
        'C4': 'Storage Cost Efficiency', 'C5': 'Compute ROI', 'C6': 'Budget Utilization',
        'C7': 'Cost Predictability',
        'S1': 'Capacity Utilization', 'S2': 'Workload Growth Rate', 'S3': 'New Use Cases Deployed',
        'S4': 'Time to Scale', 'S5': 'Resource Elasticity', 'S6': 'Peak Load Handling',
        'S7': 'Expansion Readiness',
        'R1': 'System Uptime', 'R2': 'Support Ticket Volume', 'R3': 'Mean Time to Resolution',
        'R4': 'Critical Incidents', 'R5': 'Support Satisfaction', 'R6': 'Documentation Usage',
        'B1': 'Business Value Score', 'B2': 'User Satisfaction (NPS)', 'B3': 'Feature Adoption',
        'B4': 'Time to Value', 'B5': 'Strategic Alignment', 'B6': 'Executive Engagement',
        'B7': 'Competitive Position'
    }
    
    kpi_categories = {
        'P1': 'Performance', 'P2': 'Performance', 'P3': 'Performance', 'P4': 'Performance',
        'P5': 'Performance', 'P6': 'Performance', 'P7': 'Performance', 'P8': 'Performance',
        'C1': 'Cost', 'C2': 'Cost', 'C3': 'Cost', 'C4': 'Cost', 'C5': 'Cost', 'C6': 'Cost', 'C7': 'Cost',
        'S1': 'Scalability', 'S2': 'Scalability', 'S3': 'Scalability', 'S4': 'Scalability',
        'S5': 'Scalability', 'S6': 'Scalability', 'S7': 'Scalability',
        'R1': 'Support', 'R2': 'Support', 'R3': 'Support', 'R4': 'Support', 'R5': 'Support', 'R6': 'Support',
        'B1': 'Business', 'B2': 'Business', 'B3': 'Business', 'B4': 'Business',
        'B5': 'Business', 'B6': 'Business', 'B7': 'Business'
    }
    
    with open(kpis_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Get all KPI columns (P1-P8, C1-C7, etc.)
            for kpi_code in list(kpi_names.keys()):
                if kpi_code in row:
                    session.execute(kpi_sql, {
                        'journey_account_id': journey_account_id,
                        'week_number': int(row['week_number']),
                        'measurement_date': datetime.strptime(row['date'], '%Y-%m-%d'),
                        'kpi_code': kpi_code,
                        'kpi_name': kpi_names[kpi_code],
                        'category': kpi_categories[kpi_code],
                        'value': float(row[kpi_code]),
                        'unit': '',  # Units would come from metadata
                        'health_score': float(row['health_score']),
                        'phase': row['phase']
                    })


def load_journey_health(session, journey_account_id, kpis_file, events):
    """Generate weekly health snapshots from KPI data"""
    
    health_sql = text("""
        INSERT INTO journey_health (
            journey_account_id, week_number, snapshot_date,
            overall_health_score, health_status, phase,
            events_this_week, csm_actions_this_week, total_csm_cost_this_week
        ) VALUES (
            :journey_account_id, :week_number, :snapshot_date,
            :health_score, :health_status, :phase,
            :events_count, :csm_actions, :csm_cost
        )
    """)
    
    # Group events by week
    events_by_week = {}
    for event in events:
        week = event['week_number']
        if week not in events_by_week:
            events_by_week[week] = []
        events_by_week[week].append(event)
    
    # Load KPI data for health snapshots
    with open(kpis_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            week = int(row['week_number'])
            health_score = float(row['health_score'])
            
            # Determine health status
            if health_score >= 85:
                status = 'excellent'
            elif health_score >= 70:
                status = 'good'
            elif health_score >= 50:
                status = 'at_risk'
            else:
                status = 'critical'
            
            # Get events for this week
            week_events = events_by_week.get(week, [])
            csm_actions = len([e for e in week_events if e.get('csm_action_type')])
            csm_cost = sum(e.get('csm_action_cost', 0) for e in week_events)
            
            session.execute(health_sql, {
                'journey_account_id': journey_account_id,
                'week_number': week,
                'snapshot_date': datetime.strptime(row['date'], '%Y-%m-%d'),
                'health_score': health_score,
                'health_status': status,
                'phase': row['phase'],
                'events_count': len(week_events),
                'csm_actions': csm_actions,
                'csm_cost': csm_cost if csm_cost > 0 else None
            })


def load_journey_health(session, journey_account_id, kpis_file, events):
    """Generate weekly health snapshots from KPI data"""
    
    health_sql = text("""
        INSERT INTO journey_health (
            journey_account_id, week_number, snapshot_date,
            overall_health_score, health_status, phase,
            events_this_week, csm_actions_this_week, total_csm_cost_this_week
        ) VALUES (
            :journey_account_id, :week_number, :snapshot_date,
            :health_score, :health_status, :phase,
            :events_count, :csm_actions, :csm_cost
        )
    """)
    
    # Group events by week
    events_by_week = {}
    for event in events:
        week = event['week_number']
        if week not in events_by_week:
            events_by_week[week] = []
        events_by_week[week].append(event)
    
    # Load KPI data for health snapshots
    with open(kpis_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            week = int(row['week_number'])
            health_score = float(row['health_score'])
            
            # Determine health status
            if health_score >= 85:
                status = 'excellent'
            elif health_score >= 70:
                status = 'good'
            elif health_score >= 50:
                status = 'at_risk'
            else:
                status = 'critical'
            
            # Get events for this week
            week_events = events_by_week.get(week, [])
            csm_actions = len([e for e in week_events if e.get('csm_action_type')])
            csm_cost = sum(e.get('csm_action_cost', 0) for e in week_events)
            
            session.execute(health_sql, {
                'journey_account_id': journey_account_id,
                'week_number': week,
                'snapshot_date': datetime.strptime(row['date'], '%Y-%m-%d'),
                'health_score': health_score,
                'health_status': status,
                'phase': row['phase'],
                'events_count': len(week_events),
                'csm_actions': csm_actions,
                'csm_cost': csm_cost if csm_cost > 0 else None
            })


def load_journey_milestones(session, journey_account_id, milestones_file):
    """Load milestone labels from CSV"""
    
    milestone_sql = text("""
        INSERT INTO journey_milestones (
            journey_account_id, week_number, milestone_date,
            milestone_type, milestone_outcome, leading_indicators,
            arr_impact, confidence_at_time, primary_drivers, signal_breakdown
        ) VALUES (
            :journey_account_id, :week_number, :milestone_date,
            :milestone_type, :milestone_outcome, :leading_indicators,
            :arr_impact, :confidence_at_time, :primary_drivers, :signal_breakdown
        )
    """)
    
    with open(milestones_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            session.execute(milestone_sql, {
                'journey_account_id': journey_account_id,
                'week_number': int(row['week_number']),
                'milestone_date': datetime.strptime(row['milestone_date'], '%Y-%m-%d'),
                'milestone_type': row['milestone_type'],
                'milestone_outcome': row['milestone_outcome'],
                'leading_indicators': row['leading_indicators'],  # Already JSON string
                'arr_impact': float(row['arr_impact']) if row['arr_impact'] else None,
                'confidence_at_time': float(row['confidence_at_time']) if row['confidence_at_time'] else None,
                'primary_drivers': row['primary_drivers'] if row['primary_drivers'] else None,
                'signal_breakdown': row['signal_breakdown'] if row['signal_breakdown'] else None
            })


def generate_sample_predictions(session, journey_account_id, account_id, final_outcome, milestones_file):
    """Generate sample predictions for testing feedback loop"""
    
    prediction_sql = text("""
        INSERT INTO signal_predictions (
            journey_account_id, prediction_week, prediction_date,
            predicted_outcome, churn_probability, expansion_probability,
            predicted_health_score, time_to_event_prediction,
            actual_outcome, actual_event_week, actual_arr_impact,
            prediction_correct, probability_error, timing_error_days,
            confidence_level, confidence_score, model_used, model_version,
            outcome_confirmed_at
        ) VALUES (
            :journey_account_id, :prediction_week, :prediction_date,
            :predicted_outcome, :churn_probability, :expansion_probability,
            :predicted_health_score, :time_to_event_prediction,
            :actual_outcome, :actual_event_week, :actual_arr_impact,
            :prediction_correct, :probability_error, :timing_error_days,
            :confidence_level, :confidence_score, :model_used, :model_version,
            :outcome_confirmed_at
        )
        RETURNING prediction_id
    """)
    
    explanation_sql = text("""
        INSERT INTO prediction_explanations (
            prediction_id, reasoning_text, key_insights,
            quantitative_signals_used, qualitative_signals_used,
            top_risk_drivers, top_growth_drivers, signal_weights
        ) VALUES (
            :prediction_id, :reasoning_text, :key_insights,
            :quantitative_signals_used, :qualitative_signals_used,
            :top_risk_drivers, :top_growth_drivers, :signal_weights
        )
    """)
    
    # Load milestones to know actual outcomes
    milestones = []
    with open(milestones_file, 'r') as f:
        reader = csv.DictReader(f)
        milestones = list(reader)
    
    # Generate predictions based on account pattern
    if account_id == '10007':  # Crisis-Recovery
        # Prediction at week 5 (during crisis)
        result = session.execute(prediction_sql, {
            'journey_account_id': journey_account_id,
            'prediction_week': 5,
            'prediction_date': datetime(2024, 1, 29),
            'predicted_outcome': 'stable',
            'churn_probability': 65.0,
            'expansion_probability': 10.0,
            'predicted_health_score': 40.0,
            'time_to_event_prediction': '8-12 weeks',
            'actual_outcome': 'expansion',
            'actual_event_week': 30,
            'actual_arr_impact': 400000,
            'prediction_correct': False,  # Predicted stable, got expansion
            'probability_error': 55.0,
            'timing_error_days': 175,  # Way off
            'confidence_level': 'medium',
            'confidence_score': 0.60,
            'model_used': 'bootstrap_weights_v1',
            'model_version': '0.1.0',
            'outcome_confirmed_at': datetime(2024, 7, 22)
        })
        pred_id = result.scalar()
        
        session.execute(explanation_sql, {
            'prediction_id': pred_id,
            'reasoning_text': 'Account in crisis with major outage. High churn risk due to health drop to 34.9. War room engaged but recovery uncertain.',
            'key_insights': json.dumps([
                'Major production outage impacting health',
                'War room convened with executive engagement',
                'Recovery timeline uncertain'
            ]),
            'quantitative_signals_used': json.dumps({'P2': 25, 'R1': 56, 'R4': 15}),
            'qualitative_signals_used': json.dumps(['outage', 'war_room', 'escalation']),
            'top_risk_drivers': json.dumps([
                {'driver': 'Production outage', 'weight': 0.70},
                {'driver': 'Health score drop', 'weight': 0.30}
            ]),
            'top_growth_drivers': json.dumps([]),
            'signal_weights': json.dumps({'health_impact': 0.45, 'uptime': 0.35, 'incidents': 0.20})
        })
    
    elif account_id == '{ACCOUNT_ID_START+2}':  # Ignored-Churn
        # Prediction at week 3 (early warning)
        result = session.execute(prediction_sql, {
            'journey_account_id': journey_account_id,
            'prediction_week': 3,
            'prediction_date': datetime(2024, 1, 15),
            'predicted_outcome': 'churn',
            'churn_probability': 75.0,
            'expansion_probability': 5.0,
            'predicted_health_score': 65.0,
            'time_to_event_prediction': '16-20 weeks',
            'actual_outcome': 'churn',
            'actual_event_week': 22,
            'actual_arr_impact': -3800000,
            'prediction_correct': True,  # Correctly predicted churn
            'probability_error': 25.0,  # Was 75%, actual was 100%
            'timing_error_days': 14,  # Pretty close on timing
            'confidence_level': 'high',
            'confidence_score': 0.75,
            'model_used': 'bootstrap_weights_v1',
            'model_version': '0.1.0',
            'outcome_confirmed_at': datetime(2024, 5, 27)
        })
        pred_id = result.scalar()
        
        session.execute(explanation_sql, {
            'prediction_id': pred_id,
            'reasoning_text': 'Strong churn signals: Low GPU utilization (45%), declining growth (-2%), low NPS (18). No proactive engagement detected.',
            'key_insights': json.dumps([
                'Low product adoption and declining usage',
                'Poor customer sentiment (NPS 18)',
                'No CSM engagement or intervention'
            ]),
            'quantitative_signals_used': json.dumps({'P2': 45, 'S2': -2, 'B2': 18}),
            'qualitative_signals_used': json.dumps(['low_engagement', 'competitive_threat']),
            'top_risk_drivers': json.dumps([
                {'driver': 'Low adoption', 'weight': 0.40},
                {'driver': 'Poor sentiment', 'weight': 0.35},
                {'driver': 'Declining usage', 'weight': 0.25}
            ]),
            'top_growth_drivers': json.dumps([]),
            'signal_weights': json.dumps({'P2_gpu': 0.30, 'S2_growth': 0.30, 'B2_nps': 0.25, 'engagement': 0.15})
        })
    
    elif account_id == '312000':  # Proactive-Growth
        # Prediction at week 5 (early capacity signals)
        result = session.execute(prediction_sql, {
            'journey_account_id': journey_account_id,
            'prediction_week': 5,
            'prediction_date': datetime(2024, 1, 29),
            'predicted_outcome': 'expansion',
            'churn_probability': 5.0,
            'expansion_probability': 85.0,
            'predicted_health_score': 95.0,
            'time_to_event_prediction': '8-12 weeks',
            'actual_outcome': 'expansion',
            'actual_event_week': 15,
            'actual_arr_impact': 5000000,
            'prediction_correct': True,  # Correctly predicted expansion
            'probability_error': 15.0,  # Was 85%, actual was 100%
            'timing_error_days': 21,  # Predicted 8-12 weeks, happened at 10 weeks
            'confidence_level': 'very_high',
            'confidence_score': 0.85,
            'model_used': 'bootstrap_weights_v1',
            'model_version': '0.1.0',
            'outcome_confirmed_at': datetime(2024, 4, 15)
        })
        pred_id = result.scalar()
        
        session.execute(explanation_sql, {
            'prediction_id': pred_id,
            'reasoning_text': 'Strong expansion signals: High capacity utilization (87%), sustained growth (28%), excellent executive engagement (95). Proactive capacity planning in progress.',
            'key_insights': json.dumps([
                'Capacity constraints driving expansion need',
                'Strong executive buy-in and budget approval',
                'High utilization and growth trajectory'
            ]),
            'quantitative_signals_used': json.dumps({'S1': 87, 'P2': 89, 'S2': 28, 'B6': 95}),
            'qualitative_signals_used': json.dumps(['capacity_alert', 'executive_engagement', 'budget_approved']),
            'top_risk_drivers': json.dumps([]),
            'top_growth_drivers': json.dumps([
                {'driver': 'Capacity constraints', 'weight': 0.45},
                {'driver': 'Executive buy-in', 'weight': 0.35},
                {'driver': 'High utilization', 'weight': 0.20}
            ]),
            'signal_weights': json.dumps({'S1_capacity': 0.30, 'P2_gpu': 0.25, 'B6_exec': 0.25, 'S2_growth': 0.20})
        })


def load_metadata(session, phase, accounts_loaded, events_loaded, kpis_loaded):
    """Load generation metadata"""
    
    metadata_sql = text("""
        INSERT INTO journey_metadata (
            generation_phase, generation_date, generator_version,
            accounts_generated, events_generated, kpis_generated,
            parameters, patterns, notes
        ) VALUES (
            :phase, :gen_date, :version,
            :accounts, :events, :kpis,
            :parameters, :patterns, :notes
        )
    """)
    
    patterns_list = [
        {'account_id': '10007', 'pattern': 'crisis_recovery', 'outcome': 'recovered'},
        {'account_id': '{ACCOUNT_ID_START+2}', 'pattern': 'ignored_churn', 'outcome': 'churned'},
        {'account_id': '312000', 'pattern': 'proactive_growth', 'outcome': 'expanded'}
    ]
    
    session.execute(metadata_sql, {
        'phase': phase,
        'gen_date': datetime.utcnow(),
        'version': 'phase_1_2_3',
        'accounts': accounts_loaded,
        'events': events_loaded,
        'kpis': kpis_loaded,
        'parameters': json.dumps({'source': 'journey_pattern_generator', 'phases': [1, 2, 3]}),
        'patterns': json.dumps(patterns_list),
        'notes': 'Initial load of journey training data from Phases 1-3'
    })


# ============================================================================
# MAIN LOADING SCRIPT
# ============================================================================

def main():
    """Main data loading function"""
    
    parser = argparse.ArgumentParser(description='Load journey data into PostgreSQL')
    parser.add_argument('--db-url', required=True, help='PostgreSQL connection URL')
    parser.add_argument('--data-dir', default='.', help='Directory containing JSON/CSV files')
    args = parser.parse_args()
    
    print("="*70)
    print("PHASE 4: JOURNEY DATA LOADING")
    print("="*70)
    print()
    
    # Connect to database
    print("📡 Connecting to database...")
    engine = create_engine(args.db_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Load each account
        accounts = ['10007', '{ACCOUNT_ID_START+2}', '312000']
        total_events = 0
        total_kpis = 0
        
        for account_id in accounts:
            print(f"\n📊 Loading Account {account_id}...")
            
            # Load journey JSON
            journey_file = f"{args.data_dir}/account_{account_id}_journey.json"
            with open(journey_file, 'r') as f:
                journey_data = json.load(f)
            
            # Load account
            print(f"  1/4 Loading account metadata...")
            journey_account_id = load_journey_account(session, journey_data)
            print(f"      ✅ Account created (journey_account_id={journey_account_id})")
            
            # Load events
            print(f"  2/4 Loading {len(journey_data['events'])} events...")
            load_journey_events(session, journey_account_id, journey_data['events'])
            total_events += len(journey_data['events'])
            print(f"      ✅ Events loaded")
            
            # Load KPIs
            kpis_file = f"{args.data_dir}/account_{account_id}_kpis.csv"
            print(f"  3/4 Loading KPIs from CSV...")
            load_journey_kpis(session, journey_account_id, kpis_file)
            
            # Count KPIs (35 per week)
            with open(kpis_file, 'r') as f:
                kpi_weeks = sum(1 for _ in csv.DictReader(f))
            kpis_count = kpi_weeks * 35
            total_kpis += kpis_count
            print(f"      ✅ {kpis_count} KPIs loaded")
            
            # Load health snapshots
            print(f"  4/6 Loading health snapshots...")
            load_journey_health(session, journey_account_id, kpis_file, journey_data['events'])
            print(f"      ✅ Health snapshots loaded")
            
            # Load milestones
            milestones_file = f"{args.data_dir}/account_{account_id}_milestones.csv"
            print(f"  5/6 Loading milestone labels...")
            load_journey_milestones(session, journey_account_id, milestones_file)
            print(f"      ✅ Milestones loaded")
            
            # Generate sample predictions
            print(f"  6/6 Generating sample predictions...")
            generate_sample_predictions(session, journey_account_id, account_id, 
                                       journey_data.get('final_outcome', ''), milestones_file)
            print(f"      ✅ Sample predictions generated")
        
        # Load metadata
        print(f"\n📝 Loading generation metadata...")
        load_metadata(session, 'phase_1_2_3', len(accounts), total_events, total_kpis)
        print(f"   ✅ Metadata loaded")
        
        # Commit all changes
        session.commit()
        
        print()
        print("="*70)
        print("✅ DATA LOADING COMPLETE!")
        print("="*70)
        print(f"  Accounts loaded:      {len(accounts)}")
        print(f"  Events loaded:        {total_events}")
        print(f"  KPIs loaded:          {total_kpis}")
        print(f"  Health snapshots:     {sum(1 for _ in csv.DictReader(open(f'{args.data_dir}/account_{accounts[0]}_kpis.csv'))) * 3}")
        print(f"  Milestones loaded:    {sum(1 for _ in csv.DictReader(open(f'{args.data_dir}/all_accounts_milestones.csv')))}")
        print(f"  Predictions generated: 3 (one per account)")
        print()
        print("📊 Query examples:")
        print("  SELECT * FROM journey_accounts;")
        print("  SELECT * FROM journey_events WHERE phase = 'crisis';")
        print("  SELECT * FROM journey_kpis WHERE kpi_code = 'P2' ORDER BY value DESC;")
        print("  SELECT * FROM journey_health WHERE overall_health_score < 50;")
        print("  SELECT * FROM journey_milestones WHERE milestone_type LIKE '%churn%';")
        print("  SELECT * FROM signal_predictions WHERE prediction_correct = true;")
        print()
        
    except Exception as e:
        session.rollback()
        print(f"\n❌ ERROR: {str(e)}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
