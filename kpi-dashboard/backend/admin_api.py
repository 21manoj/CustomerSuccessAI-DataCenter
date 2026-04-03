"""
Admin API Blueprint
====================
Provides endpoints for Admin Insights Dashboard (Tab 5)
- Wizard B: Pattern Analysis
- Wizard C: Weight Calibration

Register in app.py:
    from admin_api import admin_bp
    app.register_blueprint(admin_bp)
"""

from flask import Blueprint, jsonify, request, current_app
from auth_middleware import get_current_customer_id
from datetime import datetime
from pathlib import Path
import json
import os

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')


# ============================================================
# DB HELPER — Wizard B
# ============================================================

def _get_active_wizard_b_learning(customer_id):
    """
    Return the active WizardLearning row for this customer, or None.
    Deferred import to avoid circular dependency.
    """
    try:
        from models import WizardLearning
        if customer_id is not None:
            return WizardLearning.get_active(customer_id=int(customer_id))
        return None
    except Exception:
        return None


# ============================================================
# CONFIGURATION
# ============================================================

def _backend_dir():
    """Backend directory (where verticals/ lives). Prefer __file__ so paths work when root_path differs."""
    return Path(__file__).resolve().parent

def get_customer_data_path(customer_id=None):
    """Get path to customer's journey data directory"""
    root = _backend_dir()
    if customer_id:
        # Use customer-specific path
        base_path = root / 'verticals' / f'customer{customer_id}-dc2_s' / 'journey'
        if base_path.exists():
            return base_path
    
    # Default to customer9-dc2_s for now (fallback)
    base_path = root / 'verticals' / 'customer9-dc2_s' / 'journey'
    return base_path

def get_latest_wizard_run(base_path):
    """Find the most recent wizard run directory"""
    wizard_data_path = base_path / 'data' / 'wizard'
    if not wizard_data_path.exists():
        # Try wizard_a directory structure
        wizard_a_path = base_path / 'wizard_a'
        if wizard_a_path.exists():
            runs = sorted([d for d in wizard_a_path.iterdir() if d.is_dir() and d.name.startswith('test_run_')], 
                         key=lambda x: x.stat().st_mtime, reverse=True)
            return runs[0] if runs else None
        return None
    
    runs = sorted([d for d in wizard_data_path.iterdir() if d.is_dir()], 
                  key=lambda x: x.stat().st_mtime, reverse=True)
    return runs[0] if runs else None


def get_latest_pattern_file(base_path, filename):
    """
    Find the most recent run that has Wizard B output (e.g. pattern_profiles.json).
    Prefers data/learnings (canonical Wizard B output) over learnings (legacy); returns (run_name, path) or (None, None).
    """
    def scan_base(learnings_base):
        best_mtime = 0
        best_run_name = None
        best_path = None
        if not learnings_base.exists():
            return (None, None)
        for run_dir in learnings_base.iterdir():
            if not run_dir.is_dir():
                continue
            f = run_dir / filename
            if f.exists():
                m = f.stat().st_mtime
                if m > best_mtime:
                    best_mtime = m
                    best_run_name = run_dir.name
                    best_path = f
        return (best_run_name, best_path)
    # Prefer data/learnings (canonical) so we don't pick empty learnings/test_run_* over real wizard_* output
    for learnings_base in [base_path / 'data' / 'learnings', base_path / 'learnings']:
        run_name, path = scan_base(learnings_base)
        if path is not None:
            return (run_name, path)
    return (None, None)


def get_latest_learnings_run(base_path):
    """
    Return (run_name, run_dir) for the most recent Wizard B learnings run (dir that has pattern_profiles.json).
    run_dir is the Path to the learnings run directory.
    """
    _, path = get_latest_pattern_file(base_path, 'pattern_profiles.json')
    if path and path.exists():
        return (path.parent.name, path.parent)
    return (None, None)


# ============================================================
# OVERVIEW ENDPOINTS
# ============================================================

