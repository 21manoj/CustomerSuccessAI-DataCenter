#!/usr/bin/env python3
"""
CS Pulse MCP — Onboarding Tools (frictionless auth).

15 onboarding/discovery tools:
  - list_verticals
  - get_reference_customer
  - get_vertical_config
  - get_csv_templates
  - get_onboarding_status
  - validate_csv
  - create_customer
  - configure_customer_kpis
  - enable_features
  - upload_csv
  - process_data  (delegates to _process_data_impl)
  - trigger_wizard
  - complete_onboarding
  - clone_customer
  - download_customer_csv

Plus the _process_data_impl function (single source of truth for data processing).

All tools register on the shared `mcp` instance from cs_pulse_mcp_server.
"""

import os

from cs_pulse_mcp_server import (
    mcp,
    _check_mcp_enabled,
    _require_auth,  # Apr 28 2026: was missing — caused NameError at runtime
                    # in clone_customer (line 2397) and download_customer_csv.
                    # Surfaced via Claude.ai MCP error trace.
    _get_flask_app,
    _get_account_arr,
    _get_health_functions,
    _get_kpi_definitions,
    _get_dc2s_pillar_labels,  # DEPRECATED — kept for back-compat; use _get_pillar_labels(vertical)
    _get_pillar_labels,        # Apr 28 2026: vertical-aware pillar labels (saas_premium / dc2_s / etc.)
    _resolve_customer_vertical,
    _backend_dir,
    ToolError,
)
from onboarding_tool_registry import ONBOARDING_TOOLS
from mcp_server.auth import require_auth_if_key_present as _require_auth_if_key_present


def _is_onboarding_tool(name: str) -> bool:
    """Return True if the tool name is in the frictionless onboarding set."""
    return name in ONBOARDING_TOOLS


def _reference_customer_for_vertical(vertical: str):
    """Demo/reference tenant for a vertical (used by list_verticals + get_reference_customer)."""
    from models import Customer, Account

    ref_customer = None
    try:
        ref_customer = Customer.query.filter_by(
            is_reference=True,
            reference_for=vertical,
        ).first()
    except Exception:
        pass
    if not ref_customer:
        ref_customer = Customer.query.filter_by(vertical=vertical).first()
    if not ref_customer:
        return None
    acct_count = Account.query.filter_by(customer_id=ref_customer.customer_id).count()
    return {
        'customer_id': ref_customer.customer_id,
        'name': ref_customer.customer_name,
        'vertical': vertical,
        'account_count': acct_count,
    }


# ===================================================================
# Tool: list_verticals
# ===================================================================

@mcp.tool
def list_verticals() -> dict:
    """List all available verticals with their KPI counts and config types.

    Discovery tool for prospects — no authentication required.
    Returns each vertical with its description, total KPI count,
    and the number of config type templates available.
    """
    _require_auth_if_key_present('list_verticals', None)
    _check_mcp_enabled()
    app = _get_flask_app()

    with app.app_context():
        verticals: dict = {}

        try:
            from models import VerticalTemplate
            from extensions import db
            from sqlalchemy import func

            rows = (
                db.session.query(
                    VerticalTemplate.vertical,
                    VerticalTemplate.config_type,
                    func.count(VerticalTemplate.template_id).label('cnt'),
                )
                .group_by(VerticalTemplate.vertical, VerticalTemplate.config_type)
                .all()
            )

            for vertical, config_type, cnt in rows:
                if vertical not in verticals:
                    verticals[vertical] = {
                        'vertical': vertical,
                        'config_types': [],
                        'config_type_count': 0,
                        'kpi_count': 0,
                        'description': None,
                    }
                verticals[vertical]['config_types'].append(config_type)
                verticals[vertical]['config_type_count'] += 1
        except (ImportError, Exception):
            pass

        for v_key, v_info in verticals.items():
            try:
                kpi_defs = _get_kpi_definitions(v_key)
                v_info['kpi_count'] = len(kpi_defs)
            except Exception:
                pass
            # Auto-generate description from pillar names if not already set
            if not v_info.get('description'):
                try:
                    from utils.vertical_registry import get_pillars
                    pillar_names = [p.get('name', pid) for pid, p in get_pillars(v_key).items()]
                    v_info['description'] = f"{v_key.replace('_', ' ').title()} vertical — {', '.join(pillar_names)}"
                except Exception:
                    v_info['description'] = f"{v_key.replace('_', ' ').title()} vertical"

        if not verticals:
            # Auto-discover from registry instead of hardcoding
            try:
                from utils.vertical_registry import SUPPORTED_VERTICALS, get_pillars, get_kpis
                for v_slug in sorted(SUPPORTED_VERTICALS):
                    try:
                        kpi_defs = get_kpis(v_slug)
                        pillar_defs = get_pillars(v_slug)
                        pillar_names = [p.get('name', pid) for pid, p in pillar_defs.items()]
                        verticals[v_slug] = {
                            'vertical': v_slug,
                            'config_types': [],
                            'config_type_count': 0,
                            'kpi_count': len(kpi_defs),
                            'description': f"{v_slug.replace('_', ' ').title()} vertical — {', '.join(pillar_names)}",
                        }
                    except Exception:
                        pass
            except Exception:
                pass  # Registry not available — return empty

        try:
            for v_slug, v_info in verticals.items():
                v_info['reference_customer'] = _reference_customer_for_vertical(v_slug)
        except Exception:
            for v_info in verticals.values():
                v_info['reference_customer'] = None

        return {
            'scope': 'platform',
            'total_verticals': len(verticals),
            'verticals': list(verticals.values()),
        }


# ===================================================================
# Tool: get_csv_templates
# ===================================================================

@mcp.tool
def get_csv_templates(vertical: str, file_type: str = None) -> dict:
    """Get CSV column schemas for data uploads.

    Discovery tool — no authentication required.
    Returns the required and optional columns for each CSV file type
    that the platform accepts during onboarding data ingestion.

    Args:
        vertical: The vertical slug (e.g. 'dc2_s')
        file_type: Optional specific file type (e.g. 'accounts.csv', 'kpi_measurements.csv').
                   If omitted, returns all file types for the vertical.
    """
    _require_auth_if_key_present('get_csv_templates', None)
    _check_mcp_enabled()

    import json as _json

    schemas_path = os.path.join(_backend_dir, 'config', 'csv_schemas.json')
    if not os.path.isfile(schemas_path):
        raise ToolError("CSV schemas config file not found at config/csv_schemas.json")

    with open(schemas_path, 'r') as f:
        schemas = _json.load(f)

    def _flatten_model(model: dict) -> dict:
        """Return {filename: schema} from a model section, handling both flat and nested layouts."""
        result = {}
        result.update(model.get('files', {}))
        for sub_key in ('customer_provided', 'auto_generated', 'platform_curated'):
            for k, v in model.get(sub_key, {}).items():
                if k.endswith('.csv') and k not in result:
                    result[k] = v
        return result

    all_files = {}
    for model_key in ('regular_model', 'context_graph_model'):
        model = schemas.get(model_key, {})
        for fname, fschema in _flatten_model(model).items():
            all_files[fname] = {
                'file_type': fname,
                'model': model_key,
                'required_columns': fschema.get('required_columns', []),
                'optional_columns': fschema.get('optional_columns', []),
                'db_table': fschema.get('db_table', ''),
                'note': fschema.get('note', ''),
            }

    if file_type:
        if file_type not in all_files:
            raise ToolError(
                f"Unknown file_type '{file_type}'. Available: {sorted(all_files.keys())}"
            )
        return {
            'scope': 'platform',
            'vertical': vertical,
            'file_type': file_type,
            'schema': all_files[file_type],
        }

    return {
        'scope': 'platform',
        'vertical': vertical,
        'total_file_types': len(all_files),
        'schemas': all_files,
    }


# ===================================================================
# Tool: get_reference_customer
# ===================================================================

@mcp.tool
def get_reference_customer(vertical: str) -> dict:
    """Return the demo/reference customer for a vertical.

    Prospects use this after list_verticals() to find a tenant ID they can
    explore with intelligence tools or clone via clone_customer().

    Args:
        vertical: Vertical slug (e.g. 'saas_premium', 'dc2_s')
    """
    _require_auth_if_key_present('get_reference_customer', None)
    _check_mcp_enabled()
    app = _get_flask_app()

    with app.app_context():
        ref = _reference_customer_for_vertical(vertical)
        if not ref:
            return {
                'scope': 'platform',
                'vertical': vertical,
                'found': False,
                'message': f'No reference customer found for vertical {vertical!r}.',
            }
        return {
            'scope': 'platform',
            'vertical': vertical,
            'found': True,
            'reference_customer': ref,
        }


# ===================================================================
# Tool: get_vertical_config
# ===================================================================

@mcp.tool
def get_vertical_config(vertical: str) -> dict:
    """Return KPI pillars, KPI count, and playbook catalog for a vertical.

    Discovery tool — no authentication required. Use before configure_customer_kpis()
    or when explaining what a vertical supports to a prospect.

    Args:
        vertical: Vertical slug (e.g. 'saas_premium', 'dc2_s')
    """
    _require_auth_if_key_present('get_vertical_config', None)
    _check_mcp_enabled()
    app = _get_flask_app()

    with app.app_context():
        import utils.health_thresholds as ht

        pillars: dict = {}
        kpis: dict = {}
        try:
            from utils.vertical_registry import get_pillars, get_kpis, SUPPORTED_VERTICALS
            if vertical not in SUPPORTED_VERTICALS:
                raise ToolError(
                    f"Unknown vertical {vertical!r}. "
                    f"Supported: {sorted(SUPPORTED_VERTICALS)}"
                )
            pillar_defs = get_pillars(vertical)
            kpi_defs = get_kpis(vertical)
            pillars = {
                pid: {
                    'name': p.get('name', pid),
                    'weight': p.get('weight'),
                    'kpi_count': sum(
                        1 for k in kpi_defs.values()
                        if k.get('pillar') == pid
                    ),
                }
                for pid, p in pillar_defs.items()
            }
            kpis = {
                code: {
                    'name': k.get('name', code),
                    'pillar': k.get('pillar'),
                    'unit': k.get('unit'),
                }
                for code, k in kpi_defs.items()
            }
        except ToolError:
            raise
        except Exception as exc:
            raise ToolError(f"Could not load vertical config for {vertical!r}: {exc}") from exc

        playbook_config = _get_playbook_config(vertical) or {}
        playbooks = {
            pb_id: {
                'name': cfg.get('name', pb_id),
                'estimated_duration_days': cfg.get('estimated_duration_days'),
                'trigger_conditions': cfg.get('trigger_conditions'),
            }
            for pb_id, cfg in playbook_config.items()
        }

        tier_config = _load_tier_config()
        saas_tiers = list(tier_config.get('tiers', {}).keys()) if tier_config else []

        return {
            'scope': 'platform',
            'vertical': vertical,
            'pillar_count': len(pillars),
            'pillars': pillars,
            'kpi_count': len(kpis),
            'kpis': kpis,
            'playbook_count': len(playbooks),
            'playbooks': playbooks,
            'health_bands': {
                'healthy_min': ht.HEALTHY_MIN,
                'at_risk_min': ht.AT_RISK_MIN,
            },
            'saas_kpi_tiers': saas_tiers if vertical in ('saas_premium', 'saas') else [],
        }


# ===================================================================
# Tool: validate_csv
# ===================================================================

@mcp.tool
def validate_csv(customer_id: int, file_type: str, csv_content: str) -> dict:
    """Validate CSV content against platform schema without persisting.

    Same validation path as upload_csv(dry_run=True) and POST /api/onboarding/validate-csv.
    Use before upload_csv() to catch column or schema errors early.

    Args:
        customer_id: Customer ID (needed for config-aware KPI filtering when applicable)
        file_type: CSV file type (e.g. 'kpi_measurements.csv', 'accounts.csv')
        csv_content: Raw CSV string
    """
    _require_auth_if_key_present('validate_csv', customer_id)
    _check_mcp_enabled()
    app = _get_flask_app()

    with app.app_context():
        from utils.csv_upload import _upload_csv_impl
        result = _upload_csv_impl(
            customer_id=customer_id,
            file_type=file_type,
            csv_content=csv_content,
            dry_run=True,
            storage_mode='disk',
        )
        result['scope'] = 'customer'
        result['customer_id'] = customer_id
        result['validated'] = True
        return result


# ===================================================================
# Tool: get_onboarding_status
# ===================================================================

@mcp.tool
def get_onboarding_status(customer_id: int) -> dict:
    """Poll onboarding progress: checklist + in-flight process_data status.

    Combines complete_onboarding(check_only=True) with the process-data progress
    tracker (GET /api/onboarding/status/<id>). Use while process_data() is running
    or to verify Month-1 CSV requirements before finalize.

    Args:
        customer_id: The customer ID to inspect
    """
    _require_auth_if_key_present('get_onboarding_status', customer_id)
    _check_mcp_enabled()
    app = _get_flask_app()

    with app.app_context():
        checklist_impl = getattr(complete_onboarding, 'fn', complete_onboarding)
        checklist_result = checklist_impl(customer_id=customer_id, check_only=True)
        process_progress = None
        try:
            from utils.onboarding_progress_file import read_progress
            process_progress = read_progress(int(customer_id))
        except Exception:
            pass

        if not process_progress:
            try:
                from onboarding_api_v2_config_aware import _onboarding_progress
                process_progress = _onboarding_progress.get(int(customer_id))
            except Exception:
                pass

        in_progress = bool(process_progress and process_progress.get('in_progress'))
        return {
            'scope': 'customer',
            'customer_id': customer_id,
            'checklist': checklist_result,
            'process_data': {
                'in_progress': in_progress,
                'status': (process_progress or {}).get('status'),
                'current_step': (process_progress or {}).get('current_step'),
                'steps_completed': (process_progress or {}).get('steps_completed', []),
                'started_at': (process_progress or {}).get('started_at'),
                'completed_at': (process_progress or {}).get('completed_at'),
                'error': (process_progress or {}).get('error'),
            },
        }


# ===================================================================
# Tool: create_customer
# ===================================================================

# ===================================================================
# KPI Tier Helpers
# ===================================================================

def _load_tier_config():
    """Load the SaaS KPI tier definitions from config."""
    import json
    import os
    path = os.path.join(os.path.dirname(__file__), '..', 'config', 'saas_kpi_tiers.json')
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def _resolve_kpi_tier(tier: str, vertical: str) -> dict:
    """Resolve tier name to tier definition. Returns None for non-SaaS or unrecognized tier."""
    if vertical not in ('saas_premium', 'saas'):
        return None  # DC2_S uses full catalog — no tiers yet

    config = _load_tier_config()
    if not config:
        return None

    tiers = config.get('tiers', {})

    if tier and tier in tiers:
        return tiers[tier]

    # No tier specified — use default
    default = config.get('default_tier', 'saas_starter_9')
    return tiers.get(default)


def _apply_kpi_tier(customer_config, tier_def: dict) -> dict:
    """Apply tier KPI selection AND pillar weights to a CustomerConfig.

    Shift-left: sets both enabled_kpis and pillar_weights at creation time
    so health scores are computed correctly from the first process_data call.
    Without pillar_weights, the scorer falls back to full-catalog defaults
    which spread weight across all 5 pillars — including pillars with zero
    KPIs in the tier, diluting the score.
    """
    kpi_codes = tier_def.get('kpi_codes')
    if kpi_codes == 'all':
        # Full tier: clear KPI restriction (all KPIs enabled)
        customer_config.dc2s_enabled_kpis = None
        customer_config.dc2s_pillar_weights = None  # use catalog defaults
    elif kpi_codes:
        customer_config.dc2s_enabled_kpis = kpi_codes

        # Set pillar weights — distribute equally across active pillars only.
        # Without this, pillars with zero KPIs still get weight → score dilution.
        active_pillars = tier_def.get('pillars')
        if active_pillars and len(active_pillars) < 5:
            equal_weight = round(1.0 / len(active_pillars), 4)
            pw = {p: equal_weight for p in active_pillars}
            # Fix rounding to sum exactly to 1.0
            diff = round(1.0 - sum(pw.values()), 4)
            if diff != 0:
                pw[active_pillars[-1]] = round(pw[active_pillars[-1]] + diff, 4)
            customer_config.dc2s_pillar_weights = pw

    return {
        'name': tier_def.get('display_name'),
        'model_grade': tier_def.get('model_grade'),
        'kpi_count': tier_def.get('kpi_count'),
        'pillars': tier_def.get('pillars'),
        'upgrade_path': tier_def.get('upgrade_path'),
    }


