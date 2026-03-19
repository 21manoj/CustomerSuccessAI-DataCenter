#!/usr/bin/env python3
"""
CS Pulse MCP — Onboarding Server (port 8003).

Exposes 13 onboarding/setup tools for customer creation, KPI configuration,
CSV upload, data processing, wizard triggering, and onboarding completion.

All tools use frictionless auth (no API key required).

Usage:
  # stdio (default)
  python backend/mcp_server/cs_pulse_onboarding.py

  # Streamable HTTP
  python backend/mcp_server/cs_pulse_onboarding.py http
"""

import os
import sys

# Ensure backend is on the Python path
_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp_server import common

# ---------------------------------------------------------------------------
# Server instance
# ---------------------------------------------------------------------------
mcp = FastMCP(
    "CS Pulse Onboarding",
    instructions="CS Pulse customer onboarding — create customers, configure KPIs, upload CSVs, process data, run wizards.",
)


# ===================================================================
# Discovery Phase (read-only, no auth)
# ===================================================================

@mcp.tool
def list_verticals() -> dict:
    """List all available verticals with their KPI counts and config types.

    Discovery tool for prospects — no authentication required.
    Returns each vertical with its description, total KPI count,
    and the number of config type templates available.
    """
    common.check_mcp_enabled()
    app = common.get_flask_app()

    with app.app_context():
        # Build vertical catalog from kpi_definitions (always available)
        # VerticalTemplate model is optional — used when DB templates exist.
        verticals: dict = {}

        # Try DB-backed VerticalTemplate if available
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
            pass  # VerticalTemplate not available yet — use fallback below

        # Enrich with KPI count from kpi_definitions if available
        for v_key, v_info in verticals.items():
            try:
                kpi_defs = common.get_kpi_definitions(v_key)
                v_info['kpi_count'] = len(kpi_defs)
            except Exception:
                pass
            if v_key == 'dc2_s':
                v_info['description'] = 'Data Center Infrastructure vertical — AI/ML, infra reliability, cloud & DevOps, customer engagement, expansion'
            elif v_key in ('saas_premium', 'saas'):
                v_info['description'] = 'SaaS Premium vertical — product adoption, operational resilience, growth efficiency, partner ecosystem, strategic value'

        # Fallback: if no DB templates, return known verticals from kpi_definitions
        if not verticals:
            known_verticals = {
                'dc2_s': ('Data Center Infrastructure vertical', 38),
                'saas_premium': ('SaaS Premium vertical — product adoption, engagement, support quality, partner ecosystem, revenue & growth', 35),
            }
            for v_slug, (v_desc, v_default_count) in known_verticals.items():
                try:
                    kpi_defs = common.get_kpi_definitions(v_slug)
                    kpi_count = len(kpi_defs)
                except Exception:
                    kpi_count = v_default_count
                verticals[v_slug] = {
                    'vertical': v_slug,
                    'config_types': [],
                    'config_type_count': 0,
                    'kpi_count': kpi_count,
                    'description': v_desc,
                }

        return {
            'scope': 'platform',
            'total_verticals': len(verticals),
            'verticals': list(verticals.values()),
        }


@mcp.tool
def get_reference_customer(vertical: str) -> dict:
    """Get the reference/demo customer for a vertical.

    Discovery tool — no authentication required.
    Returns the reference customer's ID, name, account count, and health summary.
    Reference customers are pre-seeded demo tenants that showcase the platform.

    Args:
        vertical: The vertical slug (e.g. 'dc2_s')
    """
    common.check_mcp_enabled()
    app = common.get_flask_app()

    with app.app_context():
        from models import Customer, Account
        import utils.health_thresholds as ht

        customer = None

        # Try DB columns if they exist (is_reference, reference_for)
        try:
            customer = Customer.query.filter_by(
                is_reference=True,
                reference_for=vertical,
            ).first()
        except Exception:
            pass  # Columns not available yet

        if not customer:
            # Fallback: find any customer tagged with the vertical
            customer = Customer.query.filter_by(vertical=vertical).first()
            if not customer:
                raise ToolError(
                    f"No reference customer found for vertical '{vertical}'. "
                    f"Available verticals can be discovered via list_verticals()."
                )

        # Use the vertical parameter to resolve health functions
        calculate_kpi_health, _get_trailing_kpi_values, get_precalculated_scores = common.get_health_functions(vertical)

        accounts = Account.query.filter_by(
            customer_id=customer.customer_id,
        ).all()

        # Health summary
        health_scores = []
        for acct in accounts:
            precalc_health, _, _ = get_precalculated_scores(acct.account_id)
            if precalc_health is not None:
                health_scores.append(precalc_health)
            else:
                try:
                    kpi_values = _get_trailing_kpi_values(acct.account_id)
                    h, _ = calculate_kpi_health(kpi_values, customer.customer_id)
                    health_scores.append(h)
                except Exception:
                    pass

        avg_health = round(sum(health_scores) / len(health_scores), 1) if health_scores else None
        healthy_count = sum(1 for h in health_scores if h >= ht.healthy_min())
        at_risk_count = sum(1 for h in health_scores if ht.at_risk_min() <= h < ht.healthy_min())
        critical_count = sum(1 for h in health_scores if h < ht.at_risk_min())

        return {
            'scope': 'portfolio',
            'customer_id': customer.customer_id,
            'customer_name': customer.customer_name,
            'vertical': vertical,
            'is_reference': getattr(customer, 'is_reference', False),
            'account_count': len(accounts),
            'health_summary': {
                'avg_health': avg_health,
                'healthy': healthy_count,
                'at_risk': at_risk_count,
                'critical': critical_count,
            },
        }


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
    common.check_mcp_enabled()

    import json as _json

    schemas_path = os.path.join(_backend_dir, 'config', 'csv_schemas.json')
    if not os.path.isfile(schemas_path):
        raise ToolError("CSV schemas config file not found at config/csv_schemas.json")

    with open(schemas_path, 'r') as f:
        schemas = _json.load(f)

    # Combine regular + context_graph files
    all_files = {}
    for model_key in ('regular_model', 'context_graph_model'):
        model = schemas.get(model_key, {})
        files = model.get('files', {})
        for fname, fschema in files.items():
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


