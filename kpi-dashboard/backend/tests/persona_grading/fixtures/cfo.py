"""CFO persona fixtures — 15-yr finance leader. Lives in ROI, payback, variance."""
from ..schema import PersonaQuestion

CFO_QUESTIONS = [
    PersonaQuestion(
        id='cfo-q01-portfolio-roi',
        persona='cfo',
        question="What's our portfolio ROI on customer success investment?",
        intent="Primary CFO metric — must come from one source of truth.",
        must_cite=[
            "specific ROI multiple (e.g., 8x, 12x)",
            "CS investment $ amount (annual or QTD)",
            "$ revenue protected or expanded",
        ],
        must_call_tools=['get_portfolio_roi_summary', 'get_outcome_roi_story'],
        must_call_at_least=1,
        tone_check="ROI multiple first, then breakdown. CFO format: ratio + components.",
        anti_hallucination=[
            "no inflated ROI claims (must trace to actual outcomes, not forecast)",
        ],
        weight=1.5,
    ),
    PersonaQuestion(
        id='cfo-q02-cost-per-saved-account',
        persona='cfo',
        question="What's our cost per saved account this quarter?",
        intent="Efficiency probe — connects investment to discrete outcomes.",
        must_cite=[
            "specific dollar cost per save",
            "number of saves (denominator)",
            "total CS cost in numerator",
        ],
        must_call_tools=['get_portfolio_roi_summary', 'get_outcome_roi_story'],
        must_call_at_least=1,
        tone_check="Numerator/denominator transparency.",
        anti_hallucination=[
            "no estimated denominators",
        ],
    ),
    PersonaQuestion(
        id='cfo-q03-actual-vs-projected',
        persona='cfo',
        question="Compare actual vs projected revenue protection this quarter.",
        intent="Variance analysis — CFO's daily question.",
        must_cite=[
            "actual figure (dollar)",
            "projected/target figure (dollar)",
            "variance amount or percentage",
        ],
        must_call_tools=['get_portfolio_roi_summary', 'get_outcome_roi_story', 'get_revenue_at_risk'],
        must_call_at_least=1,
        tone_check="Variance leads. If projection wasn't set, acknowledge it.",
        anti_hallucination=[
            "no fabricated quarterly targets",
        ],
    ),
    PersonaQuestion(
        id='cfo-q04-payback-period',
        persona='cfo',
        question="What's our payback period on CS Pulse adoption?",
        intent="Investment lens — when does CS Pulse pay for itself?",
        must_cite=[
            "payback in months",
            "investment cost",
            "monthly $-of-savings rate",
        ],
        must_call_tools=['get_portfolio_roi_summary', 'calculate_power_of_1'],
        must_call_at_least=1,
        tone_check="Months, not days or quarters. CFO standard.",
        anti_hallucination=[
            "no payback claim shorter than realistic given the math",
        ],
    ),
    PersonaQuestion(
        id='cfo-q05-power-of-1',
        persona='cfo',
        question="If we move our portfolio NRR up 1 point, what's that worth in dollar terms?",
        intent="Power-of-1 framing — CS Pulse signature framing for investment scaling.",
        must_cite=[
            "specific dollar value of 1pp NRR",
            "portfolio total ARR (basis)",
            "annualized vs quarterly framing",
        ],
        must_call_tools=['calculate_power_of_1', 'get_portfolio_roi_summary'],
        must_call_at_least=1,
        tone_check="One number, leading. Then context.",
        anti_hallucination=[
            "no math errors (1pp × ARR = answer)",
        ],
    ),
    PersonaQuestion(
        id='cfo-q06-benchmark-comparison',
        persona='cfo',
        question="How does our $/ARR CS spend compare to industry benchmark?",
        intent="External calibration — is our CS spend efficient?",
        must_cite=[
            "our $/ARR ratio (typically 0.8-2.5%)",
            "industry benchmark range",
            "directional verdict (efficient / on-par / over-spending)",
        ],
        must_call_tools=['get_portfolio_roi_summary', 'calculate_power_of_1'],
        must_call_at_least=1,
        tone_check="Ratio first, benchmark second, verdict third.",
        anti_hallucination=[
            "no fabricated industry benchmarks beyond standard 0.8-2.5% range",
        ],
    ),
]
