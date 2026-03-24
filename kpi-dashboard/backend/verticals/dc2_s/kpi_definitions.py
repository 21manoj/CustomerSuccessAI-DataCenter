#!/usr/bin/env python3
"""
DC2_S Vertical - KPI Definitions
Data Center Hardware Infrastructure

Defines 38 KPIs across 5 pillars for hardware infrastructure customers.
Maps DC2_S-specific KPIs to existing SaaS schema for compatibility.

Pillars:
- P1: Deployment Velocity (15%)
- P2: Operational Stability (20%)
- P3: AI Workload Performance (25%) ⭐ Highest weight
- P4: Channel & Partner Health (15%)
- P5: Expansion Readiness (25%) ⭐ Highest weight

Bootstrap weights derived from 100-account, 12-month simulation.
"""

from typing import Dict, Any, List, Optional

# ============================================================
# MEASUREMENT FREQUENCY CONSTANTS
# ============================================================
# Canonical frequencies for KPI measurement cadence.
# Used by the trailing-average engine to size its lookback window
# and by the load driver to generate realistic synthetic data.

FREQ_REALTIME = "realtime"  # Continuous telemetry (sampled every few minutes)
FREQ_DAILY    = "daily"     # Aggregated once per day
FREQ_WEEKLY   = "weekly"    # Aggregated once per week
FREQ_MONTHLY  = "monthly"   # Aggregated once per month
FREQ_QUARTERLY = "quarterly"  # Measured once per quarter

# Frequency → typical data points per 30-day window (for trailing-average sizing)
FREQ_DATA_POINTS = {
    FREQ_REALTIME: 30,   # daily aggregates from realtime stream
    FREQ_DAILY: 30,
    FREQ_WEEKLY: 4,
    FREQ_MONTHLY: 1,
    FREQ_QUARTERLY: 0,   # may not have a data point in 30 days
}

VALID_FREQUENCIES = {FREQ_REALTIME, FREQ_DAILY, FREQ_WEEKLY, FREQ_MONTHLY, FREQ_QUARTERLY}


# ============================================================
# PILLAR DEFINITIONS
# ============================================================

DC2S_PILLARS = {
    "P1": {
        "name": "Deployment Velocity",
        "description": "Speed and efficiency of hardware deployment and configuration",
        "weight_l2": 0.15,  # 15% of overall health
        "saas_equivalent": "Product Usage & Onboarding",
        "kpi_count": 8
    },
    "P2": {
        "name": "Operational Stability",
        "description": "Hardware reliability, uptime, and failure prevention",
        "weight_l2": 0.20,  # 20% of overall health
        "saas_equivalent": "Support Engagement",
        "kpi_count": 8
    },
    "P3": {
        "name": "AI Workload Performance",
        "description": "GPU utilization and AI workload execution efficiency",
        "weight_l2": 0.25,  # 25% of overall health ⭐ HIGHEST
        "saas_equivalent": "Product Usage & Onboarding",
        "kpi_count": 8
    },
    "P4": {
        "name": "Channel & Partner Health",
        "description": "Partner engagement and channel relationship strength",
        "weight_l2": 0.15,  # 15% of overall health
        "saas_equivalent": "Relationship Strength",
        "kpi_count": 6
    },
    "P5": {
        "name": "Expansion Readiness",
        "description": "Capacity utilization and expansion probability indicators",
        "weight_l2": 0.25,  # 25% of overall health ⭐ HIGHEST
        "saas_equivalent": "Business Outcomes",
        "kpi_count": 8
    }
}

# ============================================================
# KPI DEFINITIONS (38 KPIs)
# ============================================================

