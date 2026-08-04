"""
Account-Specific Action Plan Generator (P3.1)

Orchestrates existing MCP tools to gather account context, then uses
Claude Sonnet to produce a specific, time-bound action plan with
named stakeholders, talking points, and ROI projections.

Gated behind WITH_LLM feature flag.

Usage:
    from llm.action_plan_generator import generate_action_plan
    plan = generate_action_plan(customer_id=123, account_id=456)
"""

import json
import logging
import time
from datetime import datetime, date
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Model: Sonnet for reasoning quality (action plans need judgment, not just structure)
LLM_MODEL = 'claude-sonnet-4-6'
MAX_TOKENS = 4096


def _check_prerequisites(customer_id: int) -> tuple:
    """Check WITH_LLM flag + API key. Returns (ok, reason)."""
    try:
        from models import FeatureToggle as FTModel
        toggle = FTModel.query.filter_by(
            customer_id=customer_id, feature_name='with_llm',
        ).first()
        if not (toggle and toggle.enabled):
            from feature_toggles import feature_toggles, FeatureToggle
            if not feature_toggles.is_enabled(FeatureToggle.WITH_LLM):
                return False, 'WITH_LLM disabled'
    except Exception:
        return False, 'Feature toggle check failed'

    try:
        from anthropic_key_utils import has_anthropic_api_key
        if not has_anthropic_api_key(customer_id):
            return False, 'No API key'
    except Exception:
        import os
        if not os.environ.get('ANTHROPIC_API_KEY'):
            return False, 'No ANTHROPIC_API_KEY'

    return True, 'OK'


