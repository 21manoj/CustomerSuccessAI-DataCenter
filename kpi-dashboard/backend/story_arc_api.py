#!/usr/bin/env python3
"""
Story Arc REST API
==================
Read-only endpoints for listing and retrieving story arc manifests,
plus a dynamic endpoint that builds an account-specific story arc
from real context graph data.

Endpoints:
  GET  /api/story-arcs                        — List all story arc summaries
  GET  /api/story-arcs/<arc_id>               — Get full manifest for a single arc
  GET  /api/story-arcs/account/<account_id>   — Dynamic arc from live account data

Feature flag: 'context_graph' (global + per-customer DB toggle)
Sub-toggle:   'story_arcs'
"""

import logging
from collections import defaultdict
from datetime import datetime

from flask import Blueprint, jsonify

from auth_middleware import get_current_customer_id
from feature_toggles import is_context_graph_sub_enabled
from models import ContextNode
from utils.story_arc_loader import load_arc, load_all_arcs, get_arc_summary

logger = logging.getLogger(__name__)

story_arc_api = Blueprint('story_arc_api', __name__)

# ─── Module-level cache ──────────────────────────────────────────────────────
# Story arc manifests are static JSON files that don't change at runtime.
# Cache them after the first load to avoid repeated filesystem reads.
_arc_cache = None


def _get_all_arcs():
    """Return all arcs, loading and caching on first call."""
    global _arc_cache
    if _arc_cache is None:
        _arc_cache = load_all_arcs()
        logger.info("Loaded and cached %d story arc manifests", len(_arc_cache))
    return _arc_cache


# ─── Guard ────────────────────────────────────────────────────────────────────

def _guard_story_arcs(customer_id):
    """
    Auth + feature-toggle guard for story arc endpoints.

    Returns:
        (None, None) on success — caller proceeds.
        (response, status_code) on failure — caller returns immediately.
    """
    if not customer_id:
        return jsonify({'error': 'Authentication required'}), 400

    if not is_context_graph_sub_enabled(customer_id, 'story_arcs'):
        return jsonify({
            'error': 'Story arcs not enabled for this customer'
        }), 403

    return None, None


# ─── 1. List all arcs ────────────────────────────────────────────────────────

@story_arc_api.route('/api/story-arcs', methods=['GET'])
def list_story_arcs():
    """
    List all story arc summaries.

    Returns:
        {
            "status": "ok",
            "count": N,
            "arcs": [ { arc_id, arc_name, target_audience, ... }, ... ]
        }
    """
    customer_id = get_current_customer_id()
    err, status = _guard_story_arcs(customer_id)
    if err is not None:
        return err, status

    arcs = _get_all_arcs()
    summaries = [get_arc_summary(arc) for arc in arcs.values()]

    return jsonify({
        'status': 'ok',
        'count': len(summaries),
        'arcs': summaries,
    })


# ─── 2. Get single arc ───────────────────────────────────────────────────────

@story_arc_api.route('/api/story-arcs/<arc_id>', methods=['GET'])
def get_story_arc(arc_id):
    """
    Get the full manifest for a single story arc.

    Args:
        arc_id: e.g. 'arc_expansion_champion'

    Returns:
        { "status": "ok", "arc": { ...full manifest } }
    """
    customer_id = get_current_customer_id()
    err, status = _guard_story_arcs(customer_id)
    if err is not None:
        return err, status

    # Try the module-level cache first, fall back to direct load
    arcs = _get_all_arcs()
    arc = arcs.get(arc_id)
    if arc is None:
        # Attempt direct file load (in case arc_id includes .json or wasn't in cache)
        arc = load_arc(arc_id)

    if arc is None:
        return jsonify({
            'status': 'error',
            'error': f'Story arc not found: {arc_id}',
        }), 404

    return jsonify({
        'status': 'ok',
        'arc': arc,
    })


# ─── 3. Dynamic account story arc ──────────────────────────────────────────