DC2S_KPIS: Dict[str, Dict[str, Any]] = {
    
    # ========================================
    # P1: DEPLOYMENT VELOCITY (8 KPIs, 15%)
    # ========================================
    
    "P1-KPI1": {
        "name": "Time-to-First-Workload",
        "description": "Days from hardware arrival to first AI workload running in production",
        "pillar": "P1",
        "weight_l1": 0.20,  # 20% of P1 score
        "impact": "high",  # derived from weight_l1 relative to pillar avg
        "frequency": "monthly",  # Project milestone — measured per deployment event
        "saas_kpi_code": "TTFV",
        "saas_category": "Product Usage & Onboarding",
        "unit": "days",
        "target": {"operator": "<", "value": 14},
        "ranges": {
            "healthy": {"min": 0, "max": 14, "color": "green"},
            "risk": {"min": 14, "max": 21, "color": "yellow"},
            "critical": {"min": 21, "max": 60, "color": "red"}
        },
        "higher_is_better": False,
        "correlation": 0.45,  # Moderate correlation with Phase 2 success
        "data_source": "deployment_tracking",
        "calculation": "DATE(first_workload_completion) - DATE(hardware_delivery)"
    },
    
    "P1-KPI2": {
        "name": "Installation Completion Rate",
        "description": "Percentage of planned hardware successfully installed on first attempt",
        "pillar": "P1",
        "weight_l1": 0.15,
        "impact": "medium",  # derived from weight_l1 relative to pillar avg
        "frequency": "monthly",  # Rolled up from installation events each month
        "saas_kpi_code": "ONBOARDING_COMPLETION",
        "saas_category": "Product Usage & Onboarding",
        "unit": "percentage",
        "target": {"operator": ">", "value": 90},
        "ranges": {
            "healthy": {"min": 90, "max": 100, "color": "green"},
            "risk": {"min": 75, "max": 90, "color": "yellow"},
            "critical": {"min": 0, "max": 75, "color": "red"}
        },
        "higher_is_better": True,
        "correlation": 0.35,
        "data_source": "installation_logs",
        "calculation": "(successful_installs / total_planned_installs) * 100"
    },
    
    "P1-KPI3": {
        "name": "Configuration Accuracy",
        "description": "Percentage of servers configured correctly without rework",
        "pillar": "P1",
        "weight_l1": 0.12,
        "impact": "medium",  # derived from weight_l1 relative to pillar avg
        "frequency": "weekly",  # Validated after each config batch
        "saas_kpi_code": "SETUP_ACCURACY",
        "saas_category": "Product Usage & Onboarding",
        "unit": "percentage",
        "target": {"operator": ">", "value": 95},
        "ranges": {
            "healthy": {"min": 95, "max": 100, "color": "green"},
            "risk": {"min": 85, "max": 95, "color": "yellow"},
            "critical": {"min": 0, "max": 85, "color": "red"}
        },
        "higher_is_better": True,
        "correlation": 0.28,
        "data_source": "configuration_validation",
        "calculation": "(correct_configs / total_configs) * 100"
    },
    
    "P1-KPI4": {
        "name": "Deployment Cycle Time",
        "description": "Average days to complete full deployment (all phases)",
        "pillar": "P1",
        "weight_l1": 0.15,
        "impact": "medium",  # derived from weight_l1 relative to pillar avg
        "frequency": "monthly",  # Per-project, averaged monthly
        "saas_kpi_code": "TIME_TO_VALUE",
        "saas_category": "Product Usage & Onboarding",
        "unit": "days",
        "target": {"operator": "<", "value": 30},
        "ranges": {
            "healthy": {"min": 0, "max": 30, "color": "green"},
            "risk": {"min": 30, "max": 45, "color": "yellow"},
            "critical": {"min": 45, "max": 90, "color": "red"}
        },
        "higher_is_better": False,
        "correlation": 0.38,
        "data_source": "project_tracking",
        "calculation": "AVG(deployment_end_date - deployment_start_date)"
    },
    
    "P1-KPI5": {
        "name": "Hardware Commissioning Time",
        "description": "Days from rack delivery to operational status",
        "pillar": "P1",
        "weight_l1": 0.13,
        "impact": "medium",  # derived from weight_l1 relative to pillar avg
        "frequency": "monthly",  # Per-rack event, aggregated monthly
        "saas_kpi_code": "ACTIVATION_TIME",
        "saas_category": "Product Usage & Onboarding",
        "unit": "days",
        "target": {"operator": "<", "value": 7},
        "ranges": {
            "healthy": {"min": 0, "max": 7, "color": "green"},
            "risk": {"min": 7, "max": 14, "color": "yellow"},
            "critical": {"min": 14, "max": 30, "color": "red"}
        },
        "higher_is_better": False,
        "correlation": 0.32,
        "data_source": "commissioning_logs"
    },
    
    "P1-KPI6": {
        "name": "Network Readiness Score",
        "description": "Percentage of network requirements met at deployment",
        "pillar": "P1",
        "weight_l1": 0.10,
        "impact": "medium",  # derived from weight_l1 relative to pillar avg
        "frequency": "weekly",  # Checked weekly during deployment phases
        "saas_kpi_code": "INFRASTRUCTURE_READINESS",
        "saas_category": "Product Usage & Onboarding",
        "unit": "percentage",
        "target": {"operator": ">", "value": 90},
        "ranges": {
            "healthy": {"min": 90, "max": 100, "color": "green"},
            "risk": {"min": 70, "max": 90, "color": "yellow"},
            "critical": {"min": 0, "max": 70, "color": "red"}
        },
        "higher_is_better": True,
        "correlation": 0.25
    },
    
    "P1-KPI7": {
        "name": "Deployment Team Velocity",
        "description": "Servers deployed per day per field engineer",
        "pillar": "P1",
        "weight_l1": 0.08,
        "impact": "low",  # derived from weight_l1 relative to pillar avg
        "frequency": "weekly",  # Reviewed in weekly ops standups
        "saas_kpi_code": "TEAM_PRODUCTIVITY",
        "saas_category": "Product Usage & Onboarding",
        "unit": "servers/day",
        "target": {"operator": ">", "value": 5},
        "ranges": {
            "healthy": {"min": 5, "max": 20, "color": "green"},
            "risk": {"min": 3, "max": 5, "color": "yellow"},
            "critical": {"min": 0, "max": 3, "color": "red"}
        },
        "higher_is_better": True,
        "correlation": 0.20
    },
    
    "P1-KPI8": {
        "name": "Documentation Completeness",
        "description": "Percentage of deployment docs completed and validated",
        "pillar": "P1",
        "weight_l1": 0.07,
        "impact": "low",  # derived from weight_l1 relative to pillar avg
        "frequency": "monthly",  # Reviewed at project milestones
        "saas_kpi_code": "ONBOARDING_DOCS_COMPLETE",
        "saas_category": "Product Usage & Onboarding",
        "unit": "percentage",
        "target": {"operator": ">", "value": 95},
        "ranges": {
            "healthy": {"min": 95, "max": 100, "color": "green"},
            "risk": {"min": 80, "max": 95, "color": "yellow"},
            "critical": {"min": 0, "max": 80, "color": "red"}
        },
        "higher_is_better": True,
        "correlation": 0.15
    },
    
    # ========================================
    # P2: OPERATIONAL STABILITY (8 KPIs, 20%)
    # ========================================
    
    "P2-KPI1": {
        "name": "RMA Frequency Rate",
        "description": "Percentage of hardware requiring RMA (return/replacement) ⭐ CRITICAL",
        "pillar": "P2",
        "weight_l1": 0.20,  # Highest weight in P2
        "impact": "high",  # derived from weight_l1 relative to pillar avg
        "frequency": "weekly",  # RMA events tracked weekly by ops
        "saas_kpi_code": "CRITICAL_ISSUES",
        "saas_category": "Support Engagement",
        "unit": "percentage",
        "target": {"operator": "<", "value": 2.6},
        "ranges": {
            "healthy": {"min": 0, "max": 1.2, "color": "green"},
            "risk": {"min": 1.2, "max": 2.6, "color": "yellow"},
            "critical": {"min": 2.6, "max": 10, "color": "red"}
        },
        "higher_is_better": False,
        "correlation": -0.82,  # STRONG negative correlation (high RMA = bad)
        "critical_threshold": 2.6,
        "critical_impact": "Each 1% above 2.6% = $4.4M annual margin loss",
        "data_source": "rma_tracking",
        "calculation": "(rma_units / total_deployed_units) * 100"
    },
    
    "P2-KPI2": {
        "name": "MTBF (Mean Time Between Failures)",
        "description": "Average hours between hardware failures",
        "pillar": "P2",
        "weight_l1": 0.18,
        "impact": "high",  # derived from weight_l1 relative to pillar avg
        "frequency": "weekly",  # Recalculated weekly from failure events
        "saas_kpi_code": "SYSTEM_UPTIME",
        "saas_category": "Support Engagement",
        "unit": "hours",
        "target": {"operator": ">", "value": 8760},  # 1 year
        "ranges": {
            "healthy": {"min": 8760, "max": 100000, "color": "green"},
            "risk": {"min": 4380, "max": 8760, "color": "yellow"},
            "critical": {"min": 0, "max": 4380, "color": "red"}
        },
        "higher_is_better": True,
        "correlation": 0.65,
        "data_source": "failure_tracking"
    },
    
    "P2-KPI3": {
        "name": "Critical Incidents (30d)",
        "description": "Count of P1/P2 incidents in last 30 days",
        "pillar": "P2",
        "weight_l1": 0.17,
        "impact": "medium",  # derived from weight_l1 relative to pillar avg
        "frequency": "daily",  # Incident count updated daily from ticketing system
        "saas_kpi_code": "CRITICAL_TICKETS",
        "saas_category": "Support Engagement",
        "unit": "count",
        "target": {"operator": "<", "value": 3},
        "ranges": {
            "healthy": {"min": 0, "max": 1, "color": "green"},
            "risk": {"min": 1, "max": 3, "color": "yellow"},
            "critical": {"min": 3, "max": 20, "color": "red"}
        },
        "higher_is_better": False,
        "correlation": -0.58,
        "data_source": "incident_management"
    },
    
    "P2-KPI4": {
        "name": "System Uptime Percentage",
        "description": "Percentage of time systems are operational (30d)",
        "pillar": "P2",
        "weight_l1": 0.15,
        "impact": "medium",  # derived from weight_l1 relative to pillar avg
        "frequency": "daily",  # Computed daily from monitoring telemetry
        "saas_kpi_code": "PLATFORM_UPTIME",
        "saas_category": "Support Engagement",
        "unit": "percentage",
        "target": {"operator": ">", "value": 99.5},
        "ranges": {
            "healthy": {"min": 99.5, "max": 100, "color": "green"},
            "risk": {"min": 98.0, "max": 99.5, "color": "yellow"},
            "critical": {"min": 0, "max": 98.0, "color": "red"}
        },
        "higher_is_better": True,
        "correlation": 0.52
    },
    
    "P2-KPI5": {
        "name": "Thermal Management Score",
        "description": "Percentage of time temps within optimal range",
        "pillar": "P2",
        "weight_l1": 0.12,
        "impact": "medium",  # derived from weight_l1 relative to pillar avg
        "frequency": "realtime",  # Continuous sensor telemetry, aggregated daily
        "saas_kpi_code": "ENVIRONMENTAL_HEALTH",
        "saas_category": "Support Engagement",
        "unit": "percentage",
        "target": {"operator": ">", "value": 95},
        "ranges": {
            "healthy": {"min": 95, "max": 100, "color": "green"},
            "risk": {"min": 85, "max": 95, "color": "yellow"},
            "critical": {"min": 0, "max": 85, "color": "red"}
        },
        "higher_is_better": True,
        "correlation": 0.42
    },
    
    "P2-KPI6": {
        "name": "Power Efficiency (PUE)",
        "description": "Power Usage Effectiveness ratio",
        "pillar": "P2",
        "weight_l1": 0.08,
        "impact": "low",  # derived from weight_l1 relative to pillar avg
        "frequency": "realtime",  # Continuous power monitoring, aggregated daily
        "saas_kpi_code": "RESOURCE_EFFICIENCY",
        "saas_category": "Support Engagement",
        "unit": "ratio",
        "target": {"operator": "<", "value": 1.3},
        "ranges": {
            "healthy": {"min": 1.0, "max": 1.2, "color": "green"},
            "risk": {"min": 1.2, "max": 1.4, "color": "yellow"},
            "critical": {"min": 1.4, "max": 3.0, "color": "red"}
        },
        "higher_is_better": False,
        "correlation": -0.28
    },
    
    "P2-KPI7": {
        "name": "Mean Time To Repair (MTTR)",
        "description": "Average hours to resolve hardware failures",
        "pillar": "P2",
        "weight_l1": 0.06,
        "impact": "low",  # derived from weight_l1 relative to pillar avg
        "frequency": "weekly",  # Recalculated weekly from repair logs
        "saas_kpi_code": "RESOLUTION_TIME",
        "saas_category": "Support Engagement",
        "unit": "hours",
        "target": {"operator": "<", "value": 4},
        "ranges": {
            "healthy": {"min": 0, "max": 4, "color": "green"},
            "risk": {"min": 4, "max": 12, "color": "yellow"},
            "critical": {"min": 12, "max": 72, "color": "red"}
        },
        "higher_is_better": False,
        "correlation": -0.35
    },
    
    "P2-KPI8": {
        "name": "Preventive Maintenance Compliance",
        "description": "Percentage of scheduled maintenance completed on time",
        "pillar": "P2",
        "weight_l1": 0.04,
        "impact": "low",  # derived from weight_l1 relative to pillar avg
        "frequency": "monthly",  # Monthly maintenance schedule compliance
        "saas_kpi_code": "MAINTENANCE_COMPLIANCE",
        "saas_category": "Support Engagement",
        "unit": "percentage",
        "target": {"operator": ">", "value": 95},
        "ranges": {
            "healthy": {"min": 95, "max": 100, "color": "green"},
            "risk": {"min": 80, "max": 95, "color": "yellow"},
            "critical": {"min": 0, "max": 80, "color": "red"}
        },
        "higher_is_better": True,
        "correlation": 0.38
    },
    
    # ========================================
    # P3: AI WORKLOAD PERFORMANCE (8 KPIs, 25%)
    # ========================================
    
    "P3-KPI1": {
        "name": "GPU Utilization Rate",
        "description": "Average GPU utilization percentage ⭐ TOP EXPANSION DRIVER",
        "pillar": "P3",
        "weight_l1": 0.22,  # Highest weight in P3
        "impact": "high",  # derived from weight_l1 relative to pillar avg
        "frequency": "realtime",  # Continuous GPU monitoring, aggregated daily
        "saas_kpi_code": "FEATURE_USAGE",
        "saas_category": "Product Usage & Onboarding",
        "unit": "percentage",
        "target": {"operator": ">", "value": 65},
        "ranges": {
            "healthy": {"min": 65, "max": 100, "color": "green"},
            "risk": {"min": 45, "max": 65, "color": "yellow"},
            "critical": {"min": 0, "max": 45, "color": "red"}
        },
        "higher_is_better": True,
        "correlation": 0.88,  # VERY STRONG predictor of expansion
        "expansion_signal": ">75% utilization = high Phase 2 probability",
        "data_source": "gpu_monitoring",
        "calculation": "AVG(gpu_active_time / total_time) * 100"
    },
    
    "P3-KPI2": {
        "name": "Training Job Completion Rate",
        "description": "Percentage of AI training jobs completing successfully",
        "pillar": "P3",
        "weight_l1": 0.20,
        "impact": "high",  # derived from weight_l1 relative to pillar avg
        "frequency": "daily",  # Computed daily from job scheduler logs
        "saas_kpi_code": "TASK_SUCCESS_RATE",
        "saas_category": "Product Usage & Onboarding",
        "unit": "percentage",
        "target": {"operator": ">", "value": 90},
        "ranges": {
            "healthy": {"min": 90, "max": 100, "color": "green"},
            "risk": {"min": 75, "max": 90, "color": "yellow"},
            "critical": {"min": 0, "max": 75, "color": "red"}
        },
        "higher_is_better": True,
        "correlation": 0.72
    },
    
    "P3-KPI3": {
        "name": "Inference Latency (P95)",
        "description": "95th percentile inference response time",
        "pillar": "P3",
        "weight_l1": 0.15,
        "impact": "medium",  # derived from weight_l1 relative to pillar avg
        "frequency": "realtime",  # Continuous latency monitoring, aggregated daily
        "saas_kpi_code": "RESPONSE_TIME",
        "saas_category": "Product Usage & Onboarding",
        "unit": "milliseconds",
        "target": {"operator": "<", "value": 50},
        "ranges": {
            "healthy": {"min": 0, "max": 50, "color": "green"},
            "risk": {"min": 50, "max": 100, "color": "yellow"},
            "critical": {"min": 100, "max": 1000, "color": "red"}
        },
        "higher_is_better": False,
        "correlation": -0.55
    },
    
    "P3-KPI4": {
        "name": "Model Training Time",
        "description": "Average time to train standard benchmark model",
        "pillar": "P3",
        "weight_l1": 0.14,
        "impact": "medium",  # derived from weight_l1 relative to pillar avg
        "frequency": "daily",  # Per-job completion, aggregated daily
        "saas_kpi_code": "PROCESSING_TIME",
        "saas_category": "Product Usage & Onboarding",
        "unit": "hours",
        "target": {"operator": "<", "value": 24},
        "ranges": {
            "healthy": {"min": 0, "max": 24, "color": "green"},
            "risk": {"min": 24, "max": 48, "color": "yellow"},
            "critical": {"min": 48, "max": 168, "color": "red"}
        },
        "higher_is_better": False,
        "correlation": -0.48
    },
    
    "P3-KPI5": {
        "name": "GPU Memory Efficiency",
        "description": "Percentage of GPU memory effectively utilized",
        "pillar": "P3",
        "weight_l1": 0.12,
        "impact": "medium",  # derived from weight_l1 relative to pillar avg
        "frequency": "realtime",  # Continuous GPU memory monitoring
        "saas_kpi_code": "RESOURCE_UTILIZATION",
        "saas_category": "Product Usage & Onboarding",
        "unit": "percentage",
        "target": {"operator": ">", "value": 80},
        "ranges": {
            "healthy": {"min": 80, "max": 100, "color": "green"},
            "risk": {"min": 60, "max": 80, "color": "yellow"},
            "critical": {"min": 0, "max": 60, "color": "red"}
        },
        "higher_is_better": True,
        "correlation": 0.62
    },
    
    "P3-KPI6": {
        "name": "Distributed Training Efficiency",
        "description": "Scaling efficiency across multiple GPUs",
        "pillar": "P3",
        "weight_l1": 0.09,
        "impact": "low",  # derived from weight_l1 relative to pillar avg
        "frequency": "daily",  # Computed daily from multi-GPU job metrics
        "saas_kpi_code": "PARALLEL_EFFICIENCY",
        "saas_category": "Product Usage & Onboarding",
        "unit": "percentage",
        "target": {"operator": ">", "value": 85},
        "ranges": {
            "healthy": {"min": 85, "max": 100, "color": "green"},
            "risk": {"min": 70, "max": 85, "color": "yellow"},
            "critical": {"min": 0, "max": 70, "color": "red"}
        },
        "higher_is_better": True,
        "correlation": 0.52
    },
    
    "P3-KPI7": {
        "name": "Workload Diversity Score",
        "description": "Number of distinct AI workload types running",
        "pillar": "P3",
        "weight_l1": 0.05,
        "impact": "low",  # derived from weight_l1 relative to pillar avg
        "frequency": "weekly",  # Reviewed weekly — new workload types change slowly
        "saas_kpi_code": "FEATURE_BREADTH",
        "saas_category": "Product Usage & Onboarding",
        "unit": "count",
        "target": {"operator": ">", "value": 3},
        "ranges": {
            "healthy": {"min": 3, "max": 10, "color": "green"},
            "risk": {"min": 2, "max": 3, "color": "yellow"},
            "critical": {"min": 0, "max": 2, "color": "red"}
        },
        "higher_is_better": True,
        "correlation": 0.44
    },
    
    "P3-KPI8": {
        "name": "Batch Processing Throughput",
        "description": "Samples processed per hour",
        "pillar": "P3",
        "weight_l1": 0.03,
        "impact": "low",  # derived from weight_l1 relative to pillar avg
        "frequency": "daily",  # Aggregated daily from batch job scheduler
        "saas_kpi_code": "THROUGHPUT",
        "saas_category": "Product Usage & Onboarding",
        "unit": "samples/hour",
        "target": {"operator": ">", "value": 10000},
        "ranges": {
            "healthy": {"min": 10000, "max": 1000000, "color": "green"},
            "risk": {"min": 5000, "max": 10000, "color": "yellow"},
            "critical": {"min": 0, "max": 5000, "color": "red"}
        },
        "higher_is_better": True,
        "correlation": 0.35
    },
    
    # ========================================
    # P4: CHANNEL & PARTNER HEALTH (6 KPIs, 15%)
    # ========================================
    
    "P4-KPI1": {
        "name": "Partner Engagement Score",
        "description": "Composite score of partner interaction quality",
        "pillar": "P4",
        "weight_l1": 0.22,
        "impact": "medium",  # derived from weight_l1 relative to pillar avg
        "frequency": "monthly",  # Composite score updated monthly from CRM
        "saas_kpi_code": "EXECUTIVE_ENGAGEMENT",
        "saas_category": "Relationship Strength",
        "unit": "score",
        "target": {"operator": ">", "value": 75},
        "ranges": {
            "healthy": {"min": 75, "max": 100, "color": "green"},
            "risk": {"min": 50, "max": 75, "color": "yellow"},
            "critical": {"min": 0, "max": 50, "color": "red"}
        },
        "higher_is_better": True,
        "correlation": 0.68,
        "data_source": "partner_crm"
    },
    
    "P4-KPI2": {
        "name": "VAR Performance Rating",
        "description": "Value-added reseller satisfaction and performance",
        "pillar": "P4",
        "weight_l1": 0.20,
        "impact": "medium",  # derived from weight_l1 relative to pillar avg
        "frequency": "monthly",  # Partner performance review cadence
        "saas_kpi_code": "PARTNER_SATISFACTION",
        "saas_category": "Relationship Strength",
        "unit": "score",
        "target": {"operator": ">", "value": 80},
        "ranges": {
            "healthy": {"min": 80, "max": 100, "color": "green"},
            "risk": {"min": 60, "max": 80, "color": "yellow"},
            "critical": {"min": 0, "max": 60, "color": "red"}
        },
        "higher_is_better": True,
        "correlation": 0.55
    },
    
    "P4-KPI3": {
        "name": "Joint QBR Frequency",
        "description": "Quarterly business reviews with partners (annual)",
        "pillar": "P4",
        "weight_l1": 0.18,
        "impact": "medium",  # derived from weight_l1 relative to pillar avg
        "frequency": "quarterly",  # QBRs are quarterly by definition
        "saas_kpi_code": "EXECUTIVE_TOUCHPOINTS",
        "saas_category": "Relationship Strength",
        "unit": "count",
        "target": {"operator": ">", "value": 4},
        "ranges": {
            "healthy": {"min": 4, "max": 12, "color": "green"},
            "risk": {"min": 2, "max": 4, "color": "yellow"},
            "critical": {"min": 0, "max": 2, "color": "red"}
        },
        "higher_is_better": True,
        "correlation": 0.62
    },
    
    "P4-KPI4": {
        "name": "Channel Conflict Score",
        "description": "Reverse score - lower is better (0-100)",
        "pillar": "P4",
        "weight_l1": 0.15,
        "impact": "medium",  # derived from weight_l1 relative to pillar avg
        "frequency": "monthly",  # Channel conflict assessed monthly
        "saas_kpi_code": "PARTNER_HEALTH",
        "saas_category": "Relationship Strength",
        "unit": "score",
        "target": {"operator": "<", "value": 20},
        "ranges": {
            "healthy": {"min": 0, "max": 20, "color": "green"},
            "risk": {"min": 20, "max": 50, "color": "yellow"},
            "critical": {"min": 50, "max": 100, "color": "red"}
        },
        "higher_is_better": False,
        "correlation": -0.48
    },
    
    "P4-KPI5": {
        "name": "Co-selling Opportunities",
        "description": "Active joint sales opportunities with partners",
        "pillar": "P4",
        "weight_l1": 0.13,
        "impact": "low",  # derived from weight_l1 relative to pillar avg
        "frequency": "monthly",  # Pipeline reviewed monthly
        "saas_kpi_code": "EXPANSION_PIPELINE",
        "saas_category": "Relationship Strength",
        "unit": "count",
        "target": {"operator": ">", "value": 3},
        "ranges": {
            "healthy": {"min": 3, "max": 20, "color": "green"},
            "risk": {"min": 1, "max": 3, "color": "yellow"},
            "critical": {"min": 0, "max": 1, "color": "red"}
        },
        "higher_is_better": True,
        "correlation": 0.72
    },
    
    "P4-KPI6": {
        "name": "Partner NPS",
        "description": "Net Promoter Score from channel partners",
        "pillar": "P4",
        "weight_l1": 0.12,
        "impact": "low",  # derived from weight_l1 relative to pillar avg
        "frequency": "quarterly",  # NPS surveys sent quarterly
        "saas_kpi_code": "NPS",
        "saas_category": "Relationship Strength",
        "unit": "score",
        "target": {"operator": ">", "value": 50},
        "ranges": {
            "healthy": {"min": 50, "max": 100, "color": "green"},
            "risk": {"min": 0, "max": 50, "color": "yellow"},
            "critical": {"min": -100, "max": 0, "color": "red"}
        },
        "higher_is_better": True,
        "correlation": 0.58
    },
    
    # ========================================
    # P5: EXPANSION READINESS (8 KPIs, 25%)
    # ========================================
    
    "P5-KPI1": {
        "name": "Capacity Utilization Rate",
        "description": "Percentage of deployed capacity currently in use",
        "pillar": "P5",
        "weight_l1": 0.18,
        "impact": "high",  # derived from weight_l1 relative to pillar avg
        "frequency": "daily",  # Computed daily from resource monitoring
        "saas_kpi_code": "RESOURCE_CONSUMPTION",
        "saas_category": "Business Outcomes",
        "unit": "percentage",
        "target": {"operator": ">", "value": 70},
        "ranges": {
            "healthy": {"min": 70, "max": 90, "color": "green"},
            "risk": {"min": 50, "max": 70, "color": "yellow"},
            "critical": {"min": 0, "max": 50, "color": "red"}
        },
        "higher_is_better": True,
        "correlation": 0.82,
        "expansion_signal": ">80% = strong expansion signal"
    },
    
    "P5-KPI2": {
        "name": "Capacity Utilization Trajectory",
        "description": "Month-over-month change in capacity utilization",
        "pillar": "P5",
        "weight_l1": 0.18,
        "impact": "high",  # derived from weight_l1 relative to pillar avg
        "frequency": "monthly",  # MoM comparison requires monthly cadence
        "saas_kpi_code": "GROWTH_RATE",
        "saas_category": "Business Outcomes",
        "unit": "percentage_change",
        "target": {"operator": ">", "value": 5},
        "ranges": {
            "healthy": {"min": 5, "max": 50, "color": "green"},
            "risk": {"min": -5, "max": 5, "color": "yellow"},
            "critical": {"min": -50, "max": -5, "color": "red"}
        },
        "higher_is_better": True,
        "correlation": 0.92,  # VERY STRONG expansion predictor
        "expansion_signal": ">10% MoM growth = expansion likely"
    },
    
    "P5-KPI3": {
        "name": "Workload Growth Velocity",
        "description": "Rate of increase in AI workloads (MoM)",
        "pillar": "P5",
        "weight_l1": 0.18,
        "impact": "high",  # derived from weight_l1 relative to pillar avg
        "frequency": "monthly",  # MoM comparison requires monthly cadence
        "saas_kpi_code": "USAGE_GROWTH",
        "saas_category": "Business Outcomes",
        "unit": "percentage_change",
        "target": {"operator": ">", "value": 10},
        "ranges": {
            "healthy": {"min": 10, "max": 100, "color": "green"},
            "risk": {"min": 0, "max": 10, "color": "yellow"},
            "critical": {"min": -50, "max": 0, "color": "red"}
        },
        "higher_is_better": True,
        "correlation": 0.88
    },
    
    "P5-KPI4": {
        "name": "Compute Hour Consumption Trend",
        "description": "Change in total compute hours consumed (30d)",
        "pillar": "P5",
        "weight_l1": 0.15,
        "impact": "medium",  # derived from weight_l1 relative to pillar avg
        "frequency": "weekly",  # Computed weekly from daily consumption data
        "saas_kpi_code": "CONSUMPTION_TREND",
        "saas_category": "Business Outcomes",
        "unit": "percentage_change",
        "target": {"operator": ">", "value": 15},
        "ranges": {
            "healthy": {"min": 15, "max": 200, "color": "green"},
            "risk": {"min": 0, "max": 15, "color": "yellow"},
            "critical": {"min": -100, "max": 0, "color": "red"}
        },
        "higher_is_better": True,
        "correlation": 0.85
    },
    
    "P5-KPI5": {
        "name": "Budget Availability Signals",
        "description": "Indicators of expansion budget availability",
        "pillar": "P5",
        "weight_l1": 0.10,
        "impact": "medium",  # derived from weight_l1 relative to pillar avg
        "frequency": "monthly",  # Budget signals gathered monthly from CRM + meetings
        "saas_kpi_code": "EXPANSION_READINESS",
        "saas_category": "Business Outcomes",
        "unit": "score",
        "target": {"operator": ">", "value": 70},
        "ranges": {
            "healthy": {"min": 70, "max": 100, "color": "green"},
            "risk": {"min": 40, "max": 70, "color": "yellow"},
            "critical": {"min": 0, "max": 40, "color": "red"}
        },
        "higher_is_better": True,
        "correlation": 0.65
    },
    
    "P5-KPI6": {
        "name": "New Use Case Adoption",
        "description": "New AI use cases adopted in last 90 days",
        "pillar": "P5",
        "weight_l1": 0.05,
        "impact": "low",  # derived from weight_l1 relative to pillar avg
        "frequency": "monthly",  # Tracked monthly — new use cases roll out slowly
        "saas_kpi_code": "FEATURE_ADOPTION",
        "saas_category": "Business Outcomes",
        "unit": "count",
        "target": {"operator": ">", "value": 2},
        "ranges": {
            "healthy": {"min": 2, "max": 10, "color": "green"},
            "risk": {"min": 1, "max": 2, "color": "yellow"},
            "critical": {"min": 0, "max": 1, "color": "red"}
        },
        "higher_is_better": True,
        "correlation": 0.58
    },
    
    "P5-KPI7": {
        "name": "Expansion Probability (90d)",
        "description": "ML-predicted probability of expansion in next 90 days",
        "pillar": "P5",
        "weight_l1": 0.13,
        "impact": "medium",  # derived from weight_l1 relative to pillar avg
        "frequency": "weekly",  # ML model re-scored weekly with latest signals
        "saas_kpi_code": "EXPANSION_LIKELIHOOD",
        "saas_category": "Business Outcomes",
        "unit": "percentage",
        "target": {"operator": ">", "value": 50},
        "ranges": {
            "healthy": {"min": 50, "max": 100, "color": "green"},
            "risk": {"min": 25, "max": 50, "color": "yellow"},
            "critical": {"min": 0, "max": 25, "color": "red"}
        },
        "higher_is_better": True,
        "correlation": 0.95,  # EXTREMELY STRONG (ML-derived)
        "expansion_signal": ">70% = high confidence expansion"
    },
    
    "P5-KPI8": {
        "name": "Technical Champion Engagement",
        "description": "Engagement score of technical decision makers",
        "pillar": "P5",
        "weight_l1": 0.03,
        "impact": "low",  # derived from weight_l1 relative to pillar avg
        "frequency": "monthly",  # Engagement assessed monthly from touchpoints
        "saas_kpi_code": "CHAMPION_ENGAGEMENT",
        "saas_category": "Business Outcomes",
        "unit": "score",
        "target": {"operator": ">", "value": 75},
        "ranges": {
            "healthy": {"min": 75, "max": 100, "color": "green"},
            "risk": {"min": 50, "max": 75, "color": "yellow"},
            "critical": {"min": 0, "max": 50, "color": "red"}
        },
        "higher_is_better": True,
        "correlation": 0.68
    }
}

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_kpi_by_code(kpi_code: str) -> Optional[Dict[str, Any]]:
    """Get KPI definition by code (e.g., 'P1-KPI1')"""
    return DC2S_KPIS.get(kpi_code)