def _gather_context(customer_id: int, account_id: int) -> Dict:
    """Gather all account context using existing MCP tool implementations.

    Calls the same functions that MCP tools use, directly in-process.
    Returns a dict with all context sections.
    """
    from models import Account, HealthScore
    from extensions import db
    import utils.health_thresholds as ht

    context = {
        'account_name': '', 'arr': 0, 'health_score': 0,
        'health_status': 'unknown', 'industry': '', 'renewal_date': '',
        'days_to_renewal': None, 'pillar_breakdown': '',
        'timeline_summary': '', 'stakeholder_summary': '',
        'revenue_summary': '', 'playbook_summary': '',
    }

    # Account basics
    acct = db.session.get(Account, int(account_id))
    if not acct:
        return context
    context['account_name'] = acct.account_name
    context['arr'] = float(acct.revenue or 0)
    context['industry'] = acct.industry or 'Unknown'

    # Renewal date from profile_metadata
    meta = acct.profile_metadata or {}
    renewal = meta.get('renewal_date', meta.get('contract_end', ''))
    context['renewal_date'] = str(renewal) if renewal else 'Unknown'
    if renewal:
        try:
            rd = datetime.strptime(str(renewal)[:10], '%Y-%m-%d').date()
            context['days_to_renewal'] = (rd - date.today()).days
        except (ValueError, TypeError):
            pass

    # Health score + pillars
    latest_score = (
        HealthScore.query
        .filter_by(account_id=account_id)
        .order_by(HealthScore.measurement_month.desc())
        .first()
    )
    if latest_score:
        h = float(latest_score.health_score)
        context['health_score'] = round(h, 1)
        context['health_status'] = ht.classify(h)
        if latest_score.contributing_pillars:
            pillars = latest_score.contributing_pillars
            if isinstance(pillars, str):
                pillars = json.loads(pillars)
            context['pillar_breakdown'] = '\n'.join(
                f'  {k}: {v}/100' for k, v in sorted(pillars.items())
            )

    # Timeline (signals, decisions, outcomes)
    try:
        from utils.context_graph import get_nodes
        nodes = get_nodes(customer_id, account_id, limit=30)
        timeline_lines = []
        for n in sorted(nodes, key=lambda x: x.occurred_at or datetime.min):
            prefix = {'SIGNAL': 'SIG', 'DECISION': 'DEC', 'OUTCOME': 'OUT',
                      'STAKEHOLDER': 'STK'}.get(n.node_type, '???')
            rev = f' (${n.revenue_impact:,.0f})' if n.revenue_impact else ''
            date_str = n.occurred_at.strftime('%Y-%m-%d') if n.occurred_at else '?'
            timeline_lines.append(f'  [{prefix}] {date_str}: {n.title}{rev}')
        context['timeline_summary'] = '\n'.join(timeline_lines[-20:]) or '  (no events recorded)'
    except Exception as e:
        context['timeline_summary'] = f'  (timeline unavailable: {e})'

    # Stakeholders
    try:
        from models import ContextNode
        stakeholders = ContextNode.query.filter_by(
            customer_id=customer_id, account_id=account_id,
            node_type='STAKEHOLDER',
        ).all()
        stk_lines = []
        for s in stakeholders:
            props = s.properties or {}
            name = s.title or 'Unknown'
            role = s.node_subtype or props.get('role', '?')
            title = props.get('job_title', '')
            engagement = props.get('engagement_frequency', '?')
            sentiment = props.get('sentiment', '?')
            stk_lines.append(
                f'  {name} — {role} ({title}), engagement={engagement}, sentiment={sentiment}'
            )
        context['stakeholder_summary'] = '\n'.join(stk_lines) or '  (no stakeholders mapped)'
    except Exception as e:
        context['stakeholder_summary'] = f'  (stakeholders unavailable: {e})'

    # Revenue at risk
    try:
        from utils.context_graph import get_revenue_at_risk
        rev = get_revenue_at_risk(customer_id, account_id)
        context['revenue_summary'] = (
            f'  At risk: ${rev.get("at_risk", 0):,.0f}\n'
            f'  Protected: ${rev.get("protected", 0):,.0f}\n'
            f'  Expansion: ${rev.get("expansion", 0):,.0f}\n'
            f'  Lost: ${rev.get("lost", 0):,.0f}'
        )
    except Exception:
        context['revenue_summary'] = '  (revenue data unavailable)'

    # Playbook recommendations
    try:
        from models import ContextNode as CN
        # Get arc type for playbook mapping
        arc_type = acct.arc_type or ''
        arc_map = {}
        try:
            import json as _json
            from pathlib import Path
            map_path = Path(__file__).parent.parent / 'config' / 'arc_playbook_map.json'
            if map_path.exists():
                with open(map_path) as f:
                    raw = _json.load(f)
                arc_map = {k: v for k, v in raw.items() if not k.startswith('_')}
        except Exception:
            pass

        playbooks = arc_map.get(arc_type, [])
        if playbooks:
            pb_lines = [f'  Arc type: {arc_type}']
            for pb_id in playbooks:
                pb_lines.append(f'  Recommended: {pb_id}')
            context['playbook_summary'] = '\n'.join(pb_lines)
        else:
            context['playbook_summary'] = f'  Arc type: {arc_type or "unclassified"}\n  No specific playbook mapped'
    except Exception:
        context['playbook_summary'] = '  (playbook data unavailable)'

    return context


