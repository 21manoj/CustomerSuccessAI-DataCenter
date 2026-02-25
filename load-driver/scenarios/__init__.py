"""
Load test scenarios for CS Pulse platform

Scenario Map:
  1   - Onboarding (register → upload → process → score → verify)
  2a  - KPI Simulation (12-month drift + score recalc)
  2b  - RAG Queries (multi-account vector search)
  2c  - Signal Detection (alerts + playbook triggers)
  2d  - RACI Reports (execution reports + validation)
  2e  - Churn Lifecycle (archive + hard delete)
  3   - Tenant Isolation (12 cross-tenant security tests)
  4   - Cleanup (FK-safe customer data deletion)
  5   - ROI Power-of-1 (historical + forward projections)
  6   - N8N Workflow (playbook handoff + webhook callbacks)
"""

from .base import BaseScenario
from .scenario_onboarding import ScenarioOnboarding
from .scenario_kpi_simulation import ScenarioKpiSimulation
from .scenario_rag_queries import ScenarioRagQueries
from .scenario_signal_detection import ScenarioSignalDetection
from .scenario_raci_reports import ScenarioRaciReports
from .scenario_churn_lifecycle import ScenarioChurnLifecycle
from .scenario_tenant_isolation import ScenarioTenantIsolation
from .scenario_cleanup import ScenarioCleanup
from .scenario_roi_power_of_1 import ScenarioRoiPowerOf1
from .scenario_n8n_workflow import ScenarioN8nWorkflow

__all__ = [
    'BaseScenario',
    'ScenarioOnboarding',
    'ScenarioKpiSimulation',
    'ScenarioRagQueries',
    'ScenarioSignalDetection',
    'ScenarioRaciReports',
    'ScenarioChurnLifecycle',
    'ScenarioTenantIsolation',
    'ScenarioCleanup',
    'ScenarioRoiPowerOf1',
    'ScenarioN8nWorkflow',
]