@admin_bp.route('/summary', methods=['GET'])
def get_admin_summary():
    """
    GET /api/admin/summary
    Returns overview summary for Admin Dashboard
    """
    try:
        customer_id = get_current_customer_id()
        if customer_id:
            customer_id = int(customer_id)
        
        base_path = get_customer_data_path(customer_id)
        
        # Get Wizard B summary — DB first, then filesystem fallback
        wizard_b_summary = {
            "total_patterns": 0,
            "total_accounts": 0,
            "last_analysis": None,
            "source": "none"
        }

        learning = _get_active_wizard_b_learning(customer_id)
        if learning and learning.learnings:
            profiles = learning.learnings.get('pattern_profiles', {})
            wizard_b_summary = {
                "total_patterns": len(profiles),
                "total_accounts": sum(
                    p.get('n_accounts', 0)
                    for p in profiles.values() if isinstance(p, dict)
                ),
                "last_analysis": learning.created_at.isoformat() if learning.created_at else None,
                "source": "database"
            }
        else:
            # Filesystem fallback
            run_name, run_dir = get_latest_learnings_run(base_path)
            if run_dir:
                pattern_file = run_dir / 'pattern_profiles.json'
                if pattern_file.exists():
                    with open(pattern_file, 'r') as f:
                        patterns = json.load(f)
                    wizard_b_summary = {
                        "total_patterns": len(patterns),
                        "total_accounts": sum(p.get('n_accounts', 0) for p in patterns.values() if isinstance(p, dict)),
                        "last_analysis": datetime.fromtimestamp(pattern_file.stat().st_mtime).isoformat(),
                        "source": "filesystem"
                    }
        
        bootstrap_accuracy = 0.70
        bootstrap_file = base_path / 'data' / 'bootstrap' / 'bootstrap_weights_config.json'
        if bootstrap_file.exists():
            try:
                with open(bootstrap_file, 'r') as f:
                    bootstrap_data = json.load(f)
                bootstrap_accuracy = float(bootstrap_data.get('baseline_accuracy', 0.70))
            except Exception:
                pass
        
        wizard_c_summary = {
            "current_accuracy": bootstrap_accuracy,
            "weight_source": "bootstrap",
            "last_calibration": None
        }
        weights_file = base_path / 'learned_weights.json'
        if weights_file.exists():
            with open(weights_file, 'r') as f:
                learned_data = json.load(f)
            acc = learned_data.get('accuracy')
            if acc is None or (isinstance(acc, (int, float)) and acc <= 0):
                acc = bootstrap_accuracy
            wizard_c_summary = {
                "current_accuracy": float(acc) if acc is not None else bootstrap_accuracy,
                "weight_source": "learned",
                "last_calibration": learned_data.get('timestamp', datetime.now().isoformat())
            }
        
        return jsonify({
            "wizard_b": wizard_b_summary,
            "wizard_c": wizard_c_summary,
            "status": "healthy"
        })
        
    except Exception as e:
        current_app.logger.error(f"Error loading admin summary: {str(e)}")
        return jsonify({"error": "An internal error occurred. Please try again or contact support."}), 500


# ============================================================
# WIZARD B ENDPOINTS (Pattern Analysis)
# ============================================================

@admin_bp.route('/wizard-b/patterns', methods=['GET'])
def get_wizard_b_patterns():
    """
    GET /api/admin/wizard-b/patterns
    Returns pattern profiles from Wizard B analysis
    """
    try:
        customer_id = get_current_customer_id()
        if customer_id:
            customer_id = int(customer_id)

        # DB first
        learning = _get_active_wizard_b_learning(customer_id)
        if learning and learning.learnings:
            profiles = learning.learnings.get('pattern_profiles', {})
            return jsonify({
                "patterns": profiles,
                "run_id": learning.run_id,
                "analyzed_at": learning.created_at.isoformat() if learning.created_at else None,
                "source": "database"
            })

        # Filesystem fallback
        base_path = get_customer_data_path(customer_id)
        current_app.logger.info(f"[Wizard B patterns] customer_id={customer_id} base_path={base_path}")
        run_name, pattern_file = get_latest_pattern_file(base_path, 'pattern_profiles.json')
        current_app.logger.info(f"[Wizard B patterns] run_name={run_name} pattern_file={pattern_file}")
        if pattern_file and pattern_file.exists():
            with open(pattern_file, 'r') as f:
                patterns = json.load(f)
            return jsonify({
                "patterns": patterns,
                "run_id": run_name,
                "analyzed_at": datetime.fromtimestamp(pattern_file.stat().st_mtime).isoformat(),
                "source": "filesystem"
            })
        latest_run = get_latest_wizard_run(base_path)
        if not latest_run:
            return jsonify({
                "patterns": {},
                "message": "No Wizard B analysis found. Run pattern analysis first."
            })
        for candidate in [
            base_path / 'data' / 'learnings' / latest_run.name / 'pattern_profiles.json',
            base_path / 'learnings' / latest_run.name / 'pattern_profiles.json',
            latest_run / 'pattern_profiles.json',
        ]:
            if candidate.exists():
                with open(candidate, 'r') as f:
                    patterns = json.load(f)
                return jsonify({
                    "patterns": patterns,
                    "run_id": latest_run.name,
                    "analyzed_at": datetime.fromtimestamp(candidate.stat().st_mtime).isoformat(),
                    "source": "filesystem"
                })
        return jsonify({
            "patterns": {},
            "message": "Pattern profiles not found. Run Wizard B pattern analysis first."
        })

    except Exception as e:
        current_app.logger.error(f"Error loading patterns: {str(e)}")
        return jsonify({"error": "An internal error occurred. Please try again or contact support."}), 500


