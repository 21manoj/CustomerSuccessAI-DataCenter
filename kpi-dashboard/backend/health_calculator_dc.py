"""
Data Center Health Score Calculator
Calculates health scores for DC accounts based on DC KPIs
"""

from typing import Dict, List, Optional
from kpi_definitions_dc import DC_KPIS, calculate_risk_band
from health_score_engine import HealthScoreEngine

# DC-specific category weights
DC_CATEGORY_WEIGHTS = {
    "Infrastructure & Performance": 0.30,  # 30% - Most important for DC
    "Service Delivery": 0.25,            # 25%
    "Customer Sentiment": 0.15,          # 15%
    "Business Outcomes": 0.20,          # 20%
    "Relationship Strength": 0.10        # 10%
}

def calculate_dc_health_score(account_kpis: List[Dict]) -> Dict:
    """
    Calculate health score for a DC account
    Args:
        account_kpis: List of KPI dictionaries with kpi_id, value, etc.
    Returns:
        Dictionary with overall score, category scores, and breakdown
    """
    if not account_kpis:
        return {
            "overall_score": 0,
            "health_status": "unknown",
            "category_scores": {},
            "kpi_count": 0
        }
    
    # Group KPIs by pillar/category
    category_kpis = {}
    for kpi_data in account_kpis:
        kpi_id = kpi_data.get("kpi_id") or kpi_data.get("kpi_parameter")
        kpi_def = DC_KPIS.get(kpi_id) if isinstance(kpi_id, str) else None
        
        if not kpi_def:
            # Try to find by name
            kpi_name = kpi_data.get("kpi_parameter", "")
            for k_id, k_def in DC_KPIS.items():
                if k_def.get("name") == kpi_name:
                    kpi_def = k_def
                    break
        
        if kpi_def:
            pillar = kpi_def.get("pillar", "Unknown")
            if pillar not in category_kpis:
                category_kpis[pillar] = []
            category_kpis[pillar].append(kpi_data)
    
    # Calculate category scores
    category_scores = {}
    total_weighted_score = 0
    total_weight = 0
    
    for category, kpis in category_kpis.items():
        category_weight = DC_CATEGORY_WEIGHTS.get(category, 0.20)
        
        # Calculate average health for this category
        category_health_scores = []
        for kpi in kpis:
            value = kpi.get("data") or kpi.get("value")
            if value is None:
                continue
            
            # Parse value
            try:
                if isinstance(value, str):
                    # Remove units and parse
                    value_str = value.replace("%", "").replace("$", "").replace(",", "").strip()
                    numeric_value = float(value_str)
                else:
                    numeric_value = float(value)
            except (ValueError, TypeError):
                continue
            
            # Get risk band
            kpi_id = kpi.get("kpi_id") or kpi.get("kpi_parameter")
            risk_band = calculate_risk_band(kpi_id, numeric_value)
            
            # Convert risk band to score (0-100)
            if risk_band == "healthy":
                score = 85
            elif risk_band == "at_risk":
                score = 60
            elif risk_band == "critical":
                score = 30
            elif risk_band == "expansion":
                score = 95  # Expansion is good
            else:
                score = 50
            
            category_health_scores.append(score)
        
        if category_health_scores:
            avg_category_score = sum(category_health_scores) / len(category_health_scores)
        else:
            avg_category_score = 0
        
        category_scores[category] = {
            "score": avg_category_score,
            "weight": category_weight,
            "weighted_score": avg_category_score * category_weight,
            "kpi_count": len(kpis)
        }
        
        total_weighted_score += avg_category_score * category_weight
        total_weight += category_weight
    
    # Calculate overall score
    overall_score = total_weighted_score / total_weight if total_weight > 0 else 0
    
    # Determine health status
    if overall_score >= 70:
        health_status = "healthy"
    elif overall_score >= 50:
        health_status = "at_risk"
    else:
        health_status = "critical"
    
    return {
        "overall_score": round(overall_score, 2),
        "health_status": health_status,
        "category_scores": category_scores,
        "kpi_count": len(account_kpis),
        "valid_kpi_count": sum(len(kpis) for kpis in category_kpis.values())
    }

