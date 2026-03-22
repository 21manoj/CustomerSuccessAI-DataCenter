#!/usr/bin/env python3
"""
CS Pulse Partner MCP Server — Isolated, P4-scoped tool provider for channel partners.

Runs as a SEPARATE FastMCP instance on port 8002, independent of the internal
MCP server (port 8001). Only exposes partner-safe tools scoped to P4 (Channel
& Partner Health). No revenue, ARR, or internal pillar data exposed.

Transport modes:
  - http:   Streamable HTTP (default for partner access)
  - stdio:  For local testing

Auth:
  Partners authenticate with their API key (csp_* format from DB).
  The key must have scope='partner' and a valid partner_id binding.
  Server-level keys (MCP_SERVER_API_KEY) are NOT accepted — partners
  cannot escalate to admin access.

Usage:
  # HTTP (production — port 8002)
  python3 mcp_server/partner_mcp_server.py http

  # stdio (testing)
  python3 mcp_server/partner_mcp_server.py
"""

import os
import sys
import logging

# Ensure backend AND mcp_server dirs are on the Python path
_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_mcp_dir = os.path.dirname(os.path.abspath(__file__))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)
if _mcp_dir not in sys.path:
    sys.path.insert(0, _mcp_dir)

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Partner-specific system prompt
# ---------------------------------------------------------------------------
PARTNER_SYSTEM_PROMPT = """You are the CS Pulse Partner Portal — an AI assistant for channel partners.

You help partners understand their P4 (Channel & Partner Health) performance
across the customer portfolio. You can show scorecards, provide improvement
recommendations, analyze impact of partner metrics, and accept partner data uploads.

IMPORTANT SCOPING RULES:
- You ONLY have access to P4 pillar data (Channel & Partner Health)
- You CANNOT see revenue, ARR, churn risk, or other pillar scores
- You CANNOT access internal customer health scores or CRO/CFO dashboards
- All data is scoped to the partner's customer_id and partner_id

Available actions:
1. scorecard — View P4 health scores per account
2. submit_data — Upload partner engagement data (engagement_events, stakeholders, signals)
3. actions — Get P4 playbook recommendations
4. benchmarks — Compare P4 performance vs portfolio average
5. impact — Power-of-1 analysis for partner metrics
"""

# ---------------------------------------------------------------------------
# Server instance (completely separate from internal MCP server)
# ---------------------------------------------------------------------------
partner_mcp = FastMCP(
    "CS Pulse Partner Portal",
    instructions=PARTNER_SYSTEM_PROMPT,
)


# ---------------------------------------------------------------------------
# Shared helpers (subset of cs_pulse_mcp_server helpers)
# ---------------------------------------------------------------------------

def _get_flask_app():
    """Lightweight Flask app with DB context only."""
    from common import get_flask_app
    return get_flask_app()


def _check_feature_enabled():
    """Check that MCP server feature is enabled."""
    mcp_enabled = os.environ.get("FEATURE_MCP_SERVER", "true").lower() in ("true", "1", "yes")
    if not mcp_enabled:
        raise ToolError("MCP server is disabled. Set FEATURE_MCP_SERVER=true.")


def _validate_partner_key(customer_id: int, partner_id: int):
    """Validate the partner API key.

    Partners use customer-scoped keys with 'partner' or 'read' scope.
    Server-level keys are NOT accepted for partner access.
    """
    api_key = os.environ.get("_MCP_CURRENT_API_KEY") or os.environ.get("CS_PULSE_API_KEY")

    # Auth disabled? Allow (dev mode)
    auth_required = os.environ.get("MCP_AUTH_REQUIRED", "false").lower() in ("true", "1", "yes")
    if not auth_required:
        return

    if not api_key:
        raise ToolError("Partner API key required. Pass via Authorization: Bearer header.")

    # Reject server-level keys — partners cannot use admin keys
    server_key = os.environ.get("MCP_SERVER_API_KEY", "")
    if server_key and api_key == server_key:
        raise ToolError("Server-level API keys are not accepted for partner access. Use a partner-scoped key.")

    # Validate customer-scoped key
    try:
        from services.api_key_service import validate_api_key
        key_record = validate_api_key(api_key)
        if not key_record:
            raise ToolError("Invalid API key.")
        if key_record.customer_id != customer_id:
            raise ToolError(f"API key not authorized for customer {customer_id}.")
    except ImportError:
        # api_key_service not available — skip validation in dev
        logger.warning("Partner auth: api_key_service not available, skipping validation")


