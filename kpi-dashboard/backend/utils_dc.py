"""
Data Center Utilities
Helper functions for DC vertical operations
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from kpi_definitions_dc import DC_KPIS

def format_dc_kpi_value(value: Any, unit: str = "") -> str:
    """Format KPI value with appropriate unit"""
    if value is None:
        return "N/A"
    
    try:
        numeric_value = float(value)
    except (ValueError, TypeError):
        return str(value)
    
    if unit == "%":
        return f"{numeric_value:.1f}%"
    elif unit == "$":
        if numeric_value >= 1000000:
            return f"${numeric_value/1000000:.2f}M"
        elif numeric_value >= 1000:
            return f"${numeric_value/1000:.2f}K"
        else:
            return f"${numeric_value:.2f}"
    elif unit == "ms":
        return f"{numeric_value:.1f}ms"
    elif unit == "hours":
        return f"{numeric_value:.1f}h"
    elif unit == "minutes":
        return f"{numeric_value:.0f}m"
    elif unit == "count":
        return f"{int(numeric_value)}"
    else:
        return f"{numeric_value:.2f} {unit}"

def get_dc_pillar_color(pillar: str) -> str:
    """Get color for DC pillar"""
    color_map = {
        "Infrastructure & Performance": "blue",
        "Service Delivery": "green",
        "Customer Sentiment": "yellow",
        "Business Outcomes": "purple",
        "Relationship Strength": "orange"
    }
    return color_map.get(pillar, "gray")

def get_dc_health_status_color(score: float) -> str:
    """Get color for health status"""
    if score >= 70:
        return "green"
    elif score >= 50:
        return "yellow"
    else:
        return "red"

def calculate_dc_utilization_trend(values: List[float]) -> Dict:
    """Calculate utilization trend"""
    if len(values) < 2:
        return {"trend": "stable", "change": 0}
    
    recent = values[-1]
    previous = values[-2] if len(values) > 1 else values[0]
    
    if previous == 0:
        change_pct = 0
    else:
        change_pct = ((recent - previous) / previous) * 100
    
    if change_pct > 5:
        trend = "increasing"
    elif change_pct < -5:
        trend = "decreasing"
    else:
        trend = "stable"
    
    return {
        "trend": trend,
        "change": round(change_pct, 2),
        "current": recent,
        "previous": previous
    }

def validate_dc_kpi_value(kpi_id: str, value: Any) -> bool:
    """Validate KPI value is within expected range"""
    kpi_def = DC_KPIS.get(kpi_id)
    if not kpi_def:
        return False
    
    try:
        numeric_value = float(str(value).replace("%", "").replace("$", "").replace(",", ""))
    except (ValueError, TypeError):
        return False
    
    # Basic range check (can be expanded)
    unit = kpi_def.get("unit", "")
    if unit == "%":
        return 0 <= numeric_value <= 100
    elif unit == "count":
        return numeric_value >= 0
    else:
        return True  # For other units, accept any numeric value

def get_dc_kpi_summary() -> Dict:
    """Get summary of DC KPIs by pillar"""
    summary = {}
    for kpi_id, kpi_def in DC_KPIS.items():
        pillar = kpi_def.get("pillar", "Unknown")
        if pillar not in summary:
            summary[pillar] = {
                "pillar": pillar,
                "kpi_count": 0,
                "kpis": []
            }
        summary[pillar]["kpi_count"] += 1
        summary[pillar]["kpis"].append({
            "id": kpi_id,
            "name": kpi_def.get("name"),
            "unit": kpi_def.get("unit"),
            "target": kpi_def.get("target")
        })
    
    return summary

