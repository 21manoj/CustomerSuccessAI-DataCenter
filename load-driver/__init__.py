"""
CS Pulse External Load Driver
Non-intrusive E2E testing via separate Docker instance

Scenarios:
  1. Onboarding (customer registration + account creation)
  2a. KPI Simulation (12-month KPI drift + score recalc)
  2b. RAG Queries (multi-account question answering)
  2c. Signal Detection (alert triggers + playbook execution)
  2d. RACI Reports (execution report generation)
  2e. Churn Lifecycle (account archival + deletion)
  3. Tenant Isolation (cross-tenant access validation)
  4. Post-test Cleanup (24-table FK-safe deletion)
  5. ROI Power-of-1 (historical + forward ROI validation)
  6. N8N Workflow (playbook handoff + Google Sheets mock)

Usage:
  python driver.py --scenarios 1,2a,2b,2c,2d,2e,3,4,5,6 --customers 1,2,3

Config: .env (CS_PULSE_BASE_URL, OPENAI_API_KEY, QDRANT_URL, etc.)
Results: results/LOAD_TEST_RESULTS.md
"""

__version__ = "0.1.0"
__author__ = "CS Pulse Team"

from .client import CSPulseClient
from .driver import LoadDriver

__all__ = ["CSPulseClient", "LoadDriver"]
