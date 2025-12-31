"""
Data Center Recommendation Engine
Generates actionable recommendations based on DC KPI analysis
"""

from typing import Dict, List, Optional
from kpi_definitions_dc import DC_KPIS, get_kpi
from playbooks_dc import get_playbooks_by_trigger

class DCRecommendationEngine:
    """Recommendation engine for Data Center vertical"""
    
    @staticmethod
    def generate_recommendations(account_kpis: List[Dict], health_score: float) -> List[Dict]:
        """
        Generate recommendations based on KPI analysis
        """
        recommendations = []
        
        # Analyze each KPI
        for kpi_data in account_kpis:
            kpi_id = kpi_data.get("kpi_id") or kpi_data.get("kpi_parameter")
            value = kpi_data.get("data") or kpi_data.get("value")
            
            if not value:
                continue
            
            kpi_def = get_kpi(kpi_id)
            if not kpi_def:
                continue
            
            # Get triggered playbooks
            try:
                numeric_value = float(str(value).replace("%", "").replace("$", "").replace(",", ""))
            except (ValueError, TypeError):
                continue
            
            playbooks = get_playbooks_by_trigger(kpi_id, numeric_value)
            
            for playbook in playbooks:
                rec = {
                    "recommendation_id": f"{kpi_id}_{playbook['id']}",
                    "kpi_id": kpi_id,
                    "kpi_name": kpi_def.get("name"),
                    "playbook_id": playbook["id"],
                    "playbook_name": playbook["name"],
                    "priority": "high" if kpi_def.get("risk_bands", {}).get("critical") else "medium",
                    "description": playbook.get("description"),
                    "action_items": [step["action"] for step in playbook.get("steps", [])]
                }
                recommendations.append(rec)
        
        # Add health score based recommendations
        if health_score < 50:
            recommendations.append({
                "recommendation_id": "health_critical_intervention",
                "priority": "critical",
                "description": "Account health is critical. Immediate intervention required.",
                "action_items": [
                    "Schedule executive check-in",
                    "Review all critical KPIs",
                    "Implement emergency remediation plan"
                ]
            })
        elif health_score < 70:
            recommendations.append({
                "recommendation_id": "health_at_risk_monitoring",
                "priority": "high",
                "description": "Account is at risk. Enhanced monitoring recommended.",
                "action_items": [
                    "Increase monitoring frequency",
                    "Review service delivery metrics",
                    "Plan proactive interventions"
                ]
            })
        
        return recommendations
    
    @staticmethod
    def prioritize_recommendations(recommendations: List[Dict]) -> List[Dict]:
        """
        Prioritize recommendations by impact and urgency
        """
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        
        return sorted(
            recommendations,
            key=lambda r: priority_order.get(r.get("priority", "low"), 3)
        )

