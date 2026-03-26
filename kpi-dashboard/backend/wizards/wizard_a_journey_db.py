"""
Wizard A — Arc Intelligence Engine (rebuilt Sprint 1).
=======================================================

Two responsibilities:
1. Arc Classification: assigns arc_type, arc_phase, arc_confidence to each
   account by reading HealthScore history + ContextNode signals + DC2SKPI data.
2. Arc Edge Generation: generates ContextEdge rows from the arc's edge_topology.

Also preserves the original DB-native journey generation logic
(_run_journey_generation) for backward compatibility with Wizard B / UI.

No filesystem access — everything comes from / goes to PostgreSQL.
"""

from __future__ import annotations

import logging
import statistics
from collections import defaultdict
from datetime import datetime

import utils.health_thresholds as ht

logger = logging.getLogger(__name__)


def run_wizard_a(customer_id: int) -> dict:
    """
    Top-level entrypoint for Wizard A Arc Intelligence Engine.

    Must be called inside a Flask app context.

    Two steps per account:
      1. classify_arc()    → arc_type, confidence, phase
      2. generate_edges()  → ContextEdge rows in DB

    Also runs legacy journey generation for backward compatibility.

    Returns:
        dict with arc classification results and edge counts.
    """
    from models import Account
    from extensions import db
    from utils.arc_classifier import classify_arc
    from utils.arc_edge_generator import generate_edges

    accounts = Account.query.filter_by(customer_id=customer_id).all()
    if not accounts:
        return {
            'status': 'skipped',
            'reason': f'No accounts found for customer {customer_id}.',
            'processed': 0,
            'edges_created': 0,
            'arcs': {},
        }

    results: dict = {
        'status': 'completed',
        'processed': 0,
        'edges_created': 0,
        'arcs': {},
    }

    for account in accounts:
        try:
            arc_type, confidence, phase = classify_arc(account.account_id)

            # Persist arc assignment to Account model
            account.arc_type       = arc_type
            account.arc_phase      = phase
            account.arc_confidence = confidence
            db.session.commit()

            # Generate causal edges
            edges = generate_edges(account.account_id, arc_type, phase)

            results['processed'] += 1
            results['edges_created'] += edges
            results['arcs'][account.account_id] = {
                'arc_type':   arc_type,
                'phase':      phase,
                'confidence': confidence,
                'edges':      edges,
            }
            logger.info(
                f"Wizard A: account={account.account_id} ({account.account_name}) "
                f"arc={arc_type} phase={phase} confidence={confidence:.2f} edges={edges}"
            )
        except Exception as e:
            logger.error(
                f"Wizard A failed for account {account.account_id} "
                f"({account.account_name}): {e}",
                exc_info=True,
            )
            # Continue with next account — never abort the loop
            continue

    # Run legacy journey generation (non-fatal)
    try:
        journey_result = _run_journey_generation(customer_id)
        results['journeys_created'] = journey_result.get('journeys_created', 0)
        results['patterns'] = journey_result.get('patterns', {})
    except Exception as e:
        logger.warning(f"Wizard A legacy journey generation failed (non-fatal): {e}")

    logger.info(
        f"Wizard A complete: customer={customer_id} "
        f"processed={results['processed']} edges={results['edges_created']}"
    )
    return results


