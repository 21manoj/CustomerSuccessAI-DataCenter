#!/usr/bin/env python3
"""
CS Pulse MCP — Onboarding Tools (frictionless auth).

11 tools moved from cs_pulse_mcp_server.py:
  - list_verticals
  - get_csv_templates
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
    _get_flask_app,
    _get_account_arr,
    _get_health_functions,
    _get_kpi_definitions,
    _get_dc2s_pillar_labels,
    _resolve_customer_vertical,
    _backend_dir,
    ToolError,
)


# ===================================================================
# Onboarding tool set (used by auth.py for frictionless auth)
# ===================================================================

ONBOARDING_TOOLS = {
    'list_verticals',
    'get_csv_templates',
    'create_customer',
    'configure_customer_kpis',
    'enable_features',
    'upload_csv',
    'process_data',
    'trigger_wizard',
    'complete_onboarding',
    'clone_customer',
    'download_customer_csv',
}


def _is_onboarding_tool(name: str) -> bool:
    """Return True if the tool name is in the frictionless onboarding set."""
    return name in ONBOARDING_TOOLS


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
            if v_key == 'dc2_s':
                v_info['description'] = 'Data Center Infrastructure vertical — AI/ML, infra reliability, cloud & DevOps, customer engagement, expansion'
            elif v_key in ('saas_premium', 'saas'):
                v_info['description'] = 'SaaS Premium vertical — product adoption, operational resilience, growth efficiency, partner ecosystem, strategic value'

        if not verticals:
            known_verticals = {
                'dc2_s': ('Data Center Infrastructure vertical', 38),
                'saas_premium': ('SaaS Premium vertical — product adoption, engagement, support quality, partner ecosystem, revenue & growth', 35),
            }
            for v_slug, (v_desc, v_default_count) in known_verticals.items():
                try:
                    kpi_defs = _get_kpi_definitions(v_slug)
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

        try:
            from models import Customer, Account

            for v_slug, v_info in verticals.items():
                ref_customer = None
                try:
                    ref_customer = Customer.query.filter_by(
                        is_reference=True,
                        reference_for=v_slug,
                    ).first()
                except Exception:
                    pass

                if not ref_customer:
                    ref_customer = Customer.query.filter_by(vertical=v_slug).first()

                if ref_customer:
                    acct_count = Account.query.filter_by(
                        customer_id=ref_customer.customer_id,
                    ).count()
                    v_info['reference_customer'] = {
                        'customer_id': ref_customer.customer_id,
                        'name': ref_customer.customer_name,
                        'account_count': acct_count,
                    }
                else:
                    v_info['reference_customer'] = None
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
    _check_mcp_enabled()

    import json as _json

    schemas_path = os.path.join(_backend_dir, 'config', 'csv_schemas.json')
    if not os.path.isfile(schemas_path):
        raise ToolError("CSV schemas config file not found at config/csv_schemas.json")

    with open(schemas_path, 'r') as f:
        schemas = _json.load(f)

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


# ===================================================================
# Tool: create_customer
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

        return result


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

    Args:
        customer_id: The customer ID
        file_type: The CSV file type (e.g. 'accounts.csv', 'kpi_measurements.csv')
        csv_content: The raw CSV content as a string
        dry_run: If True, validate only — do not persist. Returns validation result.
    """
    _check_mcp_enabled()

    import json as _json
    import csv as _csv
    import io as _io

    ft = file_type if file_type.endswith('.csv') else f'{file_type}.csv'

    schemas_path = os.path.join(_backend_dir, 'config', 'csv_schemas.json')
    if not os.path.isfile(schemas_path):
        raise ToolError("CSV schemas config not found.")

    with open(schemas_path, 'r') as f:
        schemas = _json.load(f)

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

    reader = _csv.DictReader(_io.StringIO(csv_content))
    headers = set(reader.fieldnames or [])
    rows = list(reader)

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

    if dry_run:
        return {
            'scope': 'validation',
            'customer_id': customer_id,
            'file_type': file_type,
            'dry_run': True,
            'valid': valid,
            'row_count': len(rows),
            'columns_found': sorted(headers),
            'required_columns': sorted(required_columns),
            'missing_required': sorted(missing_required) if missing_required else [],
            'errors': errors,
            'warnings': warnings,
        }

    if not valid:
        raise ToolError(
            f"CSV validation failed for {file_type}: {'; '.join(errors)}. "
            f"Use dry_run=True to inspect details without uploading."
        )

    app = _get_flask_app()

    with app.app_context():
        from models import Customer, db
        from pathlib import Path

        customer = db.session.get(Customer, int(customer_id))
        if not customer:
            raise ToolError(f"Customer {customer_id} not found.")

        vertical = getattr(customer, 'vertical', 'dc2_s') or 'dc2_s'
        backend_dir = Path(__file__).parent.parent
        customer_dir = backend_dir / 'verticals' / f'customer{customer_id}-{vertical}'

        data_dir = customer_dir / 'data'
        data_dir.mkdir(parents=True, exist_ok=True)

        file_path = data_dir / ft
        file_path.write_text(csv_content, encoding='utf-8')

        return {
            'scope': 'customer',
            'customer_id': customer_id,
            'file_type': file_type,
            'file_path': str(file_path),
            'bytes_written': len(csv_content.encode('utf-8')),
            'row_count': len(rows),
            'warnings': warnings,
            'message': f"Uploaded {file_type} ({len(csv_content.encode('utf-8'))} bytes, "
                       f"{len(rows)} rows). Use process_data() to ingest into the database.",
        }


