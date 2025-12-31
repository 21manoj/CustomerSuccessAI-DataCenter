"""
Data Center Playbooks Definitions
DC-specific playbooks for infrastructure and service management
"""

DC_PLAYBOOKS = {
    "churn_prevention": {
        "id": "churn_prevention",
        "name": "Churn Prevention",
        "description": "Prevent customer churn through proactive intervention",
        "triggers": {
            "health_score": {"operator": "<", "value": 50},
            "nps": {"operator": "<", "value": 30},
            "sla_breaches": {"operator": ">", "value": 3}
        },
        "steps": [
            {"id": 1, "action": "Identify at-risk accounts", "duration": 1},
            {"id": 2, "action": "Schedule executive check-in", "duration": 2},
            {"id": 3, "action": "Implement remediation plan", "duration": 7}
        ]
    },
    "sla_stabilizer": {
        "id": "sla_stabilizer",
        "name": "SLA Stabilizer",
        "description": "Rapid SLA recovery and process stabilization",
        "triggers": {
            "sla_breach_count": {"operator": ">", "value": 5},
            "mttr": {"operator": ">", "value": 16}
        },
        "steps": [
            {"id": 1, "action": "Audit SLA breaches", "duration": 1},
            {"id": 2, "action": "Implement escalation procedures", "duration": 2},
            {"id": 3, "action": "Monitor and report", "duration": 7}
        ]
    },
    "expansion": {
        "id": "expansion",
        "name": "Expansion Opportunity",
        "description": "Identify and pursue expansion opportunities",
        "triggers": {
            "power_utilization": {"operator": ">", "value": 85},
            "rack_utilization": {"operator": ">", "value": 85},
            "usage_growth_velocity": {"operator": ">", "value": 10}
        },
        "steps": [
            {"id": 1, "action": "Identify capacity constraints", "duration": 1},
            {"id": 2, "action": "Propose expansion plan", "duration": 3},
            {"id": 3, "action": "Execute expansion", "duration": 14}
        ]
    },
    "capacity_optimization": {
        "id": "capacity_optimization",
        "name": "Capacity Optimization",
        "description": "Optimize infrastructure capacity utilization",
        "triggers": {
            "power_utilization": {"operator": "<", "value": 50},
            "rack_utilization": {"operator": "<", "value": 50}
        },
        "steps": [
            {"id": 1, "action": "Analyze utilization patterns", "duration": 2},
            {"id": 2, "action": "Recommend optimization", "duration": 3},
            {"id": 3, "action": "Implement changes", "duration": 7}
        ]
    },
    "voc": {
        "id": "voc",
        "name": "Voice of Customer",
        "description": "Collect and act on customer feedback",
        "triggers": {
            "nps": {"operator": "<", "value": 30},
            "csat": {"operator": "<", "value": 3.6}
        },
        "steps": [
            {"id": 1, "action": "Conduct customer interviews", "duration": 3},
            {"id": 2, "action": "Analyze feedback themes", "duration": 2},
            {"id": 3, "action": "Implement improvements", "duration": 7}
        ]
    },
    "renewal": {
        "id": "renewal",
        "name": "Renewal Safeguard",
        "description": "Ensure successful contract renewals",
        "triggers": {
            "renewal_probability": {"operator": "<", "value": 85},
            "grr": {"operator": "<", "value": 90}
        },
        "steps": [
            {"id": 1, "action": "Assess renewal risk", "duration": 1},
            {"id": 2, "action": "Develop renewal strategy", "duration": 3},
            {"id": 3, "action": "Execute renewal plan", "duration": 14}
        ]
    }
}

def get_playbook(playbook_id):
    return DC_PLAYBOOKS.get(playbook_id)

def get_playbooks_by_trigger(kpi_id, value):
    """Get playbooks triggered by a KPI value"""
    from kpi_definitions_dc import get_kpi
    kpi = get_kpi(kpi_id)
    if not kpi:
        return []
    
    triggered_playbooks = []
    for playbook_id in kpi.get("playbooks", []):
        playbook = DC_PLAYBOOKS.get(playbook_id)
        if playbook:
            triggered_playbooks.append(playbook)
    
    return triggered_playbooks