def generate_action_plan(
    customer_id: int,
    account_id: int,
    horizon_days: int = 90,
) -> Dict:
    """Generate an account-specific action plan using Claude.

    Returns structured plan dict or error dict.
    """
    t0 = time.time()

    # Prerequisites
    ok, reason = _check_prerequisites(customer_id)
    if not ok:
        return {'status': 'skipped', 'reason': reason, 'duration_s': round(time.time() - t0, 2)}

    # Gather all context
    context = _gather_context(customer_id, account_id)
    if not context.get('account_name'):
        return {'status': 'error', 'reason': f'Account {account_id} not found', 'duration_s': round(time.time() - t0, 2)}

    # Build prompt
    from llm.prompts.action_plan import SYSTEM_PROMPT, CONTEXT_TEMPLATE, OUTPUT_SCHEMA

    user_prompt = CONTEXT_TEMPLATE.format(
        today=date.today().strftime('%Y-%m-%d'),
        account_name=context['account_name'],
        arr=context['arr'],
        health_score=context['health_score'],
        health_status=context['health_status'],
        industry=context['industry'],
        renewal_date=context['renewal_date'],
        days_to_renewal=context.get('days_to_renewal', 'Unknown'),
        pillar_breakdown=context['pillar_breakdown'],
        timeline_summary=context['timeline_summary'],
        stakeholder_summary=context['stakeholder_summary'],
        revenue_summary=context['revenue_summary'],
        playbook_summary=context['playbook_summary'],
        horizon_days=horizon_days,
    ) + '\n\n' + OUTPUT_SCHEMA

    # Get API key
    try:
        from anthropic_key_utils import get_anthropic_api_key
        api_key = get_anthropic_api_key(customer_id)
    except Exception:
        import os
        api_key = os.environ.get('ANTHROPIC_API_KEY')

    if not api_key:
        return {'status': 'error', 'reason': 'No API key', 'duration_s': round(time.time() - t0, 2)}

    # Call Claude
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        response = client.messages.create(
            model=LLM_MODEL,
            system=SYSTEM_PROMPT,
            messages=[{'role': 'user', 'content': user_prompt}],
            max_tokens=MAX_TOKENS,
            temperature=0.3,
        )

        # Cost tracking — canonical path via llm_budget_controller.
        try:
            from utils.llm_budget_controller import record_usage as _record_usage
            _record_usage(
                customer_id=customer_id,
                module='action_plan_generator',
                tokens_in=response.usage.input_tokens,
                tokens_out=response.usage.output_tokens,
                model=LLM_MODEL,
                success=True,
            )
        except Exception as _cost_err:
            logger.debug('action_plan: cost tracking failed: %s', _cost_err)

        text = response.content[0].text if response.content else ''
        # Strip markdown fences
        if text.strip().startswith('```'):
            text = text.strip().split('\n', 1)[1]
            if text.strip().endswith('```'):
                text = text.strip()[:-3]

        plan = json.loads(text)

        # Enrich with metadata
        plan['account_id'] = account_id
        plan['account_name'] = context['account_name']
        plan['arr'] = context['arr']
        plan['health_score'] = context['health_score']
        plan['plan_generated_at'] = datetime.utcnow().isoformat() + 'Z'
        plan['planning_horizon_days'] = horizon_days
        plan['model'] = LLM_MODEL
        plan['status'] = 'completed'
        plan['duration_s'] = round(time.time() - t0, 2)
        plan['tokens'] = {
            'input': response.usage.input_tokens,
            'output': response.usage.output_tokens,
        }

        logger.info(
            'Action plan generated: customer=%d account=%d (%s) '
            '%d actions, %.1fs, %d+%d tokens',
            customer_id, account_id, context['account_name'],
            len(plan.get('actions', [])), plan['duration_s'],
            response.usage.input_tokens, response.usage.output_tokens,
        )

        # Store plan as ContextNode for audit trail
        try:
            from utils.context_graph import upsert_node
            upsert_node(
                customer_id=customer_id,
                account_id=account_id,
                node_type='DECISION',
                title=f'AI Action Plan — {context["account_name"]}',
                occurred_at=datetime.utcnow(),
                properties={
                    'plan': plan,
                    'generated_by': 'llm_action_plan',
                    'actions_count': len(plan.get('actions', [])),
                },
                source_platform='llm_inference',
                source_event_id=f'action_plan:{account_id}:{date.today().isoformat()}',
                node_subtype='action_plan',
                tier=1,
                confidence=plan.get('confidence', 0.8),
            )
            from extensions import db
            db.session.commit()
        except Exception as e:
            logger.debug('Action plan storage failed (non-fatal): %s', e)

        return plan

    except json.JSONDecodeError as e:
        logger.warning('Action plan JSON parse error: %s', e)
        return {'status': 'error', 'reason': f'JSON parse error: {e}', 'duration_s': round(time.time() - t0, 2)}
    except Exception as e:
        logger.warning('Action plan generation failed: %s', e)
        # Record failure — tokens unknown on API errors.
        try:
            from utils.llm_budget_controller import record_usage as _record_usage
            _record_usage(
                customer_id=customer_id,
                module='action_plan_generator',
                tokens_in=0, tokens_out=0,
                model=LLM_MODEL,
                success=False,
                error_message=str(e)[:500],
            )
        except Exception:
            pass
        return {'status': 'error', 'reason': str(e), 'duration_s': round(time.time() - t0, 2)}
