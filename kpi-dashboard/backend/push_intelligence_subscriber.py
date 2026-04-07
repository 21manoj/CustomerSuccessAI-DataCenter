#!/usr/bin/env python3
"""
Push Intelligence Subscriber
=============================

Wires the three "push" layers into the event bus so they fire automatically:

  Layer A  – Signal Analyst  (already wired via OnboardingCompleteSubscriber)
  Layer B  – Arc → Playbook auto-dispatch  (NEW — this file)
  Layer C  – Urgent Revenue Scanner        (NEW — this file)

Event triggers:
  HEALTH_SCORES_UPDATED  →  Layer C immediate scan  (revenue at-risk)
  HEALTH_SCORES_UPDATED  →  Layer B arc→playbook     (if arc detected + auto_trigger_on_arc)

Also provides a DailyScheduler that calls process_data once every 24 h
for every active customer with fresh data.
"""

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────
#  Layer C — Urgent Scanner Subscriber  (fires IMMEDIATELY on CG update)
# ─────────────────────────────────────────────────────────────────────

class UrgentScannerSubscriber:
    """
    Listens to HEALTH_SCORES_UPDATED.
    For each account whose health changed, runs the Layer C urgent
    scanner right away — no waiting for cron.

    Debounce: max once per account per 5 minutes.
    """

    def __init__(self, cooldown_seconds: int = 300):
        self._cooldown = cooldown_seconds
        self._last_scan: dict[int, float] = {}  # account_id → timestamp
        self._lock = threading.Lock()

    def handle_event(self, event) -> None:
        try:
            customer_id = event.customer_id
            data = event.data or {}
            account_id = data.get('account_id')
            if not account_id:
                return

            # Cooldown per account
            with self._lock:
                now = time.time()
                last = self._last_scan.get(account_id, 0)
                if now - last < self._cooldown:
                    return
                self._last_scan[account_id] = now

            # Non-blocking scan in background thread
            t = threading.Thread(
                target=self._scan,
                args=(customer_id, account_id),
                name=f"urgent-scan-{account_id}",
                daemon=True,
            )
            t.start()

        except Exception as e:
            logger.error(f"UrgentScannerSubscriber error: {e}", exc_info=True)

    def _scan(self, customer_id: int, account_id: int) -> None:
        try:
            from flask import current_app
            app = current_app._get_current_object()
        except RuntimeError:
            # No app context — get it from the global
            try:
                from app_v3_minimal import app
            except ImportError:
                logger.debug("UrgentScannerSubscriber: no Flask app available")
                return

        with app.app_context():
            try:
                from utils.urgent_signal_scanner import scan_for_urgent_signals
                alerts = scan_for_urgent_signals(customer_id, account_id)
                if alerts:
                    logger.info(
                        f"Layer C: {len(alerts)} urgent alert(s) for "
                        f"customer {customer_id} / account {account_id}"
                    )
            except Exception as e:
                logger.debug(f"Layer C scan skipped for {account_id}: {e}")


# ─────────────────────────────────────────────────────────────────────
#  Layer B — Standalone playbook auto-trigger (V2-only)
#
#  Called from:
#    1. _process_data_impl() — direct call after health scores written
#    2. ArcPlaybookSubscriber — event-driven backup (when event system
#       shares the same process as the Flask app)
# ─────────────────────────────────────────────────────────────────────

# Canonical arc → playbook mapping (from config/arc_playbook_map.json)
_ARC_PLAYBOOK_MAP = {
    'crisis_recovery':          'PB-02',
    'exec_sponsor_change':      'PB-04',
    'competitive_displacement': 'PB-03',
    'stalled_deployment':       'PB-01',
    'silent_churn':             'PB-06',
    'expansion_champion':       'PB-08',
    'land_and_expand':          'PB-08',
    'seasonal_surge':           'PB-07',
    # Legacy aliases
    'crisis':           'PB-02',
    'champion_loss':    'PB-04',
    'budget_pressure':  'PB-06',
    'recovery':         'PB-02',
    'onboarding':       'PB-01',
    'stable':           None,
    'expansion':        'PB-08',
}


