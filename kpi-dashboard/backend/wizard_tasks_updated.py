"""
Wizard A - Celery Background Tasks (UPDATED)
============================================

Updated to call your wrapper scripts for journey generation!

Tasks:
1. generate_journey_data_task - Uses wizard_journey_generator.py
2. test_predictions_task - Test V3/V4 predictions
3. learn_ensemble_weights_task - Learn optimal ensemble weights
4. generate_visualizations_task - Create charts and dashboard
5. extract_learnings_task - Extract insights for Wizard B
"""

from celery import Task, current_task
from datetime import datetime
import subprocess
import json
import os
from pathlib import Path
import traceback

# Import models
from models import WizardRun, WizardLearning, WizardFile, db
from celery_app import celery


class CallbackTask(Task):
    """Base task that updates progress in database"""
    
    def update_progress(self, run_id, phase, percent, message=''):
        """Update progress in database"""
        wizard_run = WizardRun.query.filter_by(run_id=run_id).first()
        if wizard_run:
            wizard_run.update_progress(phase, percent)
            print(f"[{run_id}] {phase}: {percent}% - {message}")


# ============================================================================
# TASK 1: GENERATE JOURNEY DATA (UPDATED - Uses Wrappers!)
# ============================================================================

@celery.task(base=CallbackTask, bind=True)
def generate_journey_data_task(self, run_id, config):
    """
    Phase 1: Generate synthetic journey data
    
    NOW CALLS YOUR WRAPPER SCRIPTS:
    - wizard_journey_generator.py (wraps journey_pattern_generator.py)
    - wizard_kpi_generator.py (wraps kpi_generator_phase3.py)  
    - wizard_milestone_generator.py (enhanced generate_milestones_phase4.py)
    - load_journey_data_phase4.py (your existing script)
    
    Args:
        run_id: Wizard run ID
        config: Configuration dict
    
    Returns:
        dict with generation results
    """
    
    print(f"[{run_id}] Starting Phase 1: Generate Journey Data")
    
    wizard_run = WizardRun.query.filter_by(run_id=run_id).first()
    if not wizard_run:
        raise ValueError(f"Wizard run {run_id} not found")
    
    wizard_run.mark_started()
    self.update_progress(run_id, 'phase1_generate', 5, 'Starting data generation')
    
    try:
        # Extract config
        num_accounts = config.get('accounts', 50)
        pattern_mix = config.get('pattern_mix', {})
        db_mode = config.get('database', {}).get('mode', 'clean')
        
        # Set paths
        BASE_DIR = os.path.expanduser("~/CustomerSuccessAI-DataCenter/kpi-dashboard/backend")
        JOURNEY_DIR = os.path.join(BASE_DIR, "verticals/customer9-dc2_s/journey")
        WIZARD_DIR = os.path.join(JOURNEY_DIR, "wizard_a")
        OUTPUT_DIR = os.path.join(JOURNEY_DIR, "data/wizard", run_id)
        PROCESSED_DIR = os.path.join(JOURNEY_DIR, "data/processed/wizard", run_id)
        
        # Create directories
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        os.makedirs(PROCESSED_DIR, exist_ok=True)
        
        # ================================================================
        # STEP 1: Generate Journeys (YOUR Phase 1 script via wrapper)
        # ================================================================
        self.update_progress(run_id, 'phase1_generate', 10, 'Generating journeys...')
        
        cmd = [
            'python3',
            os.path.join(WIZARD_DIR, 'wizard_journey_generator.py'),
            '--accounts', str(num_accounts),
            '--start-id', '10001',
            '--pattern-mix', json.dumps(pattern_mix),
            '--output-dir', OUTPUT_DIR
        ]
        
        print(f"[{run_id}] Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        
        if result.returncode != 0:
            raise Exception(f"Journey generation failed: {result.stderr}")
        
        print(f"[{run_id}] Journey generation output:\n{result.stdout[-500:]}")
        
        # ================================================================
        # STEP 2: Generate KPIs (YOUR Phase 3 script via wrapper)
        # ================================================================
        self.update_progress(run_id, 'phase1_generate', 40, 'Generating KPIs...')
        
        cmd = [
            'python3',
            os.path.join(WIZARD_DIR, 'wizard_kpi_generator.py'),
            '--input-dir', OUTPUT_DIR,
            '--output-dir', OUTPUT_DIR
        ]
        
        print(f"[{run_id}] Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        
        if result.returncode != 0:
            raise Exception(f"KPI generation failed: {result.stderr}")
        
        print(f"[{run_id}] KPI generation output:\n{result.stdout[-500:]}")
        
        # ================================================================
        # STEP 3: Generate Milestones (YOUR Phase 4 script enhanced)
        # ================================================================
        self.update_progress(run_id, 'phase1_generate', 60, 'Generating milestones...')
        
        cmd = [
            'python3',
            os.path.join(WIZARD_DIR, 'wizard_milestone_generator.py'),
            '--data-dir', OUTPUT_DIR,
            '--output-dir', PROCESSED_DIR
        ]
        
        print(f"[{run_id}] Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        
        if result.returncode != 0:
            raise Exception(f"Milestone generation failed: {result.stderr}")
        
        print(f"[{run_id}] Milestone generation output:\n{result.stdout[-500:]}")
        
        # ================================================================
        # STEP 4: Load to PostgreSQL (YOUR Phase 4 script)
        # ================================================================
        self.update_progress(run_id, 'phase1_generate', 80, 'Loading to database...')
        
        cmd = [
            'python3',
            os.path.join(JOURNEY_DIR, 'scripts/phase4/load_journey_data_phase4.py'),
            '--db-url', os.environ.get('DATABASE_URL'),
            '--data-dir', OUTPUT_DIR,
            '--processed-dir', PROCESSED_DIR
        ]
        
        print(f"[{run_id}] Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=1200)
        
        if result.returncode != 0:
            raise Exception(f"Database load failed: {result.stderr}")
        
        print(f"[{run_id}] Database load output:\n{result.stdout[-500:]}")
        
        self.update_progress(run_id, 'phase1_generate', 100, 'Data generation complete')
        
        generation_results = {
            'accounts_created': num_accounts,
            'weeks_per_account': 52,
            'total_weeks': num_accounts * 52,
            'pattern_distribution': pattern_mix,
            'output_dir': OUTPUT_DIR,
            'processed_dir': PROCESSED_DIR
        }
        
        return {
            'success': True,
            'phase': 'phase1_generate',
            'results': generation_results
        }
        
    except Exception as e:
        error_msg = f"Phase 1 failed: {str(e)}\n{traceback.format_exc()}"
        wizard_run.mark_failed(error_msg)
        raise


# ============================================================================
# TASK 2: TEST PREDICTIONS
# ============================================================================

@celery.task(base=CallbackTask, bind=True)
def test_predictions_task(self, previous_result, run_id, version):
    """
    Phase 2/3: Test V3 or V4 predictions
    
    Args:
        previous_result: Results from previous task
        run_id: Wizard run ID
        version: 'v3' or 'v4'
    
    Returns:
        dict with prediction results
    """
    
    phase_name = f'phase{2 if version == "v3" else 3}_test_{version}'
    print(f"[{run_id}] Starting {phase_name}")
    
    wizard_run = WizardRun.query.filter_by(run_id=run_id).first()
    self.update_progress(run_id, phase_name, 10, f'Starting {version.upper()} testing')
    
    try:
        # Choose script
        script = 'test_signal_analyst_v3.py' if version == 'v3' else 'test_signal_analyst_v4_smart_override.py'
        
        cmd = [
            'python3',
            script,
            '--db-url', os.environ.get('DATABASE_URL'),
            '--output-dir', f'outputs/wizard_runs/{run_id}'
        ]
        
        if version == 'v4':
            cmd.extend(['--api-key', os.environ.get('OPENAI_API_KEY')])
        
        self.update_progress(run_id, phase_name, 30, f'Running {version.upper()} predictions...')
        
        # Run command
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=1800  # 30 minute timeout (for LLM calls)
        )
        
        if result.returncode != 0:
            raise Exception(f"{version.upper()} testing failed: {result.stderr}")
        
        self.update_progress(run_id, phase_name, 80, 'Parsing results...')
        
        # Parse output (look for accuracy line)
        stdout_lines = result.stdout.split('\n')
        accuracy = None
        for line in stdout_lines:
            if 'Accuracy:' in line:
                try:
                    accuracy = float(line.split(':')[1].strip().replace('%', '')) / 100
                except:
                    pass
        
        test_results = {
            'version': version,
            'accuracy': accuracy,
            'stdout': result.stdout[-1000:]  # Last 1000 chars
        }
        
        self.update_progress(run_id, phase_name, 100, f'{version.upper()} testing complete')
        
        # Merge with previous results
        if previous_result:
            test_results = {**previous_result, **test_results}
        
        return {
            'success': True,
            'phase': phase_name,
            'results': test_results
        }
        
    except Exception as e:
        error_msg = f"{phase_name} failed: {str(e)}\n{traceback.format_exc()}"
        wizard_run.mark_failed(error_msg)
        raise


# ============================================================================
# TASK 3: LEARN ENSEMBLE WEIGHTS
# ============================================================================

@celery.task(base=CallbackTask, bind=True)
def learn_ensemble_weights_task(self, previous_result, run_id):
    """
    Phase 4: Learn optimal ensemble weights
    
    Args:
        previous_result: Results from previous tasks
        run_id: Wizard run ID
    
    Returns:
        dict with learned weights
    """
    
    phase_name = 'phase4_ensemble'
    print(f"[{run_id}] Starting {phase_name}")
    
    wizard_run = WizardRun.query.filter_by(run_id=run_id).first()
    self.update_progress(run_id, phase_name, 10, 'Starting ensemble learning')
    
    try:
        cmd = [
            'python3',
            'auto_ensemble.py',
            '--db-url', os.environ.get('DATABASE_URL'),
            '--output-dir', f'outputs/wizard_runs/{run_id}'
        ]
        
        self.update_progress(run_id, phase_name, 30, 'Learning optimal weights...')
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )
        
        if result.returncode != 0:
            raise Exception(f"Ensemble learning failed: {result.stderr}")
        
        self.update_progress(run_id, phase_name, 80, 'Loading learned weights...')
        
        # Load learned weights
        weights_file = Path(f'outputs/wizard_runs/{run_id}/learned_weights.json')
        if weights_file.exists():
            with open(weights_file) as f:
                learned_weights = json.load(f)
        else:
            learned_weights = {'error': 'Weights file not found'}
        
        ensemble_results = {
            'learned_weights': learned_weights,
            'stdout': result.stdout[-1000:]
        }
        
        self.update_progress(run_id, phase_name, 100, 'Ensemble learning complete')
        
        # Merge with previous results
        if previous_result:
            ensemble_results = {**previous_result, **ensemble_results}
        
        return {
            'success': True,
            'phase': phase_name,
            'results': ensemble_results
        }
        
    except Exception as e:
        error_msg = f"{phase_name} failed: {str(e)}\n{traceback.format_exc()}"
        wizard_run.mark_failed(error_msg)
        raise


# ============================================================================
# TASK 4: GENERATE VISUALIZATIONS
# ============================================================================

@celery.task(base=CallbackTask, bind=True)
def generate_visualizations_task(self, previous_result, run_id):
    """
    Phase 5: Generate visualizations and dashboard
    
    Args:
        previous_result: Results from previous tasks
        run_id: Wizard run ID
    
    Returns:
        dict with visualization paths
    """
    
    phase_name = 'phase5_visualize'
    print(f"[{run_id}] Starting {phase_name}")
    
    wizard_run = WizardRun.query.filter_by(run_id=run_id).first()
    self.update_progress(run_id, phase_name, 10, 'Starting visualization generation')
    
    try:
        config = wizard_run.config
        viz_enabled = config.get('visualizations', {}).get('enabled', [])
        
        cmd = [
            'python3',
            'generate_dashboard.py',  # Create this next if needed
            '--run-id', run_id,
            '--output-dir', f'outputs/wizard_runs/{run_id}',
            '--charts', ','.join(viz_enabled)
        ]
        
        self.update_progress(run_id, phase_name, 30, 'Generating charts...')
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode != 0:
            print(f"[{run_id}] Warning: Visualization generation failed: {result.stderr}")
            # Don't fail the entire pipeline if visualizations fail
        
        self.update_progress(run_id, phase_name, 80, 'Indexing files...')
        
        # Index generated files
        output_dir = Path(f'outputs/wizard_runs/{run_id}')
        generated_files = []
        
        if output_dir.exists():
            for file_path in output_dir.glob('*'):
                if file_path.is_file():
                    wizard_file = WizardFile(
                        run_id=run_id,
                        filename=file_path.name,
                        filepath=str(file_path),
                        file_type=file_path.suffix[1:],  # Remove dot
                        file_size=file_path.stat().st_size,
                        description=f"Generated during {phase_name}"
                    )
                    db.session.add(wizard_file)
                    generated_files.append(file_path.name)
        
        db.session.commit()
        
        viz_results = {
            'generated_files': generated_files,
            'output_dir': str(output_dir)
        }
        
        self.update_progress(run_id, phase_name, 100, 'Visualization complete')
        
        # Merge with previous results
        if previous_result:
            viz_results = {**previous_result, **viz_results}
        
        # Mark wizard run as completed
        wizard_run.mark_completed(viz_results)
        
        # Extract learnings for Wizard B
        extract_learnings_task.delay(run_id)
        
        return {
            'success': True,
            'phase': phase_name,
            'results': viz_results
        }
        
    except Exception as e:
        error_msg = f"{phase_name} failed: {str(e)}\n{traceback.format_exc()}"
        wizard_run.mark_failed(error_msg)
        raise


# ============================================================================
# TASK 5: EXTRACT LEARNINGS (for Wizard B)
# ============================================================================

@celery.task(bind=True)
def extract_learnings_task(self, run_id):
    """
    Extract learnings from wizard run for Wizard B
    
    Args:
        run_id: Wizard run ID
    """
    
    print(f"[{run_id}] Extracting learnings for Wizard B")
    
    try:
        wizard_run = WizardRun.query.filter_by(run_id=run_id).first()
        if not wizard_run or wizard_run.status != 'completed':
            print(f"[{run_id}] Run not completed, skipping learning extraction")
            return
        
        results = wizard_run.results
        
        # Extract key learnings
        learnings = {
            'optimal_weights': results.get('learned_weights', {}).get('weights', {}),
            'accuracy_achieved': results.get('accuracy'),
            'pattern_performance': {},  # TODO: Extract from results
            'threshold_effectiveness': {}  # TODO: Extract from results
        }
        
        # Create learning record
        learning = WizardLearning(
            source_runs=[run_id],
            run_id=run_id,
            learnings=learnings,
            total_accounts_tested=wizard_run.config.get('accounts', 0),
            avg_accuracy=results.get('accuracy')
        )
        
        db.session.add(learning)
        learning.activate()  # Make this the active version
        
        print(f"[{run_id}] Learnings extracted as {learning.version}")
        
        return {
            'success': True,
            'learning_version': learning.version
        }
        
    except Exception as e:
        print(f"[{run_id}] Learning extraction failed: {e}")
        traceback.print_exc()
        # Don't fail the main pipeline if learning extraction fails
        return {
            'success': False,
            'error': str(e)
        }