@mcp.tool
def create_customer(
    name: str,
    domain: str,
    vertical: str,
    admin_email: str,
    admin_name: str,
    tier: str = None,
) -> dict:
    """Create a new customer with admin user and auto-generated API key.

    This is the first write step in onboarding. Creates:
    1. Customer record (with UUID)
    2. Admin user (with generated password)
    3. CustomerConfig (vertical defaults)
    4. API key (returned once — save it!)

    No authentication required — this is the entry point for new prospects.

    After creation, onboard in 2 stages:
      Month 1 (4 CSVs):
        1. accounts.csv — enriched with products, champion, contract, firmographic data
        2. kpi_measurements.csv — KPI time-series from customer systems
        3. enhanced_qualitative_signals.csv — signal feed (NPS, escalations, champion changes)
        4. outcomes.csv — CRM renewal/churn/expansion history (Salesforce export)
        Then call process_data() — Wizard A auto-generates context graph (rule-based, no hallucination).

      Month 2+ (incremental, as CRM integrations come online):
        - engagement_events.csv — meeting/QBR/call logs
        - industry_benchmarks.csv — platform-supplied

    Args:
        name: Company name
        domain: Email domain (e.g. 'acme.com')
        vertical: Vertical slug (e.g. 'dc2_s')
        admin_email: Admin user email
        admin_name: Admin user display name
        tier: Optional KPI tier for SaaS verticals. Options:
            'saas_starter_9' — 9 KPIs, 4 pillars, 1-hour onboarding (default for SaaS)
            'saas_predictive_11' — 11 KPIs, behavioral signals, requires product analytics
            'saas_full_43' — all KPIs, enterprise deployment
            If omitted, SaaS defaults to 'saas_starter_9'. DC2_S uses full catalog.
    """
    _require_auth_if_key_present('create_customer', None)
    _check_mcp_enabled()
    app = _get_flask_app()

    with app.app_context():
        from models import Customer, User, CustomerConfig
        from extensions import db
        from werkzeug.security import generate_password_hash
        import secrets as _secrets

        existing = Customer.query.filter_by(domain=domain).first()
        if existing:
            raise ToolError(
                f"A customer with domain '{domain}' already exists "
                f"(customer_id={existing.customer_id}). "
                f"Use complete_onboarding(check_only=True) to check its state."
            )

        existing_user = User.query.filter_by(email=admin_email).first()
        if existing_user:
            raise ToolError(f"Email '{admin_email}' is already registered.")

        try:
            from id_generator import generate_id, resolve_vertical_prefix
            uuid_vertical = 'dc' if vertical.startswith('dc') else vertical
            customer_uuid = generate_id(uuid_vertical, 'customer')
        except Exception:
            customer_uuid = None

        customer = Customer(
            customer_name=name,
            email=admin_email,
            domain=domain,
            vertical=vertical,
        )
        if customer_uuid:
            customer.uuid = customer_uuid
        db.session.add(customer)
        db.session.flush()

        customer_id = customer.customer_id

        generated_password = _secrets.token_urlsafe(16)
        user = User(
            customer_id=customer_id,
            user_name=admin_name,
            email=admin_email,
            password_hash=generate_password_hash(generated_password),
            role='admin',
            vertical=vertical,
        )
        if customer_uuid:
            user.customer_uuid = customer_uuid
        try:
            from id_generator import generate_id as _gen_id
            user.uuid = _gen_id('dc' if vertical.startswith('dc') else vertical, 'user')
        except Exception:
            pass
        db.session.add(user)
        db.session.flush()

        config = CustomerConfig(
            customer_id=customer_id,
            vertical=vertical,
        )

        # ── Apply KPI tier (SaaS verticals) ──
        resolved_tier = _resolve_kpi_tier(tier, vertical)
        tier_info = None
        if resolved_tier:
            tier_info = _apply_kpi_tier(config, resolved_tier)

        db.session.add(config)

        try:
            from api_key_service import generate_api_key as _gen_api_key
            full_key, _key_record = _gen_api_key(
                customer_id=customer_id,
                created_by=user.user_id,
                name='MCP Onboarding Key',
                scopes=['read', 'write'],
            )
        except Exception as e:
            full_key = None

        try:
            from verticals.provision_dc_customer import provision_customer
            directory_provisioned = provision_customer(
                customer_id=customer_id,
                customer_name=name,
                vertical_slug=vertical,
                force=True,
            )
        except Exception:
            directory_provisioned = False

        # ── Auto-enable ALL features for Beta ──
        ALL_FEATURES = [
            'context_graph', 'story_arcs', 'signal_edges',
            'stakeholder_tracking', 'decision_lifecycle',
            'outcome_economics', 'industry_benchmarks',
        ]
        from models import FeatureToggle as _FT
        for feat in ALL_FEATURES:
            existing = _FT.query.filter_by(customer_id=customer_id, feature_name=feat).first()
            if not existing:
                db.session.add(_FT(
                    customer_id=customer_id,
                    feature_name=feat if feat != 'context_graph' else 'context_graph',
                    enabled=True,
                    config={sub: True for sub in ALL_FEATURES if sub != 'context_graph'} if feat == 'context_graph' else {},
                    description='Auto-enabled at customer creation (Beta)',
                ))

        db.session.commit()

        result = {
            'scope': 'customer',
            'customer_id': customer_id,
            'customer_name': name,
            'customer_uuid': customer_uuid,
            'domain': domain,
            'vertical': vertical,
            'created_at': customer.created_at.isoformat() if customer.created_at else None,
            'admin_user_id': user.user_id,
            'admin_email': admin_email,
            'directory_provisioned': directory_provisioned,
        }

        if full_key:
            result['api_key'] = full_key
            result['api_key_note'] = (
                'Save this API key — it is shown only once. '
                'Use it for the intelligence tools (list_accounts, get_account_health, etc.).'
            )
            # Log masked key for audit trail (never log full key)
            import logging as _key_log
            _masked = full_key[:12] + '...' + full_key[-4:] if len(full_key) > 16 else '***'
            _key_log.getLogger(__name__).info(
                f"API key generated for customer {customer_id}: {_masked}"
            )

        if tier_info:
            result['tier'] = tier_info

        return result


# ===================================================================
# KPI Dependency Guard
# ===================================================================

def _check_kpi_dependencies(enabled_kpis=None, enabled_pillars=None, cust_vertical='dc2_s'):
    """Check if disabled KPIs/pillars affect downstream engines (ROI, arc classifier).

    Returns list of warning strings. Empty list = no issues.
    Only warns when the customer has EXPLICITLY selected a subset of KPIs/pillars
    (not when using defaults = all enabled).
    """
    if not enabled_kpis and not enabled_pillars:
        return []  # Using all defaults — no warnings needed

    import json
    import os
    deps_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'kpi_dependencies.json')
    try:
        with open(deps_path) as f:
            deps = json.load(f)
    except Exception:
        return []  # Can't load deps file — skip silently

    warnings = []

    # Check pillar-level dependencies
    if enabled_pillars:
        all_pillars = set(deps.get('pillar_dependencies', {}).keys())
        disabled_pillars = all_pillars - set(enabled_pillars)
        for p in sorted(disabled_pillars):
            dep = deps['pillar_dependencies'].get(p)
            if dep:
                warnings.append(dep['warning'])

    # Check KPI-level dependencies
    if enabled_kpis:
        all_kpi_deps = deps.get('dependencies', {})
        for kpi_code, dep in all_kpi_deps.items():
            if kpi_code not in enabled_kpis:
                warnings.append(dep['warning'])

    return warnings


# ===================================================================
# Tool: configure_customer_kpis
# ===================================================================

@mcp.tool
def configure_customer_kpis(
    customer_id: int,
    enabled_pillars: list = None,
    enabled_kpis: list = None,
    pillar_weights: dict = None,
    kpi_weights: dict = None,
    lifecycle_stage_weights: dict = None,
    upgrade_tier: str = None,
) -> dict:
    """Configure KPI selection and weights for a customer.

    Sets customer-level overrides via CustomerConfig. You can:
    - Select which pillars are active (enabled_pillars)
    - Select exact KPIs (enabled_kpis overrides enabled_pillars)
    - Set L2 pillar weights (pillar_weights)
    - Set L1 KPI weights per pillar (kpi_weights)
    - Set lifecycle-stage weight profiles (lifecycle_stage_weights)
    - Upgrade to a named KPI tier (upgrade_tier)

    Args:
        customer_id: The customer ID
        enabled_pillars: Optional list of pillar codes (e.g. ['P1', 'P3', 'P5'])
        enabled_kpis: Optional list of KPI codes (e.g. ['P1-KPI1', 'P1-KPI2'])
        pillar_weights: Optional dict of pillar weights (e.g. {'P1': 0.4, 'P3': 0.35, 'P5': 0.25})
        kpi_weights: Optional dict of KPI weights per pillar (e.g. {'P1': {'P1-KPI1': 0.5}})
        lifecycle_stage_weights: Optional dict with lifecycle stage definitions.
            Schema: {"enabled": true, "date_field": "contract_start",
                     "stages": [{"name": "onboarding", "min_days": 0, "max_days": 90,
                                 "pillar_weights": {"P1": 0.35, ...}}, ...]}
            Pass {"enabled": true} with no stages to use defaults (onboarding/stabilization/growth).
            Pass {"enabled": false} to disable lifecycle-stage weighting.
        upgrade_tier: Optional tier name to upgrade to. Options:
            'saas_starter_9', 'saas_predictive_11', 'saas_full_43'.
            Sets enabled_kpis from tier definition. Overrides enabled_kpis/enabled_pillars.
    """
    _require_auth_if_key_present('configure_customer_kpis', customer_id)
    _check_mcp_enabled()
    app = _get_flask_app()

    with app.app_context():
        from models import Customer, CustomerConfig
        from extensions import db

        customer = db.session.get(Customer, int(customer_id))
        if not customer:
            raise ToolError(f"Customer {customer_id} not found. Use create_customer() first.")

        config = CustomerConfig.query.filter_by(customer_id=customer_id).first()
        cust_vertical = getattr(customer, 'vertical', 'dc2_s') or 'dc2_s'
        if not config:
            config = CustomerConfig(customer_id=customer_id, vertical=cust_vertical)

        # Snapshot previous weights before any changes (for history tracking)
        _prev_pw = dict(config.dc2s_pillar_weights) if config.dc2s_pillar_weights else None
        _prev_kw = dict(config.dc2s_kpi_weights) if config.dc2s_kpi_weights else None

        # ── Tier upgrade: override enabled_kpis from tier definition ──
        tier_info = None
        if upgrade_tier:
            tier_def = _resolve_kpi_tier(upgrade_tier, cust_vertical)
            if not tier_def:
                raise ToolError(
                    f"Unknown tier '{upgrade_tier}'. Valid SaaS tiers: "
                    f"saas_starter_9, saas_predictive_11, saas_full_43"
                )
            tier_info = _apply_kpi_tier(config, tier_def)
            # Tier sets enabled_kpis — clear manual overrides
            enabled_kpis = None
            enabled_pillars = None
            db.session.add(config)

        if enabled_kpis:
            config.dc2s_enabled_kpis = enabled_kpis
        elif enabled_pillars:
            try:
                kpi_defs = _get_kpi_definitions(cust_vertical)
                derived_kpis = [
                    code for code, defn in kpi_defs.items()
                    if defn.get('pillar') in enabled_pillars
                ]
                config.dc2s_enabled_kpis = derived_kpis
            except Exception:
                raise ToolError("Could not load KPI definitions for pillar-based selection.")

        if pillar_weights:
            pw_total = sum(pillar_weights.values())
            if pw_total > 0 and abs(pw_total - 1.0) > 0.0001:
                pillar_weights = {k: round(v / pw_total, 4) for k, v in pillar_weights.items()}
                _pw_keys = list(pillar_weights.keys())
                _pw_diff = round(1.0 - sum(pillar_weights.values()), 4)
                if _pw_diff != 0 and _pw_keys:
                    pillar_weights[_pw_keys[-1]] = round(pillar_weights[_pw_keys[-1]] + _pw_diff, 4)
            config.dc2s_pillar_weights = pillar_weights

        if kpi_weights:
            for pillar, kw in kpi_weights.items():
                kw_total = sum(kw.values())
                if kw_total > 0 and abs(kw_total - 1.0) > 0.0001:
                    kpi_weights[pillar] = {k: round(v / kw_total, 4) for k, v in kw.items()}
                    _kw_keys = list(kpi_weights[pillar].keys())
                    _kw_diff = round(1.0 - sum(kpi_weights[pillar].values()), 4)
                    if _kw_diff != 0 and _kw_keys:
                        kpi_weights[pillar][_kw_keys[-1]] = round(
                            kpi_weights[pillar][_kw_keys[-1]] + _kw_diff, 4)
            config.dc2s_kpi_weights = kpi_weights

        if lifecycle_stage_weights is not None:
            from utils.lifecycle_stages import (
                validate_lifecycle_config, normalize_stage_weights, DEFAULT_LIFECYCLE_CONFIG
            )
            # If just {"enabled": true} with no stages, use defaults
            if lifecycle_stage_weights.get('enabled') and not lifecycle_stage_weights.get('stages'):
                import copy
                lc = copy.deepcopy(DEFAULT_LIFECYCLE_CONFIG)
                lc['enabled'] = True
                lifecycle_stage_weights = lc

            errors = validate_lifecycle_config(lifecycle_stage_weights)
            if errors and lifecycle_stage_weights.get('enabled'):
                raise ToolError(f"Invalid lifecycle config: {'; '.join(errors)}")

            lifecycle_stage_weights = normalize_stage_weights(lifecycle_stage_weights)
            config.dc2s_lifecycle_stage_weights = lifecycle_stage_weights

        # Record weight change history (for CDI aggregation + rollback + audit)
        if pillar_weights or kpi_weights or upgrade_tier:
            try:
                from models import WeightCalibrationHistory
                _source = 'tier_upgrade' if upgrade_tier else 'manual'
                history = WeightCalibrationHistory(
                    customer_id=int(customer_id),
                    calibration_type='both',
                    vertical=cust_vertical,
                    previous_weights={'pillar': _prev_pw, 'kpi': _prev_kw},
                    new_weights={'pillar': config.dc2s_pillar_weights, 'kpi': config.dc2s_kpi_weights},
                    pillar_weights=config.dc2s_pillar_weights,
                    kpi_weights=config.dc2s_kpi_weights,
                    previous_pillar_weights=_prev_pw,
                    previous_kpi_weights=_prev_kw,
                    triggered_by=_source,
                    source=_source,
                    notes=f'Tier: {upgrade_tier}' if upgrade_tier else None,
                )
                db.session.add(history)
            except Exception:
                pass  # best-effort — don't block config save

        db.session.commit()

        lifecycle_info = None
        if config.dc2s_lifecycle_stage_weights:
            lc = config.dc2s_lifecycle_stage_weights
            lifecycle_info = {
                'enabled': lc.get('enabled', False),
                'stages': [s.get('name') for s in lc.get('stages', [])],
                'date_field': lc.get('date_field', 'contract_start'),
            }

        # ── KPI Dependency Guard: warn when disabling load-bearing KPIs ──
        warnings = _check_kpi_dependencies(
            enabled_kpis=config.dc2s_enabled_kpis,
            enabled_pillars=list(config.dc2s_pillar_weights.keys()) if config.dc2s_pillar_weights else None,
            cust_vertical=cust_vertical,
        )

        result = {
            'scope': 'customer',
            'customer_id': customer_id,
            'enabled_kpis': config.dc2s_enabled_kpis,
            'enabled_kpi_count': len(config.dc2s_enabled_kpis) if config.dc2s_enabled_kpis else 0,
            'pillar_weights': config.dc2s_pillar_weights,
            'kpi_weights': config.dc2s_kpi_weights,
            'lifecycle_stage_weights': lifecycle_info,
            'message': 'Customer KPI configuration updated.',
        }
        if warnings:
            result['dependency_warnings'] = warnings
            result['message'] += f' ⚠️ {len(warnings)} dependency warning(s) — some downstream engines may be affected.'
        if tier_info:
            result['tier'] = tier_info
            result['message'] = f'Upgraded to {tier_info["name"]}. ' + result['message']
        return result


# ===================================================================
# Tool: enable_features
# ===================================================================

@mcp.tool
def enable_features(customer_id: int, features: list = None) -> dict:
    """Enable or disable feature toggles for a customer.

    Each feature is a per-customer DB toggle. Common features include:
    context_graph, story_arcs, signal_edges, stakeholder_tracking,
    decision_lifecycle, outcome_economics, industry_benchmarks.

    Args:
        customer_id: The customer ID
        features: List of feature names to enable. If None, returns current state.
    """
    _require_auth_if_key_present('enable_features', customer_id)
    _check_mcp_enabled()
    app = _get_flask_app()

    with app.app_context():
        from models import Customer
        from models import FeatureToggle as FTModel
        from extensions import db

        customer = db.session.get(Customer, int(customer_id))
        if not customer:
            raise ToolError(f"Customer {customer_id} not found.")

        if features is None:
            toggles = FTModel.query.filter_by(customer_id=customer_id).all()
            return {
                'scope': 'customer',
                'customer_id': customer_id,
                'features': {
                    t.feature_name: t.enabled for t in toggles
                },
                'total_features': len(toggles),
            }

        results = {}
        for feature_name in features:
            toggle = FTModel.query.filter_by(
                customer_id=customer_id,
                feature_name=feature_name,
            ).first()
            if toggle:
                toggle.enabled = True
            else:
                toggle = FTModel(
                    customer_id=customer_id,
                    feature_name=feature_name,
                    enabled=True,
                    description=f'Enabled via MCP onboarding',
                )
                db.session.add(toggle)
            results[feature_name] = True

        db.session.commit()

        return {
            'scope': 'customer',
            'customer_id': customer_id,
            'features_enabled': results,
            'total_enabled': len(results),
            'message': f'Enabled {len(results)} features for customer {customer_id}.',
        }


