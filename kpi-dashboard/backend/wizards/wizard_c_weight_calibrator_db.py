"""
Wizard C — DB-Native Weight Calibration
=========================================

Reads KPI measurements and health scores from PostgreSQL, correlates
KPI values with account success/failure, and calibrates L1 (KPI) and
L2 (pillar) weights.  Results are saved directly to ``CustomerConfig``.

No filesystem access — everything comes from / goes to PostgreSQL.
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from datetime import datetime

import utils.health_thresholds as ht


def run_wizard_c(customer_id: int) -> dict:
    """
    Top-level entrypoint for DB-native Wizard C.

    Must be called inside a Flask app context.

    Returns:
        dict with ``pillar_weights``, ``kpi_weights``, ``correlations``,
        ``significant_changes``, etc.
    """
    from models import Account, DC2SKPI, HealthScore, CustomerConfig
    from extensions import db
    from sqlalchemy import func
    # Import KPI definitions directly to avoid fastmcp dependency
    try:
        from mcp_server.common import get_kpi_definitions
    except ImportError:
        # Fallback: load directly from vertical module
        def get_kpi_definitions(vertical):
            from verticals.dc2_s.kpi_definitions import DC2S_KPIS
            return DC2S_KPIS

    # ------------------------------------------------------------------
    # 0. Resolve vertical and load base weights from kpi_definitions
    # ------------------------------------------------------------------
    customer = db.session.query(Account.customer_id).filter_by(
        customer_id=customer_id).first()

    # Determine vertical
    from models import Customer
    cust_row = db.session.get(Customer, customer_id)
    vertical = getattr(cust_row, 'vertical', 'dc2_s') or 'dc2_s'

    kpi_defs = get_kpi_definitions(vertical)

    # Base L1 weights: {kpi_code: weight_l1}
    base_l1: dict[str, float] = {}
    kpi_to_pillar: dict[str, str] = {}
    for code, info in kpi_defs.items():
        base_l1[code] = info.get('weight_l1', info.get('weight', 0.1))
        kpi_to_pillar[code] = info.get('pillar', code.split('-')[0])

    # Base L2 weights from pillar definitions
    pillar_codes = sorted(set(kpi_to_pillar.values()))
    try:
        if vertical == 'dc2_s':
            from verticals.dc2_s.kpi_definitions import DC2S_PILLARS
            base_l2 = {pid: info.get('weight_l2', info.get('weight', 0.2))
                       for pid, info in DC2S_PILLARS.items()}
        else:
            # Equal weights as fallback
            base_l2 = {p: 1.0 / len(pillar_codes) for p in pillar_codes}
    except ImportError:
        base_l2 = {p: 1.0 / len(pillar_codes) for p in pillar_codes}

    # ------------------------------------------------------------------
    # 1. Get all accounts and classify as successful / unsuccessful
    # ------------------------------------------------------------------
    accounts = Account.query.filter_by(customer_id=customer_id).all()
    if len(accounts) < 2:
        return {
            'status': 'skipped',
            'reason': f'Need at least 2 accounts for calibration, got {len(accounts)}.',
        }

    account_ids = [a.account_id for a in accounts]
    successful: list[int] = []
    unsuccessful: list[int] = []
    neutral: list[int] = []

    for acct in accounts:
        latest = (
            HealthScore.query
            .filter_by(account_id=acct.account_id)
            .order_by(HealthScore.measurement_month.desc())
            .first()
        )
        if not latest or latest.health_score is None:
            neutral.append(acct.account_id)
            continue
        score = float(latest.health_score)
        if score >= ht.healthy_min():
            successful.append(acct.account_id)
        elif score < ht.at_risk_min():
            unsuccessful.append(acct.account_id)
        else:
            neutral.append(acct.account_id)

    # If we can't split into success/fail, use top-half / bottom-half
    if not successful or not unsuccessful:
        scores_by_acct = []
        for acct in accounts:
            latest = (
                HealthScore.query
                .filter_by(account_id=acct.account_id)
                .order_by(HealthScore.measurement_month.desc())
                .first()
            )
            s = float(latest.health_score) if latest and latest.health_score else 50.0
            scores_by_acct.append((acct.account_id, s))
        scores_by_acct.sort(key=lambda x: x[1], reverse=True)
        mid = max(1, len(scores_by_acct) // 2)
        successful = [a for a, _ in scores_by_acct[:mid]]
        unsuccessful = [a for a, _ in scores_by_acct[mid:]]

    # ------------------------------------------------------------------
    # 2. Query KPI averages per account
    # ------------------------------------------------------------------
    kpi_avgs = (
        db.session.query(
            DC2SKPI.account_id,
            DC2SKPI.kpi_code,
            func.avg(DC2SKPI.value).label('avg_value'),
        )
        .filter(DC2SKPI.account_id.in_(account_ids))
        .group_by(DC2SKPI.account_id, DC2SKPI.kpi_code)
        .all()
    )

    # Organise: {kpi_code: {account_id: avg_value}}
    kpi_vals: dict[str, dict[int, float]] = defaultdict(dict)
    for row in kpi_avgs:
        kpi_vals[row.kpi_code][row.account_id] = float(row.avg_value)

    # ------------------------------------------------------------------
    # 3. Calculate correlation per KPI
    # ------------------------------------------------------------------
    correlations: dict[str, float] = {}
    for kpi_code in kpi_defs:
        vals = kpi_vals.get(kpi_code, {})
        success_vals = [vals[a] for a in successful if a in vals]
        fail_vals = [vals[a] for a in unsuccessful if a in vals]

        if success_vals and fail_vals:
            s_mean = statistics.mean(success_vals)
            f_mean = statistics.mean(fail_vals)
            # Normalize to 0-1: how much does this KPI differ between groups
            correlation = min(abs(s_mean - f_mean) / max(abs(s_mean), abs(f_mean), 1.0), 1.0)
        else:
            correlation = 0.5  # neutral — not enough data
        correlations[kpi_code] = correlation

    # ------------------------------------------------------------------
    # 4. Adjust L1 weights per KPI and normalize per pillar
    # ------------------------------------------------------------------
    adjusted_l1: dict[str, float] = {}
    for kpi_code, base_w in base_l1.items():
        factor = 0.5 + correlations.get(kpi_code, 0.5)
        adjusted_l1[kpi_code] = base_w * factor

    # Group by pillar and normalize each pillar to sum to 1.0
    kpi_weights_by_pillar: dict[str, dict[str, float]] = defaultdict(dict)
    for kpi_code, w in adjusted_l1.items():
        pillar = kpi_to_pillar.get(kpi_code, kpi_code.split('-')[0])
        kpi_weights_by_pillar[pillar][kpi_code] = w

    for pillar in kpi_weights_by_pillar:
        total = sum(kpi_weights_by_pillar[pillar].values())
        if total > 0:
            kpi_weights_by_pillar[pillar] = {
                k: round(v / total, 4) for k, v in kpi_weights_by_pillar[pillar].items()
            }
            # Force exact 1.0 sum: adjust last weight to absorb rounding error
            _keys = list(kpi_weights_by_pillar[pillar].keys())
            _diff = round(1.0 - sum(kpi_weights_by_pillar[pillar].values()), 4)
            if _diff != 0 and _keys:
                kpi_weights_by_pillar[pillar][_keys[-1]] = round(
                    kpi_weights_by_pillar[pillar][_keys[-1]] + _diff, 4)

    # ------------------------------------------------------------------
    # 5. Adjust L2 pillar weights
    # ------------------------------------------------------------------
    adjusted_l2: dict[str, float] = {}
    for pillar in pillar_codes:
        pillar_kpis = [k for k, p in kpi_to_pillar.items() if p == pillar]
        if pillar_kpis:
            avg_corr = statistics.mean(
                correlations.get(k, 0.5) for k in pillar_kpis
            )
        else:
            avg_corr = 0.5
        adjusted_l2[pillar] = base_l2.get(pillar, 0.2) * (0.5 + avg_corr)

    # Normalize to sum to 1.0
    l2_total = sum(adjusted_l2.values())
    if l2_total > 0:
        adjusted_l2 = {k: round(v / l2_total, 4) for k, v in adjusted_l2.items()}
        # Force exact 1.0 sum for L2 as well
        _l2_keys = list(adjusted_l2.keys())
        _l2_diff = round(1.0 - sum(adjusted_l2.values()), 4)
        if _l2_diff != 0 and _l2_keys:
            adjusted_l2[_l2_keys[-1]] = round(adjusted_l2[_l2_keys[-1]] + _l2_diff, 4)

    # ------------------------------------------------------------------
    # 6. Compute significant changes report
    # ------------------------------------------------------------------
    significant_changes = []
    for kpi_code in sorted(base_l1.keys()):
        pillar = kpi_to_pillar.get(kpi_code, kpi_code.split('-')[0])
        old = base_l1[kpi_code]
        new = kpi_weights_by_pillar.get(pillar, {}).get(kpi_code, old)
        if old > 0:
            change_pct = ((new - old) / old) * 100
            if abs(change_pct) > 10:
                significant_changes.append({
                    'kpi_code': kpi_code,
                    'pillar': pillar,
                    'old_weight': round(old, 4),
                    'new_weight': round(new, 4),
                    'change_pct': round(change_pct, 1),
                })

    # ------------------------------------------------------------------
    # 7. Apply weight changes — direct or via approval queue
    #
    # Toggle: WIZARD_C_APPROVAL_REQUIRED
    #   OFF (default) → apply weights directly (demo mode, instant feedback)
    #   ON → submit to approval queue, customer owner/senior CSM must approve
    #         + notify all CSMs about the pending change
    # ------------------------------------------------------------------
    config = CustomerConfig.query.filter_by(customer_id=customer_id).first()
    if not config:
        config = CustomerConfig(customer_id=customer_id, vertical=vertical)
        db.session.add(config)
        db.session.flush()

    _previous_l2 = config.dc2s_pillar_weights or {}
    _previous_l1 = config.dc2s_kpi_weights or {}

    # Check approval toggle — per-customer feature flag or env var
    _approval_required = False
    try:
        from models import FeatureToggle
        _ft = FeatureToggle.query.filter_by(
            customer_id=customer_id, feature_name='wizard_c_approval'
        ).first()
        if _ft and _ft.enabled:
            _approval_required = True
    except Exception:
        pass
    # Env var override (for global setting)
    import os
    if os.environ.get('WIZARD_C_APPROVAL_REQUIRED', '').lower() in ('true', '1', 'yes'):
        _approval_required = True

    approval_submitted = False
    approval_results = []

    if not _approval_required:
        # ── Direct apply (demo mode — default) ──
        config.dc2s_pillar_weights = adjusted_l2
        config.dc2s_kpi_weights = dict(kpi_weights_by_pillar)
        config.customized_by = 'wizard_c_db'
    else:
        # ── Approval queue (production mode) ──
        try:
            from approval_queue import ApprovalQueueService
            aq = ApprovalQueueService()

            # Format readable reasoning
            change_lines = []
            for sc in significant_changes:
                direction = 'increased' if sc['change_pct'] > 0 else 'decreased'
                change_lines.append(
                    f"{sc['kpi_code']} ({sc['pillar']}): {sc['old_weight']:.3f} → {sc['new_weight']:.3f} "
                    f"({direction} {abs(sc['change_pct']):.1f}%)"
                )
            reasoning = (
                f"Wizard C analyzed {len(successful)} successful and {len(unsuccessful)} unsuccessful "
                f"accounts to calibrate KPI weights. {len(significant_changes)} significant changes found:\n"
                + "\n".join(change_lines[:10])
            )

            # Submit global weight change for approval (customer owner / senior CSM)
            result = aq.submit(
                customer_id=customer_id,
                account_id='ALL',  # Portfolio-wide — approved by customer owner
                action_type='weight_calibration',
                confidence=0.75,  # Below auto-execute (0.85) → always requires human review
                predicted_outcome='weight_optimization',
                reasoning=reasoning,
                dollar_impact=None,
                action_payload={
                    'scope': 'global',
                    'pillar_weights': adjusted_l2,
                    'kpi_weights': dict(kpi_weights_by_pillar),
                    'previous_pillar_weights': _previous_l2,
                    'previous_kpi_weights': _previous_l1,
                    'significant_changes': significant_changes,
                    'successful_accounts': len(successful),
                    'unsuccessful_accounts': len(unsuccessful),
                },
                agent_id='wizard_c',
            )
            approval_results.append(result)
            approval_submitted = True

            # Notify individual CSMs about pending weight change
            try:
                from models import Notification, Account
                _csm_accounts = Account.query.filter_by(customer_id=customer_id).all()
                _csm_names = set()
                for _a in _csm_accounts:
                    _pm = _a.profile_metadata or {}
                    _csm = _pm.get('csm_name')
                    if _csm and _csm not in _csm_names:
                        _csm_names.add(_csm)
                        _notif = Notification(
                            customer_id=customer_id,
                            account_id=_a.account_id,
                            type='weight_change_pending',
                            priority='medium',
                            payload={
                                'csm_name': _csm,
                                'significant_changes': significant_changes[:5],
                                'approval_request_id': result.get('request_id'),
                                'message': (
                                    f"Wizard C proposes {len(significant_changes)} KPI weight changes. "
                                    f"Pending customer owner approval. Your accounts will be affected."
                                ),
                            },
                        )
                        db.session.add(_notif)
            except Exception:
                pass  # Notification is best-effort

            logger.info(
                f"Wizard C: weight change submitted for approval "
                f"(request_id={result.get('request_id')}, status={result.get('status')})"
            )

        except Exception as _aq_err:
            # Approval queue unavailable — fall back to direct write
            logger.warning(
                f"Wizard C: approval queue unavailable, applying directly: {_aq_err}"
            )
            config.dc2s_pillar_weights = adjusted_l2
            config.dc2s_kpi_weights = dict(kpi_weights_by_pillar)
            config.customized_by = 'wizard_c_db_direct'

    # ------------------------------------------------------------------
    # 8. Per-stage calibration (if lifecycle stages are enabled)
    # ------------------------------------------------------------------
    per_stage_calibration = {}
    lifecycle_config = config.dc2s_lifecycle_stage_weights
    if lifecycle_config and lifecycle_config.get('enabled'):
        try:
            from utils.lifecycle_stages import resolve_account_stage
            # Group accounts by their current lifecycle stage
            stage_accounts: dict[str, list[int]] = defaultdict(list)
            for acct in accounts:
                latest_hs = (
                    HealthScore.query
                    .filter_by(account_id=acct.account_id)
                    .order_by(HealthScore.measurement_month.desc())
                    .first()
                )
                month = latest_hs.measurement_month if latest_hs else datetime.utcnow().date()
                stage = resolve_account_stage(acct, month, lifecycle_config)
                stage_name = stage.get('name', 'unknown') if stage else 'unknown'
                stage_accounts[stage_name].append(acct.account_id)

            # For each stage with >= 3 accounts, run correlation analysis
            for stage_name, stage_acct_ids in stage_accounts.items():
                if len(stage_acct_ids) < 3:
                    per_stage_calibration[stage_name] = {
                        'status': 'skipped',
                        'reason': f'Only {len(stage_acct_ids)} accounts in stage (need >= 3)',
                    }
                    continue

                # Split stage accounts into successful/unsuccessful
                stage_success = [a for a in stage_acct_ids if a in successful]
                stage_fail = [a for a in stage_acct_ids if a in unsuccessful]
                if not stage_success or not stage_fail:
                    # Use top-half / bottom-half within this stage
                    stage_scores = []
                    for aid in stage_acct_ids:
                        hs = HealthScore.query.filter_by(account_id=aid) \
                            .order_by(HealthScore.measurement_month.desc()).first()
                        s = float(hs.health_score) if hs and hs.health_score else 50.0
                        stage_scores.append((aid, s))
                    stage_scores.sort(key=lambda x: x[1], reverse=True)
                    mid = max(1, len(stage_scores) // 2)
                    stage_success = [a for a, _ in stage_scores[:mid]]
                    stage_fail = [a for a, _ in stage_scores[mid:]]

                # Correlate within this stage
                stage_correlations = {}
                for kpi_code in kpi_defs:
                    vals = kpi_vals.get(kpi_code, {})
                    s_vals = [vals[a] for a in stage_success if a in vals]
                    f_vals = [vals[a] for a in stage_fail if a in vals]
                    if s_vals and f_vals:
                        s_mean = statistics.mean(s_vals)
                        f_mean = statistics.mean(f_vals)
                        corr = min(abs(s_mean - f_mean) / max(abs(s_mean), abs(f_mean), 1.0), 1.0)
                    else:
                        corr = 0.5
                    stage_correlations[kpi_code] = corr

                # Adjust L2 for this stage
                stage_l2 = {}
                for pillar in pillar_codes:
                    p_kpis = [k for k, p in kpi_to_pillar.items() if p == pillar]
                    avg_c = statistics.mean(stage_correlations.get(k, 0.5) for k in p_kpis) if p_kpis else 0.5
                    stage_l2[pillar] = base_l2.get(pillar, 0.2) * (0.5 + avg_c)
                sl2_total = sum(stage_l2.values())
                if sl2_total > 0:
                    stage_l2 = {k: round(v / sl2_total, 4) for k, v in stage_l2.items()}

                per_stage_calibration[stage_name] = {
                    'status': 'calibrated',
                    'accounts': len(stage_acct_ids),
                    'successful': len(stage_success),
                    'unsuccessful': len(stage_fail),
                    'pillar_weights': stage_l2,
                }

            # Update the lifecycle config stages with calibrated weights.
            # IMPORTANT: Only overwrite pillar_weights if the stage is using
            # defaults (no explicit customization). If the customer or admin
            # set custom stage weights, preserve them — Wizard C reports its
            # recommendations in per_stage_calibration but does NOT override.
            # This protects curated lifecycle differentiation (e.g., P1 heavy
            # for onboarding, P5 heavy for growth) from being flattened.
            import copy
            from utils.lifecycle_stages import DEFAULT_STAGES
            _default_pw = {s['name']: s.get('pillar_weights') for s in DEFAULT_STAGES}

            updated_lc = copy.deepcopy(lifecycle_config)
            for stage in updated_lc.get('stages', []):
                cal = per_stage_calibration.get(stage.get('name'))
                if cal and cal.get('status') == 'calibrated':
                    current_pw = stage.get('pillar_weights', {})
                    default_pw = _default_pw.get(stage.get('name'), {})
                    # Only auto-apply if stage is still using defaults
                    if current_pw == default_pw or not current_pw:
                        stage['pillar_weights'] = cal['pillar_weights']
                        cal['auto_applied'] = True
                    else:
                        # Stage has custom weights — report recommendation only
                        cal['auto_applied'] = False
                        cal['recommendation'] = cal['pillar_weights']
                        cal['current_preserved'] = current_pw
            config.dc2s_lifecycle_stage_weights = updated_lc

        except Exception as stage_err:
            import logging as _log_stage
            _log_stage.getLogger(__name__).warning(
                f"Wizard C per-stage calibration failed (non-fatal): {stage_err}",
                exc_info=True,
            )

    db.session.commit()

    return {
        'status': 'completed',
        'pillar_weights': adjusted_l2,
        'kpi_weights': dict(kpi_weights_by_pillar),
        'successful_accounts': len(successful),
        'unsuccessful_accounts': len(unsuccessful),
        'neutral_accounts': len(neutral),
        'total_kpis_calibrated': len(adjusted_l1),
        'significant_changes': significant_changes,
        'per_stage_calibration': per_stage_calibration or None,
        'approval': {
            'mode': 'approval_required' if _approval_required else 'direct_apply',
            'submitted': approval_submitted,
            'results': approval_results,
            'message': (
                'Weight changes submitted for customer owner approval. '
                'Individual CSMs notified. Weights apply after approval.'
                if approval_submitted else
                'Weights applied directly (demo mode — toggle wizard_c_approval feature to require approval).'
                if not _approval_required else
                'Weights applied directly (approval queue unavailable).'
            ),
        },
        'calibration_date': datetime.utcnow().isoformat(),
    }
