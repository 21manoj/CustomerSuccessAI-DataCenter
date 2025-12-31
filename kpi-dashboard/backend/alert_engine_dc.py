"""
Data Center Alert Engine
Monitors DC KPIs and generates alerts based on thresholds
"""

from typing import Dict, List, Optional
from datetime import datetime
from kpi_definitions_dc import DC_KPIS, calculate_risk_band

class DCAlertEngine:
    """Alert engine for Data Center vertical"""
    
    @staticmethod
    def check_kpi_alerts(kpi_id: str, value: float, account_id: int, account_name: str) -> List[Dict]:
        """
        Check if a KPI value triggers any alerts
        Returns list of alert dictionaries
        """
        alerts = []
        kpi_def = DC_KPIS.get(kpi_id)
        
        if not kpi_def:
            return alerts
        
        risk_band = calculate_risk_band(kpi_id, value)
        
        # Generate alert for critical or at_risk bands
        if risk_band in ["critical", "at_risk"]:
            alert = {
                "alert_id": f"{kpi_id}_{account_id}_{datetime.now().timestamp()}",
                "kpi_id": kpi_id,
                "kpi_name": kpi_def.get("name"),
                "account_id": account_id,
                "account_name": account_name,
                "value": value,
                "risk_band": risk_band,
                "severity": "critical" if risk_band == "critical" else "warning",
                "message": f"{kpi_def.get('name')} is {risk_band} for {account_name}",
                "timestamp": datetime.now().isoformat(),
                "pillar": kpi_def.get("pillar")
            }
            alerts.append(alert)
        
        # Check for SLA breaches
        if kpi_id == "DC-SVC-015" and value > 0:  # SLA Breach Count
            alert = {
                "alert_id": f"sla_breach_{account_id}_{datetime.now().timestamp()}",
                "kpi_id": kpi_id,
                "kpi_name": "SLA Breach Count",
                "account_id": account_id,
                "account_name": account_name,
                "value": value,
                "risk_band": "critical",
                "severity": "critical",
                "message": f"SLA breach detected for {account_name}",
                "timestamp": datetime.now().isoformat(),
                "pillar": "Service Delivery"
            }
            alerts.append(alert)
        
        return alerts
    
    @staticmethod
    def check_health_score_alerts(health_score: float, account_id: int, account_name: str) -> Optional[Dict]:
        """
        Check if health score triggers an alert
        """
        if health_score < 50:
            return {
                "alert_id": f"health_critical_{account_id}_{datetime.now().timestamp()}",
                "account_id": account_id,
                "account_name": account_name,
                "health_score": health_score,
                "severity": "critical",
                "message": f"Critical health score for {account_name}: {health_score}",
                "timestamp": datetime.now().isoformat()
            }
        elif health_score < 70:
            return {
                "alert_id": f"health_warning_{account_id}_{datetime.now().timestamp()}",
                "account_id": account_id,
                "account_name": account_name,
                "health_score": health_score,
                "severity": "warning",
                "message": f"At-risk health score for {account_name}: {health_score}",
                "timestamp": datetime.now().isoformat()
            }
        
        return None
    
    @staticmethod
    def aggregate_alerts(alerts: List[Dict]) -> Dict:
        """
        Aggregate alerts by severity and pillar
        """
        aggregated = {
            "total": len(alerts),
            "critical": len([a for a in alerts if a.get("severity") == "critical"]),
            "warning": len([a for a in alerts if a.get("severity") == "warning"]),
            "by_pillar": {},
            "by_account": {}
        }
        
        for alert in alerts:
            pillar = alert.get("pillar", "Unknown")
            account_id = alert.get("account_id")
            
            if pillar not in aggregated["by_pillar"]:
                aggregated["by_pillar"][pillar] = 0
            aggregated["by_pillar"][pillar] += 1
            
            if account_id:
                if account_id not in aggregated["by_account"]:
                    aggregated["by_account"][account_id] = 0
                aggregated["by_account"][account_id] += 1
        
        return aggregated