def _run_journey_generation(customer_id: int) -> dict:
    """
    Legacy journey generation logic — preserved for backward compatibility.

    Builds journey timeline per account from KPI + health data and upserts
    into the journey_data table for the Journey Visualizer UI.
    """
    from models import Account, DC2SKPI, HealthScore, JourneyData
    from extensions import db
    from sqlalchemy import func

    accounts = Account.query.filter_by(customer_id=customer_id).all()
    if not accounts:
        return {
            'status': 'skipped',
            'reason': f'No accounts found for customer {customer_id}.',
        }

    account_ids = [a.account_id for a in accounts]
    pattern_counts: dict[str, int] = defaultdict(int)
    journeys_created = 0

    # ------------------------------------------------------------------
    # 1. Fetch KPI time-series grouped by (account, month, kpi_code)
    # ------------------------------------------------------------------
    kpi_rows = (
        db.session.query(
            DC2SKPI.account_id,
            DC2SKPI.kpi_code,
            func.date_trunc('month', DC2SKPI.measured_at).label('month'),
            func.avg(DC2SKPI.value).label('avg_value'),
        )
        .filter(DC2SKPI.account_id.in_(account_ids))
        .group_by(DC2SKPI.account_id, DC2SKPI.kpi_code,
                  func.date_trunc('month', DC2SKPI.measured_at))
        .order_by(DC2SKPI.account_id,
                  func.date_trunc('month', DC2SKPI.measured_at))
        .all()
    )

    # Organise: {account_id: {month_str: {kpi_code: avg_value}}}
    kpi_by_acct: dict[int, dict[str, dict[str, float]]] = defaultdict(
        lambda: defaultdict(dict)
    )
    for row in kpi_rows:
        month_str = row.month.strftime('%Y-%m') if row.month else 'unknown'
        kpi_by_acct[row.account_id][month_str][row.kpi_code] = float(row.avg_value)

    # ------------------------------------------------------------------
    # 2. Fetch health score history per account
    # ------------------------------------------------------------------
    health_rows = (
        HealthScore.query
        .filter(HealthScore.account_id.in_(account_ids))
        .order_by(HealthScore.account_id, HealthScore.measurement_month)
        .all()
    )
    health_by_acct: dict[int, list[tuple[str, float]]] = defaultdict(list)
    for hs in health_rows:
        month_str = hs.measurement_month.strftime('%Y-%m') if hs.measurement_month else 'unknown'
        health_by_acct[hs.account_id].append(
            (month_str, float(hs.health_score) if hs.health_score else 0.0)
        )

    # ------------------------------------------------------------------
    # 3. Build journey per account
    # ------------------------------------------------------------------
    for acct in accounts:
        aid = acct.account_id
        months_data = kpi_by_acct.get(aid, {})
        health_series = health_by_acct.get(aid, [])
        sorted_months = sorted(months_data.keys())

        if len(sorted_months) < 1:
            continue

        # Health scores as list of floats
        h_scores = [s for _, s in health_series] if health_series else []

        # Classify trajectory
        pattern = _classify_trajectory(h_scores)
        pattern_counts[pattern] += 1

        # Build events list (one per month)
        events = []
        for i, month in enumerate(sorted_months):
            kpis_this_month = months_data[month]

            # Find matching health score for this month
            month_health = None
            for hm, hs in health_series:
                if hm == month:
                    month_health = hs
                    break
            if month_health is None and h_scores:
                # Use latest available
                month_health = h_scores[min(i, len(h_scores) - 1)]

            phase = ht.classify(month_health) if month_health is not None else 'unknown'

            # Trend: compare to previous month
            prev_health = events[-1]['health_score_after'] if events else month_health
            delta = (month_health or 0) - (prev_health or 0)
            sentiment = 1.0 if delta > 2 else (-1.0 if delta < -2 else 0.0)

            events.append({
                'week': (i + 1) * 4,  # approximate week number
                'month': month,
                'health_score_after': round(month_health, 2) if month_health else None,
                'phase': phase,
                'sentiment_value': sentiment,
                'kpi_snapshot': {k: round(v, 2) for k, v in list(kpis_this_month.items())[:10]},
            })

        journey_json = {
            'account_id': aid,
            'account_name': acct.account_name,
            'pattern_type': pattern,
            'starting_health': h_scores[0] if h_scores else None,
            'ending_health': h_scores[-1] if h_scores else None,
            'lowest_health': min(h_scores) if h_scores else None,
            'highest_health': max(h_scores) if h_scores else None,
            'total_weeks': len(sorted_months) * 4,
            'total_months': len(sorted_months),
            'events': events,
            'summary': {
                'total_events': len(events),
                'months_covered': len(sorted_months),
                'kpi_codes_seen': len(set(
                    k for m in months_data.values() for k in m.keys()
                )),
            },
        }

        # Upsert into JourneyData
        existing = JourneyData.query.filter_by(
            customer_id=customer_id, account_id=aid,
        ).first()
        if existing:
            existing.journey_json = journey_json
            existing.journey_pattern = pattern
            existing.total_weeks = journey_json['total_weeks']
            existing.updated_at = datetime.utcnow()
        else:
            jd = JourneyData(
                customer_id=customer_id,
                account_id=aid,
                journey_json=journey_json,
                journey_pattern=pattern,
                total_weeks=journey_json['total_weeks'],
                generator_version='2.0-db',
            )
            db.session.add(jd)
        journeys_created += 1

    db.session.commit()

    return {
        'status': 'completed',
        'accounts_processed': len(accounts),
        'journeys_created': journeys_created,
        'patterns': dict(pattern_counts),
    }


def _classify_trajectory(scores: list[float]) -> str:
    """Classify account trajectory from health score time-series."""
    if not scores:
        return 'unknown'

    n = len(scores)
    if n < 2:
        if scores[0] < ht.at_risk_min():
            return 'crisis'
        return 'stable'

    # Split into first half and second half
    mid = max(1, n // 2)
    first_avg = statistics.mean(scores[:mid])
    last_avg = statistics.mean(scores[mid:])

    has_crisis = any(s < ht.at_risk_min() for s in scores)

    if has_crisis:
        # Check if recovering from crisis
        if last_avg > first_avg + 5:
            return 'recovery'
        return 'crisis'
    if last_avg > first_avg + 5:
        return 'improving'
    if last_avg < first_avg - 5:
        return 'declining'
    return 'stable'
