"""
Data Center Configuration
DC-specific configuration settings
"""

import os
from typing import Dict

# DC Vertical Configuration
DC_CONFIG = {
    "vertical": "datacenter",
    "name": "Data Center",
    "description": "Data Center Customer Success Management",
    
    # KPI Configuration
    "kpi_count": 31,
    "pillars": [
        "Infrastructure & Performance",
        "Service Delivery",
        "Customer Sentiment",
        "Business Outcomes",
        "Relationship Strength"
    ],
    
    # Category Weights
    "category_weights": {
        "Infrastructure & Performance": 0.30,
        "Service Delivery": 0.25,
        "Customer Sentiment": 0.15,
        "Business Outcomes": 0.20,
        "Relationship Strength": 0.10
    },
    
    # Health Score Thresholds
    "health_thresholds": {
        "healthy": 70,
        "at_risk": 50,
        "critical": 0
    },
    
    # Alert Configuration
    "alert_config": {
        "critical_threshold": 50,
        "warning_threshold": 70,
        "enable_email_alerts": os.getenv("DC_ENABLE_EMAIL_ALERTS", "false").lower() == "true"
    },
    
    # API Configuration
    "api_prefix": "/api/dc",
    "enable_recommendations": True,
    "enable_alerts": True
}

def get_dc_config() -> Dict:
    """Get DC configuration"""
    return DC_CONFIG

def get_dc_category_weight(category: str) -> float:
    """Get weight for a DC category"""
    return DC_CONFIG["category_weights"].get(category, 0.20)

def get_dc_health_threshold(threshold_type: str) -> float:
    """Get health threshold"""
    return DC_CONFIG["health_thresholds"].get(threshold_type, 0)