# ===================================================================
# Tool: upload_csv
# ===================================================================

@mcp.tool
def upload_csv(customer_id: int, file_type: str, csv_content: str, dry_run: bool = False) -> dict:
    """Upload CSV data for a customer.

    Saves the CSV content to the customer's data directory on disk.
    The file can then be processed via process_data().

    When dry_run=True, validates the CSV against the platform schema
    (required/optional columns, row count) but does NOT persist data.
    Use dry_run=True to check your CSV before committing an upload.

    Month 1 (required — 4 CSVs for onboarding):
      'accounts.csv' — enriched with products, champion, contract, firmographic
      'kpi_measurements.csv' — KPI time-series
      'enhanced_qualitative_signals.csv' — signal feed
      'outcomes.csv' — CRM renewal/churn/expansion history

    Month 2+ (optional — as CRM integrations come online):
      'engagement_events.csv' — meeting/QBR/call logs
      'industry_benchmarks.csv' — platform-supplied benchmarks

    Args:
        customer_id: The customer ID
        file_type: The CSV file type (e.g. 'accounts.csv', 'kpi_measurements.csv')
        csv_content: The raw CSV content as a string
        dry_run: If True, validate only — do not persist. Returns validation result.
    """
    _require_auth_if_key_present('upload_csv', customer_id)
    _check_mcp_enabled()

    app = _get_flask_app()
    with app.app_context():
        from utils.csv_upload import _upload_csv_impl
        result = _upload_csv_impl(
            customer_id=customer_id,
            file_type=file_type,
            csv_content=csv_content,
            dry_run=dry_run,
            storage_mode='disk',
        )

        if result.status == 'error' or (result.status == 'validation_error' and not dry_run):
            raise ToolError(
                f"CSV upload failed for {file_type}: {'; '.join(result.errors)}. "
                f"Use dry_run=True to inspect details."
            )

        # Return dict with backward-compatible keys
        d = result.to_dict()
        d['scope'] = 'validation' if dry_run else 'customer'
        return d


# ===================================================================
# _process_data_impl — Single source of truth for data processing
# ===================================================================

