"""
Weight calibration history for Wizard C / KPI config changes.

Shared by MCP get_calibration_history and Ask AI.
"""

from __future__ import annotations


def fetch_calibration_history(customer_id: int, limit: int = 10) -> dict:
    from models import WeightCalibrationHistory

    records = (
        WeightCalibrationHistory.query
        .filter_by(customer_id=int(customer_id))
        .order_by(WeightCalibrationHistory.calibrated_at.desc())
        .limit(limit)
        .all()
    )

    if not records:
        return {
            'scope': 'customer',
            'customer_id': customer_id,
            'calibrations': [],
            'count': 0,
            'message': (
                'No calibration history found. Run Wizard C or '
                'configure_customer_kpis to create weight records.'
            ),
        }

    calibrations = [r.to_dict() for r in records]
    latest = records[0]
    earliest = records[-1]
    drift = {}
    if latest.pillar_weights and earliest.pillar_weights:
        for pillar in latest.pillar_weights:
            new_w = latest.pillar_weights.get(pillar, 0)
            old_w = earliest.pillar_weights.get(pillar, 0)
            if old_w > 0:
                drift[pillar] = {
                    'current': round(new_w, 4),
                    'earliest': round(old_w, 4),
                    'change_pct': round((new_w - old_w) / old_w * 100, 1),
                }

    return {
        'scope': 'customer',
        'customer_id': customer_id,
        'calibrations': calibrations,
        'count': len(calibrations),
        'drift_summary': drift,
        'latest_source': latest.triggered_by or latest.source,
        'latest_date': latest.calibrated_at.isoformat() if latest.calibrated_at else None,
        'note': (
            'Use pillar_weights and correlation_scores for what-if analysis. '
            'drift_summary shows how weights evolved from earliest to latest calibration.'
        ),
    }