@admin_bp.route('/wizard-b/early-warnings', methods=['GET'])
def get_wizard_b_early_warnings():
    """
    GET /api/admin/wizard-b/early-warnings
    Returns early warning rules from Wizard B
    """
    try:
        customer_id = get_current_customer_id()
        if customer_id:
            customer_id = int(customer_id)

        # DB first
        learning = _get_active_wizard_b_learning(customer_id)
        if learning:
            # Prefer validation_rules, fall back to learnings blob
            rules = learning.validation_rules
            if rules is None and learning.learnings:
                rules = learning.learnings.get('early_warning_rules', [])
            if rules is not None:
                return jsonify({
                    "rules": rules,
                    "source": "database"
                })

        # Filesystem fallback
        base_path = get_customer_data_path(customer_id)
        run_name, run_dir = get_latest_learnings_run(base_path)
        if not run_dir:
            return jsonify({"rules": [], "message": "No analysis found"})
        rules_file = run_dir / 'early_warning_rules.json'
        if not rules_file.exists():
            # Return default rules if file doesn't exist
            return jsonify({
                "rules": [
                    {
                        "rule_id": "EW001",
                        "description": "Health score drops below 50 within first 10 weeks",
                        "confidence": 0.85,
                        "support": 12,
                        "action": "Immediate CSM intervention required"
                    },
                    {
                        "rule_id": "EW002",
                        "description": "3+ critical incidents in 4-week period",
                        "confidence": 0.78,
                        "support": 8,
                        "action": "Schedule executive review"
                    },
                    {
                        "rule_id": "EW003",
                        "description": "GPU utilization below 40% for 3+ weeks",
                        "confidence": 0.72,
                        "support": 15,
                        "action": "Review workload optimization"
                    }
                ],
                "source": "default"
            })

        with open(rules_file, 'r') as f:
            rules = json.load(f)

        return jsonify({
            "rules": rules,
            "source": "filesystem"
        })

    except Exception as e:
        current_app.logger.error(f"Error loading early warnings: {str(e)}")
        return jsonify({"error": "An internal error occurred. Please try again or contact support."}), 500


@admin_bp.route('/wizard-b/report', methods=['GET'])
def get_wizard_b_report():
    """
    GET /api/admin/wizard-b/report
    Returns markdown analysis report from Wizard B
    """
    try:
        customer_id = get_current_customer_id()
        if customer_id:
            customer_id = int(customer_id)

        # DB first
        learning = _get_active_wizard_b_learning(customer_id)
        if learning and learning.analysis_report:
            return jsonify({
                "report": learning.analysis_report,
                "run_id": learning.run_id,
                "source": "database"
            })

        # Filesystem fallback
        base_path = get_customer_data_path(customer_id)
        run_name, run_dir = get_latest_learnings_run(base_path)
        if not run_dir:
            return jsonify({"report": "# No Analysis Report\n\nRun Wizard B to generate pattern analysis."})
        report_file = run_dir / 'ANALYSIS_REPORT.md'
        if not report_file.exists():
            return jsonify({"report": "# Analysis Report Not Found\n\nReport file missing from latest run."})

        with open(report_file, 'r') as f:
            report = f.read()

        latest_run = get_latest_wizard_run(base_path)
        return jsonify({
            "report": report,
            "run_id": latest_run.name if latest_run else run_name,
            "source": "filesystem"
        })

    except Exception as e:
        current_app.logger.error(f"Error loading report: {str(e)}")
        return jsonify({"error": "An internal error occurred. Please try again or contact support."}), 500