def _week_number(dt, origin):
    """Return the week offset from origin date."""
    if dt is None or origin is None:
        return 0
    delta = (dt - origin).days
    return max(0, delta // 7)


def _phase_name_from_signals(signals):
    """Derive a descriptive phase name from dominant signal subtypes."""
    subtypes = defaultdict(int)
    for s in signals:
        st = s.node_subtype or 'general'
        subtypes[st] += 1
    if not subtypes:
        return 'Activity'

    dominant = max(subtypes, key=subtypes.get)
    name_map = {
        'engagement': 'Stakeholder Engagement',
        'milestone': 'Milestone Achievement',
        'kpi_change': 'KPI Movement',
        'incident': 'Incident Response',
        'escalation': 'Escalation Period',
        'meeting': 'Executive Alignment',
        'ticket': 'Support Activity',
        'nps': 'Customer Feedback',
        'general': 'Activity',
    }
    return name_map.get(dominant, dominant.replace('_', ' ').title())


def _sentiment_to_health(signals):
    """Derive a health range from signal sentiment scores."""
    scores = []
    for s in signals:
        props = s.properties or {}
        sent = props.get('sentiment_score')
        if sent is not None:
            try:
                scores.append(float(sent))
            except (ValueError, TypeError):
                pass
        shift = props.get('sentiment_shift')
        if shift is not None and sent is None:
            try:
                scores.append(float(shift))
            except (ValueError, TypeError):
                pass

    if not scores:
        return {'start': 60, 'end': 65}

    avg = sum(scores) / len(scores)
    # Map sentiment (-1..1) to health (20..90)
    base = int(55 + avg * 30)
    base = max(20, min(90, base))
    # Slight progression within phase
    first_half = scores[:len(scores)//2] if len(scores) > 1 else scores
    second_half = scores[len(scores)//2:] if len(scores) > 1 else scores
    avg_first = sum(first_half) / len(first_half) if first_half else 0
    avg_second = sum(second_half) / len(second_half) if second_half else 0
    start = int(55 + avg_first * 30)
    end = int(55 + avg_second * 30)
    return {'start': max(20, min(90, start)), 'end': max(20, min(90, end))}


def build_account_story_arc(customer_id, account_id):
    """
    Build a StoryArcFull-compatible dict from real context graph data.

    Queries SIGNAL, DECISION, OUTCOME, and STAKEHOLDER nodes for the
    given account and assembles them into the same shape the frontend
    StoryArcsView renders — phases, cast, decisions, outcomes, revenue
    narrative, causal chains, and health trajectory.
    """
    from models import Account
    from utils.context_graph import (
        get_nodes,
        get_edges,
        get_revenue_at_risk,
        get_account_graph_summary,
    )

    # ── Fetch account metadata ──
    account = Account.query.filter_by(
        account_id=account_id,
        customer_id=customer_id,
    ).first()
    if not account:
        return None

    account_name = account.account_name or f'Account {account_id}'
    arr = float(account.revenue or 0)

    # ── Fetch all node types ──
    signals = get_nodes(account_id, node_type='SIGNAL', limit=200)
    decisions = get_nodes(account_id, node_type='DECISION', limit=200)
    outcomes = get_nodes(account_id, node_type='OUTCOME', limit=200)
    stakeholders = get_nodes(account_id, node_type='STAKEHOLDER', limit=50)

    # ── Revenue breakdown ──
    revenue = get_revenue_at_risk(account_id)
    summary = get_account_graph_summary(account_id)

    # ── Determine timeline origin ──
    all_dated = [n for n in signals + decisions + outcomes if n.occurred_at]
    if not all_dated:
        origin = datetime.utcnow()
    else:
        origin = min(n.occurred_at for n in all_dated)

    latest = max((n.occurred_at for n in all_dated), default=origin)
    total_weeks = max(1, _week_number(latest, origin) + 1)

    # ── Build PHASES from monthly signal buckets ──
    signals_sorted = sorted(
        [s for s in signals if s.occurred_at],
        key=lambda s: s.occurred_at,
    )
    monthly_buckets = defaultdict(list)
    for s in signals_sorted:
        key = s.occurred_at.strftime('%Y-%m')
        monthly_buckets[key].append(s)

    phases = []
    phase_week_offset = 0
    sorted_months = sorted(monthly_buckets.keys())
    for idx, month_key in enumerate(sorted_months):
        bucket = monthly_buckets[month_key]
        # Duration: ~4 weeks per month
        duration = 4
        health_range = _sentiment_to_health(bucket)
        phase_name = _phase_name_from_signals(bucket)

        plot_points = []
        for sig in bucket[:5]:  # Limit to 5 plot points per phase
            props = sig.properties or {}
            plot_points.append({
                'week_offset': max(0, _week_number(sig.occurred_at, origin) - phase_week_offset),
                'event_type': sig.node_subtype or 'signal',
                'description': sig.title or '',
                'sentiment_shift': float(props.get('sentiment_shift', 0) or 0),
                'revenue_impact': float(sig.revenue_impact or 0),
                'generates_node_type': 'SIGNAL',
                'kpi_impacts': [],
            })

        phases.append({
            'phase_id': idx,
            'name': phase_name,
            'duration_weeks': duration,
            'health_range': health_range,
            'description': f'{len(bucket)} signals detected in {month_key}',
            'revenue_impact_type': 'none',
            'plot_points': plot_points,
        })
        phase_week_offset += duration

    # Fallback: if no phases, create a single phase
    if not phases:
        phases = [{
            'phase_id': 0,
            'name': 'Current State',
            'duration_weeks': 4,
            'health_range': {'start': 60, 'end': 65},
            'description': 'Account activity period',
            'revenue_impact_type': 'none',
            'plot_points': [],
        }]

    total_phase_weeks = sum(p['duration_weeks'] for p in phases)
    num_phases = len(phases)

    # ── Build CAST from STAKEHOLDER nodes ──
    cast = []
    for sh in stakeholders:
        props = sh.properties or {}
        # Extract name and title from node title (format: "Name (Title)")
        title_str = sh.title or ''
        role = sh.node_subtype or props.get('role', 'stakeholder')
        person_title = role.replace('_', ' ').title()
        if '(' in title_str and ')' in title_str:
            person_title = title_str.split('(')[1].rstrip(')')

        cast.append({
            'role': role,
            'title': person_title,
            'influence_score': float(props.get('influence_score', sh.confidence or 0.5)),
            'sentiment_arc': [0.5] * num_phases,  # Flat for now
            'engagement_frequency': props.get('engagement_frequency', 'monthly'),
            'appears_in_phase': list(range(num_phases)),
        })

    # ── Build DECISIONS from DECISION nodes ──
    arc_decisions = []
    for dec in decisions:
        props = dec.properties or {}
        week = _week_number(dec.occurred_at, origin) if dec.occurred_at else 0

        # Build options from properties if available
        raw_options = props.get('options', [])
        if raw_options and isinstance(raw_options, list):
            options = []
            for opt in raw_options:
                if isinstance(opt, dict):
                    options.append({
                        'option': opt.get('option', str(opt)),
                        'projected_impact': float(opt.get('projected_impact', 0)),
                        'risk_level': opt.get('risk_level', 'medium'),
                    })
                else:
                    options.append({
                        'option': str(opt),
                        'projected_impact': 0,
                        'risk_level': 'medium',
                    })
        else:
            # Single option: the chosen action
            chosen_label = props.get('chosen_option', dec.title or 'Executed')
            options = [{
                'option': chosen_label,
                'projected_impact': float(dec.revenue_impact or 0),
                'risk_level': 'low',
            }]

        # Find the phase_id this decision belongs to
        phase_id = 0
        if dec.occurred_at:
            dec_month = dec.occurred_at.strftime('%Y-%m')
            if dec_month in sorted_months:
                phase_id = sorted_months.index(dec_month)

        arc_decisions.append({
            'decision_id': f'dec_{dec.node_id}',
            'title': dec.title or 'Decision',
            'week': week,
            'phase_id': phase_id,
            'decision_maker_role': props.get('decision_maker_role', 'CSM'),
            'options': options,
            'chosen_option': 0,
            'revenue_impact': float(dec.revenue_impact or 0),
            'outcome_description': props.get('outcome_description', ''),
        })

    # ── Build OUTCOMES from OUTCOME nodes ──
    type_map = {
        'at_risk': 'churn_averted',
        'protected': 'retention',
        'expansion': 'expansion',
        'lost': 'churn_loss',
    }
    arc_outcomes = []
    for out in outcomes:
        props = out.properties or {}
        week = _week_number(out.occurred_at, origin) if out.occurred_at else total_phase_weeks

        arc_outcomes.append({
            'outcome_id': props.get('outcome_id', f'out_{out.node_id}'),
            'title': out.title or 'Outcome',
            'outcome_type': type_map.get(out.revenue_impact_type, out.node_subtype or 'retention'),
            'revenue_value': float(out.revenue_impact or 0),
            'realized_week': week,
            'confidence': float(out.confidence or 0.8),
        })

    # ── Build REVENUE NARRATIVE from aggregates ──
    at_risk = float(revenue.get('at_risk', 0))
    protected = float(revenue.get('protected', 0))
    expansion = float(revenue.get('expansion', 0))
    lost = float(revenue.get('lost', 0))
    net_saved = protected + expansion
    cost_of_inaction = at_risk + lost
    # Estimate intervention cost as ~5-10% of net_saved (reasonable default)
    intervention_cost = max(10000, net_saved * 0.05) if net_saved > 0 else 50000
    roi = int((net_saved / intervention_cost) * 100) if intervention_cost > 0 else 0

    revenue_narrative = {
        'arr_start': arr,
        'arr_end': arr,
        'arr_at_risk_peak': at_risk,
        'roi_of_intervention': roi,
        'cost_of_inaction': cost_of_inaction,
        'time_horizon_weeks': total_phase_weeks,
        'intervention_cost': round(intervention_cost, 2),
        'net_revenue_saved': round(net_saved, 2),
    }

    # ── Build CAUSAL CHAINS from edges ──
    causal_chains = []
    chain_idx = 0
    for dec in decisions[:10]:  # Limit to avoid large queries
        edges = get_edges(dec.node_id, direction='both')
        if not edges:
            continue

        links = []
        chain_revenue = float(dec.revenue_impact or 0)
        for edge in edges:
            # Resolve from/to node titles
            from_title = dec.title or f'Node {edge.from_node_id}'
            to_title = dec.title or f'Node {edge.to_node_id}'

            # Find the connected node
            if edge.from_node_id != dec.node_id:
                connected = ContextNode.query.get(edge.from_node_id)
                if connected:
                    from_title = connected.title or from_title
                    to_title = dec.title or to_title
            else:
                connected = ContextNode.query.get(edge.to_node_id)
                if connected:
                    from_title = dec.title or from_title
                    to_title = connected.title or to_title

            if edge.revenue_impact:
                chain_revenue += float(edge.revenue_impact)

            links.append({
                'from_event': from_title,
                'to_event': to_title,
                'edge_type': edge.edge_type or 'LED_TO',
                'lag_weeks': (edge.properties or {}).get('lag_days', 7) // 7 if isinstance(edge.properties, dict) else 1,
                'confidence': float(edge.confidence or 0.8),
            })

        if links:
            chain_idx += 1
            causal_chains.append({
                'chain_id': f'chain_{dec.node_id}',
                'name': f'{dec.title or "Decision"} Impact Chain',
                'revenue_impact': round(chain_revenue, 2),
                'links': links,
            })

    # ── Assemble StoryArcFull ──
    arc = {
        'arc_id': f'account_{account_id}_story',
        'arc_name': f'{account_name} — Revenue Story',
        'version': '1.0',
        'description': (
            f'Dynamic story arc built from {summary.get("total_nodes", 0)} context graph nodes '
            f'and {summary.get("total_edges", 0)} causal edges for {account_name}. '
            f'This reflects real account data, not a template narrative.'
        ),
        'intelligence_dimensions': [
            'value_realization', 'engagement_depth', 'operational_risk',
            'expansion_readiness', 'sentiment_momentum',
        ],
        'target_audience': 'CRO',
        'duration_weeks': total_phase_weeks,
        'arr_start': arr,
        'arr_end': arr,
        'roi_of_intervention': roi,
        'num_phases': num_phases,
        'num_decisions': len(arc_decisions),
        'num_causal_chains': len(causal_chains),
        'num_outcomes': len(arc_outcomes),
        'revenue_narrative': revenue_narrative,
        'cast': cast,
        'phases': phases,
        'causal_chains': causal_chains,
        'decisions': arc_decisions,
        'outcomes': arc_outcomes,
        'kpi_trajectories': {},
        'edges_template': [],
        'industry_benchmarks': [],
    }

    return arc


@story_arc_api.route('/api/story-arcs/account/<int:account_id>', methods=['GET'])
def get_account_story_arc(account_id):
    """
    Build a dynamic story arc from live context graph data for a specific account.

    The returned object has the same shape as a template StoryArcFull, so the
    frontend can render it with zero changes to the detail panel.

    Args:
        account_id: e.g. 291007

    Returns:
        { "status": "ok", "arc": { ...StoryArcFull } }
    """
    customer_id = get_current_customer_id()
    err, status = _guard_story_arcs(customer_id)
    if err is not None:
        return err, status

    try:
        arc = build_account_story_arc(customer_id, account_id)
    except Exception as e:
        logger.exception("Failed to build account story arc for %s", account_id)
        return jsonify({
            'status': 'error',
            'error': f'Failed to build account story: {str(e)}',
        }), 500

    if arc is None:
        return jsonify({
            'status': 'error',
            'error': f'Account not found: {account_id}',
        }), 404

    return jsonify({
        'status': 'ok',
        'arc': arc,
    })
