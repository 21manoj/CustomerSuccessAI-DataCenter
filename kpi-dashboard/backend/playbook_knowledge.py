"""
Playbook Knowledge Base
Defines the 5 system playbooks for RAG to reference
"""

SYSTEM_PLAYBOOKS = {
    "voc-sprint": {
        "id": "voc-sprint",
        "name": "VoC Sprint",
        "icon": "🎤",
        "description": "4-week intensive Voice of Customer program to surface value gaps and convert feedback to executive-backed actions",
        "improves_kpis": [
            "Net Promoter Score (NPS)",
            "Customer Satisfaction (CSAT)",
            "Customer Complaints",
            "Churn Risk Flags Triggered",
            "Product Feedback Score"
        ],
        "triggers": {
            "nps_threshold": "< 10",
            "csat_threshold": "< 3.6",
            "churn_risk_threshold": "≥ 30%",
            "health_drop_threshold": "≥ 10 points"
        },
        "duration": "30 days",
        "outcomes": [
            "NPS improvement of 10-20 points",
            "CSAT increase of 0.5-1.0 points",
            "Top 5 customer themes identified",
            "Executive sponsor alignment",
            "3 fastest value actions with owners"
        ],
        "use_cases": [
            "Low NPS or CSAT scores",
            "High churn risk",
            "Customer complaints increasing",
            "Sentiment declining"
        ]
    },
    
    "activation-blitz": {
        "id": "activation-blitz",
        "name": "Activation Blitz",
        "icon": "🚀",
        "description": "4-week activation program to compress time-to-value and drive user engagement for low-adoption accounts",
        "improves_kpis": [
            "Product Activation Rate",
            "Feature Adoption Rate",
            "Active User Growth",
            "Time to First Value (TTFV)",
            "Onboarding Completion Rate",
            "Daily Active Users (DAU)",
            "Monthly Active Users (MAU)",
            "Feature Utilization Rate"
        ],
        "triggers": {
            "adoption_index": "< 60",
            "active_users": "< 50",
            "dau_mau_ratio": "< 25%",
            "feature_adoption": "< 40%"
        },
        "duration": "30 days",
        "outcomes": [
            "20-30% increase in active users",
            "15-25% improvement in feature adoption",
            "Onboarding completion rate > 80%",
            "Time to value reduced by 40%"
        ],
        "use_cases": [
            "Low product adoption",
            "Few active users",
            "Poor feature utilization",
            "Slow onboarding",
            "Low engagement"
        ]
    },
    
    "sla-stabilizer": {
        "id": "sla-stabilizer",
        "name": "SLA Stabilizer",
        "icon": "⚡",
        "description": "Rapid SLA recovery and process stabilization program for accounts with support issues",
        "improves_kpis": [
            "First Response Time",
            "Mean Time to Resolution (MTTR)",
            "SLA Adherence",
            "Ticket Volume",
            "Customer Support Satisfaction",
            "Escalation Rate",
            "Ticket Reopen Rate"
        ],
        "triggers": {
            "sla_breaches": "> 5 per month",
            "response_time": "> 2x target",
            "escalations": "increasing trend",
            "reopen_rate": "> 20%"
        },
        "duration": "14-21 days",
        "outcomes": [
            "90%+ SLA compliance restored",
            "Response time reduced by 50%",
            "Escalations reduced by 70%",
            "Customer support satisfaction improved"
        ],
        "use_cases": [
            "Multiple SLA breaches",
            "Slow support response",
            "High escalation rate",
            "Support satisfaction declining",
            "Ticket volume increasing"
        ]
    },
    
    "renewal-safeguard": {
        "id": "renewal-safeguard",
        "name": "Renewal Safeguard",
        "icon": "🛡️",
        "description": "90-day proactive renewal risk mitigation and value demonstration program",
        "improves_kpis": [
            "Net Revenue Retention (NRR)",
            "Gross Revenue Retention (GRR)",
            "Churn Risk Flags Triggered",
            "Account Engagement Score",
            "Executive Sponsor Engagement",
            "Business Review Frequency",
            "Customer Lifetime Value (CLV)"
        ],
        "triggers": {
            "renewal_window": "< 90 days",
            "health_score": "< 70",
            "engagement": "declining",
            "champion_status": "departed or at risk"
        },
        "duration": "90 days",
        "outcomes": [
            "Renewal probability increased by 25-40%",
            "Health score improved to > 75",
            "Executive sponsor re-engaged",
            "Value demonstration completed",
            "Renewal committed or signed"
        ],
        "use_cases": [
            "Renewal within 90 days with low health",
            "Champion departed",
            "Engagement declining",
            "Value not demonstrated",
            "At-risk renewal"
        ]
    },
    
    "expansion-timing": {
        "id": "expansion-timing",
        "name": "Expansion Timing",
        "icon": "📈",
        "description": "Strategic expansion opportunity identification and optimal timing program for healthy accounts",
        "improves_kpis": [
            "Upsell and Cross-sell Revenue",
            "Expansion Revenue Rate",
            "Revenue Growth",
            "Customer Lifetime Value (CLV)",
            "Net Revenue Retention (NRR)",
            "Account Expansion Velocity"
        ],
        "triggers": {
            "health_score": "> 80",
            "adoption": "> 85%",
            "usage": "> 80% of license",
            "budget_window": "open (Q1 or Q4)",
            "champion_strength": "strong"
        },
        "duration": "60-90 days",
        "outcomes": [
            "Expansion opportunity identified",
            "Business case developed",
            "30-50% ARR increase",
            "New use cases activated",
            "Multi-year commitment secured"
        ],
        "use_cases": [
            "High health score (> 80)",
            "High adoption and usage",
            "Strong champion relationship",
            "Budget available",
            "Expansion signals detected"
        ]
    }
}


