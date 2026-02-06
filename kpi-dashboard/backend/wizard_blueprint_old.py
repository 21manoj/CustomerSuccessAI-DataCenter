"""
Wizard A - Data Generation & Model Training Blueprint
=====================================================

Flask backend for the journey data generation wizard.

Endpoints:
- GET  /wizard/config       - Get current configuration
- POST /wizard/generate     - Start generation job
- GET  /wizard/status/:id   - Check job status
- GET  /wizard/results/:id  - Get generation results
- POST /wizard/validate     - Validate configuration
- GET  /wizard/learnings    - Get extracted learnings
"""

from flask import Blueprint, request, jsonify, render_template, current_app
from datetime import datetime
import json
import os
from pathlib import Path

# Import Celery tasks (we'll create these next)
# Import Celery tasks
from wizard_tasks import (
    generate_journey_data_task,
    test_predictions_task,
    learn_ensemble_weights_task,
    generate_visualizations_task,
    extract_learnings_task
)

# Import models (adjust based on your project structure)
# Import models if they exist
try:
    from models import WizardRun, WizardLearning, db
except ImportError:
    WizardRun = None
    WizardLearning = None
    db = None
    print("⚠️  Warning: Wizard models not found. Database features disabled.")
# Create blueprint
wizard_bp = Blueprint('wizard', __name__, url_prefix='/admin/wizard')


# ============================================================================
# ROUTES
# ============================================================================

@wizard_bp.route('/')
def index():
    """Render the wizard UI"""
    return render_template('wizard/index.html')


@wizard_bp.route('/config', methods=['GET'])
def get_config():
    """Get default configuration for wizard"""
    
    default_config = {
        'accounts': 50,
        'weeks_per_account': 20,
        'pattern_mix': {
            'crisis': 0.20,
            'churn': 0.15,
            'stable': 0.40,
            'expansion': 0.25
        },
        'llm_strategy': {
            'triggers': ['arr>25M', 'health<30', 'event_risk>15', 'borderline'],
            'arr_threshold': 25000000,
            'expected_usage': 0.30
        },
        'data_sources': {
            'signals': 'generate',
            'bootstrap': 'bootstrap_weights_config.json'
        },
        'database': {
            'mode': 'clean',
            'backup': True,
            'rollback_on_failure': True
        },
        'pipeline': {
            'phases': [1, 2, 3, 4, 5],
            'skip': []
        },
        'visualizations': {
            'enabled': ['timeline', 'distribution', 'accuracy', 'cost', 'confusion', 'dashboard'],
            'format': 'html'
        }
    }
    
    # Check if there's a previous successful run to use as template
    last_run = None
    if WizardRun is not None:
        try:
            last_run = WizardRun.query.filter_by(status='completed').order_by(
                WizardRun.created_at.desc()
            ).first()
        except Exception as e:
            print(f"⚠️  Warning: Error getting last run: {e}")
            last_run = None
    
    if last_run and last_run.config:
        default_config['_last_run'] = {
            'run_id': last_run.run_id,
            'created_at': last_run.created_at.isoformat(),
            'accuracy': last_run.results.get('accuracy') if last_run.results else None
        }
    
    return jsonify({
        'success': True,
        'config': default_config
    })


@wizard_bp.route('/validate', methods=['POST'])
def validate_config():
    """Validate wizard configuration before running"""
    
    config = request.json
    errors = []
    warnings = []
    
    # Validate accounts
    if config.get('accounts', 0) < 10:
        errors.append("Minimum 10 accounts required")
    elif config.get('accounts', 0) > 500:
        errors.append("Maximum 500 accounts allowed")
    
    # Validate weeks
    if config.get('weeks_per_account', 0) < 10:
        errors.append("Minimum 10 weeks per account required")
    elif config.get('weeks_per_account', 0) > 52:
        warnings.append("More than 52 weeks will take significant time")
    
    # Validate pattern mix
    pattern_mix = config.get('pattern_mix', {})
    total = sum(pattern_mix.values())
    if abs(total - 1.0) > 0.01:
        errors.append(f"Pattern mix must sum to 1.0 (currently {total:.2f})")
    
    # Validate LLM strategy
    llm_strategy = config.get('llm_strategy', {})
    arr_threshold = llm_strategy.get('arr_threshold', 0)
    if arr_threshold < 0:
        errors.append("ARR threshold cannot be negative")
    
    # Estimate cost
    total_predictions = config.get('accounts', 0) * config.get('weeks_per_account', 0)
    llm_usage = llm_strategy.get('expected_usage', 0.30)
    llm_calls = int(total_predictions * llm_usage)
    estimated_cost = llm_calls * 0.008  # $0.008 per LLM call
    
    # Cost warning
    if estimated_cost > 10:
        warnings.append(f"Estimated cost (${estimated_cost:.2f}) exceeds $10. Consider reducing accounts or LLM usage.")
    
    # Estimate time
    estimated_time_minutes = (
        2 +  # Data generation
        (llm_calls / 100) +  # LLM calls (100 per minute)
        3 +  # Model training
        1    # Visualization
    )
    
    return jsonify({
        'success': len(errors) == 0,
        'errors': errors,
        'warnings': warnings,
        'estimates': {
            'total_predictions': total_predictions,
            'llm_calls': llm_calls,
            'cost': round(estimated_cost, 2),
            'time_minutes': round(estimated_time_minutes, 1)
        }
    })


