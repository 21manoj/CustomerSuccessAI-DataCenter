"""
Data Center KPI Calculator
Calculates DC-specific KPI metrics and aggregations
"""

from typing import Dict, List, Optional
from kpi_definitions_dc import DC_KPIS, get_kpi, get_kpis_by_pillar

def calculate_kpi_value(kpi_id: str, raw_value: any) -> Optional[float]:
    """
    Parse and normalize KPI value for DC KPIs
    """
    if raw_value is None:
        return None
    
    # Convert to string and clean
    value_str = str(raw_value).strip()
    
    # Remove common units
    value_str = value_str.replace("%", "").replace("$", "").replace(",", "").strip()
    
    # Handle time units
    if "hours" in value_str.lower():
        value_str = value_str.lower().replace("hours", "").strip()
    elif "minutes" in value_str.lower():
        value_str = value_str.lower().replace("minutes", "").strip()
        try:
            return float(value_str) / 60.0  # Convert minutes to hours
        except ValueError:
            return None
    
    # Handle K/M suffixes
    if "k" in value_str.lower():
        value_str = value_str.lower().replace("k", "")
        try:
            return float(value_str) * 1000
        except ValueError:
            return None
    elif "m" in value_str.lower():
        value_str = value_str.lower().replace("m", "")
        try:
            return float(value_str) * 1000000
        except ValueError:
            return None
    
    try:
        return float(value_str)
    except ValueError:
        return None

def calculate_pillar_score(pillar: str, kpi_values: List[Dict]) -> Dict:
    """
    Calculate aggregate score for a pillar
    """
    pillar_kpis = get_kpis_by_pillar(pillar)
    if not pillar_kpis:
        return {"score": 0, "kpi_count": 0, "valid_count": 0}
    
    scores = []
    for kpi_data in kpi_values:
        kpi_id = kpi_data.get("kpi_id") or kpi_data.get("kpi_parameter")
        kpi_def = get_kpi(kpi_id)
        
        if kpi_def and kpi_def.get("pillar") == pillar:
            value = calculate_kpi_value(kpi_id, kpi_data.get("data") or kpi_data.get("value"))
            if value is not None:
                # Calculate score based on target
                target = kpi_def.get("target", 0)
                if target > 0:
                    # Simple percentage of target
                    score = min(100, (value / target) * 100) if value >= 0 else 0
                    scores.append(score)
    
    if scores:
        avg_score = sum(scores) / len(scores)
    else:
        avg_score = 0
    
    return {
        "score": round(avg_score, 2),
        "kpi_count": len(pillar_kpis),
        "valid_count": len(scores)
    }

def get_kpi_trend(kpi_id: str, historical_values: List[float]) -> Dict:
    """
    Calculate trend for a KPI over time
    """
    if len(historical_values) < 2:
        return {"trend": "stable", "change": 0, "direction": "none"}
    
    recent = historical_values[-1]
    previous = historical_values[-2]
    
    if previous == 0:
        change_pct = 0
    else:
        change_pct = ((recent - previous) / previous) * 100
    
    if change_pct > 5:
        trend = "improving"
        direction = "up"
    elif change_pct < -5:
        trend = "declining"
        direction = "down"
    else:
        trend = "stable"
        direction = "none"
    
    return {
        "trend": trend,
        "change": round(change_pct, 2),
        "direction": direction
    }