# ============================================================
# WIZARD C ENDPOINTS (Weight Calibration)
# ============================================================

@admin_bp.route('/wizard-c/weights/current', methods=['GET'])
def get_wizard_c_current_weights():
    """
    GET /api/admin/wizard-c/weights/current
    Returns current pillar weights (L2) and accuracy
    """
    try:
        customer_id = get_current_customer_id()
        if customer_id:
            customer_id = int(customer_id)
        
        base_path = get_customer_data_path(customer_id)
        
        # Default bootstrap weights
        default_weights = {
            "P1": {"name": "Deployment Velocity", "weight": 0.15, "source": "bootstrap"},
            "P2": {"name": "Operational Stability", "weight": 0.20, "source": "bootstrap"},
            "P3": {"name": "AI Workload Performance", "weight": 0.25, "source": "bootstrap"},
            "P4": {"name": "Channel & Partner Health", "weight": 0.15, "source": "bootstrap"},
            "P5": {"name": "Expansion Readiness", "weight": 0.25, "source": "bootstrap"}
        }
        
        # Prefer bootstrap baseline_accuracy when learned has 0 or missing (avoid showing 0% in UI)
        bootstrap_accuracy = 0.70
        bootstrap_file = base_path / 'data' / 'bootstrap' / 'bootstrap_weights_config.json'
        if bootstrap_file.exists():
            try:
                with open(bootstrap_file, 'r') as f:
                    bootstrap_data = json.load(f)
                bootstrap_accuracy = float(bootstrap_data.get('baseline_accuracy', 0.70))
            except Exception:
                pass
        
        weights_file = base_path / 'learned_weights.json'
        if weights_file.exists():
            with open(weights_file, 'r') as f:
                learned = json.load(f)
            
            # Merge learned pillar weights if present (some files only have ensemble v3/llm)
            for pillar, data in learned.get('pillar_weights', {}).items():
                if pillar in default_weights:
                    default_weights[pillar]['weight'] = data.get('weight', default_weights[pillar]['weight'])
                    default_weights[pillar]['source'] = 'learned'
            
            acc = learned.get('accuracy')
            # Avoid showing 0%: use bootstrap when learned accuracy is 0 or missing
            if acc is None or (isinstance(acc, (int, float)) and acc <= 0):
                acc = bootstrap_accuracy
            return jsonify({
                "weights": default_weights,
                "accuracy": float(acc) if acc is not None else bootstrap_accuracy,
                "last_calibration": learned.get('timestamp'),
                "source": "learned"
            })
        
        return jsonify({
            "weights": default_weights,
            "accuracy": bootstrap_accuracy,
            "last_calibration": None,
            "source": "bootstrap"
        })
        
    except Exception as e:
        current_app.logger.error(f"Error loading weights: {str(e)}")
        return jsonify({"error": "An internal error occurred. Please try again or contact support."}), 500


@admin_bp.route('/wizard-c/weights/history', methods=['GET'])
def get_wizard_c_weights_history():
    """
    GET /api/admin/wizard-c/weights/history
    Returns weight evolution over time
    """
    try:
        customer_id = get_current_customer_id()
        if customer_id:
            customer_id = int(customer_id)
        
        base_path = get_customer_data_path(customer_id)
        history_file = base_path / 'weights_history.json'
        
        if not history_file.exists():
            # Return sample history for demo
            return jsonify({
                "history": [
                    {"date": "2025-12-01", "accuracy": 0.65, "source": "bootstrap"},
                    {"date": "2025-12-15", "accuracy": 0.72, "source": "learned"},
                    {"date": "2026-01-01", "accuracy": 0.78, "source": "learned"},
                    {"date": "2026-01-15", "accuracy": 0.82, "source": "learned"}
                ],
                "source": "sample"
            })
        
        with open(history_file, 'r') as f:
            history = json.load(f)
        
        return jsonify({
            "history": history,
            "source": "actual"
        })
        
    except Exception as e:
        current_app.logger.error(f"Error loading weight history: {str(e)}")
        return jsonify({"error": "An internal error occurred. Please try again or contact support."}), 500