def get_kpis_by_pillar(pillar: str) -> Dict[str, Dict[str, Any]]:
    """Get all KPIs for a specific pillar"""
    return {k: v for k, v in DC2S_KPIS.items() if v.get('pillar') == pillar}

def get_pillar_info(pillar: str) -> Optional[Dict[str, Any]]:
    """Get pillar definition"""
    return DC2S_PILLARS.get(pillar)

def get_kpi_frequency(kpi_code: str) -> str:
    """Get measurement frequency for a KPI (defaults to 'monthly')."""
    kpi = DC2S_KPIS.get(kpi_code)
    return kpi.get('frequency', 'monthly') if kpi else 'monthly'

def get_kpis_by_frequency(frequency: str) -> Dict[str, Dict[str, Any]]:
    """Get all KPIs with a given measurement frequency."""
    return {k: v for k, v in DC2S_KPIS.items() if v.get('frequency') == frequency}

def get_frequency_summary() -> Dict[str, int]:
    """Return count of KPIs per measurement frequency."""
    summary: Dict[str, int] = {}
    for kpi in DC2S_KPIS.values():
        freq = kpi.get('frequency', 'monthly')
        summary[freq] = summary.get(freq, 0) + 1
    return summary

def get_trailing_window_days(frequency: str) -> int:
    """
    Suggested trailing-average window size for a given frequency.

    The trailing-average engine uses this to decide how many days of
    history to query for each KPI.

    Heuristic: use ~3x the measurement interval so there are enough
    data points for a meaningful weighted average.
    """
    windows = {
        'realtime': 7,    # 7 days of continuous data
        'daily': 30,      # 30 days (standard)
        'weekly': 56,     # ~8 weeks (≈2 months)
        'monthly': 90,    # 3 months
        'quarterly': 365, # 1 year
    }
    return windows.get(frequency, 30)

