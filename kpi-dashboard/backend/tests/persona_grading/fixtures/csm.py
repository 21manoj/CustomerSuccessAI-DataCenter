"""CSM persona fixtures — frontline operator. Lives in their accounts, today.

Note: there's no explicit 'csm' entry in PERSONA_PROMPTS today; the framework
runs CSM questions against the closest match ('vpcs') and the grader flags
this as a gap. That gap-finding is intentional — fixing it is a future-roadmap item.
"""
from ..schema import PersonaQuestion

CSM_QUESTIONS = [
    PersonaQuestion(
        id='csm-q01-today-priority',
        persona='csm',
        question="What should I do today? Give me my top 3 actions ranked by impact.",
        intent="The single most important CSM question — daily prioritization.",
        must_cite=[
            "exactly 3 (or fewer) actions",
            "specific account name per action",
            "$-impact or urgency reason",
        ],
        must_call_tools=['get_csm_daily_actions', 'get_at_risk_accounts'],
        must_call_at_least=1,
        tone_check="Action-oriented verbs. Specific. CSM should know what to do in 60 sec of reading.",
        anti_hallucination=[
            "no actions on accounts not assigned to this CSM",
        ],
        weight=1.5,
    ),
    PersonaQuestion(
        id='csm-q02-why-health-dropped',
        persona='csm',
        question="Why did my account health drop last week? Pick the worst-trending one.",
        intent="Investigation — connecting the journey to specific signals.",
        must_cite=[
            "specific account name",
            "specific signals or KPI movements",
            "timeline (when did the drop start)",
        ],
        must_call_tools=['get_account_journey_timeline', 'analyze_root_cause', 'search_signals', 'explain_kpi_anomaly'],
        must_call_at_least=2,
        tone_check="Investigative tone. Cite evidence, not feelings.",
        anti_hallucination=[
            "no synthesized causes that don't map to actual signals/KPI movements",
        ],
    ),
    PersonaQuestion(
        id='csm-q03-recommend-playbook',
        persona='csm',
        question="Recommend the right playbook for my worst-trending account, and tell me what success looks like.",
        intent="Recommendation + expected outcome — tests if AI can plan, not just observe.",
        must_cite=[
            "specific playbook name",
            "specific account it's recommended for",
            "expected outcome (e.g., '$X protected', 'Y% health recovery')",
        ],
        must_call_tools=['get_playbook_recommendations', 'get_outcome_roi_story', 'get_at_risk_accounts'],
        must_call_at_least=1,
        tone_check="Specific playbook, specific account, specific success metric.",
        anti_hallucination=[
            "no playbook hallucination — must trace to actual playbook catalog",
        ],
    ),
    PersonaQuestion(
        id='csm-q04-qbr-prep',
        persona='csm',
        question="Give me talking points for my next QBR with my biggest account.",
        intent="Communication prep — synthesizes data into a meeting agenda.",
        must_cite=[
            "specific account name",
            "key metrics to discuss (health, ARR, KPI trends)",
            "wins to celebrate AND issues to flag",
        ],
        must_call_tools=['get_account_health', 'get_stakeholder_map', 'get_account_journey_timeline'],
        must_call_at_least=1,
        tone_check="Bulleted talking-point format. Wins + risks balanced.",
        anti_hallucination=[
            "no invented stakeholder names",
        ],
    ),
    PersonaQuestion(
        id='csm-q05-open-playbooks',
        persona='csm',
        question="Show me my open playbook executions and how each one is progressing.",
        intent="Tracking — the daily what's-in-flight question.",
        must_cite=[
            "specific playbook IDs / names",
            "account each is on",
            "progress indicator (% complete or stage)",
        ],
        must_call_tools=['get_csm_daily_actions', 'get_outcome_roi_story'],
        must_call_at_least=1,
        tone_check="Table-style or list. Status per row.",
        anti_hallucination=[
            "no fabricated progress percentages",
        ],
    ),
    PersonaQuestion(
        id='csm-q06-untouched-accounts',
        persona='csm',
        question="Which of my accounts haven't been touched in 30+ days? Sort by ARR.",
        intent="Gap detection — which accounts are getting ghosted.",
        must_cite=[
            "specific account names",
            "days since last interaction or signal",
            "ARR for each (since user asked to sort by it)",
        ],
        must_call_tools=['list_accounts', 'search_signals', 'get_account_journey_timeline'],
        must_call_at_least=1,
        tone_check="Ranked by ARR descending.",
        anti_hallucination=[
            "no fabricated 'last touched' dates",
        ],
    ),
]
