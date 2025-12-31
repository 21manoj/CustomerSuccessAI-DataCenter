"""
Data Center KPI Definitions - 31 KPIs
Latest framework: Infrastructure(11) + Service(6) + Sentiment(3) + Business(6) + Relationship(5)
"""

DC_KPIS = {
    # PILLAR 1: Infrastructure & Performance (11 KPIs)
    "DC-INF-001": {
        "id": "DC-INF-001",
        "name": "Server Uptime %",
        "pillar": "Infrastructure & Performance",
        "unit": "%",
        "target": 99.9,
        "risk_bands": {"critical": (0, 99), "at_risk": (99, 99.5), "healthy": (99.5, 100)},
        "playbooks": ["churn_prevention", "sla_stabilizer"]
    },
    "DC-INF-002": {
        "id": "DC-INF-002",
        "name": "Network Latency",
        "pillar": "Infrastructure & Performance",
        "unit": "ms",
        "target": 5.0,
        "risk_bands": {"critical": (15, 999), "at_risk": (8, 15), "healthy": (0, 8)}
    },
    "DC-INF-003": {
        "id": "DC-INF-003",
        "name": "Power Utilization %",
        "pillar": "Infrastructure & Performance",
        "unit": "%",
        "target": 70.0,
        "risk_bands": {"critical": (0, 30), "at_risk": (30, 50), "healthy": (50, 85), "expansion": (85, 100)},
        "playbooks": ["expansion", "capacity_optimization"]
    },
    "DC-INF-004": {
        "id": "DC-INF-004",
        "name": "Rack Utilization %",
        "pillar": "Infrastructure & Performance",
        "unit": "%",
        "target": 70.0,
        "risk_bands": {"critical": (0, 40), "at_risk": (40, 60), "healthy": (60, 85), "expansion": (85, 100)},
        "playbooks": ["expansion", "capacity_optimization"]
    },
    "DC-INF-005": {
        "id": "DC-INF-005",
        "name": "Bandwidth Utilization %",
        "pillar": "Infrastructure & Performance",
        "unit": "%",
        "target": 70.0,
        "risk_bands": {"critical": (0, 30), "at_risk": (30, 50), "healthy": (50, 85), "expansion": (85, 100)}
    },
    "DC-INF-006": {"id": "DC-INF-006", "name": "Provisioning Time", "unit": "hours", "target": 8.0, "pillar": "Infrastructure & Performance"},
    "DC-INF-007": {"id": "DC-INF-007", "name": "Backup Success Rate %", "unit": "%", "target": 99.0, "pillar": "Infrastructure & Performance"},
    "DC-INF-008": {"id": "DC-INF-008", "name": "Environmental Alerts", "unit": "count", "target": 5, "pillar": "Infrastructure & Performance"},
    "DC-INF-009": {"id": "DC-INF-009", "name": "Security Incidents", "unit": "count", "target": 0, "pillar": "Infrastructure & Performance"},
    "DC-INF-010": {"id": "DC-INF-010", "name": "Cooling Efficiency (PUE)", "unit": "ratio", "target": 1.5, "pillar": "Infrastructure & Performance"},
    "DC-INF-029": {
        "id": "DC-INF-029",
        "name": "Usage Growth Velocity %",
        "pillar": "Infrastructure & Performance",
        "unit": "%",
        "target": 5.0,
        "is_new": True,
        "risk_bands": {"critical": (-999, -15), "at_risk": (-15, 0), "healthy": (0, 10), "expansion": (10, 999)},
        "playbooks": ["expansion", "churn_prevention", "capacity_optimization"]
    },
    
    # PILLAR 2: Service Delivery (6 KPIs)
    "DC-SVC-011": {"id": "DC-SVC-011", "name": "MTTR", "unit": "hours", "target": 8.0, "pillar": "Service Delivery", "risk_bands": {"critical": (16, 999), "at_risk": (8, 16), "healthy": (0, 8)}},
    "DC-SVC-012": {"id": "DC-SVC-012", "name": "Support Satisfaction", "unit": "score", "target": 4.0, "pillar": "Service Delivery"},
    "DC-SVC-013": {"id": "DC-SVC-013", "name": "Ticket Volume", "unit": "count", "target": 10, "pillar": "Service Delivery"},
    "DC-SVC-014": {"id": "DC-SVC-014", "name": "Customer Effort Score", "unit": "score", "target": 3.0, "pillar": "Service Delivery"},
    "DC-SVC-015": {"id": "DC-SVC-015", "name": "SLA Breach Count", "unit": "count", "target": 0, "pillar": "Service Delivery", "risk_bands": {"critical": (3, 999), "at_risk": (1, 3), "healthy": (0, 1)}, "playbooks": ["sla_stabilizer", "churn_prevention"]},
    "DC-SVC-016": {"id": "DC-SVC-016", "name": "Remote Hands Response Time", "unit": "minutes", "target": 30, "pillar": "Service Delivery"},
    
    # PILLAR 3: Customer Sentiment (3 KPIs)
    "DC-SENT-017": {"id": "DC-SENT-017", "name": "NPS", "unit": "score", "target": 50, "pillar": "Customer Sentiment", "risk_bands": {"critical": (-100, 30), "at_risk": (30, 50), "healthy": (50, 100)}, "playbooks": ["voc", "churn_prevention"]},
    "DC-SENT-018": {"id": "DC-SENT-018", "name": "CSAT", "unit": "score", "target": 4.2, "pillar": "Customer Sentiment"},
    "DC-SENT-019": {"id": "DC-SENT-019", "name": "Complaints", "unit": "count", "target": 2, "pillar": "Customer Sentiment"},
    
    # PILLAR 4: Business Outcomes (6 KPIs)
    "DC-BIZ-020": {"id": "DC-BIZ-020", "name": "CLV", "unit": "$", "target": "3x ARR", "pillar": "Business Outcomes"},
    "DC-BIZ-021": {"id": "DC-BIZ-021", "name": "ROI %", "unit": "%", "target": 200, "pillar": "Business Outcomes"},
    "DC-BIZ-022": {"id": "DC-BIZ-022", "name": "GRR", "unit": "%", "target": 90.0, "pillar": "Business Outcomes", "risk_bands": {"critical": (0, 85), "at_risk": (85, 90), "healthy": (90, 100)}, "playbooks": ["renewal", "churn_prevention"]},
    "DC-BIZ-023": {"id": "DC-BIZ-023", "name": "NRR", "unit": "%", "target": 105.0, "pillar": "Business Outcomes", "risk_bands": {"critical": (0, 95), "at_risk": (95, 105), "healthy": (105, 999)}, "playbooks": ["expansion", "renewal"]},
    "DC-BIZ-030": {"id": "DC-BIZ-030", "name": "Payment Health Score", "unit": "score", "target": 85, "is_new": True, "pillar": "Business Outcomes", "risk_bands": {"critical": (0, 50), "at_risk": (50, 85), "healthy": (85, 100)}, "playbooks": ["churn_prevention"]},
    "DC-BIZ-031": {"id": "DC-BIZ-031", "name": "Service Breadth Score", "unit": "score", "target": 43, "is_new": True, "pillar": "Business Outcomes", "risk_bands": {"critical": (0, 14), "at_risk": (14, 29), "healthy": (29, 57), "expansion": (57, 100)}, "playbooks": ["expansion"]},
    
    # PILLAR 5: Relationship Strength (5 KPIs)
    "DC-REL-024": {"id": "DC-REL-024", "name": "QBR Frequency", "unit": "count", "target": 4, "pillar": "Relationship Strength"},
    "DC-REL-025": {"id": "DC-REL-025", "name": "Account Engagement", "unit": "score", "target": 70, "pillar": "Relationship Strength"},
    "DC-REL-026": {"id": "DC-REL-026", "name": "Executive Engagement", "unit": "score", "target": 60, "pillar": "Relationship Strength"},
    "DC-REL-027": {"id": "DC-REL-027", "name": "Renewal Probability", "unit": "%", "target": 85, "pillar": "Relationship Strength", "risk_bands": {"critical": (0, 60), "at_risk": (60, 85), "healthy": (85, 100)}, "playbooks": ["renewal", "churn_prevention"]},
    "DC-REL-028": {"id": "DC-REL-028", "name": "Multi-Site Deployment", "unit": "count", "target": 2, "pillar": "Relationship Strength"},
}

def get_kpi(kpi_id):
    return DC_KPIS.get(kpi_id)

def get_kpis_by_pillar(pillar):
    return {k: v for k, v in DC_KPIS.items() if v.get("pillar") == pillar}

def calculate_risk_band(kpi_id, value):
    kpi = DC_KPIS.get(kpi_id)
    if not kpi or "risk_bands" not in kpi:
        return "healthy"
    for band, (min_val, max_val) in kpi["risk_bands"].items():
        if min_val <= value < max_val:
            return band
    return "healthy"