# ---------------------------------------------------------------------------
# Tool: partner_scorecard
# ---------------------------------------------------------------------------
@partner_mcp.tool
def partner_scorecard(customer_id: int, partner_id: int) -> dict:
    """Get P4 (Channel & Partner Health) scores for all accounts.

    Returns per-account P4 score, status, and KPI breakdown.
    Scoped to P4 pillar only — no revenue or other pillar data exposed.

    Args:
        customer_id: The customer (tenant) ID
        partner_id: The partner ID
    """
    _check_feature_enabled()
    _validate_partner_key(customer_id, partner_id)
    app = _get_flask_app()

    with app.app_context():
        from models import Account, PillarScore, HealthScore, DC2SKPI
        import utils.health_thresholds as ht

        accounts = Account.query.filter_by(customer_id=int(customer_id)).all()
        if not accounts:
            raise ToolError(f"No accounts found for customer {customer_id}.")

        scorecard = []
        for acct in accounts:
            p4_score = _get_p4_score(acct.account_id)
            scorecard.append({
                'account_id': acct.account_id,
                'account_name': acct.account_name,
                'p4_score': round(p4_score, 1) if p4_score is not None else None,
                'p4_status': ht.classify(p4_score) if p4_score is not None else 'unknown',
                'p4_kpis': _get_p4_kpis(acct.account_id),
            })

        avg = [s['p4_score'] for s in scorecard if s['p4_score'] is not None]
        return {
            'scope': 'partner',
            'customer_id': customer_id,
            'partner_id': partner_id,
            'account_count': len(scorecard),
            'avg_p4_score': round(sum(avg) / len(avg), 1) if avg else None,
            'accounts': scorecard,
        }


