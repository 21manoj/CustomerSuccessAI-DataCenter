"""CRO persona fixtures — 15-yr revenue leader. Lives in $ amounts and risk."""
from ..schema import PersonaQuestion

CRO_QUESTIONS = [
    PersonaQuestion(
        id='cro-q01-revenue-at-risk',
        persona='cro',
        question="What's our portfolio revenue at risk over the next 90 days?",
        intent="Foundational risk question; tests the canonical context-graph-driven answer.",
        must_cite=[
            "specific dollar amount (in $M or $K)",
            "number of accounts contributing to that risk",
            "context graph or evidence basis (not just health-band aggregation)",
        ],
        must_call_tools=['get_revenue_at_risk', 'get_at_risk_accounts'],
        must_call_at_least=1,
        tone_check="Lead with the dollar number, not a percentage. CRO-style: '$ first'.",
        anti_hallucination=[
            "no fabricated account_ids (must come from list_accounts or tool output)",
            "no fabricated dollar amounts (must come from a tool call)",
        ],
        weight=1.5,  # foundational — slightly higher weight
    ),
    PersonaQuestion(
        id='cro-q02-worst-accounts-why',
        persona='cro',
        question="Which 3 accounts are most likely to churn next quarter, and what's driving each?",
        intent="Tests root-cause traversal — not just lists, but causal evidence.",
        must_cite=[
            "specific account names (3 of them)",
            "specific signals or KPIs driving each prediction",
            "renewal date or timeline",
        ],
        must_call_tools=['get_at_risk_accounts', 'analyze_root_cause', 'get_account_journey_timeline', 'search_signals'],
        must_call_at_least=2,
        tone_check="Each account framed in one tight paragraph: name, ARR, why-it's-at-risk, when.",
        anti_hallucination=[
            "no invented driver narratives that don't trace to an actual signal/KPI",
        ],
    ),
    PersonaQuestion(
        id='cro-q03-expansion-upside',
        persona='cro',
        question="Where's our biggest expansion upside in the portfolio over the next two quarters?",
        intent="Tests positive-side surfacing — most CS tools over-index on risk.",
        must_cite=[
            "specific account names",
            "expansion dollar amount or pipeline figure",
            "what signal indicates the opportunity (usage, exec engagement, etc.)",
        ],
        must_call_tools=['get_at_risk_accounts', 'list_accounts', 'search_signals'],
        must_call_at_least=1,
        tone_check="Frame as opportunity, not risk. Quantify the upside in $.",
        anti_hallucination=[
            "no fabricated expansion deal sizes",
        ],
    ),
    PersonaQuestion(
        id='cro-q04-causal-chain',
        persona='cro',
        question="Show me the causal chain for our worst-trending account this quarter.",
        intent="Probes context graph traversal — buyer AI-DD will run this exact query.",
        must_cite=[
            "specific account name",
            "ordered chain of events (signals → decisions → outcomes)",
            "starting health and current health",
        ],
        must_call_tools=['get_context_graph_mermaid', 'get_account_journey_timeline', 'analyze_root_cause'],
        must_call_at_least=2,
        tone_check="Tell the story chronologically. Avoid jargon.",
        anti_hallucination=[
            "no synthesized signals that aren't in the actual context graph",
        ],
        weight=1.3,
    ),
    PersonaQuestion(
        id='cro-q05-nrr-trajectory',
        persona='cro',
        question="How are we tracking vs. our quarterly NRR target? Are we ahead, behind, or on plan?",
        intent="Forecast accountability — tests honest forecasting (not over-confident).",
        must_cite=[
            "current portfolio NRR percentage",
            "without-CS-Pulse comparison or trajectory",
            "specific dollar variance or directional indicator",
        ],
        must_call_tools=['get_portfolio_roi_summary', 'get_revenue_at_risk', 'list_accounts'],
        must_call_at_least=1,
        tone_check="Honest: if we're behind, say so. CRO doesn't want spin.",
        anti_hallucination=[
            "no invented NRR targets — should ask user or note the lack",
        ],
    ),
    PersonaQuestion(
        id='cro-q06-playbook-roi',
        persona='cro',
        question="Which playbooks are actually moving revenue, and which are wasting CSM time?",
        intent="Investment efficiency — CRO-as-CFO-of-revenue.",
        must_cite=[
            "specific playbook names with ROI multiples",
            "comparison: top vs bottom performers",
            "$ saved or expanded per playbook",
        ],
        must_call_tools=['get_playbook_recommendations', 'get_outcome_roi_story', 'get_portfolio_roi_summary'],
        must_call_at_least=1,
        tone_check="Rank by $-impact. Be willing to call out underperformers.",
        anti_hallucination=[
            "no fabricated ROI multiples",
        ],
    ),
]
