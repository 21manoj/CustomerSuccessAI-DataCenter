"""
Test Runner API — Drive load-driver scenarios from the UI

Spawns load-driver scenarios as subprocesses, tracks their status,
and returns results to the frontend for display.
"""

import glob as globmod
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
# Scenario → required feature toggles mapping
# ---------------------------------------------------------------------------
SCENARIO_FEATURE_TOGGLES = {
    '5':  ['revenue_intelligence'],
    '8':  ['context_graph'],
    '9':  ['revenue_intelligence'],
}


def _ensure_feature_toggles(customer_id: int, scenario_ids: list):
    """Auto-enable per-customer feature toggles required by the selected scenarios."""
    toggles_needed = set()
    for sid in scenario_ids:
        toggles_needed.update(SCENARIO_FEATURE_TOGGLES.get(sid, []))
    if not toggles_needed:
        return

    try:
        from models import db
        from models import FeatureToggle as FTModel
        from models import CustomerConfig

        for toggle_name in toggles_needed:
            existing = FTModel.query.filter_by(
                customer_id=customer_id,
                feature_name=toggle_name
            ).first()
            if existing:
                if not existing.enabled:
                    existing.enabled = True
                    logger.info(f"Auto-enabled feature toggle '{toggle_name}' for customer {customer_id}")
            else:
                db.session.add(FTModel(
                    customer_id=customer_id,
                    feature_name=toggle_name,
                    enabled=True,
                    description=f'Auto-enabled by test runner for scenarios {scenario_ids}',
                ))
                logger.info(f"Created feature toggle '{toggle_name}' for customer {customer_id}")

        # Ensure customer tier is at least 'professional' for entitlement checks
        cc = CustomerConfig.query.filter_by(customer_id=customer_id).first()
        if cc:
            if cc.tier in (None, 'starter'):
                cc.tier = 'professional'
                logger.info(f"Upgraded customer {customer_id} tier to 'professional' for test scenarios")
        else:
            db.session.add(CustomerConfig(
                customer_id=customer_id,
                tier='professional',
            ))
            logger.info(f"Created CustomerConfig with tier 'professional' for customer {customer_id}")

        db.session.commit()
    except Exception as e:
        logger.warning(f"Failed to auto-enable feature toggles: {e}")


# ---------------------------------------------------------------------------
# Disk-backed run tracker (survives multi-worker / restarts)
# ---------------------------------------------------------------------------
# Each run is stored as a JSON file in RESULTS_BASE_DIR/<run_id>/run_state.json
# This ensures all gunicorn workers see the same state.
_runs_lock = threading.Lock()

# In-memory cache (per-worker) — used for the background thread writing state.
# Reads always go to disk first; the cache is only for the thread that owns the run.
_runs_cache: Dict[str, Dict[str, Any]] = {}


def _generate_run_id() -> str:
    return datetime.now().strftime('run_%Y%m%d_%H%M%S')


def _run_state_path(run_id: str) -> Path:
    return RESULTS_BASE_DIR / run_id / 'run_state.json'


def _save_run(run_id: str, run: Dict[str, Any]) -> None:
    """Persist run state to disk (called from background thread)."""
    state_file = _run_state_path(run_id)
    state_file.parent.mkdir(parents=True, exist_ok=True)
    try:
        state_file.write_text(json.dumps(run, indent=2, default=str))
    except Exception as e:
        logger.warning(f"Failed to persist run state for {run_id}: {e}")


def _load_run(run_id: str) -> Optional[Dict[str, Any]]:
    """Load run state from disk."""
    state_file = _run_state_path(run_id)
    if not state_file.exists():
        return None
    try:
        return json.loads(state_file.read_text())
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Failed to read run state for {run_id}: {e}")
        return None


