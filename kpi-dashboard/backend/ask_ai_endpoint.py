#!/usr/bin/env python3
"""
Ask AI v2 Endpoint — Claude-powered intelligent assistant with tool_use.

Replaces the GPT-4o-based /api/executive/ask with a Claude API endpoint that:
1. Receives user query + persona
2. Builds lightweight system context (portfolio summary only)
3. Calls Claude with tool definitions (MCP tools as Claude tools)
4. Loops tool_use rounds until Claude has enough data
5. Returns structured response with artifacts for rich frontend rendering

Behind feature flag: FEATURE_ASK_AI_V2=true

Design principles:
- Feature flag controls endpoint registration only — no new DB columns
- Tools call existing MCP functions directly (same process, no transport)
- customer_id always injected server-side (never trust Claude's input)
- Fallback: if no Anthropic key, return helpful error (frontend falls back to v1)
"""

import json
import time
import logging
from flask import Blueprint, request, jsonify

from auth_middleware import get_current_customer_id
from anthropic_key_utils import get_anthropic_api_key
from ask_ai_tools import TOOL_DEFINITIONS, execute_tool, extract_artifacts

logger = logging.getLogger(__name__)

ask_ai_v2_api = Blueprint('ask_ai_v2', __name__)

# ─── Persona Prompts (reused from executive_dashboard_api.py) ─────────────────

PERSONA_PROMPTS = {
    'cro': {
        'role': 'Chief Revenue Officer',
        'focus': 'revenue protection, pipeline growth, churn prevention, expansion acceleration',
        'tone': 'Think like a CRO — every insight should connect to revenue impact. '
                'Lead with dollar amounts. Quantify risk in ARR terms. '
                'Recommend actions that protect or grow revenue.',
    },
    'cfo': {
        'role': 'Chief Financial Officer',
        'focus': 'CS investment ROI, cost efficiency, payback periods, budget allocation',
        'tone': 'Think like a CFO — every insight should connect to investment returns. '
                'Show ROI ratios, cost-per-account, payback periods. '
                'Compare actual vs projected. Flag inefficient spend.',
    },
    'ceo': {
        'role': 'Chief Executive Officer',
        'focus': 'portfolio health, strategic risks, competitive positioning, board narrative',
        'tone': 'Think like a CEO — synthesize across the entire portfolio. '
                'Highlight the 2-3 things that matter most. '
                'Frame insights in terms of strategic risk and opportunity.',
    },
    'vpcs': {
        'role': 'VP of Customer Success',
        'focus': 'account health, CSM actions, playbook effectiveness, team capacity',
        'tone': 'Think like a VP CS — focus on operational excellence. '
                'Prioritize by impact and urgency. '
                'Recommend specific playbooks and CSM actions.',
    },
}


def _build_system_prompt(persona: str, portfolio_summary: str) -> str:
    """Build the system prompt for Claude with persona + portfolio context."""
    config = PERSONA_PROMPTS.get(persona, PERSONA_PROMPTS['cro'])

    return f"""You are the AI assistant for CS Pulse, a Customer Success Revenue Intelligence platform.
You are speaking to a {config['role']} who cares about: {config['focus']}.

{config['tone']}

PORTFOLIO CONTEXT (lightweight summary — use tools for details):
{portfolio_summary}

INSTRUCTIONS:
- Use the provided tools to fetch specific data when needed. Do NOT guess numbers.
- When showing account-level data, always call the appropriate tool first.
- Use markdown formatting: **bold** for key metrics, bullet points for lists.
- Keep responses concise (200-500 words) unless the user asks for detail.
- Reference specific accounts by name and include health scores and ARR.
- When you call a tool that returns visual data (context graph, pillar breakdown),
  the frontend will render it as a rich artifact — just reference it in your text.
- End with 1-2 suggested follow-up questions when appropriate.
"""


