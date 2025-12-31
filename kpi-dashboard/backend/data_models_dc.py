"""
Data Center Data Models
DC-specific data models and schemas
"""

from typing import Dict, List, Optional
from datetime import datetime
from kpi_definitions_dc import DC_KPIS

class DCTenant:
    """Data Center Tenant model"""
    def __init__(self, tenant_id: int, tenant_name: str, customer_id: int):
        self.tenant_id = tenant_id
        self.tenant_name = tenant_name
        self.customer_id = customer_id
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict:
        return {
            "tenant_id": self.tenant_id,
            "tenant_name": self.tenant_name,
            "customer_id": self.customer_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

class DCKPIValue:
    """Data Center KPI Value model"""
    def __init__(self, kpi_id: str, tenant_id: int, value: float, timestamp: datetime = None):
        self.kpi_id = kpi_id
        self.tenant_id = tenant_id
        self.value = value
        self.timestamp = timestamp or datetime.now()
        self.kpi_def = DC_KPIS.get(kpi_id)
    
    def to_dict(self) -> Dict:
        return {
            "kpi_id": self.kpi_id,
            "kpi_name": self.kpi_def.get("name") if self.kpi_def else self.kpi_id,
            "pillar": self.kpi_def.get("pillar") if self.kpi_def else "Unknown",
            "tenant_id": self.tenant_id,
            "value": self.value,
            "unit": self.kpi_def.get("unit") if self.kpi_def else "",
            "target": self.kpi_def.get("target") if self.kpi_def else 0,
            "timestamp": self.timestamp.isoformat()
        }

class DCHealthSnapshot:
    """Data Center Health Snapshot model"""
    def __init__(self, tenant_id: int, overall_score: float, category_scores: Dict, timestamp: datetime = None):
        self.tenant_id = tenant_id
        self.overall_score = overall_score
        self.category_scores = category_scores
        self.timestamp = timestamp or datetime.now()
    
    def to_dict(self) -> Dict:
        return {
            "tenant_id": self.tenant_id,
            "overall_score": self.overall_score,
            "health_status": self.get_health_status(),
            "category_scores": self.category_scores,
            "timestamp": self.timestamp.isoformat()
        }
    
    def get_health_status(self) -> str:
        if self.overall_score >= 70:
            return "healthy"
        elif self.overall_score >= 50:
            return "at_risk"
        else:
            return "critical"

class DCAlert:
    """Data Center Alert model"""
    def __init__(self, alert_id: str, tenant_id: int, kpi_id: str, severity: str, message: str):
        self.alert_id = alert_id
        self.tenant_id = tenant_id
        self.kpi_id = kpi_id
        self.severity = severity
        self.message = message
        self.timestamp = datetime.now()
        self.acknowledged = False
    
    def to_dict(self) -> Dict:
        return {
            "alert_id": self.alert_id,
            "tenant_id": self.tenant_id,
            "kpi_id": self.kpi_id,
            "kpi_name": DC_KPIS.get(self.kpi_id, {}).get("name", self.kpi_id),
            "severity": self.severity,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "acknowledged": self.acknowledged
        }

