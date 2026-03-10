"""
Test Runner API — Drive load-driver scenarios from the UI

Spawns load-driver scenarios as subprocesses, tracks their status,
and returns results to the frontend for display.
"""

import json
import logging
import os
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)

test_runner_api = Blueprint('test_runner_api', __name__)

# ---------------------------------------------------------------------------
# Path to load-driver directory
# ---------------------------------------------------------------------------
# Priority: 1) LOAD_DRIVER_DIR env var  2) /app/load-driver (Docker)
#           3) sibling of kpi-dashboard (local dev)
_BACKEND_DIR = Path(__file__).resolve().parent

def _resolve_load_driver_dir() -> Path:
    """Find load-driver directory across local-dev and Docker environments."""
    # 1) Explicit env var (highest priority)
    env_dir = os.environ.get('LOAD_DRIVER_DIR')
    if env_dir:
        p = Path(env_dir)
        if p.exists():
            return p

    # 2) Docker container path (/app/load-driver)
    docker_path = Path('/app/load-driver')
    if docker_path.exists():
        return docker_path

    # 3) Local dev: sibling of kpi-dashboard
    project_root = _BACKEND_DIR.parent.parent  # CustomerSuccessAI-DataCenter
    local_path = project_root / 'load-driver'
    return local_path  # may not exist, checked at runtime

LOAD_DRIVER_DIR = _resolve_load_driver_dir()
RUN_SCENARIO_SCRIPT = LOAD_DRIVER_DIR / 'run_scenario.py'

# Directory for run results (inside load-driver/results/)
RESULTS_BASE_DIR = LOAD_DRIVER_DIR / 'results' / 'ui-runs'

# ---------------------------------------------------------------------------
# Scenario metadata (mirrors load-driver SCENARIO_MAP)
# ---------------------------------------------------------------------------
SCENARIO_META = {
    '1':  {'name': 'Customer Onboarding',  'group': 'Core',     'description': 'Register, create accounts, load data, calculate scores', 'est_minutes': 8},
    '2a': {'name': 'KPI Simulation',       'group': 'Analytics', 'description': '12-month KPI drift with 5 behavior profiles', 'est_minutes': 5},
    '2b': {'name': 'RAG Queries',          'group': 'AI',       'description': 'Natural language queries against Qdrant', 'est_minutes': 12},
    '2c': {'name': 'Signal Detection',     'group': 'AI',       'description': 'Churn/expansion signals, playbook triggering', 'est_minutes': 5},
    '2d': {'name': 'RACI Reports',         'group': 'Reports',  'description': 'Playbook execution reports and RACI validation', 'est_minutes': 2},
    '2e': {'name': 'Churn Lifecycle',      'group': 'Lifecycle', 'description': 'Account archival, deletion, cascade verification', 'est_minutes': 3},
    '3':  {'name': 'Tenant Isolation',     'group': 'Security', 'description': '12 cross-tenant security tests', 'est_minutes': 5},
    '4':  {'name': 'Customer Cleanup',     'group': 'Admin',    'description': 'FK-safe 24-table delete + filesystem cleanup', 'est_minutes': 2},
    '5':  {'name': 'ROI Power-of-1',       'group': 'Analytics', 'description': 'Historical/forward ROI at 1%/4%/6% improvement', 'est_minutes': 3},
    '6':  {'name': 'N8N Workflow',         'group': 'Integration', 'description': 'Playbook-to-n8n handoff simulation', 'est_minutes': 10},
    '7':  {'name': 'Data Ingestion',       'group': 'Integration', 'description': 'Ring 3: Google Sheets + n8n pipeline simulator', 'est_minutes': 5},
    '8':  {'name': 'Context Graph',        'group': 'Analytics', 'description': 'Story arc → 9 CSVs → context nodes/edges', 'est_minutes': 8},
    '9':  {'name': 'ROI Simulation',       'group': 'Analytics', 'description': 'Weight-aware improvement → ROI pipeline validation', 'est_minutes': 5},
}

# ---------------------------------------------------------------------------
# In-memory run tracker
# ---------------------------------------------------------------------------
_runs: Dict[str, Dict[str, Any]] = {}
_runs_lock = threading.Lock()


def _generate_run_id() -> str:
    return datetime.now().strftime('run_%Y%m%d_%H%M%S')


