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

try:
    from utils.llm_budget_controller import can_call as _budget_can_call, record_usage as _budget_record
except Exception:
    _budget_can_call = None
    _budget_record = None

logger = logging.getLogger(__name__)

ask_ai_v2_api = Blueprint('ask_ai_v2', __name__)

# ─── Persona Prompts (reused from executive_dashboard_api.py) ─────────────────

PERSONA_PROMPTS = {
    'cro': {
        'role': 'Chief Revenue Officer',
        'focus': 'revenue protection, pipeline growth, churn prevention, expansion acceleration',
        # Sprint 1.4 (Apr 26 2026): evidence-citing nudge for expansion / pipeline
        # questions. cro-q03 with the Item 7 fix returned numbers (e.g. "$9.6M
        # pipeline") but the grader flagged "appears without supporting evidence
        # or methodology, raising concerns about fabrication." Adding explicit
        # signal-citation requirement so account-level claims are anchored.
        'tone': 'Think like a CRO — every insight should connect to revenue impact. '
                'Lead with dollar amounts. Quantify risk in ARR terms. '
                'Recommend actions that protect or grow revenue. '
                'When reporting expansion or at-risk DOLLAR figures per account, '
                'cite the specific signal/decision/outcome evidence: usage spike, '
                'exec engagement uptick, NPS shift, budget cycle alignment, '
                'champion departure, etc. Top-3 accounts in any ranking MUST have '
                'at least one signal cited each — \"$X expansion\" without a "why" '
                'reads as fabricated to a 15-yr CRO.',
    },
    'cfo': {
        'role': 'Chief Financial Officer',
        'focus': 'CS investment ROI, cost efficiency, payback periods, budget allocation',
        # Apr 25 2026 (Sprint 1): tone enriched with explicit benchmark anchors
        # so CFO benchmark-comparison questions cite a defensible range.
        'tone': 'Think like a CFO — every insight should connect to investment returns. '
                'Show ROI ratios, cost-per-account, payback periods. '
                'Compare actual vs projected. Flag inefficient spend. '
                'When citing industry benchmarks: CS spend 0.8–2.5% of ARR, '
                'ROI typically 5–15×, payback 3–6 months. Use the wider range '
                'unless the customer has a defined target. '
                'Never conflate: (1) context-graph confirmed revenue at risk, '
                '(2) playbook-attributed revenue protected, (3) modeled churn exposure '
                'from unhealthy accounts. Name which lens you use. For NRR, state whether '
                'historical actuals, Wizard B TTM counterfactual, or Predictor v3 forward.',
        'suggested': [
            'What is our CS investment returning per dollar?',
            'How much confirmed revenue is at risk in the context graph?',
            'Compare actual vs projected revenue protection — do we have a target set?',
            'What is our payback period on CS Pulse at current playbook economics?',
            'How does modeled ROI scale if we add more accounts?',
        ],
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
    # Apr 25 2026 (Sprint 1): added 'csm' persona that was previously falling
    # back to 'vpcs' at runtime. Frontline operator tone — narrower scope
    # (own accounts only), action-oriented, comms-prep ready.
    'csm': {
        'role': 'Customer Success Manager',
        'focus': 'my own assigned accounts, what to do today on each, comms prep, '
                 'investigation of recent health movements',
        'tone': 'Think like a frontline CSM — specific, action-oriented, tied to MY '
                'assigned accounts only. Surface what to do today with $-impact '
                'reasoning per action. Draft comms when asked. Investigate by '
                'tracing to specific signals or KPI movements, not narratives.',
    },
}


def _build_system_prompt(persona: str, portfolio_summary: str) -> str:
    """Build the system prompt for Claude with persona + persona-specific
    rules + portfolio context.

    Apr 25 2026 (Sprint 1) additions:
      - Foundational-question tool-call enforcement (Item 2)
      - CEO length budget for summary-style questions (Item 3)
      - Ask-when-unspecified rule (Item 4)
      - Ranking deliverable enforcement (Item 6)
    All additions are persona-conditional where it makes sense to avoid
    cross-persona tone bleed.
    """
    config = PERSONA_PROMPTS.get(persona, PERSONA_PROMPTS['cro'])

    # ── Persona-conditional rule blocks ─────────────────────────────────
    # Sprint 1 (Apr 25): added LENGTH BUDGET for CEO.
    # Sprint 1.2 (Apr 26): decoupled TOOL-CALL DISCIPLINE corollary from the
    # generic FOUNDATIONAL rule. Sprint 1.1 had the corollary apply to all
    # personas — that fixed CEO truncation but caused CRO q01/q06 to
    # under-call tools (regressions of -1.4 and -2.3 grade-pts). Synthesis
    # personas (CEO) need budget reservation; analytical personas (CRO,
    # CFO, VP CS, CSM) need permission to make multiple tool calls without
    # self-throttling.
    persona_specific_rules = ""
    if persona == 'ceo':
        persona_specific_rules += (
            "\n- LENGTH BUDGET: For questions explicitly asking for a "
            "'summary', 'headline', '30-second', or 'TL;DR' view, the "
            "response MUST be ≤ 4 sentences. Resist elaboration. CEO "
            "wants the synthesized top 2-3, not the laundry list."
            "\n- TOOL-CALL DISCIPLINE (CEO synthesis questions): pick the "
            "1-2 tools MOST central to the question; do NOT call every "
            "tangentially-related tool. Always reserve enough token budget "
            "for a complete synthesis paragraph with conclusions — a "
            "truncated mid-analysis answer is worse than a shorter answer "
            "with fewer tools. (CEO only — analytical personas like CRO, "
            "CFO, VP CS need to call multiple tools to do their job.)"
        )
    if persona == 'cfo':
        persona_specific_rules += (
            "\n- CFO NRR LENS: When asked 'what is our NRR' (or similar), "
            "state which lens before the number: (1) historical actuals from "
            "outcomes, (2) Wizard B TTM counterfactual, or (3) Predictor v3 "
            "forward 12mo. Do not blend lenses in one headline %."
            "\n- CFO VARIANCE (actual vs projected): If no corporate budget "
            "target or quarterly projection exists in context or tool output, "
            "say so explicitly — do NOT invent a 'projected' figure. Offer "
            "modeled Po1 or playbook forward impact as context only, labeled "
            "as modeled."
            "\n- CFO TOOL DISCIPLINE: For portfolio ROI, cost-per-save, or "
            "payback questions you MUST call get_portfolio_roi_summary and/or "
            "get_outcome_roi_story before stating multiples or $. For "
            "confirmed $ at risk / expansion, cite CONTEXT GRAPH totals first."
            "\n- CFO REVENUE LENSES: playbook-attributed $ ≠ context-graph "
            "confirmed $ ≠ modeled churn exposure (health-based COI)."
        )
    if persona == 'vpcs':
        persona_specific_rules += (
            "\n- VP CS TEAM OPS: For CSM rankings, capacity, or daily queue questions, call "
            "get_csm_scorecard, get_team_capacity, and get_csm_daily_actions — deliver CSM "
            "names, account counts, and ranked lists. Never invent headcount targets or NRR benchmarks."
            "\n- VP CS CAPACITY: get_team_capacity includes capacity_planning (recommended CSM "
            "count) and top_performers (critical→expansion playbooks). Cite allocation_rationale."
            "\n- VP CS PLAYBOOKS: For effectiveness, use get_playbook_success_metrics and "
            "get_outcome_roi_story; label $0 attributed when executions exist without proof."
            "\n- VP CS UNCOVERED RISK: When asked about accounts without playbook coverage, use "
            "uncovered_at_risk from get_team_capacity or list at-risk accounts with last touch."
        )
    if persona == 'cro':
        persona_specific_rules += (
            "\n- CRO REVENUE LENSES: Never mix in one headline without naming the lens: "
            "(1) context-graph confirmed $ at risk / protected / expansion, "
            "(2) ARR exposure (health-band sub-70 ARR), (3) forward NRR / Predictor v3. "
            "Portfolio revenue questions MUST call get_portfolio_revenue_breakdown first "
            "(includes top_at_risk_accounts and top_expansion_accounts) — do NOT stop after "
            "an empty preamble. Expansion upside questions MUST deliver account names, $, and "
            "one signal each."
            "\n- CRO NRR TARGET: If no customer NRR target exists in tools or context, say "
            "'no quarterly NRR target configured' — do NOT invent 105% or any benchmark target. "
            "Offer Wizard B or forward NRR as optional context, labeled."
            "\n- CRO PLAYBOOK ROI: For playbook effectiveness questions, call "
            "get_outcome_roi_story and get_playbook_recommendations even when no active "
            "recommendations — rank historical $ impact when executions exist."
            "\n- CRO CAUSAL CHAIN: For causal-chain questions, call get_context_graph_mermaid "
            "or get_account_journey_timeline plus analyze_root_cause; cite signal→outcome order."
            "\n- CRO WHAT-IF DISCIPLINE: A 'what if we intervene / act on these accounts' answer is a "
            "FORESIGHT (predictive) estimate — present it as a RANGE with stated confidence, never a bare "
            "point estimate. Cap upside at the INTERVENTION CEILING in the portfolio summary "
            "(revenue at risk + expansion pipeline); a projection above it is wrong. Compute ROI against the "
            "actual intervention cost; if the implied return exceeds 10x, call it an unvalidated upper bound, "
            "not a forecast. When you cite a with-vs-without-intervention NRR delta, reconcile it to the "
            "dashboard lens you are using (Foresight = Predictor v3, or Hindsight = Wizard B counterfactual) "
            "and name that lens — do not produce a third, unlabeled NRR path."
        )

    return f"""You are the AI assistant for CS Pulse, a Customer Success Revenue Intelligence platform.
You are speaking to a {config['role']} who cares about: {config['focus']}.

{config['tone']}

PORTFOLIO CONTEXT (lightweight summary — use tools for details):
{portfolio_summary}

INSTRUCTIONS:
- Use the provided tools to fetch specific data when needed. Do NOT guess numbers.
- CRITICAL: Account IDs are large integers (e.g. 444001, 444002). ALWAYS call list_accounts first to get the correct account_id before calling any account-specific tool. Never guess account IDs.
- When showing account-level data, always call the appropriate tool first.
- Use markdown formatting: **bold** for key metrics, bullet points for lists.
- Keep responses concise (200-500 words) unless the user asks for detail.
- Reference specific accounts by name and include health scores and ARR.
- When you call a tool that returns visual data (context graph, pillar breakdown),
  the frontend will render it as a rich artifact — just reference it in your text.
- End with 1-2 suggested follow-up questions when appropriate.

- HARD CAP ON TOOL CALLS (Apr 27 2026, Fix B): You may call AT MOST 4 tools
  total across this entire response. After 4 calls, you MUST stop calling
  tools and write the synthesis paragraph with whatever data you have.
  Looping the same tool over multiple accounts to "verify" a portfolio
  number is the #1 cause of truncated answers. Trust the portfolio-level
  tools (get_portfolio_revenue_breakdown, get_csm_scorecard, get_team_capacity,
  get_portfolio_roi_summary) — they include top-N account detail in one call.
  A complete answer with 3 tool calls beats a truncated mid-analysis with 6.

- ROADMAP ACKNOWLEDGEMENT (Apr 27 2026): Some quantitative analyses are
  not yet available in the platform — specifically: per-signal lead-time
  statistics, per-signal predictor accuracy rates, churn-probability
  scoring with confidence intervals. If asked for any of these, do NOT
  fabricate. Instead: (a) explicitly note "Quantitative signal-attribution
  with lead-time + accuracy stats is on our Q3 2026 roadmap", (b) deliver
  what's available today via search_signals + get_account_journey_timeline
  (signal types collected, counts per account, qualitative observations),
  (c) close with "happy to commit a date once the predictor model lands."
  An honest "we'll have this in Q3 + here's the data we have today" beats
  an invented answer.

- CONTEXT GRAPH FIRST: The CONTEXT GRAPH section in PORTFOLIO CONTEXT was
  loaded from the database before this turn. For revenue at risk / protected /
  expansion totals, cite those numbers first; use tools for drill-down or
  account-level detail. Include node_id when referencing a specific signal/outcome.

- FOUNDATIONAL-QUESTION TOOL-CALL ENFORCEMENT (Apr 25 2026, Sprint 1.2 decoupled):
  For any question that asks about (a) revenue at risk, (b) ROI / payback /
  CS investment, (c) at-risk accounts, (d) portfolio NRR, you MUST call
  the appropriate tool BEFORE producing a numeric answer when the CONTEXT
  GRAPH block does not already contain the needed account-level detail.
  The PORTFOLIO CONTEXT block is authoritative for portfolio-level context
  graph dollar totals; tools validate and extend it.
  Call as many tools as the analysis requires — analytical personas
  (CRO, CFO, VP CS, CSM) often need to triangulate across 3-5 tools to
  produce a defensible answer. Do NOT self-throttle on tool count.
  (Note: CEO synthesis questions have a separate TOOL-CALL DISCIPLINE
  rule below that DOES cap tool count to preserve synthesis budget.
  That rule is CEO-only and should not generalize to other personas.)

- ASK-WHEN-UNSPECIFIED — narrow scope (Apr 25 2026, tightened Sprint 1.1):
  This rule applies ONLY when the question itself explicitly compares
  against a numeric target/quota/projection that has NOT been provided
  (e.g., "are we on pace vs our 105% NRR target?", "how does this
  compare to our $5M expansion goal?"). In that case, ask for the
  target rather than inventing one.
  DEFAULT BEHAVIOR for everything else: gather data via tools and
  answer directly. Questions like "how effective have our playbooks
  been", "show me at-risk accounts", "which CSMs need help" — these
  do NOT have hidden targets and should be answered by calling the
  relevant tool, NOT by asking clarifying questions. Asking when the
  user expected analysis is a deflection, not professionalism.

- RANKING-DELIVERABLE ENFORCEMENT (Apr 25 2026):
  For "which X is best/worst/most/least", "rank the Ys", or "compare A vs
  B" questions, you MUST deliver a ranked list of at least 3 items (or
  fewer only if the underlying data has fewer items, in which case state
  that explicitly). A vague answer or "no data available" is acceptable
  ONLY if the relevant tool was actually called and confirmed empty.

- CRITICAL ROI CONSISTENCY: For any investment, ROI, or cost question, use get_portfolio_roi_summary.
  The numbers MUST match the CFO dashboard exactly. Key benchmarks for reference:
  CS Investment scales at ~1-1.5% of ARR (industry benchmark). ROI is typically 5-15x.
  Revenue per CS dollar is typically $5-$15. Payback is typically 3-6 months.
  Never use different calculation paths — all ROI answers come from one source of truth.
- CRITICAL REVENUE CONSISTENCY: "Revenue at risk" is the context graph assessed risk from the
  PORTFOLIO CONTEXT above, NOT the total ARR of critical/at-risk accounts. These are different:
  * Revenue at Risk (context graph): assessed risk based on causal evidence chains
  * Critical Account ARR: total revenue of accounts with health < 50
  Always use the Revenue Intelligence numbers from PORTFOLIO CONTEXT for revenue questions.
  When asked "how much revenue is at risk", cite the context graph number, then optionally
  mention the critical account ARR as additional context.
{persona_specific_rules}
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
        avg_health_simple = round(sum(scores) / len(scores), 1) if scores else 0
        # Revenue-weighted avg health (same as CRO dashboard)
        revenue_map = {a.account_id: float(a.revenue or 0) for a in accounts}
        weighted_sum = sum(health_map.get(aid, 0) * revenue_map.get(aid, 0) for aid in account_ids)
        total_rev = sum(revenue_map.get(aid, 0) for aid in account_ids)
        avg_health = round(weighted_sum / total_rev, 1) if total_rev > 0 else avg_health_simple

        # Top 5 accounts by ARR
        top_accounts = sorted(accounts, key=lambda a: a.revenue or 0, reverse=True)[:5]
        top_str = ', '.join(
            f"{a.account_name} (${a.revenue or 0:,.0f})"
            for a in top_accounts
        )

        # Rough health-derived NRR PROXY. This is a fallback only — the
        # authoritative NRR comes from the two dashboard lenses (Foresight =
        # Predictor v3 forward; Hindsight = Wizard B counterfactual). Presenting
        # this proxy as "the" NRR is what made Ask AI's number diverge from the
        # dashboard, so it is explicitly labeled a proxy below.
        if avg_health >= 70:
            nrr = round(100 + (avg_health - 70) * 0.33)
        elif avg_health >= 40:
            nrr = round(90 + (avg_health - 40) * 0.33)
        else:
            nrr = round(85 + avg_health * 0.125)

        # Aggregate revenue intelligence from context graph (same as CRO dashboard)
        rev_at_risk = 0
        rev_protected = 0
        rev_expansion = 0
        try:
            from utils.context_graph import aggregate_revenue_across_accounts
            rev_data = aggregate_revenue_across_accounts(customer_id, account_ids)
            rev_at_risk = rev_data.get('revenue_at_risk', 0)
            rev_protected = rev_data.get('revenue_protected', 0)
            rev_expansion = rev_data.get('expansion_pipeline', 0)
        except Exception:
            pass

        # Critical accounts ARR (for context, NOT revenue at risk)
        critical_arr = sum(
            revenue_map.get(aid, 0)
            for aid in account_ids
            if health_map.get(aid, 100) < ht.at_risk_min()
        )

        # Deterministic ceiling for any what-if / intervention projection.
        # You cannot protect more than what is at risk, nor capture more than
        # the identified expansion pipeline — so upside is hard-bounded by these.
        max_protectable = rev_at_risk
        max_upside = rev_at_risk + rev_expansion

        return f"""Accounts: {len(accounts)} | Total ARR: ${total_arr:,.0f}
Health: {healthy} healthy, {at_risk} at-risk, {critical} critical | Avg: {avg_health}
NRR (health proxy): {nrr}% — ROUGH PROXY ONLY, not authoritative. For the real NRR cite the two dashboard lenses and NAME the lens: Foresight (Predictor v3, forward 12mo) or Hindsight (Wizard B counterfactual, TTM). Never present this proxy as the NRR or blend it with the lenses.
Top accounts by ARR: {top_str}
Health thresholds: Critical (<{ht.at_risk_min()}), At-Risk ({ht.at_risk_min()}-{ht.healthy_min()-1}), Healthy (>={ht.healthy_min()})

REVENUE INTELLIGENCE (from Context Graph — same source as CRO dashboard):
  Revenue at Risk: ${rev_at_risk:,.0f} (causal evidence from context graph outcomes)
  Revenue Protected: ${rev_protected:,.0f} (confirmed by interventions)
  Expansion Pipeline: ${rev_expansion:,.0f} (identified opportunities)
  Critical Accounts ARR: ${critical_arr:,.0f} (total ARR of critical accounts — NOT the same as revenue at risk)

INTERVENTION CEILING (hard bounds for any "what if we intervene / act on these accounts" projection):
  Max revenue protectable = ${max_protectable:,.0f} (cannot protect more than what is at risk)
  Max total upside incl. expansion = ${max_upside:,.0f}
  Any projected recovered/protected $ MUST be <= these ceilings. Compute ROI against the ACTUAL
  intervention cost and present it as a RANGE labeled Foresight (predictive, not realized). If the
  implied return exceeds 10x, present it as an unvalidated upper bound and say so — never as a forecast.
  Never imply a hundreds-of-x return from a small spend.

CRITICAL RULES:
- NRR: {nrr}% is a HEALTH PROXY, not authoritative and NOT a benchmark (never invent 105%). When asked
  the NRR, cite the Foresight and/or Hindsight lens by name; use the proxy only if no lens is available, labeled as such.
- What-if upside is bounded by the INTERVENTION CEILING above — a projection exceeding ${max_upside:,.0f} is wrong by construction.
- "Revenue at risk" means ${rev_at_risk:,.0f} from context graph, NOT ${critical_arr:,.0f} (total ARR of critical accounts).
  Revenue at risk is the ASSESSED risk based on causal evidence chains, not the full ARR of unhealthy accounts.
- NEVER equate "critical account ARR" with "revenue at risk" — they are fundamentally different metrics."""

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

        # Portfolio summary + full context graph block (loaded before any tool/LLM turn)
        portfolio_summary = _build_portfolio_summary(customer_id)
        from utils.context_graph_ask_context import build_ask_context_graph_block
        graph_context, graph_stats = build_ask_context_graph_block(customer_id)
        system_prompt = _build_system_prompt(
            persona,
            f"{portfolio_summary}\n\n=== CONTEXT GRAPH (authoritative — cite node_id when referencing) ===\n{graph_context}",
        )

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

        # ── Budget check ──────────────────────────────────────────────
        _budget_blocked = False
        try:
            if _budget_can_call and not _budget_can_call(customer_id, 'ask_ai_v2'):
                _budget_blocked = True
        except Exception:
            pass  # fail-open

        if _budget_blocked:
            return jsonify({
                'response': 'Daily AI budget reached — please try again tomorrow or contact your admin.',
                'budget_exceeded': True,
            }), 429

        # ── Tool Use Loop ──────────────────────────────────────────────
        all_artifacts = []
        tools_called = []
        max_rounds = 5  # Safety limit on tool_use rounds
        final_text = ""

        # llm_call() wraps messages.create + record_usage on every exit
        # path. Migrated Apr 21 2026 from the dual-call pattern.
        from utils.llm_budget_controller import llm_call
        for round_num in range(max_rounds):
            try:
                response = llm_call(
                    client,
                    customer_id=customer_id,
                    module='ask_ai_v2',
                    model="claude-sonnet-4-6",
                    system=system_prompt,
                    messages=messages,
                    tools=TOOL_DEFINITIONS,
                    # Sprint 1.1 (Apr 25 2026): bumped 4096→6144 to give
                    # multi-tool synthesis answers room to land a final
                    # paragraph. Sprint 1 saw ceo-q03 truncate mid-analysis
                    # at 4096 after the model spent budget on 5 tool calls.
                    max_tokens=6144,
                    temperature=0.3,
                )
            except anthropic.APIError as e:
                logger.error(f"Anthropic API error: {e}")
                # llm_call() already emitted record_usage(success=False) before
                # re-raising, so no need to repeat it here.
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

        # ── Ensure final_text is non-empty ─────────────────────────────
        if not final_text and tools_called:
            # Claude exhausted tool rounds without returning final text.
            # Make one more call asking it to summarize.
            try:
                messages.append({"role": "user", "content": (
                    "Based on the data you gathered from the tools above, "
                    "provide a concise answer to the original question. "
                    "Be specific with numbers, account names, and actionable recommendations."
                )})
                summary_resp = llm_call(
                    client,
                    customer_id=customer_id,
                    module='ask_ai_v2',
                    model="claude-sonnet-4-6",
                    system=system_prompt,
                    messages=messages,
                    max_tokens=2048,
                    temperature=0.3,
                )
                for block in summary_resp.content:
                    if block.type == "text":
                        final_text = block.text
                        break
            except Exception as e:
                logger.warning(f"Ask AI v2: summary fallback failed: {e}")

        if not final_text:
            final_text = ("I retrieved data about your portfolio but couldn't generate a summary. "
                          "Please try rephrasing your question.")
            logger.warning(f"Ask AI v2: empty final_text for customer {customer_id} "
                           f"after {min(round_num + 1, max_rounds)} rounds, "
                           f"tools called: {tools_called}")

        # ── Build Response ─────────────────────────────────────────────
        elapsed_ms = int((time.time() - start_time) * 1000)

        # Activity log: AI query visibility for customer admins
        try:
            from activity_logging import ActivityLogger
            ActivityLogger.log_activity(
                customer_id=customer_id,
                action_type='ai_query',
                action_description=f"Ask AI ({persona}): {query_text[:80]}",
                resource_type='ai',
                details={'persona': persona, 'tools_called': tools_called, 'elapsed_ms': elapsed_ms, 'rounds': min(round_num + 1, max_rounds)},
            )
        except Exception:
            pass

        return jsonify({
            'response': final_text,
            'artifacts': all_artifacts,
            'tools_called': tools_called,
            'context_stats': {
                **graph_stats,
                'tool_rounds': min(round_num + 1, max_rounds),
                'tools_used': len(tools_called),
                'unique_tools': list(set(tools_called)),
            },
            'context_graph_loaded': True,
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
