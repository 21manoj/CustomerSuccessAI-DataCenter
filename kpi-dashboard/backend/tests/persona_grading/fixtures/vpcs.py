"""VP CS persona fixtures — operational excellence. Lives in playbooks + capacity."""
from ..schema import PersonaQuestion

VPCS_QUESTIONS = [
    PersonaQuestion(
        id='vpcs-q01-csms-need-help',
        persona='vpcs',
        question="Which CSMs need help today? Show me workload + outcomes.",
        intent="Capacity management — VP CS's daily-stand-up question.",
        must_cite=[
            "specific CSM names",
            "their current workload (account count, pending playbooks)",
            "outcome metrics (saves, escalations, etc.)",
        ],
        must_call_tools=['get_csm_daily_actions', 'list_accounts'],
        must_call_at_least=1,
        tone_check="Operational tone — names, numbers, suggested action. Not narrative.",
        anti_hallucination=[
            "no fabricated CSM names",
        ],
        weight=1.3,
    ),
    PersonaQuestion(
        id='vpcs-q02-playbook-effectiveness',
        persona='vpcs',
        question="Which playbooks haven't been working in the last 60 days, and why?",
        intent="Playbook governance — flagging non-performers and root-causing.",
        must_cite=[
            "specific playbook names",
            "success rate or $ impact (or lack of)",
            "hypothesis for why it's not working (signal mismatch, timing, etc.)",
        ],
        must_call_tools=['get_playbook_recommendations', 'get_outcome_roi_story'],
        must_call_at_least=1,
        tone_check="Critical lens — willing to recommend retiring or revising playbooks.",
        anti_hallucination=[
            "no invented playbook names — must trace to actual playbook execution data",
        ],
    ),
    PersonaQuestion(
        id='vpcs-q03-daily-action-queue',
        persona='vpcs',
        question="Show me the daily action queue prioritized by impact across the team.",
        intent="Cross-CSM prioritization — VP-level view of operational queue.",
        must_cite=[
            "specific accounts in priority order",
            "$-impact or urgency for each",
            "assigned CSM per action",
        ],
        must_call_tools=['get_csm_daily_actions', 'get_at_risk_accounts'],
        must_call_at_least=1,
        tone_check="Ranked list, top-down. Action verbs.",
        anti_hallucination=[
            "no manufactured prioritization rationale",
        ],
    ),
    PersonaQuestion(
        id='vpcs-q04-uncovered-risk',
        persona='vpcs',
        question="Who's at risk that we haven't intervened on yet?",
        intent="Governance gap detection — which accounts fell through the cracks.",
        must_cite=[
            "specific account names",
            "their risk indicator (signal or health)",
            "duration without intervention (days since last touch)",
        ],
        must_call_tools=['get_at_risk_accounts', 'get_account_journey_timeline', 'search_signals'],
        must_call_at_least=1,
        tone_check="Each account: name, why it's at risk, how long uncovered.",
        anti_hallucination=[
            "no fabricated 'last touch' timestamps",
        ],
    ),
    PersonaQuestion(
        id='vpcs-q05-team-capacity',
        persona='vpcs',
        question="What's our team capacity utilization across all CSMs?",
        intent="Staffing — are we over/under capacity for current load?",
        must_cite=[
            "utilization metric (per CSM or aggregate)",
            "headroom or overflow assessment",
            "specific CSMs above or below threshold",
        ],
        must_call_tools=['get_team_capacity', 'get_csm_scorecard'],
        must_call_at_least=1,
        tone_check="Quantified. % or hours-based; cite recommended CSM count when present.",
        anti_hallucination=[
            "no manufactured capacity benchmarks",
        ],
    ),
    PersonaQuestion(
        id='vpcs-q07-capacity-allocation',
        persona='vpcs',
        question=(
            "Do we have the right number of CSMs, and who are the top performers "
            "on critical-to-expansion playbooks?"
        ),
        intent="Capacity planning and correct allocation — headcount + playbook leaders.",
        must_cite=[
            "current vs recommended CSM count",
            "named top performers",
            "playbook IDs or names tied to expansion/recovery",
        ],
        must_call_tools=['get_team_capacity', 'get_csm_scorecard'],
        must_call_at_least=1,
        tone_check="Staffing recommendation with evidence from scorecard/capacity tools.",
        anti_hallucination=[
            "no invented headcount targets",
            "no fabricated performer names",
        ],
        weight=1.2,
    ),
    PersonaQuestion(
        id='vpcs-q06-early-predictors',
        persona='vpcs',
        question="Which signals have been the strongest early predictors of churn in the last 6 months?",
        intent="Pattern recognition — what should CSMs be watching for?",
        must_cite=[
            "specific signal types (champion_loss, exec_disengage, etc.)",
            "lead time before realized churn",
            "false positive / accuracy implication",
        ],
        must_call_tools=['search_signals', 'analyze_root_cause', 'get_outcome_roi_story'],
        must_call_at_least=1,
        tone_check="Honest about which signals work and which don't.",
        anti_hallucination=[
            "no claimed signal-to-churn lag without supporting data",
        ],
    ),
]
