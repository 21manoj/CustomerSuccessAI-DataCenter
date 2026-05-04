#!/usr/bin/env python3
"""
Layer A — Proactive LLM Signal Analyst
=======================================

Called from _process_data_impl() when account health drops >10 pts OR a
severity=critical signal lands.

Flow:
    1. check_and_analyze() checks the drop threshold.
    2. If triggered, collect last-N SIGNAL ContextNodes + pillar deltas.
    3. Build a concise prompt and call LLM (Anthropic Claude first, OpenAI fallback).
    4. Store result as Notification(type='signal_insight').
    5. Write inferred ContextNode (source='inferred') and edge to most recent observed customer signal.
    6. Return payload dict — or None if analysis was not triggered.

Errors are caught at every layer; this function must NEVER crash process_data.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

import utils.push_intelligence_config as pic

logger = logging.getLogger(__name__)


def check_and_analyze(
    customer_id: int,
    account_id: int,
    health_before: float,
    health_after: float,
    arc_type: Optional[str] = None,
) -> Optional[dict]:
    """
    Trigger LLM analysis if health dropped > health_drop_trigger() pts.

    Args:
        customer_id:   Customer scope for DB lookup.
        account_id:    Account that experienced the health change.
        health_before: Health score before the latest process_data run.
        health_after:  Health score after the latest process_data run.
        arc_type:      Optional Wizard A arc label (e.g. 'champion_loss').

    Returns:
        Notification payload dict if analysis ran, None otherwise.
    """
    delta = health_after - health_before
    if not pic.layer_a_enabled() or delta > -pic.health_drop_trigger():
        return None  # Not a significant drop — skip

    try:
        # ── Lazy imports to avoid circular dependencies ──
        from models import ContextNode, HealthScore, Notification, db, Account

        # ── 1. Collect signals — QDRANT semantic search with SQL fallback ──
        signal_texts = []
        _qdrant_used = False
        try:
            from utils.qdrant_signal_search import SignalVectorStore
            _store = SignalVectorStore(customer_id)
            _query = f"health decline signals engagement drop risk indicators for account {account_id}"
            _semantic = _store.search(_query, account_id=account_id, top_k=pic.max_signals_context())
            if _semantic:
                signal_texts = [
                    f"- [{s['subtype']}] {s['title']} (relevance: {s['score']:.0%}, sentiment: {s['sentiment']})"
                    for s in _semantic
                ]
                _qdrant_used = True
                logger.debug(f"signal_analyst: QDRANT returned {len(_semantic)} semantic matches for account {account_id}")
        except Exception as _q_err:
            logger.debug(f"signal_analyst: QDRANT unavailable, falling back to SQL: {_q_err}")

        if not _qdrant_used:
            recent_signals = (
                ContextNode.query
                .filter_by(account_id=account_id, node_type='SIGNAL')
                .order_by(ContextNode.occurred_at.desc())
                .limit(pic.max_signals_context())
                .all()
            )
            signal_texts = [
                f"- [{n.node_subtype or 'signal'}] {n.title or '(no title)'}"
                for n in recent_signals
            ]

        # ── 2. Pillar deltas from last two HealthScore rows ──
        last_two_scores = (
            HealthScore.query
            .filter_by(account_id=account_id)
            .order_by(HealthScore.measurement_month.desc())
            .limit(2)
            .all()
        )

        pillar_delta_text = ""
        if len(last_two_scores) >= 2:
            # contributing_pillars is a JSON column — already a dict from SQLAlchemy
            _cp0 = last_two_scores[0].contributing_pillars
            _cp1 = last_two_scores[1].contributing_pillars
            current_pillars = _cp0 if isinstance(_cp0, dict) else ({} if not _cp0 else __import__('json').loads(_cp0))
            previous_pillars = _cp1 if isinstance(_cp1, dict) else ({} if not _cp1 else __import__('json').loads(_cp1))
            if current_pillars and previous_pillars:
                lines = []
                for pillar, cur_val in current_pillars.items():
                    prev_val = previous_pillars.get(pillar, cur_val)
                    d = round(cur_val - prev_val, 1)
                    lines.append(f"  {pillar}: {cur_val:.1f} (Δ{d:+.1f})")
                pillar_delta_text = "\n".join(lines)

        # ── 3. Account name for context ──
        account = db.session.get(Account, account_id)
        account_name = account.account_name if account else f"Account {account_id}"

        # ── 4. Build LLM prompt ──
        arc_note = f"\nWizard A arc classification: {arc_type}" if arc_type else ""
        signal_block = "\n".join(signal_texts) if signal_texts else "  (no recent signals)"
        pillar_block = pillar_delta_text if pillar_delta_text else "  (pillar data unavailable)"

        prompt = f"""You are a Customer Success analyst. An account has experienced a significant health drop.

Account: {account_name} (ID {account_id})
Health change: {health_before:.1f} → {health_after:.1f} (Δ{delta:+.1f}){arc_note}

Recent signals (last {pic.max_signals_context()}):
{signal_block}

Pillar scores (current with delta from previous month):
{pillar_block}