@wizard_bp.route('/generate', methods=['POST'])
def start_generation():
    """Start the data generation pipeline"""
    
    config = request.json
    
    # Validate first
    validation = validate_config_internal(config)
    if not validation['success']:
        return jsonify({
            'success': False,
            'error': 'Configuration validation failed',
            'details': validation['errors']
        }), 400
    
    # Create wizard run record
    # Create wizard run record (if models exist)
wizard_run = None
run_id = f"wizard_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

if WizardRun is not None and db is not None:
    try:
        wizard_run = WizardRun(
            config=config,
            status='queued',
            created_by=request.headers.get('X-User-ID', 'admin')
        )
        db.session.add(wizard_run)
        db.session.commit()
        run_id = wizard_run.run_id
    except:
        pass
    
    # Start background job
    job = generate_full_pipeline.delay(wizard_run.run_id, config)
    
    # Update with job ID
    wizard_run.job_id = job.id
    db.session.commit()
    
    return jsonify({
        'success': True,
        'run_id': wizard_run.run_id if wizard_run else run_id,
        'job_id': job.id,
        'status': 'queued',
        'message': 'Generation pipeline started'
    })


@wizard_bp.route('/status/<run_id>', methods=['GET'])
def get_status(run_id):
    """Get status of a wizard run"""
    
    wizard_run = WizardRun.query.filter_by(run_id=run_id).first()
    
    if not wizard_run:
        return jsonify({
            'success': False,
            'error': 'Run not found'
        }), 404
    
    # Get job status if running
    job_status = None
    if wizard_run.job_id:
        from celery_app import celery
        job = celery.AsyncResult(wizard_run.job_id)
        job_status = {
            'state': job.state,
            'info': job.info
        }
    
    response = {
        'success': True,
        'run_id': wizard_run.run_id,
        'status': wizard_run.status,
        'progress': wizard_run.progress or {},
        'current_phase': wizard_run.current_phase,
        'created_at': wizard_run.created_at.isoformat(),
        'completed_at': wizard_run.completed_at.isoformat() if wizard_run.completed_at else None,
        'error_message': wizard_run.error_message,
        'job_status': job_status
    }
    
    # Add results if completed
    if wizard_run.status == 'completed' and wizard_run.results:
        response['results'] = wizard_run.results
    
    return jsonify(response)


@wizard_bp.route('/results/<run_id>', methods=['GET'])
def get_results(run_id):
    """Get detailed results of a completed run"""
    
    wizard_run = WizardRun.query.filter_by(run_id=run_id).first()
    
    if not wizard_run:
        return jsonify({
            'success': False,
            'error': 'Run not found'
        }), 404
    
    if wizard_run.status != 'completed':
        return jsonify({
            'success': False,
            'error': f'Run is {wizard_run.status}, not completed'
        }), 400
    
    # Load results
    results = wizard_run.results or {}
    
    # Add file paths for visualizations
    output_dir = Path(f"outputs/wizard_runs/{run_id}")
    if output_dir.exists():
        results['files'] = {
            'dashboard': f"/wizard/download/{run_id}/dashboard.html",
            'visualizations': [
                f"/wizard/download/{run_id}/{f.name}"
                for f in output_dir.glob("*.png")
            ],
            'config': f"/wizard/download/{run_id}/config.json",
            'learned_weights': f"/wizard/download/{run_id}/learned_weights.json"
        }
    
    return jsonify({
        'success': True,
        'run_id': run_id,
        'results': results,
        'created_at': wizard_run.created_at.isoformat(),
        'completed_at': wizard_run.completed_at.isoformat()
    })