def _link_stakeholders_to_decision(
    customer_id: int,
    account_id: int,
    account,
    decision_node,
) -> None:
    """Link existing STAKEHOLDER nodes to a DECISION node via INVOLVES edges.

    Also creates lightweight system stakeholder nodes from profile_metadata
    (assigned_csm, champion) if no STAKEHOLDER nodes exist from CSV.
    """
    try:
        from models import ContextNode, ContextEdge, db

        # 1. Find existing STAKEHOLDER nodes for this account
        stakeholders = (
            ContextNode.query
            .filter_by(
                account_id=account_id,
                customer_id=customer_id,
                node_type='STAKEHOLDER',
            )
            .all()
        )

        # 2. If no CSV stakeholders, create from profile_metadata
        if not stakeholders and account:
            meta = account.profile_metadata or {}
            for field, role in [('assigned_csm', 'CSM'), ('champion', 'Champion'),
                                ('executive_sponsor', 'Executive Sponsor')]:
                name = meta.get(field)
                if name and isinstance(name, str) and name.strip():
                    sn = ContextNode(
                        account_id=account_id,
                        customer_id=customer_id,
                        node_type='STAKEHOLDER',
                        source='system',
                        node_subtype=role.lower().replace(' ', '_'),
                        title=f'{name} ({role})',
                        properties={
                            'name': name.strip(),
                            'role': role,
                            'auto_created': True,
                            'source_field': field,
                        },
                        tier=2,
                        occurred_at=datetime.utcnow(),
                        source_platform='playbook_auto_trigger',
                    )
                    db.session.add(sn)
                    stakeholders.append(sn)

            if stakeholders:
                db.session.flush()
                logger.info(
                    f"Layer 2: auto-created {len(stakeholders)} STAKEHOLDER node(s) "
                    f"from profile_metadata for account {account_id}"
                )

        # 3. Create INVOLVES edges from stakeholders → decision
        for sh in stakeholders:
            # Dedup: skip if edge already exists
            existing = (
                ContextEdge.query
                .filter_by(
                    from_node_id=sh.node_id,
                    to_node_id=decision_node.node_id,
                    edge_type='INVOLVES',
                )
                .first()
            )
            if not existing:
                db.session.add(ContextEdge(
                    customer_id=customer_id,
                    from_node_id=sh.node_id,
                    to_node_id=decision_node.node_id,
                    edge_type='INVOLVES',
                    confidence=0.8,
                    source_platform='playbook_auto_trigger',
                    properties={'label': f'{sh.title or "Stakeholder"} involved in decision'},
                ))

        if stakeholders:
            db.session.commit()

    except Exception as e:
        logger.debug(f"_link_stakeholders_to_decision failed (non-fatal): {e}")
        try:
            from extensions import db as _db
            _db.session.rollback()
        except Exception:
            pass


def evaluate_playbook_triggers_for_customer(customer_id: int) -> list:
    """Evaluate all at-risk/critical accounts for playbook auto-trigger.

    Scans accounts with health < 70, checks arc classification, maps to
    playbook, deduplicates against recent V2 executions, and creates new
    PlaybookExecutionV2 records for qualifying accounts.

    Returns list of dicts: [{'account_id': ..., 'playbook_id': ..., 'decision': ...}, ...]
    Safe to call multiple times — 7-day dedup window prevents duplicates.
    """
    from models import Account, HealthScore
    from extensions import db

    accounts = Account.query.filter_by(customer_id=customer_id).all()
    results = []

    for account in accounts:
        hs = (
            HealthScore.query.filter_by(account_id=account.account_id)
            .order_by(HealthScore.measurement_month.desc())
            .first()
        )
        health = float(hs.health_score) if hs and hs.health_score else None
        if not health or health >= 70:
            continue

        result = evaluate_playbook_trigger_for_account(
            customer_id, account.account_id, health, _ARC_PLAYBOOK_MAP
        )
        if result:
            results.append(result)

    return results