In 3-4 concise bullet points, explain:
1. The most likely root cause of this health drop.
2. The highest-risk outcome if not addressed within 30 days.
3. The single most impactful action the CSM should take this week.
4. Any expansion or recovery opportunity visible in the data.

Be specific and action-oriented. Avoid generic advice."""

        # ── 5. Call OpenAI ──
        analysis_text = _call_llm(customer_id, prompt)
        if not analysis_text:
            logger.warning(
                f"signal_analyst: OpenAI returned empty response for account {account_id}"
            )
            return None

        # ── 6. Build payload ──
        payload = {
            'account_id': account_id,
            'account_name': account_name,
            'health_before': round(health_before, 1),
            'health_after': round(health_after, 1),
            'delta': round(delta, 1),
            'arc_type': arc_type,
            'analysis': analysis_text,
            'signal_count': len(recent_signals),
            'generated_at': datetime.utcnow().isoformat(),
        }

        # ── 7. Store as Notification ──
        notification = Notification(
            customer_id=customer_id,
            account_id=account_id,
            type='signal_insight',
            priority='critical' if delta <= -20 else 'high',
            payload=payload,
        )
        db.session.add(notification)
        db.session.commit()

        logger.info(
            f"signal_analyst: analysis stored for account {account_id} "
            f"(Δ{delta:+.1f}, arc={arc_type})"
        )

        # ── 8. Write system signal to context graph ──
        try:
            from models import ContextEdge
            insight_node = ContextNode(
                account_id=account_id,
                customer_id=customer_id,
                node_type='SIGNAL',
                source='inferred',        # runtime LLM analysis over real customer signals
                node_subtype='ai_insight',
                title=f'AI Insight: health {health_before:.0f}→{health_after:.0f}',
                properties={
                    'health_before':   health_before,
                    'health_after':    health_after,
                    'arc_type':        arc_type,
                    'notification_id': notification.id,
                    'triggered_by':    'signal_analyst',
                },
                tier=2,
                occurred_at=datetime.utcnow(),  # detection timestamp (when we noticed), not narrative date
            )
            db.session.add(insight_node)
            db.session.flush()

            # Connect customer signals → AI insight (LED_TO — causal chain)
            recent_signals = (
                ContextNode.query
                .filter_by(account_id=account_id, node_type='SIGNAL', source='observed')
                .order_by(ContextNode.occurred_at.desc())
                .limit(3)
                .all()
            )

            # Back-date insight to most recent triggering signal for timeline coherence
            if recent_signals and recent_signals[0].occurred_at:
                insight_node.occurred_at = recent_signals[0].occurred_at
                db.session.flush()

            for sig in recent_signals:
                db.session.add(ContextEdge(
                    customer_id=customer_id,
                    from_node_id=sig.node_id,
                    to_node_id=insight_node.node_id,
                    edge_type='LED_TO',
                    confidence=0.85,
                    source_platform='signal_analyst',
                    properties={'label': f'Signal led to health drop insight'},
                ))

            # Connect AI insight → downstream DECISION nodes (if any exist for this account)
            recent_decision = (
                ContextNode.query
                .filter_by(account_id=account_id, customer_id=customer_id, node_type='DECISION')
                .order_by(ContextNode.occurred_at.desc())
                .first()
            )
            if recent_decision:
                db.session.add(ContextEdge(
                    customer_id=customer_id,
                    from_node_id=insight_node.node_id,
                    to_node_id=recent_decision.node_id,
                    edge_type='TRIGGERED',
                    confidence=0.7,
                    source_platform='signal_analyst',
                    properties={'label': 'AI insight informed decision'},
                ))
            db.session.commit()
        except Exception as graph_err:
            logger.error(
                f"signal_analyst: context graph write failed for account {account_id}: {graph_err}",
                exc_info=True,
            )
            try:
                db.session.rollback()
            except Exception:
                pass

        return payload

    except Exception as e:
        logger.error(
            f"signal_analyst: check_and_analyze failed for account {account_id}: {e}",
            exc_info=True,
        )
        try:
            from extensions import db as _db
            _db.session.rollback()
        except Exception:
            pass
        return None


# ─────────────────────────────────────────────────────────────────────
#  PROACTIVE: Trigger on leading qualitative signals (not health drops)
# ─────────────────────────────────────────────────────────────────────

# Signal types that should trigger IMMEDIATE analysis — these are leading
# indicators that predict health score drops BEFORE they show up in KPIs.
HIGH_RISK_SIGNAL_TYPES = {
    # Champion / stakeholder changes
    'champion_change':        {'priority': 'critical', 'playbook': 'PB-DC-02', 'label': 'Champion departed or changed'},
    'champion_loss':          {'priority': 'critical', 'playbook': 'PB-DC-02', 'label': 'Key champion lost'},
    'executive_change':       {'priority': 'critical', 'playbook': 'PB-DC-02', 'label': 'Executive sponsor changed'},
    'stakeholder_departure':  {'priority': 'high',     'playbook': 'PB-DC-02', 'label': 'Key stakeholder departed'},
    'stakeholder_escalation': {'priority': 'high',     'playbook': 'PB-DC-02', 'label': 'Stakeholder escalated concern'},
    # Budget / commercial
    'budget_cut':             {'priority': 'high',     'playbook': 'PB-DC-03', 'label': 'Budget reduction signaled'},
    'budget_pressure':        {'priority': 'high',     'playbook': 'PB-DC-03', 'label': 'Budget pressure detected'},
    'contract_dispute':       {'priority': 'critical', 'playbook': 'PB-DC-01', 'label': 'Contract dispute escalated'},
    'downgrade_request':      {'priority': 'critical', 'playbook': 'PB-DC-01', 'label': 'Downgrade or cancellation request'},
    # Escalation (all variants from CSV data)
    'escalation':             {'priority': 'high',     'playbook': 'PB-DC-01', 'label': 'Issue escalated'},
    'support_escalation':     {'priority': 'high',     'playbook': 'PB-DC-01', 'label': 'Support ticket escalated'},
    'executive_escalation':   {'priority': 'critical', 'playbook': 'PB-DC-01', 'label': 'Executive-level escalation'},
    'critical_incident':      {'priority': 'critical', 'playbook': 'PB-DC-01', 'label': 'Critical incident reported'},
    # Competitive / churn
    'competitor_mention':     {'priority': 'high',     'playbook': 'PB-DC-04', 'label': 'Competitor mentioned by customer'},
    'usage_decline':          {'priority': 'high',     'playbook': 'PB-DC-04', 'label': 'Product usage declining'},
    'engagement_gap':         {'priority': 'high',     'playbook': 'PB-DC-04', 'label': 'Customer engagement gap detected'},
    # Sentiment / satisfaction (Predictive 11+ tier signals)
    'nps_decline':            {'priority': 'high',     'playbook': 'PB-DC-04', 'label': 'NPS score declining — friction vs value risk'},
    'nps_drop':               {'priority': 'high',     'playbook': 'PB-DC-04', 'label': 'NPS dropped significantly'},
}


def analyze_on_signal(
    customer_id: int,
    account_id: int,
    signal_type: str,
    signal_content: str,
    signal_sentiment: str = 'negative',
) -> Optional[dict]:
    """
    Proactive analysis triggered by a leading qualitative signal.

    Unlike check_and_analyze() which waits for a health score drop,
    this function fires IMMEDIATELY when a high-risk signal arrives
    (champion loss, budget cut, escalation, etc.).

    Args:
        customer_id:      Customer scope.
        account_id:       Account that received the signal.
        signal_type:      Signal type (must be in HIGH_RISK_SIGNAL_TYPES).
        signal_content:   The signal text/description.
        signal_sentiment: Sentiment (negative, neutral, positive).

    Returns:
        Notification payload dict if analysis ran, None otherwise.
    """
    if not pic.layer_a_enabled():
        return None

    risk_info = HIGH_RISK_SIGNAL_TYPES.get(signal_type)
    if not risk_info:
        return None  # Not a high-risk signal type — skip

    try:
        from models import ContextNode, HealthScore, Notification, db, Account

        # ── 1. Get current health score for context ──
        account = db.session.get(Account, account_id)
        account_name = account.account_name if account else f"Account {account_id}"

        latest_hs = (
            HealthScore.query
            .filter_by(account_id=account_id)
            .order_by(HealthScore.measurement_month.desc())
            .first()
        )
        current_health = float(latest_hs.health_score) if latest_hs and latest_hs.health_score else None

        # ── 2. Get pillar scores for context ──
        pillar_text = ""
        if latest_hs and latest_hs.contributing_pillars:
            cp = latest_hs.contributing_pillars
            pillars = cp if isinstance(cp, dict) else __import__('json').loads(cp)
            pillar_text = "\n".join(f"  {k}: {v:.1f}" for k, v in pillars.items())

        # ── 3. Get recent signals — QDRANT semantic search with SQL fallback ──
        signal_texts = []
        _qdrant_used = False
        try:
            from utils.qdrant_signal_search import SignalVectorStore
            _store = SignalVectorStore(customer_id)
            _query = f"{signal_type} {risk_label} signals for account with engagement and retention risk"
            _semantic = _store.search(_query, account_id=account_id, top_k=pic.max_signals_context())
            if _semantic:
                signal_texts = [
                    f"- [{s['subtype']}] {s['title']} (relevance: {s['score']:.0%}, sentiment: {s['sentiment']})"
                    for s in _semantic
                ]
                _qdrant_used = True
        except Exception:
            pass

        if not _qdrant_used:
            recent_signals = (
                ContextNode.query
                .filter_by(account_id=account_id, node_type='SIGNAL')
                .order_by(ContextNode.occurred_at.desc())
                .limit(pic.max_signals_context())
                .all()
            )
            signal_texts = [
                f"- [{n.node_subtype or 'signal'}] {n.title or '(no title)'}"
                for n in recent_signals
            ]

        # ── 4. Build proactive LLM prompt ──
        health_line = f"Current health score: {current_health:.1f}/100" if current_health else "Health score: not yet calculated"
        pillar_block = pillar_text if pillar_text else "  (not yet calculated)"
        signal_block = "\n".join(signal_texts) if signal_texts else "  (no recent signals)"

        prompt = f"""You are a Customer Success analyst. A HIGH-RISK leading signal has just arrived for an account. This is a PROACTIVE alert — the health score has NOT dropped yet, but this signal predicts it WILL.