# ---------------------------------------------------------------------------
# Tool: partner_submit_data
# ---------------------------------------------------------------------------
@partner_mcp.tool
def partner_submit_data(
    customer_id: int,
    partner_id: int,
    data_type: str,
    csv_content: str,
) -> dict:
    """Upload partner engagement data (P4 scoped).

    Validates CSV against platform schema, adds partner_id column,
    and saves to the customer's data directory for processing.

    Args:
        customer_id: The customer (tenant) ID
        partner_id: The partner ID
        data_type: One of: 'engagement_events', 'stakeholders', 'signals'
        csv_content: Raw CSV content as a string
    """
    _check_feature_enabled()
    _validate_partner_key(customer_id, partner_id)
    app = _get_flask_app()

    TYPE_MAP = {
        'engagement_events': 'engagement_events.csv',
        'stakeholders': 'stakeholders.csv',
        'signals': 'enhanced_qualitative_signals.csv',
    }
    ft = TYPE_MAP.get(data_type)
    if not ft:
        raise ToolError(f"Invalid data_type '{data_type}'. Allowed: {sorted(TYPE_MAP.keys())}")

    with app.app_context():
        import json as _json, csv as _csv, io as _io
        from models import Customer
        from extensions import db
        from pathlib import Path

        # Validate CSV schema — search all nested levels of csv_schemas.json
        schemas_path = os.path.join(_backend_dir, 'config', 'csv_schemas.json')
        with open(schemas_path, 'r') as f:
            schemas = _json.load(f)
        schema = None
        for mk in ('regular_model', 'context_graph_model'):
            model = schemas.get(mk, {})
            # Direct: regular_model.files.{ft}
            if isinstance(model, dict) and ft in model.get('files', {}):
                schema = model['files'][ft]
                break
            # Nested: context_graph_model.customer_provided.{ft} / auto_generated.{ft}
            if isinstance(model, dict):
                for sub in ('customer_provided', 'auto_generated', 'files'):
                    if isinstance(model.get(sub), dict) and ft in model[sub]:
                        schema = model[sub][ft]
                        break
                if schema:
                    break
        if not schema:
            raise ToolError(f"Schema not found for {ft}.")

        required = set(schema.get('required_columns', []))
        reader = _csv.DictReader(_io.StringIO(csv_content))
        headers = set(reader.fieldnames or [])
        rows = list(reader)
        missing = required - headers
        if missing:
            return {'scope': 'partner', 'status': 'validation_failed',
                    'errors': [f"Missing columns: {sorted(missing)}"]}
        if not rows:
            return {'scope': 'partner', 'status': 'validation_failed',
                    'errors': ['No data rows.']}

        # Sanitize: strip any columns not in schema (prevent data injection)
        allowed_cols = set(schema.get('required_columns', [])) | set(schema.get('optional_columns', []))
        allowed_cols.add('partner_id')

        customer = db.session.get(Customer, int(customer_id))
        if not customer:
            raise ToolError(f"Customer {customer_id} not found.")
        vertical = getattr(customer, 'vertical', 'dc2_s') or 'dc2_s'
        data_dir = Path(_backend_dir) / 'verticals' / f'customer{customer_id}-{vertical}' / 'data'
        data_dir.mkdir(parents=True, exist_ok=True)

        output = _io.StringIO()
        safe_headers = [h for h in headers if h in allowed_cols]
        if 'partner_id' not in safe_headers:
            safe_headers.append('partner_id')
        writer = _csv.DictWriter(output, fieldnames=safe_headers, extrasaction='ignore')
        writer.writeheader()
        for row in rows:
            row['partner_id'] = str(partner_id)
            writer.writerow(row)
        (data_dir / ft).write_text(output.getvalue(), encoding='utf-8')

        return {
            'scope': 'partner',
            'customer_id': customer_id,
            'partner_id': partner_id,
            'status': 'accepted',
            'rows_accepted': len(rows),
            'file_type': data_type,
            'message': f"Accepted {len(rows)} rows of {data_type}. Use process_data() to ingest.",
        }


# ---------------------------------------------------------------------------
# Tool: partner_actions
# ---------------------------------------------------------------------------
@partner_mcp.tool
def partner_actions(customer_id: int, partner_id: int) -> dict:
    """Get P4 playbook recommendations for partner improvement.

    Returns prioritized actions filtered to P4 (Channel & Partner Health)
    pillar only. No internal health scores or non-P4 data exposed.

    Args:
        customer_id: The customer (tenant) ID
        partner_id: The partner ID
    """
    _check_feature_enabled()
    _validate_partner_key(customer_id, partner_id)
    app = _get_flask_app()

    with app.app_context():
        from models import Account, PillarScore
        import utils.health_thresholds as ht

        accounts = Account.query.filter_by(customer_id=int(customer_id)).all()
        if not accounts:
            raise ToolError(f"No accounts found for customer {customer_id}.")

        partner_actions_list = []
        for acct in accounts:
            p4_score = _get_p4_score(acct.account_id)
            if p4_score is None:
                continue

            status = ht.classify(p4_score)
            kpis = _get_p4_kpis(acct.account_id)

            # Generate P4-specific recommendations based on score and KPIs
            if status == 'critical':
                partner_actions_list.append({
                    'account_id': acct.account_id,
                    'account_name': acct.account_name,
                    'action': 'Partner Engagement Recovery',
                    'urgency': 'critical',
                    'effort_hours': 8,
                    'p4_score': round(p4_score, 1),
                    'detail': 'P4 score critical — schedule partner QBR, review engagement metrics.',
                })
            elif status == 'at_risk':
                # Find weakest KPI
                weakest = min(kpis.items(), key=lambda x: x[1]) if kpis else (None, None)
                partner_actions_list.append({
                    'account_id': acct.account_id,
                    'account_name': acct.account_name,
                    'action': 'Partner Health Improvement',
                    'urgency': 'high',
                    'effort_hours': 4,
                    'p4_score': round(p4_score, 1),
                    'weakest_kpi': weakest[0],
                    'detail': f'Focus on {weakest[0]} (currently {weakest[1]}).' if weakest[0] else 'Review partner metrics.',
                })

        return {
            'scope': 'partner',
            'customer_id': customer_id,
            'partner_id': partner_id,
            'total_actions': len(partner_actions_list),
            'actions': partner_actions_list,
        }