def _process_data_impl(customer_id: int, mode: str = 'auto') -> dict:
    """Trigger the data processing pipeline for a customer.

    Modes:
    - 'auto' (default): Only score NEW months — existing health scores are immutable.
      Health scores are point-in-time artifacts; weight changes apply forward only.
    - 'full_recalc': Admin override — rewrite ALL months with current weights.

    Two paths for CSV loading:
    - Path 1 (DB-native): Data already in DB -> recalculate new health scores
    - Path 2 (Fresh CSV): No data in DB -> load CSVs into DB, then calculate

    Args:
        customer_id: The customer ID
        mode: 'auto' (immutable scores) or 'full_recalc' (admin rewrite)
    """
    import time as _time
    _pipeline_t0 = _time.time()

    _check_mcp_enabled()
    app = _get_flask_app()

    with app.app_context():
        from models import Customer
        from extensions import db as _db
        from models import Account, DC2SKPI, QualitativeSignal
        from pathlib import Path
        from datetime import datetime as _dt
        import pandas as pd

        customer = _db.session.get(Customer, int(customer_id))
        if not customer:
            raise ToolError(f"Customer {customer_id} not found.")

        vertical = getattr(customer, 'vertical', 'dc2_s') or 'dc2_s'
        backend_dir = Path(__file__).parent.parent
        data_dir = backend_dir / 'verticals' / f'customer{customer_id}-{vertical}' / 'data'

        steps_completed = []
        errors = []
        csv_files = []

        # ----------------------------------------------------------
        # Detect which path to take
        # ----------------------------------------------------------
        existing_accounts = Account.query.filter_by(customer_id=customer_id).all()
        existing_acct_ids = [a.account_id for a in existing_accounts]
        existing_kpi_count = DC2SKPI.query.filter(
            DC2SKPI.account_id.in_(existing_acct_ids)
        ).count() if existing_acct_ids else 0

        data_in_db = len(existing_accounts) > 0 and existing_kpi_count > 0
        has_csv_dir = data_dir.exists() and any(
            f.suffix == '.csv' for f in data_dir.iterdir()
        ) if data_dir.exists() else False

        if not data_in_db and not has_csv_dir:
            raise ToolError(
                f"No data found for customer {customer_id}. "
                f"Either upload CSV files via upload_csv() or ensure data is in the database."
            )

        # ----------------------------------------------------------
        # Detect incremental CSVs: data in DB AND new CSVs on disk.
        # Compare CSV file timestamps to last KPI upload timestamp.
        # If any CSV is newer, load them (Path 2) before recalculating.
        # ----------------------------------------------------------
        has_new_csvs = False  # default for fresh customers
        # ----------------------------------------------------------
        # full_recalc always reloads CSVs (semantic contract: redo everything).
        # For auto mode, use MAX(created_at) — the wall-clock insertion time.
        if mode == 'full_recalc' and has_csv_dir:
            has_new_csvs = True
        elif data_in_db and has_csv_dir:
            try:
                last_kpi_ts = _db.session.execute(_db.text(
                    "SELECT MAX(k.created_at) FROM dc2s_kpis k "
                    "JOIN accounts a ON k.account_id = a.account_id "
                    "WHERE a.customer_id = :cid"
                ), {"cid": customer_id}).scalar()

                for f in data_dir.iterdir():
                    if f.suffix == '.csv':
                        # last_kpi_ts (created_at) is stored via datetime.utcnow() — the
                        # mtime must be converted to UTC too, or this comparison is wrong
                        # by the host's UTC offset on any non-UTC machine (silently skips
                        # every same-day incremental reload).
                        csv_mtime = _dt.utcfromtimestamp(os.path.getmtime(str(f)))
                        # CSV file modified after last process_data run
                        if last_kpi_ts is None or csv_mtime > last_kpi_ts:
                            has_new_csvs = True
                            break
            except Exception as _inc_err:
                import logging as _log_inc
                _log_inc.getLogger(__name__).debug(f"Incremental CSV detection error (non-fatal): {_inc_err}")

        # ----------------------------------------------------------
        # Path 2: Load CSVs into DB
        #   - Fresh customer: no data in DB
        #   - Incremental: data in DB but newer CSVs on disk
        # ----------------------------------------------------------
        _csv_load_t0 = _time.time()
        if (not data_in_db and has_csv_dir) or has_new_csvs:
            csv_files = [f.name for f in data_dir.iterdir()
                         if f.is_file() and f.suffix == '.csv']

            # Step 1: Load accounts (prefer account_details.csv, fallback to accounts.csv)
            accounts_csv = data_dir / 'account_details.csv'
            _using_enriched = True
            if not accounts_csv.exists():
                accounts_csv = data_dir / 'accounts.csv'
                _using_enriched = False
            _products_extracted = False
            _stakeholders_extracted = False

            # All profile_metadata keys we extract from CSV columns
            _PROFILE_KEYS = [
                'contract_start', 'contract_end', 'renewal_date',
                'csm_name', 'csm_email', 'csm_manager',
                'executive_sponsor', 'tier',
                'primary_champion_name', 'primary_champion_title',
                'primary_champion_email', 'primary_champion_engagement_score',
                # Enriched account_details.csv fields
                'employee_count', 'tech_stack', 'cloud_provider',
                'deployment_type', 'competitive_landscape',
                'strategic_initiatives', 'budget_cycle', 'fiscal_year_end',
            ]

            if accounts_csv.exists():
                df_accts = pd.read_csv(str(accounts_csv))
                if not df_accts.empty:
                    _created_acct_ids = []  # track for post-load stakeholder extraction
                    for _, row in df_accts.iterrows():
                        aname = row.get('account_name', row.get('name', ''))
                        existing = Account.query.filter_by(
                            customer_id=customer_id, account_name=aname,
                        ).first()
                        if not existing:
                            # Build profile_metadata from CSV columns
                            _profile = {}
                            for _pkey in _PROFILE_KEYS:
                                _pval = row.get(_pkey)
                                if _pval is not None and str(_pval) != 'nan' and str(_pval) != '':
                                    _profile[_pkey] = str(_pval) if not isinstance(_pval, (int, float)) else _pval

                            # Parse products JSON column if present
                            _products_raw = row.get('products')
                            if _products_raw is not None and str(_products_raw) not in ('nan', '', 'None'):
                                try:
                                    import json as _json
                                    _prods = _json.loads(_products_raw) if isinstance(_products_raw, str) else _products_raw
                                    if isinstance(_prods, list):
                                        _profile['products'] = _prods
                                except (ValueError, TypeError):
                                    pass

                            acct = Account(
                                customer_id=customer_id, account_name=aname,
                                revenue=row.get('arr', row.get('annual_revenue', row.get('revenue', 0))),
                                vertical=vertical,
                                industry=str(row.get('industry', '')) if row.get('industry') and str(row.get('industry')) != 'nan' else None,
                                region=str(row.get('region', '')) if row.get('region') and str(row.get('region')) != 'nan' else None,
                                account_status=str(row.get('account_status', 'active')) if row.get('account_status') else 'active',
                                profile_metadata=_profile if _profile else None,
                            )
                            _db.session.add(acct)
                            _db.session.flush()  # get account_id
                            _created_acct_ids.append(acct.account_id)
                        else:
                            # Update existing account with any missing profile_metadata
                            _profile = existing.profile_metadata or {}
                            _updated = False
                            for _pkey in _PROFILE_KEYS:
                                _pval = row.get(_pkey)
                                if _pval is not None and str(_pval) != 'nan' and _pkey not in _profile:
                                    _profile[_pkey] = str(_pval) if not isinstance(_pval, (int, float)) else _pval
                                    _updated = True
                            # Parse products JSON on update too
                            _products_raw = row.get('products')
                            if _products_raw is not None and str(_products_raw) not in ('nan', '', 'None') and 'products' not in _profile:
                                try:
                                    import json as _json
                                    _prods = _json.loads(_products_raw) if isinstance(_products_raw, str) else _products_raw
                                    if isinstance(_prods, list):
                                        _profile['products'] = _prods
                                        _updated = True
                                except (ValueError, TypeError):
                                    pass
                            if _updated:
                                existing.profile_metadata = _profile
                            _created_acct_ids.append(existing.account_id)
                    _db.session.flush()
                    steps_completed.append('accounts_loaded_from_csv')

                    # ── Auto-extract products from profile_metadata into Product table ──
                    from models import Product
                    _prod_count = 0
                    for acct in Account.query.filter_by(customer_id=customer_id).all():
                        pm = acct.profile_metadata or {}
                        prods = pm.get('products', [])
                        if not isinstance(prods, list):
                            continue
                        for p in prods:
                            pname = p.get('name', '') if isinstance(p, dict) else str(p)
                            if not pname:
                                continue
                            existing_prod = Product.query.filter_by(
                                account_id=acct.account_id, product_name=pname).first()
                            if not existing_prod:
                                _db.session.add(Product(
                                    account_id=acct.account_id,
                                    customer_id=customer_id,
                                    product_name=pname,
                                    product_type=p.get('category', '') if isinstance(p, dict) else '',
                                    revenue=p.get('arr') if isinstance(p, dict) else None,
                                    status='active',
                                ))
                                _prod_count += 1
                    if _prod_count > 0:
                        _db.session.flush()
                        _products_extracted = True
                        steps_completed.append(f'products_extracted_from_account_details({_prod_count})')

                    # ── Auto-create STAKEHOLDER ContextNodes from profile_metadata ──
                    from models import ContextNode
                    _stk_count = 0
                    _STAKEHOLDER_FIELDS = [
                        ('primary_champion_name', 'champion', 'primary_champion_title', 'primary_champion_email'),
                        ('executive_sponsor', 'executive_sponsor', None, None),
                        ('csm_name', 'csm', None, 'csm_email'),
                        ('csm_manager', 'cs_manager', None, None),
                    ]
                    for acct in Account.query.filter_by(customer_id=customer_id).all():
                        pm = acct.profile_metadata or {}
                        for name_field, role, title_field, email_field in _STAKEHOLDER_FIELDS:
                            name_val = pm.get(name_field)
                            if not name_val or str(name_val) in ('nan', '', 'None'):
                                continue
                            # Check if stakeholder already exists for this account+role
                            existing_stk = ContextNode.query.filter_by(
                                customer_id=customer_id,
                                account_id=acct.account_id,
                                node_type='STAKEHOLDER',
                                node_subtype=role,
                            ).first()
                            if not existing_stk:
                                title_val = pm.get(title_field, '') if title_field else role.replace('_', ' ').title()
                                email_val = pm.get(email_field, '') if email_field else ''
                                _db.session.add(ContextNode(
                                    customer_id=customer_id,
                                    account_id=acct.account_id,
                                    node_type='STAKEHOLDER',
                                    source='account_details',
                                    node_subtype=role,
                                    title=f'{name_val} ({title_val})' if title_val else name_val,
                                    properties={
                                        'name': str(name_val),
                                        'role': role,
                                        'job_title': str(title_val) if title_val else '',
                                        'email': str(email_val) if email_val else '',
                                        'auto_created': True,
                                        'source_field': name_field,
                                    },
                                    tier=1,
                                    occurred_at=_dt.utcnow(),
                                    source_platform='account_details_extraction',
                                ))
                                _stk_count += 1
                    if _stk_count > 0:
                        _db.session.flush()
                        _stakeholders_extracted = True
                        steps_completed.append(f'stakeholders_extracted_from_account_details({_stk_count})')

            existing_accounts = Account.query.filter_by(customer_id=customer_id).all()
            existing_acct_ids = [a.account_id for a in existing_accounts]

            # Step 2: Build CSV->DB account ID mapping
            db_accounts = existing_accounts
            accounts_by_name = {a.account_name: a.account_id for a in db_accounts}
            accounts_by_db_id = {a.account_id: a for a in db_accounts}
            csv_to_db_aid = {}
            if accounts_csv.exists():
                df_accts = pd.read_csv(str(accounts_csv))
                for _, arow in df_accts.iterrows():
                    csv_aid = arow.get('source_account_id', arow.get('account_id'))
                    aname = arow.get('account_name', '')
                    if csv_aid and aname and aname in accounts_by_name:
                        csv_to_db_aid[int(csv_aid)] = accounts_by_name[aname]
            if not csv_to_db_aid:
                sorted_db = sorted(db_accounts, key=lambda a: a.account_id)
                for i, a in enumerate(sorted_db, 1):
                    csv_to_db_aid[customer_id * 1000 + i] = a.account_id

            def _resolve_acct_id(row):
                aname = row.get('account_name', row.get('account', ''))
                if aname and aname in accounts_by_name:
                    return accounts_by_name[aname]
                raw = row.get('source_account_id', row.get('account_id'))
                if raw is None:
                    return None
                raw = int(raw)
                # Check csv_to_db_aid FIRST — this maps CSV source_account_id
                # (e.g. 447001) to the real DB account_id (e.g. 732).
                # Without this priority, placeholder accounts with matching IDs
                # would intercept the lookup and KPIs would land on the wrong account.
                mapped = csv_to_db_aid.get(raw)
                if mapped is not None:
                    return mapped
                if raw in accounts_by_db_id:
                    return raw
                return None

            # Step 3: Load KPIs, signals, and other CSVs
            try:
                for csv_file in csv_files:
                    if csv_file == 'accounts.csv':
                        continue
                    csv_path = data_dir / csv_file
                    df = pd.read_csv(str(csv_path))
                    if df.empty:
                        continue

                    if 'kpi_measurements' in csv_file:
                        _kpi_added = 0
                        _kpi_skipped = 0
                        for _, row in df.iterrows():
                            acct_id = _resolve_acct_id(row)
                            if acct_id:
                                kpi_code = row.get('kpi_code', row.get('kpi_id', ''))
                                measured_at = row.get('measured_at', row.get('date'))

                                # Dedup: skip if exact (account, kpi_code, measured_at) already exists
                                if has_new_csvs:
                                    exists = DC2SKPI.query.filter_by(
                                        account_id=acct_id,
                                        kpi_code=kpi_code,
                                        measured_at=measured_at,
                                    ).first()
                                    if exists:
                                        _kpi_skipped += 1
                                        continue

                                kpi = DC2SKPI(
                                    account_id=acct_id,
                                    kpi_code=kpi_code,
                                    value=float(row.get('value', 0)),
                                    target=float(row.get('target', 100)),
                                    pillar=row.get('pillar', ''),
                                    weight=float(row.get('weight', 0)) if row.get('weight') else None,
                                    status=row.get('status', ''),
                                    measured_at=measured_at,
                                )
                                _db.session.add(kpi)
                                _kpi_added += 1
                        if has_new_csvs and _kpi_skipped > 0:
                            steps_completed.append(f'kpis_loaded_{_kpi_added}_new_{_kpi_skipped}_skipped')
                        else:
                            steps_completed.append('kpis_loaded')
                        # Commit KPIs immediately so a signals error can't roll them back
                        _db.session.commit()

                    elif 'qualitative_signals' in csv_file:
                        import uuid as _uuid
                        for _, row in df.iterrows():
                            acct_id = _resolve_acct_id(row)
                            if acct_id:
                                raw_sig_id = row.get('signal_id') or f"sig_{_uuid.uuid4().hex[:12]}"
                                # Customer-scope signal_id to prevent PK collision
                                # across tenants (e.g. two customers both having
                                # 'sig_424001_1' from the same manifest template).
                                sig_id = f"c{customer_id}_{raw_sig_id}" if not str(raw_sig_id).startswith(f"c{customer_id}_") else str(raw_sig_id)
                                # Truncate to 50 chars (PK column width)
                                sig_id = sig_id[:50]

                                # Dedup: skip if signal_id already exists for this customer
                                if has_new_csvs:
                                    exists = QualitativeSignal.query.filter_by(
                                        customer_id=int(customer_id), signal_id=sig_id
                                    ).first()
                                    if exists:
                                        continue

                                sh_name = str(row.get('stakeholder_name', '') or '').strip()
                                sh_title = str(row.get('stakeholder_title', '') or '').strip()
                                stakeholder_roles = None
                                if sh_name:
                                    stakeholder_roles = [
                                        {'name': sh_name, 'role': sh_title or 'contact'},
                                    ]

                                sig = QualitativeSignal(
                                    signal_id=sig_id, customer_id=int(customer_id),
                                    account_id=acct_id,
                                    signal_type=row.get('signal_type', 'nps'),
                                    content=row.get('content', row.get('signal_text', '')),
                                    sentiment=row.get('sentiment', 'neutral'),
                                    sentiment_score=float(row.get('sentiment_score', 0.5)),
                                    signal_date=row.get('signal_date', row.get('date')),
                                    stakeholder_roles=stakeholder_roles,
                                )
                                _db.session.add(sig)
                                sig_ref = row.get('signal_ref')
                                if sig_ref and str(sig_ref) != 'nan':
                                    from models import ContextNode as CN_
                                    # Dedup: skip if a ContextNode with same account+title+date already exists
                                    _sig_title = str(row.get('content') if str(row.get('content', '')).lower() not in ('nan', '', 'none') else row.get('signal_type', 'Signal'))[:200]
                                    _sig_date = pd.to_datetime(row.get('signal_date')) if row.get('signal_date') else _dt.utcnow()
                                    _existing_cn = CN_.query.filter(
                                        CN_.customer_id == customer_id,
                                        CN_.account_id == acct_id,
                                        CN_.node_type == 'SIGNAL',
                                        CN_.title == _sig_title,
                                    ).first()
                                    if _existing_cn:
                                        continue
                                    _sig_props = {
                                        'signal_ref': str(sig_ref),
                                        'sentiment': str(row.get('sentiment', '') or ''),
                                        'sentiment_score': str(row.get('sentiment_score', '') or ''),
                                    }
                                    if sh_name:
                                        _sig_props['stakeholder_name'] = sh_name
                                    if sh_title:
                                        _sig_props['stakeholder_title'] = sh_title
                                    sig_node = CN_(
                                        customer_id=customer_id, account_id=acct_id,
                                        node_type='SIGNAL',
                                        source='observed',
                                        node_subtype=str(row.get('signal_type', 'signal') or 'signal'),
                                        title=str(row.get('content') if str(row.get('content', '')).lower() not in ('nan', '', 'none') else row.get('signal_type', 'Signal'))[:200],
                                        properties=_sig_props,
                                        tier=2,
                                        occurred_at=pd.to_datetime(row.get('signal_date')) if row.get('signal_date') else _dt.utcnow(),
                                        source_platform=str(row.get('source_platform', 'csv_import')),
                                        source_event_id=str(sig_ref),
                                    )
                                    _db.session.add(sig_node)
                        steps_completed.append('signals_loaded')

                _db.session.commit()
                _step_timings_csv = round(_time.time() - _csv_load_t0, 2)
            except Exception as e:
                _step_timings_csv = round(_time.time() - _csv_load_t0, 2)
                errors.append(f"csv_loading: {str(e)}")
                try:
                    _db.session.rollback()
                except Exception:
                    pass

            # Steps 4-9: Context graph CSVs
            _cg_load_t0 = _time.time()
            # On incremental loads (has_new_csvs), skip CG node re-loading if nodes
            # already exist — only load new KPIs/signals above. CG regeneration is
            # handled by the ContextGraphRegenerationSubscriber when health changes.
            try:
                from models import ContextNode, ContextEdge
                _skip_cg_reload = (has_new_csvs and mode != 'full_recalc'
                                   and ContextNode.query.filter_by(
                                       customer_id=customer_id).first() is not None)
                if _skip_cg_reload:
                    import logging as _log_cg
                    _log_cg.getLogger(__name__).info(
                        f"Incremental load: skipping CG node re-loading for customer {customer_id} "
                        f"(CG nodes already exist, will regenerate via event subscriber)"
                    )
                    steps_completed.append('context_graph_incremental_skip')

                # Stakeholders
                stakeholder_path = data_dir / 'stakeholders.csv'
                if not stakeholder_path.exists():
                    stakeholder_path = data_dir / 'context_graph' / 'stakeholders.csv'
                if stakeholder_path.exists() and not _skip_cg_reload and not _stakeholders_extracted:
                    df_s = pd.read_csv(str(stakeholder_path))
                    for _, row in df_s.iterrows():
                        acct_id = _resolve_acct_id(row)
                        if not acct_id:
                            continue
                        _db.session.add(ContextNode(
                            customer_id=customer_id, account_id=acct_id,
                            node_type='STAKEHOLDER',
                            source='observed',
                            node_subtype=str(row.get('role', 'contact')),
                            title=str(row.get('stakeholder_name', row.get('name', ''))),
                            properties={
                                'job_title': str(row.get('title', '')),
                                'email': str(row.get('email', '')),
                                'department': str(row.get('department', '')),
                                'influence_score': str(row.get('influence_score', '')),
                                'engagement_frequency': str(row.get('engagement_frequency', '')),
                                'sentiment': str(row.get('sentiment', '')),
                            },
                            tier=1,
                            occurred_at=pd.to_datetime(row.get('first_observed_at')) if row.get('first_observed_at') and str(row.get('first_observed_at')) != 'nan' else _dt.utcnow(),
                            source_platform=str(row.get('source_platform', 'csv_import')),
                        ))
                    _db.session.flush()
                    steps_completed.append('stakeholders_loaded')

                    # Link stakeholders to decisions via INVOLVES edges
                    ROLE_DECISION_MAP = {
                        'champion': ['renewal', 'champion', 'renewal_confirmed'],
                        'executive_sponsor': ['escalation', 'executive_sponsor', 'playbook'],
                        'technical_lead': ['technical', 'playbook', 'remediation'],
                        'csm': ['playbook', 'intervention', 'playbook_crisis_recovery', 'playbook_exec_sponsor_change'],
                        'primary_contact': ['renewal', 'champion'],
                    }

                    try:
                        _stakeholder_nodes = ContextNode.query.filter_by(
                            customer_id=customer_id, node_type='STAKEHOLDER'
                        ).all()
                        _decision_nodes = ContextNode.query.filter_by(
                            customer_id=customer_id, node_type='DECISION'
                        ).all()

                        _edges_created = 0
                        for sn in _stakeholder_nodes:
                            role = (sn.node_subtype or '').lower()
                            match_subtypes = []
                            for role_key, subtypes in ROLE_DECISION_MAP.items():
                                if role_key in role:
                                    match_subtypes = subtypes
                                    break
                            if not match_subtypes:
                                match_subtypes = ['playbook', 'renewal']  # default

                            for dn in _decision_nodes:
                                if dn.account_id != sn.account_id:
                                    continue
                                dec_sub = (dn.node_subtype or '').lower()
                                if any(ms in dec_sub for ms in match_subtypes):
                                    existing = ContextEdge.query.filter_by(
                                        from_node_id=sn.node_id, to_node_id=dn.node_id
                                    ).first()
                                    if not existing:
                                        _db.session.add(ContextEdge(
                                            customer_id=customer_id,
                                            from_node_id=sn.node_id,
                                            to_node_id=dn.node_id,
                                            edge_type='INVOLVES',
                                            confidence=0.8,
                                            properties={'source': 'role_match', 'stakeholder_role': role},
                                        ))
                                        _edges_created += 1

                        if _edges_created:
                            _db.session.flush()
                            steps_completed.append(f'stakeholder_edges_{_edges_created}')
                    except Exception as _se:
                        import logging as _slog
                        _slog.getLogger(__name__).warning(f'Stakeholder edge creation: {_se}')

                # Outcomes
                outcomes_path = data_dir / 'outcomes.csv'
                if not outcomes_path.exists():
                    outcomes_path = data_dir / 'context_graph' / 'outcomes.csv'
                if outcomes_path.exists() and not _skip_cg_reload:
                    df_o = pd.read_csv(str(outcomes_path))
                    for _, row in df_o.iterrows():
                        acct_id = _resolve_acct_id(row)
                        if not acct_id:
                            continue
                        rev_impact = None
                        for rev_col in ('revenue_value', 'revenue_impact'):
                            try:
                                v = row.get(rev_col)
                                if v is not None and str(v).strip():
                                    rev_impact = float(v)
                                    break
                            except (ValueError, TypeError):
                                pass
                        # Store outcome_type as source_event_id for edge resolution
                        outcome_type = str(row.get('outcome_type', 'revenue'))
                        outcome_src_id = f"outcome:{outcome_type}" if outcome_type else None
                        # Parse outcome_date for correct timeline ordering
                        raw_out_date = row.get('outcome_date')
                        out_occurred_at = pd.to_datetime(raw_out_date) if raw_out_date and str(raw_out_date) != 'nan' else _dt.utcnow()
                        _db.session.add(ContextNode(
                            customer_id=customer_id, account_id=acct_id,
                            node_type='OUTCOME',
                            source='observed',
                            node_subtype=outcome_type,
                            title=str(row.get('title', row.get('outcome_name', ''))),
                            revenue_impact=rev_impact,
                            revenue_impact_type=outcome_type,
                            properties={'evidence': str(row.get('evidence', '')),
                                        'confidence': str(row.get('confidence', ''))},
                            tier=1, occurred_at=out_occurred_at,
                            source_platform=str(row.get('source_platform', 'csv_import')),
                            source_event_id=outcome_src_id,
                        ))
                    _db.session.flush()
                    steps_completed.append('outcomes_loaded')

                # Decisions
                decisions_path = data_dir / 'decisions.csv'
                if not decisions_path.exists():
                    decisions_path = data_dir / 'context_graph' / 'decisions.csv'
                if decisions_path.exists() and not _skip_cg_reload:
                    df_d = pd.read_csv(str(decisions_path))
                    for _, row in df_d.iterrows():
                        acct_id = _resolve_acct_id(row)
                        if not acct_id:
                            continue
                        dec_id = str(row.get('decision_id', '')).strip()
                        # source_event_id uses 'decision:<id>' prefix so _resolve_edge_ref
                        # can find this node via srcid_to_node lookup
                        src_eid = f'decision:{dec_id}' if dec_id and dec_id != 'nan' else None
                        # Parse decision_date for correct timeline ordering
                        raw_dec_date = row.get('decision_date')
                        dec_occurred_at = pd.to_datetime(raw_dec_date) if raw_dec_date and str(raw_dec_date) != 'nan' else _dt.utcnow()
                        _db.session.add(ContextNode(
                            customer_id=customer_id, account_id=acct_id,
                            node_type='DECISION',
                            source='observed',
                            node_subtype=str(row.get('decision_maker_role', 'action')),
                            title=str(row.get('title', row.get('decision_name', ''))),
                            properties={'chosen_option': str(row.get('chosen_option', '')),
                                        'outcome_description': str(row.get('outcome_description', '')),
                                        'risk_level': str(row.get('risk_level', '')),
                                        'decision_id': dec_id},
                            tier=1, occurred_at=dec_occurred_at,
                            source_platform=str(row.get('source_platform', 'csv_import')),
                            source_event_id=src_eid,
                        ))
                    _db.session.flush()
                    steps_completed.append('decisions_loaded')

                # Engagement Events
                ee_path = data_dir / 'engagement_events.csv'
                if ee_path.exists() and not _skip_cg_reload:
                    df_ee = pd.read_csv(str(ee_path))
                    for _, row in df_ee.iterrows():
                        acct_id = _resolve_acct_id(row)
                        if not acct_id:
                            continue
                        evt_date = row.get('event_date')
                        # Title: prefer 'title', fall back to 'description', then construct from event_type
                        ee_title = str(row.get('title', '') or row.get('description', '') or '')
                        if not ee_title or ee_title == 'nan':
                            ee_type = str(row.get('event_type', 'engagement'))
                            ee_title = ee_type.replace('_', ' ').title()
                        _db.session.add(ContextNode(
                            customer_id=customer_id, account_id=acct_id,
                            node_type='SIGNAL', node_subtype='engagement',
                            source='observed',
                            title=ee_title[:200],
                            properties={
                                'event_type': str(row.get('event_type', '')),
                                'channel': str(row.get('channel', '')),
                                'duration_minutes': str(row.get('duration_minutes', '')),
                                'outcome': str(row.get('outcome', '')),
                                'participants': str(row.get('participants', '')),
                                'notes': str(row.get('notes', '')),
                                'stakeholder_name': str(row.get('stakeholder_name', '')),
                                'sentiment_shift': str(row.get('sentiment_shift', '')),
                            },
                            tier=2,
                            occurred_at=pd.to_datetime(evt_date) if evt_date else _dt.utcnow(),
                            source_platform=str(row.get('source_platform', 'csv_import')),
                        ))
                    steps_completed.append('engagement_events_loaded')

                # Enhanced Qualitative Signals → SIGNAL ContextNodes
                # Skip if qualitative_signals.csv was already processed above
                # (the QualitativeSignal path at line ~1051 creates ContextNodes
                # for signals with signal_ref — processing the same file again
                # here would create duplicates).
                _eqs_already_processed = any(
                    'qualitative_signals' in f for f in csv_files
                )

                _existing_sig_refs = set()
                if not _eqs_already_processed:
                    try:
                        _existing = ContextNode.query.filter_by(
                            customer_id=customer_id, node_type='SIGNAL', source='observed'
                        ).with_entities(ContextNode.source_event_id).all()
                        _existing_sig_refs = {r[0] for r in _existing if r[0]}
                    except Exception:
                        pass

                # Only process enhanced_qualitative_signals.csv (old format) if
                # qualitative_signals.csv wasn't already handled above
                eqs_path = None
                if not _eqs_already_processed:
                    eqs_path = data_dir / 'enhanced_qualitative_signals.csv'
                    if not eqs_path.exists():
                        eqs_path = data_dir / 'context_graph' / 'enhanced_qualitative_signals.csv'
                    if not eqs_path.exists():
                        eqs_path = None
                if eqs_path and not _skip_cg_reload:
                    df_eqs = pd.read_csv(str(eqs_path))
                    _eqs_deduped = 0
                    for _, row in df_eqs.iterrows():
                        acct_id = _resolve_acct_id(row)
                        if not acct_id:
                            continue
                        sig_ref = str(row.get('signal_ref', '')).strip()
                        # Skip if this signal_ref was already created
                        if sig_ref and sig_ref != 'nan' and sig_ref in _existing_sig_refs:
                            _eqs_deduped += 1
                            continue
                        if sig_ref and sig_ref != 'nan':
                            _existing_sig_refs.add(sig_ref)
                        _db.session.add(ContextNode(
                            customer_id=customer_id, account_id=acct_id,
                            node_type='SIGNAL',
                            source='observed',
                            node_subtype=str(row.get('signal_type', 'signal') or 'signal'),
                            title=str(row.get('content', ''))[:200],
                            properties={
                                'signal_ref': sig_ref,
                                'signal_type': str(row.get('signal_type', '')),
                                'sentiment': str(row.get('sentiment', '')),
                                'sentiment_score': str(row.get('sentiment_score', '')),
                            },
                            tier=2,
                            occurred_at=pd.to_datetime(row.get('signal_date')) if row.get('signal_date') else _dt.utcnow(),
                            source_platform=str(row.get('source_platform', 'csv_import')),
                            source_event_id=sig_ref if sig_ref and sig_ref != 'nan' else None,
                        ))
                    _db.session.flush()
                    _loaded = len(df_eqs) - _eqs_deduped
                    steps_completed.append(f'enhanced_signals_cg_loaded_{_loaded}_deduped_{_eqs_deduped}')

                # Products (skip if already extracted from account_details.csv)
                try:
                    from models import Product
                    prod_path = data_dir / 'products.csv'
                    if prod_path.exists() and not _products_extracted:
                        df_p = pd.read_csv(str(prod_path))
                        for _, row in df_p.iterrows():
                            acct_id = _resolve_acct_id(row)
                            if not acct_id:
                                continue
                            pname = str(row.get('product_name', ''))
                            if pname:
                                existing_prod = Product.query.filter_by(
                                    account_id=acct_id, product_name=pname).first()
                                if not existing_prod:
                                    _db.session.add(Product(
                                        account_id=acct_id, customer_id=customer_id,
                                        product_name=pname,
                                        product_type=row.get('product_category', row.get('product_type', '')),
                                        status=row.get('status', 'active'),
                                    ))
                        steps_completed.append('products_loaded')
                except Exception:
                    pass

                # Profiles
                bp_path = data_dir / 'account_business_profiles.csv'
                if bp_path.exists():
                    accounts_by_db_id_fresh = {a.account_id: a for a in existing_accounts}
                    df_bp = pd.read_csv(str(bp_path))
                    for _, row in df_bp.iterrows():
                        acct_id = _resolve_acct_id(row)
                        if not acct_id or acct_id not in accounts_by_db_id_fresh:
                            continue
                        acct = accounts_by_db_id_fresh[acct_id]
                        profile = {}
                        for col in ['arr', 'employee_count', 'industry', 'fiscal_year_end',
                                    'tech_stack', 'cloud_provider', 'competitive_landscape',
                                    'strategic_initiatives', 'budget_cycle', 'assigned_csm',
                                    'csm_manager', 'executive_sponsor', 'mrr',
                                    'primary_champion_name', 'primary_champion_title',
                                    'primary_champion_email', 'primary_champion_engagement_score']:
                            val = row.get(col)
                            if val is not None and str(val).strip() and str(val) != 'nan':
                                profile[col] = str(val) if not isinstance(val, (int, float)) else val
                        acct.profile_metadata = profile
                        arr_val = row.get('arr')
                        if arr_val and str(arr_val) != 'nan':
                            try:
                                acct.revenue = float(arr_val)
                            except (ValueError, TypeError):
                                pass
                    steps_completed.append('profiles_loaded')

                # Benchmarks
                bench_path = data_dir / 'industry_benchmarks.csv'
                if bench_path.exists() and existing_accounts:
                    first_acct_id = existing_accounts[0].account_id
                    df_bench = pd.read_csv(str(bench_path))
                    for _, row in df_bench.iterrows():
                        kpi_code = row.get('kpi_code', '')
                        _db.session.add(ContextNode(
                            customer_id=customer_id, account_id=first_acct_id,
                            node_type='EXTERNAL_CONTEXT', node_subtype='industry_benchmark',
                            source='observed',
                            title=f'Benchmark: {kpi_code}',
                            properties={
                                'kpi_code': str(kpi_code),
                                'benchmark_source': str(row.get('benchmark_source', '')),
                                'industry_p50': str(row.get('industry_p50', '')),
                                'industry_p25': str(row.get('industry_p25', '')),
                                'industry_p75': str(row.get('industry_p75', '')),
                                'account_percentile': str(row.get('account_percentile', '')),
                                'sample_size': str(row.get('sample_size', '')),
                            },
                            tier=1, occurred_at=_dt.utcnow(),
                            source_platform='csv_import',
                            source_event_id=f'bench_{kpi_code}',
                        ))
                    steps_completed.append('benchmarks_loaded')

                _db.session.commit()

                # Signal Edges (must run last — needs all nodes)
                se_path = data_dir / 'signal_edges.csv'
                if not se_path.exists():
                    se_path = data_dir / 'context_graph' / 'signal_edges.csv'
                if se_path.exists():
                    # Clear existing CSV-imported edges before re-inserting (idempotent)
                    ContextEdge.query.filter_by(
                        customer_id=customer_id, source_platform='csv_import'
                    ).delete(synchronize_session='fetch')
                    _db.session.flush()
                    df_se = pd.read_csv(str(se_path))
                    all_nodes = ContextNode.query.filter_by(customer_id=customer_id).all()
                    title_to_node, sigref_to_node, srcid_to_node = {}, {}, {}
                    # Per-account lookup for refs shared across accounts (e.g. outcome:revenue_at_risk)
                    acct_srcid_to_node = {}  # (account_id, ref) → node_id
                    for n in all_nodes:
                        if n.title:
                            title_to_node[n.title.strip()] = n.node_id
                            title_to_node[n.title.strip()[:60]] = n.node_id
                        if n.source_event_id:
                            srcid_to_node[n.source_event_id] = n.node_id
                            acct_srcid_to_node[(n.account_id, n.source_event_id)] = n.node_id
                        if n.properties and isinstance(n.properties, dict):
                            sr = n.properties.get('signal_ref')
                            if sr:
                                sigref_to_node[str(sr)] = n.node_id
                                acct_srcid_to_node[(n.account_id, str(sr))] = n.node_id

                    def _resolve_edge_ref(ref_str, account_id=None):
                        if not ref_str or str(ref_str) == 'nan':
                            return None
                        ref_str = str(ref_str).strip()

                        # Strategy 0: Per-account scoped lookup (handles outcome:type refs)
                        if account_id:
                            nid = acct_srcid_to_node.get((account_id, ref_str))
                            if nid:
                                return nid

                        # Strategy 1: Direct signal_ref or source_event_id
                        nid = sigref_to_node.get(ref_str) or srcid_to_node.get(ref_str)
                        if nid:
                            return nid

                        # Strategy 1b: CSV refs without prefix → DB source_event_ids WITH prefix
                        # e.g. CSV "dec_10001_1" → DB "decision:dec_10001_1"
                        #      CSV "revenue_at_risk" → DB "outcome:revenue_at_risk"
                        for prefix in ('decision:', 'outcome:', 'signal:'):
                            prefixed = f'{prefix}{ref_str}'
                            if account_id:
                                nid = acct_srcid_to_node.get((account_id, prefixed))
                                if nid:
                                    return nid
                            nid = srcid_to_node.get(prefixed)
                            if nid:
                                return nid

                        # Strategy 2: Split on separator, try phase_ref + title
                        phase_ref, title_part = None, None
                        for sep in [' \u2014 ', ' \u2013 ', ' - ']:
                            if sep in ref_str:
                                phase_ref = ref_str.split(sep, 1)[0].strip()
                                title_part = ref_str.split(sep, 1)[1].strip()
                                break
                        if phase_ref:
                            if account_id:
                                nid = acct_srcid_to_node.get((account_id, phase_ref))
                                if nid:
                                    return nid
                            nid = sigref_to_node.get(phase_ref) or srcid_to_node.get(phase_ref)
                            if nid:
                                return nid
                        if title_part:
                            for t in [title_part, title_part[:200], title_part[:60]]:
                                nid = title_to_node.get(t)
                                if nid:
                                    return nid

                        return title_to_node.get(ref_str)

                    edges_created = 0
                    for _, row in df_se.iterrows():
                        edge_acct = _resolve_acct_id(row)
                        from_id = _resolve_edge_ref(row.get('from_signal_ref'), account_id=edge_acct)
                        to_id = _resolve_edge_ref(row.get('to_signal_ref'), account_id=edge_acct)
                        if from_id and to_id and from_id != to_id:
                            edge = ContextEdge(
                                customer_id=customer_id,
                                from_node_id=from_id, to_node_id=to_id,
                                edge_type=str(row.get('edge_type', 'LED_TO')),
                                weight=float(row.get('weight', 1.0)),
                                confidence=float(row.get('confidence', 1.0)) if row.get('confidence') else 1.0,
                                source_platform=str(row.get('source_platform', 'csv_import')),
                                created_by=str(row.get('created_by', 'process_data')),
                                properties={'evidence': str(row.get('evidence', ''))},
                            )
                            rev = row.get('revenue_impact')
                            if rev and str(rev) != 'nan':
                                try:
                                    edge.revenue_impact = float(rev)
                                except (ValueError, TypeError):
                                    pass
                            lag = row.get('lag_days')
                            if lag and str(lag) != 'nan':
                                try:
                                    edge.lag_days = int(float(lag))
                                except (ValueError, TypeError):
                                    pass
                            _db.session.add(edge)
                            edges_created += 1
                    _db.session.commit()
                    steps_completed.append(f'edges_loaded_{edges_created}')

                steps_completed.append('context_graph_loaded')
                _step_timings_cg = round(_time.time() - _cg_load_t0, 2)
            except Exception as e:
                _step_timings_cg = round(_time.time() - _cg_load_t0, 2)
                errors.append(f"context_graph: {str(e)}")
                try:
                    _db.session.rollback()
                except Exception:
                    pass

        else:
            _step_timings_csv = 0
            _step_timings_cg = 0
            steps_completed.append(
                f'data_already_in_db_{len(existing_accounts)}_accounts_{existing_kpi_count}_kpis'
            )

        # ══════════════════════════════════════════════════════════
        # POST-PROCESSING PIPELINE — delegated to process_data_pipeline.py
        # Each stage is standalone, testable, never raises, logs own errors.
        # ══════════════════════════════════════════════════════════
        from mcp_server.process_data_pipeline import (
            run_proactive_signal_scan,
            calculate_health_scores,
            run_wizard_a_step,
            run_llm_tier1_inference,
            run_wizard_b_step,
            run_signal_analyst,
            run_urgent_scanner,
            run_roi_engine,
            run_qdrant_indexing,
            run_onboarding_agent_analyze,
            publish_health_events,
            record_wizard_run,
        )

        _step_timings = {}
        _step_timings['csv_load'] = _step_timings_csv
        _step_timings['cg_load'] = _step_timings_cg

        # Stage 2: Health score calculation (immutable — only new months)
        # NOTE: Proactive signal scan moved to Stage 2c (after health scores exist)
        # so that signal-triggered playbooks can look up health_at_trigger.
        acct_list = Account.query.filter_by(customer_id=customer_id).all()
        _health_step, _changed_account_ids, _health_timings = calculate_health_scores(
            customer_id=customer_id,
            acct_list=acct_list,
            vertical=vertical,
            mode=mode,
        )
        if _health_step:
            steps_completed.append(_health_step)
        _step_timings.update(_health_timings)

        # Publish health events for downstream subscribers
        _t_stage = _time.time()
        if _changed_account_ids:
            existing_acct_ids = [a.account_id for a in acct_list]
            publish_health_events(customer_id, existing_acct_ids)
        _step_timings['event_publish'] = round(_time.time() - _t_stage, 2)

        # Stage 2b: Back-fill product adoption from P1 pillar score
        _t_adoption = _time.time()
        try:
            from models import HealthScore as _HS
            _adoption_count = 0
            for acct in acct_list:
                pm = acct.profile_metadata or {}
                prods = pm.get('products', [])
                if not isinstance(prods, list) or not prods:
                    continue
                # Get latest health score with contributing_pillars
                latest_hs = _HS.query.filter_by(
                    account_id=acct.account_id
                ).order_by(_HS.measurement_month.desc()).first()
                if latest_hs and latest_hs.contributing_pillars:
                    p1_score = latest_hs.contributing_pillars.get('P1')
                    if p1_score is not None:
                        for p in prods:
                            if isinstance(p, dict):
                                p['adoption'] = round(float(p1_score), 1)
                        pm['products'] = prods
                        pm['product_adoption'] = round(float(p1_score), 1)
                        acct.profile_metadata = pm
                        _adoption_count += 1
            if _adoption_count > 0:
                _db.session.commit()
                steps_completed.append(f'product_adoption_backfill({_adoption_count})')
        except Exception as _adopt_err:
            import logging as _log_adopt
            _log_adopt.getLogger(__name__).debug(f"Product adoption back-fill failed (non-fatal): {_adopt_err}")
        _step_timings['product_adoption'] = round(_time.time() - _t_adoption, 2)

        # Stage 2c: Proactive signal scan (runs AFTER health scores so
        # signal-triggered playbooks can look up health_at_trigger/close)
        _t_stage = _time.time()
        _step = run_proactive_signal_scan(customer_id)
        if _step:
            steps_completed.append(_step)
        _step_timings['signal_scan'] = round(_time.time() - _t_stage, 2)

        # Stage 3: Wizard A — arc classification (incremental)
        _wa_step, _wa_duration = run_wizard_a_step(customer_id, _changed_account_ids, mode)
        if _wa_step:
            steps_completed.append(_wa_step)
        _step_timings['wizard_a'] = _wa_duration

        # Stage 3a: LLM Tier 1 Inference (gated — only runs if WITH_LLM enabled + API key)
        _llm_step, _llm_duration = run_llm_tier1_inference(customer_id)
        if _llm_step:
            steps_completed.append(_llm_step)
        _step_timings['llm_inference'] = _llm_duration

        # Stage 3b: Wizard B — pattern analysis (auto after Wizard A, needs ≥5 journeys)
        _wb_step, _wb_duration = run_wizard_b_step(customer_id)
        if _wb_step:
            steps_completed.append(_wb_step)
        _step_timings['wizard_b'] = _wb_duration

        # Stage 4: Signal analyst (Layer A)
        _t_stage = _time.time()
        run_signal_analyst(customer_id)
        _step_timings['signal_analyst'] = round(_time.time() - _t_stage, 2)

        # Stage 5: Urgent signal scanner (Layer C)
        _t_stage = _time.time()
        _urgent_step = run_urgent_scanner(customer_id)
        if _urgent_step:
            steps_completed.append(_urgent_step)
        _step_timings['urgent_scanner'] = round(_time.time() - _t_stage, 2)

        # Stage 6: ROI engine
        _t_stage = _time.time()
        _roi_step = run_roi_engine(customer_id)
        if _roi_step:
            steps_completed.append(_roi_step)
        _step_timings['roi_engine'] = round(_time.time() - _t_stage, 2)

        # Stage 6a: Seed approval queue from vertical-aware playbook recommendations
        # (config-playbook verticals only: dc2_s, datacenter_v1). Non-fatal, idempotent.
        _t_stage = _time.time()
        try:
            from playbook_recommendations_api import seed_approval_queue_from_recommendations
            _seed = seed_approval_queue_from_recommendations(customer_id)
            if _seed.get('seeded'):
                steps_completed.append(f"approval_seed_{_seed['seeded']}")
            logger.info(f"Approval-queue seed for customer {customer_id}: {_seed}")
        except Exception as _e:
            logger.warning(f"Approval-queue seed failed (non-fatal): {_e}")
        _step_timings['approval_seed'] = round(_time.time() - _t_stage, 2)

        # Stage 7: QDRANT indexing
        _t_stage = _time.time()
        _qdrant_step = run_qdrant_indexing(customer_id)
        if _qdrant_step:
            steps_completed.append(_qdrant_step)
        _step_timings['qdrant'] = round(_time.time() - _t_stage, 2)

        # Stage 8: Onboarding activation plan (once per customer; non-fatal)
        _onboarding_step, _onboarding_duration = run_onboarding_agent_analyze(customer_id)
        if _onboarding_step:
            steps_completed.append(_onboarding_step)
        _step_timings['onboarding_agent'] = _onboarding_duration

        # ── Result + tracking ──
        status = 'success' if steps_completed and not errors else 'partial' if steps_completed else 'failed'
        _pipeline_duration = round(_time.time() - _pipeline_t0, 1)
        _step_timings['total'] = _pipeline_duration

        # Record WizardRun for audit trail
        _scores_written = int(_health_step.split('_')[-2]) if _health_step and '_' in _health_step else 0
        record_wizard_run(
            customer_id=customer_id,
            mode=mode,
            duration_s=_pipeline_duration,
            scores_written=_scores_written,
            changed_accounts=len(_changed_account_ids),
            timings=_step_timings,
            pipeline_status=status,
        )

        import logging as _log_pd
        _log_pd.getLogger(__name__).info(
            f"process_data complete: customer={customer_id} mode={mode} "
            f"duration={_pipeline_duration}s timings={_step_timings}"
        )

        # Activity log: system action visibility
        try:
            from activity_logging import ActivityLogger
            ActivityLogger.log_activity(
                customer_id=customer_id,
                action_type='health_recalculation',
                action_description=f"Pipeline {mode}: {len(acct_list)} accounts, {_pipeline_duration:.1f}s",
                resource_type='pipeline',
                details={'mode': mode, 'accounts': len(acct_list), 'duration_s': round(_pipeline_duration, 1)},
                status=status,
            )
        except Exception:
            pass

        return {
            'scope': 'customer',
            'customer_id': customer_id,
            'status': status,
            'mode': mode,
            'accounts': len(acct_list),
            'kpi_measurements': existing_kpi_count or DC2SKPI.query.filter(
                DC2SKPI.account_id.in_([a.account_id for a in acct_list])).count(),
            'csv_files_processed': csv_files if csv_files else None,
            'steps_completed': steps_completed,
            'errors': errors,
            'duration_s': _pipeline_duration,
            'timings': _step_timings,
            'message': (
                f"Data processing {'completed' if status == 'success' else 'completed with issues'} "
                f"(mode={mode}, {_pipeline_duration}s). "
                f"Steps: {', '.join(steps_completed) if steps_completed else 'none'}."
            ),
        }

        # Legacy post-processing code (350+ lines) has been extracted to
        # process_data_pipeline.py — see git history for the original inline version.
        # ── END OF _process_data_impl ──
