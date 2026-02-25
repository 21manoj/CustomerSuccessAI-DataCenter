#!/usr/bin/env python3
"""
RAG Query Templates for Load Testing

20 natural language queries spanning different intent categories:
  - Health overview (5)
  - KPI deep-dive (4)
  - Trend analysis (3)
  - Comparative (3)
  - Actionable recommendations (3)
  - Playbook/signal context (2)

Placeholders:
  {account_name} — Replaced with actual account name
  {kpi_name} — Replaced with actual KPI name
  {pillar_name} — Replaced with pillar name
  {time_period} — Replaced with date range
"""

# ================================================================
# HEALTH OVERVIEW QUERIES
# ================================================================
HEALTH_QUERIES = [
    "What is the current health score for {account_name}?",
    "Give me a summary of {account_name}'s overall health across all pillars.",
    "Which accounts are currently in critical health status?",
    "List the top 5 healthiest accounts and their scores.",
    "Which accounts have dropped below 60 health score this month?",
]

# ================================================================
# KPI DEEP-DIVE QUERIES
# ================================================================
KPI_QUERIES = [
    "What is the current value of {kpi_name} for {account_name}?",
    "Show me all KPI scores for {account_name} in the {pillar_name} pillar.",
    "Which KPIs are below target for {account_name}?",
    "What are the worst-performing KPIs across all accounts?",
]

# ================================================================
# TREND ANALYSIS QUERIES
# ================================================================
TREND_QUERIES = [
    "How has {account_name}'s health score changed over the last 6 months?",
    "Show me the trend for {kpi_name} across all accounts over {time_period}.",
    "Which accounts have shown the most improvement in the last quarter?",
]

# ================================================================
# COMPARATIVE QUERIES
# ================================================================
COMPARATIVE_QUERIES = [
    "Compare the health scores of our top 3 accounts vs bottom 3.",
    "How does {account_name} compare to the portfolio average?",
    "Which pillar has the widest gap between best and worst accounts?",
]

# ================================================================
# ACTIONABLE RECOMMENDATION QUERIES
# ================================================================
ACTION_QUERIES = [
    "What actions should we take for {account_name} given their current health?",
    "Which accounts need immediate intervention and why?",
    "What playbook should we run for accounts with declining GPU utilization?",
]

# ================================================================
# PLAYBOOK / SIGNAL CONTEXT QUERIES
# ================================================================
PLAYBOOK_QUERIES = [
    "What playbooks have been triggered for {account_name} recently?",
    "Are there any churn signals detected across the portfolio?",
]

# ================================================================
# ALL QUERIES (combined)
# ================================================================
ALL_QUERIES = (
    HEALTH_QUERIES
    + KPI_QUERIES
    + TREND_QUERIES
    + COMPARATIVE_QUERIES
    + ACTION_QUERIES
    + PLAYBOOK_QUERIES
)


def get_queries_for_account(
    account_name: str,
    kpi_name: str = "GPU Utilization Rate",
    pillar_name: str = "AI Workload Performance",
    time_period: str = "the last 12 months",
    num_queries: int = 5
) -> list:
    """
    Get a set of queries with placeholders filled in

    Args:
        account_name: Real account name
        kpi_name: KPI to query about
        pillar_name: Pillar to query about
        time_period: Time range string
        num_queries: How many queries to return (random selection)

    Returns:
        List of query strings
    """
    import random

    filled = []
    for q in ALL_QUERIES:
        filled.append(
            q.replace('{account_name}', account_name)
             .replace('{kpi_name}', kpi_name)
             .replace('{pillar_name}', pillar_name)
             .replace('{time_period}', time_period)
        )

    return random.sample(filled, min(num_queries, len(filled)))


# KPI names for substitution
KPI_NAMES = [
    "GPU Utilization Rate",
    "AI Job Completion Rate",
    "Partner Engagement Score",
    "Deployment Velocity",
    "Uptime SLA Compliance",
    "Mean Time to Recovery",
    "Capacity Utilization",
    "Expansion Pipeline Score",
    "Configuration Accuracy",
    "Channel Revenue Contribution",
]

PILLAR_NAMES = [
    "AI Workload Performance",
    "Operational Stability",
    "Deployment Velocity",
    "Channel & Partner Health",
    "Expansion Readiness",
]
