"""CEO persona fixtures — strategic synthesizer. Wants top 2-3, board-ready."""
from ..schema import PersonaQuestion

CEO_QUESTIONS = [
    PersonaQuestion(
        id='ceo-q01-30-second-summary',
        persona='ceo',
        question="Give me the 30-second summary of our customer health right now.",
        intent="The on-the-run question. CEO needs this in transit between meetings.",
        must_cite=[
            "portfolio NRR percentage",
            "biggest single risk or biggest single opportunity",
            "one specific number (revenue at risk OR expansion upside)",
        ],
        must_call_tools=['get_revenue_at_risk', 'get_portfolio_roi_summary', 'get_at_risk_accounts'],
        must_call_at_least=1,
        tone_check="Under 4 sentences. Tight. Board-ready cadence.",
        anti_hallucination=[
            "no laundry list — CEO wants top 2-3, not exhaustive",
        ],
        weight=1.5,
    ),
    PersonaQuestion(
        id='ceo-q02-strategic-risk',
        persona='ceo',
        question="What's the biggest strategic risk in our customer portfolio right now?",
        intent="Synthesis — not 'top 5 at-risk accounts' but 'what pattern matters'.",
        must_cite=[
            "specific risk theme (concentration / segment / geographic / etc.)",
            "supporting evidence (dollar exposure, account count, or pattern)",
            "implication for the company",
        ],
        must_call_tools=['get_revenue_at_risk', 'get_at_risk_accounts'],
        must_call_at_least=1,
        tone_check="Risk framed as theme + evidence + implication, not just account list.",
        anti_hallucination=[
            "no manufactured risk themes — must come from actual data patterns",
        ],
    ),
    PersonaQuestion(
        id='ceo-q03-cascade-exposure',
        persona='ceo',
        question="If we lose our top at-risk account, what's the cascade exposure across other customers?",
        intent="Customer-graph thinking — does losing one signal-fail others?",
        must_cite=[
            "specific account being lost (with ARR)",
            "any cross-account dependencies or shared signals",
            "estimated cascade $ exposure or 'minimal cascade'",
        ],
        must_call_tools=['get_at_risk_accounts', 'get_stakeholder_map', 'search_signals'],
        must_call_at_least=1,
        tone_check="Strategic framing — not just 'we lose $X', but 'and that affects Y'.",
        anti_hallucination=[
            "no invented inter-account dependencies",
        ],
    ),
    PersonaQuestion(
        id='ceo-q04-board-headline',
        persona='ceo',
        question="What's the headline story I should tell the board about customer success this quarter?",
        intent="Pure narrative request. Tests if the system can synthesize a story.",
        must_cite=[
            "one clear headline (e.g., 'NRR holding at 105%')",
            "two supporting points",
            "one risk to flag",
        ],
        must_call_tools=['get_portfolio_roi_summary', 'get_revenue_at_risk', 'get_outcome_roi_story'],
        must_call_at_least=1,
        tone_check="Headline + 3 bullets. Board-deck format.",
        anti_hallucination=[
            "no spin — the story must be honest about both upside and risk",
        ],
    ),
    PersonaQuestion(
        id='ceo-q05-vs-market',
        persona='ceo',
        question="Where are we beating the market on customer success and where are we behind?",
        intent="Competitive context. CEO calibrates vs industry, not just internal trend.",
        must_cite=[
            "an area where we're strong (with metric)",
            "an area where we're behind (with metric)",
            "industry benchmark reference for at least one",
        ],
        must_call_tools=['get_portfolio_roi_summary', 'calculate_power_of_1'],
        must_call_at_least=1,
        tone_check="Honest both ways. Don't only celebrate.",
        anti_hallucination=[
            "no claim of beating market without data backing",
        ],
    ),
]