def _run_scenario_subprocess(run_id: str, scenario_id: str, customer_id: int, base_url: str, options: Dict[str, Any] = None):
    """
    Execute a single scenario via subprocess and update _runs state.
    Called from a background thread.
    """
    output_dir = RESULTS_BASE_DIR / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    # Write a JSON result file alongside the markdown
    json_result_file = output_dir / f"scenario_{scenario_id}.json"

    # Update status to running
    with _runs_lock:
        for s in _runs[run_id]['scenarios']:
            if s['id'] == scenario_id:
                s['status'] = 'running'
                s['start_time'] = datetime.now().isoformat()
                break

    try:
        cmd = [
            sys.executable,
            str(RUN_SCENARIO_SCRIPT),
            '--scenario', scenario_id,
            '--customer-id', str(customer_id),
            '--base-url', base_url,
            '--output-dir', str(output_dir),
            '--verbose'
        ]

        # Append advanced options as CLI flags (from UI Advanced Options panel)
        if options:
            if options.get('num_accounts'):
                cmd.extend(['--num-accounts', str(int(options['num_accounts']))])
            if options.get('dry_run'):
                cmd.append('--dry-run')
            if options.get('seed') is not None:
                cmd.extend(['--seed', str(int(options['seed']))])
            if options.get('industry'):
                cmd.extend(['--industry', str(options['industry'])])
            if options.get('onboarding_mode'):
                cmd.extend(['--onboarding-mode', str(options['onboarding_mode'])])
            if options.get('showcase_pattern_mix'):
                cmd.extend(['--showcase-pattern-mix', json.dumps(options['showcase_pattern_mix'])])
            if options.get('weights'):
                cmd.extend(['--weights', json.dumps(options['weights'])])

        logger.info(f"[{run_id}] Starting scenario {scenario_id}: {' '.join(cmd)}")

        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,  # 10 minute max per scenario
            cwd=str(LOAD_DRIVER_DIR)
        )

        exit_code = proc.returncode
        stdout = proc.stdout
        stderr = proc.stderr

        # Try to read the markdown result file for structured data
        md_file = output_dir / f"{customer_id}-test_results.md"
        result_data = _parse_result_from_md(md_file)

        if result_data is None:
            # Fallback: infer from exit code
            result_data = {
                'status': 'success' if exit_code == 0 else 'failure',
                'message': f'Scenario {scenario_id} exited with code {exit_code}',
                'duration_seconds': 0,
                'details': {},
            }

        # Save JSON result
        json_result_file.write_text(json.dumps(result_data, indent=2, default=str))

        # Update run state
        with _runs_lock:
            for s in _runs[run_id]['scenarios']:
                if s['id'] == scenario_id:
                    s['status'] = 'pass' if result_data.get('status') == 'success' else 'fail'
                    s['end_time'] = datetime.now().isoformat()
                    s['result'] = result_data
                    s['exit_code'] = exit_code
                    if stderr and exit_code != 0:
                        s['stderr'] = stderr[-500:]  # last 500 chars
                    break

        logger.info(f"[{run_id}] Scenario {scenario_id} finished: {result_data.get('status')}")

    except subprocess.TimeoutExpired:
        with _runs_lock:
            for s in _runs[run_id]['scenarios']:
                if s['id'] == scenario_id:
                    s['status'] = 'fail'
                    s['end_time'] = datetime.now().isoformat()
                    s['result'] = {'status': 'failure', 'message': 'Timeout (10 minutes)', 'duration_seconds': 600}
                    break
        logger.error(f"[{run_id}] Scenario {scenario_id} timed out")

    except Exception as e:
        with _runs_lock:
            for s in _runs[run_id]['scenarios']:
                if s['id'] == scenario_id:
                    s['status'] = 'fail'
                    s['end_time'] = datetime.now().isoformat()
                    s['result'] = {'status': 'failure', 'message': str(e), 'duration_seconds': 0}
                    break
        logger.error(f"[{run_id}] Scenario {scenario_id} error: {e}")


def _run_all_scenarios(run_id: str, scenario_ids: list, customer_id: int, base_url: str, options: Dict[str, Any] = None):
    """Run scenarios sequentially in a background thread."""
    for scenario_id in scenario_ids:
        _run_scenario_subprocess(run_id, scenario_id, customer_id, base_url, options)

    # Mark run as completed
    with _runs_lock:
        run = _runs[run_id]
        run['status'] = 'completed'
        run['end_time'] = datetime.now().isoformat()

        # Calculate summary
        scenarios = run['scenarios']
        passed = sum(1 for s in scenarios if s['status'] == 'pass')
        failed = sum(1 for s in scenarios if s['status'] == 'fail')
        total_duration = sum(
            s.get('result', {}).get('duration_seconds', 0)
            for s in scenarios
        )
        run['summary'] = {
            'total': len(scenarios),
            'passed': passed,
            'failed': failed,
            'duration_seconds': round(total_duration, 2),
        }

    logger.info(f"[{run_id}] All scenarios complete: {passed}/{len(scenarios)} passed")


