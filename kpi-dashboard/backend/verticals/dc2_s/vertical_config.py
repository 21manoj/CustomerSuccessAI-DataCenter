#!/usr/bin/env python3
"""
DC2_S Vertical - Configuration
Vertical-specific settings for data center hardware infrastructure

Defines:
- Partner tier access levels
- Customer journey phases
- Playbook mappings
- Alert thresholds
- Integration settings
"""

from typing import Dict, Any, List, Optional
from enum import Enum

# ============================================================
# PARTNER TIERS & ACCESS CONTROL
# ============================================================

class PartnerTier(Enum):
    """Partner access tiers"""
    INTERNAL = "supermicro_internal"
    PARTNER = "partner"
    VAR = "var"

PARTNER_TIER_CONFIG = {
    "supermicro_internal": {
        "name": "Internal (Supermicro)",
        "access_level": "full",
        "can_edit_accounts": True,
        "can_view_all_data": True,
        "can_execute_playbooks": True,
        "can_modify_kpis": True,
        "dashboards": ["all"],
        "api_access": True,
        "google_sheets_access": "edit",
        "description": "Full internal access for Supermicro employees"
    },
    "partner": {
        "name": "Tier 1 Partner",
        "access_level": "read_write",
        "can_edit_accounts": False,
        "can_view_all_data": True,  # Can see all portfolio data
        "can_execute_playbooks": False,
        "can_modify_kpis": False,
        "dashboards": ["portfolio_health", "expansion_pipeline", "partner_performance"],
        "api_access": False,
        "google_sheets_access": "view",
        "description": "Strategic partners with portfolio visibility"
    },
    "var": {
        "name": "VAR (Value-Added Reseller)",
        "access_level": "read_only_filtered",
        "can_edit_accounts": False,
        "can_view_all_data": False,  # Only their assigned accounts
        "can_execute_playbooks": False,
        "can_modify_kpis": False,
        "dashboards": ["account_health", "deployment_status"],
        "api_access": False,
        "google_sheets_access": "view_filtered",  # Only their accounts
        "description": "VARs see only their assigned customer accounts"
    }
}

def get_partner_permissions(tier: str) -> Dict[str, Any]:
    """Get permissions for a partner tier"""
    return PARTNER_TIER_CONFIG.get(tier, {})

def can_access_resource(tier: str, resource_type: str) -> bool:
    """Check if tier can access a resource type"""
    config = PARTNER_TIER_CONFIG.get(tier, {})
    
    if resource_type == "all_accounts":
        return config.get("can_view_all_data", False)
    elif resource_type == "execute_playbooks":
        return config.get("can_execute_playbooks", False)
    elif resource_type == "api":
        return config.get("api_access", False)
    
    return False

# ============================================================
# CUSTOMER JOURNEY PHASES
# ============================================================

class CustomerPhase(Enum):
    """DC2_S customer journey phases"""
    DEPLOYMENT = "deployment"
    PERFORMANCE = "performance"
    EXCELLENCE = "excellence"