def _build_portfolio_summary(customer_id: int) -> str:
    """
    Build a lightweight portfolio summary for the system prompt.
    Only basic stats — Claude will use tools for details.
    """
    try:
        from models import Account, HealthScore, db
        import utils.health_thresholds as ht

        accounts = Account.query.filter_by(customer_id=customer_id).all()
        if not accounts:
            return "No accounts found for this customer."

        account_ids = [a.account_id for a in accounts]
        total_arr = sum(a.revenue or 0 for a in accounts)

        # Get latest health scores
        from sqlalchemy import func
        latest_sub = (
            db.session.query(
                HealthScore.account_id,
                func.max(HealthScore.measurement_month).label('max_month')
            )
            .filter(HealthScore.account_id.in_(account_ids))
            .group_by(HealthScore.account_id)
            .subquery()
        )
        health_rows = (
            db.session.query(HealthScore)
            .join(latest_sub, db.and_(
                HealthScore.account_id == latest_sub.c.account_id,
                HealthScore.measurement_month == latest_sub.c.max_month
            ))
            .all()
        )

        health_map = {h.account_id: float(h.health_score) for h in health_rows}
        scores = list(health_map.values())

        critical = sum(1 for s in scores if s < ht.at_risk_min())
        at_risk = sum(1 for s in scores if ht.at_risk_min() <= s < ht.healthy_min())
        healthy = sum(1 for s in scores if s >= ht.healthy_min())
        avg_health = round(sum(scores) / len(scores), 1) if scores else 0

        # Top 5 accounts by ARR
        top_accounts = sorted(accounts, key=lambda a: a.revenue or 0, reverse=True)[:5]
        top_str = ', '.join(
            f"{a.account_name} (${a.revenue or 0:,.0f})"
            for a in top_accounts
        )

        return f"""Accounts: {len(accounts)} | Total ARR: ${total_arr:,.0f}
Health: {healthy} healthy, {at_risk} at-risk, {critical} critical | Avg: {avg_health}
Top accounts by ARR: {top_str}
Health thresholds: Critical (<{ht.at_risk_min()}), At-Risk ({ht.at_risk_min()}-{ht.healthy_min()-1}), Healthy (>={ht.healthy_min()})"""

    except Exception as e:
        logger.warning(f"Portfolio summary error: {e}")
        return "Portfolio data unavailable — use tools to fetch account details."


# ─── Main Endpoint ───────────────────────────────────────────────────────────

