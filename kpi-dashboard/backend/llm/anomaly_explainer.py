"""
KPI Anomaly Explainer (P6.1) — Explain why a KPI changed significantly.

Correlates KPI anomalies with signals, decisions, and stakeholder events
in the same timeframe to provide a causal explanation.

Gated behind WITH_LLM feature flag.

Usage:
    from llm.anomaly_explainer import explain_anomaly
    result = explain_anomaly(customer_id=123, account_id=456, kpi_code='P1-KPI1')
"""

import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# How far back/forward to look for correlated events
LOOKBACK_DAYS = 28
LOOKFORWARD_DAYS = 14


def _find_anomaly(account_id: int, kpi_code: str) -> Optional[Dict]:
    """Find the most significant recent anomaly for a KPI.

    Looks for the largest month-over-month change in the last 6 months.
    """
    from models import DC2SKPI

    kpis = (
        DC2SKPI.query
        .filter_by(account_id=account_id, kpi_code=kpi_code)
        .order_by(DC2SKPI.measured_at.asc())
        .all()
    )
    if len(kpis) < 2:
        return None

    # Find biggest change
    max_change = 0
    anomaly = None
    for i in range(1, len(kpis)):
        old = float(kpis[i - 1].value)
        new = float(kpis[i].value)
        if old == 0:
            continue
        pct = (new - old) / old * 100
        if abs(pct) > abs(max_change):
            max_change = pct
            anomaly = {
                'kpi_code': kpi_code,
                'kpi_name': kpis[i].kpi_code,  # TODO: resolve from catalog
                'pillar': kpis[i].pillar or kpi_code.split('-')[0],
                'old_value': round(old, 2),
                'new_value': round(new, 2),
                'change_pct': round(pct, 1),
                'anomaly_date': str(kpis[i].measured_at)[:10],
                'prev_date': str(kpis[i - 1].measured_at)[:10],
            }

    return anomaly


def _get_correlated_kpis(account_id: int, anomaly_date: str, exclude_kpi: str) -> str:
    """Find other KPIs that changed significantly around the same time."""
    from models import DC2SKPI

    try:
        target_date = datetime.strptime(anomaly_date[:10], '%Y-%m-%d')
    except (ValueError, TypeError):
        return '  (none)'

    window_start = target_date - timedelta(days=14)
    window_end = target_date + timedelta(days=14)

    kpis = (
        DC2SKPI.query
        .filter(
            DC2SKPI.account_id == account_id,
            DC2SKPI.kpi_code != exclude_kpi,
            DC2SKPI.measured_at >= window_start,
            DC2SKPI.measured_at <= window_end,
        )
        .order_by(DC2SKPI.kpi_code, DC2SKPI.measured_at)
        .all()
    )

    # Group by KPI, compute change within window
    by_kpi = defaultdict(list)
    for k in kpis:
        by_kpi[k.kpi_code].append(float(k.value))

    changes = []
    for code, vals in by_kpi.items():
        if len(vals) >= 2 and vals[0] != 0:
            pct = (vals[-1] - vals[0]) / vals[0] * 100
            if abs(pct) > 10:
                changes.append(f"  {code}: {vals[0]:.0f} → {vals[-1]:.0f} ({pct:+.0f}%)")

    return '\n'.join(changes[:5]) or '  (no significant co-movements)'


def _get_events_in_window(ctx: Dict, center_date: str, before_days: int, after_days: int) -> tuple:
    """Get events before and after a date from the context."""
    try:
        center = datetime.strptime(center_date[:10], '%Y-%m-%d')
    except (ValueError, TypeError):
        return '  (no events)', '  (no events)'

    before_start = center - timedelta(days=before_days)
    after_end = center + timedelta(days=after_days)

    before_lines = []
    after_lines = []

    for event_list in [ctx['signals'], ctx['decisions'], ctx['outcomes']]:
        for e in event_list:
            if not e.get('date'):
                continue
            try:
                edate = datetime.strptime(e['date'][:10], '%Y-%m-%d')
            except (ValueError, TypeError):
                continue

            prefix = {'SIGNAL': 'SIG', 'DECISION': 'DEC', 'OUTCOME': 'OUT'}.get(e['type'], '???')
            rev = f" (${e['revenue_impact']:,.0f})" if e.get('revenue_impact') else ''
            line = f"  [{prefix}] {e['date']}: {e['subtype']} — {e['title'][:70]}{rev}"

            if before_start <= edate < center:
                before_lines.append((edate, line))
            elif center <= edate <= after_end:
                after_lines.append((edate, line))

    before_lines.sort(key=lambda x: x[0])
    after_lines.sort(key=lambda x: x[0])

    return (
        '\n'.join(l[1] for l in before_lines) or '  (no events in window)',
        '\n'.join(l[1] for l in after_lines) or '  (no events in window)',
    )


