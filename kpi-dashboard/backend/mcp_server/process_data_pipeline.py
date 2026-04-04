"""
process_data pipeline stages — extracted from _process_data_impl for testability.

Each stage is a standalone function that:
- Takes customer_id + any context it needs
- Returns a step description string (for steps_completed list)
- Never raises — catches exceptions and returns None on failure
- Logs its own errors

Usage from _process_data_impl:
    step = run_proactive_signal_scan(customer_id)
    if step: steps_completed.append(step)
"""

import logging
import os
import time
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# Stage 1: Proactive Signal Scan
# ═══════════════════════════════════════════════════════════════

def run_proactive_signal_scan(customer_id: int) -> Optional[str]:
    """Scan newly loaded signals for leading indicators (champion loss, etc.).

    Returns step description or None on failure.
    """
    try:
        from utils.signal_analyst import scan_signals_for_proactive_triggers
        results = scan_signals_for_proactive_triggers(customer_id)
        if results:
            return f'proactive_signals_{len(results)}_triggered'
    except Exception as e:
        logger.warning(f"Proactive signal scan failed (non-fatal): {e}")
    return None


# ═══════════════════════════════════════════════════════════════
# Stage 2: Health Score Calculation (immutable scores)
# ═══════════════════════════════════════════════════════════════