def evaluate_playbook_trigger_for_account(
    customer_id: int,
    account_id: int,
    health_score: float,
    arc_playbook_map: dict = None,
) -> dict:
    """Evaluate a single account for playbook auto-trigger (V2-only).

    Returns dict with trigger result, or None if no trigger.
    Dedup: skips if PlaybookExecutionV2 exists for same account+playbook within 7 days.
    """
    from models import ContextNode, Account, PlaybookExecutionV2, db
    from datetime import datetime
    import uuid

    if arc_playbook_map is None:
        arc_playbook_map = _ARC_PLAYBOOK_MAP

    # 1. Get arc classification (prefer Account.arc_type, fall back to ContextNode)
    account = db.session.get(Account, account_id)
    if not account:
        return None
    account_name = account.account_name or f'Account {account_id}'

    arc_type = account.arc_type
    arc_confidence = account.arc_confidence or 0.5

    if not arc_type:
        # Fall back to latest arc_detection ContextNode
        arc_node = (
            ContextNode.query
            .filter(
                ContextNode.account_id == account_id,
                ContextNode.customer_id == customer_id,
                ContextNode.node_type == 'SIGNAL',
                ContextNode.node_subtype == 'arc_detection',
            )
            .order_by(ContextNode.occurred_at.desc())
            .first()
        )
        if not arc_node:
            return None
        arc_type = (arc_node.properties or {}).get('arc_type', 'unknown')
        arc_confidence = (arc_node.properties or {}).get('confidence', 0.5)

    playbook_id = arc_playbook_map.get(arc_type)
    if not playbook_id:
        return None

    # 2. Dedup: check PlaybookExecutionV2 for recent execution (V2-only)
    recent_cutoff = datetime.utcnow() - timedelta(days=7)
    existing = (
        PlaybookExecutionV2.query
        .filter(
            PlaybookExecutionV2.account_id == account_id,
            PlaybookExecutionV2.playbook_id == playbook_id,
            PlaybookExecutionV2.triggered_at > recent_cutoff,
            PlaybookExecutionV2.status.in_(['in_progress', 'completed']),
        )
        .first()
    )
    if existing:
        logger.debug(
            f"Playbook {playbook_id} already running/completed for "
            f"account {account_id} within 7d — skipping"
        )
        return {'account_id': account_id, 'playbook_id': playbook_id,
                'decision': 'skipped_dedup', 'existing_execution_id': existing.execution_id}

    # 3. Decide: rule-based (LLM validation is optional overlay)
    decision = 'auto_approved'
    confidence = arc_confidence
    reasoning = f"Arc '{arc_type}' detected with confidence {arc_confidence:.2f}"

    try:
        from playbook_trigger_validator import PlaybookTriggerValidator
        validator = PlaybookTriggerValidator()
        result = validator.validate_trigger(
            account_id=str(account_id),
            customer_id=customer_id,
            playbook_id=playbook_id,
            trigger_context={
                'arc_type': arc_type,
                'arc_confidence': arc_confidence,
                'health_score': health_score,
                'source': 'arc_detection',
            },
            account_name=account_name,
            health_score=health_score,
        )
        decision = result.decision.value if hasattr(result.decision, 'value') else str(result.decision)
        confidence = result.confidence
        reasoning = result.reasoning
    except Exception:
        # Fallback: rule-based
        if health_score < 50 and arc_confidence >= 0.7:
            decision = 'auto_approved'
            confidence = arc_confidence
        elif health_score < 70:
            decision = 'pending_manual_approval'
            confidence = arc_confidence * 0.8
        else:
            decision = 'auto_rejected'
            confidence = arc_confidence * 0.5

    # 4. Act on decision
    if decision == 'auto_approved':
        arr = float(account.revenue or 0)
        execution_id = f"auto-{playbook_id}-{account_id}-{uuid.uuid4().hex[:8]}"

        v2 = PlaybookExecutionV2(
            execution_id=execution_id,
            customer_id=customer_id,
            account_id=account_id,
            playbook_id=playbook_id,
            playbook_name=f'Auto: {playbook_id} ({arc_type})',
            triggered_by='health_drop',
            arc_type=arc_type,
            status='in_progress',
            phase='stabilize',
            health_at_trigger=health_score,
            health_status_at_trigger='critical' if health_score < 50 else 'at_risk',
            arr_at_trigger=arr,
            csm_hourly_rate=85.0,
        )
        db.session.add(v2)
        db.session.commit()

        logger.info(
            f"✅ Layer B AUTO-APPROVED: playbook {playbook_id} for "
            f"account {account_name} (arc={arc_type}, "
            f"confidence={confidence:.2f}, health={health_score:.1f})"
        )

        # Activity log: playbook auto-trigger
        try:
            from activity_logging import ActivityLogger
            ActivityLogger.log_activity(
                customer_id=customer_id,
                action_type='playbook_auto_trigger',
                action_description=(
                    f"Playbook {playbook_id} auto-triggered for {account_name} "
                    f"(arc={arc_type}, health={health_score:.1f})"
                ),
                resource_type='playbook',
                resource_id=execution_id,
                details={
                    'playbook_id': playbook_id,
                    'account_id': account_id,
                    'account_name': account_name,
                    'arc_type': arc_type,
                    'arc_confidence': arc_confidence,
                    'health_score': health_score,
                    'decision': decision,
                    'validation_confidence': confidence,
                },
            )
        except Exception:
            pass

        # Write DECISION node to context graph
        try:
            from models import ContextEdge
            decision_node = ContextNode(
                account_id=account_id,
                customer_id=customer_id,
                node_type='DECISION',
                source='system',
                node_subtype=f'playbook_{arc_type}',
                title=f'Playbook {playbook_id} Auto-Approved — {account_name}',
                properties={
                    'playbook_id': playbook_id,
                    'execution_id': execution_id,
                    'arc_type': arc_type,
                    'arc_confidence': arc_confidence,
                    'validation_decision': decision,
                    'validation_confidence': confidence,
                    'health_score': health_score,
                },
                tier=2,
                occurred_at=datetime.utcnow(),
                source_platform='playbook_auto_trigger',
                source_event_id=f'playbook:{execution_id}',
            )
            db.session.add(decision_node)
            db.session.flush()

            # Link arc_detection signal → playbook decision
            # If no arc_detection signal exists, CREATE one (fallback)
            arc_signal = (
                ContextNode.query
                .filter_by(account_id=account_id, customer_id=customer_id,
                           node_subtype='arc_detection')
                .order_by(ContextNode.occurred_at.desc())
                .first()
            )
            if not arc_signal:
                # Create arc_detection signal so the causal chain is complete
                arc_signal = ContextNode(
                    account_id=account_id,
                    customer_id=customer_id,
                    node_type='SIGNAL',
                    source='system',
                    node_subtype='arc_detection',
                    title=f'Arc detected: {arc_type} (health={health_score:.0f})',
                    properties={
                        'arc_type': arc_type,
                        'confidence': arc_confidence,
                        'health_score': health_score,
                        'auto_created': True,
                    },
                    tier=2,
                    occurred_at=datetime.utcnow(),
                    source_platform='playbook_auto_trigger',
                )
                db.session.add(arc_signal)
                db.session.flush()
                logger.info(
                    f"Layer B: auto-created arc_detection SIGNAL node for "
                    f"account {account_id} (arc={arc_type})"
                )

            db.session.add(ContextEdge(
                customer_id=customer_id,
                from_node_id=arc_signal.node_id,
                to_node_id=decision_node.node_id,
                edge_type='TRIGGERED',
                confidence=arc_confidence,
                source_platform='playbook_auto_trigger',
                properties={'label': f'Arc detection triggered {playbook_id}'},
            ))

            # Layer 2: Link stakeholders to this DECISION via INVOLVES edges
            _link_stakeholders_to_decision(
                customer_id, account_id, account, decision_node
            )
            db.session.commit()
        except Exception as cg_err:
            logger.warning(f"Context graph DECISION write failed (non-fatal): {cg_err}")

        # Publish event (best-effort, for any downstream subscribers)
        try:
            from event_system import event_manager, EventType
            event_manager.publisher.publish(
                EventType.PLAYBOOK_AUTO_TRIGGERED, customer_id,
                {'account_id': account_id, 'playbook_id': playbook_id,
                 'execution_id': execution_id, 'arc_type': arc_type},
                priority=1,
            )
        except Exception:
            pass

        return {'account_id': account_id, 'account_name': account_name,
                'playbook_id': playbook_id, 'decision': 'auto_approved',
                'execution_id': execution_id, 'health': health_score,
                'arc_type': arc_type}

    elif decision == 'pending_manual_approval':
        logger.info(
            f"⏳ Layer B PENDING REVIEW: playbook {playbook_id} for "
            f"account {account_name} (confidence={confidence:.2f})"
        )
        try:
            from models import Notification
            Notification.query  # ensure model is available
            notif = Notification(
                customer_id=customer_id, account_id=account_id,
                type='playbook_approval_needed', priority='high',
                payload={
                    'playbook_id': playbook_id, 'arc_type': arc_type,
                    'health_score': health_score, 'confidence': confidence,
                    'reasoning': reasoning,
                    'detected_at': datetime.utcnow().isoformat(),
                },
            )
            db.session.add(notif)
            db.session.commit()
        except Exception:
            pass
        return {'account_id': account_id, 'playbook_id': playbook_id,
                'decision': 'pending_manual_approval'}

    else:
        return {'account_id': account_id, 'playbook_id': playbook_id,
                'decision': 'auto_rejected'}