def _parse_result_from_md(md_file: Path) -> Optional[Dict[str, Any]]:
    """Extract JSON result from the markdown file's Raw Result section."""
    if not md_file.exists():
        return None

    content = md_file.read_text()

    # Find the ```json block at the end
    json_start = content.rfind('```json')
    if json_start == -1:
        return None

    json_start = content.index('\n', json_start) + 1
    json_end = content.index('```', json_start)
    json_str = content[json_start:json_end].strip()

    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return None


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@test_runner_api.route('/api/test-runner/scenarios', methods=['GET'])
def list_scenarios():
    """List all available scenarios with metadata."""
    scenarios = []
    for sid, meta in SCENARIO_META.items():
        scenarios.append({
            'id': sid,
            'name': meta['name'],
            'group': meta['group'],
            'description': meta['description'],
            'est_minutes': meta['est_minutes'],
        })
    return jsonify({'scenarios': scenarios})


@test_runner_api.route('/api/test-runner/start', methods=['POST'])
def start_run():
    """
    Start a test run with selected scenarios.

    Body: { scenario_ids: ["1", "4"], customer_id: 500 }
    """
    data = request.get_json() or {}
    scenario_ids = data.get('scenario_ids', [])
    customer_id = data.get('customer_id')

    if not scenario_ids:
        return jsonify({'error': 'No scenarios selected'}), 400
    if not customer_id:
        return jsonify({'error': 'customer_id is required'}), 400

    # Validate scenario IDs
    invalid = [s for s in scenario_ids if s not in SCENARIO_META]
    if invalid:
        return jsonify({'error': f'Unknown scenarios: {invalid}'}), 400

    # Check load-driver exists
    if not RUN_SCENARIO_SCRIPT.exists():
        return jsonify({'error': f'Load driver not found at {RUN_SCENARIO_SCRIPT}'}), 500

    # Determine base URL (the backend itself)
    base_url = data.get('base_url', 'http://localhost:5059')

    # Advanced options from UI (num_accounts, dry_run, seed, industry, etc.)
    options = data.get('options', {})

    # Entitlement check: filter advanced options based on customer tier
    stripped_options = []
    try:
        from entitlements import filter_test_runner_options
        options, stripped_options = filter_test_runner_options(int(customer_id), options)
        if stripped_options:
            logger.info(f"Entitlement gate: stripped advanced options {stripped_options} for customer {customer_id}")
    except ImportError:
        pass  # entitlements module not available — allow all options

    run_id = _generate_run_id()

    run_entry = {
        'run_id': run_id,
        'status': 'running',
        'customer_id': customer_id,
        'base_url': base_url,
        'start_time': datetime.now().isoformat(),
        'end_time': None,
        'scenarios': [
            {
                'id': sid,
                'name': SCENARIO_META[sid]['name'],
                'status': 'pending',
                'start_time': None,
                'end_time': None,
                'result': None,
            }
            for sid in scenario_ids
        ],
        'summary': None,
        'options': options,  # Store for observability in status responses
    }

    with _runs_lock:
        _runs[run_id] = run_entry

    # Spawn background thread
    t = threading.Thread(
        target=_run_all_scenarios,
        args=(run_id, scenario_ids, customer_id, base_url, options),
        daemon=True
    )
    t.start()

    return jsonify({
        'run_id': run_id,
        'status': 'running',
        'scenarios': len(scenario_ids),
        'customer_id': customer_id,
    })


@test_runner_api.route('/api/test-runner/status/<run_id>', methods=['GET'])
def get_run_status(run_id):
    """Poll run status — returns current state of all scenarios."""
    with _runs_lock:
        run = _runs.get(run_id)

    if not run:
        return jsonify({'error': f'Run {run_id} not found'}), 404

    return jsonify(run)


@test_runner_api.route('/api/test-runner/runs', methods=['GET'])
def list_runs():
    """List all runs (most recent first)."""
    with _runs_lock:
        runs_list = sorted(
            _runs.values(),
            key=lambda r: r['start_time'],
            reverse=True
        )

    # Return summary view (without full result details to keep response small)
    summaries = []
    for run in runs_list:
        summaries.append({
            'run_id': run['run_id'],
            'status': run['status'],
            'customer_id': run['customer_id'],
            'start_time': run['start_time'],
            'end_time': run['end_time'],
            'scenario_count': len(run['scenarios']),
            'summary': run.get('summary'),
        })

    return jsonify({'runs': summaries})


@test_runner_api.route('/api/test-runner/runs/<run_id>', methods=['DELETE'])
def delete_run(run_id):
    """Remove a run from history."""
    with _runs_lock:
        if run_id in _runs:
            del _runs[run_id]
            return jsonify({'deleted': run_id})

    return jsonify({'error': f'Run {run_id} not found'}), 404