def calculate_health_scores(
    customer_id: int,
    acct_list: list,
    vertical: str,
    mode: str = 'auto',
) -> Tuple[Optional[str], Set[int], Dict[str, float]]:
    """Calculate health scores for new (account, month) pairs.

    In 'auto' mode, existing scores are immutable — only new months are scored.
    In 'full_recalc' mode, all months are rewritten with current weights.

    Returns:
        (step_description, changed_account_ids, step_timings)
    """
    import utils.health_thresholds as ht
    from datetime import date as _date
    from sqlalchemy import create_engine, text as _text
    import json as _json
    from models import DC2SKPI, CustomerConfig
    from extensions import db as _db

    timings = {}
    changed_account_ids = set()
    t0 = time.time()

    try:
        # Get health calculation function for this vertical
        from mcp_server.cs_pulse_onboarding import _get_health_functions
        calculate_fn, _, _ = _get_health_functions(vertical)

        acct_by_id = {a.account_id: a for a in acct_list}

        # Load lifecycle stage config
        _lifecycle_config = None
        try:
            _cc = CustomerConfig.query.filter_by(customer_id=customer_id).first()
            if _cc and _cc.dc2s_lifecycle_stage_weights:
                _lifecycle_config = _cc.dc2s_lifecycle_stage_weights
        except Exception:
            pass

        # Build set of already-scored (account_id, month) pairs
        scored_set = set()
        if mode != 'full_recalc':
            _existing_rows = _db.session.execute(_db.text(
                "SELECT account_id, measurement_month FROM health_scores "
                "WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = :cid)"
            ), {"cid": customer_id}).fetchall()
            scored_set = {(int(r[0]), r[1]) for r in _existing_rows}

        # Fetch all KPIs, group by (account, month), skip already-scored
        all_kpis = DC2SKPI.query.filter(
            DC2SKPI.account_id.in_([a.account_id for a in acct_list])
        ).all()

        account_month_kpis = defaultdict(lambda: defaultdict(list))
        _skipped_immutable = 0
        for k in all_kpis:
            if k.measured_at:
                month_key = k.measured_at.date().replace(day=1) if hasattr(k.measured_at, 'date') else k.measured_at.replace(day=1)
            else:
                month_key = _date.today().replace(day=1)

            if (k.account_id, month_key) in scored_set:
                _skipped_immutable += 1
                continue
            account_month_kpis[(k.account_id, month_key)][k.kpi_code].append(float(k.value))

        timings['kpi_grouping'] = round(time.time() - t0, 2)

        if _skipped_immutable:
            logger.info(
                f"Immutable scores: skipped {_skipped_immutable} KPI rows "
                f"({len(scored_set)} scored months preserved) — "
                f"{len(account_month_kpis)} new (account, month) pairs to score"
            )

        # Calculate health for each new (account, month) pair
        score_rows = []
        scores_skipped = 0
        for (account_id, month), kpi_groups in account_month_kpis.items():
            try:
                kpi_vals = {code: sum(vals) / len(vals) for code, vals in kpi_groups.items()}
                if not kpi_vals:
                    scores_skipped += 1
                    continue

                # Lifecycle stage weight overrides
                _pw_override, _kw_override = None, None
                if _lifecycle_config:
                    try:
                        from utils.lifecycle_stages import resolve_account_stage, get_stage_weights
                        _acct_obj = acct_by_id.get(account_id)
                        if _acct_obj:
                            _stage = resolve_account_stage(_acct_obj, month, _lifecycle_config)
                            _pw_override, _kw_override = get_stage_weights(_stage)
                    except Exception:
                        pass

                if _pw_override or _kw_override:
                    try:
                        health, pillars = calculate_fn(
                            kpi_vals, customer_id=customer_id,
                            pillar_weight_overrides=_pw_override,
                            kpi_weight_overrides=_kw_override,
                        )
                    except TypeError:
                        health, pillars = calculate_fn(kpi_vals, customer_id=customer_id)
                else:
                    health, pillars = calculate_fn(kpi_vals, customer_id=customer_id)

                score_rows.append({
                    "aid": account_id,
                    "month": month,
                    "score": round(health, 2),
                    "status": ht.classify(health),
                    "pillars": _json.dumps({k: round(v, 2) for k, v in pillars.items()}) if pillars else None,
                })
            except Exception as calc_err:
                logger.warning(f"Health score calc failed for account {account_id} month {month}: {calc_err}")

        timings['health_calc'] = round(time.time() - t0, 2)

        changed_account_ids = set(r['aid'] for r in score_rows)

        # Write scores to DB
        scores_written = 0
        database_url = os.environ.get('DATABASE_URL')
        if database_url and score_rows:
            engine = create_engine(database_url)
            with engine.begin() as conn:
                if mode == 'full_recalc':
                    for row in score_rows:
                        conn.execute(_text("""
                            INSERT INTO health_scores
                                (account_id, measurement_month, health_score, health_status, contributing_pillars)
                            VALUES (:aid, :month, :score, :status, :pillars)
                            ON CONFLICT (account_id, measurement_month)
                            DO UPDATE SET
                                health_score = EXCLUDED.health_score,
                                health_status = EXCLUDED.health_status,
                                contributing_pillars = EXCLUDED.contributing_pillars
                        """), row)
                        scores_written += 1
                else:
                    for row in score_rows:
                        conn.execute(_text("""
                            INSERT INTO health_scores
                                (account_id, measurement_month, health_score, health_status, contributing_pillars)
                            VALUES (:aid, :month, :score, :status, :pillars)
                            ON CONFLICT (account_id, measurement_month) DO NOTHING
                        """), row)
                        scores_written += 1

                # Compute change_from_last_month for changed accounts
                if changed_account_ids:
                    conn.execute(_text("""
                        UPDATE health_scores hs
                        SET change_from_last_month = hs.health_score - prev.health_score
                        FROM (
                            SELECT account_id, measurement_month, health_score,
                                   LAG(health_score) OVER (PARTITION BY account_id ORDER BY measurement_month) AS prev_score
                            FROM health_scores
                            WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = :cid)
                        ) prev
                        WHERE hs.account_id = prev.account_id
                          AND hs.measurement_month = prev.measurement_month
                          AND prev.prev_score IS NOT NULL
                    """), {"cid": customer_id})
            engine.dispose()

        timings['health_write'] = round(time.time() - t0, 2)

        logger.info(
            f"Health scores: {scores_written} written, {scores_skipped} skipped — "
            f"customer {customer_id} (mode={mode})"
        )

        step = f'health_scores_{mode}_{scores_written}_written'
        return step, changed_account_ids, timings

    except Exception as e:
        logger.error(f"Health score calculation failed: {e}", exc_info=True)
        return None, set(), timings


