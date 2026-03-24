#!/usr/bin/env python3
"""
SaaS Premium Vertical - KPI Definitions
Product-led SaaS companies

Defines 41 KPIs across 5 pillars for SaaS Premium customers.
Auto-generated from load-driver/saas_premium_kpi_catalog.json (v2.0)

Pillars:
- P1: Product Adoption & Usage (30%)
- P2: Customer Engagement (15%)
- P3: Customer Sentiment & Support (20%)
- P4: Partner & Ecosystem Health (15%)
- P5: Revenue & Growth (20%)
"""

from typing import Dict, Any


# ============================================================
# PILLAR DEFINITIONS
# ============================================================

SAAS_PILLARS: Dict[str, Dict[str, Any]] = {
    "P1": {
        "name": "Product Adoption & Usage",
        "weight_l2": 0.3,
        "kpi_count": 9
    },
    "P2": {
        "name": "Customer Engagement",
        "weight_l2": 0.15,
        "kpi_count": 7
    },
    "P3": {
        "name": "Customer Sentiment & Support",
        "weight_l2": 0.2,
        "kpi_count": 10
    },
    "P4": {
        "name": "Partner & Ecosystem Health",
        "weight_l2": 0.15,
        "kpi_count": 7
    },
    "P5": {
        "name": "Revenue & Growth",
        "weight_l2": 0.2,
        "kpi_count": 8
    },
}


# ============================================================
# KPI DEFINITIONS (41 KPIs)
# ============================================================

