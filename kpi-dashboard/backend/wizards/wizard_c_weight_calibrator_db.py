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
    # 7. Save to CustomerConfig
    # ------------------------------------------------------------------
    config = CustomerConfig.query.filter_by(customer_id=customer_id).first()
    if not config:
        config = CustomerConfig(customer_id=customer_id, vertical=vertical)
        db.session.add(config)

    config.dc2s_pillar_weights = adjusted_l2
    config.dc2s_kpi_weights = dict(kpi_weights_by_pillar)
    config.customized_by = 'wizard_c_db'
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
        'calibration_date': datetime.utcnow().isoformat(),
    }