PHASE_CONFIG = {
    "deployment": {
        "name": "Deployment Phase",
        "description": "Initial hardware deployment and configuration",
        "typical_duration_days": 90,
        "focus_pillars": ["P1"],  # Deployment Velocity
        "key_kpis": ["P1-KPI1", "P1-KPI2", "P1-KPI4"],  # Time-to-first-workload, installation rate, cycle time
        "success_criteria": {
            "P1-KPI1": {"operator": "<", "value": 14},  # < 14 days to first workload
            "P1-KPI2": {"operator": ">", "value": 90},  # > 90% installation completion
        },
        "playbooks": ["PB-01"],  # Deployment Acceleration
        "next_phase": "performance"
    },
    "performance": {
        "name": "Performance Phase",
        "description": "Optimize workload performance and stability",
        "typical_duration_days": 180,
        "focus_pillars": ["P2", "P3"],  # Operational Stability + AI Workload Performance
        "key_kpis": ["P2-KPI1", "P2-KPI2", "P3-KPI1", "P3-KPI2"],  # RMA rate, MTBF, GPU utilization, job completion
        "success_criteria": {
            "P2-KPI1": {"operator": "<", "value": 2.6},  # < 2.6% RMA rate
            "P3-KPI1": {"operator": ">", "value": 65},   # > 65% GPU utilization
        },
        "playbooks": ["PB-02", "PB-03", "PB-05"],  # RMA Prevention, GPU Optimization, Health Monitoring
        "next_phase": "excellence"
    },
    "excellence": {
        "name": "Excellence Phase",
        "description": "Maximize efficiency and drive expansion",
        "typical_duration_days": 365,  # Ongoing
        "focus_pillars": ["P4", "P5"],  # Channel Health + Expansion Readiness
        "key_kpis": ["P4-KPI1", "P5-KPI2", "P5-KPI7"],  # Partner engagement, capacity trajectory, expansion probability
        "success_criteria": {
            "P5-KPI2": {"operator": ">", "value": 5},   # > 5% MoM capacity growth
            "P5-KPI7": {"operator": ">", "value": 50},  # > 50% expansion probability
        },
        "playbooks": ["PB-04", "PB-06"],  # Capacity Planning, Customer Engagement
        "next_phase": None  # Final phase (or expansion/renewal)
    }
}

def get_phase_info(phase: str) -> Dict[str, Any]:
    """Get configuration for a customer phase"""
    return PHASE_CONFIG.get(phase, {})

def determine_customer_phase(account_data: Dict[str, Any]) -> str:
    """
    Determine customer phase based on account data
    
    Args:
        account_data: Account metadata dict
        
    Returns:
        Phase identifier
    """
    # Check metadata first
    if "phase" in account_data:
        return account_data["phase"]
    
    # Otherwise infer from deployment date and KPIs
    days_since_deployment = account_data.get("days_since_deployment", 0)
    
    if days_since_deployment < 90:
        return "deployment"
    elif days_since_deployment < 270:
        return "performance"
    else:
        return "excellence"

# ============================================================
# PLAYBOOK CONFIGURATION
# ============================================================