@admin_bp.route('/wizard-c/accuracy', methods=['GET'])
def get_wizard_c_accuracy():
    """
    GET /api/admin/wizard-c/accuracy
    Returns detailed accuracy metrics
    """
    try:
        customer_id = get_current_customer_id()
        if customer_id:
            customer_id = int(customer_id)
        
        base_path = get_customer_data_path(customer_id)
        
        # Default accuracy metrics
        metrics = {
            "overall_accuracy": 0.70,
            "prediction_accuracy": {
                "churn": 0.75,
                "expansion": 0.68,
                "stable": 0.82
            },
            "samples_used": 0,
            "validation_method": "bootstrap"
        }
        
        accuracy_file = base_path / 'accuracy_metrics.json'
        if accuracy_file.exists():
            with open(accuracy_file, 'r') as f:
                metrics = json.load(f)
        
        return jsonify(metrics)
        
    except Exception as e:
        current_app.logger.error(f"Error loading accuracy: {str(e)}")
        return jsonify({"error": "An internal error occurred. Please try again or contact support."}), 500


@admin_bp.route('/wizard-c/recalibrate', methods=['POST'])
def trigger_wizard_c_recalibration():
    """
    POST /api/admin/wizard-c/recalibrate
    Triggers real DB-native Wizard C weight calibration.
    """
    import time as _time
    try:
        customer_id = get_current_customer_id()
        if customer_id:
            customer_id = int(customer_id)

        current_app.logger.info(f"Wizard C recalibration triggered for customer {customer_id}")

        from wizards.wizard_c_weight_calibrator_db import run_wizard_c
        t0 = _time.time()
        result = run_wizard_c(customer_id)
        duration = round(_time.time() - t0, 2)

        current_app.logger.info(
            f"✅ Wizard C completed in {duration}s — status={result.get('status')}"
        )

        return jsonify({
            "status": result.get("status", "success"),
            "message": result.get("message", "Weight calibration completed"),
            "kpis_calibrated": result.get("kpis_calibrated", 0),
            "pillars_calibrated": result.get("pillars_calibrated", 0),
            "accounts_analyzed": result.get("accounts_analyzed", 0),
            "duration_seconds": duration,
        })

    except Exception as e:
        current_app.logger.error(f"Error triggering Wizard C: {str(e)}", exc_info=True)
        return jsonify({"error": "An internal error occurred. Please try again or contact support."}), 500


# ============================================================
# ENSEMBLE WEIGHTS (V3 vs LLM blend)
# ============================================================

