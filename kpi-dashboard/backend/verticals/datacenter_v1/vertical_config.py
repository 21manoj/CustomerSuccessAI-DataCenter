"""DataCenterV1 (GPU-rental neocloud) — playbook configuration.

Mirrors the structure of verticals/dc2_s/vertical_config.py PLAYBOOK_CONFIG so it
is drop-in consumable once the playbook evaluator is made vertical-aware
(playbook_recommendations_api._evaluate_dc2s_playbooks is currently dc2_s-specific
— see docs/GPU_NEOCLOUD_VERTICAL_SPEC.md sec 9.3 #5).

KPI codes reference config/datacenter_v1_kpi_catalog.json:
  P1 Revenue & Unit Economics | P2 Fleet Utilization & Goodput
  P3 Reliability & SLA Delivery | P4 Power & Facility
  P5 Commercial & Expansion | P6 Provisioning Velocity

`signal_triggers` is an optional additive key for signal-driven plays (subtypes
from config/taxonomy_datacenter_v1.json). AND-logic plays are noted in
`trigger_logic` ("AND"/"OR", default OR).
"""

VERTICAL = "datacenter_v1"

# Playbooks that require ALL trigger conditions (AND), else OR (any).
AND_LOGIC_PLAYBOOKS = {"PB-04", "PB-09"}