SAAS_KPIS: Dict[str, Dict[str, Any]] = {

    # ========================================
    # P1: PRODUCT ADOPTION & USAGE (9 KPIs, 30%)
    # ========================================

    "P1-KPI1": {
        "name": "Daily Active Users (DAU) Rate",
        "pillar": "P1",
        "weight_l1": 0.16,
        "impact": "high",  # derived from weight_l1 relative to pillar avg
        "frequency": "daily",
        "unit": "percentage",
        "higher_is_better": True,
        "target": {"operator": ">", "value": 60},
        "ranges": {
            "healthy": {"min": 60, "max": 95},
            "risk": {"min": 35, "max": 60},
            "critical": {"min": 0, "max": 35},
        },
        "data_source": "OBR",
    },
    "P1-KPI2": {
        "name": "Feature Adoption Breadth",
        "pillar": "P1",
        "weight_l1": 0.15,
        "impact": "medium",  # derived from weight_l1 relative to pillar avg
        "frequency": "weekly",
        "unit": "percentage",
        "higher_is_better": True,
        "target": {"operator": ">", "value": 45},
        "ranges": {
            "healthy": {"min": 45, "max": 90},
            "risk": {"min": 25, "max": 45},
            "critical": {"min": 0, "max": 25},
        },
        "data_source": "OBR",
    },
    "P1-KPI3": {
        "name": "Time-to-First-Value (TTFV)",
        "pillar": "P1",
        "weight_l1": 0.14,
        "impact": "medium",  # derived from weight_l1 relative to pillar avg
        "frequency": "monthly",
        "unit": "days",
        "higher_is_better": False,
        "target": {"operator": "<", "value": 21},
        "ranges": {
            "healthy": {"min": 1, "max": 21},
            "risk": {"min": 21, "max": 45},
            "critical": {"min": 45, "max": 120},
        },
        "data_source": "CSR",
    },
    "P1-KPI4": {
        "name": "Login Frequency",
        "pillar": "P1",
        "weight_l1": 0.12,
        "impact": "medium",  # derived from weight_l1 relative to pillar avg
        "frequency": "weekly",
        "unit": "sessions/user/week",
        "higher_is_better": True,
        "target": {"operator": ">", "value": 3.5},
        "ranges": {
            "healthy": {"min": 3.5, "max": 12},
            "risk": {"min": 1.5, "max": 3.5},
            "critical": {"min": 0, "max": 1.5},
        },
        "data_source": "OBR",
    },
    "P1-KPI5": {
        "name": "Onboarding Completion Rate",
        "pillar": "P1",
        "weight_l1": 0.12,
        "impact": "medium",  # derived from weight_l1 relative to pillar avg
        "frequency": "monthly",
        "unit": "percentage",
        "higher_is_better": True,
        "target": {"operator": ">", "value": 80},
        "ranges": {
            "healthy": {"min": 80, "max": 100},
            "risk": {"min": 50, "max": 80},
            "critical": {"min": 0, "max": 50},
        },
        "data_source": "CSR",
    },
    "P1-KPI6": {
        "name": "Workflow Completion Rate",
        "pillar": "P1",
        "weight_l1": 0.09,
        "impact": "medium",  # derived from weight_l1 relative to pillar avg
        "frequency": "weekly",
        "unit": "percentage",
        "higher_is_better": True,
        "target": {"operator": ">", "value": 75},
        "ranges": {
            "healthy": {"min": 75, "max": 99},
            "risk": {"min": 50, "max": 75},
            "critical": {"min": 0, "max": 50},
        },
        "data_source": "OBR",
    },
    "P1-KPI7": {
        "name": "Module Activation Rate",
        "pillar": "P1",
        "weight_l1": 0.08,
        "impact": "low",  # derived from weight_l1 relative to pillar avg
        "frequency": "monthly",
        "unit": "percentage",
        "higher_is_better": True,
        "target": {"operator": ">", "value": 70},
        "ranges": {
            "healthy": {"min": 70, "max": 100},
            "risk": {"min": 40, "max": 70},
            "critical": {"min": 0, "max": 40},
        },
        "data_source": "OBR",
    },
    "P1-KPI8": {
        "name": "API Integration Usage",
        "pillar": "P1",
        "weight_l1": 0.07,
        "impact": "low",  # derived from weight_l1 relative to pillar avg
        "frequency": "weekly",
        "unit": "percentage",
        "higher_is_better": True,
        "target": {"operator": ">", "value": 30},
        "ranges": {
            "healthy": {"min": 30, "max": 85},
            "risk": {"min": 15, "max": 30},
            "critical": {"min": 0, "max": 15},
        },
        "data_source": "OBR",
    },
    "P1-KPI9": {
        "name": "Knowledge Base Usage",
        "pillar": "P1",
        "weight_l1": 0.07,
        "impact": "low",  # derived from weight_l1 relative to pillar avg
        "frequency": "monthly",
        "unit": "percentage",
        "higher_is_better": True,
        "target": {"operator": ">", "value": 40},
        "ranges": {
            "healthy": {"min": 40, "max": 90},
            "risk": {"min": 20, "max": 40},
            "critical": {"min": 0, "max": 20},
        },
        "data_source": "OBR",
    },

    # ========================================
    # P2: CUSTOMER ENGAGEMENT (7 KPIs, 15%)
    # ========================================

    "P2-KPI1": {
        "name": "Executive Sponsor Engagement",
        "pillar": "P2",
        "weight_l1": 0.22,
        "impact": "high",  # derived from weight_l1 relative to pillar avg
        "frequency": "monthly",
        "unit": "score",
        "higher_is_better": True,
        "target": {"operator": ">", "value": 70},
        "ranges": {
            "healthy": {"min": 70, "max": 100},
            "risk": {"min": 40, "max": 70},
            "critical": {"min": 0, "max": 40},
        },
        "data_source": "CSR",
    },
    "P2-KPI2": {
        "name": "QBR Attendance Rate",
        "pillar": "P2",
        "weight_l1": 0.18,
        "impact": "medium",  # derived from weight_l1 relative to pillar avg
        "frequency": "quarterly",
        "unit": "percentage",
        "higher_is_better": True,
        "target": {"operator": ">", "value": 85},
        "ranges": {
            "healthy": {"min": 85, "max": 100},
            "risk": {"min": 50, "max": 85},
            "critical": {"min": 0, "max": 50},
        },
        "data_source": "CSR",
    },
    "P2-KPI3": {
        "name": "Training Completion Rate",
        "pillar": "P2",
        "weight_l1": 0.15,
        "impact": "medium",  # derived from weight_l1 relative to pillar avg
        "frequency": "monthly",
        "unit": "percentage",
        "higher_is_better": True,
        "target": {"operator": ">", "value": 60},
        "ranges": {
            "healthy": {"min": 60, "max": 100},
            "risk": {"min": 30, "max": 60},
            "critical": {"min": 0, "max": 30},
        },
        "data_source": "CSR",
    },
    "P2-KPI4": {
        "name": "Community Participation Score",
        "pillar": "P2",
        "weight_l1": 0.12,
        "impact": "medium",  # derived from weight_l1 relative to pillar avg
        "frequency": "monthly",
        "unit": "score",
        "higher_is_better": True,
        "target": {"operator": ">", "value": 40},
        "ranges": {
            "healthy": {"min": 40, "max": 100},
            "risk": {"min": 20, "max": 40},
            "critical": {"min": 0, "max": 20},
        },
        "data_source": "CSR",
    },
    "P2-KPI5": {
        "name": "CSM Interaction Frequency",
        "pillar": "P2",
        "weight_l1": 0.13,
        "impact": "medium",  # derived from weight_l1 relative to pillar avg
        "frequency": "monthly",
        "unit": "interactions/month",
        "higher_is_better": True,
        "target": {"operator": ">", "value": 4},
        "ranges": {
            "healthy": {"min": 4, "max": 15},
            "risk": {"min": 2, "max": 4},
            "critical": {"min": 0, "max": 2},
        },
        "data_source": "CSR",
    },
    "P2-KPI6": {
        "name": "Webinar/Event Attendance",
        "pillar": "P2",
        "weight_l1": 0.1,
        "impact": "low",  # derived from weight_l1 relative to pillar avg
        "frequency": "monthly",
        "unit": "percentage",
        "higher_is_better": True,
        "target": {"operator": ">", "value": 25},
        "ranges": {
            "healthy": {"min": 25, "max": 80},
            "risk": {"min": 10, "max": 25},
            "critical": {"min": 0, "max": 10},
        },
        "data_source": "CSR",
    },
    "P2-KPI7": {
        "name": "Customer Advocacy Score",
        "pillar": "P2",
        "weight_l1": 0.1,
        "impact": "low",  # derived from weight_l1 relative to pillar avg
        "frequency": "quarterly",
        "unit": "score",
        "higher_is_better": True,
        "target": {"operator": ">", "value": 50},
        "ranges": {
            "healthy": {"min": 50, "max": 100},
            "risk": {"min": 25, "max": 50},
            "critical": {"min": 0, "max": 25},
        },
        "data_source": "CSR",
    },

    # ========================================
    # P3: CUSTOMER SENTIMENT & SUPPORT (10 KPIs, 20%)
    # ========================================

    "P3-KPI1": {
        "name": "Ticket Resolution Time",
        "pillar": "P3",
        "weight_l1": 0.13,
        "impact": "medium",  # derived from weight_l1 relative to pillar avg
        "frequency": "daily",
        "unit": "hours",
        "higher_is_better": False,
        "target": {"operator": "<", "value": 24},
        "ranges": {
            "healthy": {"min": 1, "max": 24},
            "risk": {"min": 24, "max": 48},
            "critical": {"min": 48, "max": 168},
        },
        "data_source": "SBR",
    },
    "P3-KPI10": {
        "name": "Customer Complaints Rate",
        "pillar": "P3",
        "weight_l1": 0.07,
        "impact": "low",  # derived from weight_l1 relative to pillar avg
        "frequency": "monthly",
        "unit": "per_1000_users",
        "higher_is_better": False,
        "target": {"operator": "<", "value": 5},
        "ranges": {
            "healthy": {"min": 0, "max": 5},
            "risk": {"min": 5, "max": 12},
            "critical": {"min": 12, "max": 50},
        },
        "data_source": "SBR",
    },
    "P3-KPI2": {
        "name": "CSAT Score",
        "pillar": "P3",
        "weight_l1": 0.14,
        "impact": "high",  # derived from weight_l1 relative to pillar avg
        "frequency": "monthly",
        "unit": "score",
        "higher_is_better": True,
        "target": {"operator": ">", "value": 85},
        "ranges": {
            "healthy": {"min": 85, "max": 100},
            "risk": {"min": 65, "max": 85},
            "critical": {"min": 0, "max": 65},
        },
        "data_source": "SBR",
    },
    "P3-KPI3": {
        "name": "Net Promoter Score (NPS)",
        "pillar": "P3",
        "weight_l1": 0.14,
        "impact": "high",  # derived from weight_l1 relative to pillar avg
        "frequency": "quarterly",
        "unit": "score",
        "higher_is_better": True,
        "target": {"operator": ">", "value": 40},
        "ranges": {
            "healthy": {"min": 40, "max": 100},
            "risk": {"min": 10, "max": 40},
            "critical": {"min": -100, "max": 10},
        },
        "data_source": "CSR",
    },
    "P3-KPI4": {
        "name": "Escalation Rate",
        "pillar": "P3",
        "weight_l1": 0.1,
        "impact": "medium",  # derived from weight_l1 relative to pillar avg
        "frequency": "monthly",
        "unit": "percentage",
        "higher_is_better": False,
        "target": {"operator": "<", "value": 8},
        "ranges": {
            "healthy": {"min": 0, "max": 8},
            "risk": {"min": 8, "max": 15},
            "critical": {"min": 15, "max": 50},
        },
        "data_source": "SBR",
    },
    "P3-KPI5": {
        "name": "First Contact Resolution Rate",
        "pillar": "P3",
        "weight_l1": 0.1,
        "impact": "medium",  # derived from weight_l1 relative to pillar avg
        "frequency": "monthly",
        "unit": "percentage",
        "higher_is_better": True,
        "target": {"operator": ">", "value": 70},
        "ranges": {
            "healthy": {"min": 70, "max": 100},
            "risk": {"min": 45, "max": 70},
            "critical": {"min": 0, "max": 45},
        },
        "data_source": "SBR",
    },
    "P3-KPI6": {
        "name": "SLA Compliance Rate",
        "pillar": "P3",
        "weight_l1": 0.08,
        "impact": "low",  # derived from weight_l1 relative to pillar avg
        "frequency": "monthly",
        "unit": "percentage",
        "higher_is_better": True,
        "target": {"operator": ">", "value": 95},
        "ranges": {
            "healthy": {"min": 95, "max": 100},
            "risk": {"min": 85, "max": 95},
            "critical": {"min": 0, "max": 85},
        },
        "data_source": "SBR",
    },
    "P3-KPI7": {
        "name": "Support Ticket Volume Trend",
        "pillar": "P3",
        "weight_l1": 0.07,
        "impact": "low",  # derived from weight_l1 relative to pillar avg
        "frequency": "monthly",
        "unit": "percentage_mom",
        "higher_is_better": False,
        "target": {"operator": "<", "value": 5},
        "ranges": {
            "healthy": {"min": -20, "max": 5},
            "risk": {"min": 5, "max": 15},
            "critical": {"min": 15, "max": 100},
        },
        "data_source": "SBR",
    },
    "P3-KPI8": {
        "name": "Customer Effort Score (CES)",
        "pillar": "P3",
        "weight_l1": 0.1,
        "impact": "medium",  # derived from weight_l1 relative to pillar avg
        "frequency": "monthly",
        "unit": "score",
        "higher_is_better": True,
        "target": {"operator": ">", "value": 5.5},
        "ranges": {
            "healthy": {"min": 5.5, "max": 7.0},
            "risk": {"min": 4.0, "max": 5.5},
            "critical": {"min": 1.0, "max": 4.0},
        },
        "data_source": "SBR",
    },
    "P3-KPI9": {
        "name": "Case Deflection Rate",
        "pillar": "P3",
        "weight_l1": 0.07,
        "impact": "low",  # derived from weight_l1 relative to pillar avg
        "frequency": "monthly",
        "unit": "percentage",
        "higher_is_better": True,
        "target": {"operator": ">", "value": 30},
        "ranges": {
            "healthy": {"min": 30, "max": 75},
            "risk": {"min": 15, "max": 30},
            "critical": {"min": 0, "max": 15},
        },
        "data_source": "SBR",
    },

    # ========================================
    # P4: PARTNER & ECOSYSTEM HEALTH (7 KPIs, 15%)
    # ========================================

    "P4-KPI1": {
        "name": "Partner-Sourced Revenue Rate",
        "pillar": "P4",
        "weight_l1": 0.2,
        "impact": "high",  # derived from weight_l1 relative to pillar avg
        "frequency": "monthly",
        "unit": "percentage",
        "higher_is_better": True,
        "target": {"operator": ">", "value": 25},
        "ranges": {
            "healthy": {"min": 25, "max": 70},
            "risk": {"min": 12, "max": 25},
            "critical": {"min": 0, "max": 12},
        },
        "data_source": "VBR",
    },
    "P4-KPI2": {
        "name": "Partner Certification Level",
        "pillar": "P4",
        "weight_l1": 0.16,
        "impact": "medium",  # derived from weight_l1 relative to pillar avg
        "frequency": "quarterly",
        "unit": "score",
        "higher_is_better": True,
        "target": {"operator": ">", "value": 60},
        "ranges": {
            "healthy": {"min": 60, "max": 100},
            "risk": {"min": 35, "max": 60},
            "critical": {"min": 0, "max": 35},
        },
        "data_source": "CSR",
    },
    "P4-KPI3": {
        "name": "Partner Deal Registration Rate",
        "pillar": "P4",
        "weight_l1": 0.15,
        "impact": "medium",  # derived from weight_l1 relative to pillar avg
        "frequency": "monthly",
        "unit": "percentage",
        "higher_is_better": True,
        "target": {"operator": ">", "value": 40},
        "ranges": {
            "healthy": {"min": 40, "max": 85},
            "risk": {"min": 20, "max": 40},
            "critical": {"min": 0, "max": 20},
        },
        "data_source": "VBR",
    },
    "P4-KPI4": {
        "name": "Channel Conflict Resolution Time",
        "pillar": "P4",
        "weight_l1": 0.13,
        "impact": "medium",  # derived from weight_l1 relative to pillar avg
        "frequency": "monthly",
        "unit": "days",
        "higher_is_better": False,
        "target": {"operator": "<", "value": 14},
        "ranges": {
            "healthy": {"min": 1, "max": 14},
            "risk": {"min": 14, "max": 30},
            "critical": {"min": 30, "max": 90},
        },
        "data_source": "CSR",
    },
    "P4-KPI5": {
        "name": "Partner Satisfaction Score",
        "pillar": "P4",
        "weight_l1": 0.14,
        "impact": "medium",  # derived from weight_l1 relative to pillar avg
        "frequency": "quarterly",
        "unit": "score",
        "higher_is_better": True,
        "target": {"operator": ">", "value": 75},
        "ranges": {
            "healthy": {"min": 75, "max": 100},
            "risk": {"min": 50, "max": 75},
            "critical": {"min": 0, "max": 50},
        },
        "data_source": "CSR",
    },
    "P4-KPI6": {
        "name": "Co-Marketing Campaign ROI",
        "pillar": "P4",
        "weight_l1": 0.12,
        "impact": "medium",  # derived from weight_l1 relative to pillar avg
        "frequency": "quarterly",
        "unit": "percentage",
        "higher_is_better": True,
        "target": {"operator": ">", "value": 200},
        "ranges": {
            "healthy": {"min": 200, "max": 800},
            "risk": {"min": 100, "max": 200},
            "critical": {"min": 0, "max": 100},
        },
        "data_source": "VBR",
    },
    "P4-KPI7": {
        "name": "Partner Technical Enablement Score",
        "pillar": "P4",
        "weight_l1": 0.1,
        "impact": "low",  # derived from weight_l1 relative to pillar avg
        "frequency": "quarterly",
        "unit": "score",
        "higher_is_better": True,
        "target": {"operator": ">", "value": 65},
        "ranges": {
            "healthy": {"min": 65, "max": 100},
            "risk": {"min": 40, "max": 65},
            "critical": {"min": 0, "max": 40},
        },
        "data_source": "CSR",
    },

    # ========================================
    # P5: REVENUE & GROWTH (8 KPIs, 20%)
    # ========================================

    "P5-KPI1": {
        "name": "Net Revenue Retention (NRR)",
        "pillar": "P5",
        "weight_l1": 0.2,
        "impact": "high",  # derived from weight_l1 relative to pillar avg
        "frequency": "monthly",
        "unit": "percentage",
        "higher_is_better": True,
        "target": {"operator": ">", "value": 110},
        "ranges": {
            "healthy": {"min": 110, "max": 160},
            "risk": {"min": 95, "max": 110},
            "critical": {"min": 0, "max": 95},
        },
        "data_source": "VBR",
    },
    "P5-KPI2": {
        "name": "Gross Revenue Retention (GRR)",
        "pillar": "P5",
        "weight_l1": 0.16,
        "impact": "medium",  # derived from weight_l1 relative to pillar avg
        "frequency": "monthly",
        "unit": "percentage",
        "higher_is_better": True,
        "target": {"operator": ">", "value": 92},
        "ranges": {
            "healthy": {"min": 92, "max": 100},
            "risk": {"min": 85, "max": 92},
            "critical": {"min": 0, "max": 85},
        },
        "data_source": "VBR",
    },
    "P5-KPI3": {
        "name": "Expansion Revenue Rate",
        "pillar": "P5",
        "weight_l1": 0.13,
        "impact": "medium",  # derived from weight_l1 relative to pillar avg
        "frequency": "monthly",
        "unit": "percentage",
        "higher_is_better": True,
        "target": {"operator": ">", "value": 15},
        "ranges": {
            "healthy": {"min": 15, "max": 50},
            "risk": {"min": 5, "max": 15},
            "critical": {"min": 0, "max": 5},
        },
        "data_source": "VBR",
    },
    "P5-KPI4": {
        "name": "Annual Contract Value (ACV) Growth",
        "pillar": "P5",
        "weight_l1": 0.1,
        "impact": "medium",  # derived from weight_l1 relative to pillar avg
        "frequency": "quarterly",
        "unit": "percentage",
        "higher_is_better": True,
        "target": {"operator": ">", "value": 12},
        "ranges": {
            "healthy": {"min": 12, "max": 40},
            "risk": {"min": 5, "max": 12},
            "critical": {"min": -20, "max": 5},
        },
        "data_source": "VBR",
    },
    "P5-KPI5": {
        "name": "Renewal Probability (90d)",
        "pillar": "P5",
        "weight_l1": 0.14,
        "impact": "medium",  # derived from weight_l1 relative to pillar avg
        "frequency": "monthly",
        "unit": "percentage",
        "higher_is_better": True,
        "target": {"operator": ">", "value": 85},
        "ranges": {
            "healthy": {"min": 85, "max": 100},
            "risk": {"min": 60, "max": 85},
            "critical": {"min": 0, "max": 60},
        },
        "data_source": "CSR",
    },
    "P5-KPI6": {
        "name": "Churn Risk Score",
        "pillar": "P5",
        "weight_l1": 0.09,
        "impact": "low",  # derived from weight_l1 relative to pillar avg
        "frequency": "monthly",
        "unit": "percentage",
        "higher_is_better": False,
        "target": {"operator": "<", "value": 20},
        "ranges": {
            "healthy": {"min": 0, "max": 20},
            "risk": {"min": 20, "max": 40},
            "critical": {"min": 40, "max": 100},
        },
        "data_source": "CSR",
    },
    "P5-KPI7": {
        "name": "Customer Lifetime Value Trend",
        "pillar": "P5",
        "weight_l1": 0.08,
        "impact": "low",  # derived from weight_l1 relative to pillar avg
        "frequency": "quarterly",
        "unit": "ratio",
        "higher_is_better": True,
        "target": {"operator": ">", "value": 2.0},
        "ranges": {
            "healthy": {"min": 2.0, "max": 8.0},
            "risk": {"min": 1.2, "max": 2.0},
            "critical": {"min": 0, "max": 1.2},
        },
        "data_source": "VBR",
    },
    "P5-KPI8": {
        "name": "Share of Wallet",
        "pillar": "P5",
        "weight_l1": 0.1,
        "impact": "medium",  # derived from weight_l1 relative to pillar avg
        "frequency": "quarterly",
        "unit": "percentage",
        "higher_is_better": True,
        "target": {"operator": ">", "value": 35},
        "ranges": {
            "healthy": {"min": 35, "max": 80},
            "risk": {"min": 15, "max": 35},
            "critical": {"min": 0, "max": 15},
        },
        "data_source": "VBR",
    },
}


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================

def get_kpi(code: str) -> Dict:
    """Get KPI definition by code (e.g. P1-KPI1)."""
    return SAAS_KPIS.get(code)


def get_pillar(code: str) -> Dict:
    """Get pillar definition by code (e.g. P1)."""
    return SAAS_PILLARS.get(code)


def get_kpis_for_pillar(pillar_code: str) -> Dict[str, Dict]:
    """Get all KPIs for a pillar."""
    return {k: v for k, v in SAAS_KPIS.items() if v["pillar"] == pillar_code}

