"""
Shared context gathering helpers for LLM reasoning modules.

Used by causal_reasoning.py, anomaly_explainer.py, and action_plan_generator.py
to build rich account context from the DB without duplicating queries.
"""

import json
import logging
from datetime import datetime, date
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def check_llm_prerequisites(customer_id: int) -> tuple:
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


def get_api_key(customer_id: int) -> Optional[str]:
    """Get Anthropic API key for a customer."""
    try:
        from anthropic_key_utils import get_anthropic_api_key
        return get_anthropic_api_key(customer_id)
    except Exception:
        import os
        return os.environ.get('ANTHROPIC_API_KEY')


def get_account_context(customer_id: int, account_id: int) -> Dict:
    """Gather comprehensive account context from DB.

    Returns dict with: account basics, health, pillars, timeline,
    stakeholders, revenue, arc_type, renewal info.
    """
    from models import Account, HealthScore, ContextNode
    from extensions import db
    import utils.health_thresholds as ht

    ctx = {
        'account_name': '', 'arr': 0, 'health_score': 0,
        'health_status': 'unknown', 'industry': '', 'arc_type': '',
        'renewal_date': '', 'days_to_renewal': None,
        'pillar_scores': {}, 'health_history': [],
        'signals': [], 'decisions': [], 'outcomes': [], 'stakeholders': [],
        'revenue': {'at_risk': 0, 'protected': 0, 'expansion': 0, 'lost': 0},
    }

    acct = db.session.get(Account, int(account_id))
    if not acct:
        return ctx

    ctx['account_name'] = acct.account_name
    ctx['arr'] = float(acct.revenue or 0)
    ctx['industry'] = acct.industry or 'Unknown'
    ctx['arc_type'] = acct.arc_type or ''

    # Renewal
    meta = acct.profile_metadata or {}
    renewal = meta.get('renewal_date', meta.get('contract_end', ''))
    ctx['renewal_date'] = str(renewal) if renewal else ''
    if renewal:
        try:
            rd = datetime.strptime(str(renewal)[:10], '%Y-%m-%d').date()
            ctx['days_to_renewal'] = (rd - date.today()).days
        except (ValueError, TypeError):
            pass

    # Health history
    scores = (
        HealthScore.query
        .filter_by(account_id=account_id)
        .order_by(HealthScore.measurement_month.asc())
        .all()
    )
    if scores:
        ctx['health_score'] = round(float(scores[-1].health_score), 1)
        ctx['health_status'] = ht.classify(float(scores[-1].health_score))
        ctx['health_history'] = [
            {'month': str(s.measurement_month), 'score': round(float(s.health_score), 1)}
            for s in scores
        ]
        if scores[-1].contributing_pillars:
            pillars = scores[-1].contributing_pillars
            if isinstance(pillars, str):
                pillars = json.loads(pillars)
            ctx['pillar_scores'] = {k: round(float(v), 1) for k, v in pillars.items()}

    # Context graph nodes by type
    nodes = ContextNode.query.filter_by(
        customer_id=customer_id, account_id=account_id,
    ).order_by(ContextNode.occurred_at.asc()).all()

    for n in nodes:
        entry = {
            'node_id': n.node_id,
            'type': n.node_type,
            'subtype': n.node_subtype or '',
            'title': n.title or '',
            'date': n.occurred_at.strftime('%Y-%m-%d') if n.occurred_at else '',
            'revenue_impact': float(n.revenue_impact) if n.revenue_impact else None,
            'confidence': float(n.confidence) if n.confidence else 1.0,
            'properties': n.properties or {},
        }
        if n.node_type == 'SIGNAL':
            ctx['signals'].append(entry)
        elif n.node_type == 'DECISION':
            ctx['decisions'].append(entry)
        elif n.node_type == 'OUTCOME':
            ctx['outcomes'].append(entry)
        elif n.node_type == 'STAKEHOLDER':
            ctx['stakeholders'].append(entry)

    # Revenue from authoritative source
    try:
        from utils.context_graph import get_revenue_at_risk
        rev = get_revenue_at_risk(customer_id, account_id)
        ctx['revenue'] = {
            'at_risk': rev.get('at_risk', 0),
            'protected': rev.get('protected', 0),
            'expansion': rev.get('expansion', 0),
            'lost': rev.get('lost', 0),
        }
    except Exception:
        pass

    return ctx


def format_timeline(ctx: Dict, limit: int = 20) -> str:
    """Format context graph events as a readable timeline."""
    events = []
    for sig in ctx['signals']:
        events.append((sig['date'], 'SIG', sig['subtype'], sig['title']))
    for dec in ctx['decisions']:
        events.append((dec['date'], 'DEC', dec['subtype'], dec['title']))
    for out in ctx['outcomes']:
        rev = f" (${out['revenue_impact']:,.0f})" if out.get('revenue_impact') else ''
        events.append((out['date'], 'OUT', out['subtype'], f"{out['title']}{rev}"))

    events.sort(key=lambda x: x[0])
    lines = [f"  [{e[1]}] {e[0]}: {e[2]} — {e[3][:80]}" for e in events[-limit:]]
    return '\n'.join(lines) or '  (no events recorded)'


def format_stakeholders(ctx: Dict) -> str:
    """Format stakeholders as readable list."""
    lines = []
    for s in ctx['stakeholders']:
        props = s.get('properties', {})
        name = s['title']
        role = s['subtype']
        title = props.get('job_title', '')
        engagement = props.get('engagement_frequency', '?')
        sentiment = props.get('sentiment', '?')
        lines.append(f"  {name} — {role} ({title}), engagement={engagement}, sentiment={sentiment}")
    return '\n'.join(lines) or '  (no stakeholders mapped)'


def format_health_trajectory(ctx: Dict) -> str:
    """Format health score history as arrow trajectory."""
    if not ctx['health_history']:
        return 'No history'
    return ' → '.join(str(h['score']) for h in ctx['health_history'])


def call_claude(system_prompt: str, user_prompt: str, customer_id: int,
                model: str = 'claude-sonnet-4-20250514', max_tokens: int = 2048,
                temperature: float = 0.3) -> tuple:
    """Call Claude API. Returns (parsed_json, usage_dict, duration_s) or (None, {}, duration)."""
    import time
    api_key = get_api_key(customer_id)
    if not api_key:
        return None, {}, 0

    import anthropic
    client = anthropic.Anthropic(api_key=api_key)

    t0 = time.time()
    try:
        response = client.messages.create(
            model=model,
            system=system_prompt,
            messages=[{'role': 'user', 'content': user_prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        duration = round(time.time() - t0, 2)

        text = response.content[0].text if response.content else ''
        if text.strip().startswith('```'):
            text = text.strip().split('\n', 1)[1]
            if text.strip().endswith('```'):
                text = text.strip()[:-3]

        result = json.loads(text)
        usage = {'input': response.usage.input_tokens, 'output': response.usage.output_tokens}
        return result, usage, duration

    except json.JSONDecodeError as e:
        logger.warning('Claude JSON parse error: %s', e)
        return None, {}, round(time.time() - t0, 2)
    except Exception as e:
        logger.warning('Claude API error: %s', e)
        return None, {}, round(time.time() - t0, 2)