def get_playbook_recommendations_for_kpi(kpi_name: str) -> list:
    """
    Given a KPI name, return which playbooks can improve it
    """
    recommendations = []
    
    kpi_lower = kpi_name.lower()
    
    for playbook_id, playbook in SYSTEM_PLAYBOOKS.items():
        # Check if this playbook improves the KPI
        for improved_kpi in playbook['improves_kpis']:
            if improved_kpi.lower() in kpi_lower or kpi_lower in improved_kpi.lower():
                recommendations.append({
                    'playbook_id': playbook_id,
                    'playbook_name': playbook['name'],
                    'icon': playbook['icon'],
                    'description': playbook['description'],
                    'expected_improvement': f"Improves {improved_kpi}",
                    'duration': playbook['duration'],
                    'outcomes': playbook['outcomes'][:2]  # Top 2 outcomes
                })
                break
    
    return recommendations


def get_playbook_for_goal(goal: str) -> list:
    """
    Given a business goal (like "improve NRR"), return relevant playbooks
    """
    recommendations = []
    goal_lower = goal.lower()
    
    # Map common goals to KPIs
    goal_to_kpis = {
        'nrr': ['Net Revenue Retention', 'Gross Revenue Retention', 'Expansion Revenue'],
        'revenue': ['Revenue Growth', 'Upsell', 'Cross-sell', 'NRR', 'CLV'],
        'retention': ['Churn Risk', 'NRR', 'GRR', 'Engagement'],
        'adoption': ['Product Activation', 'Feature Adoption', 'Active Users', 'Onboarding'],
        'satisfaction': ['NPS', 'CSAT', 'Complaints', 'Support Satisfaction'],
        'support': ['Response Time', 'MTTR', 'SLA', 'Ticket', 'Escalation'],
        'engagement': ['Active Users', 'Engagement Score', 'Usage', 'Feature Adoption'],
        'expansion': ['Expansion Revenue', 'Upsell', 'Cross-sell', 'CLV']
    }
    
    # Find matching playbooks
    for keyword, kpi_keywords in goal_to_kpis.items():
        if keyword in goal_lower:
            for playbook_id, playbook in SYSTEM_PLAYBOOKS.items():
                # Check if playbook improves related KPIs
                for kpi_keyword in kpi_keywords:
                    for improved_kpi in playbook['improves_kpis']:
                        if kpi_keyword.lower() in improved_kpi.lower():
                            if playbook_id not in [r['playbook_id'] for r in recommendations]:
                                recommendations.append({
                                    'playbook_id': playbook_id,
                                    'playbook_name': playbook['name'],
                                    'icon': playbook['icon'],
                                    'description': playbook['description'],
                                    'improves': playbook['improves_kpis'],
                                    'duration': playbook['duration'],
                                    'key_outcomes': playbook['outcomes'][:3]
                                })
                            break
    
    return recommendations


def format_playbook_knowledge_for_rag() -> str:
    """
    Format playbook knowledge for RAG context
    """
    context = "\n\n=== SYSTEM-DEFINED PLAYBOOKS ===\n"
    context += "The platform has 5 pre-built playbooks available:\n\n"
    
    for playbook_id, playbook in SYSTEM_PLAYBOOKS.items():
        context += f"{playbook['icon']} **{playbook['name']}** ({playbook['duration']})\n"
        context += f"   Purpose: {playbook['description']}\n"
        context += f"   Improves: {', '.join(playbook['improves_kpis'][:5])}\n"
        if len(playbook['improves_kpis']) > 5:
            context += f"   ... and {len(playbook['improves_kpis']) - 5} more KPIs\n"
        context += f"   Triggers: {', '.join([f'{k}={v}' for k,v in list(playbook['triggers'].items())[:2]])}\n"
        context += "\n"
    
    context += "Always recommend these system playbooks instead of generic ones.\n"
    return context