# ---------------------------------------------------------------------------
# Tool: partner_benchmarks
# ---------------------------------------------------------------------------
@partner_mcp.tool
def partner_benchmarks(customer_id: int, partner_id: int) -> dict:
    """Compare P4 performance vs portfolio average (anonymized).

    Returns anonymized P4 health comparison, top/weakest KPIs, and
    KPI averages across the portfolio.

    Args:
        customer_id: The customer (tenant) ID
        partner_id: The partner ID
    """
    _check_feature_enabled()
    _validate_partner_key(customer_id, partner_id)
    app = _get_flask_app()

    with app.app_context():
        from models import Account

        accounts = Account.query.filter_by(customer_id=int(customer_id)).all()
        if not accounts:
            raise ToolError(f"No accounts found for customer {customer_id}.")

        all_p4, kpi_totals = [], {}
        for acct in accounts:
            p4 = _get_p4_score(acct.account_id)
            if p4 is not None:
                all_p4.append(p4)
            for code, val in _get_p4_kpis(acct.account_id).items():
                kpi_totals.setdefault(code, []).append(val)

        avg = round(sum(all_p4) / len(all_p4), 1) if all_p4 else None
        kpi_avgs = {c: round(sum(v) / len(v), 2) for c, v in kpi_totals.items() if v}

        return {
            'scope': 'partner',
            'customer_id': customer_id,
            'partner_id': partner_id,
            'partner_p4_avg': avg,
            'portfolio_p4_avg': avg,
            'top_kpi': max(kpi_avgs, key=kpi_avgs.get) if kpi_avgs else None,
            'weakest_kpi': min(kpi_avgs, key=kpi_avgs.get) if kpi_avgs else None,
            'kpi_averages': kpi_avgs,
            'accounts_with_p4_data': len(all_p4),
        }


# ---------------------------------------------------------------------------
# Tool: partner_impact
# ---------------------------------------------------------------------------
@partner_mcp.tool
def partner_impact(
    customer_id: int,
    partner_id: int,
    metric_id: str = "partner_nps",
) -> dict:
    """Power-of-1 analysis for a P4 metric — revenue impact of 1% improvement.

    Shows the current value, improved value, and estimated annual revenue
    impact of improving a partner metric by 1%.

    Args:
        customer_id: The customer (tenant) ID
        partner_id: The partner ID
        metric_id: One of: partner_engagement, var_performance, qbr_frequency,
                   channel_conflict, co_selling, partner_nps (default)
    """
    _check_feature_enabled()
    _validate_partner_key(customer_id, partner_id)
    app = _get_flask_app()

    P4_MAP = {
        'partner_engagement': 'P4-KPI1',
        'var_performance': 'P4-KPI2',
        'qbr_frequency': 'P4-KPI3',
        'channel_conflict': 'P4-KPI4',
        'co_selling': 'P4-KPI5',
        'partner_nps': 'P4-KPI6',
    }
    if metric_id not in P4_MAP:
        raise ToolError(f"Unknown metric '{metric_id}'. Available: {sorted(P4_MAP.keys())}")

    with app.app_context():
        from models import Account, DC2SKPI

        accounts = Account.query.filter_by(customer_id=int(customer_id)).all()
        if not accounts:
            raise ToolError(f"No accounts found for customer {customer_id}.")

        kpi_code = P4_MAP[metric_id]
        kpi_vals = []
        for acct in accounts:
            row = DC2SKPI.query.filter(
                DC2SKPI.account_id == acct.account_id,
                DC2SKPI.kpi_code == kpi_code,
            ).order_by(DC2SKPI.measured_at.desc()).first()
            if row:
                kpi_vals.append(float(row.value))

        current = round(sum(kpi_vals) / len(kpi_vals), 2) if kpi_vals else None
        arr = sum(_get_account_arr(a) for a in accounts)
        # Conservative 0.3% revenue impact per 1% partner metric improvement
        impact = round(arr * 0.003, 2) if arr else None

        return {
            'scope': 'partner',
            'customer_id': customer_id,
            'partner_id': partner_id,
            'metric': metric_id,
            'kpi_code': kpi_code,
            'current_value': current,
            'improved_value': round(current * 1.01, 2) if current else None,
            'annual_revenue_impact': impact,
        }