# ===================================================================
# Tool: process_data
# ===================================================================

@mcp.tool
def process_data(customer_id: int, mode: str = 'auto') -> dict:
    """Trigger the data processing pipeline for a customer.

    Processes uploaded CSV files through the pipeline:
    1. Data loading (CSVs -> PostgreSQL)
    2. Health score calculation (incremental — only NEW months)
    3. Wizard A — arc classification + context graph generation (rule-based)
    4. Wizard B — pattern analysis (requires ≥5 accounts)
    5. Signal analysis + ROI engine
    6. Onboarding activation plan (LLM if entitled, else rule-based fallback)

    With just 3 CSVs (accounts, kpis, signals), the pipeline generates a full
    context graph automatically:
    - Arc classification: 8 deterministic rules (health thresholds + signal matching)
    - Edge generation: template-driven from arc topology (no LLM, no hallucination)
    - Revenue intelligence: ROI engine computes Power-of-1 impact

    Health scores are immutable: once written for (account, month), they are
    never retroactively recalculated. Weight changes apply forward only.

    Args:
        customer_id: The customer ID
        mode: 'auto' (default, immutable scores) or 'full_recalc' (admin rewrite)
    """
    _require_auth_if_key_present('process_data', customer_id)
    if mode not in ('auto', 'full_recalc'):
        mode = 'auto'
    return _process_data_impl(customer_id, mode=mode)