# ═══════════════════════════════════════════════════════════════
# Stage 3: Wizard A — Arc classification
# ═══════════════════════════════════════════════════════════════

def run_wizard_a_step(
    customer_id: int,
    changed_account_ids: Set[int],
    mode: str = 'auto',
) -> Tuple[Optional[str], float]:
    """Run Wizard A arc classification for changed accounts.

    Returns (step_description, duration_seconds).
    """
    t0 = time.time()
    try:
        from wizards.wizard_a_journey_db import run_wizard_a
        result = run_wizard_a(
            customer_id,
            account_ids=changed_account_ids if mode != 'full_recalc' else None,
        )
        duration = round(time.time() - t0, 2)
        logger.info(
            f"Wizard A complete: {result.get('processed', 0)} accounts, "
            f"{result.get('edges_created', 0)} edges created"
        )
        return f"wizard_a_{result.get('processed', 0)}_accounts", duration
    except Exception as e:
        logger.warning(f"Wizard A failed (non-fatal): {e}", exc_info=True)
        return None, round(time.time() - t0, 2)


# ═══════════════════════════════════════════════════════════════
# Stage 4: Signal Analyst (Layer A)
# ═══════════════════════════════════════════════════════════════

def run_signal_analyst(customer_id: int) -> Optional[str]:
    """Compare latest two health scores per account, trigger analysis on drops."""
    try:
        from utils.signal_analyst import check_and_analyze
        from models import Account, HealthScore
        from sqlalchemy import desc

        acct_list = Account.query.filter_by(customer_id=customer_id).all()
        for acct in acct_list:
            try:
                last_two = (
                    HealthScore.query
                    .filter_by(account_id=acct.account_id)
                    .order_by(desc(HealthScore.measurement_month))
                    .limit(2)
                    .all()
                )
                if len(last_two) >= 2:
                    check_and_analyze(
                        customer_id=customer_id,
                        account_id=acct.account_id,
                        health_before=float(last_two[1].health_score),
                        health_after=float(last_two[0].health_score),
                    )
            except Exception as e:
                logger.debug(f"signal_analyst: skipped account {acct.account_id}: {e}")
    except Exception as e:
        logger.warning(f"Signal analyst trigger failed (non-fatal): {e}")
    return None


# ═══════════════════════════════════════════════════════════════
# Stage 5: Urgent Signal Scanner (Layer C)
# ═══════════════════════════════════════════════════════════════

def run_urgent_scanner(customer_id: int) -> Optional[str]:
    """Scan for revenue risk pre-emption signals."""
    try:
        from utils.urgent_signal_scanner import scan_for_urgent_signals
        from models import Account

        acct_list = Account.query.filter_by(customer_id=customer_id).all()
        total = 0
        for acct in acct_list:
            try:
                alerts = scan_for_urgent_signals(
                    customer_id=customer_id,
                    account_id=acct.account_id,
                )
                total += len(alerts)
            except Exception as e:
                logger.debug(f"urgent_signal_scanner: skipped account {acct.account_id}: {e}")
        if total:
            return f'urgent_alerts_created_{total}'
    except Exception as e:
        logger.warning(f"Urgent signal scanner failed (non-fatal): {e}")
    return None


# ═══════════════════════════════════════════════════════════════
# Stage 6: ROI Engine
# ═══════════════════════════════════════════════════════════════

