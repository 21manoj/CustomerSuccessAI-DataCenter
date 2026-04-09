"""
Causal Reasoning Engine (P2.1) — Root cause analysis from context graph.

Traverses Signal → Decision → Outcome chains to answer "WHY" —
correct root cause identification, not just symptom listing.

Gated behind WITH_LLM feature flag.

Usage:
    from llm.causal_reasoning import analyze_root_cause
    result = analyze_root_cause(customer_id=123, account_id=456)
"""

import logging
import time
from datetime import datetime
from typing import Dict

logger = logging.getLogger(__name__)


def analyze_root_cause(customer_id: int, account_id: int) -> Dict:
    """Analyze root cause of an account's current trajectory.

    Returns:
        {
            status, root_cause, causal_chain[], contributing_factors[],
            stakeholder_dynamics, what_worked, what_failed, prediction,
            confidence, duration_s, tokens
        }
    """
    t0 = time.time()

    from llm.context_helpers import (
        check_llm_prerequisites, get_account_context,
        format_timeline, format_stakeholders, format_health_trajectory,
        call_claude,
    )

    ok, reason = check_llm_prerequisites(customer_id)
    if not ok:
        return {'status': 'skipped', 'reason': reason, 'duration_s': round(time.time() - t0, 2)}

    ctx = get_account_context(customer_id, account_id)
    if not ctx['account_name']:
        return {'status': 'error', 'reason': f'Account {account_id} not found', 'duration_s': round(time.time() - t0, 2)}

    from llm.prompts.causal_reasoning import SYSTEM_PROMPT, USER_TEMPLATE

    user_prompt = USER_TEMPLATE.format(
        account_name=ctx['account_name'],
        arr=ctx['arr'],
        health_score=ctx['health_score'],
        health_status=ctx['health_status'],
        arc_type=ctx['arc_type'] or 'unclassified',
        health_trajectory=format_health_trajectory(ctx),
        timeline=format_timeline(ctx, limit=25),
        stakeholders=format_stakeholders(ctx),
        at_risk=ctx['revenue']['at_risk'],
        protected=ctx['revenue']['protected'],
        lost=ctx['revenue']['lost'],
        expansion=ctx['revenue']['expansion'],
    )

    result, usage, duration = call_claude(SYSTEM_PROMPT, user_prompt, customer_id)

    if not result:
        return {
            'status': 'error',
            'reason': 'Claude returned no result',
            'duration_s': round(time.time() - t0, 2),
        }

    # Enrich with metadata
    result['account_id'] = account_id
    result['account_name'] = ctx['account_name']
    result['health_score'] = ctx['health_score']
    result['arr'] = ctx['arr']
    result['status'] = 'completed'
    result['duration_s'] = round(time.time() - t0, 2)
    result['tokens'] = usage
    result['model'] = 'claude-sonnet-4-20250514'

    logger.info(
        'Root cause analysis: customer=%d account=%d (%s) '
        'chain=%d events, confidence=%.2f, %.1fs',
        customer_id, account_id, ctx['account_name'],
        len(result.get('causal_chain', [])),
        result.get('confidence', 0),
        result['duration_s'],
    )

    return result