# ===================================================================
# Tool: trigger_wizard
# ===================================================================

@mcp.tool
def trigger_wizard(customer_id: int, wizard: str) -> dict:
    """Trigger a wizard (A, B, or C) for a customer.

    Wizards perform advanced analysis:
    - Wizard A: Journey generation — creates journey JSON for each account
    - Wizard B: Pattern analysis — extracts patterns, early warnings, phase transitions
    - Wizard C: Weight calibration — self-learning optimal KPI/pillar weights

    Args:
        customer_id: The customer ID
        wizard: Which wizard to trigger: 'a', 'b', or 'c'
    """
    _require_auth_if_key_present('trigger_wizard', customer_id)
    _check_mcp_enabled()
    app = _get_flask_app()

    with app.app_context():
        from models import Customer, WizardRun
        from extensions import db
        from pathlib import Path
        from datetime import datetime

        customer = db.session.get(Customer, int(customer_id))
        if not customer:
            raise ToolError(f"Customer {customer_id} not found.")

        wizard = wizard.lower().strip()
        if wizard not in ('a', 'b', 'c'):
            raise ToolError(f"Invalid wizard '{wizard}'. Must be 'a', 'b', or 'c'.")

        wizard_name = {
            'a': 'Journey Generation',
            'b': 'Pattern Analysis',
            'c': 'Weight Calibration',
        }[wizard]

        import uuid as _uuid
        run_id = f"wizard_{wizard}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{_uuid.uuid4().hex[:8]}"

        run = WizardRun(
            run_id=run_id,
            customer_id=customer_id,
            status='queued',
            config={'wizard': wizard, 'triggered_via': 'mcp_onboarding'},
        )
        db.session.add(run)
        db.session.commit()

        result_summary = {}

        try:
            db.session.rollback()

            if wizard == 'a':
                from wizards.wizard_a_journey_db import run_wizard_a
                wiz_result = run_wizard_a(customer_id)
                result_summary = wiz_result
                result_summary['return_code'] = 0

            elif wizard == 'b':
                try:
                    from wizards.wizard_b_pattern_db import run_wizard_b
                    wiz_result = run_wizard_b(customer_id)
                    result_summary = wiz_result
                    result_summary['return_code'] = 0
                except Exception as wb_err:
                    result_summary['error'] = str(wb_err)
                    result_summary['return_code'] = 1

            elif wizard == 'c':
                from wizards.wizard_c_weight_calibrator_db import run_wizard_c
                wiz_result = run_wizard_c(customer_id)
                result_summary = wiz_result
                result_summary['return_code'] = 0

            elif wizard == 'd':
                # Predictor v3 calibrator. Required after any onboarding /
                # data refresh — without it, predict_for_account_id falls
                # back to CDI seed priors (prediction_method='cold_start')
                # and per-account NRR forecasts are non-tenant-specific.
                try:
                    from wizards.wizard_d_predictor_calibrator import run_wizard_d
                    wiz_result = run_wizard_d(customer_ids=[customer_id])
                    result_summary = wiz_result
                    # run_wizard_d returns 'status' not 'return_code'
                    result_summary['return_code'] = (
                        0 if wiz_result.get('status') == 'completed' else 1
                    )
                except Exception as wd_err:
                    result_summary['error'] = str(wd_err)
                    result_summary['return_code'] = 1

            run.status = 'completed' if result_summary.get('return_code', 1) == 0 else 'failed'
            run.completed_at = datetime.utcnow()
            run.results = result_summary
            db.session.commit()

        except Exception as e:
            run.status = 'failed'
            run.error_message = str(e)
            run.completed_at = datetime.utcnow()
            db.session.commit()
            result_summary['error'] = str(e)

        # Activity log: wizard execution visibility
        try:
            from activity_logging import ActivityLogger
            ActivityLogger.log_activity(
                customer_id=customer_id,
                action_type='wizard_execution',
                action_description=f"Wizard {wizard.upper()} ({wizard_name}): {run.status}",
                resource_type='wizard',
                resource_id=run_id,
                details={'wizard': wizard, 'wizard_name': wizard_name, 'status': run.status},
                status='success' if run.status == 'completed' else 'failure',
            )
        except Exception:
            pass

        return {
            'scope': 'customer',
            'customer_id': customer_id,
            'wizard': wizard,
            'wizard_name': wizard_name,
            'run_id': run_id,
            'status': run.status,
            'result_summary': result_summary,
        }


# ===================================================================
# Tool: complete_onboarding
# ===================================================================

@mcp.tool
def complete_onboarding(customer_id: int, check_only: bool = False) -> dict:
    """Finalize onboarding for a customer.

    Performs final checks and marks the customer as onboarded:
    1. Verifies all required steps are done (customer, accounts, KPIs, scores)
    2. Sets the customer status to active
    3. Returns a final summary with next steps

    When check_only=True, returns a detailed onboarding status checklist
    (customer record, admin user, config, accounts, KPI data, scores,
    wizard runs, data files) without finalizing. Use this to monitor
    onboarding progress before completing.

    Minimum requirements (Month 1 — 3 CSVs):
    ✅ Customer record created
    ✅ Admin user exists
    ✅ CustomerConfig exists
    ✅ Accounts uploaded (≥1)
    ✅ KPI data loaded (≥1)
    ✅ Health scores calculated (≥1)
    ✅ Qualitative signals loaded (≥1)
    ℹ️ Context graph (auto-generated by Wizard A from 3 CSVs)
    ℹ️ Engagement events (optional, Month 2+)
    ℹ️ Outcomes (optional, Month 2+)

    Args:
        customer_id: The customer ID
        check_only: If True, return onboarding status checklist without finalizing.
    """
    _require_auth_if_key_present('complete_onboarding', customer_id)
    _check_mcp_enabled()
    app = _get_flask_app()

    with app.app_context():
        from models import Customer, CustomerConfig, Account, User, DC2SKPI, WizardRun
        from extensions import db
        from pathlib import Path

        if check_only:
            checklist = {
                'customer_exists': False,
                'admin_user_exists': False,
                'config_exists': False,
                'accounts_uploaded': False,
                'account_count': 0,
                'kpi_data_loaded': False,
                'kpi_record_count': 0,
                'signals_loaded': False,
                'signal_count': 0,
                'scores_calculated': False,
                'context_graph_nodes': 0,
                'context_graph_edges': 0,
                'wizard_runs': 0,
                'directory_provisioned': False,
                'data_files_present': [],
                'month2_optional': {
                    'engagement_events': False,
                    'outcomes': False,
                    'industry_benchmarks': False,
                },
            }

            customer = db.session.get(Customer, int(customer_id))
            if not customer:
                return {
                    'scope': 'customer',
                    'customer_id': customer_id,
                    'check_only': True,
                    'status': 'not_found',
                    'checklist': checklist,
                    'message': f'Customer {customer_id} does not exist yet. Use create_customer() to begin.',
                }
            checklist['customer_exists'] = True

            admin = User.query.filter_by(customer_id=customer_id).first()
            checklist['admin_user_exists'] = admin is not None

            config = CustomerConfig.query.filter_by(customer_id=customer_id).first()
            checklist['config_exists'] = config is not None

            accounts = Account.query.filter_by(customer_id=customer_id).all()
            checklist['accounts_uploaded'] = len(accounts) > 0
            checklist['account_count'] = len(accounts)

            if accounts:
                account_ids = [a.account_id for a in accounts]
                kpi_count = DC2SKPI.query.filter(
                    DC2SKPI.account_id.in_(account_ids)
                ).count()
                checklist['kpi_data_loaded'] = kpi_count > 0
                checklist['kpi_record_count'] = kpi_count

            if accounts:
                account_ids = [a.account_id for a in accounts]

                # Signals check
                from models import QualitativeSignal
                sig_count = QualitativeSignal.query.filter(
                    QualitativeSignal.customer_id == int(customer_id)
                ).count()
                checklist['signals_loaded'] = sig_count > 0
                checklist['signal_count'] = sig_count

                # Health scores check
                cust_vertical = getattr(customer, 'vertical', 'dc2_s') or 'dc2_s'
                _, _, get_precalculated_scores_fn = _get_health_functions(cust_vertical)
                scored = 0
                for acct in accounts:
                    h, _, _ = get_precalculated_scores_fn(acct.account_id)
                    if h is not None:
                        scored += 1
                checklist['scores_calculated'] = scored > 0

                # Context graph check (auto-generated by Wizard A)
                from models import ContextNode, ContextEdge
                cg_nodes = ContextNode.query.filter(
                    ContextNode.customer_id == int(customer_id)
                ).count()
                cg_edges = ContextEdge.query.filter(
                    ContextEdge.customer_id == int(customer_id)
                ).count()
                checklist['context_graph_nodes'] = cg_nodes
                checklist['context_graph_edges'] = cg_edges

                # Month 2+ optional data
                data_dir = Path(__file__).parent.parent / 'verticals' / f'customer{customer_id}-{getattr(customer, "vertical", "dc2_s") or "dc2_s"}' / 'data'
                if data_dir.exists():
                    files = [f.name for f in data_dir.iterdir() if f.is_file() and f.suffix == '.csv']
                    checklist['month2_optional']['engagement_events'] = any('engagement' in f for f in files)
                    checklist['month2_optional']['outcomes'] = any('outcome' in f for f in files)
                    checklist['month2_optional']['industry_benchmarks'] = any('benchmark' in f for f in files)

            wizard_count = WizardRun.query.filter_by(customer_id=customer_id).count()
            checklist['wizard_runs'] = wizard_count

            backend_dir = Path(__file__).parent.parent
            cust_v = getattr(customer, 'vertical', 'dc2_s') or 'dc2_s'
            customer_dir = backend_dir / 'verticals' / f'customer{customer_id}-{cust_v}'
            checklist['directory_provisioned'] = customer_dir.exists()
            if customer_dir.exists():
                data_dir = customer_dir / 'data'
                if data_dir.exists():
                    checklist['data_files_present'] = [
                        f.name for f in data_dir.iterdir() if f.is_file() and f.suffix == '.csv'
                    ]

            all_done = all([
                checklist['customer_exists'],
                checklist['admin_user_exists'],
                checklist['config_exists'],
                checklist['accounts_uploaded'],
                checklist['kpi_data_loaded'],
                checklist['signals_loaded'],
                checklist['scores_calculated'],
            ])
            status = 'complete' if all_done else 'in_progress'

            return {
                'scope': 'customer',
                'customer_id': customer_id,
                'customer_name': customer.customer_name,
                'created_at': customer.created_at.isoformat() if customer.created_at else None,
                'check_only': True,
                'status': status,
                'checklist': checklist,
            }

        # --- Normal finalization mode ---
        customer = db.session.get(Customer, int(customer_id))
        if not customer:
            raise ToolError(f"Customer {customer_id} not found.")

        issues = []

        admin = User.query.filter_by(customer_id=customer_id).first()
        if not admin:
            issues.append('No admin user found. Use create_customer() to create one.')

        config = CustomerConfig.query.filter_by(customer_id=customer_id).first()
        if not config:
            issues.append('No customer config found. Use configure_customer_kpis() to set one up.')

        accounts = Account.query.filter_by(customer_id=customer_id).all()
        if not accounts:
            issues.append('No accounts found. Upload accounts.csv via upload_csv() and process_data().')

        kpi_count = 0
        if accounts:
            account_ids = [a.account_id for a in accounts]
            kpi_count = DC2SKPI.query.filter(
                DC2SKPI.account_id.in_(account_ids)
            ).count()
            if kpi_count == 0:
                issues.append('No KPI data loaded. Upload kpi_measurements.csv via upload_csv() and process_data().')

        if issues:
            return {
                'scope': 'customer',
                'customer_id': customer_id,
                'customer_name': customer.customer_name,
                'status': 'incomplete',
                'issues': issues,
                'message': 'Onboarding cannot be finalized. Resolve the issues above.',
            }

        cust_vertical = getattr(customer, 'vertical', 'dc2_s') or 'dc2_s'
        calculate_kpi_health, _get_trailing_kpi_values, get_precalculated_scores = _get_health_functions(cust_vertical)
        import utils.health_thresholds as ht

        health_scores = []
        total_arr = 0.0
        for acct in accounts:
            precalc_health, _, _ = get_precalculated_scores(acct.account_id)
            if precalc_health is not None:
                health_scores.append(precalc_health)
            else:
                try:
                    kpi_values = _get_trailing_kpi_values(acct.account_id)
                    h, _ = calculate_kpi_health(kpi_values, customer_id)
                    health_scores.append(h)
                except Exception:
                    pass
            total_arr += _get_account_arr(acct)

        avg_health = round(sum(health_scores) / len(health_scores), 1) if health_scores else 0

        return {
            'scope': 'customer',
            'customer_id': customer_id,
            'customer_name': customer.customer_name,
            'customer_uuid': getattr(customer, 'uuid', None),
            'vertical': getattr(customer, 'vertical', None) or 'dc2_s',
            'status': 'onboarded',
            'summary': {
                'account_count': len(accounts),
                'kpi_records': kpi_count,
                'avg_health_score': avg_health,
                'total_arr': round(total_arr, 2),
                'enabled_kpis': config.dc2s_enabled_kpis if config else None,
            },
            'next_steps': [
                'Use list_accounts() to view all accounts and health scores.',
                'Use get_account_health() to drill into individual accounts.',
                'Use get_at_risk_accounts() to find accounts needing attention.',
                'Use get_csm_actions() for AI-recommended next-best actions.',
                'Use the Context Graph tools for revenue intelligence (if enabled).',
            ],
            'message': f'Onboarding complete. {len(accounts)} accounts, avg health {avg_health}.',
        }


# ===================================================================
# Tool: clone_customer
# ===================================================================