@wizard_bp.route('/learnings', methods=['GET'])
def get_learnings():
    """Get extracted learnings from all wizard runs"""
    
    # Get latest learnings
    latest = WizardLearning.query.order_by(
        WizardLearning.created_at.desc()
    ).first()
    
    if not latest:
        return jsonify({
            'success': False,
            'error': 'No learnings available yet. Run the wizard first.'
        }), 404
    
    return jsonify({
        'success': True,
        'version': latest.version,
        'created_at': latest.created_at.isoformat(),
        'source_runs': latest.source_runs,
        'learnings': latest.learnings,
        'industry_benchmarks': latest.industry_benchmarks,
        'validation_rules': latest.validation_rules
    })


@wizard_bp.route('/download/<run_id>/<filename>', methods=['GET'])
def download_file(run_id, filename):
    """Download generated files"""
    
    from flask import send_file
    
    # Validate run exists
    wizard_run = WizardRun.query.filter_by(run_id=run_id).first()
    if not wizard_run:
        return jsonify({'error': 'Run not found'}), 404
    
    # Build file path
    file_path = Path(f"outputs/wizard_runs/{run_id}/{filename}")
    
    if not file_path.exists():
        return jsonify({'error': 'File not found'}), 404
    
    # Security check - ensure file is within run directory
    if not str(file_path.resolve()).startswith(str(Path(f"outputs/wizard_runs/{run_id}").resolve())):
        return jsonify({'error': 'Invalid file path'}), 403
    
    return send_file(file_path, as_attachment=True)


@wizard_bp.route('/runs', methods=['GET'])
def list_runs():
    """List all wizard runs"""
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    status_filter = request.args.get('status')
    
    query = WizardRun.query
    
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    pagination = query.order_by(WizardRun.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    runs = []
    for run in pagination.items:
        runs.append({
            'run_id': run.run_id,
            'status': run.status,
            'current_phase': run.current_phase,
            'created_at': run.created_at.isoformat(),
            'completed_at': run.completed_at.isoformat() if run.completed_at else None,
            'accounts_generated': run.config.get('accounts') if run.config else None,
            'accuracy': run.results.get('accuracy') if run.results else None
        })
    
    return jsonify({
        'success': True,
        'runs': runs,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': pagination.total,
            'pages': pagination.pages
        }
    })


@wizard_bp.route('/cancel/<run_id>', methods=['POST'])
def cancel_run(run_id):
    """Cancel a running wizard job"""
    
    wizard_run = WizardRun.query.filter_by(run_id=run_id).first()
    
    if not wizard_run:
        return jsonify({'success': False, 'error': 'Run not found'}), 404
    
    if wizard_run.status not in ['queued', 'running']:
        return jsonify({
            'success': False,
            'error': f'Cannot cancel run with status: {wizard_run.status}'
        }), 400
    
    # Revoke Celery task
    if wizard_run.job_id:
        from .celery_app import celery
        celery.control.revoke(wizard_run.job_id, terminate=True)
    
    # Update status
    wizard_run.status = 'cancelled'
    wizard_run.completed_at = datetime.utcnow()
    wizard_run.error_message = 'Cancelled by user'
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Run cancelled successfully'
    })


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def validate_config_internal(config):
    """Internal config validation (returns dict, not Flask response)"""
    errors = []
    
    if config.get('accounts', 0) < 10:
        errors.append("Minimum 10 accounts required")
    
    pattern_mix = config.get('pattern_mix', {})
    total = sum(pattern_mix.values())
    if abs(total - 1.0) > 0.01:
        errors.append(f"Pattern mix must sum to 1.0")
    
    return {
        'success': len(errors) == 0,
        'errors': errors
    }


# ============================================================================
# CELERY TASK ORCHESTRATOR
# ============================================================================

from celery import chain, group

def generate_full_pipeline(run_id, config):
    """
    Orchestrate the full pipeline as a Celery chain
    
    Phase 1: Generate data
    Phase 2: Test V3
    Phase 3: Test V4
    Phase 4: Learn weights
    Phase 5: Generate visualizations
    """
    
    phases = config.get('pipeline', {}).get('phases', [1, 2, 3, 4, 5])
    
    # Build task chain
    tasks = []
    
    if 1 in phases:
        tasks.append(generate_journey_data_task.s(run_id, config))
    
    if 2 in phases:
        tasks.append(test_predictions_task.s(run_id, 'v3'))
    
    if 3 in phases:
        tasks.append(test_predictions_task.s(run_id, 'v4'))
    
    if 4 in phases:
        tasks.append(learn_ensemble_weights_task.s(run_id))
    
    if 5 in phases:
        tasks.append(generate_visualizations_task.s(run_id))
    
    # Execute chain
    pipeline = chain(*tasks)
    return pipeline.apply_async()