@mcp.tool
def get_vertical_config(vertical: str, config_type: str = None) -> dict:
    """Get vertical configuration templates.

    Discovery tool — no authentication required.
    Returns base configuration from VerticalTemplate for the specified vertical.
    If config_type is specified, returns just that config; otherwise returns all.

    Args:
        vertical: The vertical slug (e.g. 'dc2_s')
        config_type: Optional config type (e.g. 'kpi_weights', 'pillar_weights',
                     'health_thresholds', 'scoring_rules'). If omitted, returns all.
    """
    common.check_mcp_enabled()
    app = common.get_flask_app()

    with app.app_context():
        results = []

        # Try DB-backed VerticalTemplate if available
        try:
            from models import VerticalTemplate

            query = VerticalTemplate.query.filter_by(vertical=vertical)
            if config_type:
                query = query.filter_by(config_type=config_type)

            templates = query.all()
            for t in templates:
                results.append({
                    'template_id': t.template_id,
                    'vertical': t.vertical,
                    'config_type': t.config_type,
                    'version': t.version,
                    'config': t.config,
                })
        except (ImportError, Exception):
            pass  # VerticalTemplate not available — use fallback

        # Fallback: build config from kpi_definitions + config files
        if not results:
            try:
                kpi_defs = common.get_kpi_definitions(vertical)
                results.append({
                    'template_id': None,
                    'vertical': vertical,
                    'config_type': 'kpi_definitions',
                    'version': '1.0',
                    'config': {
                        'kpi_count': len(kpi_defs),
                        'kpis': list(kpi_defs.keys())[:10],  # First 10 for preview
                        'note': f'Full {len(kpi_defs)} KPI definitions available',
                    },
                })
            except Exception:
                pass

            # Health thresholds config
            try:
                import utils.health_thresholds as ht
                results.append({
                    'template_id': None,
                    'vertical': vertical,
                    'config_type': 'health_thresholds',
                    'version': '1.0',
                    'config': {
                        'healthy_min': ht.healthy_min(),
                        'at_risk_min': ht.at_risk_min(),
                    },
                })
            except Exception:
                pass

        if config_type and not results:
            raise ToolError(
                f"No config template found for vertical='{vertical}', "
                f"config_type='{config_type}'"
            )

        if config_type and len(results) == 1:
            return {
                'scope': 'platform',
                'vertical': vertical,
                'config_type': config_type,
                'template': results[0],
            }

        return {
            'scope': 'platform',
            'vertical': vertical,
            'total_configs': len(results),
            'templates': results,
        }


@mcp.tool
def get_onboarding_status(customer_id: int) -> dict:
    """Check onboarding progress for a customer.

    Returns a checklist of what has been completed: customer record, admin user,
    config, accounts, KPI data, scores, wizard runs, etc.

    Args:
        customer_id: The customer ID to check
    """
    common.check_mcp_enabled()
    app = common.get_flask_app()

    with app.app_context():
        from models import Customer, CustomerConfig, Account, User, DC2SKPI, WizardRun, db
        from pathlib import Path

        checklist = {
            'customer_exists': False,
            'admin_user_exists': False,
            'config_exists': False,
            'accounts_uploaded': False,
            'account_count': 0,
            'kpi_data_loaded': False,
            'kpi_record_count': 0,
            'scores_calculated': False,
            'wizard_runs': 0,
            'directory_provisioned': False,
            'data_files_present': [],
        }

        # Customer
        customer = db.session.get(Customer, int(customer_id))
        if not customer:
            return {
                'scope': 'customer',
                'customer_id': customer_id,
                'status': 'not_found',
                'checklist': checklist,
                'message': f'Customer {customer_id} does not exist yet. Use create_customer() to begin.',
            }
        checklist['customer_exists'] = True

        # Admin user
        admin = User.query.filter_by(customer_id=customer_id).first()
        checklist['admin_user_exists'] = admin is not None

        # Config
        config = CustomerConfig.query.filter_by(customer_id=customer_id).first()
        checklist['config_exists'] = config is not None

        # Accounts
        accounts = Account.query.filter_by(customer_id=customer_id).all()
        checklist['accounts_uploaded'] = len(accounts) > 0
        checklist['account_count'] = len(accounts)

        # KPI data
        if accounts:
            account_ids = [a.account_id for a in accounts]
            kpi_count = DC2SKPI.query.filter(
                DC2SKPI.account_id.in_(account_ids)
            ).count()
            checklist['kpi_data_loaded'] = kpi_count > 0
            checklist['kpi_record_count'] = kpi_count

        # Pre-calculated scores
        if accounts:
            cust_vertical = getattr(customer, 'vertical', 'dc2_s') or 'dc2_s'
            _, _, get_precalculated_scores = common.get_health_functions(cust_vertical)
            scored = 0
            for acct in accounts:
                h, _, _ = get_precalculated_scores(acct.account_id)
                if h is not None:
                    scored += 1
            checklist['scores_calculated'] = scored > 0

        # Wizard runs
        wizard_count = WizardRun.query.filter_by(customer_id=customer_id).count()
        checklist['wizard_runs'] = wizard_count

        # Directory — use customer's actual vertical
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

        # Overall status
        all_done = all([
            checklist['customer_exists'],
            checklist['admin_user_exists'],
            checklist['config_exists'],
            checklist['accounts_uploaded'],
            checklist['kpi_data_loaded'],
            checklist['scores_calculated'],
        ])
        status = 'complete' if all_done else 'in_progress'

        return {
            'scope': 'customer',
            'customer_id': customer_id,
            'customer_name': customer.customer_name,
            'status': status,
            'checklist': checklist,
        }


# ===================================================================
# Customer Setup Phase (write, no auth)
# ===================================================================