Account: {account_name} (ID {account_id})
{health_line}

⚠️ CRITICAL SIGNAL: {risk_info['label']}
Signal type: {signal_type}
Signal content: {signal_content}
Sentiment: {signal_sentiment}

Recent account signals:
{signal_block}

Current pillar scores:
{pillar_block}

In 3-4 concise bullet points, explain:
1. The PREDICTED impact of this signal on account health over the next 30-60 days.
2. Which KPI pillars will be most affected and by approximately how much.
3. The single most urgent action the CSM should take THIS WEEK (before the score drops).
4. What recovery looks like if we act now vs. wait for the score to drop.

Be specific, predictive, and urgent. This is a pre-emptive intervention window."""

        # ── 5. Call LLM ──
        analysis_text = _call_llm(customer_id, prompt)
        if not analysis_text:
            logger.warning(f"signal_analyst: LLM returned empty for proactive signal on account {account_id}")
            return None

        # ── 6. Build payload ──
        payload = {
            'account_id': account_id,
            'account_name': account_name,
            'trigger': 'proactive_signal',
            'signal_type': signal_type,
            'signal_content': signal_content[:200],
            'risk_label': risk_info['label'],
            'recommended_playbook': risk_info['playbook'],
            'current_health': current_health,
            'analysis': analysis_text,
            'signal_count': len(recent_signals),
            'generated_at': datetime.utcnow().isoformat(),
        }

        # ── 7. Store as Notification ──
        notification = Notification(
            customer_id=customer_id,
            account_id=account_id,
            type='proactive_signal_insight',
            priority=risk_info['priority'],
            payload=payload,
        )
        db.session.add(notification)
        db.session.commit()

        logger.info(
            f"signal_analyst: PROACTIVE analysis for account {account_id} "
            f"(signal={signal_type}, playbook={risk_info['playbook']}, "
            f"priority={risk_info['priority']})"
        )

        # ── 8. Write inferred signal to context graph ──
        try:
            from models import ContextEdge
            insight_node = ContextNode(
                account_id=account_id,
                customer_id=customer_id,
                node_type='SIGNAL',
                source='inferred',
                node_subtype='proactive_insight',
                title=f'Proactive Alert: {risk_info["label"]}',
                properties={
                    'signal_type':     signal_type,
                    'risk_label':      risk_info['label'],
                    'playbook':        risk_info['playbook'],
                    'current_health':  current_health,
                    'notification_id': notification.id,
                    'triggered_by':    'signal_analyst_proactive',
                },
                tier=2,
                occurred_at=datetime.utcnow(),  # placeholder, back-dated below
            )
            db.session.add(insight_node)
            db.session.flush()

            # Link triggering customer signal → proactive insight (causal)
            trigger_signal = (
                ContextNode.query
                .filter_by(account_id=account_id, node_type='SIGNAL', source='observed')
                .order_by(ContextNode.occurred_at.desc())
                .first()
            )

            # Back-date insight to triggering signal for timeline coherence
            if trigger_signal and trigger_signal.occurred_at:
                insight_node.occurred_at = trigger_signal.occurred_at
                db.session.flush()

            if trigger_signal:
                db.session.add(ContextEdge(
                    from_node_id=trigger_signal.node_id,
                    to_node_id=insight_node.node_id,
                    edge_type='LED_TO',
                    confidence=1.0,
                    customer_id=customer_id,
                    source_platform='signal_analyst',
                    properties={'label': f'Proactive detection: {signal_type}'},
                ))

            # Create DECISION node for ALL high-risk signals (not just stakeholder types)
            playbook_id = risk_info.get('playbook')
            signal_occurred_at = insight_node.occurred_at or datetime.utcnow()

            if playbook_id:
                decision_node = ContextNode(
                    account_id=account_id,
                    customer_id=customer_id,
                    node_type='DECISION',
                    source='inferred',
                    node_subtype=f'respond_to_{signal_type}',
                    title=f'Action needed: {risk_info["label"]}',
                    properties={
                        'recommended_playbook': playbook_id,
                        'signal_type': signal_type,
                        'auto_created': True,
                        'triggered_by': 'signal_analyst_proactive',
                    },
                    tier=2,
                    occurred_at=signal_occurred_at,
                    source_platform='signal_analyst',
                )
                db.session.add(decision_node)
                db.session.flush()

                # Signal → Decision (TRIGGERED)
                db.session.add(ContextEdge(
                    customer_id=customer_id,
                    from_node_id=insight_node.node_id,
                    to_node_id=decision_node.node_id,
                    edge_type='TRIGGERED',
                    confidence=0.9,
                    source_platform='signal_analyst',
                    properties={'label': f'{signal_type} triggered response decision'},
                ))

                # Link stakeholders via INVOLVES (for all signal types — stakeholders
                # are relevant to any intervention, not just stakeholder-related signals)
                _STAKEHOLDER_SIGNAL_TYPES = {
                    'champion_change', 'champion_loss', 'executive_change',
                    'stakeholder_departure', 'stakeholder_escalation',
                }
                if signal_type in _STAKEHOLDER_SIGNAL_TYPES:
                    stakeholders = (
                        ContextNode.query
                        .filter_by(
                            account_id=account_id,
                            customer_id=customer_id,
                            node_type='STAKEHOLDER',
                        )
                        .all()
                    )
                    for sh in stakeholders:
                        db.session.add(ContextEdge(
                            customer_id=customer_id,
                            from_node_id=sh.node_id,
                            to_node_id=decision_node.node_id,
                            edge_type='INVOLVES',
                            confidence=0.7,
                            source_platform='signal_analyst',
                            properties={'label': f'{sh.title or "Stakeholder"} involved'},
                        ))

            db.session.commit()
        except Exception as graph_err:
            logger.error(f"signal_analyst: proactive CG write failed: {graph_err}", exc_info=True)
            try:
                db.session.rollback()
            except Exception:
                pass

        # ── 9. Execute playbook (time-aware) ──
        # After CG commit, create PlaybookExecutionV2 from the recommended playbook.
        # This is Layer A's independent path — separate from Layer B (health+arc trigger).
        if playbook_id:
            try:
                pb_result = _execute_playbook_from_signal(
                    customer_id=customer_id,
                    account_id=account_id,
                    playbook_id=playbook_id,
                    signal_type=signal_type,
                    signal_date=signal_occurred_at,
                )
                if pb_result:
                    payload['playbook_execution'] = pb_result
            except Exception as pb_err:
                logger.warning(f"signal_analyst: playbook execution failed (non-fatal): {pb_err}")

        return payload

    except Exception as e:
        logger.error(f"signal_analyst: analyze_on_signal failed for account {account_id}: {e}", exc_info=True)
        try:
            from extensions import db as _db
            _db.session.rollback()
        except Exception:
            pass
        return None


def scan_signals_for_proactive_triggers(customer_id: int) -> list:
    """
    Scan recently loaded qualitative signals for high-risk types.
    Called from _process_data_impl() AFTER signals are loaded into DB.

    Returns list of (account_id, signal_type, content) tuples that triggered.
    """
    if not pic.layer_a_enabled():
        return []

    # ── Enforce max proactive calls per run ──
    try:
        from utils.llm_budget_controller import get_max_proactive_calls
        max_proactive = get_max_proactive_calls(customer_id)
    except Exception:
        max_proactive = 50  # fallback default

    triggered = []
    try:
        from models import Account, ContextNode, db
        from datetime import timedelta

        # Get account IDs for this customer
        acct_ids = [a.account_id for a in Account.query.filter_by(customer_id=customer_id).all()]
        if not acct_ids:
            return []

        # Scan TWO sources for high-risk signals:
        # 1. ContextNode SIGNAL nodes (if CG was loaded)
        # 2. QualitativeSignal table (always — covers incremental loads where CG skip is on)
        #
        # Use last process_data run timestamp as cutoff to avoid re-analyzing
        # old signals that were already triggered in a previous run.
        # For FIRST RUN (no WizardRun exists): scan ALL historical signals —
        # they need playbook executions created with time-aware timestamps.
        cutoff = None  # None = scan everything (first run)
        try:
            from models import WizardRun
            last_run = (
                WizardRun.query
                .filter(
                    WizardRun.customer_id == customer_id,
                    WizardRun.config['wizard'].astext == 'process_data',
                )
                .order_by(WizardRun.created_at.desc())
                .first()
            )
            if last_run and last_run.created_at:
                cutoff = last_run.created_at
                logger.info(f"signal_analyst: using last process_data run as cutoff: {cutoff}")
            else:
                logger.info(f"signal_analyst: first run for customer {customer_id} — scanning ALL historical signals")
        except Exception:
            pass  # cutoff stays None = scan everything

        seen = set()  # (account_id, signal_type) to avoid duplicate triggers

        # Pre-populate seen set with signals already analyzed (have proactive_insight nodes).
        # This prevents re-triggering LLM on signals analyzed in previous process_data runs.
        try:
            _existing_insights = (
                ContextNode.query
                .filter(
                    ContextNode.customer_id == customer_id,
                    ContextNode.node_subtype == 'proactive_insight',
                )
                .all()
            )
            for _ei in _existing_insights:
                _ei_props = _ei.properties or {}
                _ei_sig_type = _ei_props.get('signal_type', '')
                if _ei_sig_type and _ei.account_id:
                    seen.add((_ei.account_id, _ei_sig_type))
            if seen:
                logger.info(f"signal_analyst: {len(seen)} already-analyzed signals pre-loaded into dedup set")
        except Exception:
            pass

        # Source 1: ContextNode table
        _cg_query = (
            ContextNode.query
            .filter(
                ContextNode.customer_id == customer_id,
                ContextNode.account_id.in_(acct_ids),
                ContextNode.node_type == 'SIGNAL',
                ContextNode.source == 'customer',
            )
        )
        if cutoff is not None:
            _cg_query = _cg_query.filter(ContextNode.occurred_at >= cutoff)
        recent_cg = _cg_query.all()
        for node in recent_cg:
            if len(triggered) >= max_proactive:
                logger.info(
                    f"signal_analyst: proactive call cap reached ({max_proactive}) "
                    f"for customer {customer_id} — stopping CG scan"
                )
                break
            st = node.node_subtype or ''
            props = node.properties or {}
            for sig_type in [st, props.get('signal_type', ''), props.get('event_type', '')]:
                if sig_type in HIGH_RISK_SIGNAL_TYPES:
                    key = (node.account_id, sig_type)
                    if key not in seen:
                        seen.add(key)
                        content = node.title or props.get('content', sig_type)
                        signal_date = node.occurred_at or datetime.utcnow()
                        signal_age_days = (datetime.utcnow() - signal_date).days if node.occurred_at else 0

                        # Fast path: for historical signals (>14 days old),
                        # skip LLM analysis and directly create time-aware
                        # playbook execution. LLM is for real-time alerts.
                        if signal_age_days > 14:
                            risk_info = HIGH_RISK_SIGNAL_TYPES[sig_type]
                            pb_id = risk_info.get('playbook')
                            if pb_id:
                                pb_result = _execute_playbook_from_signal(
                                    customer_id=customer_id,
                                    account_id=node.account_id,
                                    playbook_id=pb_id,
                                    signal_type=sig_type,
                                    signal_date=signal_date,
                                )
                                if pb_result:
                                    triggered.append((node.account_id, sig_type, content))
                        else:
                            # Recent signal: full LLM analysis path
                            result = analyze_on_signal(
                                customer_id=customer_id,
                                account_id=node.account_id,
                                signal_type=sig_type,
                                signal_content=str(content)[:500],
                                signal_sentiment=props.get('sentiment', 'negative'),
                            )
                            if result:
                                triggered.append((node.account_id, sig_type, content))

        # Source 2: QualitativeSignal table (catches incremental loads where CG skip is on)
        try:
            from models import QualitativeSignal
            _qs_query = QualitativeSignal.query.filter(
                QualitativeSignal.account_id.in_(acct_ids),
            )
            if cutoff is not None:
                cutoff_date = cutoff.date() if hasattr(cutoff, 'date') else cutoff
                _qs_query = _qs_query.filter(QualitativeSignal.signal_date >= cutoff_date)
            recent_qual = _qs_query.all()
            high_risk_qual = [
                qs for qs in recent_qual
                if (qs.signal_type or '') in HIGH_RISK_SIGNAL_TYPES
            ]
            logger.info(
                f"signal_analyst: proactive scan — {len(recent_qual)} recent qualitative signals, "
                f"{len(high_risk_qual)} high-risk matches for customer {customer_id}"
            )
            for qs in high_risk_qual:
                if len(triggered) >= max_proactive:
                    logger.info(
                        f"signal_analyst: proactive call cap reached ({max_proactive}) "
                        f"for customer {customer_id} — stopping QS scan"
                    )
                    break
                sig_type = qs.signal_type or ''
                key = (qs.account_id, sig_type)
                if key not in seen:
                    seen.add(key)
                    content = qs.content or sig_type
                    signal_date = datetime.combine(qs.signal_date, datetime.min.time()) if qs.signal_date else datetime.utcnow()
                    signal_age_days = (datetime.utcnow() - signal_date).days if qs.signal_date else 0

                    # Fast path for historical signals (same as Source 1)
                    if signal_age_days > 14:
                        risk_info = HIGH_RISK_SIGNAL_TYPES[sig_type]
                        pb_id = risk_info.get('playbook')
                        if pb_id:
                            pb_result = _execute_playbook_from_signal(
                                customer_id=customer_id,
                                account_id=qs.account_id,
                                playbook_id=pb_id,
                                signal_type=sig_type,
                                signal_date=signal_date,
                            )
                            if pb_result:
                                triggered.append((qs.account_id, sig_type, content))
                    else:
                        logger.info(
                            f"signal_analyst: PROACTIVE trigger — account {qs.account_id} "
                            f"signal_type={sig_type} content={str(content)[:80]}"
                        )
                        result = analyze_on_signal(
                            customer_id=customer_id,
                            account_id=qs.account_id,
                            signal_type=sig_type,
                            signal_content=str(content)[:500],
                            signal_sentiment=qs.sentiment or 'negative',
                        )
                        if result:
                            triggered.append((qs.account_id, sig_type, content))
        except Exception as qs_err:
            logger.error(f"QualitativeSignal proactive scan failed: {qs_err}", exc_info=True)

        if triggered:
            logger.info(
                f"signal_analyst: {len(triggered)} proactive trigger(s) for customer {customer_id}: "
                + ", ".join(f"{a}:{s}" for a, s, _ in triggered)
            )

    except Exception as e:
        logger.error(f"signal_analyst: scan_signals_for_proactive_triggers failed: {e}", exc_info=True)

    return triggered


def _call_llm(customer_id: int, prompt: str) -> Optional[str]:
    """
    Call an LLM for signal analysis.

    Priority: Anthropic (Claude) → OpenAI (GPT-4o-mini) → None.
    Returns the assistant message text, or None on failure.

    Budget controller integration:
    - Checks can_call() before making the API request.
    - Calls record_usage() after the call completes (success or failure).
    - If budget is exhausted, returns None (no LLM call made).
    """
    # ── Budget gate ──
    try:
        from utils.llm_budget_controller import can_call, record_usage
        if not can_call(customer_id, 'signal_analyst', estimated_tokens=1000):
            logger.warning(
                f"signal_analyst: LLM call BLOCKED by budget controller for customer {customer_id}"
            )
            return None
    except Exception as budget_err:
        # Fail-open: if budget check fails, proceed with the call
        logger.debug(f"signal_analyst: budget check error (proceeding): {budget_err}")
        record_usage = None  # type: ignore[assignment]

    # ── Try Anthropic first ──
    try:
        import os
        anthropic_key = os.environ.get('ANTHROPIC_API_KEY')
        if anthropic_key:
            import anthropic
            client = anthropic.Anthropic(api_key=anthropic_key)
            response = client.messages.create(
                model='claude-sonnet-4-20250514',
                max_tokens=400,
                system=(
                    'You are an expert Customer Success analyst. '
                    'You produce concise, actionable insights from account health data. '
                    'Always respond with bullet points. Keep each bullet under 30 words.'
                ),
                messages=[{'role': 'user', 'content': prompt}],
            )
            text = response.content[0].text.strip() if response.content else None
            if text:
                logger.info(f"signal_analyst: Anthropic call succeeded for customer {customer_id}")
                # Record usage
                try:
                    tokens_in = getattr(response.usage, 'input_tokens', 0) or 0
                    tokens_out = getattr(response.usage, 'output_tokens', 0) or 0
                    from utils.llm_budget_controller import record_usage as _record
                    _record(customer_id, 'signal_analyst', tokens_in, tokens_out,
                            model='claude-sonnet-4-20250514')
                except Exception as rec_err:
                    logger.debug(f"signal_analyst: usage recording failed: {rec_err}")
                return text
    except Exception as e:
        logger.debug(f"signal_analyst: Anthropic call failed, trying OpenAI: {e}")
        # Record failed Anthropic attempt
        try:
            from utils.llm_budget_controller import record_usage as _record
            _record(customer_id, 'signal_analyst', 0, 0,
                    model='claude-sonnet-4-20250514', success=False, error_message=str(e)[:200])
        except Exception:
            pass

    # ── Fallback to OpenAI ──
    try:
        from openai_key_utils import get_openai_api_key
        import openai

        api_key = get_openai_api_key(customer_id)
        if not api_key:
            logger.warning(
                f"signal_analyst: no LLM API key for customer {customer_id} — skipping"
            )
            return None

        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model='gpt-4o-mini',
            messages=[
                {
                    'role': 'system',
                    'content': (
                        'You are an expert Customer Success analyst. '
                        'You produce concise, actionable insights from account health data. '
                        'Always respond with bullet points. Keep each bullet under 30 words.'
                    ),
                },
                {'role': 'user', 'content': prompt},
            ],
            max_tokens=400,
            temperature=0.3,
        )
        result_text = response.choices[0].message.content.strip()
        # Record usage
        try:
            usage = response.usage
            tokens_in = getattr(usage, 'prompt_tokens', 0) or 0
            tokens_out = getattr(usage, 'completion_tokens', 0) or 0
            from utils.llm_budget_controller import record_usage as _record
            _record(customer_id, 'signal_analyst', tokens_in, tokens_out, model='gpt-4o-mini')
        except Exception as rec_err:
            logger.debug(f"signal_analyst: usage recording failed: {rec_err}")
        return result_text

    except Exception as e:
        logger.error(f"signal_analyst: LLM call failed: {e}", exc_info=True)
        # Record failed OpenAI attempt
        try:
            from utils.llm_budget_controller import record_usage as _record
            _record(customer_id, 'signal_analyst', 0, 0,
                    model='gpt-4o-mini', success=False, error_message=str(e)[:200])
        except Exception:
            pass
        return None


# Keep old name as alias for backward compatibility
_call_openai = _call_llm


# ─────────────────────────────────────────────────────────────────────
#  Time-aware playbook execution from signal detection
# ─────────────────────────────────────────────────────────────────────

# Playbook duration in days (how long an intervention typically takes)
_PLAYBOOK_DURATION_DAYS = {
    'PB-DC-01': 21, 'PB-DC-02': 14, 'PB-DC-03': 30, 'PB-DC-04': 21,
    'PB-01': 21, 'PB-02': 14, 'PB-03': 21, 'PB-04': 14,
    'PB-05': 21, 'PB-06': 30, 'PB-07': 21, 'PB-08': 30,
}


def _get_health_at_date(account_id: int, target_date) -> Optional[float]:
    """Get the health score closest to (but not after) a target date.

    Returns the health_score float, or None if no score exists before that date.
    """
    try:
        from models import HealthScore
        target = target_date.date() if hasattr(target_date, 'date') else target_date
        hs = (
            HealthScore.query
            .filter(
                HealthScore.account_id == account_id,
                HealthScore.measurement_month <= target,
            )
            .order_by(HealthScore.measurement_month.desc())
            .first()
        )
        if hs and hs.health_score is not None:
            return float(hs.health_score)
        # Fallback: get ANY health score for this account (earliest available)
        hs_any = (
            HealthScore.query
            .filter_by(account_id=account_id)
            .order_by(HealthScore.measurement_month.asc())
            .first()
        )
        return float(hs_any.health_score) if hs_any and hs_any.health_score else None
    except Exception as e:
        logger.debug(f"_get_health_at_date failed for account {account_id}: {e}")
        return None


def _execute_playbook_from_signal(
    customer_id: int,
    account_id: int,
    playbook_id: str,
    signal_type: str,
    signal_date: datetime,
) -> Optional[dict]:
    """Create a time-aware PlaybookExecutionV2 from a detected signal.

    If the signal is old enough (>14 days), auto-closes the execution
    with health-at-close looked up from the appropriate date.

    Dedup: skips if a PlaybookExecutionV2 already exists for the same
    account+playbook within 7 days of the signal date.

    Returns dict with execution details, or None if skipped/failed.
    """
    try:
        from models import PlaybookExecutionV2, db
        from utils.playbook_lifecycle import start_execution, close_execution

        # ── Dedup: check for existing execution near signal date ──
        dedup_start = signal_date - timedelta(days=7)
        dedup_end = signal_date + timedelta(days=7)
        existing = (
            PlaybookExecutionV2.query
            .filter(
                PlaybookExecutionV2.customer_id == customer_id,
                PlaybookExecutionV2.account_id == account_id,
                PlaybookExecutionV2.playbook_id == playbook_id,
                PlaybookExecutionV2.triggered_at >= dedup_start,
                PlaybookExecutionV2.triggered_at <= dedup_end,
            )
            .first()
        )
        if existing:
            logger.debug(
                f"signal_analyst: playbook {playbook_id} already exists for "
                f"account {account_id} near {signal_date.date()} — skipping"
            )
            return None

        # ── Get health at signal time ──
        health_at_trigger = _get_health_at_date(account_id, signal_date)

        # ── Create execution with signal's timestamp ──
        try:
            execution = start_execution(
                customer_id=customer_id,
                account_id=account_id,
                playbook_id=playbook_id,
                triggered_by='signal_analyst',
                triggered_at=signal_date,
                health_at_trigger=health_at_trigger,
            )
        except ValueError as e:
            logger.debug(f"signal_analyst: start_execution failed: {e}")
            return None

        logger.info(
            f"signal_analyst: ✅ PlaybookExecution created for account {account_id} "
            f"— {playbook_id} triggered by {signal_type} at {signal_date.date()} "
            f"(health={health_at_trigger})"
        )

        result = {
            'execution_id': execution.execution_id,
            'playbook_id': playbook_id,
            'account_id': account_id,
            'triggered_at': signal_date.isoformat(),
            'health_at_trigger': health_at_trigger,
            'signal_type': signal_type,
        }

        # ── Auto-close if signal is old enough ──
        days_elapsed = (datetime.utcnow() - signal_date).days
        playbook_duration = _PLAYBOOK_DURATION_DAYS.get(playbook_id, 21)

        if days_elapsed > playbook_duration:
            closed_at = signal_date + timedelta(days=playbook_duration)
            health_at_close = _get_health_at_date(account_id, closed_at)

            # Determine outcome from health trajectory
            if health_at_trigger is not None and health_at_close is not None:
                if health_at_close > health_at_trigger + 5:
                    outcome = 'resolved'
                elif health_at_close < health_at_trigger - 10:
                    outcome = 'timeout'
                else:
                    outcome = 'resolved'  # stabilized = success
            else:
                outcome = 'resolved'

            try:
                close_execution(
                    customer_id=customer_id,
                    execution_id=execution.execution_id,
                    outcome=outcome,
                    outcome_notes=(
                        f'Auto-closed: {playbook_id} triggered by {signal_type} '
                        f'at {signal_date.date()}, closed after {playbook_duration}d'
                    ),
                    health_at_close=health_at_close,
                    closed_at=closed_at,
                )
                result['outcome'] = outcome
                result['closed_at'] = closed_at.isoformat()
                result['health_at_close'] = health_at_close
                logger.info(
                    f"signal_analyst: ✅ Auto-closed {execution.execution_id} as {outcome} "
                    f"(health {health_at_trigger}→{health_at_close}, closed={closed_at.date()})"
                )
            except Exception as close_err:
                logger.warning(f"signal_analyst: auto-close failed for {execution.execution_id}: {close_err}")
                result['auto_close_error'] = str(close_err)

        return result

    except Exception as e:
        logger.error(f"signal_analyst: _execute_playbook_from_signal failed: {e}", exc_info=True)
        try:
            from extensions import db as _db
            _db.session.rollback()
        except Exception:
            pass
        return None