def _list_all_runs() -> list:
    """List all run state files from disk."""
    runs = []
    if not RESULTS_BASE_DIR.exists():
        return runs
    for state_file in RESULTS_BASE_DIR.glob('run_*/run_state.json'):
        try:
            run = json.loads(state_file.read_text())
            runs.append(run)
        except (json.JSONDecodeError, OSError):
            continue
    return runs


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
        run = _runs_cache.get(run_id, {})
        for s in run.get('scenarios', []):
            if s['id'] == scenario_id:
                s['status'] = 'running'
                s['start_time'] = datetime.now().isoformat()
                break
        _save_run(run_id, run)

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
            # KPI Configuration (Scenario 1: Onboarding)
            if options.get('enabled_pillars'):
                cmd.extend(['--enabled-pillars', json.dumps(options['enabled_pillars'])])
            if options.get('enabled_kpis'):
                cmd.extend(['--enabled-kpis', json.dumps(options['enabled_kpis'])])
            # Scenario 8: Context Graph options
            if options.get('arc_id'):
                cmd.extend(['--arc-id', str(options['arc_id'])])
            # Scenario 9: ROI Simulation options
            if options.get('months'):
                cmd.extend(['--months', str(int(options['months']))])
            if options.get('improvement'):
                cmd.extend(['--improvement', str(float(options['improvement']))])

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

        # Collect artifact paths for this run
        artifacts = {
            'test_results_md': str(md_file) if md_file.exists() else None,
            'result_json': str(json_result_file),
            'run_dir': str(output_dir),
        }

        # For Scenario 1 (Onboarding): include CSV directory
        if scenario_id == '1' and result_data.get('details', {}).get('customer_id'):
            cid = result_data['details']['customer_id']
            csv_dir = Path(__file__).parent / 'verticals' / f'customer{cid}-dc2_s' / 'data'
            if csv_dir.exists():
                csv_files = sorted([f.name for f in csv_dir.glob('*.csv')])
                artifacts['csv_dir'] = str(csv_dir)
                artifacts['csv_files'] = csv_files
                # Context graph CSVs (subdirectory)
                cg_dir = csv_dir / 'context_graph'
                if cg_dir.exists():
                    cg_files = sorted([f.name for f in cg_dir.glob('*.csv')])
                    if cg_files:
                        artifacts['context_graph_dir'] = str(cg_dir)
                        artifacts['context_graph_files'] = cg_files

        # For Scenario 8 (Context Graph): include context graph CSV directory
        if scenario_id == '8' and result_data.get('details', {}).get('customer_id'):
            cid = result_data['details'].get('customer_id', customer_id)
            cg_dir = Path(__file__).parent / 'verticals' / f'customer{cid}-dc2_s' / 'data' / 'context_graph'
            if cg_dir.exists():
                cg_files = sorted([f.name for f in cg_dir.glob('*.csv')])
                if cg_files:
                    artifacts['context_graph_dir'] = str(cg_dir)
                    artifacts['context_graph_files'] = cg_files

        result_data['artifacts'] = artifacts

        # Save JSON result
        json_result_file.write_text(json.dumps(result_data, indent=2, default=str))

        # Update run state
        with _runs_lock:
            run = _runs_cache.get(run_id, {})
            for s in run.get('scenarios', []):
                if s['id'] == scenario_id:
                    s['status'] = 'pass' if result_data.get('status') == 'success' else 'fail'
                    s['end_time'] = datetime.now().isoformat()
                    s['result'] = result_data
                    s['exit_code'] = exit_code
                    # Always capture stdout/stderr for visibility in UI
                    if stdout:
                        s['stdout'] = stdout[-3000:]  # last 3000 chars
                    if stderr:
                        s['stderr'] = stderr[-1500:]  # last 1500 chars
                    break
            _save_run(run_id, run)

        logger.info(f"[{run_id}] Scenario {scenario_id} finished: {result_data.get('status')}")

    except subprocess.TimeoutExpired:
        with _runs_lock:
            run = _runs_cache.get(run_id, {})
            for s in run.get('scenarios', []):
                if s['id'] == scenario_id:
                    s['status'] = 'fail'
                    s['end_time'] = datetime.now().isoformat()
                    s['result'] = {'status': 'failure', 'message': 'Timeout (10 minutes)', 'duration_seconds': 600}
                    break
            _save_run(run_id, run)
        logger.error(f"[{run_id}] Scenario {scenario_id} timed out")

    except Exception as e:
        with _runs_lock:
            run = _runs_cache.get(run_id, {})
            for s in run.get('scenarios', []):
                if s['id'] == scenario_id:
                    s['status'] = 'fail'
                    s['end_time'] = datetime.now().isoformat()
                    s['result'] = {'status': 'failure', 'message': str(e), 'duration_seconds': 0}
                    break
            _save_run(run_id, run)
        logger.error(f"[{run_id}] Scenario {scenario_id} error: {e}")