def run_roi_engine(customer_id: int) -> Optional[str]:
    """Calculate portfolio ROI snapshot for dashboards."""
    try:
        from outcome_roi_engine import calculate_outcome_story
        from outcome_roi_api import _extract_historical_actuals, _extract_accounts_at_risk
        from models import Account

        accounts = Account.query.filter_by(customer_id=customer_id).all()
        if accounts:
            total_arr = sum(float(a.revenue) for a in accounts if a.revenue) or None
            acct_ids = [a.account_id for a in accounts]
            metric_actuals, _data_src = _extract_historical_actuals(accounts, 6)
            at_risk = _extract_accounts_at_risk(accounts, customer_id=customer_id)
            vertical = getattr(accounts[0], 'vertical', None)

            roi_story = calculate_outcome_story(
                metric_actuals=metric_actuals,
                target_improvement_pct=1.0,
                account_arr=total_arr,
                projection_months=6,
                accounts_at_risk=at_risk,
                customer_id=customer_id,
                account_ids=acct_ids,
                vertical=vertical,
            )
            if roi_story:
                logger.info(
                    f"ROI Engine: portfolio ROI calculated for customer {customer_id} "
                    f"({len(accounts)} accounts, ARR=${total_arr or 0:,.0f})"
                )
                return 'roi_engine_calculated'
    except Exception as e:
        logger.warning(f"ROI engine failed (non-fatal): {e}")
    return None


# ═══════════════════════════════════════════════════════════════
# Stage 7: QDRANT Indexing
# ═══════════════════════════════════════════════════════════════

def run_qdrant_indexing(customer_id: int) -> Optional[str]:
    """Index signals for semantic search."""
    try:
        qdrant_url = os.environ.get('QDRANT_URL')
        if qdrant_url:
            from utils.qdrant_signal_search import SignalVectorStore
            store = SignalVectorStore(customer_id)
            indexed = store.index_signals(limit=500)
            if indexed > 0:
                return f'qdrant_signals_indexed_{indexed}'
    except Exception as e:
        logger.debug(f"QDRANT indexing skipped (non-fatal): {e}")
    return None


# ═══════════════════════════════════════════════════════════════
# Stage 8: Publish Health Score Events
# ═══════════════════════════════════════════════════════════════

def publish_health_events(customer_id: int, acct_ids: List[int]) -> None:
    """Publish HEALTH_SCORES_UPDATED events for downstream subscribers."""
    try:
        from event_system import event_manager, EventType
        from extensions import db

        batch_accounts = []
        for aid in acct_ids:
            latest = db.session.execute(db.text(
                "SELECT health_score FROM health_scores "
                "WHERE account_id = :aid ORDER BY measurement_month DESC LIMIT 1"
            ), {"aid": aid}).fetchone()
            if latest and latest[0] is not None:
                batch_accounts.append({'account_id': aid, 'score': float(latest[0])})

        for ba in batch_accounts:
            event_manager.publisher.publish(
                EventType.HEALTH_SCORES_UPDATED,
                customer_id,
                {
                    'account_id': ba['account_id'],
                    'score': ba['score'],
                    'source': 'process_data',
                },
                priority=2,
            )

        logger.info(
            f"Published HEALTH_SCORES_UPDATED for {len(batch_accounts)} accounts "
            f"(customer {customer_id})"
        )
    except Exception as e:
        logger.debug(f"Event publish failed (non-fatal): {e}")


# ═══════════════════════════════════════════════════════════════
# Stage 9: Record WizardRun for audit + incremental detection
# ═══════════════════════════════════════════════════════════════

def record_wizard_run(
    customer_id: int,
    mode: str,
    duration_s: float,
    scores_written: int,
    changed_accounts: int,
    timings: dict,
) -> None:
    """Write WizardRun row for audit trail."""
    try:
        from models import WizardRun
        from extensions import db

        run = WizardRun(
            customer_id=customer_id,
            config={
                'wizard': 'process_data',
                'mode': mode,
                'duration_s': duration_s,
                'scores_written': scores_written,
                'changed_accounts': changed_accounts,
                'timings': timings,
            },
        )
        db.session.add(run)
        db.session.commit()
    except Exception as e:
        logger.debug(f"WizardRun tracking failed (non-fatal): {e}")