PLAYBOOK_CONFIG = {
    "PB-01": {
        "id": "PB-01",
        "name": "Deployment Acceleration",
        "description": "Accelerate time-to-first-workload for new deployments",
        "trigger_kpis": ["P1-KPI1", "P1-KPI4"],  # TTFV, Deployment Cycle Time
        "trigger_conditions": {
            "P1-KPI1": {"operator": ">", "value": 20},  # > 20 days to first workload
            "P1-KPI4": {"operator": ">", "value": 35},  # > 35 day deployment cycle
        },
        "automation_level": "partial",
        "human_approval_required": False,
        "estimated_impact": "+30% deployment velocity",
        "phases": ["deployment"],
        "estimated_duration_days": 21,
        "estimated_duration_display": "14–21 days",
        "sub_components": [
            {"id": "PB-01-S1", "name": "Kickoff & assessment", "description": "Stakeholder alignment, bottleneck identification", "estimated_hours": 8},
            {"id": "PB-01-S2", "name": "Milestone tracking setup", "description": "Track TTFV and cycle time; assign owners", "estimated_hours": 16},
            {"id": "PB-01-S3", "name": "Unblock & escalation", "description": "Remove blockers (parts, access, approvals)", "estimated_hours": 40},
            {"id": "PB-01-S4", "name": "Go-live validation", "description": "First workload verification and sign-off", "estimated_hours": 8},
        ],
    },
    "PB-02": {
        "id": "PB-02",
        "name": "RMA Prevention",
        "description": "Proactive hardware failure prevention and RMA reduction",
        "trigger_kpis": ["P2-KPI1", "P2-KPI2"],  # RMA rate, MTBF
        "trigger_conditions": {
            "P2-KPI1": {"operator": ">", "value": 2.6},  # > 2.6% RMA rate (CRITICAL)
            "P2-KPI2": {"operator": "<", "value": 4380},  # < 6 months MTBF
        },
        "automation_level": "high",
        "human_approval_required": False,
        "estimated_impact": "-40% RMA rate, $4.4M saved per 1% reduction",
        "phases": ["performance", "excellence"],
        "estimated_duration_days": 14,
        "estimated_duration_display": "7–14 days",
        "sub_components": [
            {"id": "PB-02-S1", "name": "Triage & root-cause analysis", "description": "RMA batch analysis, thermal and component review", "estimated_hours": 24},
            {"id": "PB-02-S2", "name": "Remediation plan", "description": "Firmware, cooling, or batch replacement actions", "estimated_hours": 16},
            {"id": "PB-02-S3", "name": "Execution & monitoring", "description": "Apply fixes; monitor RMA and MTBF", "estimated_hours": 40},
            {"id": "PB-02-S4", "name": "Verification & close-out", "description": "Confirm RMA rate improvement; document learnings", "estimated_hours": 8},
        ],
    },
    "PB-03": {
        "id": "PB-03",
        "name": "GPU Optimization",
        "description": "Improve GPU utilization and workload efficiency",
        "trigger_kpis": ["P3-KPI1", "P3-KPI5"],  # GPU utilization, GPU memory efficiency
        "trigger_conditions": {
            "P3-KPI1": {"operator": "<", "value": 60},  # < 60% GPU utilization
            "P3-KPI5": {"operator": "<", "value": 75},  # < 75% memory efficiency
        },
        "automation_level": "medium",
        "human_approval_required": False,
        "estimated_impact": "+25% GPU utilization",
        "phases": ["performance", "excellence"],
        "estimated_duration_days": 21,
        "estimated_duration_display": "14–21 days",
        "sub_components": [
            {"id": "PB-03-S1", "name": "Utilization analysis", "description": "Baseline GPU and memory utilization; identify gaps", "estimated_hours": 16},
            {"id": "PB-03-S2", "name": "Workload tuning", "description": "Job sizing, batching, and memory optimization", "estimated_hours": 32},
            {"id": "PB-03-S3", "name": "Scheduling improvements", "description": "Queue and scheduler configuration", "estimated_hours": 24},
            {"id": "PB-03-S4", "name": "Re-measure & report", "description": "Post-optimization metrics and recommendations", "estimated_hours": 8},
        ],
    },
    "PB-04": {
        "id": "PB-04",
        "name": "Capacity Planning",
        "description": "Identify expansion opportunities and forecast capacity needs",
        "trigger_kpis": ["P5-KPI1", "P5-KPI2", "P5-KPI7"],  # Capacity utilization, trajectory, expansion probability
        "trigger_conditions": {
            "P5-KPI1": {"operator": ">", "value": 80},  # > 80% capacity utilization
            "P5-KPI2": {"operator": ">", "value": 10},  # > 10% MoM growth
            "P5-KPI7": {"operator": ">", "value": 70},  # > 70% expansion probability
        },
        "automation_level": "low",
        "human_approval_required": True,  # High-value decision
        "estimated_impact": "$4.8M avg Phase 2 expansion ARR",
        "phases": ["excellence"],
        "estimated_duration_days": 60,
        "estimated_duration_display": "30–60 days",
        "sub_components": [
            {"id": "PB-04-S1", "name": "Opportunity identification", "description": "Capacity and growth analysis; expansion scoring", "estimated_hours": 24},
            {"id": "PB-04-S2", "name": "Value proposition development", "description": "ROI and business case for Phase 2", "estimated_hours": 40},
            {"id": "PB-04-S3", "name": "Executive alignment", "description": "Stakeholder and sponsor alignment; approval path", "estimated_hours": 24},
            {"id": "PB-04-S4", "name": "Proposal & negotiation", "description": "Pricing, terms, and contract discussion", "estimated_hours": 40},
            {"id": "PB-04-S5", "name": "Implementation planning", "description": "Rollout timeline and success criteria", "estimated_hours": 16},
        ],
    },
    "PB-05": {
        "id": "PB-05",
        "name": "Health Monitoring",
        "description": "Continuous health score monitoring and alert generation",
        "trigger_kpis": ["OVERALL_HEALTH"],  # Overall health score
        "trigger_conditions": {
            "OVERALL_HEALTH": {"operator": "<", "value": 60},  # < 60 health score
        },
        "automation_level": "high",
        "human_approval_required": False,
        "estimated_impact": "+15% early intervention success rate",
        "phases": ["deployment", "performance", "excellence"],  # All phases
        "estimated_duration_days": 14,
        "estimated_duration_display": "7–14 days",
        "sub_components": [
            {"id": "PB-05-S1", "name": "Health review & triage", "description": "Review pillar scores and root causes", "estimated_hours": 8},
            {"id": "PB-05-S2", "name": "Action plan", "description": "Prioritized actions and owners", "estimated_hours": 16},
            {"id": "PB-05-S3", "name": "Intervention execution", "description": "Execute top actions (playbooks, outreach)", "estimated_hours": 32},
            {"id": "PB-05-S4", "name": "Follow-up & re-score", "description": "Re-measure health and close or escalate", "estimated_hours": 8},
        ],
    },
    "PB-06": {
        "id": "PB-06",
        "name": "Customer Engagement",
        "description": "Maintain executive relationships and strategic alignment",
        "trigger_kpis": ["P4-KPI3", "P5-KPI8"],  # QBR frequency, champion engagement
        "trigger_conditions": {
            "P4-KPI3": {"operator": "<", "value": 3},  # < 3 QBRs annually
            "P5-KPI8": {"operator": "<", "value": 60},  # < 60 champion engagement
        },
        "automation_level": "medium",
        "human_approval_required": False,
        "estimated_impact": "+20% executive engagement score",
        "phases": ["excellence"],
        "estimated_duration_days": 45,
        "estimated_duration_display": "30–90 days (ongoing)",
        "sub_components": [
            {"id": "PB-06-S1", "name": "Stakeholder mapping", "description": "Identify exec sponsor, champion, and key contacts", "estimated_hours": 8},
            {"id": "PB-06-S2", "name": "QBR schedule & prep", "description": "Set quarterly cadence; prepare agenda and metrics", "estimated_hours": 24},
            {"id": "PB-06-S3", "name": "Champion engagement", "description": "Regular touchpoints and success stories", "estimated_hours": 24},
            {"id": "PB-06-S4", "name": "Executive alignment", "description": "Executive briefing and strategic alignment", "estimated_hours": 16},
        ],
    }
}