# ===================================================================
# _process_data_impl — Single source of truth for data processing
# ===================================================================

def _process_data_impl(customer_id: int) -> dict:
    """Trigger the data processing pipeline for a customer.

    Two paths:
    - Path 1 (DB-native): Data already in DB -> recalculate health scores
    - Path 2 (Fresh CSV): No data in DB -> load CSVs into DB, then calculate

    Args:
        customer_id: The customer ID
    """
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
        # Path 2 ONLY: Fresh customer — load CSVs into DB
        # ----------------------------------------------------------
        if not data_in_db and has_csv_dir:
            csv_files = [f.name for f in data_dir.iterdir()
                         if f.is_file() and f.suffix == '.csv']

            # Step 1: Load accounts
            accounts_csv = data_dir / 'accounts.csv'
            if accounts_csv.exists():
                df_accts = pd.read_csv(str(accounts_csv))
                if not df_accts.empty:
                    for _, row in df_accts.iterrows():
                        aname = row.get('account_name', row.get('name', ''))
                        existing = Account.query.filter_by(
                            customer_id=customer_id, account_name=aname,
                        ).first()
                        if not existing:
                            acct = Account(
                                customer_id=customer_id, account_name=aname,
                                revenue=row.get('arr', row.get('annual_revenue', row.get('revenue', 0))),
                                vertical=vertical,
                            )
                            _db.session.add(acct)
                    _db.session.flush()
                    steps_completed.append('accounts_loaded_from_csv')

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
                if raw in accounts_by_db_id:
                    return raw
                return csv_to_db_aid.get(raw)

            # Step 3: Load KPIs, signals, and other CSVs
            try:
                for csv_file in csv_files:
                    if csv_file == 'accounts.csv':
                        continue
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
                                    signal_id=sig_id, account_id=acct_id,
                                    signal_type=row.get('signal_type', 'nps'),
                                    content=row.get('content', row.get('signal_text', '')),
                                    sentiment=row.get('sentiment', 'neutral'),
                                    sentiment_score=float(row.get('sentiment_score', 0.5)),
                                    signal_date=row.get('signal_date', row.get('date')),
                                )
                                _db.session.add(sig)
                                sig_ref = row.get('signal_ref')
                                if sig_ref and str(sig_ref) != 'nan':
                                    from models import ContextNode as CN_
                                    sig_node = CN_(
                                        customer_id=customer_id, account_id=acct_id,
                                        node_type='SIGNAL',
                                        node_subtype=str(row.get('signal_type', 'signal')),
                                        title=str(row.get('content', ''))[:200],
                                        properties={'signal_ref': str(sig_ref),
                                                    'sentiment': str(row.get('sentiment', '')),
                                                    'sentiment_score': str(row.get('sentiment_score', ''))},
                                        tier=2,
                                        occurred_at=pd.to_datetime(row.get('signal_date')) if row.get('signal_date') else _dt.utcnow(),
                                        source_platform=str(row.get('source_platform', 'csv_import')),
                                        source_event_id=str(sig_ref),
                                    )
                                    _db.session.add(sig_node)
                        steps_completed.append('signals_loaded')

                _db.session.commit()
            except Exception as e:
                errors.append(f"csv_loading: {str(e)}")
                try:
                    _db.session.rollback()
                except Exception:
                    pass

            # Steps 4-9: Context graph CSVs
            try:
                from models import ContextNode, ContextEdge

                # Stakeholders
                stakeholder_path = data_dir / 'stakeholders.csv'
                if stakeholder_path.exists():
                    df_s = pd.read_csv(str(stakeholder_path))
                    for _, row in df_s.iterrows():
                        acct_id = _resolve_acct_id(row)
                        if not acct_id:
                            continue
                        _db.session.add(ContextNode(
                            customer_id=customer_id, account_id=acct_id,
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
                            tier=1, occurred_at=_dt.utcnow(),
                            source_platform=str(row.get('source_platform', 'csv_import')),
                        ))
                    _db.session.flush()
                    steps_completed.append('stakeholders_loaded')

                # Outcomes
                outcomes_path = data_dir / 'outcomes.csv'
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
                        _db.session.add(ContextNode(
                            customer_id=customer_id, account_id=acct_id,
                            node_type='OUTCOME',
                            node_subtype=str(row.get('outcome_type', 'revenue')),
                            title=str(row.get('title', row.get('outcome_name', ''))),
                            revenue_impact=rev_impact,
                            revenue_impact_type=str(row.get('outcome_type', 'expansion')),
                            properties={'evidence': str(row.get('evidence', '')),
                                        'confidence': str(row.get('confidence', ''))},
                            tier=1, occurred_at=_dt.utcnow(),
                            source_platform=str(row.get('source_platform', 'csv_import')),
                        ))
                    _db.session.flush()
                    steps_completed.append('outcomes_loaded')

                # Decisions
                decisions_path = data_dir / 'decisions.csv'
                if decisions_path.exists():
                    df_d = pd.read_csv(str(decisions_path))
                    for _, row in df_d.iterrows():
                        acct_id = _resolve_acct_id(row)
                        if not acct_id:
                            continue
                        _db.session.add(ContextNode(
                            customer_id=customer_id, account_id=acct_id,
                            node_type='DECISION',
                            node_subtype=str(row.get('decision_maker_role', 'action')),
                            title=str(row.get('title', row.get('decision_name', ''))),
                            properties={'chosen_option': str(row.get('chosen_option', '')),
                                        'outcome_description': str(row.get('outcome_description', '')),
                                        'risk_level': str(row.get('risk_level', ''))},
                            tier=1, occurred_at=_dt.utcnow(),
                            source_platform=str(row.get('source_platform', 'csv_import')),
                        ))
                    _db.session.flush()
                    steps_completed.append('decisions_loaded')

                # Engagement Events
                ee_path = data_dir / 'engagement_events.csv'
                if ee_path.exists():
                    df_ee = pd.read_csv(str(ee_path))
                    for _, row in df_ee.iterrows():
                        acct_id = _resolve_acct_id(row)
                        if not acct_id:
                            continue
                        evt_date = row.get('event_date')
                        _db.session.add(ContextNode(
                            customer_id=customer_id, account_id=acct_id,
                            node_type='SIGNAL', node_subtype='engagement',
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
                        ))
                    steps_completed.append('engagement_events_loaded')

                # Products
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
                if se_path.exists():
                    df_se = pd.read_csv(str(se_path))
                    all_nodes = ContextNode.query.filter_by(customer_id=customer_id).all()
                    title_to_node, sigref_to_node, srcid_to_node = {}, {}, {}
                    for n in all_nodes:
                        if n.title:
                            title_to_node[n.title.strip()] = n.node_id
                            title_to_node[n.title.strip()[:60]] = n.node_id
                        if n.source_event_id:
                            srcid_to_node[n.source_event_id] = n.node_id
                        if n.properties and isinstance(n.properties, dict):
                            sr = n.properties.get('signal_ref')
                            if sr:
                                sigref_to_node[str(sr)] = n.node_id

                    def _resolve_edge_ref(ref_str):
                        if not ref_str or str(ref_str) == 'nan':
                            return None
                        ref_str = str(ref_str).strip()
                        phase_ref, title_part = None, None
                        for sep in [' \u2014 ', ' \u2013 ', ' - ']:
                            if sep in ref_str:
                                phase_ref = ref_str.split(sep, 1)[0].strip()
                                title_part = ref_str.split(sep, 1)[1].strip()
                                break
                        if phase_ref:
                            nid = sigref_to_node.get(phase_ref) or srcid_to_node.get(phase_ref)
                            if nid:
                                return nid
                        if title_part:
                            for t in [title_part, title_part[:200], title_part[:60]]:
                                nid = title_to_node.get(t)
                                if nid:
                                    return nid
                        return title_to_node.get(ref_str) or srcid_to_node.get(ref_str)

                    edges_created = 0
                    for _, row in df_se.iterrows():
                        from_id = _resolve_edge_ref(row.get('from_signal_ref'))
                        to_id = _resolve_edge_ref(row.get('to_signal_ref'))
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
            except Exception as e:
                errors.append(f"context_graph: {str(e)}")
                try:
                    _db.session.rollback()
                except Exception:
                    pass

        else:
            steps_completed.append(
                f'data_already_in_db_{len(existing_accounts)}_accounts_{existing_kpi_count}_kpis'
            )

        # ----------------------------------------------------------
        # ALWAYS: Recalculate health scores from DB data
        # Per-month: group KPIs by month, compute health per month
        # per account. This enables ROI engine to see historical
        # deltas (e.g. Phase 1 baseline vs Phase 2 intervention).
        # ----------------------------------------------------------
        try:
            calculate_fn, _, _ = _get_health_functions(vertical)
            import utils.health_thresholds as ht
            from datetime import date as _date
            from sqlalchemy import create_engine, text as _text
            import json as _json, logging
            from collections import defaultdict
            _logger = logging.getLogger(__name__)

            database_url = os.environ.get('DATABASE_URL')
            if not database_url:
                from dotenv import load_dotenv
                load_dotenv()
                database_url = os.environ.get('DATABASE_URL')

            acct_list = Account.query.filter_by(customer_id=customer_id).all()

            # Fetch ALL KPI measurements for this customer, grouped by account+month
            from models import DC2SKPI
            all_kpis = DC2SKPI.query.filter(
                DC2SKPI.account_id.in_([a.account_id for a in acct_list])
            ).all()

            # Group by (account_id, month) → {kpi_code: [values]}
            account_month_kpis = defaultdict(lambda: defaultdict(list))
            for k in all_kpis:
                if k.measured_at:
                    month_key = k.measured_at.date().replace(day=1) if hasattr(k.measured_at, 'date') else k.measured_at.replace(day=1)
                else:
                    month_key = _date.today().replace(day=1)
                account_month_kpis[(k.account_id, month_key)][k.kpi_code].append(float(k.value))

            # For each (account, month), average the KPI values and compute health
            score_rows = []
            scores_skipped = 0
            for (account_id, month), kpi_groups in account_month_kpis.items():
                try:
                    # Average multiple measurements per KPI within the same month
                    kpi_vals = {code: sum(vals) / len(vals) for code, vals in kpi_groups.items()}
                    if not kpi_vals:
                        scores_skipped += 1
                        continue
                    health, pillars = calculate_fn(kpi_vals, customer_id=customer_id)
                    score_rows.append({
                        "aid": account_id,
                        "month": month,
                        "score": round(health, 2),
                        "status": ht.classify(health),
                        "pillars": _json.dumps({k: round(v, 2) for k, v in pillars.items()}) if pillars else None,
                    })
                except Exception as calc_err:
                    _logger.warning(f"Health score calc failed for account {account_id} month {month}: {calc_err}")

            _logger.info(f"Per-month health calc: {len(score_rows)} rows for {len(set(r['aid'] for r in score_rows))} accounts, "
                         f"{len(set(r['month'] for r in score_rows))} distinct months")

            scores_written = 0
            if database_url and score_rows:
                engine = create_engine(database_url)
                with engine.begin() as conn:
                    # UPSERT: preserve historical months, update only matching (account_id, measurement_month).
                    # This is critical for 2-phase loads where Phase 1 and Phase 2 produce different months.
                    # Old behavior (DELETE all) destroyed historical data needed by ROI engine.
                    for row in score_rows:
                        conn.execute(_text("""
                            INSERT INTO health_scores
                                (account_id, measurement_month, health_score, health_status, contributing_pillars)
                            VALUES (:aid, :month, :score, :status, :pillars)
                            ON CONFLICT (account_id, measurement_month)
                            DO UPDATE SET
                                health_score = EXCLUDED.health_score,
                                health_status = EXCLUDED.health_status,
                                contributing_pillars = EXCLUDED.contributing_pillars
                        """), row)
                        scores_written += 1

                    # Compute change_from_last_month for all this customer's health scores
                    conn.execute(_text("""
                        UPDATE health_scores hs
                        SET change_from_last_month = hs.health_score - prev.health_score
                        FROM (
                            SELECT account_id, measurement_month, health_score,
                                   LAG(health_score) OVER (PARTITION BY account_id ORDER BY measurement_month) AS prev_score
                            FROM health_scores
                            WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = :cid)
                        ) prev
                        WHERE hs.account_id = prev.account_id
                          AND hs.measurement_month = prev.measurement_month
                          AND prev.prev_score IS NOT NULL
                    """), {"cid": customer_id})
                engine.dispose()
            elif not database_url:
                _logger.error("DATABASE_URL not set — cannot write health scores")

            _logger.info(
                f"Health scores: {scores_written} written, {scores_skipped} skipped (no KPIs) "
                f"— customer {customer_id}"
            )
            steps_completed.append(f'health_scores_recalculated_{scores_written}_accounts')
        except Exception as e:
            errors.append(f"health_calc: {str(e)}")
            import logging as _log2
            _log2.getLogger(__name__).error(
                f"Health score recalculation failed for customer {customer_id}: {e}", exc_info=True
            )

        status = 'success' if steps_completed and not errors else 'partial' if steps_completed else 'failed'

        return {
            'scope': 'customer',
            'customer_id': customer_id,
            'status': status,
            'accounts': len(existing_accounts),
            'kpi_measurements': existing_kpi_count or DC2SKPI.query.filter(
                DC2SKPI.account_id.in_(existing_acct_ids)).count(),
            'csv_files_processed': csv_files if csv_files else None,
            'steps_completed': steps_completed,
            'errors': errors,
            'message': (
                f"Data processing {'completed' if status == 'success' else 'completed with issues'}. "
                f"Steps: {', '.join(steps_completed) if steps_completed else 'none'}."
            ),
        }