@ask_ai_v2_api.route('/api/executive/ask-v2', methods=['POST'])
def ask_v2():
    """
    Claude-powered Ask AI with tool_use and rich artifacts.

    Request:
        { "query": str, "persona": str, "conversation_history": list }

    Response:
        {
            "response": str (markdown),
            "artifacts": [{ type, title, ... }],
            "tools_called": [str],
            "context_stats": { accounts, tools_used, rounds },
            "suggested_followups": [str],
            "elapsed_ms": int,
            "version": "v2"
        }
    """
    start_time = time.time()

    try:
        customer_id = get_current_customer_id()
        if not customer_id:
            return jsonify({'error': 'Authentication required'}), 401

        data = request.json
        if not data or 'query' not in data:
            return jsonify({'error': 'query is required'}), 400

        query_text = data['query']
        persona = data.get('persona', 'cro')
        conversation_history = data.get('conversation_history', [])

        # Check for Anthropic API key
        api_key = get_anthropic_api_key(customer_id)
        if not api_key:
            return jsonify({
                'error': 'Anthropic API key not configured',
                'message': 'Set ANTHROPIC_API_KEY environment variable or configure per-customer key.',
                'fallback': True,  # Signal frontend to use v1 endpoint
            }), 503

        # Build system prompt with lightweight portfolio summary
        portfolio_summary = _build_portfolio_summary(customer_id)
        system_prompt = _build_system_prompt(persona, portfolio_summary)

        # Initialize Anthropic client
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        # Build conversation messages
        messages = []

        # Add conversation history (last 5 turns max)
        for turn in conversation_history[-5:]:
            if turn.get('query'):
                messages.append({"role": "user", "content": turn['query']})
            if turn.get('response'):
                messages.append({"role": "assistant", "content": turn['response']})

        # Add current query
        messages.append({"role": "user", "content": query_text})

        # ── Tool Use Loop ──────────────────────────────────────────────
        all_artifacts = []
        tools_called = []
        max_rounds = 5  # Safety limit on tool_use rounds
        final_text = ""

        for round_num in range(max_rounds):
            try:
                response = client.messages.create(
                    model="claude-sonnet-4-5-20250514",
                    system=system_prompt,
                    messages=messages,
                    tools=TOOL_DEFINITIONS,
                    max_tokens=4096,
                    temperature=0.3,
                )
            except anthropic.APIError as e:
                logger.error(f"Anthropic API error: {e}")
                return jsonify({
                    'error': 'AI service error',
                    'message': str(e),
                    'fallback': True,
                }), 502

            # Collect text from this response
            text_parts = []
            tool_use_blocks = []

            for block in response.content:
                if block.type == "text":
                    text_parts.append(block.text)
                elif block.type == "tool_use":
                    tool_use_blocks.append(block)

            if text_parts:
                final_text = "\n".join(text_parts)

            # If no tool_use, we're done
            if response.stop_reason != "tool_use":
                break

            # Execute tool calls and feed results back
            tool_results_for_claude = []
            for tool_block in tool_use_blocks:
                tool_name = tool_block.name
                tool_input = tool_block.input
                tools_called.append(tool_name)

                logger.info(f"Ask AI v2: calling tool {tool_name} for customer {customer_id}")

                # Execute (customer_id injected server-side)
                result = execute_tool(tool_name, tool_input, customer_id)

                # Extract artifacts
                artifacts = extract_artifacts(tool_name, result)
                all_artifacts.extend(artifacts)

                # Feed result back to Claude
                tool_results_for_claude.append({
                    "type": "tool_result",
                    "tool_use_id": tool_block.id,
                    "content": json.dumps(result, default=str),
                })

            # Append assistant response + tool results for next round
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results_for_claude})

        # ── Build Response ─────────────────────────────────────────────
        elapsed_ms = int((time.time() - start_time) * 1000)

        return jsonify({
            'response': final_text,
            'artifacts': all_artifacts,
            'tools_called': tools_called,
            'context_stats': {
                'tool_rounds': min(round_num + 1, max_rounds),
                'tools_used': len(tools_called),
                'unique_tools': list(set(tools_called)),
            },
            'suggested_followups': _generate_followups(persona, tools_called),
            'elapsed_ms': elapsed_ms,
            'persona': persona,
            'version': 'v2',
        })

    except Exception as e:
        logger.error(f"Ask AI v2 error: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error', 'message': str(e)}), 500


def _generate_followups(persona: str, tools_called: list) -> list:
    """Generate contextual follow-up suggestions based on what was asked."""
    base = PERSONA_PROMPTS.get(persona, PERSONA_PROMPTS['cro'])

    # Context-aware followups based on tools used
    followups = []
    if 'get_at_risk_accounts' in tools_called or 'list_accounts' in tools_called:
        followups.append("What playbooks should we activate for the at-risk accounts?")
    if 'get_context_graph_mermaid' in tools_called:
        followups.append("What are the key stakeholders involved in this account?")
    if 'get_revenue_at_risk' in tools_called:
        followups.append("How much revenue can we protect if we act this quarter?")
    if 'get_csm_daily_actions' in tools_called:
        followups.append("Which of these actions has the highest ROI impact?")
    if 'calculate_power_of_1' in tools_called:
        followups.append("Show me the full portfolio ROI summary.")

    # Pad with persona defaults if we don't have enough
    if len(followups) < 2:
        defaults = {
            'cro': ["Which accounts have the highest churn risk?", "Where is our biggest expansion opportunity?"],
            'cfo': ["What is our CS investment returning per dollar?", "Give me the board-ready ROI summary."],
            'ceo': ["Give me the 30-second board summary.", "What is our single biggest strategic risk?"],
            'vpcs': ["What should my CSMs focus on today?", "Which playbooks are most effective?"],
        }
        for d in defaults.get(persona, defaults['cro']):
            if d not in followups:
                followups.append(d)
            if len(followups) >= 3:
                break

    return followups[:3]