PLAYBOOK_CONFIG = {
    # ---- Kept / adapted from the base data-center motion ----
    "PB-01": {
        "id": "PB-01",
        "name": "Provisioning Acceleration",
        "description": "Accelerate time-to-first-job for new tenants (adapted from Deployment Acceleration)",
        "trigger_kpis": ["P6-KPI1", "P6-KPI2"],
        "trigger_conditions": {
            "P6-KPI1": {"operator": ">", "value": 48},   # > 48h to first job
            "P6-KPI2": {"operator": ">", "value": 12},   # > 12h provisioning/quota grant
        },
        "trigger_logic": "OR",
        "automation_level": "partial",
        "human_approval_required": False,
        "estimated_impact": "-50% time-to-first-job",
        "power_of_1_lever": "provisioning_velocity",
        "owner_roles": ["solutions_engineer", "csm"],
        "phases": ["deployment"],
        "estimated_duration_display": "3–7 days",
        "sub_components": [
            {"id": "PB-01-S1", "name": "Onboarding review", "description": "Quota, image, and access readiness", "estimated_hours": 6},
            {"id": "PB-01-S2", "name": "Unblock provisioning", "description": "Clear quota/config blockers", "estimated_hours": 16},
            {"id": "PB-01-S3", "name": "First-job validation", "description": "Confirm first workload runs", "estimated_hours": 6},
        ],
    },
    "PB-03": {
        "id": "PB-03",
        "name": "GPU Optimization",
        "description": "Improve GPU utilization and goodput efficiency (tuning, not idle-revenue-risk — see PB-07)",
        "trigger_kpis": ["P2-KPI1", "P2-KPI2"],
        "trigger_conditions": {
            "P2-KPI1": {"operator": "<", "value": 60},   # < 60% allocated utilization
            "P2-KPI2": {"operator": "<", "value": 75},   # < 75% goodput
        },
        "trigger_logic": "OR",
        "automation_level": "medium",
        "human_approval_required": False,
        "estimated_impact": "+25% effective utilization",
        "power_of_1_lever": "utilization_uplift",
        "owner_roles": ["solutions_engineer"],
        "phases": ["performance", "excellence"],
        "estimated_duration_display": "14–21 days",
        "sub_components": [
            {"id": "PB-03-S1", "name": "Utilization/goodput analysis", "description": "Baseline allocated vs effective; find idle gaps", "estimated_hours": 16},
            {"id": "PB-03-S2", "name": "Workload tuning", "description": "Job sizing, batching, scheduling", "estimated_hours": 32},
            {"id": "PB-03-S3", "name": "Re-measure & report", "description": "Confirm goodput improvement", "estimated_hours": 8},
        ],
    },
    "PB-04": {
        "id": "PB-04",
        "name": "Capacity Planning",
        "description": "Forecast capacity and structure reserved-commitment expansion",
        "trigger_kpis": ["P4-KPI1", "P5-KPI3", "P5-KPI4"],
        "trigger_conditions": {
            "P4-KPI1": {"operator": ">", "value": 80},   # > 80% power-capacity utilization
            "P5-KPI3": {"operator": ">", "value": 10},   # > 10% compute-hour growth
            "P5-KPI4": {"operator": ">", "value": 70},   # > 70% expansion probability
        },
        "trigger_logic": "AND",
        "automation_level": "low",
        "human_approval_required": True,
        "estimated_impact": "reserved-commitment expansion (TCV uplift)",
        "power_of_1_lever": "reserved_commitment_coverage",
        "owner_roles": ["account_exec", "capacity_engineer"],
        "phases": ["excellence"],
        "estimated_duration_display": "30–60 days",
        "sub_components": [
            {"id": "PB-04-S1", "name": "Opportunity identification", "description": "Capacity + growth + probability read", "estimated_hours": 24},
            {"id": "PB-04-S2", "name": "Commit proposal", "description": "Reserved-capacity offer & negotiation", "estimated_hours": 40},
            {"id": "PB-04-S3", "name": "Provisioning plan", "description": "Allocation and ramp schedule", "estimated_hours": 16},
        ],
    },
    "PB-05": {
        "id": "PB-05",
        "name": "Health Monitoring",
        "description": "Continuous account-health monitoring and alerting",
        "trigger_kpis": ["OVERALL_HEALTH"],
        "trigger_conditions": {"OVERALL_HEALTH": {"operator": "<", "value": 60}},
        "trigger_logic": "OR",
        "automation_level": "high",
        "human_approval_required": False,
        "estimated_impact": "+15% early-intervention success",
        "power_of_1_lever": "grr",
        "owner_roles": ["csm"],
        "phases": ["deployment", "performance", "excellence"],
        "estimated_duration_display": "7–14 days",
        "sub_components": [
            {"id": "PB-05-S1", "name": "Health triage", "description": "Review drivers of the drop", "estimated_hours": 8},
            {"id": "PB-05-S2", "name": "Action plan", "description": "Assign owner and remediation", "estimated_hours": 16},
            {"id": "PB-05-S3", "name": "Follow-up & re-score", "description": "Verify recovery", "estimated_hours": 8},
        ],
    },
    "PB-06": {
        "id": "PB-06",
        "name": "Customer Engagement",
        "description": "Maintain executive relationships and technical champion engagement",
        "trigger_kpis": ["P5-KPI7"],
        "trigger_conditions": {"P5-KPI7": {"operator": "<", "value": 60}},
        "trigger_logic": "OR",
        "automation_level": "medium",
        "human_approval_required": False,
        "estimated_impact": "+20% champion engagement",
        "power_of_1_lever": "grr",
        "owner_roles": ["csm", "account_exec"],
        "phases": ["excellence"],
        "estimated_duration_display": "30–90 days",
        "sub_components": [
            {"id": "PB-06-S1", "name": "Stakeholder mapping", "description": "Identify champion and exec sponsors", "estimated_hours": 8},
            {"id": "PB-06-S2", "name": "Engagement cadence", "description": "QBRs, roadmap reviews", "estimated_hours": 24},
        ],
    },

    # ---- NEW rental-native rescue/expansion playbooks (spec sec 4.2) ----
    "PB-07": {
        "id": "PB-07",
        "name": "Idle-Reserved-Cluster Rescue",
        "description": "A paid-for reserved cluster sitting idle is a renewal threat — intervene before it becomes a renegotiation.",
        "trigger_kpis": ["P2-KPI4"],
        "trigger_conditions": {"P2-KPI4": {"operator": "<", "value": 40}},  # reserved-cluster util < 40%
        "signal_triggers": ["reserved_cluster_idle", "commitment_ramp_miss"],
        "trigger_logic": "OR",
        "automation_level": "low",
        "human_approval_required": True,
        "estimated_impact": "protect reserved-commitment TCV at renewal",
        "power_of_1_lever": "reserved_commitment_coverage",
        "owner_roles": ["csm", "solutions_engineer"],
        "phases": ["performance", "excellence"],
        "estimated_duration_display": "14–30 days",
        "sub_components": [
            {"id": "PB-07-S1", "name": "Usage review", "description": "Why is the reserved cluster idle?", "estimated_hours": 12},
            {"id": "PB-07-S2", "name": "Workload onboarding", "description": "Help the customer land workloads", "estimated_hours": 32},
            {"id": "PB-07-S3", "name": "Right-size vs renegotiate", "description": "Commercial path + exec align", "estimated_hours": 24},
        ],
    },
    "PB-08": {
        "id": "PB-08",
        "name": "SLA / Goodput-Breach Recovery",
        "description": "Runs keep dying (interruptions / fabric errors) — proactive credits + reliability fix before escalation.",
        "trigger_kpis": ["P3-KPI2", "P3-KPI4"],
        "trigger_conditions": {
            "P3-KPI2": {"operator": ">", "value": 5},    # interruption rate > 5%
            "P3-KPI4": {"operator": ">", "value": 5},    # fabric errors/hr > 5
        },
        "signal_triggers": ["reliability_sla_breach", "job_preemption_complaint", "interconnect_bottleneck"],
        "trigger_logic": "OR",
        "automation_level": "high",
        "human_approval_required": False,
        "estimated_impact": "churn averted + SLA credits avoided",
        "power_of_1_lever": "goodput_sla_credit_avoided",
        "owner_roles": ["reliability_engineer", "csm"],
        "phases": ["performance"],
        "estimated_duration_display": "3–10 days",
        "sub_components": [
            {"id": "PB-08-S1", "name": "Incident RCA", "description": "Root-cause interruptions/fabric faults", "estimated_hours": 16},
            {"id": "PB-08-S2", "name": "Proactive credits + comms", "description": "Own it with the customer", "estimated_hours": 8},
            {"id": "PB-08-S3", "name": "Reliability fix", "description": "Remediate + verify goodput restored", "estimated_hours": 32},
        ],
    },
    "PB-09": {
        "id": "PB-09",
        "name": "Power & Thermal Headroom",
        "description": "Approaching MW/cooling limits or rising stranded power — protect sellable capacity, avoid declined expansion.",
        "trigger_kpis": ["P4-KPI1", "P4-KPI2"],
        "trigger_conditions": {
            "P4-KPI1": {"operator": ">", "value": 90},   # power-capacity util > 90%
            "P4-KPI2": {"operator": ">", "value": 20},   # stranded power > 20%
        },
        "signal_triggers": ["power_capacity_constraint", "thermal_event"],
        "trigger_logic": "AND",
        "automation_level": "low",
        "human_approval_required": True,
        "estimated_impact": "protect sellable MW / avoid declined expansion",
        "power_of_1_lever": "power_passthrough_margin",
        "owner_roles": ["capacity_engineer", "facility"],
        "phases": ["performance", "excellence"],
        "estimated_duration_display": "14–45 days",
        "sub_components": [
            {"id": "PB-09-S1", "name": "Capacity plan", "description": "MW/cooling headroom modeling", "estimated_hours": 24},
            {"id": "PB-09-S2", "name": "Remediation / rebalance", "description": "Cooling fix or allocation rebalance", "estimated_hours": 40},
        ],
    },
    "PB-10": {
        "id": "PB-10",
        "name": "Silicon-Refresh Upsell",
        "description": "H100 customer + newer generation available (H200/GB200) — migration offer for retention + expansion.",
        "trigger_kpis": ["P5-KPI5"],
        "trigger_conditions": {"P5-KPI5": {"operator": ">", "value": 60}},  # refresh readiness
        "signal_triggers": ["silicon_refresh_interest"],
        "trigger_logic": "OR",
        "automation_level": "low",
        "human_approval_required": False,
        "estimated_impact": "expansion / NRR uplift",
        "power_of_1_lever": "reserved_commitment_coverage",
        "owner_roles": ["account_exec", "solutions_engineer"],
        "phases": ["excellence"],
        "estimated_duration_display": "30–60 days",
        "sub_components": [
            {"id": "PB-10-S1", "name": "Migration offer", "description": "Benchmark + commercial", "estimated_hours": 24},
            {"id": "PB-10-S2", "name": "Commit uplift", "description": "New-gen reservation close", "estimated_hours": 24},
        ],
    },
    "PB-11": {
        "id": "PB-11",
        "name": "Funding-Triggered Expansion",
        "description": "Customer raised a round — pre-allocate capacity and land the expansion ahead of the training scale-up.",
        "trigger_kpis": [],
        "signal_triggers": ["funding_raised"],
        "trigger_logic": "OR",
        "automation_level": "low",
        "human_approval_required": False,
        "estimated_impact": "expansion (net-new reserved capacity)",
        "power_of_1_lever": "reserved_commitment_coverage",
        "owner_roles": ["account_exec", "csm"],
        "phases": ["excellence"],
        "estimated_duration_display": "14–45 days",
        "sub_components": [
            {"id": "PB-11-S1", "name": "Capacity pre-allocation", "description": "Reserve ahead of ramp", "estimated_hours": 16},
            {"id": "PB-11-S2", "name": "Commit upsell", "description": "Roadmap-aligned expansion", "estimated_hours": 24},
        ],
    },
    "PB-12": {
        "id": "PB-12",
        "name": "Runway / Collections Guard",
        "description": "Short runway or late payment — right-size, restructure to prepay/commit, and protect revenue against default.",
        "trigger_kpis": ["P5-KPI6"],
        "trigger_conditions": {"P5-KPI6": {"operator": "<", "value": 6}},  # runway < 6 months
        "signal_triggers": ["runway_risk", "payment_delinquency"],
        "trigger_logic": "OR",
        "automation_level": "low",
        "human_approval_required": True,
        "estimated_impact": "protect revenue / reduce bad debt",
        "power_of_1_lever": "grr",
        "owner_roles": ["csm", "finance"],
        "phases": ["performance", "excellence"],
        "estimated_duration_display": "7–30 days",
        "sub_components": [
            {"id": "PB-12-S1", "name": "Right-size", "description": "Match commit to real consumption", "estimated_hours": 12},
            {"id": "PB-12-S2", "name": "Restructure / collections", "description": "Prepay/commit or collections workflow", "estimated_hours": 16},
        ],
    },
    "PB-13": {
        "id": "PB-13",
        "name": "Competitive Price-Defense",
        "description": "Spot-price pressure or a competitor capacity offer — respond with price/commit levers + technical proof (goodput, fabric).",
        "trigger_kpis": ["P1-KPI1"],
        "trigger_conditions": {"P1-KPI1": {"operator": "<", "value": 1.8}},  # realized $/gpu-hr eroding
        "signal_triggers": ["spot_price_pressure", "competitor_capacity_offer", "multicloud_diversification"],
        "trigger_logic": "OR",
        "automation_level": "low",
        "human_approval_required": True,
        "estimated_impact": "churn averted / retention",
        "power_of_1_lever": "utilization_uplift",
        "owner_roles": ["account_exec", "pricing"],
        "phases": ["performance", "excellence"],
        "estimated_duration_display": "7–21 days",
        "sub_components": [
            {"id": "PB-13-S1", "name": "Price/commit response", "description": "Structured counter within guardrails", "estimated_hours": 16},
            {"id": "PB-13-S2", "name": "Technical proof", "description": "Goodput/fabric benchmark vs competitor", "estimated_hours": 24},
        ],
    },
}