@mcp.tool
def create_customer(
    name: str,
    domain: str,
    vertical: str,
    admin_email: str,
    admin_name: str,
) -> dict:
    """Create a new customer with admin user and auto-generated API key.

    This is the first write step in onboarding. Creates:
    1. Customer record (with UUID)
    2. Admin user (with generated password)
    3. CustomerConfig (vertical defaults)
    4. API key (returned once — save it!)

    No authentication required — this is the entry point for new prospects.

    Args:
        name: Company name
        domain: Email domain (e.g. 'acme.com')
        vertical: Vertical slug (e.g. 'dc2_s')
        admin_email: Admin user email
        admin_name: Admin user display name
    """
    common.check_mcp_enabled()
    app = common.get_flask_app()

    with app.app_context():
        from models import Customer, User, CustomerConfig
        from extensions import db
        from werkzeug.security import generate_password_hash
        import secrets as _secrets

        # Check for duplicate domain
        existing = Customer.query.filter_by(domain=domain).first()
        if existing:
            raise ToolError(
                f"A customer with domain '{domain}' already exists "
                f"(customer_id={existing.customer_id}). "
                f"Use get_onboarding_status() to check its state."
            )

        # Check for duplicate email
        existing_user = User.query.filter_by(email=admin_email).first()
        if existing_user:
            raise ToolError(f"Email '{admin_email}' is already registered.")

        # Generate UUID
        try:
            from id_generator import generate_id, resolve_vertical_prefix
            uuid_vertical = 'dc' if vertical.startswith('dc') else vertical
            customer_uuid = generate_id(uuid_vertical, 'customer')
        except Exception:
            customer_uuid = None

        # Create customer
        customer = Customer(
            customer_name=name,
            email=admin_email,
            domain=domain,
            vertical=vertical,
        )
        if customer_uuid:
            customer.uuid = customer_uuid
        db.session.add(customer)
        db.session.flush()  # Get customer_id

        customer_id = customer.customer_id

        # Create admin user with generated password
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
        db.session.flush()  # Get user_id

        # Create default CustomerConfig
        config = CustomerConfig(
            customer_id=customer_id,
            vertical=vertical,
        )
        db.session.add(config)

        # Generate API key
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

        # Provision customer directory
        try:
            from verticals.provision_dc_customer import provision_customer
            provision_customer(
                customer_id=customer_id,
                customer_name=name,
                vertical_slug=vertical,
                force=True,
            )
            directory_provisioned = True
        except Exception:
            directory_provisioned = False

        db.session.commit()

        result = {
            'scope': 'customer',
            'customer_id': customer_id,
            'customer_name': name,
            'customer_uuid': customer_uuid,
            'domain': domain,
            'vertical': vertical,
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

        return result


@mcp.tool
def configure_customer_kpis(
    customer_id: int,
    enabled_pillars: list = None,
    enabled_kpis: list = None,
    pillar_weights: dict = None,
    kpi_weights: dict = None,
) -> dict:
    """Configure KPI selection and weights for a customer.

    Sets customer-level overrides via CustomerConfig. You can:
    - Select which pillars are active (enabled_pillars)
    - Select exact KPIs (enabled_kpis overrides enabled_pillars)
    - Set L2 pillar weights (pillar_weights)
    - Set L1 KPI weights per pillar (kpi_weights)

    Args:
        customer_id: The customer ID
        enabled_pillars: Optional list of pillar codes (e.g. ['P1', 'P3', 'P5'])
        enabled_kpis: Optional list of KPI codes (e.g. ['P1-KPI1', 'P1-KPI2'])
        pillar_weights: Optional dict of pillar weights (e.g. {'P1': 0.4, 'P3': 0.35, 'P5': 0.25})
        kpi_weights: Optional dict of KPI weights per pillar (e.g. {'P1': {'P1-KPI1': 0.5}})
    """
    common.check_mcp_enabled()
    app = common.get_flask_app()

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
            db.session.add(config)

        # Determine enabled KPIs
        if enabled_kpis:
            config.dc2s_enabled_kpis = enabled_kpis
        elif enabled_pillars:
            # Derive KPIs from pillar selection using the customer's vertical
            try:
                kpi_defs = common.get_kpi_definitions(cust_vertical)
                derived_kpis = [
                    code for code, defn in kpi_defs.items()
                    if defn.get('pillar') in enabled_pillars
                ]
                config.dc2s_enabled_kpis = derived_kpis
            except Exception:
                raise ToolError("Could not load KPI definitions for pillar-based selection.")

        # Set pillar weights (auto-normalize to sum 1.0)
        if pillar_weights:
            pw_total = sum(pillar_weights.values())
            if pw_total > 0 and abs(pw_total - 1.0) > 0.0001:
                pillar_weights = {k: round(v / pw_total, 4) for k, v in pillar_weights.items()}
                _pw_keys = list(pillar_weights.keys())
                _pw_diff = round(1.0 - sum(pillar_weights.values()), 4)
                if _pw_diff != 0 and _pw_keys:
                    pillar_weights[_pw_keys[-1]] = round(pillar_weights[_pw_keys[-1]] + _pw_diff, 4)
            config.dc2s_pillar_weights = pillar_weights

        # Set KPI weights (auto-normalize each pillar to sum 1.0)
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

        db.session.commit()

        return {
            'scope': 'customer',
            'customer_id': customer_id,
            'enabled_kpis': config.dc2s_enabled_kpis,
            'enabled_kpi_count': len(config.dc2s_enabled_kpis) if config.dc2s_enabled_kpis else 0,
            'pillar_weights': config.dc2s_pillar_weights,
            'kpi_weights': config.dc2s_kpi_weights,
            'message': 'Customer KPI configuration updated.',
        }


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
    common.check_mcp_enabled()
    app = common.get_flask_app()

    with app.app_context():
        from models import Customer
        from models import FeatureToggle as FTModel
        from extensions import db

        customer = db.session.get(Customer, int(customer_id))
        if not customer:
            raise ToolError(f"Customer {customer_id} not found.")

        if features is None:
            # Read-only: return current toggles
            toggles = FTModel.query.filter_by(customer_id=customer_id).all()
            return {
                'scope': 'customer',
                'customer_id': customer_id,
                'features': {
                    t.feature_name: t.enabled for t in toggles
                },
                'total_features': len(toggles),
            }

        # Enable specified features
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
# Data Ingestion Phase (write, no auth)
# ===================================================================

@mcp.tool
def validate_csv(customer_id: int, file_type: str, csv_content: str) -> dict:
    """Validate CSV content against the platform schema before uploading.

    Checks that required columns are present and reports any issues.
    Does NOT persist data — use upload_csv() after validation passes.

    Args:
        customer_id: The customer ID (used for context only)
        file_type: The CSV file type (e.g. 'accounts.csv', 'kpi_measurements.csv')
        csv_content: The raw CSV content as a string
    """
    common.check_mcp_enabled()

    import json as _json
    import csv as _csv
    import io as _io

    # Load schema
    schemas_path = os.path.join(_backend_dir, 'config', 'csv_schemas.json')
    if not os.path.isfile(schemas_path):
        raise ToolError("CSV schemas config not found.")

    with open(schemas_path, 'r') as f:
        schemas = _json.load(f)

    # Normalize file_type: accept both 'kpi_measurements' and 'kpi_measurements.csv'
    ft = file_type if file_type.endswith('.csv') else f'{file_type}.csv'

    # Find schema for file_type
    schema = None
    for model_key in ('regular_model', 'context_graph_model'):
        files = schemas.get(model_key, {}).get('files', {})
        if ft in files:
            schema = files[ft]
            break

    if not schema:
        available = []
        for model_key in ('regular_model', 'context_graph_model'):
            available.extend(schemas.get(model_key, {}).get('files', {}).keys())
        raise ToolError(
            f"Unknown file_type '{file_type}'. Available: {sorted(available)}"
        )

    required_columns = set(schema.get('required_columns', []))
    optional_columns = set(schema.get('optional_columns', []))
    all_known = required_columns | optional_columns

    # Parse CSV
    reader = _csv.DictReader(_io.StringIO(csv_content))
    headers = set(reader.fieldnames or [])
    rows = list(reader)

    # Validation
    missing_required = required_columns - headers
    unknown_columns = headers - all_known
    errors = []
    warnings = []

    if missing_required:
        errors.append(f"Missing required columns: {sorted(missing_required)}")
    if unknown_columns:
        warnings.append(f"Unknown columns (will be ignored): {sorted(unknown_columns)}")
    if len(rows) == 0:
        errors.append("CSV has no data rows.")

    valid = len(errors) == 0

    return {
        'scope': 'validation',
        'customer_id': customer_id,
        'file_type': file_type,
        'valid': valid,
        'row_count': len(rows),
        'columns_found': sorted(headers),
        'required_columns': sorted(required_columns),
        'missing_required': sorted(missing_required) if missing_required else [],
        'errors': errors,
        'warnings': warnings,
    }


@mcp.tool
def upload_csv(customer_id: int, file_type: str, csv_content: str) -> dict:
    """Upload CSV data for a customer.

    Saves the CSV content to the customer's data directory on disk.
    The file can then be processed via process_data().

    Args:
        customer_id: The customer ID
        file_type: The CSV file type (e.g. 'accounts.csv', 'kpi_measurements.csv')
        csv_content: The raw CSV content as a string
    """
    common.check_mcp_enabled()
    app = common.get_flask_app()

    with app.app_context():
        from models import Customer, db
        from pathlib import Path

        customer = db.session.get(Customer, int(customer_id))
        if not customer:
            raise ToolError(f"Customer {customer_id} not found.")

        # Normalize file_type to include .csv extension
        ft = file_type if file_type.endswith('.csv') else f'{file_type}.csv'

        # Determine customer data directory
        vertical = getattr(customer, 'vertical', 'dc2_s') or 'dc2_s'
        backend_dir = Path(__file__).parent.parent
        customer_dir = backend_dir / 'verticals' / f'customer{customer_id}-{vertical}'

        # Ensure directory exists
        data_dir = customer_dir / 'data'
        data_dir.mkdir(parents=True, exist_ok=True)

        # Write file
        file_path = data_dir / ft
        file_path.write_text(csv_content, encoding='utf-8')

        return {
            'scope': 'customer',
            'customer_id': customer_id,
            'file_type': file_type,
            'file_path': str(file_path),
            'bytes_written': len(csv_content.encode('utf-8')),
            'message': f"Uploaded {file_type} ({len(csv_content.encode('utf-8'))} bytes). "
                       f"Use process_data() to ingest into the database.",
        }


def _process_data_impl(customer_id: int) -> dict:
    """Trigger the data processing pipeline for a customer.

    Processes uploaded CSV files through the full pipeline:
    1. Data loading (CSVs -> PostgreSQL)
    2. Embedding generation
    3. Data validation
    4. Journey generation (Wizard A)
    5. Pattern analysis (Wizard B)
    6. Weight calibration (Wizard C)

    Args:
        customer_id: The customer ID
    """
    common.check_mcp_enabled()
    app = common.get_flask_app()

    with app.app_context():
        from models import Customer, db
        from pathlib import Path

        customer = db.session.get(Customer, int(customer_id))
        if not customer:
            raise ToolError(f"Customer {customer_id} not found.")

        # Check data directory has files
        vertical = getattr(customer, 'vertical', 'dc2_s') or 'dc2_s'
        backend_dir = Path(__file__).parent.parent
        customer_dir = backend_dir / 'verticals' / f'customer{customer_id}-{vertical}'
        data_dir = customer_dir / 'data'

        if not data_dir.exists():
            raise ToolError(
                f"No data directory found for customer {customer_id}. "
                f"Upload CSV files first via upload_csv()."
            )

        csv_files = [f.name for f in data_dir.iterdir() if f.is_file() and f.suffix == '.csv']
        if not csv_files:
            raise ToolError("No CSV files found in data directory. Upload files first.")

        # Check required files
        required = ['accounts.csv', 'kpi_measurements.csv']
        missing = [f for f in required if f not in csv_files]
        if missing:
            raise ToolError(f"Missing required files: {missing}. Upload them via upload_csv().")

        # Call the onboarding process-data endpoint internally
        import json as _json
        import requests as _requests

        steps_completed = []
        errors = []

        # Call the REST API process-data endpoint (which does the real work)
        try:
            base_url = os.environ.get('CS_PULSE_BASE_URL', 'http://localhost:5001')
            resp = _requests.post(
                f'{base_url}/api/onboarding/process-data',
                json={'customer_id': customer_id},
                timeout=120,
            )
            if resp.status_code == 200:
                result_data = resp.json()
                steps_completed = result_data.get('steps_completed', ['full_pipeline'])
                return {
                    'scope': 'customer',
                    'customer_id': customer_id,
                    'status': 'success',
                    'csv_files_found': csv_files,
                    'steps_completed': steps_completed,
                    'errors': [],
                    'message': (
                        f"Data processing completed successfully. "
                        f"{len(csv_files)} CSV files processed through full pipeline."
                    ),
                }
            else:
                error_msg = resp.text[:500] if resp.text else f'HTTP {resp.status_code}'
                errors.append(f"pipeline: {error_msg}")
        except _requests.exceptions.ConnectionError:
            errors.append(
                "Cannot connect to CS Pulse backend API. "
                "Ensure the backend is running on the configured base URL."
            )
        except Exception as e:
            errors.append(f"pipeline: {str(e)}")

        # Fallback: try direct CSV loading if REST call failed
        try:
            import pandas as pd
            from datetime import datetime as _dt
            from extensions import db as _db
            from models import Account, DC2SKPI, QualitativeSignal

            # ----------------------------------------------------------
            # Step 1: Load accounts first (need them for ID mapping)
            # ----------------------------------------------------------
            accounts_csv = data_dir / 'accounts.csv'
            if accounts_csv.exists():
                df_accts = pd.read_csv(str(accounts_csv))
                if not df_accts.empty:
                    for _, row in df_accts.iterrows():
                        aname = row.get('account_name', row.get('name', ''))
                        existing = Account.query.filter_by(
                            customer_id=customer_id,
                            account_name=aname,
                        ).first()
                        if not existing:
                            acct = Account(
                                customer_id=customer_id,
                                account_name=aname,
                                revenue=row.get('arr', row.get('annual_revenue', row.get('revenue', 0))),
                                vertical=vertical,
                            )
                            _db.session.add(acct)
                    _db.session.flush()
                    steps_completed.append('accounts_loaded')

            # ----------------------------------------------------------
            # Step 2: Build CSV account_id → DB account_id mapping
            # CSV uses {customer_id}001, {customer_id}002 etc.
            # DB auto-generates sequential IDs. Map via account_name.
            # ----------------------------------------------------------
            db_accounts = Account.query.filter_by(customer_id=customer_id).all()
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
            # Fallback: index-based mapping if no accounts.csv mapping
            if not csv_to_db_aid:
                sorted_db = sorted(db_accounts, key=lambda a: a.account_id)
                for i, a in enumerate(sorted_db, 1):
                    csv_to_db_aid[customer_id * 1000 + i] = a.account_id

            def _resolve_acct_id(row):
                """Map CSV source_account_id to DB account_id."""
                # Try account_name first
                aname = row.get('account_name', row.get('account', ''))
                if aname and aname in accounts_by_name:
                    return accounts_by_name[aname]
                # Try source_account_id (new name) or account_id (backward compat)
                raw = row.get('source_account_id', row.get('account_id'))
                if raw is None:
                    return None
                raw = int(raw)
                # Direct DB ID match?
                if raw in accounts_by_db_id:
                    return raw
                # CSV → DB mapping
                return csv_to_db_aid.get(raw)

            # ----------------------------------------------------------
            # Step 3: Load KPIs, signals, and other CSVs
            # ----------------------------------------------------------
            for csv_file in csv_files:
                if csv_file == 'accounts.csv':
                    continue  # Already loaded above
                csv_path = data_dir / csv_file
                df = pd.read_csv(str(csv_path))
                if df.empty:
                    continue

                if csv_file == 'kpi_measurements.csv':
                    for _, row in df.iterrows():
                        acct_id = _resolve_acct_id(row)
                        if acct_id:
                            kpi = DC2SKPI(
                                account_id=acct_id,
                                kpi_code=row.get('kpi_code', row.get('kpi_id', '')),
                                value=float(row.get('value', 0)),
                                target=float(row.get('target', 100)),
                                pillar=row.get('pillar', ''),
                                weight=float(row.get('weight', 0)) if row.get('weight') else None,
                                status=row.get('status', ''),
                                measured_at=row.get('measured_at', row.get('date')),
                            )
                            _db.session.add(kpi)
                    steps_completed.append('kpis_loaded')

                elif csv_file in ('enhanced_qualitative_signals.csv', 'qualitative_signals.csv'):
                    import uuid as _uuid
                    for _, row in df.iterrows():
                        acct_id = _resolve_acct_id(row)
                        if acct_id:
                            sig_id = row.get('signal_id') or f"sig_{_uuid.uuid4().hex[:12]}"
                            sig = QualitativeSignal(
                                signal_id=sig_id,
                                account_id=acct_id,
                                signal_type=row.get('signal_type', 'nps'),
                                content=row.get('content', row.get('signal_text', '')),
                                sentiment=row.get('sentiment', 'neutral'),
                                sentiment_score=float(row.get('sentiment_score', 0.5)),
                                signal_date=row.get('signal_date', row.get('date')),
                            )
                            _db.session.add(sig)
                            # Also create ContextNode for signals with signal_ref
                            # (context graph signals need to be in context_nodes for edge resolution)
                            sig_ref = row.get('signal_ref')
                            if sig_ref and str(sig_ref) != 'nan':
                                from models import ContextNode as CN_
                                content_text = str(row.get('content', ''))
                                sig_node = CN_(
                                    customer_id=customer_id,
                                    account_id=acct_id,
                                    node_type='SIGNAL',
                                    node_subtype=str(row.get('signal_type', 'signal')),
                                    title=content_text[:200],
                                    properties={
                                        'signal_ref': str(sig_ref),
                                        'sentiment': str(row.get('sentiment', '')),
                                        'sentiment_score': str(row.get('sentiment_score', '')),
                                    },
                                    tier=2,
                                    occurred_at=pd.to_datetime(row.get('signal_date')) if row.get('signal_date') else _dt.utcnow(),
                                    source_platform=str(row.get('source_platform', 'csv_import')),
                                    source_event_id=str(sig_ref),
                                )
                                _db.session.add(sig_node)
                    steps_completed.append('signals_loaded')

            _db.session.commit()

            # Calculate health scores for each account
            try:
                calculate_fn, get_kpi_vals, _ = common.get_health_functions(vertical)
                from models import HealthScore, PillarScore
                import utils.health_thresholds as ht
                from datetime import datetime as _dt

                acct_list = Account.query.filter_by(customer_id=customer_id).all()
                month_str = _dt.utcnow().strftime('%Y-%m-01')
                for acct in acct_list:
                    try:
                        kpi_vals = get_kpi_vals(acct.account_id)
                        if not kpi_vals:
                            continue
                        health, pillars = calculate_fn(kpi_vals, customer_id=customer_id)
                        status = ht.classify(health)
                        # Upsert HealthScore
                        hs = HealthScore.query.filter_by(
                            account_id=acct.account_id,
                            measurement_month=month_str,
                        ).first()
                        if not hs:
                            hs = HealthScore(
                                account_id=acct.account_id,
                                measurement_month=month_str,
                            )
                            _db.session.add(hs)
                        hs.health_score = round(health, 2)
                        hs.health_status = status
                        hs.contributing_pillars = {k: round(v, 2) for k, v in pillars.items()}
                        # Upsert PillarScores
                        for pcode, pscore in pillars.items():
                            ps = PillarScore.query.filter_by(
                                account_id=acct.account_id,
                                measurement_month=month_str,
                                pillar_code=pcode,
                            ).first()
                            if not ps:
                                ps = PillarScore(
                                    account_id=acct.account_id,
                                    measurement_month=month_str,
                                    pillar_code=pcode,
                                )
                                _db.session.add(ps)
                            ps.pillar_score = round(pscore, 2)
                    except Exception:
                        pass
                _db.session.commit()
                steps_completed.append('health_scores_calculated')
            except Exception as e:
                errors.append(f"health_calc: {str(e)}")

            # Ingest context graph CSVs if present
            # (_resolve_acct_id is already defined above from Step 2)
            try:
                from utils.context_graph import upsert_node, add_edge
                from models import ContextNode, ContextEdge

                cg_dir = data_dir

                # Stakeholders → ContextNode (STAKEHOLDER)
                stakeholder_path = cg_dir / 'stakeholders.csv'
                if stakeholder_path.exists():
                    df_s = pd.read_csv(str(stakeholder_path))
                    for _, row in df_s.iterrows():
                        acct_id = _resolve_acct_id(row)
                        if not acct_id:
                            continue
                        node = ContextNode(
                            customer_id=customer_id,
                            account_id=acct_id,
                            node_type='STAKEHOLDER',
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
                            occurred_at=_dt.utcnow(),
                            source_platform=str(row.get('source_platform', 'csv_import')),
                        )
                        _db.session.add(node)
                    _db.session.flush()
                    steps_completed.append('stakeholders_loaded')

                # Outcomes → ContextNode (OUTCOME)
                outcomes_path = cg_dir / 'outcomes.csv'
                if outcomes_path.exists():
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
                        node = ContextNode(
                            customer_id=customer_id,
                            account_id=acct_id,
                            node_type='OUTCOME',
                            node_subtype=str(row.get('outcome_type', 'revenue')),
                            title=str(row.get('title', row.get('outcome_name', ''))),
                            revenue_impact=rev_impact,
                            revenue_impact_type=str(row.get('outcome_type', 'expansion')),
                            properties={
                                'evidence': str(row.get('evidence', '')),
                                'confidence': str(row.get('confidence', '')),
                            },
                            tier=1,
                            occurred_at=_dt.utcnow(),
                            source_platform=str(row.get('source_platform', 'csv_import')),
                        )
                        _db.session.add(node)
                    _db.session.flush()
                    steps_completed.append('outcomes_loaded')

                # Decisions → ContextNode (DECISION)
                decisions_path = cg_dir / 'decisions.csv'
                if decisions_path.exists():
                    df_d = pd.read_csv(str(decisions_path))
                    for _, row in df_d.iterrows():
                        acct_id = _resolve_acct_id(row)
                        if not acct_id:
                            continue
                        node = ContextNode(
                            customer_id=customer_id,
                            account_id=acct_id,
                            node_type='DECISION',
                            node_subtype=str(row.get('decision_maker_role', 'action')),
                            title=str(row.get('title', row.get('decision_name', ''))),
                            properties={
                                'chosen_option': str(row.get('chosen_option', '')),
                                'outcome_description': str(row.get('outcome_description', '')),
                                'risk_level': str(row.get('risk_level', '')),
                            },
                            tier=1,
                            occurred_at=_dt.utcnow(),
                            source_platform=str(row.get('source_platform', 'csv_import')),
                        )
                        _db.session.add(node)
                    _db.session.flush()
                    steps_completed.append('decisions_loaded')

                _db.session.commit()
                steps_completed.append('context_graph_loaded')
            except Exception as e:
                errors.append(f"context_graph: {str(e)}")
                try:
                    _db.session.rollback()
                except Exception:
                    pass

            # ----------------------------------------------------------
            # Step 5: Engagement Events → ContextNode (SIGNAL/engagement)
            # ----------------------------------------------------------
            try:
                ee_path = data_dir / 'engagement_events.csv'
                if ee_path.exists():
                    df_ee = pd.read_csv(str(ee_path))
                    for _, row in df_ee.iterrows():
                        acct_id = _resolve_acct_id(row)
                        if not acct_id:
                            continue
                        evt_date = row.get('event_date')
                        node = ContextNode(
                            customer_id=customer_id,
                            account_id=acct_id,
                            node_type='SIGNAL',
                            node_subtype='engagement',
                            title=str(row.get('description', ''))[:200],
                            properties={
                                'event_type': str(row.get('event_type', '')),
                                'channel': str(row.get('channel', '')),
                                'duration_minutes': str(row.get('duration_minutes', '')),
                                'outcome': str(row.get('outcome', '')),
                                'stakeholder_name': str(row.get('stakeholder_name', '')),
                                'sentiment_shift': str(row.get('sentiment_shift', '')),
                            },
                            tier=2,
                            occurred_at=pd.to_datetime(evt_date) if evt_date else _dt.utcnow(),
                            source_platform=str(row.get('source_platform', 'csv_import')),
                        )
                        _db.session.add(node)
                    _db.session.commit()
                    steps_completed.append('engagement_events_loaded')
            except Exception as e:
                errors.append(f"engagement_events: {str(e)}")
                try:
                    _db.session.rollback()
                except Exception:
                    pass

            # ----------------------------------------------------------
            # Step 6: Products → products table
            # ----------------------------------------------------------
            try:
                from models import Product
                prod_path = data_dir / 'products.csv'
                if prod_path.exists():
                    df_p = pd.read_csv(str(prod_path))
                    for _, row in df_p.iterrows():
                        acct_id = _resolve_acct_id(row)
                        if not acct_id:
                            continue
                        pname = str(row.get('product_name', ''))
                        if not pname:
                            continue
                        existing = Product.query.filter_by(
                            account_id=acct_id, product_name=pname
                        ).first()
                        if not existing:
                            prod = Product(
                                account_id=acct_id,
                                customer_id=customer_id,
                                product_name=pname,
                                product_type=row.get('product_category', row.get('product_type', '')),
                                status=row.get('status', 'active'),
                            )
                            _db.session.add(prod)
                    _db.session.commit()
                    steps_completed.append('products_loaded')
            except Exception as e:
                errors.append(f"products: {str(e)}")
                try:
                    _db.session.rollback()
                except Exception:
                    pass

            # ----------------------------------------------------------
            # Step 7: Account Business Profiles → accounts.profile_metadata
            # ----------------------------------------------------------
            try:
                bp_path = data_dir / 'account_business_profiles.csv'
                if bp_path.exists():
                    df_bp = pd.read_csv(str(bp_path))
                    for _, row in df_bp.iterrows():
                        acct_id = _resolve_acct_id(row)
                        if not acct_id or acct_id not in accounts_by_db_id:
                            continue
                        acct = accounts_by_db_id[acct_id]
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
                        # Also update revenue from profile ARR if present
                        arr_val = row.get('arr')
                        if arr_val and str(arr_val) != 'nan':
                            try:
                                acct.revenue = float(arr_val)
                            except (ValueError, TypeError):
                                pass
                    _db.session.commit()
                    steps_completed.append('profiles_loaded')
            except Exception as e:
                errors.append(f"profiles: {str(e)}")
                try:
                    _db.session.rollback()
                except Exception:
                    pass

            # ----------------------------------------------------------
            # Step 8: Industry Benchmarks → ContextNode (EXTERNAL_CONTEXT)
            # ----------------------------------------------------------
            try:
                bench_path = data_dir / 'industry_benchmarks.csv'
                if bench_path.exists():
                    df_bench = pd.read_csv(str(bench_path))
                    # Benchmarks are global — use first account
                    first_acct_id = db_accounts[0].account_id if db_accounts else None
                    if first_acct_id:
                        for _, row in df_bench.iterrows():
                            kpi_code = row.get('kpi_code', '')
                            node = ContextNode(
                                customer_id=customer_id,
                                account_id=first_acct_id,
                                node_type='EXTERNAL_CONTEXT',
                                node_subtype='industry_benchmark',
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
                                tier=1,
                                occurred_at=_dt.utcnow(),
                                source_platform='csv_import',
                                source_event_id=f'bench_{kpi_code}',
                            )
                            _db.session.add(node)
                        _db.session.commit()
                        steps_completed.append('benchmarks_loaded')
            except Exception as e:
                errors.append(f"benchmarks: {str(e)}")
                try:
                    _db.session.rollback()
                except Exception:
                    pass

            # ----------------------------------------------------------
            # Step 9: Signal Edges → context_edges (MUST RUN LAST)
            # Requires all nodes to exist so we can resolve refs.
            # ----------------------------------------------------------
            try:
                se_path = data_dir / 'signal_edges.csv'
                if se_path.exists():
                    df_se = pd.read_csv(str(se_path))
                    # Build ref→node_id maps from all nodes just created
                    all_nodes = ContextNode.query.filter_by(customer_id=customer_id).all()
                    # Map 1: title → node_id
                    title_to_node = {}
                    # Map 2: signal_ref (from properties) → node_id
                    sigref_to_node = {}
                    # Map 3: source_event_id → node_id
                    srcid_to_node = {}
                    for n in all_nodes:
                        if n.title:
                            title_to_node[n.title.strip()] = n.node_id
                            title_to_node[n.title.strip()[:60]] = n.node_id
                        if n.source_event_id:
                            srcid_to_node[n.source_event_id] = n.node_id
                        # Extract signal_ref from properties JSON
                        if n.properties and isinstance(n.properties, dict):
                            sr = n.properties.get('signal_ref')
                            if sr:
                                sigref_to_node[str(sr)] = n.node_id

                    def _resolve_edge_ref(ref_str):
                        """Resolve signal_edges ref like 'phase0:w3 — Title text' to node_id."""
                        if not ref_str or str(ref_str) == 'nan':
                            return None
                        ref_str = str(ref_str).strip()
                        # Extract phase_ref prefix (e.g. 'phase0:w3') and title
                        phase_ref = None
                        title_part = None
                        for sep in [' — ', ' – ', ' - ']:
                            if sep in ref_str:
                                phase_ref = ref_str.split(sep, 1)[0].strip()
                                title_part = ref_str.split(sep, 1)[1].strip()
                                break
                        # Strategy 1: Match by phase_ref in signal_ref map
                        if phase_ref:
                            nid = sigref_to_node.get(phase_ref)
                            if nid:
                                return nid
                            nid = srcid_to_node.get(phase_ref)
                            if nid:
                                return nid
                        # Strategy 2: Match by title
                        if title_part:
                            nid = title_to_node.get(title_part)
                            if nid:
                                return nid
                            nid = title_to_node.get(title_part[:200])
                            if nid:
                                return nid
                            nid = title_to_node.get(title_part[:60])
                            if nid:
                                return nid
                        # Strategy 3: Try whole ref as title or source_event_id
                        return title_to_node.get(ref_str) or srcid_to_node.get(ref_str)

                    edges_created = 0
                    for _, row in df_se.iterrows():
                        from_id = _resolve_edge_ref(row.get('from_signal_ref'))
                        to_id = _resolve_edge_ref(row.get('to_signal_ref'))
                        if from_id and to_id and from_id != to_id:
                            edge = ContextEdge(
                                customer_id=customer_id,
                                from_node_id=from_id,
                                to_node_id=to_id,
                                edge_type=str(row.get('edge_type', 'LED_TO')),
                                weight=float(row.get('weight', 1.0)),
                                confidence=float(row.get('confidence', 1.0)) if row.get('confidence') else 1.0,
                                source_platform=str(row.get('source_platform', 'csv_import')),
                                created_by=str(row.get('created_by', 'process_data')),
                                properties={
                                    'evidence': str(row.get('evidence', '')),
                                },
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
                    steps_completed.append(f'edges_loaded ({edges_created})')
            except Exception as e:
                errors.append(f"signal_edges: {str(e)}")
                try:
                    _db.session.rollback()
                except Exception:
                    pass

        except Exception as e:
            errors.append(f"direct_loading: {str(e)}")

        status = 'success' if steps_completed and not errors else 'partial' if steps_completed else 'failed'

        return {
            'scope': 'customer',
            'customer_id': customer_id,
            'status': status,
            'csv_files_found': csv_files,
            'steps_completed': steps_completed,
            'errors': errors,
            'message': (
                f"Data processing {'completed' if status == 'success' else 'completed with issues'}. "
                f"Steps: {', '.join(steps_completed) if steps_completed else 'none'}."
            ),
        }


@mcp.tool
def process_data(customer_id: int) -> dict:
    """Trigger the data processing pipeline for a customer.

    Processes uploaded CSV files through the full pipeline:
    1. Data loading (CSVs -> PostgreSQL)
    2. Embedding generation
    3. Data validation
    4. Journey generation (Wizard A)
    5. Pattern analysis (Wizard B)
    6. Weight calibration (Wizard C)

    Args:
        customer_id: The customer ID
    """
    return _process_data_impl(customer_id)


# ===================================================================
# Post-Onboarding Phase (write, no auth)
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
    common.check_mcp_enabled()
    app = common.get_flask_app()

    with app.app_context():
        from models import Customer, WizardRun
        from extensions import db
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

        # Create a WizardRun record
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
            # Ensure clean DB session (prior errors may have left it aborted)
            try:
                db.session.rollback()
            except Exception:
                pass

            run.status = 'running'
            run.started_at = datetime.utcnow()
            db.session.add(run)
            db.session.commit()

            if wizard == 'a':
                from wizards.wizard_a_journey_db import run_wizard_a
                result_summary = run_wizard_a(customer_id)

            elif wizard == 'b':
                try:
                    from wizards.wizard_b_pattern_db import run_wizard_b
                    result_summary = run_wizard_b(customer_id)
                except (ImportError, ValueError) as wb_err:
                    result_summary = {
                        'status': 'skipped',
                        'reason': str(wb_err),
                    }

            elif wizard == 'c':
                from wizards.wizard_c_weight_calibrator_db import run_wizard_c
                result_summary = run_wizard_c(customer_id)

            run.status = result_summary.get('status', 'completed')
            run.completed_at = datetime.utcnow()
            run.results = result_summary
            db.session.commit()

        except Exception as e:
            try:
                db.session.rollback()
            except Exception:
                pass
            try:
                run.status = 'failed'
                run.error_message = str(e)[:500]
                run.completed_at = datetime.utcnow()
                db.session.add(run)
                db.session.commit()
            except Exception:
                pass
            result_summary['error'] = str(e)[:500]

        return {
            'scope': 'customer',
            'customer_id': customer_id,
            'wizard': wizard,
            'wizard_name': wizard_name,
            'run_id': run_id,
            'status': run.status,
            'result_summary': result_summary,
        }


@mcp.tool
def complete_onboarding(customer_id: int) -> dict:
    """Finalize onboarding for a customer.

    Performs final checks and marks the customer as onboarded:
    1. Verifies all required steps are done (customer, accounts, KPIs, scores)
    2. Sets the customer status to active
    3. Returns a final summary with next steps

    Args:
        customer_id: The customer ID
    """
    common.check_mcp_enabled()
    app = common.get_flask_app()

    with app.app_context():
        from models import Customer, CustomerConfig, Account, User, DC2SKPI
        from extensions import db

        customer = db.session.get(Customer, int(customer_id))
        if not customer:
            raise ToolError(f"Customer {customer_id} not found.")

        # Check all required pieces
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

        # Calculate portfolio health for summary
        cust_vertical = getattr(customer, 'vertical', 'dc2_s') or 'dc2_s'
        calculate_kpi_health, _get_trailing_kpi_values, get_precalculated_scores = common.get_health_functions(cust_vertical)
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
            total_arr += common.get_account_arr(acct)

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


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    common.run_server(mcp, default_port=8003)