@mcp.tool
def clone_customer(
    source_customer_id: int,
    new_name: str,
    new_domain: str,
) -> dict:
    """Deep-copy an existing customer with all data into a new customer.

    Creates a full clone including accounts, KPI measurements, health scores,
    context graph (nodes + edges with remapped IDs), qualitative signals,
    playbook executions, and ROI snapshots. Enables instant demo setup:
    "clone Gold_DC_Alpha as Acme Corp" in ~2 seconds.

    Requires authentication — this is a data export operation, not discovery.

    Args:
        source_customer_id: Customer ID to clone from (e.g. 407 for Gold_DC_Alpha)
        new_name: Name for the new customer (e.g. 'Acme Corp')
        new_domain: Domain for the new customer (e.g. 'acme.com')
    """
    _check_mcp_enabled()
    _require_auth(source_customer_id, required_scope='read')
    app = _get_flask_app()

    with app.app_context():
        from models import (
            Customer, CustomerConfig, Account, DC2SKPI,
            HealthScore, KPIScore, PillarScore,
            ContextNode, ContextEdge,
            QualitativeSignal, PlaybookExecution,
            ROISnapshot, JourneyData,
            FeatureToggle, WeightCalibrationHistory,
        )
        from extensions import db
        import uuid as _uuid_mod
        from datetime import datetime

        source = db.session.get(Customer, int(source_customer_id))
        if not source:
            raise ToolError(f"Source customer {source_customer_id} not found.")

        existing = Customer.query.filter_by(domain=new_domain).first()
        if existing:
            raise ToolError(
                f"A customer with domain '{new_domain}' already exists "
                f"(customer_id={existing.customer_id})."
            )

        summary = {}

        # 1. Clone Customer record
        new_customer = Customer(
            customer_name=new_name,
            email=None,
            domain=new_domain,
            vertical=source.vertical,
        )
        try:
            from id_generator import generate_id
            uuid_vertical = 'dc' if (source.vertical or '').startswith('dc') else (source.vertical or 'dc')
            new_customer.uuid = generate_id(uuid_vertical, 'customer')
        except Exception:
            new_customer.uuid = f"clone_{_uuid_mod.uuid4().hex[:16]}"
        db.session.add(new_customer)
        db.session.flush()

        new_cid = new_customer.customer_id
        summary['customer_id'] = new_cid
        summary['customer_name'] = new_name
        summary['domain'] = new_domain
        summary['vertical'] = source.vertical
        summary['created_at'] = new_customer.created_at.isoformat() if new_customer.created_at else None

        # 2. Clone CustomerConfig
        source_config = CustomerConfig.query.filter_by(customer_id=source_customer_id).first()
        if source_config:
            new_config = CustomerConfig(
                customer_id=new_cid,
                vertical=source_config.vertical,
                kpi_upload_mode=source_config.kpi_upload_mode,
                dc2s_pillar_weights=source_config.dc2s_pillar_weights,
                dc2s_enabled_kpis=source_config.dc2s_enabled_kpis,
                dc2s_kpi_overrides=source_config.dc2s_kpi_overrides,
                dc2s_kpi_weights=source_config.dc2s_kpi_weights,
                dc2s_kpi_definitions=source_config.dc2s_kpi_definitions,
                config_version=source_config.config_version,
            )
            db.session.add(new_config)
            summary['config_cloned'] = True
        else:
            summary['config_cloned'] = False

        # 3. Clone Accounts
        source_accounts = Account.query.filter_by(customer_id=source_customer_id).all()
        acct_id_map = {}
        for acct in source_accounts:
            new_acct = Account(
                customer_id=new_cid,
                account_name=acct.account_name,
                revenue=acct.revenue,
                account_status=acct.account_status,
                industry=acct.industry,
                vertical=acct.vertical,
                region=acct.region,
                external_account_id=acct.external_account_id,
                profile_metadata=acct.profile_metadata,
                arc_type=acct.arc_type,
                arc_phase=acct.arc_phase,
                arc_confidence=acct.arc_confidence,
            )
            try:
                new_acct.uuid = generate_id(uuid_vertical, 'account')
            except Exception:
                new_acct.uuid = f"clone_acct_{_uuid_mod.uuid4().hex[:12]}"
            new_acct.customer_uuid = new_customer.uuid
            db.session.add(new_acct)
            db.session.flush()
            acct_id_map[acct.account_id] = new_acct.account_id
        summary['accounts_cloned'] = len(acct_id_map)

        # 4. Clone DC2S KPI measurements
        kpi_count = 0
        for old_aid, new_aid in acct_id_map.items():
            kpis = DC2SKPI.query.filter_by(account_id=old_aid).all()
            for kpi in kpis:
                new_kpi = DC2SKPI(
                    account_id=new_aid, kpi_code=kpi.kpi_code, value=kpi.value,
                    target=kpi.target, pillar=kpi.pillar, weight=kpi.weight,
                    status=kpi.status, measured_at=kpi.measured_at, created_at=kpi.created_at,
                )
                db.session.add(new_kpi)
                kpi_count += 1
        summary['kpis_cloned'] = kpi_count

        # 5. Clone Health Scores
        hs_count = 0
        for old_aid, new_aid in acct_id_map.items():
            scores = HealthScore.query.filter_by(account_id=old_aid).all()
            for s in scores:
                new_hs = HealthScore(
                    account_id=new_aid, measurement_month=s.measurement_month,
                    health_score=s.health_score, health_status=s.health_status,
                    trend=s.trend, change_from_last_month=s.change_from_last_month,
                    contributing_pillars=s.contributing_pillars, pillar_weights=s.pillar_weights,
                    calculated_at=s.calculated_at,
                )
                db.session.add(new_hs)
                hs_count += 1
        summary['health_scores_cloned'] = hs_count

        # 5b. Clone KPI Scores + Pillar Scores
        kpi_score_count = 0
        for old_aid, new_aid in acct_id_map.items():
            rows = KPIScore.query.filter_by(account_id=old_aid).all()
            for r in rows:
                new_row = KPIScore(
                    account_id=new_aid, measurement_month=r.measurement_month,
                    kpi_code=r.kpi_code, kpi_value=r.kpi_value, kpi_target=r.kpi_target,
                    kpi_score=r.kpi_score, kpi_status=r.kpi_status, calculated_at=r.calculated_at,
                )
                db.session.add(new_row)
                kpi_score_count += 1
        summary['kpi_scores_cloned'] = kpi_score_count

        pillar_score_count = 0
        for old_aid, new_aid in acct_id_map.items():
            rows = PillarScore.query.filter_by(account_id=old_aid).all()
            for r in rows:
                new_row = PillarScore(
                    account_id=new_aid, measurement_month=r.measurement_month,
                    pillar_code=r.pillar_code, pillar_score=r.pillar_score,
                    pillar_status=r.pillar_status, contributing_kpis=r.contributing_kpis,
                    kpi_weights=r.kpi_weights, calculated_at=r.calculated_at,
                )
                db.session.add(new_row)
                pillar_score_count += 1
        summary['pillar_scores_cloned'] = pillar_score_count

        # 6. Clone Context Graph Nodes
        source_nodes = ContextNode.query.filter_by(customer_id=source_customer_id).all()
        node_id_map = {}
        for node in source_nodes:
            new_account_id = acct_id_map.get(node.account_id)
            if new_account_id is None:
                continue
            new_node = ContextNode(
                customer_id=new_cid, account_id=new_account_id,
                node_type=node.node_type, node_subtype=node.node_subtype, tier=node.tier,
                source=node.source,
                title=node.title, properties=node.properties,
                revenue_impact=node.revenue_impact, revenue_impact_type=node.revenue_impact_type,
                confidence=node.confidence, source_platform=node.source_platform,
                source_event_id=node.source_event_id, source_ref=node.source_ref,
                occurred_at=node.occurred_at, expires_at=node.expires_at, weight_decay=node.weight_decay,
            )
            db.session.add(new_node)
            db.session.flush()
            node_id_map[node.node_id] = new_node.node_id
        summary['context_nodes_cloned'] = len(node_id_map)

        # 7. Clone Context Graph Edges
        edge_count = 0
        source_edges = ContextEdge.query.filter_by(customer_id=source_customer_id).all()
        for edge in source_edges:
            new_from = node_id_map.get(edge.from_node_id)
            new_to = node_id_map.get(edge.to_node_id)
            if new_from is None or new_to is None:
                continue
            new_edge = ContextEdge(
                customer_id=new_cid, from_node_id=new_from, to_node_id=new_to,
                edge_type=edge.edge_type, lag_days=edge.lag_days, weight=edge.weight,
                confidence=edge.confidence, revenue_impact=edge.revenue_impact,
                revenue_impact_type=edge.revenue_impact_type, properties=edge.properties,
                source_platform=edge.source_platform, created_by=edge.created_by,
                occurred_at=edge.occurred_at, expires_at=edge.expires_at,
            )
            db.session.add(new_edge)
            edge_count += 1
        summary['context_edges_cloned'] = edge_count

        # 8. Clone Qualitative Signals
        signal_count = 0
        for old_aid, new_aid in acct_id_map.items():
            signals = QualitativeSignal.query.filter_by(account_id=old_aid).all()
            for sig in signals:
                new_sig = QualitativeSignal(
                    signal_id=f"clone_{_uuid_mod.uuid4().hex[:8]}_{sig.signal_id[-8:] if len(sig.signal_id) > 8 else sig.signal_id}",
                    customer_id=new_cid,
                    account_id=new_aid, signal_date=sig.signal_date, signal_type=sig.signal_type,
                    content=sig.content, sentiment=sig.sentiment,
                    stakeholder_level=sig.stakeholder_level, stakeholder_title=sig.stakeholder_title,
                    sentiment_score=sig.sentiment_score, keywords=sig.keywords,
                    is_narrative_signal=sig.is_narrative_signal,
                )
                db.session.add(new_sig)
                signal_count += 1
        summary['qualitative_signals_cloned'] = signal_count

        # 9. Clone Playbook Executions
        pb_count = 0
        source_pbs = PlaybookExecution.query.filter_by(customer_id=source_customer_id).all()
        for pb in source_pbs:
            new_account_id = acct_id_map.get(pb.account_id) if pb.account_id else None
            new_pb = PlaybookExecution(
                execution_id=str(_uuid_mod.uuid4()), customer_id=new_cid,
                account_id=new_account_id, playbook_id=pb.playbook_id,
                status=pb.status, current_step=pb.current_step,
                execution_data=pb.execution_data, started_at=pb.started_at,
                completed_at=pb.completed_at, execution_mode=pb.execution_mode,
                trigger_context=pb.trigger_context, outcome=pb.outcome,
                outcome_notes=pb.outcome_notes, llm_validation_result=pb.llm_validation_result,
            )
            db.session.add(new_pb)
            pb_count += 1
        summary['playbook_executions_cloned'] = pb_count

        # 10. Clone ROI Snapshots
        roi_count = 0
        source_rois = ROISnapshot.query.filter_by(customer_id=source_customer_id).all()
        for roi in source_rois:
            new_roi = ROISnapshot(
                customer_id=new_cid, snapshot_date=roi.snapshot_date,
                improvement_pct=roi.improvement_pct, historical_roi_pct=roi.historical_roi_pct,
                historical_impact=roi.historical_impact, historical_investment=roi.historical_investment,
                forward_roi_pct=roi.forward_roi_pct, forward_impact=roi.forward_impact,
                forward_investment=roi.forward_investment, combined_roi_pct=roi.combined_roi_pct,
                total_arr=roi.total_arr, metric_details=roi.metric_details,
            )
            db.session.add(new_roi)
            roi_count += 1
        summary['roi_snapshots_cloned'] = roi_count

        # 11. Clone Journey Data
        journey_count = 0
        for old_aid, new_aid in acct_id_map.items():
            journeys = JourneyData.query.filter_by(
                customer_id=source_customer_id, account_id=old_aid,
            ).all()
            for j in journeys:
                new_j = JourneyData(
                    customer_id=new_cid, account_id=new_aid,
                    journey_json=j.journey_json, total_weeks=j.total_weeks,
                    journey_pattern=j.journey_pattern, generator_version=j.generator_version,
                    generated_at=j.generated_at,
                )
                db.session.add(new_j)
                journey_count += 1
        summary['journey_data_cloned'] = journey_count

        # 11b. Clone Feature Toggles
        ft_count = 0
        source_toggles = FeatureToggle.query.filter_by(customer_id=source_customer_id).all()
        for ft in source_toggles:
            new_ft = FeatureToggle(
                customer_id=new_cid, feature_name=ft.feature_name,
                enabled=ft.enabled, config=ft.config, description=ft.description,
            )
            db.session.add(new_ft)
            ft_count += 1
        summary['feature_toggles_cloned'] = ft_count

        # 11c. Clone Weight Calibration History
        wch_count = 0
        source_wchs = WeightCalibrationHistory.query.filter_by(customer_id=source_customer_id).all()
        for wch in source_wchs:
            new_wch = WeightCalibrationHistory(
                customer_id=new_cid, calibration_type=wch.calibration_type,
                vertical=wch.vertical, previous_weights=wch.previous_weights,
                new_weights=wch.new_weights, weight_deltas=wch.weight_deltas,
                pillar_weights=wch.pillar_weights, kpi_weights=wch.kpi_weights,
                previous_pillar_weights=wch.previous_pillar_weights,
                previous_kpi_weights=wch.previous_kpi_weights,
                sample_size=wch.sample_size,
                prediction_error_before=wch.prediction_error_before,
                prediction_error_after=wch.prediction_error_after,
                error_reduction_pct=wch.error_reduction_pct,
                triggered_by=wch.triggered_by, source=wch.source,
                approved=wch.approved, notes=wch.notes,
                successful_accounts=wch.successful_accounts,
                unsuccessful_accounts=wch.unsuccessful_accounts,
                correlation_scores=wch.correlation_scores,
                health_accuracy=wch.health_accuracy,
                significant_changes=wch.significant_changes,
                is_cdi_eligible=wch.is_cdi_eligible,
                calibrated_at=wch.calibrated_at,
            )
            db.session.add(new_wch)
            wch_count += 1
        summary['weight_calibration_history_cloned'] = wch_count

        # 12. Create admin user
        admin_user = None
        try:
            from models import User
            from werkzeug.security import generate_password_hash
            import secrets as _secrets
            admin_email = f"admin@{new_domain}"
            admin_password = _secrets.token_urlsafe(16)
            new_user = User(
                email=admin_email, user_name=f"Admin ({new_name})",
                customer_id=new_cid, role='admin',
                password_hash=generate_password_hash(admin_password),
                vertical=source.vertical,
            )
            new_user.customer_uuid = new_customer.uuid
            try:
                new_user.uuid = generate_id(uuid_vertical, 'user')
            except Exception:
                new_user.uuid = f"clone_user_{_uuid_mod.uuid4().hex[:12]}"
            db.session.add(new_user)
            db.session.flush()
            admin_user = {
                'user_id': new_user.user_id, 'email': admin_email,
                'password': admin_password, 'role': 'admin',
            }
            summary['admin_user_created'] = True
        except Exception as e:
            summary['admin_user_created'] = False
            summary['admin_user_error'] = str(e)

        # 13. Generate API key
        api_key = None
        try:
            from api_key_service import generate_api_key as _gen_api_key
            full_key, _key_record = _gen_api_key(
                customer_id=new_cid, created_by=0,
                name='Clone Onboarding Key', scopes=['read', 'write'],
            )
            api_key = full_key
        except Exception:
            api_key = None

        db.session.commit()

        total_records = (
            summary.get('accounts_cloned', 0) + summary.get('kpis_cloned', 0)
            + summary.get('health_scores_cloned', 0) + summary.get('kpi_scores_cloned', 0)
            + summary.get('pillar_scores_cloned', 0) + summary.get('context_nodes_cloned', 0)
            + summary.get('context_edges_cloned', 0) + summary.get('qualitative_signals_cloned', 0)
            + summary.get('playbook_executions_cloned', 0) + summary.get('roi_snapshots_cloned', 0)
            + summary.get('journey_data_cloned', 0) + summary.get('feature_toggles_cloned', 0)
            + summary.get('weight_calibration_history_cloned', 0)
        )

        result = {
            'scope': 'customer', 'status': 'cloned',
            'source_customer_id': source_customer_id,
            'new_customer_id': new_cid, 'new_customer_name': new_name,
            'new_domain': new_domain, 'vertical': source.vertical,
            'total_records_cloned': total_records, 'details': summary,
            'message': (
                f"Successfully cloned customer {source_customer_id} "
                f"as '{new_name}' (ID={new_cid}). "
                f"{summary.get('accounts_cloned', 0)} accounts, "
                f"{summary.get('context_nodes_cloned', 0)} context nodes, "
                f"{total_records} total records."
            ),
        }

        if api_key:
            result['api_key'] = api_key
            result['api_key_note'] = 'Save this API key — it is shown only once.'

        if admin_user:
            result['admin_user'] = admin_user
            result['admin_user_note'] = 'Admin user auto-created. Use these credentials to log in.'

        result['next_steps'] = (
            'OPTION 1 — Use as-is: Clone is ready immediately. '
            'All data has been deep-copied with pre-calculated scores, '
            'feature toggles, and weight calibration history. '
            'OPTION 2 — Customize: Use download_customer_csv() to get '
            'CSVs, modify them, then upload_csv() + process_data() to recalculate. '
            'Month 1 requires 4 CSVs: accounts, kpi_measurements, signals, outcomes.'
        )

        # Apr 28 2026: was hardcoded to _get_dc2s_pillar_labels() — caused
        # saas_premium clones (e.g. 331→388 vinayak321) to return the
        # ImportError fallback DC2_S labels in the response message.
        # Cust data was always correct; only this display string was wrong.
        # Now uses the vertical-aware helper with the new customer's actual
        # vertical, so saas_premium clones return SaaS pillar names.
        new_vertical = _resolve_customer_vertical(new_cid) or 'dc2_s'
        result['pillar_labels'] = _get_pillar_labels(new_vertical)

        return result


def _build_kpi_catalog_lookup(customer) -> dict:
    """Map kpi_code → display fields for CSV export (DB stores code only)."""
    try:
        vertical = _resolve_customer_vertical(customer.customer_id)
    except Exception:
        vertical = getattr(customer, 'vertical', 'dc2_s') or 'dc2_s'
    defs = _get_kpi_definitions(vertical) or {}
    lookup = {}
    for code, defn in defs.items():
        lookup[code] = {
            'kpi_name': defn.get('name') or defn.get('kpi_name') or code,
            'unit': defn.get('unit', ''),
            'pillar': defn.get('pillar', ''),
        }
    return lookup