def get_playbook_config(playbook_id: str) -> Dict[str, Any]:
    """Get configuration for a playbook"""
    return PLAYBOOK_CONFIG.get(playbook_id, {})


def get_playbook_duration_and_sub_components(playbook_id: str) -> Dict[str, Any]:
    """Get estimated duration and sub-components for a playbook (for APIs/docs)."""
    cfg = get_playbook_config(playbook_id)
    if not cfg:
        return {}
    return {
        "playbook_id": cfg.get("id"),
        "name": cfg.get("name"),
        "estimated_duration_days": cfg.get("estimated_duration_days"),
        "estimated_duration_display": cfg.get("estimated_duration_display"),
        "sub_components": cfg.get("sub_components", []),
    }

def get_playbooks_for_phase(phase: str) -> List[str]:
    """Get all playbooks applicable for a customer phase"""
    return [
        pb_id for pb_id, config in PLAYBOOK_CONFIG.items()
        if phase in config.get("phases", [])
    ]

def should_trigger_playbook(
    playbook_id: str,
    kpi_values: Dict[str, float]
) -> bool:
    """
    Check if playbook should trigger based on KPI values
    
    Args:
        playbook_id: Playbook identifier
        kpi_values: Current KPI values
        
    Returns:
        True if playbook should trigger
    """
    config = get_playbook_config(playbook_id)
    conditions = config.get("trigger_conditions", {})
    
    for kpi, condition in conditions.items():
        if kpi not in kpi_values:
            return False
        
        value = kpi_values[kpi]
        operator = condition.get("operator")
        threshold = condition.get("value")
        
        if operator == ">":
            if value <= threshold:
                return False
        elif operator == "<":
            if value >= threshold:
                return False
        elif operator == "==":
            if value != threshold:
                return False
    
    return True

# ============================================================
# ALERT CONFIGURATION
# ============================================================