def explain_anomaly(
    customer_id: int,
    account_id: int,
    kpi_code: str,
) -> Dict:
    """Explain why a KPI changed significantly.

    Finds the biggest recent change for the KPI, correlates with
    surrounding events, and asks Claude to explain the cause.

    Returns:
        {
            status, explanation, primary_cause, contributing_factors[],
            correlated_changes[], is_leading_indicator, recommended_response,
            confidence, anomaly_details, duration_s, tokens
        }
    """
    t0 = time.time()

    from llm.context_helpers import (
        check_llm_prerequisites, get_account_context,
        format_stakeholders, call_claude,
    )

    ok, reason = check_llm_prerequisites(customer_id)
    if not ok:
        return {'status': 'skipped', 'reason': reason, 'duration_s': round(time.time() - t0, 2)}

    # Find the anomaly
    anomaly = _find_anomaly(account_id, kpi_code)
    if not anomaly:
        return {
            'status': 'skipped',
            'reason': f'No significant anomaly found for {kpi_code}',
            'duration_s': round(time.time() - t0, 2),
        }

    # Gather context
    ctx = get_account_context(customer_id, account_id)
    if not ctx['account_name']:
        return {'status': 'error', 'reason': f'Account {account_id} not found', 'duration_s': round(time.time() - t0, 2)}

    # Events around the anomaly date
    preceding, following = _get_events_in_window(ctx, anomaly['anomaly_date'], LOOKBACK_DAYS, LOOKFORWARD_DAYS)

    # Other KPIs that changed at the same time
    correlated = _get_correlated_kpis(account_id, anomaly['anomaly_date'], kpi_code)

    from llm.prompts.anomaly_explainer import SYSTEM_PROMPT, USER_TEMPLATE

    user_prompt = USER_TEMPLATE.format(
        account_name=ctx['account_name'],
        arr=ctx['arr'],
        health_score=ctx['health_score'],
        kpi_code=anomaly['kpi_code'],
        kpi_name=anomaly['kpi_name'],
        old_value=anomaly['old_value'],
        new_value=anomaly['new_value'],
        change_pct=anomaly['change_pct'],
        anomaly_date=anomaly['anomaly_date'],
        pillar=anomaly['pillar'],
        preceding_events=preceding,
        following_events=following,
        stakeholders=format_stakeholders(ctx),
        correlated_kpis=correlated,
    )

    # Use Haiku for anomaly explanation (structured, not deep reasoning)
    result, usage, duration = call_claude(
        SYSTEM_PROMPT, user_prompt, customer_id,
        model='claude-haiku-4-5-20251001',
        max_tokens=1024,
    )

    if not result:
        return {
            'status': 'error',
            'reason': 'Claude returned no result',
            'duration_s': round(time.time() - t0, 2),
        }

    # Enrich
    result['account_id'] = account_id
    result['account_name'] = ctx['account_name']
    result['anomaly_details'] = anomaly
    result['status'] = 'completed'
    result['duration_s'] = round(time.time() - t0, 2)
    result['tokens'] = usage
    result['model'] = 'claude-haiku-4-5-20251001'

    logger.info(
        'Anomaly explanation: customer=%d account=%d kpi=%s '
        'change=%+.0f%% confidence=%.2f %.1fs',
        customer_id, account_id, kpi_code,
        anomaly['change_pct'], result.get('confidence', 0),
        result['duration_s'],
    )

    return result
