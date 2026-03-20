#!/usr/bin/env python3
"""
V2 HTTP client — extends CSPulseClient with helpers used by ScenarioManifestV2.

Keeps load-driver/client.py unchanged for legacy scenarios; V2 validation uses
GET /api/dc2s/health-score/{id} (KPI-derived, works immediately after onboarding).
"""

from typing import Any, Dict, Optional

from client import CSPulseClient


class CSPulseClientV2(CSPulseClient):
    """CSPulseClient + DC2S health-score endpoint for post-ingest validation."""

    def get_dc2s_health_score(
        self, account_id: int, month: str = "aggregate"
    ) -> Optional[Dict[str, Any]]:
        """
        DC2S health from latest KPI rows (works right after onboarding ingest).

        Unlike get_account_scores(), this does not require health_scores rows.
        """
        params = {"month": month} if month else None
        return self.get(f"/api/dc2s/health-score/{account_id}", params=params)
