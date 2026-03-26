#!/usr/bin/env python3
"""
Layer A — Proactive LLM Signal Analyst
=======================================

Called from _process_data_impl() when account health drops >10 pts OR a
severity=critical signal lands.

Flow:
    1. check_and_analyze() checks the drop threshold.
    2. If triggered, collect last-N SIGNAL ContextNodes + pillar deltas.
    3. Build a concise prompt and call OpenAI (same key pattern as RAG).
    4. Store result as Notification(type='signal_insight').
    5. Write system ContextNode (source='system') and edge to most recent customer signal.
    6. Return payload dict — or None if analysis was not triggered.

Errors are caught at every layer; this function must NEVER crash process_data.
"""

import logging
from datetime import datetime
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

        # ── 1. Collect last-N SIGNAL ContextNodes for this account ──
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
            import json as _json
            current_pillars = _json.loads(last_two_scores[0].contributing_pillars or '{}') if last_two_scores[0].contributing_pillars else {}
            previous_pillars = _json.loads(last_two_scores[1].contributing_pillars or '{}') if last_two_scores[1].contributing_pillars else {}
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
        analysis_text = _call_openai(customer_id, prompt)
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
                source='system',          # distinguishes from customer CSV signals
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
                occurred_at=datetime.utcnow(),
            )
            db.session.add(insight_node)
            db.session.flush()

            # Connect to most recent customer signal (RELATES_TO — non-causal)
            recent = (ContextNode.query
                      .filter_by(account_id=account_id, node_type='SIGNAL', source='customer')
                      .order_by(ContextNode.occurred_at.desc())
                      .first())
            if recent:
                db.session.add(ContextEdge(
                    from_node_id=recent.node_id,
                    to_node_id=insight_node.node_id,
                    edge_type='RELATES_TO',
                    confidence=1.0,
                    properties={'label': 'AI observation of health drop'},
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


def _call_openai(customer_id: int, prompt: str) -> Optional[str]:
    """
    Call OpenAI chat completions using the customer-specific API key.

    Follows the same key-retrieval pattern as enhanced_rag_openai.py.
    Returns the assistant message text, or None on failure.
    """
    try:
        from openai_key_utils import get_openai_api_key
        import openai

        api_key = get_openai_api_key(customer_id)
        if not api_key:
            logger.warning(
                f"signal_analyst: no OpenAI API key for customer {customer_id} — skipping LLM call"
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

        return response.choices[0].message.content.strip()

    except Exception as e:
        logger.error(f"signal_analyst: OpenAI call failed: {e}", exc_info=True)
        return None