# ===================================================================
# Tool: process_data
# ===================================================================

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

    Args:
        customer_id: The customer ID
        check_only: If True, return onboarding status checklist without finalizing.
    """
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
                'scores_calculated': False,
                'wizard_runs': 0,
                'directory_provisioned': False,
                'data_files_present': [],
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
                cust_vertical = getattr(customer, 'vertical', 'dc2_s') or 'dc2_s'
                _, _, get_precalculated_scores_fn = _get_health_functions(cust_vertical)
                scored = 0
                for acct in accounts:
                    h, _, _ = get_precalculated_scores_fn(acct.account_id)
                    if h is not None:
                        scored += 1
                checklist['scores_calculated'] = scored > 0

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

    No authentication required (onboarding tool).

    Args:
        source_customer_id: Customer ID to clone from (e.g. 407 for Gold_DC_Alpha)
        new_name: Name for the new customer (e.g. 'Acme Corp')
        new_domain: Domain for the new customer (e.g. 'acme.com')
    """
    _check_mcp_enabled()
    app = _get_flask_app()

    with app.app_context():
        from models import (
            Customer, CustomerConfig, Account, DC2SKPI,
            HealthScore, KPIScore, PillarScore,
            ContextNode, ContextEdge,
            QualitativeSignal, PlaybookExecution,
            ROISnapshot, JourneyData,
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
        summary['dc2s_kpis_cloned'] = kpi_count

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
            summary.get('accounts_cloned', 0) + summary.get('dc2s_kpis_cloned', 0)
            + summary.get('health_scores_cloned', 0) + summary.get('kpi_scores_cloned', 0)
            + summary.get('pillar_scores_cloned', 0) + summary.get('context_nodes_cloned', 0)
            + summary.get('context_edges_cloned', 0) + summary.get('qualitative_signals_cloned', 0)
            + summary.get('playbook_executions_cloned', 0) + summary.get('roi_snapshots_cloned', 0)
            + summary.get('journey_data_cloned', 0)
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
            'All data has been deep-copied with pre-calculated scores. '
            'OPTION 2 — Customize: Use download_customer_csv() to get '
            'the 8 CSVs, modify them, then upload_csv() + process_data() to recalculate.'
        )

        result['dc2s_pillar_labels'] = _get_dc2s_pillar_labels()

        return result


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

    No authentication required (onboarding tool).

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
                    rows.append({
                        'account_id': k.account_id, 'kpi_code': k.kpi_code,
                        'measured_at': k.measured_at.isoformat() if k.measured_at else '',
                        'value': float(k.value), 'kpi_name': '', 'pillar': k.pillar or '',
                        'target': float(k.target) if k.target else '',
                        'weight': float(k.weight) if k.weight else '',
                        'unit': '', 'status': k.status or '',
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
                    rows.append({
                        'account_id': s.account_id,
                        'signal_date': s.signal_date.isoformat() if s.signal_date else '',
                        'signal_type': s.signal_type or '', 'content': s.content or '',
                        'sentiment': s.sentiment or '', 'signal_ref': s.signal_id or '',
                        'sentiment_score': float(s.sentiment_score) if s.sentiment_score else '',
                        'stakeholder_name': '', 'stakeholder_title': s.stakeholder_title or '',
                        'causal_chain_ref': '', 'revenue_impact': '', 'confidence': '',
                        'source_platform': '',
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
