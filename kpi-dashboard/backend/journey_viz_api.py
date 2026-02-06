"""
Journey Visualization API
=========================

Flask endpoints to serve journey data to the React visualization component.

Endpoints:
- GET /api/wizard/runs - List all wizard runs
- GET /api/wizard/journey/{run_id} - Get journey data for a run
- GET /api/wizard/kpis/{run_id} - Get KPI data for a run  
- GET /api/wizard/milestones/{run_id} - Get milestone data for a run
"""

from flask import Blueprint, jsonify, send_file
from pathlib import Path
import json
import csv
import os

# Create blueprint
journey_viz_api = Blueprint('journey_viz', __name__, url_prefix='/api/wizard')

# Base paths
BASE_DIR = Path(os.path.expanduser("~/CustomerSuccessAI-DataCenter/kpi-dashboard/backend"))
JOURNEY_BASE = BASE_DIR / "verticals/customer9-dc2_s/journey"
WIZARD_DATA_DIR = JOURNEY_BASE / "data/wizard"
WIZARD_PROCESSED_DIR = JOURNEY_BASE / "data/processed/wizard"


@journey_viz_api.route('/runs', methods=['GET'])
def list_runs():
    """List all wizard runs"""
    
    runs = []
    
    if WIZARD_DATA_DIR.exists():
        for run_dir in sorted(WIZARD_DATA_DIR.iterdir(), reverse=True):
            if run_dir.is_dir() and run_dir.name.startswith('wizard_'):
                # Count accounts
                journey_files = list(run_dir.glob('account_*_journey.json'))
                
                # Get metadata
                metadata_file = run_dir / 'kpi_metadata.json'
                metadata = {}
                if metadata_file.exists():
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                
                runs.append({
                    'run_id': run_dir.name,
                    'created_at': run_dir.stat().st_ctime,
                    'accounts_generated': len(journey_files),
                    'metadata': metadata
                })
    
    return jsonify({
        'success': True,
        'runs': runs,
        'total': len(runs)
    })


@journey_viz_api.route('/journey/<run_id>', methods=['GET'])
def get_journey_data(run_id):
    """Get all journey data for a specific run"""
    
    run_dir = WIZARD_DATA_DIR / run_id
    
    if not run_dir.exists():
        return jsonify({
            'success': False,
            'error': 'Run not found'
        }), 404
    
    journeys = []
    
    # Load all journey JSON files
    for journey_file in sorted(run_dir.glob('account_*_journey.json')):
        with open(journey_file, 'r') as f:
            journey_data = json.load(f)
            journeys.append(journey_data)
    
    return jsonify({
        'success': True,
        'run_id': run_id,
        'journeys': journeys,
        'total_accounts': len(journeys)
    })


@journey_viz_api.route('/kpis/<run_id>', methods=['GET'])
def get_kpi_data(run_id):
    """Get KPI data for a specific run"""
    
    run_dir = WIZARD_DATA_DIR / run_id
    kpi_file = run_dir / 'all_accounts_kpis.csv'
    
    if not kpi_file.exists():
        return jsonify({
            'success': False,
            'error': 'KPI data not found'
        }), 404
    
    kpis = []
    
    # Read CSV file
    with open(kpi_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Convert numeric values
            kpis.append({
                'account_id': row['account_id'],
                'week_number': int(row['week_number']),
                'kpi_name': row['kpi_name'],
                'value': float(row['value']) if row['value'] else None,
                'percentile': float(row['percentile']) if row.get('percentile') else None,
                'pillar': row.get('pillar', ''),
                'health_score': float(row.get('health_score', 0))
            })
    
    # Load metadata
    metadata_file = run_dir / 'kpi_metadata.json'
    metadata = {}
    if metadata_file.exists():
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
    
    return jsonify({
        'success': True,
        'run_id': run_id,
        'kpis': kpis,
        'total_records': len(kpis),
        'metadata': metadata
    })


@journey_viz_api.route('/milestones/<run_id>', methods=['GET'])
def get_milestone_data(run_id):
    """Get milestone data for a specific run"""
    
    processed_dir = WIZARD_PROCESSED_DIR / run_id
    milestone_file = processed_dir / 'all_milestones.json'
    
    if not milestone_file.exists():
        return jsonify({
            'success': False,
            'error': 'Milestone data not found'
        }), 404
    
    with open(milestone_file, 'r') as f:
        milestones = json.load(f)
    
    return jsonify({
        'success': True,
        'run_id': run_id,
        'milestones': milestones,
        'total_milestones': len(milestones)
    })


@journey_viz_api.route('/account/<run_id>/<account_id>', methods=['GET'])
def get_account_detail(run_id, account_id):
    """Get detailed data for a specific account"""
    
    run_dir = WIZARD_DATA_DIR / run_id
    
    # Load journey
    journey_file = run_dir / f'{account_id}_journey.json'
    if not journey_file.exists():
        return jsonify({
            'success': False,
            'error': 'Account not found'
        }), 404
    
    with open(journey_file, 'r') as f:
        journey = json.load(f)
    
    # Load events CSV
    events_file = run_dir / f'{account_id}_events.csv'
    events = []
    if events_file.exists():
        with open(events_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                events.append(row)
    
    # Filter KPIs for this account
    kpi_file = run_dir / 'all_accounts_kpis.csv'
    account_kpis = []
    if kpi_file.exists():
        with open(kpi_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['account_id'] == account_id:
                    account_kpis.append({
                        'week_number': int(row['week_number']),
                        'kpi_name': row['kpi_name'],
                        'value': float(row['value']) if row['value'] else None,
                        'percentile': float(row['percentile']) if row.get('percentile') else None
                    })
    
    # Filter milestones for this account
    milestone_file = WIZARD_PROCESSED_DIR / run_id / 'all_milestones.json'
    account_milestones = []
    if milestone_file.exists():
        with open(milestone_file, 'r') as f:
            all_milestones = json.load(f)
            account_milestones = [m for m in all_milestones if m.get('account_id') == account_id]
    
    return jsonify({
        'success': True,
        'account_id': account_id,
        'journey': journey,
        'events': events,
        'kpis': account_kpis,
        'milestones': account_milestones
    })


@journey_viz_api.route('/export/<run_id>', methods=['GET'])
def export_run_data(run_id):
    """Export all data for a run as a zip file"""
    
    # TODO: Implement ZIP export of all files
    # For now, return a link to the directory
    
    run_dir = WIZARD_DATA_DIR / run_id
    
    if not run_dir.exists():
        return jsonify({
            'success': False,
            'error': 'Run not found'
        }), 404
    
    return jsonify({
        'success': True,
        'message': 'Export functionality coming soon',
        'data_directory': str(run_dir)
    })