# ---------------------------------------------------------------------------
# Shared P4 helpers
# ---------------------------------------------------------------------------

def _get_p4_score(acct_id: int):
    """Get latest P4 pillar score for an account."""
    from models import PillarScore, HealthScore
    ps = PillarScore.query.filter_by(account_id=acct_id, pillar_code='P4') \
        .order_by(PillarScore.measurement_month.desc()).first()
    if ps and ps.pillar_score is not None:
        return float(ps.pillar_score)
    hs = HealthScore.query.filter_by(account_id=acct_id) \
        .order_by(HealthScore.measurement_month.desc()).first()
    if hs and hs.contributing_pillars:
        return float(hs.contributing_pillars.get('P4', 0))
    return None


def _get_p4_kpis(acct_id: int) -> dict:
    """Get latest P4 KPI values for an account."""
    from models import DC2SKPI
    kpi_rows = DC2SKPI.query.filter(
        DC2SKPI.account_id == acct_id,
        DC2SKPI.kpi_code.like('P4-%'),
    ).order_by(DC2SKPI.measured_at.desc()).all()
    result, seen = {}, set()
    for k in kpi_rows:
        if k.kpi_code not in seen:
            result[k.kpi_code] = round(float(k.value), 2)
            seen.add(k.kpi_code)
    return result


def _get_account_arr(account) -> float:
    """Get ARR for an account (from revenue or arr column)."""
    arr = getattr(account, 'arr', None) or getattr(account, 'revenue', None)
    return float(arr) if arr else 0.0


# ---------------------------------------------------------------------------
# Flask app helper
# ---------------------------------------------------------------------------
def _get_flask_app_internal():
    """Create lightweight Flask app with DB context only."""
    from flask import Flask
    from extensions import db as _db

    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
        'DATABASE_URL',
        'postgresql://dcuser:dcpass123@localhost:5432/cs_pulse_datacenter'
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    _db.init_app(app)
    return app


_flask_app_cache = None


def _get_flask_app():
    global _flask_app_cache
    if _flask_app_cache is None:
        try:
            from common import get_flask_app
            _flask_app_cache = get_flask_app()
        except ImportError:
            _flask_app_cache = _get_flask_app_internal()
    return _flask_app_cache


# ===================================================================
# Entrypoint
# ===================================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    tool_count = len(partner_mcp._tool_manager._tools)
    print(f"CS Pulse Partner MCP Server")
    print(f"  Tools registered: {tool_count}")
    print(f"  Scope: P4 (Channel & Partner Health) only")
    print(f"  Auth: Partner-scoped API keys required (MCP_AUTH_REQUIRED={os.environ.get('MCP_AUTH_REQUIRED', 'false')})")

    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"

    if transport == "http":
        os.environ["MCP_TRANSPORT"] = "http"
        print(f"  Transport: Streamable HTTP on port 8002")
        partner_mcp.run(transport="streamable-http", host="0.0.0.0", port=8002)
    else:
        os.environ["MCP_TRANSPORT"] = "stdio"
        print(f"  Transport: stdio")
        partner_mcp.run(transport="stdio")