class ArcPlaybookSubscriber:
    """
    Listens to HEALTH_SCORES_UPDATED.
    When an account's health crosses a boundary (e.g. healthy→at_risk),
    checks for arc classifications and triggers playbook validation via
    the Layer B validator.

    If confidence > 0.8 → auto-approve → publish PLAYBOOK_AUTO_TRIGGERED.
    If 0.4 ≤ confidence ≤ 0.8 → queue for CSM manual review.
    If confidence < 0.4 → auto-reject.
    """

    # Reuse module-level mapping
    ARC_PLAYBOOK_MAP = _ARC_PLAYBOOK_MAP

    def __init__(self, cooldown_seconds: int = 600):
        self._cooldown = cooldown_seconds
        self._last_eval: dict[int, float] = {}  # account_id → timestamp
        self._lock = threading.Lock()

    def handle_event(self, event) -> None:
        try:
            import utils.push_intelligence_config as pic
            if not pic.layer_b_enabled():
                return
            if not pic.auto_trigger_on_arc():
                return

            customer_id = event.customer_id
            data = event.data or {}
            account_id = data.get('account_id')
            new_score = data.get('score') or data.get('health_score')
            if not account_id or new_score is None:
                return

            # Only trigger for at-risk or critical accounts
            from utils.health_thresholds import classify
            cls = classify(float(new_score))
            if cls == 'healthy':
                return

            # Cooldown per account
            with self._lock:
                now = time.time()
                last = self._last_eval.get(account_id, 0)
                if now - last < self._cooldown:
                    return
                self._last_eval[account_id] = now

            # Evaluate in background thread
            t = threading.Thread(
                target=self._evaluate,
                args=(customer_id, account_id, float(new_score)),
                name=f"arc-playbook-{account_id}",
                daemon=True,
            )
            t.start()

        except Exception as e:
            logger.error(f"ArcPlaybookSubscriber error: {e}", exc_info=True)

    def _evaluate(self, customer_id: int, account_id: int, health_score: float) -> None:
        try:
            from flask import current_app
            app = current_app._get_current_object()
        except RuntimeError:
            try:
                from app_v3_minimal import app
            except ImportError:
                logger.debug("ArcPlaybookSubscriber: no Flask app available")
                return

        with app.app_context():
            try:
                self._do_evaluate(customer_id, account_id, health_score)
            except Exception as e:
                logger.debug(f"Layer B eval skipped for {account_id}: {e}")

    def _do_evaluate(self, customer_id: int, account_id: int, health_score: float) -> None:
        """Delegate to the standalone function (V2-only)."""
        evaluate_playbook_trigger_for_account(
            customer_id, account_id, health_score, self.ARC_PLAYBOOK_MAP
        )


