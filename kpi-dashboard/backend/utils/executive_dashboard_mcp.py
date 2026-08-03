"""
Invoke executive dashboard Flask handlers from MCP (same payloads as REST).

Uses X-Customer-ID in a test request context — no HTTP hop, no duplicate logic.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def _response_to_dict(response) -> dict:
    if isinstance(response, tuple):
        body, status = response[0], response[1]
    else:
        body, status = response, 200
    data = body.get_json(silent=True) if hasattr(body, 'get_json') else None
    if data is None:
        return {'error': 'Non-JSON dashboard response', 'http_status': status}
    if status >= 400 or data.get('error'):
        return {
            'error': data.get('error', f'Dashboard request failed ({status})'),
            'http_status': status,
            'details': data,
        }
    return data


def fetch_executive_dashboard(customer_id: int, persona: str, period: Optional[str] = None) -> dict:
    """Return CRO/CFO/CEO dashboard JSON for a tenant (mirrors /api/executive/*)."""
    persona = (persona or '').lower().strip()
    handlers = {
        'cro': ('executive_dashboard_api', 'cro_dashboard'),
        'cfo': ('executive_dashboard_api', 'cfo_dashboard'),
        'ceo': ('executive_dashboard_api', 'ceo_dashboard'),
    }
    if persona not in handlers:
        raise ValueError(f"Unknown persona {persona!r}; expected cro, cfo, or ceo")

    from app_v3_minimal import app

    headers = {'X-Customer-ID': str(int(customer_id))}
    query_string = {}
    if period and persona == 'cro':
        query_string['period'] = period

    mod_name, fn_name = handlers[persona]
    with app.app_context():
        with app.test_request_context(headers=headers, query_string=query_string):
            import importlib
            mod = importlib.import_module(mod_name)
            handler = getattr(mod, fn_name)
            result = _response_to_dict(handler())
            if 'error' not in result:
                result.setdefault('scope', 'customer')
                result.setdefault('customer_id', int(customer_id))
                result.setdefault('persona', persona)
            return result