def _build_signal_export_indexes(customer_id: int, account_ids: list):
    """Index context nodes + edges for enriching qualitative signal exports."""
    from models import ContextNode, ContextEdge

    if not account_ids:
        return {}, {}, {}

    nodes = ContextNode.query.filter(
        ContextNode.customer_id == customer_id,
        ContextNode.account_id.in_(account_ids),
    ).all()
    node_by_id = {n.node_id: n for n in nodes}

    sig_ref_to_node = {}
    for n in nodes:
        if n.node_type != 'SIGNAL':
            continue
        keys = []
        if n.source_event_id:
            keys.append((n.account_id, str(n.source_event_id)))
        props = n.properties if isinstance(n.properties, dict) else {}
        sr = props.get('signal_ref')
        if sr:
            keys.append((n.account_id, str(sr)))
        for key in keys:
            sig_ref_to_node.setdefault(key, n)

    edges = ContextEdge.query.filter_by(customer_id=customer_id).all()
    outgoing = {}
    for e in edges:
        outgoing.setdefault(e.from_node_id, []).append(e)

    return sig_ref_to_node, node_by_id, outgoing


def _signal_id_lookup_keys(customer_id: int, account_id: int, signal_id: str):
    """Match QualitativeSignal.signal_id to ContextNode source_event_id / signal_ref."""
    sid = str(signal_id or '')
    keys = [(account_id, sid)]
    prefix = f'c{customer_id}_'
    if sid.startswith(prefix):
        keys.append((account_id, sid[len(prefix):]))
    return keys


def _stakeholder_name_from_signal(signal) -> str:
    roles = getattr(signal, 'stakeholder_roles', None)
    if isinstance(roles, list):
        for entry in roles:
            if isinstance(entry, dict):
                name = entry.get('name') or entry.get('stakeholder_name')
                if name:
                    return str(name)
            elif entry:
                return str(entry)
    return ''


def _confidence_export_value(raw) -> str:
    if raw is None or raw == '':
        return ''
    if isinstance(raw, (int, float)):
        return str(float(raw))
    if isinstance(raw, dict):
        for key in ('overall', 'score', 'point'):
            if key in raw and raw[key] is not None:
                try:
                    return str(float(raw[key]))
                except (TypeError, ValueError):
                    pass
        nums = []
        for v in raw.values():
            try:
                nums.append(float(v))
            except (TypeError, ValueError):
                continue
        if nums:
            return str(max(nums))
        return ''
    try:
        return str(float(raw))
    except (TypeError, ValueError):
        return str(raw)


def _node_export_ref(node) -> str:
    if not node:
        return ''
    props = node.properties if isinstance(node.properties, dict) else {}
    return (
        str(node.source_event_id or props.get('signal_ref') or node.source_ref or '')
    )


def _enrich_signal_export_row(signal, customer_id: int, sig_ref_to_node, node_by_id, outgoing):
    """Fill stakeholder / causal / platform fields absent from QualitativeSignal rows."""
    node = None
    if getattr(signal, 'cg_node_id', None):
        node = node_by_id.get(signal.cg_node_id)
    if not node:
        for key in _signal_id_lookup_keys(customer_id, signal.account_id, signal.signal_id):
            node = sig_ref_to_node.get(key)
            if node:
                break

    stakeholder_name = _stakeholder_name_from_signal(signal)
    source_platform = getattr(signal, 'source_type', None) or ''
    causal_chain_ref = ''
    revenue_impact = ''
    confidence = _confidence_export_value(getattr(signal, 'confidence', None))

    if node:
        props = node.properties if isinstance(node.properties, dict) else {}
        if not stakeholder_name:
            stakeholder_name = str(props.get('stakeholder_name') or '')
        if not source_platform:
            source_platform = node.source_platform or 'csv_import'
        if node.confidence is not None and not confidence:
            confidence = str(float(node.confidence))
        if node.revenue_impact is not None:
            revenue_impact = float(node.revenue_impact)

        out_edges = outgoing.get(node.node_id, [])
        if out_edges:
            refs = []
            rev_total = 0.0
            rev_seen = False
            for edge in sorted(out_edges, key=lambda e: e.edge_id):
                if edge.confidence is not None and not confidence:
                    confidence = str(float(edge.confidence))
                if edge.revenue_impact is not None:
                    rev_total += float(edge.revenue_impact)
                    rev_seen = True
                target_ref = _node_export_ref(node_by_id.get(edge.to_node_id))
                if target_ref:
                    refs.append(target_ref)
            if refs:
                causal_chain_ref = ';'.join(refs[:5])
            if rev_seen and not revenue_impact:
                revenue_impact = rev_total

    if not source_platform:
        source_platform = 'cs_pulse'

    return {
        'stakeholder_name': stakeholder_name,
        'causal_chain_ref': causal_chain_ref,
        'revenue_impact': revenue_impact if revenue_impact != '' else '',
        'confidence': confidence,
        'source_platform': source_platform,
    }


# ===================================================================
# Tool: download_customer_csv
# ===================================================================

@mcp.tool
def download_customer_csv(
    customer_id: int,
    file_type: str = 'all',
) -> dict:
    """Download customer data as CSV content returned inline in the response.

    Unlike export_customer_csvs() which writes to the server filesystem,
    this tool returns CSV content directly in the response — making it
    accessible to Claude.ai and other MCP clients that cannot access
    the server's filesystem.

    Requires authentication — this is a data export operation.

    Args:
        customer_id: Customer ID to download data from
        file_type: Which CSV to download. Options:
            'all' — returns all 8 CSVs (may be large)
            'accounts' — accounts.csv
            'kpi_measurements' — kpi_measurements.csv
            'signals' — enhanced_qualitative_signals.csv
            'products' — products.csv
            'stakeholders' — stakeholders.csv
            'engagement_events' — engagement_events.csv
            'profiles' — account_business_profiles.csv
            'outcomes' — outcomes.csv
    """
    _check_mcp_enabled()
    _require_auth(customer_id, required_scope='read')
    app = _get_flask_app()

    with app.app_context():
        import csv
        import io
        from models import (
            Customer, Account, DC2SKPI, Product,
            QualitativeSignal, ContextNode,
        )
        from extensions import db

        customer = db.session.get(Customer, int(customer_id))
        if not customer:
            raise ToolError(f"Customer {customer_id} not found.")

        accounts = Account.query.filter_by(customer_id=int(customer_id)).all()
        account_ids = [a.account_id for a in accounts]

        def _csv_string(columns: list, rows: list) -> str:
            buf = io.StringIO()
            writer = csv.DictWriter(buf, fieldnames=columns, extrasaction='ignore')
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
            return buf.getvalue()

        valid_types = [
            'accounts', 'kpi_measurements', 'signals', 'products',
            'stakeholders', 'engagement_events', 'profiles', 'outcomes',
        ]

        if file_type != 'all' and file_type not in valid_types:
            raise ToolError(
                f"Invalid file_type '{file_type}'. "
                f"Valid options: 'all', {', '.join(valid_types)}"
            )

        requested = valid_types if file_type == 'all' else [file_type]
        csvs = {}

        kpi_catalog = _build_kpi_catalog_lookup(customer)
        need_signal_indexes = 'signals' in requested
        sig_ref_to_node, node_by_id, outgoing_edges = (
            _build_signal_export_indexes(int(customer_id), account_ids)
            if need_signal_indexes else ({}, {}, {})
        )

        if 'accounts' in requested:
            cols = ['account_id', 'customer_id', 'account_name', 'industry', 'region',
                    'vertical', 'tier', 'arr', 'revenue', 'contract_start', 'contract_end',
                    'renewal_date', 'csm_name', 'csm_email', 'account_status', 'uuid']
            rows = []
            for a in accounts:
                pm = a.profile_metadata or {}
                rows.append({
                    'account_id': a.account_id, 'customer_id': a.customer_id,
                    'account_name': a.account_name, 'industry': a.industry, 'region': a.region,
                    'vertical': a.vertical, 'tier': pm.get('tier', ''),
                    'arr': pm.get('arr', '') or (float(a.revenue) if a.revenue else ''),
                    'revenue': float(a.revenue) if a.revenue else '',
                    'contract_start': pm.get('contract_start', ''),
                    'contract_end': pm.get('contract_end', ''),
                    'renewal_date': pm.get('renewal_date', ''),
                    'csm_name': pm.get('assigned_csm', '') or pm.get('csm_name', ''),
                    'csm_email': pm.get('csm_email', ''),
                    'account_status': a.account_status, 'uuid': a.uuid or '',
                })
            csvs['accounts.csv'] = {'content': _csv_string(cols, rows), 'rows': len(rows)}

        if 'kpi_measurements' in requested:
            cols = ['account_id', 'kpi_code', 'measured_at', 'value',
                    'kpi_name', 'pillar', 'target', 'weight', 'unit', 'status']
            rows = []
            if account_ids:
                kpis = DC2SKPI.query.filter(DC2SKPI.account_id.in_(account_ids)).all()
                for k in kpis:
                    meta = kpi_catalog.get(k.kpi_code, {})
                    rows.append({
                        'account_id': k.account_id, 'kpi_code': k.kpi_code,
                        'measured_at': k.measured_at.isoformat() if k.measured_at else '',
                        'value': float(k.value),
                        'kpi_name': meta.get('kpi_name') or k.kpi_code,
                        'pillar': k.pillar or meta.get('pillar', ''),
                        'target': float(k.target) if k.target else '',
                        'weight': float(k.weight) if k.weight else '',
                        'unit': meta.get('unit', ''),
                        'status': k.status or '',
                    })
            csvs['kpi_measurements.csv'] = {'content': _csv_string(cols, rows), 'rows': len(rows)}

        if 'signals' in requested:
            cols = ['account_id', 'signal_date', 'signal_type', 'content', 'sentiment',
                    'signal_ref', 'sentiment_score', 'stakeholder_name', 'stakeholder_title',
                    'causal_chain_ref', 'revenue_impact', 'confidence', 'source_platform']
            rows = []
            if account_ids:
                signals = QualitativeSignal.query.filter(
                    QualitativeSignal.account_id.in_(account_ids)
                ).all()
                for s in signals:
                    extra = _enrich_signal_export_row(
                        s, int(customer_id), sig_ref_to_node, node_by_id, outgoing_edges,
                    )
                    rows.append({
                        'account_id': s.account_id,
                        'signal_date': s.signal_date.isoformat() if s.signal_date else '',
                        'signal_type': s.signal_type or '', 'content': s.content or '',
                        'sentiment': s.sentiment or '', 'signal_ref': s.signal_id or '',
                        'sentiment_score': float(s.sentiment_score) if s.sentiment_score else '',
                        'stakeholder_name': extra['stakeholder_name'],
                        'stakeholder_title': s.stakeholder_title or '',
                        'causal_chain_ref': extra['causal_chain_ref'],
                        'revenue_impact': extra['revenue_impact'],
                        'confidence': extra['confidence'],
                        'source_platform': extra['source_platform'],
                    })
            csvs['enhanced_qualitative_signals.csv'] = {'content': _csv_string(cols, rows), 'rows': len(rows)}

        if 'products' in requested:
            cols = ['account_id', 'product_name', 'product_category', 'quantity',
                    'unit_price', 'deployment_date', 'status', 'customer_id']
            rows = []
            if account_ids:
                products = Product.query.filter(Product.account_id.in_(account_ids)).all()
                for p in products:
                    rows.append({
                        'account_id': p.account_id, 'product_name': p.product_name,
                        'product_category': p.product_type or '', 'quantity': '',
                        'unit_price': float(p.revenue) if p.revenue else '',
                        'deployment_date': '', 'status': p.status or '',
                        'customer_id': p.customer_id,
                    })
            csvs['products.csv'] = {'content': _csv_string(cols, rows), 'rows': len(rows)}

        ctx_nodes = []
        if account_ids and any(t in requested for t in ['stakeholders', 'engagement_events', 'profiles', 'outcomes']):
            ctx_nodes = ContextNode.query.filter(
                ContextNode.account_id.in_(account_ids)
            ).all()

        nodes_by_type = {}
        for n in ctx_nodes:
            nodes_by_type.setdefault(n.node_type, []).append(n)

        if 'stakeholders' in requested:
            cols = ['account_id', 'stakeholder_name', 'title', 'role', 'influence_score',
                    'email', 'engagement_frequency', 'sentiment', 'department',
                    'is_active', 'source_platform', 'first_observed_at']
            rows = []
            for n in nodes_by_type.get('STAKEHOLDER', []):
                props = n.properties or {}
                rows.append({
                    'account_id': n.account_id,
                    'stakeholder_name': n.title or props.get('stakeholder_name', ''),
                    'title': props.get('title', ''),
                    'role': props.get('role', n.node_subtype or ''),
                    'influence_score': props.get('influence_score', ''),
                    'email': props.get('email', ''),
                    'engagement_frequency': props.get('engagement_frequency', ''),
                    'sentiment': props.get('sentiment', ''),
                    'department': props.get('department', ''),
                    'is_active': props.get('is_active', ''),
                    'source_platform': n.source_platform or '',
                    'first_observed_at': n.occurred_at.isoformat() if n.occurred_at else '',
                })
            csvs['stakeholders.csv'] = {'content': _csv_string(cols, rows), 'rows': len(rows)}

        if 'engagement_events' in requested:
            cols = ['account_id', 'event_date', 'event_type', 'description',
                    'stakeholder_name', 'sentiment_shift', 'channel',
                    'duration_minutes', 'outcome', 'source_platform']
            rows = []
            for n in nodes_by_type.get('SIGNAL', []):
                props = n.properties or {}
                rows.append({
                    'account_id': n.account_id,
                    'event_date': n.occurred_at.isoformat() if n.occurred_at else '',
                    'event_type': n.node_subtype or props.get('event_type', ''),
                    'description': n.title or '',
                    'stakeholder_name': props.get('stakeholder_name', ''),
                    'sentiment_shift': props.get('sentiment_shift', ''),
                    'channel': props.get('channel', ''),
                    'duration_minutes': props.get('duration_minutes', ''),
                    'outcome': props.get('outcome', ''),
                    'source_platform': n.source_platform or '',
                })
            csvs['engagement_events.csv'] = {'content': _csv_string(cols, rows), 'rows': len(rows)}

        if 'profiles' in requested:
            cols = ['account_id', 'arr', 'industry', 'employee_count',
                    'fiscal_year_end', 'tech_stack', 'cloud_provider',
                    'competitive_landscape', 'strategic_initiatives', 'budget_cycle',
                    'profile_date', 'assigned_csm', 'csm_manager', 'executive_sponsor',
                    'mrr', 'primary_champion_name', 'primary_champion_title',
                    'primary_champion_email', 'primary_champion_engagement_score',
                    'last_updated']
            rows = []
            account_nodes = nodes_by_type.get('ACCOUNT', [])
            if account_nodes:
                for n in account_nodes:
                    props = n.properties or {}
                    rows.append({
                        'account_id': n.account_id,
                        **{c: props.get(c, '') for c in cols if c not in ('account_id', 'profile_date', 'last_updated')},
                        'profile_date': n.occurred_at.isoformat() if n.occurred_at else '',
                        'last_updated': n.updated_at.isoformat() if n.updated_at else '',
                    })
            else:
                for a in accounts:
                    pm = a.profile_metadata or {}
                    rows.append({
                        'account_id': a.account_id,
                        **{c: pm.get(c, '') for c in cols if c not in ('account_id', 'profile_date', 'last_updated')},
                        'arr': pm.get('arr', '') or (float(a.revenue) if a.revenue else ''),
                        'industry': a.industry or '',
                        'profile_date': '',
                        'last_updated': a.updated_at.isoformat() if a.updated_at else '',
                    })
            csvs['account_business_profiles.csv'] = {'content': _csv_string(cols, rows), 'rows': len(rows)}

        if 'outcomes' in requested:
            cols = ['account_id', 'outcome_date', 'title', 'outcome_type', 'revenue_value',
                    'outcome_id', 'evidence', 'confidence', 'related_decision_id', 'source_platform']
            rows = []
            for n in nodes_by_type.get('OUTCOME', []):
                props = n.properties or {}
                rows.append({
                    'account_id': n.account_id,
                    'outcome_date': n.occurred_at.isoformat() if n.occurred_at else '',
                    'title': n.title or '',
                    'outcome_type': n.node_subtype or props.get('outcome_type', ''),
                    'revenue_value': float(n.revenue_impact) if n.revenue_impact else '',
                    'outcome_id': n.source_ref or n.source_event_id or '',
                    'evidence': props.get('evidence', ''),
                    'confidence': float(n.confidence) if n.confidence else '',
                    'related_decision_id': props.get('related_decision_id', ''),
                    'source_platform': n.source_platform or '',
                })
            csvs['outcomes.csv'] = {'content': _csv_string(cols, rows), 'rows': len(rows)}

        total_rows = sum(f['rows'] for f in csvs.values())
        files_summary = [{'file': name, 'rows': info['rows']} for name, info in csvs.items()]

        result = {
            'scope': 'customer', 'customer_id': customer_id,
            'customer_name': customer.customer_name, 'file_type': file_type,
            'total_files': len(csvs), 'total_rows': total_rows, 'files': files_summary,
            'message': (
                f"Downloaded {total_rows} rows across {len(csvs)} CSV(s) for "
                f"{customer.customer_name}. CSV content is in the 'csv_data' field."
            ),
            'csv_data': {name: info['content'] for name, info in csvs.items()},
        }

        if file_type != 'all' and len(csvs) == 1:
            fname = list(csvs.keys())[0]
            result['filename'] = fname
            result['csv_content'] = csvs[fname]['content']

        return result