def get_health_status(kpi_code: str, value: float) -> str:
    """
    Determine health status (healthy/risk/critical) for a KPI value
    
    Args:
        kpi_code: KPI identifier (e.g., 'P1-KPI1')
        value: Current KPI value
        
    Returns:
        'healthy', 'risk', or 'critical'
    """
    kpi = get_kpi_by_code(kpi_code)
    if not kpi:
        return 'unknown'
    
    ranges = kpi.get('ranges', {})
    
    # Check each range
    for status in ['healthy', 'risk', 'critical']:
        range_def = ranges.get(status, {})
        min_val = range_def.get('min', float('-inf'))
        max_val = range_def.get('max', float('inf'))
        
        if min_val <= value <= max_val:
            return status
    
    return 'unknown'

def calculate_pillar_score(pillar: str, kpi_values: Dict[str, float]) -> float:
    """
    Calculate weighted pillar score from KPI values
    
    Args:
        pillar: Pillar identifier (e.g., 'P1')
        kpi_values: Dict of {kpi_code: value}
        
    Returns:
        Weighted score (0-100)
    """
    pillar_kpis = get_kpis_by_pillar(pillar)
    
    total_score = 0
    total_weight = 0
    
    for kpi_code, kpi_def in pillar_kpis.items():
        if kpi_code not in kpi_values:
            continue
            
        value = kpi_values[kpi_code]
        weight = kpi_def.get('weight_l1', 0)
        
        # Normalize value to 0-100 based on ranges
        ranges = kpi_def.get('ranges', {})
        healthy_range = ranges.get('healthy', {})
        
        # Simple normalization (can be enhanced)
        if kpi_def.get('higher_is_better', True):
            max_val = healthy_range.get('max', 100)
            normalized = min(100, (value / max_val) * 100) if max_val > 0 else 0
        else:
            min_val = healthy_range.get('min', 0)
            max_val = healthy_range.get('max', 100)
            normalized = max(0, 100 - ((value - min_val) / (max_val - min_val)) * 100) if (max_val - min_val) > 0 else 0
        
        total_score += normalized * weight
        total_weight += weight
    
    return (total_score / total_weight) if total_weight > 0 else 0