def _run_all_scenarios(run_id: str, scenario_ids: list, customer_id: int, base_url: str, options: Dict[str, Any] = None):
    """Run scenarios sequentially in a background thread."""
    for scenario_id in scenario_ids:
        _run_scenario_subprocess(run_id, scenario_id, customer_id, base_url, options)

    # Mark run as completed
    with _runs_lock:
        run = _runs_cache.get(run_id, {})
        run['status'] = 'completed'
        run['end_time'] = datetime.now().isoformat()

        # Calculate summary
        scenarios = run.get('scenarios', [])
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
        _save_run(run_id, run)

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
           For Scenario 1 (Onboarding) with new customer: customer_id can be "auto" or 0.
    """
    data = request.get_json() or {}
    scenario_ids = data.get('scenario_ids', [])
    customer_id = data.get('customer_id')

    if not scenario_ids:
        return jsonify({'error': 'No scenarios selected'}), 400

    # Validate scenario IDs
    invalid = [s for s in scenario_ids if s not in SCENARIO_META]
    if invalid:
        return jsonify({'error': f'Unknown scenarios: {invalid}'}), 400

    # New Customer (auto) mode: for Scenario 1, customer_id is optional.
    # The onboarding API auto-generates a new customer_id.
    is_new_customer = not customer_id or str(customer_id) in ('0', 'auto', '')
    if is_new_customer:
        if scenario_ids == ['1']:
            # Scenario 1 = Onboarding: auto-generate customer_id.
            # Use a high random ID as the CLI still requires --customer-id for auth context.
            import random
            customer_id = random.randint(800000, 999999)
            logger.info(f"New Customer (auto) mode: generated temp customer_id={customer_id} for onboarding")
        else:
            return jsonify({'error': 'customer_id is required (use "auto" only for Scenario 1 onboarding)'}), 400

    # Check load-driver exists
    if not RUN_SCENARIO_SCRIPT.exists():
        return jsonify({'error': f'Load driver not found at {RUN_SCENARIO_SCRIPT}'}), 500

    # Determine base URL (the backend itself)
    base_url = data.get('base_url', 'http://localhost:5059')

    # Advanced options from UI (num_accounts, dry_run, seed, industry, etc.)
    options = data.get('options', {})

    # Entitlement check: filter advanced options based on customer tier
    # (skip for new/auto customers — no entitlements yet)
    stripped_options = []
    if not is_new_customer:
        try:
            from entitlements import filter_test_runner_options
            options, stripped_options = filter_test_runner_options(int(customer_id), options)
            if stripped_options:
                logger.info(f"Entitlement gate: stripped advanced options {stripped_options} for customer {customer_id}")
        except ImportError:
            pass  # entitlements module not available — allow all options

    # Auto-enable required feature toggles for test runner scenarios.
    # Scenarios 5/8/9 need revenue_intelligence and context_graph enabled.
    # (skip for new/auto customers — toggles will be set after onboarding)
    if not is_new_customer:
        _ensure_feature_toggles(int(customer_id), scenario_ids)

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
        _runs_cache[run_id] = run_entry
        _save_run(run_id, run_entry)

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
    # Try in-memory cache first (same worker that created the run)
    with _runs_lock:
        run = _runs_cache.get(run_id)

    # Fall back to disk (different worker or after restart)
    if not run:
        run = _load_run(run_id)

    if not run:
        return jsonify({'error': f'Run {run_id} not found'}), 404

    return jsonify(run)


@test_runner_api.route('/api/test-runner/runs', methods=['GET'])
def list_runs():
    """List all runs (most recent first)."""
    # Load from disk (works across workers)
    all_runs = _list_all_runs()
    runs_list = sorted(all_runs, key=lambda r: r.get('start_time', ''), reverse=True)

    # Return summary view (without full result details to keep response small)
    summaries = []
    for run in runs_list:
        summaries.append({
            'run_id': run.get('run_id', ''),
            'status': run.get('status', 'unknown'),
            'customer_id': run.get('customer_id', ''),
            'start_time': run.get('start_time', ''),
            'end_time': run.get('end_time'),
            'scenario_count': len(run.get('scenarios', [])),
            'summary': run.get('summary'),
        })

    return jsonify({'runs': summaries})


@test_runner_api.route('/api/test-runner/runs/<run_id>', methods=['DELETE'])
def delete_run(run_id):
    """Remove a run from history."""
    deleted = False

    with _runs_lock:
        if run_id in _runs_cache:
            del _runs_cache[run_id]
            deleted = True

    # Also remove from disk
    state_file = _run_state_path(run_id)
    if state_file.exists():
        try:
            state_file.unlink()
            deleted = True
        except OSError:
            pass

    if deleted:
        return jsonify({'deleted': run_id})
    return jsonify({'error': f'Run {run_id} not found'}), 404


# ---------------------------------------------------------------------------
# Platform State Endpoint (Tab 2)
# ---------------------------------------------------------------------------

@test_runner_api.route('/api/test-runner/platform-state', methods=['GET'])
def get_platform_state():
    """
    Return live platform state for a customer: accounts, health scores, ARR,
    pillar breakdowns, and context graph node counts.

    Query params: customer_id (required)
    """
    customer_id = request.args.get('customer_id')
    if not customer_id:
        return jsonify({'error': 'customer_id query param is required'}), 400

    try:
        customer_id = int(customer_id)
    except ValueError:
        return jsonify({'error': 'customer_id must be an integer'}), 400

    try:
        from models import db, Customer, Account, PrecalculatedScore, ContextNode
        import utils.health_thresholds as ht
    except ImportError as e:
        return jsonify({'error': f'Import error: {e}'}), 500

    customer = Customer.query.get(customer_id)
    if not customer:
        return jsonify({'error': f'Customer {customer_id} not found'}), 404

    accounts = Account.query.filter_by(customer_id=customer_id, is_active=True).all()

    account_list = []
    total_arr = 0
    health_scores = []
    healthy = at_risk = critical = 0
    total_cg_nodes = 0

    for acct in accounts:
        # Get latest precalculated score
        latest_score = (
            PrecalculatedScore.query
            .filter_by(account_id=acct.id, customer_id=customer_id)
            .order_by(PrecalculatedScore.calculated_at.desc())
            .first()
        )

        health_score = latest_score.overall_score if latest_score else None
        pillar_scores = {}
        if latest_score and latest_score.pillar_scores:
            pillar_scores = latest_score.pillar_scores

        # Count context graph nodes for this account
        cg_count = (
            ContextNode.query
            .filter_by(account_id=acct.id, customer_id=customer_id)
            .count()
        )
        total_cg_nodes += cg_count

        arr = float(acct.arr or 0)
        total_arr += arr

        if health_score is not None:
            health_scores.append(health_score)
            status = ht.classify(health_score)
            if status == 'critical':
                critical += 1
            elif status == 'at_risk':
                at_risk += 1
            else:
                healthy += 1
        else:
            status = 'unknown'

        # Find latest KPI date
        latest_kpi_date = None
        if latest_score and latest_score.calculated_at:
            latest_kpi_date = latest_score.calculated_at.isoformat()

        account_list.append({
            'account_id': acct.id,
            'account_name': acct.name,
            'health_score': round(health_score, 1) if health_score else None,
            'status': status,
            'arr': arr,
            'pillar_scores': pillar_scores,
            'context_graph_nodes': cg_count,
            'latest_kpi_date': latest_kpi_date,
        })

    # Sort worst-first
    account_list.sort(key=lambda a: a['health_score'] if a['health_score'] is not None else 999)

    # Check if context graph feature is enabled
    cg_enabled = False
    try:
        from feature_toggles import is_feature_enabled
        cg_enabled = is_feature_enabled('CONTEXT_GRAPH', customer_id)
    except Exception:
        cg_enabled = total_cg_nodes > 0

    avg_health = round(sum(health_scores) / len(health_scores), 1) if health_scores else None

    return jsonify({
        'customer_id': customer_id,
        'customer_name': customer.name,
        'accounts': account_list,
        'summary': {
            'total_accounts': len(account_list),
            'avg_health': avg_health,
            'total_arr': total_arr,
            'healthy': healthy,
            'at_risk': at_risk,
            'critical': critical,
            'context_graph_enabled': cg_enabled,
            'total_cg_nodes': total_cg_nodes,
        },
    })


# ---------------------------------------------------------------------------
# Story Arcs Endpoint (for Scenario 8 dropdown)
# ---------------------------------------------------------------------------

@test_runner_api.route('/api/test-runner/story-arcs', methods=['GET'])
def list_story_arcs():
    """
    List available story arc manifests from config/story_arcs/.
    Returns arc_id, arc_name, description, target_audience, arr_start, arr_end.
    """
    config_dir = _BACKEND_DIR / 'config' / 'story_arcs'
    arcs = []

    if not config_dir.exists():
        return jsonify({'arcs': arcs})

    for arc_file in sorted(config_dir.glob('arc_*.json')):
        try:
            with open(arc_file, 'r') as f:
                manifest = json.load(f)
            meta = manifest.get('metadata', manifest)
            arcs.append({
                'arc_id': meta.get('arc_id', arc_file.stem.replace('arc_', '')),
                'arc_name': meta.get('arc_name', arc_file.stem),
                'description': meta.get('description', ''),
                'target_audience': meta.get('target_audience', ''),
                'arr_start': meta.get('arr_start', meta.get('arr_range', {}).get('start', 0)),
                'arr_end': meta.get('arr_end', meta.get('arr_range', {}).get('end', 0)),
            })
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Skipping {arc_file}: {e}")

    return jsonify({'arcs': arcs})


# ---------------------------------------------------------------------------
# Power-of-1 Endpoint (for Analytics tab)
# ---------------------------------------------------------------------------

@test_runner_api.route('/api/test-runner/power-of-1', methods=['GET'])
def calculate_power_of_1():
    """
    Calculate Power-of-1 revenue impact.

    Query params:
      - customer_id (required)
      - metric_id (required): NRR, GRR, product_adoption, expansion_rate, ticket_resolution_time, TTFV
      - improvement_pct (optional, default 1.0)
      - account_arr (optional, overrides portfolio total)
    """
    customer_id = request.args.get('customer_id')
    metric_id = request.args.get('metric_id')
    improvement_pct = float(request.args.get('improvement_pct', 1.0))
    account_arr = request.args.get('account_arr')

    if not customer_id:
        return jsonify({'error': 'customer_id is required'}), 400
    if not metric_id:
        return jsonify({'error': 'metric_id is required'}), 400

    try:
        customer_id = int(customer_id)
    except ValueError:
        return jsonify({'error': 'customer_id must be an integer'}), 400

    try:
        from power_of_1_model import calculate_power_of_1_impact
        result = calculate_power_of_1_impact(
            customer_id=customer_id,
            metric_id=metric_id,
            improvement_pct=improvement_pct,
            account_arr=float(account_arr) if account_arr else None,
        )
        return jsonify(result)
    except ImportError:
        # Fallback: simple estimation
        arr_basis = float(account_arr) if account_arr else 10_000_000
        annual_impact = arr_basis * (improvement_pct / 100)
        return jsonify({
            'metric_id': metric_id,
            'improvement_pct': improvement_pct,
            'arr_basis': arr_basis,
            'annual_impact': round(annual_impact, 2),
            'monthly_impact': round(annual_impact / 12, 2),
            'description': f'{improvement_pct}% improvement in {metric_id}',
            'source': 'fallback_estimate',
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ---------------------------------------------------------------------------
# Customer List Endpoint (for dropdown)
# ---------------------------------------------------------------------------

@test_runner_api.route('/api/test-runner/customers', methods=['GET'])
def list_customers_for_dropdown():
    """List existing customers for the Test Runner dropdown."""
    try:
        from models import db, Customer, Account
    except ImportError as e:
        return jsonify({'error': f'Import error: {e}'}), 500

    customers = Customer.query.order_by(Customer.customer_id.desc()).all()
    result = []
    for c in customers:
        acct_count = Account.query.filter_by(customer_id=c.customer_id).count()
        result.append({
            'customer_id': c.customer_id,
            'customer_name': c.customer_name or f'Customer {c.customer_id}',
            'vertical': c.vertical or 'dc2_s',
            'account_count': acct_count,
        })

    return jsonify({'customers': result})


# ---------------------------------------------------------------------------
# Simulation Endpoints (continuous KPI injection)
# ---------------------------------------------------------------------------

_simulations: Dict[str, Dict[str, Any]] = {}
_sim_lock = threading.Lock()


def _generate_kpi_value(base_value: float, target: float, day: int, total_days: int, profile: str) -> float:
    """Generate a KPI value with drift based on profile.

    Profiles:
      - stable:    small noise around base
      - expansion: gradual improvement toward target
      - churn:     gradual degradation away from target
      - crisis:    sharp degradation
      - mixed:     random per-account blend
    """
    import random
    import math

    noise = random.gauss(0, 0.02)  # 2% noise
    progress = day / max(total_days, 1)

    if profile == 'stable':
        value = base_value * (1 + noise)
    elif profile == 'expansion':
        value = base_value + (target - base_value) * progress * 0.8 + base_value * noise
    elif profile == 'churn':
        decay = 1 - progress * 0.4  # drop up to 40%
        value = base_value * decay + base_value * noise
    elif profile == 'crisis':
        decay = 1 - progress * 0.7  # drop up to 70%
        value = base_value * max(decay, 0.3) + base_value * noise
    else:  # mixed
        r = random.random()
        if r < 0.5:
            value = base_value * (1 + noise)
        elif r < 0.75:
            value = base_value + (target - base_value) * progress * 0.6 + base_value * noise
        else:
            decay = 1 - progress * 0.3
            value = base_value * decay + base_value * noise

    return max(0, round(value, 2))


def _simulation_thread(customer_id: int, interval_seconds: int, num_days: int, drift_profile: str, base_url: str):
    """Background thread: inject KPI data for each simulated day."""
    import time as _time
    from datetime import date, timedelta

    sim_key = str(customer_id)
    logger.info(f"[SIM-{customer_id}] Starting simulation: {num_days} days, {interval_seconds}s interval, profile={drift_profile}")

    try:
        # Load account + KPI info
        from models import db, Account, CustomerConfig
        from flask import current_app

        with current_app.app_context():
            config = CustomerConfig.query.filter_by(customer_id=customer_id, vertical='dc2_s').first()
            if not config:
                with _sim_lock:
                    _simulations[sim_key]['status'] = 'error'
                    _simulations[sim_key]['error'] = f'No DC2_S config for customer {customer_id}'
                return

            enabled_kpis = config.dc2s_enabled_kpis or []
            if not enabled_kpis:
                # Fall back to all 38 KPIs
                try:
                    from verticals.dc2_s.kpi_definitions import get_all_kpis
                    all_kpis = get_all_kpis()
                    enabled_kpis = list(all_kpis.keys())
                except Exception:
                    enabled_kpis = [f'P{p}-KPI{k}' for p in range(1, 6) for k in range(1, 9)]

            accounts = Account.query.filter_by(customer_id=customer_id, is_active=True).all()
            if not accounts:
                with _sim_lock:
                    _simulations[sim_key]['status'] = 'error'
                    _simulations[sim_key]['error'] = f'No active accounts for customer {customer_id}'
                return

            account_ids = [a.id for a in accounts]

            # Load KPI definitions for targets
            kpi_targets = {}
            try:
                from verticals.dc2_s.kpi_definitions import get_all_kpis
                all_kpi_defs = get_all_kpis()
                for code, kdef in all_kpi_defs.items():
                    kpi_targets[code] = kdef.get('target', 80)
            except Exception:
                pass

        # Initialize base values (random starting point 60-90% of target)
        import random
        random.seed(customer_id)
        base_values: Dict[str, Dict[str, float]] = {}  # {account_id: {kpi_code: base_value}}
        for aid in account_ids:
            base_values[str(aid)] = {}
            for kpi in enabled_kpis:
                target = kpi_targets.get(kpi, 80)
                base_values[str(aid)][kpi] = target * random.uniform(0.60, 0.95)

        # Per-account drift profiles (for "mixed" mode)
        account_profiles = {}
        profiles_pool = ['stable', 'expansion', 'churn', 'crisis', 'stable', 'stable', 'expansion']
        for i, aid in enumerate(account_ids):
            if drift_profile == 'mixed':
                account_profiles[aid] = profiles_pool[i % len(profiles_pool)]
            else:
                account_profiles[aid] = drift_profile

        start_date = date.today() - timedelta(days=num_days)
        sim_start_time = _time.time()

        for day_num in range(1, num_days + 1):
            # Check if stopped
            with _sim_lock:
                if _simulations.get(sim_key, {}).get('stop_requested'):
                    _simulations[sim_key]['status'] = 'stopped'
                    logger.info(f"[SIM-{customer_id}] Stopped at day {day_num}")
                    return

            current_date = start_date + timedelta(days=day_num)
            date_str = current_date.isoformat()

            # Generate KPI data for all accounts
            kpi_rows = []
            for aid in account_ids:
                prof = account_profiles[aid]
                for kpi_code in enabled_kpis:
                    target = kpi_targets.get(kpi_code, 80)
                    base = base_values[str(aid)].get(kpi_code, target * 0.75)
                    value = _generate_kpi_value(base, target, day_num, num_days, prof)
                    kpi_rows.append({
                        'account_id': aid,
                        'kpi_code': kpi_code,
                        'measured_at': date_str,
                        'value': value,
                        'target': target,
                    })
                    # Update base for next day (running average)
                    base_values[str(aid)][kpi_code] = base * 0.7 + value * 0.3

            # Inject via data-ingestion API (internal call)
            try:
                with current_app.app_context():
                    with current_app.test_client() as tc:
                        resp = tc.post(
                            '/api/data-ingestion/kpis',
                            json={'kpis': kpi_rows},
                            headers={'X-Customer-ID': str(customer_id), 'Content-Type': 'application/json'},
                        )
                        injected_ok = resp.status_code == 200
            except Exception as e:
                logger.warning(f"[SIM-{customer_id}] Day {day_num} injection error: {e}")
                injected_ok = False

            # Recalculate scores every 30 simulated days
            recalc_msg = ''
            if day_num % 30 == 0 or day_num == num_days:
                try:
                    with current_app.app_context():
                        with current_app.test_client() as tc:
                            resp = tc.post(
                                '/api/dc2s/scores/calculate',
                                json={'customer_id': customer_id},
                                headers={'X-Customer-ID': str(customer_id), 'Content-Type': 'application/json'},
                            )
                            if resp.status_code == 200:
                                recalc_msg = f' | scores recalculated'
                except Exception as e:
                    recalc_msg = f' | score recalc error: {e}'

            # Update progress
            elapsed = _time.time() - sim_start_time
            with _sim_lock:
                _simulations[sim_key].update({
                    'current_day': day_num,
                    'current_date': date_str,
                    'kpis_injected': day_num * len(kpi_rows) // max(day_num, 1) * day_num,
                    'last_inject_ok': injected_ok,
                    'elapsed_seconds': round(elapsed, 1),
                })

            if day_num % 10 == 0 or day_num == 1:
                logger.info(f"[SIM-{customer_id}] Day {day_num}/{num_days} ({date_str}) — {len(kpi_rows)} KPIs{recalc_msg}")

            # Wait for next interval
            _time.sleep(interval_seconds)

        # Completed
        with _sim_lock:
            _simulations[sim_key]['status'] = 'completed'
            _simulations[sim_key]['elapsed_seconds'] = round(_time.time() - sim_start_time, 1)

        logger.info(f"[SIM-{customer_id}] Simulation complete: {num_days} days in {_simulations[sim_key]['elapsed_seconds']}s")

    except Exception as e:
        logger.error(f"[SIM-{customer_id}] Simulation error: {e}")
        with _sim_lock:
            _simulations[sim_key]['status'] = 'error'
            _simulations[sim_key]['error'] = str(e)


@test_runner_api.route('/api/test-runner/simulate/start', methods=['POST'])
def start_simulation():
    """
    Start continuous KPI injection simulation for a customer.

    Body: { customer_id, interval_seconds: 10, num_days: 90, drift_profile: "mixed" }
    """
    data = request.get_json() or {}
    customer_id = data.get('customer_id')
    if not customer_id:
        return jsonify({'error': 'customer_id is required'}), 400

    try:
        customer_id = int(customer_id)
    except ValueError:
        return jsonify({'error': 'customer_id must be an integer'}), 400

    interval_seconds = int(data.get('interval_seconds', 10))
    num_days = int(data.get('num_days', 90))
    drift_profile = data.get('drift_profile', 'mixed')
    base_url = data.get('base_url', 'http://localhost:5059')

    sim_key = str(customer_id)

    # Check if already running
    with _sim_lock:
        existing = _simulations.get(sim_key)
        if existing and existing.get('status') == 'running':
            return jsonify({'error': f'Simulation already running for customer {customer_id}', 'current_day': existing.get('current_day', 0)}), 409

    sim_entry = {
        'customer_id': customer_id,
        'status': 'running',
        'interval_seconds': interval_seconds,
        'num_days': num_days,
        'drift_profile': drift_profile,
        'current_day': 0,
        'current_date': None,
        'kpis_injected': 0,
        'last_inject_ok': True,
        'elapsed_seconds': 0,
        'stop_requested': False,
        'error': None,
        'start_time': datetime.now().isoformat(),
    }

    with _sim_lock:
        _simulations[sim_key] = sim_entry

    t = threading.Thread(
        target=_simulation_thread,
        args=(customer_id, interval_seconds, num_days, drift_profile, base_url),
        daemon=True,
        name=f'sim-{customer_id}'
    )
    t.start()

    return jsonify({
        'status': 'started',
        'customer_id': customer_id,
        'interval_seconds': interval_seconds,
        'num_days': num_days,
        'drift_profile': drift_profile,
    })


@test_runner_api.route('/api/test-runner/simulate/stop', methods=['POST'])
def stop_simulation():
    """Stop running simulation for a customer."""
    data = request.get_json() or {}
    customer_id = data.get('customer_id')
    if not customer_id:
        return jsonify({'error': 'customer_id is required'}), 400

    sim_key = str(customer_id)

    with _sim_lock:
        sim = _simulations.get(sim_key)
        if not sim:
            return jsonify({'error': f'No simulation found for customer {customer_id}'}), 404
        if sim.get('status') != 'running':
            return jsonify({'error': f'Simulation not running (status: {sim.get("status")})'}), 400
        sim['stop_requested'] = True

    return jsonify({'status': 'stop_requested', 'customer_id': int(customer_id)})


@test_runner_api.route('/api/test-runner/simulate/status', methods=['GET'])
def simulation_status():
    """Get simulation progress for a customer."""
    customer_id = request.args.get('customer_id')
    if not customer_id:
        return jsonify({'error': 'customer_id query param is required'}), 400

    sim_key = str(customer_id)

    with _sim_lock:
        sim = _simulations.get(sim_key)

    if not sim:
        return jsonify({
            'is_running': False,
            'status': 'idle',
            'customer_id': int(customer_id),
        })

    return jsonify({
        'is_running': sim.get('status') == 'running',
        'status': sim.get('status', 'idle'),
        'customer_id': int(customer_id),
        'current_day': sim.get('current_day', 0),
        'num_days': sim.get('num_days', 0),
        'current_date': sim.get('current_date'),
        'interval_seconds': sim.get('interval_seconds', 10),
        'drift_profile': sim.get('drift_profile', 'mixed'),
        'kpis_injected': sim.get('kpis_injected', 0),
        'last_inject_ok': sim.get('last_inject_ok', True),
        'elapsed_seconds': sim.get('elapsed_seconds', 0),
        'error': sim.get('error'),
        'start_time': sim.get('start_time'),
    })