@admin_bp.route('/wizard-c/ensemble', methods=['GET'])
def get_ensemble_weights():
    """
    GET /api/admin/wizard-c/ensemble
    Returns ensemble weights (V3 quantitative vs LLM qualitative blend)
    """
    try:
        return jsonify({
            "ensemble": {
                "v3_weight": 0.65,
                "llm_weight": 0.35,
                "description": "65% quantitative (V3 health scores) + 35% qualitative (LLM signal analysis)"
            },
            "v3_components": {
                "kpi_scores": 0.40,
                "trend_analysis": 0.15,
                "phase_detection": 0.10
            },
            "llm_components": {
                "signal_sentiment": 0.20,
                "context_analysis": 0.10,
                "recommendation_confidence": 0.05
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error loading ensemble: {str(e)}")
        return jsonify({"error": "An internal error occurred. Please try again or contact support."}), 500


# ============================================================
# S2.1 — HEALTH SCORE RESET
# ============================================================

@admin_bp.route('/accounts/<int:account_id>/reset-health', methods=['POST'])
def reset_account_health(account_id):
    """
    POST /api/admin/accounts/<account_id>/reset-health
    Recalculate health scores for a single account from existing KPI data.
    Body: {"dry_run": bool, "reason": "string"}
    """
    from models import db, Account, DC2SKPI, HealthScore, CustomerConfig
    import utils.health_thresholds as ht
    from collections import defaultdict
    from datetime import date as _date
    from mcp_server.cs_pulse_mcp_server import _get_health_functions

    customer_id = get_current_customer_id()
    if not customer_id:
        return jsonify({"error": "Authentication required"}), 401

    body = request.get_json(silent=True) or {}
    dry_run = body.get('dry_run', False)
    reason = body.get('reason', '')

    # Verify account belongs to this customer
    account = Account.query.filter_by(account_id=account_id, customer_id=int(customer_id)).first()
    if not account:
        return jsonify({"error": f"Account {account_id} not found for customer {customer_id}"}), 404

    try:
        # Get vertical and calculator
        vertical = 'dc2_s'
        try:
            cc = CustomerConfig.query.filter_by(customer_id=int(customer_id)).first()
            if cc and cc.vertical:
                vertical = cc.vertical
        except Exception:
            pass

        calculate_fn, _, _ = _get_health_functions(vertical)

        # Load all KPI measurements for this account, grouped by month
        all_kpis = DC2SKPI.query.filter_by(account_id=account_id).all()
        month_kpis = defaultdict(lambda: defaultdict(list))
        for k in all_kpis:
            if k.measured_at:
                month_key = k.measured_at.date().replace(day=1) if hasattr(k.measured_at, 'date') else k.measured_at.replace(day=1)
            else:
                month_key = _date.today().replace(day=1)
            month_kpis[month_key][k.kpi_code].append(float(k.value))

        if not month_kpis:
            return jsonify({"error": "No KPI data found for this account", "account_id": account_id}), 404

        # Calculate health for each month
        new_scores = []
        for month, kpi_groups in sorted(month_kpis.items()):
            kpi_vals = {code: sum(vals) / len(vals) for code, vals in kpi_groups.items()}
            if not kpi_vals:
                continue
            health, pillars = calculate_fn(kpi_vals, customer_id=int(customer_id))
            new_scores.append({
                "month": str(month),
                "health_score": round(health, 2),
                "health_status": ht.classify(health),
                "pillar_scores": {k: round(v, 2) for k, v in pillars.items()} if pillars else {},
            })

        # Get current scores for comparison
        current_scores = HealthScore.query.filter_by(account_id=account_id).order_by(
            HealthScore.measurement_month.desc()
        ).limit(1).first()

        current_health = float(current_scores.health_score) if current_scores else None
        latest_new = new_scores[-1] if new_scores else None

        result = {
            "account_id": account_id,
            "account_name": account.account_name,
            "dry_run": dry_run,
            "months_recalculated": len(new_scores),
            "current_health": current_health,
            "new_health": latest_new["health_score"] if latest_new else None,
            "new_status": latest_new["health_status"] if latest_new else None,
            "delta": round(latest_new["health_score"] - current_health, 2) if latest_new and current_health else None,
            "scores": new_scores,
        }

        if dry_run:
            result["message"] = "Dry run — no changes applied"
            return jsonify(result)

        # Apply: upsert health scores
        for s in new_scores:
            month_date = _date.fromisoformat(s["month"])
            existing = HealthScore.query.filter_by(
                account_id=account_id, measurement_month=month_date
            ).first()
            pillars_json = json.dumps(s["pillar_scores"]) if s["pillar_scores"] else None
            if existing:
                existing.health_score = s["health_score"]
                existing.health_status = s["health_status"]
                existing.contributing_pillars = pillars_json
            else:
                db.session.add(HealthScore(
                    account_id=account_id,
                    measurement_month=month_date,
                    health_score=s["health_score"],
                    health_status=s["health_status"],
                    contributing_pillars=pillars_json,
                ))
        db.session.commit()

        # Log the action
        try:
            from activity_log_api import log_activity
            log_activity(
                customer_id=int(customer_id),
                action_type='health_score_reset',
                action_description=f"Reset health scores for account {account_id} ({account.account_name}). Reason: {reason}. "
                                   f"Previous: {current_health}, New: {result['new_health']}",
                resource_type='account',
                resource_id=str(account_id),
                status='success',
            )
        except Exception:
            pass

        result["message"] = f"Health scores recalculated for {len(new_scores)} months"
        return jsonify(result)

    except Exception as e:
        current_app.logger.error(f"Health score reset failed for account {account_id}: {e}")
        return jsonify({"error": str(e)}), 500


@admin_bp.route('/customers/<int:cid>/reset-all-health', methods=['POST'])
def reset_customer_health(cid):
    """
    POST /api/admin/customers/<cid>/reset-all-health
    Recalculate health scores for ALL accounts of a customer.
    Body: {"dry_run": bool, "reason": "string"}
    """
    from models import Account

    customer_id = get_current_customer_id()
    if not customer_id:
        return jsonify({"error": "Authentication required"}), 401

    body = request.get_json(silent=True) or {}
    dry_run = body.get('dry_run', False)
    reason = body.get('reason', 'Bulk health reset')

    accounts = Account.query.filter_by(customer_id=cid).all()
    if not accounts:
        return jsonify({"error": f"No accounts found for customer {cid}"}), 404

    results = []
    errors = []
    for acct in accounts:
        try:
            with current_app.test_request_context(
                f'/api/admin/accounts/{acct.account_id}/reset-health',
                method='POST',
                json={"dry_run": dry_run, "reason": reason},
            ):
                # Reuse the single-account endpoint logic
                resp = reset_account_health(acct.account_id)
                if hasattr(resp, 'get_json'):
                    data = resp.get_json()
                else:
                    data = resp[0].get_json() if isinstance(resp, tuple) else {"error": "unknown"}
                results.append(data)
        except Exception as e:
            errors.append({"account_id": acct.account_id, "error": str(e)})

    return jsonify({
        "customer_id": cid,
        "dry_run": dry_run,
        "accounts_processed": len(results),
        "errors": errors,
        "results": results,
    })


# ============================================================
# S2.2 — WEIGHT OVERRIDE
# ============================================================

@admin_bp.route('/customers/<int:cid>/override-weights', methods=['POST'])
def override_customer_weights(cid):
    """
    POST /api/admin/customers/<cid>/override-weights
    Directly set pillar and/or KPI weights, bypassing Wizard C.
    Body: {
      "pillar_weights": {"P1": 0.15, "P2": 0.20, ...},
      "kpi_weights": {"P1": {"P1-KPI1": 0.20, ...}, ...},
      "reason": "string"
    }
    """
    from models import db, CustomerConfig

    customer_id = get_current_customer_id()
    if not customer_id:
        return jsonify({"error": "Authentication required"}), 401

    body = request.get_json(silent=True) or {}
    pillar_weights = body.get('pillar_weights')
    kpi_weights = body.get('kpi_weights')
    reason = body.get('reason', '')

    if not pillar_weights and not kpi_weights:
        return jsonify({"error": "Provide pillar_weights and/or kpi_weights"}), 400

    # Validate pillar weights sum to ~1.0
    if pillar_weights:
        total = sum(pillar_weights.values())
        if abs(total - 1.0) > 0.02:
            return jsonify({"error": f"Pillar weights must sum to 1.0 (got {total:.3f})"}), 400

    # Validate KPI weights sum to ~1.0 per pillar
    if kpi_weights:
        for pillar, kw in kpi_weights.items():
            total = sum(kw.values())
            if abs(total - 1.0) > 0.02:
                return jsonify({"error": f"KPI weights for {pillar} must sum to 1.0 (got {total:.3f})"}), 400

    try:
        cc = CustomerConfig.query.filter_by(customer_id=cid).first()
        if not cc:
            return jsonify({"error": f"CustomerConfig not found for customer {cid}"}), 404

        previous = {
            "pillar_weights": cc.dc2s_pillar_weights,
            "kpi_weights": cc.dc2s_kpi_weights,
        }

        if pillar_weights:
            cc.dc2s_pillar_weights = pillar_weights
        if kpi_weights:
            cc.dc2s_kpi_weights = kpi_weights

        db.session.commit()

        # Log the action
        try:
            from activity_log_api import log_activity
            log_activity(
                customer_id=cid,
                action_type='weight_override',
                action_description=f"Admin weight override. Reason: {reason}. "
                                   f"Pillar: {pillar_weights or 'unchanged'}, KPI: {'updated' if kpi_weights else 'unchanged'}",
                resource_type='customer_config',
                resource_id=str(cid),
                status='success',
            )
        except Exception:
            pass

        return jsonify({
            "customer_id": cid,
            "message": "Weights updated successfully",
            "source": "admin_override",
            "previous": previous,
            "current": {
                "pillar_weights": cc.dc2s_pillar_weights,
                "kpi_weights": cc.dc2s_kpi_weights,
            },
        })

    except Exception as e:
        current_app.logger.error(f"Weight override failed for customer {cid}: {e}")
        return jsonify({"error": str(e)}), 500


@admin_bp.route('/customers/<int:cid>/reset-weights', methods=['POST'])
def reset_customer_weights(cid):
    """
    POST /api/admin/customers/<cid>/reset-weights
    Revert weights to JSON catalog defaults (clear DB overrides).
    Body: {"reason": "string"}
    """
    from models import db, CustomerConfig

    customer_id = get_current_customer_id()
    if not customer_id:
        return jsonify({"error": "Authentication required"}), 401

    body = request.get_json(silent=True) or {}
    reason = body.get('reason', 'Reset to catalog defaults')

    try:
        cc = CustomerConfig.query.filter_by(customer_id=cid).first()
        if not cc:
            return jsonify({"error": f"CustomerConfig not found for customer {cid}"}), 404

        previous = {
            "pillar_weights": cc.dc2s_pillar_weights,
            "kpi_weights": cc.dc2s_kpi_weights,
        }

        cc.dc2s_pillar_weights = None
        cc.dc2s_kpi_weights = None
        db.session.commit()

        try:
            from activity_log_api import log_activity
            log_activity(
                customer_id=cid,
                action_type='weight_reset',
                action_description=f"Reset weights to catalog defaults. Reason: {reason}. Previous pillar: {previous['pillar_weights']}",
                resource_type='customer_config',
                resource_id=str(cid),
                status='success',
            )
        except Exception:
            pass

        return jsonify({
            "customer_id": cid,
            "message": "Weights reset to catalog defaults",
            "source": "catalog_default",
            "previous": previous,
        })

    except Exception as e:
        current_app.logger.error(f"Weight reset failed for customer {cid}: {e}")
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# Stuck User Detection — Support Tooling
# ---------------------------------------------------------------------------

@admin_bp.route('/onboarding/stuck-users', methods=['GET'])
def get_stuck_users():
    """Return new customers whose onboarding wizard hasn't completed.

    A customer is "stuck" when:
      - Their onboarding_state is not 'active' (no real health scores yet), AND
      - Their most recent onboarding activity log entry is > `threshold_minutes` old
        (default 30 minutes — they started but went quiet)

    Query params:
      threshold_minutes  int   — inactivity window (default 30)
      include_fresh      bool  — include customers with zero activity logs (default true)
    """
    from extensions import db
    from models import Customer, Account, HealthScore, ActivityLog
    from sqlalchemy import func, desc

    threshold_minutes = request.args.get('threshold_minutes', 30, type=int)
    include_fresh = request.args.get('include_fresh', 'true').lower() != 'false'
    cutoff = datetime.utcnow() - __import__('datetime').timedelta(minutes=threshold_minutes)

    try:
        # Customers without any health scores (not yet 'active')
        active_customer_ids = db.session.query(HealthScore.customer_id).distinct()
        inactive_customers = (
            Customer.query
            .filter(Customer.customer_id.notin_(active_customer_ids))
            .all()
        )

        # Latest onboarding activity per customer
        latest_activity_sq = (
            db.session.query(
                ActivityLog.customer_id,
                func.max(ActivityLog.created_at).label('last_activity'),
            )
            .filter(ActivityLog.action_category == 'onboarding')
            .group_by(ActivityLog.customer_id)
            .subquery()
        )

        results = []
        for customer in inactive_customers:
            cid = customer.customer_id
            row = (
                db.session.query(latest_activity_sq.c.last_activity)
                .filter(latest_activity_sq.c.customer_id == cid)
                .scalar()
            )

            if row is None:
                # No onboarding activity at all
                if not include_fresh:
                    continue
                last_step = None
                last_activity_iso = None
                minutes_idle = None
                is_stuck = True
            else:
                minutes_idle = int((datetime.utcnow() - row).total_seconds() / 60)
                is_stuck = row < cutoff
                if not is_stuck:
                    continue  # Still active — skip
                last_activity_iso = row.isoformat()
                # Get the last step name from ActivityLog
                last_log = (
                    ActivityLog.query
                    .filter_by(customer_id=cid, action_category='onboarding')
                    .order_by(desc(ActivityLog.created_at))
                    .first()
                )
                last_step = (last_log.action_description if last_log else None)

            results.append({
                'customer_id': cid,
                'customer_name': customer.customer_name,
                'created_at': customer.created_at.isoformat() if customer.created_at else None,
                'last_onboarding_activity': last_activity_iso,
                'minutes_idle': minutes_idle,
                'last_step': last_step,
                'is_stuck': is_stuck,
            })

        results.sort(key=lambda r: r['minutes_idle'] or 99999, reverse=True)

        return jsonify({
            'stuck_users': results,
            'total': len(results),
            'threshold_minutes': threshold_minutes,
            'as_of': datetime.utcnow().isoformat(),
        })

    except Exception as e:
        current_app.logger.error(f"get_stuck_users failed: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500