def calculate_overall_health(pillar_scores: Dict[str, float]) -> float:
    """
    Calculate overall health score from pillar scores
    
    Args:
        pillar_scores: Dict of {pillar: score}
        
    Returns:
        Overall health score (0-100)
    """
    total_score = 0
    
    for pillar, score in pillar_scores.items():
        pillar_def = get_pillar_info(pillar)
        if pillar_def:
            weight = pillar_def.get('weight_l2', 0)
            total_score += score * weight
    
    return total_score

# ============================================================
# METADATA
# ============================================================

DC2S_METADATA = {
    "vertical_name": "dc2_S",
    "vertical_full_name": "Data Center Hardware Infrastructure",
    "version": "1.1.0",
    "last_updated": "2026-03-05",
    "description": "KPI framework for data center hardware infrastructure customers (AI/ML workloads)",
    "total_kpis": 38,
    "pillar_count": 5,
    "data_source": "100-account, 12-month simulation",
    "methodology": "Statistical percentile analysis with correlation validation",
    "measurement_frequencies": {
        "realtime": 5,   # GPU util, inference latency, thermal, PUE, GPU memory
        "daily": 7,      # Incidents, uptime, training jobs, batch throughput, capacity util, etc.
        "weekly": 9,     # RMA rate, MTBF, MTTR, config accuracy, deployment velocity, etc.
        "monthly": 15,   # Deployment milestones, partner scores, budget signals, etc.
        "quarterly": 2,  # QBR frequency, Partner NPS
    },
    "key_predictors": [
        {"kpi": "P5-KPI7", "name": "Expansion Probability (90d)", "correlation": 0.95, "type": "ML-derived"},
        {"kpi": "P5-KPI2", "name": "Capacity Utilization Trajectory", "correlation": 0.92, "type": "growth"},
        {"kpi": "P3-KPI1", "name": "GPU Utilization Rate", "correlation": 0.88, "type": "usage"},
        {"kpi": "P5-KPI3", "name": "Workload Growth Velocity", "correlation": 0.88, "type": "growth"},
        {"kpi": "P5-KPI4", "name": "Compute Hour Consumption Trend", "correlation": 0.85, "type": "consumption"}
    ],
    "critical_kpis": [
        {"kpi": "P2-KPI1", "name": "RMA Frequency Rate", "threshold": 2.6, "impact": "$4.4M per 1% increase"}
    ]
}