ALERT_THRESHOLDS = {
    "critical": {
        "rma_rate_critical": {
            "kpi": "P2-KPI1",
            "condition": {"operator": ">", "value": 3.0},
            "priority": "critical",
            "action": "Immediate field engineer intervention",
            "notification": ["cro", "coo", "field_engineer_lead"],
            "playbook": "PB-02"
        },
        "deployment_delay_critical": {
            "kpi": "P1-KPI1",
            "condition": {"operator": ">", "value": 30},
            "priority": "critical",
            "action": "Escalate to deployment manager",
            "notification": ["csm", "deployment_manager"],
            "playbook": "PB-01"
        },
        "health_score_critical": {
            "kpi": "OVERALL_HEALTH",
            "condition": {"operator": "<", "value": 50},
            "priority": "critical",
            "action": "Executive review meeting",
            "notification": ["cro", "csm", "account_manager"],
            "playbook": "PB-05"
        }
    },
    "high": {
        "expansion_opportunity": {
            "kpi": "P5-KPI7",
            "condition": {"operator": ">", "value": 75},
            "priority": "high",
            "action": "Schedule expansion planning call",
            "notification": ["csm", "sales_rep"],
            "playbook": "PB-04"
        },
        "gpu_underutilization": {
            "kpi": "P3-KPI1",
            "condition": {"operator": "<", "value": 50},
            "priority": "high",
            "action": "GPU optimization review",
            "notification": ["csm", "technical_success_engineer"],
            "playbook": "PB-03"
        }
    },
    "medium": {
        "partner_engagement_low": {
            "kpi": "P4-KPI1",
            "condition": {"operator": "<", "value": 60},
            "priority": "medium",
            "action": "Partner relationship check-in",
            "notification": ["channel_manager"],
            "playbook": "PB-06"
        }
    }
}

def get_triggered_alerts(kpi_values: Dict[str, float]) -> List[Dict[str, Any]]:
    """Get all triggered alerts for current KPI values"""
    triggered = []
    
    for priority, alerts in ALERT_THRESHOLDS.items():
        for alert_name, alert_config in alerts.items():
            kpi = alert_config["kpi"]
            condition = alert_config["condition"]
            
            if kpi in kpi_values:
                value = kpi_values[kpi]
                operator = condition["operator"]
                threshold = condition["value"]
                
                triggered_flag = False
                if operator == ">" and value > threshold:
                    triggered_flag = True
                elif operator == "<" and value < threshold:
                    triggered_flag = True
                
                if triggered_flag:
                    triggered.append({
                        "name": alert_name,
                        "priority": priority,
                        "kpi": kpi,
                        "value": value,
                        "threshold": threshold,
                        **alert_config
                    })
    
    return triggered

# ============================================================
# INTEGRATION SETTINGS
# ============================================================

INTEGRATION_CONFIG = {
    "google_sheets": {
        "enabled": True,
        "sync_interval_minutes": 15,
        "master_sheet_name": "DC2_S_Master",
        "tabs_per_account": ["KPIs", "Health", "Communications", "Actions", "Profile"]
    },
    "n8n": {
        "enabled": True,
        "workflow_count": 10,
        "webhook_base_url": "/api/webhooks/dc2_s",
        "parallel_execution": True
    },
    "agents": {
        "signal_analyst": {"enabled": True, "vertical_mode": "dc2_S"},
        "playbook_planner": {"enabled": True},
        "expansion_opportunity": {"enabled": True},
        "portfolio_triage": {"enabled": True},
        "narrative_generator": {"enabled": True}
    }
}

# ============================================================
# METADATA
# ============================================================

VERTICAL_METADATA = {
    "vertical_id": "dc2_S",
    "vertical_name": "Data Center Hardware Infrastructure",
    "industry": "AI/ML Infrastructure",
    "target_customers": "Data center operators, AI labs, enterprise ML teams",
    "typical_deal_size": "$2M-$15M Phase 1, $4M-$10M Phase 2",
    "sales_cycle_days": 120,
    "deployment_cycle_days": 90,
    "version": "1.0.0",
    "last_updated": "2026-01-01"
}