# ─────────────────────────────────────────────────────────────────────
#  Daily Scheduler — runs process_data for all active customers
# ─────────────────────────────────────────────────────────────────────

class DailyProcessDataScheduler:
    """
    Background thread that fires process_data for every active customer
    once every interval (default 24 hours).

    - Runs as a daemon thread so it dies with the process.
    - Skips customers with no accounts or no recent data.
    - Fully non-blocking — errors never crash the app.
    """

    def __init__(self, interval_hours: int = 24):
        self._interval = interval_hours * 3600
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._loop,
            name="daily-process-data",
            daemon=True,
        )
        self._thread.start()
        logger.info(
            f"✅ Daily process_data scheduler started "
            f"(interval={self._interval // 3600}h)"
        )

    def stop(self) -> None:
        self._running = False

    def _loop(self) -> None:
        # Wait 60s on startup to let the app fully initialize
        time.sleep(60)

        while self._running:
            try:
                self._run_cycle()
            except Exception as e:
                logger.error(f"DailyScheduler cycle error: {e}", exc_info=True)

            # Sleep in 60s increments so we can stop quickly
            remaining = self._interval
            while remaining > 0 and self._running:
                time.sleep(min(remaining, 60))
                remaining -= 60

    def _run_cycle(self) -> None:
        try:
            from flask import current_app
            app = current_app._get_current_object()
        except RuntimeError:
            try:
                from app_v3_minimal import app
            except ImportError:
                logger.debug("DailyScheduler: no Flask app available")
                return

        with app.app_context():
            from models import Customer, Account, db

            # Get all customers that have accounts (Customer model has no status column)
            customer_ids_rows = (
                db.session.query(Account.customer_id)
                .distinct()
                .all()
            )
            customer_ids_list = [r[0] for r in customer_ids_rows]
            customers = Customer.query.filter(
                Customer.customer_id.in_(customer_ids_list)
            ).all() if customer_ids_list else []

            if not customers:
                customer_ids = customer_ids_rows
                customer_ids = [c[0] for c in customer_ids]
            else:
                customer_ids = [c.customer_id for c in customers]

            logger.info(
                f"DailyScheduler: processing {len(customer_ids)} customers"
            )

            for cid in customer_ids:
                try:
                    self._process_customer(cid)
                except Exception as e:
                    logger.warning(f"DailyScheduler: customer {cid} failed: {e}")

    def _process_customer(self, customer_id: int) -> None:
        """Run health score recalculation for a single customer."""
        from models import Account, HealthScore, DC2SKPI, db
        from datetime import datetime, date

        # Only process if there's recent KPI data (within last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_kpi = (
            DC2SKPI.query
            .filter(
                DC2SKPI.customer_id == customer_id,
                DC2SKPI.uploaded_at >= week_ago,
            )
            .first()
        )

        if not recent_kpi:
            logger.debug(f"DailyScheduler: customer {customer_id} has no recent data — skipping")
            return

        # Recalculate health scores for all accounts
        accounts = Account.query.filter_by(customer_id=customer_id).all()
        recalculated = 0

        for account in accounts:
            try:
                # Get previous health score for delta detection
                prev_score = None
                prev_hs = (
                    HealthScore.query
                    .filter_by(account_id=account.account_id)
                    .order_by(HealthScore.calculated_at.desc())
                    .first()
                )
                if prev_hs and prev_hs.health_score is not None:
                    prev_score = float(prev_hs.health_score)

                from utils.score_calculator import calculate_health_score
                score_result = calculate_health_score(account.account_id, customer_id)
                if score_result:
                    recalculated += 1
                    new_score = score_result.get('health_score')

                    # Publish health score update event → triggers Layer C + Layer B
                    try:
                        from event_system import event_manager, EventType
                        event_manager.publisher.publish(
                            EventType.HEALTH_SCORES_UPDATED,
                            customer_id,
                            {
                                'account_id': account.account_id,
                                'score': new_score,
                                'source': 'daily_scheduler',
                            },
                            priority=2,
                        )
                    except Exception:
                        pass

                    # Layer A: trigger Signal Analyst if health dropped >10pts
                    if (prev_score is not None and new_score is not None
                            and prev_score - new_score >= 10):
                        try:
                            from utils.signal_analyst import check_and_analyze
                            check_and_analyze(
                                customer_id=customer_id,
                                account_id=account.account_id,
                                health_before=prev_score,
                                health_after=float(new_score),
                            )
                            logger.info(
                                f"Layer A: health drop {prev_score:.0f}→{new_score:.0f} "
                                f"for account {account.account_id} — Signal Analyst triggered"
                            )
                        except Exception as sa_err:
                            logger.debug(f"Layer A skipped for {account.account_id}: {sa_err}")

            except Exception as e:
                logger.debug(f"DailyScheduler: account {account.account_id} recalc failed: {e}")

        if recalculated:
            logger.info(
                f"DailyScheduler: customer {customer_id} — "
                f"recalculated {recalculated}/{len(accounts)} accounts"
            )
