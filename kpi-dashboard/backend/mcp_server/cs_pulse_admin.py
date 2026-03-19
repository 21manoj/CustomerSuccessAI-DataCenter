#!/usr/bin/env python3
"""
CS Pulse Admin MCP Server — admin tools for cloning customers,
exporting/downloading CSV data.

Extracted from the monolithic cs_pulse_mcp_server.py.
Runs on port 8004.
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

mcp = FastMCP(
    "CS Pulse Admin",
    instructions="CS Pulse admin tools — clone customers, export/download CSVs. Requires admin scope.",
)


# ===================================================================
# Tool: clone_customer — Deep-copy an existing customer for demos
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
    common.check_mcp_enabled()
    app = common.get_flask_app()

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

        # ----------------------------------------------------------
        # Validate source customer exists
        # ----------------------------------------------------------
        source = db.session.get(Customer, int(source_customer_id))
        if not source:
            raise ToolError(f"Source customer {source_customer_id} not found.")

        # Check for duplicate domain
        existing = Customer.query.filter_by(domain=new_domain).first()
        if existing:
            raise ToolError(
                f"A customer with domain '{new_domain}' already exists "
                f"(customer_id={existing.customer_id})."
            )

        summary = {}

        # ----------------------------------------------------------
        # 1. Clone Customer record
        # ----------------------------------------------------------
        new_customer = Customer(
            customer_name=new_name,
            email=None,  # No email for cloned customer
            domain=new_domain,
            vertical=source.vertical,
        )
        # Generate UUID
        try:
            from id_generator import generate_id
            uuid_vertical = 'dc' if (source.vertical or '').startswith('dc') else (source.vertical or 'dc')
            new_customer.uuid = generate_id(uuid_vertical, 'customer')
        except Exception:
            new_customer.uuid = f"clone_{_uuid_mod.uuid4().hex[:16]}"
        db.session.add(new_customer)
        db.session.flush()  # Get new customer_id

        new_cid = new_customer.customer_id
        summary['customer_id'] = new_cid
        summary['customer_name'] = new_name
        summary['domain'] = new_domain
        summary['vertical'] = source.vertical

        # ----------------------------------------------------------
        # 2. Clone CustomerConfig
        # ----------------------------------------------------------
        source_config = CustomerConfig.query.filter_by(
            customer_id=source_customer_id,
        ).first()
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

        # ----------------------------------------------------------
        # 3. Clone Accounts (build old->new account_id map)
        # ----------------------------------------------------------
        source_accounts = Account.query.filter_by(
            customer_id=source_customer_id,
        ).all()

        acct_id_map = {}  # old_account_id -> new_account_id
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
            # Generate account UUID
            try:
                new_acct.uuid = generate_id(uuid_vertical, 'account')
            except Exception:
                new_acct.uuid = f"clone_acct_{_uuid_mod.uuid4().hex[:12]}"
            new_acct.customer_uuid = new_customer.uuid
            db.session.add(new_acct)
            db.session.flush()
            acct_id_map[acct.account_id] = new_acct.account_id

        summary['accounts_cloned'] = len(acct_id_map)

        # ----------------------------------------------------------
        # 4. Clone DC2S KPI measurements (joins through accounts)
        # ----------------------------------------------------------
        kpi_count = 0
        for old_aid, new_aid in acct_id_map.items():
            kpis = DC2SKPI.query.filter_by(account_id=old_aid).all()
            for kpi in kpis:
                new_kpi = DC2SKPI(
                    account_id=new_aid,
                    kpi_code=kpi.kpi_code,
                    value=kpi.value,
                    target=kpi.target,
                    pillar=kpi.pillar,
                    weight=kpi.weight,
                    status=kpi.status,
                    measured_at=kpi.measured_at,
                    created_at=kpi.created_at,
                )
                db.session.add(new_kpi)
                kpi_count += 1
        summary['dc2s_kpis_cloned'] = kpi_count

        # ----------------------------------------------------------
        # 5. Clone Health Scores (joins through accounts)
        # ----------------------------------------------------------
        hs_count = 0
        for old_aid, new_aid in acct_id_map.items():
            scores = HealthScore.query.filter_by(account_id=old_aid).all()
            for s in scores:
                new_hs = HealthScore(
                    account_id=new_aid,
                    measurement_month=s.measurement_month,
                    health_score=s.health_score,
                    health_status=s.health_status,
                    trend=s.trend,
                    change_from_last_month=s.change_from_last_month,
                    contributing_pillars=s.contributing_pillars,
                    pillar_weights=s.pillar_weights,
                    calculated_at=s.calculated_at,
                )
                db.session.add(new_hs)
                hs_count += 1
        summary['health_scores_cloned'] = hs_count

        # ----------------------------------------------------------
        # 5b. Clone KPI Scores (L1) and Pillar Scores (L2)
        # ----------------------------------------------------------
        kpi_score_count = 0
        for old_aid, new_aid in acct_id_map.items():
            rows = KPIScore.query.filter_by(account_id=old_aid).all()
            for r in rows:
                new_row = KPIScore(
                    account_id=new_aid,
                    measurement_month=r.measurement_month,
                    kpi_code=r.kpi_code,
                    kpi_value=r.kpi_value,
                    kpi_target=r.kpi_target,
                    kpi_score=r.kpi_score,
                    kpi_status=r.kpi_status,
                    calculated_at=r.calculated_at,
                )
                db.session.add(new_row)
                kpi_score_count += 1
        summary['kpi_scores_cloned'] = kpi_score_count

        pillar_score_count = 0
        for old_aid, new_aid in acct_id_map.items():
            rows = PillarScore.query.filter_by(account_id=old_aid).all()
            for r in rows:
                new_row = PillarScore(
                    account_id=new_aid,
                    measurement_month=r.measurement_month,
                    pillar_code=r.pillar_code,
                    pillar_score=r.pillar_score,
                    pillar_status=r.pillar_status,
                    contributing_kpis=r.contributing_kpis,
                    kpi_weights=r.kpi_weights,
                    calculated_at=r.calculated_at,
                )
                db.session.add(new_row)
                pillar_score_count += 1
        summary['pillar_scores_cloned'] = pillar_score_count

        # ----------------------------------------------------------
        # 6. Clone Context Graph Nodes (has customer_id)
        # ----------------------------------------------------------
        source_nodes = ContextNode.query.filter_by(
            customer_id=source_customer_id,
        ).all()

        node_id_map = {}  # old_node_id -> new_node_id
        for node in source_nodes:
            new_account_id = acct_id_map.get(node.account_id)
            if new_account_id is None:
                continue  # Skip orphaned nodes
            new_node = ContextNode(
                customer_id=new_cid,
                account_id=new_account_id,
                node_type=node.node_type,
                node_subtype=node.node_subtype,
                tier=node.tier,
                title=node.title,
                properties=node.properties,
                revenue_impact=node.revenue_impact,
                revenue_impact_type=node.revenue_impact_type,
                confidence=node.confidence,
                source_platform=node.source_platform,
                source_event_id=node.source_event_id,
                source_ref=node.source_ref,
                occurred_at=node.occurred_at,
                expires_at=node.expires_at,
                weight_decay=node.weight_decay,
            )
            db.session.add(new_node)
            db.session.flush()  # Get new node_id for edge remapping
            node_id_map[node.node_id] = new_node.node_id

        summary['context_nodes_cloned'] = len(node_id_map)

        # ----------------------------------------------------------
        # 7. Clone Context Graph Edges (remap node IDs)
        # ----------------------------------------------------------
        edge_count = 0
        source_edges = ContextEdge.query.filter_by(
            customer_id=source_customer_id,
        ).all()
        for edge in source_edges:
            new_from = node_id_map.get(edge.from_node_id)
            new_to = node_id_map.get(edge.to_node_id)
            if new_from is None or new_to is None:
                continue  # Skip edges with unmapped nodes
            new_edge = ContextEdge(
                customer_id=new_cid,
                from_node_id=new_from,
                to_node_id=new_to,
                edge_type=edge.edge_type,
                lag_days=edge.lag_days,
                weight=edge.weight,
                confidence=edge.confidence,
                revenue_impact=edge.revenue_impact,
                revenue_impact_type=edge.revenue_impact_type,
                properties=edge.properties,
                source_platform=edge.source_platform,
                created_by=edge.created_by,
                occurred_at=edge.occurred_at,
                expires_at=edge.expires_at,
            )
            db.session.add(new_edge)
            edge_count += 1
        summary['context_edges_cloned'] = edge_count

        # ----------------------------------------------------------
        # 8. Clone Qualitative Signals (account_id based)
        # ----------------------------------------------------------
        signal_count = 0
        for old_aid, new_aid in acct_id_map.items():
            signals = QualitativeSignal.query.filter_by(account_id=old_aid).all()
            for sig in signals:
                new_sig = QualitativeSignal(
                    signal_id=f"clone_{_uuid_mod.uuid4().hex[:8]}_{sig.signal_id[-8:] if len(sig.signal_id) > 8 else sig.signal_id}",
                    account_id=new_aid,
                    signal_date=sig.signal_date,
                    signal_type=sig.signal_type,
                    content=sig.content,
                    sentiment=sig.sentiment,
                    stakeholder_level=sig.stakeholder_level,
                    stakeholder_title=sig.stakeholder_title,
                    sentiment_score=sig.sentiment_score,
                    keywords=sig.keywords,
                    is_narrative_signal=sig.is_narrative_signal,
                )
                db.session.add(new_sig)
                signal_count += 1
        summary['qualitative_signals_cloned'] = signal_count

        # ----------------------------------------------------------
        # 9. Clone Playbook Executions (has customer_id)
        # ----------------------------------------------------------
        pb_count = 0
        source_pbs = PlaybookExecution.query.filter_by(
            customer_id=source_customer_id,
        ).all()
        for pb in source_pbs:
            new_account_id = acct_id_map.get(pb.account_id) if pb.account_id else None
            new_exec_id = str(_uuid_mod.uuid4())
            new_pb = PlaybookExecution(
                execution_id=new_exec_id,
                customer_id=new_cid,
                account_id=new_account_id,
                playbook_id=pb.playbook_id,
                status=pb.status,
                current_step=pb.current_step,
                execution_data=pb.execution_data,
                started_at=pb.started_at,
                completed_at=pb.completed_at,
                execution_mode=pb.execution_mode,
                trigger_context=pb.trigger_context,
                outcome=pb.outcome,
                outcome_notes=pb.outcome_notes,
                llm_validation_result=pb.llm_validation_result,
            )
            db.session.add(new_pb)
            pb_count += 1
        summary['playbook_executions_cloned'] = pb_count

        # ----------------------------------------------------------
        # 10. Clone ROI Snapshots (has customer_id)
        # ----------------------------------------------------------
        roi_count = 0
        source_rois = ROISnapshot.query.filter_by(
            customer_id=source_customer_id,
        ).all()
        for roi in source_rois:
            new_roi = ROISnapshot(
                customer_id=new_cid,
                snapshot_date=roi.snapshot_date,
                improvement_pct=roi.improvement_pct,
                historical_roi_pct=roi.historical_roi_pct,
                historical_impact=roi.historical_impact,
                historical_investment=roi.historical_investment,
                forward_roi_pct=roi.forward_roi_pct,
                forward_impact=roi.forward_impact,
                forward_investment=roi.forward_investment,
                combined_roi_pct=roi.combined_roi_pct,
                total_arr=roi.total_arr,
                metric_details=roi.metric_details,
            )
            db.session.add(new_roi)
            roi_count += 1
        summary['roi_snapshots_cloned'] = roi_count

        # ----------------------------------------------------------
        # 11. Clone Journey Data (has customer_id + account_id)
        # ----------------------------------------------------------
        journey_count = 0
        for old_aid, new_aid in acct_id_map.items():
            journeys = JourneyData.query.filter_by(
                customer_id=source_customer_id,
                account_id=old_aid,
            ).all()
            for j in journeys:
                new_j = JourneyData(
                    customer_id=new_cid,
                    account_id=new_aid,
                    journey_json=j.journey_json,
                    total_weeks=j.total_weeks,
                    journey_pattern=j.journey_pattern,
                    generator_version=j.generator_version,
                    generated_at=j.generated_at,
                )
                db.session.add(new_j)
                journey_count += 1
        summary['journey_data_cloned'] = journey_count

        # ----------------------------------------------------------
        # 12. Create admin user for the new customer
        # ----------------------------------------------------------
        admin_user = None
        try:
            from models import User
            from werkzeug.security import generate_password_hash
            import secrets as _secrets
            admin_email = f"admin@{new_domain}"
            admin_password = _secrets.token_urlsafe(16)
            new_user = User(
                email=admin_email,
                user_name=f"Admin ({new_name})",
                customer_id=new_cid,
                role='admin',
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
                'user_id': new_user.user_id,
                'email': admin_email,
                'password': admin_password,
                'role': 'admin',
            }
            summary['admin_user_created'] = True
        except Exception as e:
            summary['admin_user_created'] = False
            summary['admin_user_error'] = str(e)

        # ----------------------------------------------------------
        # 13. Generate API key for the new customer
        # ----------------------------------------------------------
        api_key = None
        try:
            from api_key_service import generate_api_key as _gen_api_key
            full_key, _key_record = _gen_api_key(
                customer_id=new_cid,
                created_by=0,  # System-generated
                name='Clone Onboarding Key',
                scopes=['read', 'write'],
            )
            api_key = full_key
        except Exception:
            api_key = None

        # ----------------------------------------------------------
        # Commit the entire transaction atomically
        # ----------------------------------------------------------
        db.session.commit()

        # ----------------------------------------------------------
        # Build response
        # ----------------------------------------------------------
        total_records = (
            summary.get('accounts_cloned', 0)
            + summary.get('dc2s_kpis_cloned', 0)
            + summary.get('health_scores_cloned', 0)
            + summary.get('kpi_scores_cloned', 0)
            + summary.get('pillar_scores_cloned', 0)
            + summary.get('context_nodes_cloned', 0)
            + summary.get('context_edges_cloned', 0)
            + summary.get('qualitative_signals_cloned', 0)
            + summary.get('playbook_executions_cloned', 0)
            + summary.get('roi_snapshots_cloned', 0)
            + summary.get('journey_data_cloned', 0)
        )

        result = {
            'scope': 'customer',
            'status': 'cloned',
            'source_customer_id': source_customer_id,
            'new_customer_id': new_cid,
            'new_customer_name': new_name,
            'new_domain': new_domain,
            'vertical': source.vertical,
            'total_records_cloned': total_records,
            'details': summary,
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
            result['api_key_note'] = (
                'Save this API key — it is shown only once. '
                'Use it for the intelligence tools.'
            )

        if admin_user:
            result['admin_user'] = admin_user
            result['admin_user_note'] = (
                'Admin user auto-created. Use these credentials to log in.'
            )

        result['next_steps'] = (
            'OPTION 1 — Use as-is: Clone is ready immediately. '
            'All data (accounts, KPIs, health scores, context graph, '
            'signals, playbooks, ROI) has been deep-copied with '
            'pre-calculated scores. No Wizards or process_data needed. '
            'OPTION 2 — Customize: Use export_customer_csvs() to download '
            'the 8 CSVs, modify them (change account names, KPI values, etc.), '
            'then upload_csv() + process_data() to recalculate scores '
            'with your changes. Wizards A/B/C only needed if you want '
            'to regenerate journeys or recalibrate weights.'
        )

        # Include canonical pillar labels so LLM clients display correct names
        result['dc2s_pillar_labels'] = common.get_pillar_labels('dc2_s')

        return result


# ===================================================================
# Tool: export_customer_csvs — Export all customer data as CSVs
# ===================================================================

@mcp.tool
def export_customer_csvs(
    customer_id: int,
    output_dir: str = '',
) -> dict:
    """Export all data for a customer as CSV files matching the onboarding upload format.

    Produces CSVs that can be re-uploaded via upload_csv() + process_data()
    without any transformation. Useful for cloning, backup, or data migration.

    No authentication required (onboarding tool).

    Exported files (8 customer-provided CSVs matching config/csv_schemas.json):
      Regular model: accounts.csv, kpi_measurements.csv, enhanced_qualitative_signals.csv, products.csv
      Context graph: stakeholders.csv, engagement_events.csv, account_business_profiles.csv, outcomes.csv

    Note: The 3 auto-generated files (decisions.csv, signal_edges.csv, industry_benchmarks.csv)
    are NOT exported — they get regenerated by process_data() from the uploaded data.

    Args:
        customer_id: Customer ID to export data from
        output_dir: Directory to save CSVs. Default: /tmp/cs_pulse_export_{customer_id}/
    """
    common.check_mcp_enabled()
    app = common.get_flask_app()

    with app.app_context():
        import csv
        import io
        from pathlib import Path
        from models import (
            Customer, Account, DC2SKPI, Product,
            QualitativeSignal, ContextNode,
        )
        from extensions import db

        # ----------------------------------------------------------
        # Validate customer
        # ----------------------------------------------------------
        customer = db.session.get(Customer, int(customer_id))
        if not customer:
            raise ToolError(f"Customer {customer_id} not found.")

        # Resolve output directory
        if not output_dir:
            output_dir = f'/tmp/cs_pulse_export_{customer_id}'
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        # ----------------------------------------------------------
        # Helper: write rows to CSV
        # ----------------------------------------------------------
        def _write_csv(filename: str, columns: list, rows: list) -> int:
            """Write rows to a CSV file. Returns row count."""
            fp = out_path / filename
            with open(fp, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=columns, extrasaction='ignore')
                writer.writeheader()
                for row in rows:
                    writer.writerow(row)
            return len(rows)

        # ----------------------------------------------------------
        # Load all accounts for this customer (needed for joins)
        # ----------------------------------------------------------
        accounts = Account.query.filter_by(customer_id=int(customer_id)).all()
        account_ids = [a.account_id for a in accounts]
        # Build account_id -> account_name lookup
        acct_name_map = {a.account_id: a.account_name for a in accounts}

        results = {}

        # ----------------------------------------------------------
        # 1. accounts.csv
        # ----------------------------------------------------------
        acct_cols = [
            'source_account_id', 'customer_id', 'account_name', 'industry', 'region',
            'vertical', 'tier', 'arr', 'revenue', 'contract_start', 'contract_end',
            'renewal_date', 'csm_name', 'csm_email', 'account_status', 'uuid',
        ]
        acct_rows = []
        for a in accounts:
            pm = a.profile_metadata or {}
            acct_rows.append({
                'source_account_id': a.account_id,
                'customer_id': a.customer_id,
                'account_name': a.account_name,
                'industry': a.industry,
                'region': a.region,
                'vertical': a.vertical,
                'tier': pm.get('tier', ''),
                'arr': pm.get('arr', '') or (float(a.revenue) if a.revenue else ''),
                'revenue': float(a.revenue) if a.revenue else '',
                'contract_start': pm.get('contract_start', ''),
                'contract_end': pm.get('contract_end', ''),
                'renewal_date': pm.get('renewal_date', ''),
                'csm_name': pm.get('assigned_csm', '') or pm.get('csm_name', ''),
                'csm_email': pm.get('csm_email', ''),
                'account_status': a.account_status,
                'uuid': a.uuid or '',
            })
        results['accounts.csv'] = _write_csv('accounts.csv', acct_cols, acct_rows)

        # ----------------------------------------------------------
        # 2. kpi_measurements.csv
        # ----------------------------------------------------------
        kpi_cols = [
            'source_account_id', 'kpi_code', 'measured_at', 'value',
            'kpi_name', 'pillar', 'target', 'weight', 'unit', 'status',
        ]
        kpi_rows = []
        if account_ids:
            kpis = DC2SKPI.query.filter(DC2SKPI.account_id.in_(account_ids)).all()
            for k in kpis:
                kpi_rows.append({
                    'source_account_id': k.account_id,
                    'kpi_code': k.kpi_code,
                    'measured_at': k.measured_at.isoformat() if k.measured_at else '',
                    'value': float(k.value),
                    'kpi_name': '',
                    'pillar': k.pillar or '',
                    'target': float(k.target) if k.target else '',
                    'weight': float(k.weight) if k.weight else '',
                    'unit': '',
                    'status': k.status or '',
                })
        results['kpi_measurements.csv'] = _write_csv('kpi_measurements.csv', kpi_cols, kpi_rows)

        # ----------------------------------------------------------
        # 3. enhanced_qualitative_signals.csv
        # ----------------------------------------------------------
        qs_cols = [
            'source_account_id', 'signal_date', 'signal_type', 'content', 'sentiment',
            'signal_ref', 'sentiment_score', 'stakeholder_name', 'stakeholder_title',
            'causal_chain_ref', 'revenue_impact', 'confidence', 'source_platform',
        ]
        qs_rows = []
        if account_ids:
            signals = QualitativeSignal.query.filter(
                QualitativeSignal.account_id.in_(account_ids)
            ).all()
            for s in signals:
                qs_rows.append({
                    'source_account_id': s.account_id,
                    'signal_date': s.signal_date.isoformat() if s.signal_date else '',
                    'signal_type': s.signal_type or '',
                    'content': s.content or '',
                    'sentiment': s.sentiment or '',
                    'signal_ref': s.signal_id or '',
                    'sentiment_score': float(s.sentiment_score) if s.sentiment_score else '',
                    'stakeholder_name': '',
                    'stakeholder_title': s.stakeholder_title or '',
                    'causal_chain_ref': '',
                    'revenue_impact': '',
                    'confidence': '',
                    'source_platform': '',
                })
        results['enhanced_qualitative_signals.csv'] = _write_csv(
            'enhanced_qualitative_signals.csv', qs_cols, qs_rows
        )

        # ----------------------------------------------------------
        # 4. products.csv
        # ----------------------------------------------------------
        prod_cols = [
            'source_account_id', 'product_name', 'product_category', 'quantity',
            'unit_price', 'deployment_date', 'status', 'customer_id',
        ]
        prod_rows = []
        if account_ids:
            products = Product.query.filter(Product.account_id.in_(account_ids)).all()
            for p in products:
                prod_rows.append({
                    'source_account_id': p.account_id,
                    'product_name': p.product_name,
                    'product_category': p.product_type or '',
                    'quantity': '',
                    'unit_price': float(p.revenue) if p.revenue else '',
                    'deployment_date': '',
                    'status': p.status or '',
                    'customer_id': p.customer_id,
                })
        results['products.csv'] = _write_csv('products.csv', prod_cols, prod_rows)

        # ----------------------------------------------------------
        # Context Graph CSVs — from context_nodes table
        # ----------------------------------------------------------
        ctx_nodes = []
        if account_ids:
            ctx_nodes = ContextNode.query.filter(
                ContextNode.account_id.in_(account_ids)
            ).all()

        # Group nodes by type
        nodes_by_type = {}
        for n in ctx_nodes:
            nodes_by_type.setdefault(n.node_type, []).append(n)

        # ----------------------------------------------------------
        # 5. stakeholders.csv (node_type=STAKEHOLDER)
        # ----------------------------------------------------------
        sh_cols = [
            'source_account_id', 'stakeholder_name', 'title', 'role', 'influence_score',
            'email', 'engagement_frequency', 'sentiment', 'department',
            'is_active', 'source_platform', 'first_observed_at',
        ]
        sh_rows = []
        for n in nodes_by_type.get('STAKEHOLDER', []):
            props = n.properties or {}
            sh_rows.append({
                'source_account_id': n.account_id,
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
        results['stakeholders.csv'] = _write_csv('stakeholders.csv', sh_cols, sh_rows)

        # ----------------------------------------------------------
        # 6. engagement_events.csv (node_type=SIGNAL, subtype=engagement)
        # ----------------------------------------------------------
        ee_cols = [
            'source_account_id', 'event_date', 'event_type', 'description',
            'stakeholder_name', 'sentiment_shift', 'channel',
            'duration_minutes', 'outcome', 'source_platform',
        ]
        ee_rows = []
        for n in nodes_by_type.get('SIGNAL', []):
            props = n.properties or {}
            # Include all SIGNAL nodes as engagement events
            ee_rows.append({
                'source_account_id': n.account_id,
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
        results['engagement_events.csv'] = _write_csv('engagement_events.csv', ee_cols, ee_rows)

        # ----------------------------------------------------------
        # 7. account_business_profiles.csv (node_type=ACCOUNT)
        # ----------------------------------------------------------
        abp_cols = [
            'source_account_id', 'arr', 'industry', 'employee_count',
            'fiscal_year_end', 'tech_stack', 'cloud_provider',
            'competitive_landscape', 'strategic_initiatives', 'budget_cycle',
            'profile_date', 'assigned_csm', 'csm_manager', 'executive_sponsor',
            'mrr', 'primary_champion_name', 'primary_champion_title',
            'primary_champion_email', 'primary_champion_engagement_score',
            'last_updated',
        ]
        abp_rows = []
        # If no ACCOUNT nodes, build from the accounts table profile_metadata
        account_nodes = nodes_by_type.get('ACCOUNT', [])
        if account_nodes:
            for n in account_nodes:
                props = n.properties or {}
                abp_rows.append({
                    'source_account_id': n.account_id,
                    'arr': props.get('arr', ''),
                    'industry': props.get('industry', ''),
                    'employee_count': props.get('employee_count', ''),
                    'fiscal_year_end': props.get('fiscal_year_end', ''),
                    'tech_stack': props.get('tech_stack', ''),
                    'cloud_provider': props.get('cloud_provider', ''),
                    'competitive_landscape': props.get('competitive_landscape', ''),
                    'strategic_initiatives': props.get('strategic_initiatives', ''),
                    'budget_cycle': props.get('budget_cycle', ''),
                    'profile_date': n.occurred_at.isoformat() if n.occurred_at else '',
                    'assigned_csm': props.get('assigned_csm', ''),
                    'csm_manager': props.get('csm_manager', ''),
                    'executive_sponsor': props.get('executive_sponsor', ''),
                    'mrr': props.get('mrr', ''),
                    'primary_champion_name': props.get('primary_champion_name', ''),
                    'primary_champion_title': props.get('primary_champion_title', ''),
                    'primary_champion_email': props.get('primary_champion_email', ''),
                    'primary_champion_engagement_score': props.get('primary_champion_engagement_score', ''),
                    'last_updated': n.updated_at.isoformat() if n.updated_at else '',
                })
        else:
            # Fallback: build from accounts table profile_metadata
            for a in accounts:
                pm = a.profile_metadata or {}
                abp_rows.append({
                    'source_account_id': a.account_id,
                    'arr': pm.get('arr', '') or (float(a.revenue) if a.revenue else ''),
                    'industry': a.industry or '',
                    'employee_count': pm.get('employee_count', ''),
                    'fiscal_year_end': pm.get('fiscal_year_end', ''),
                    'tech_stack': pm.get('tech_stack', ''),
                    'cloud_provider': pm.get('cloud_provider', ''),
                    'competitive_landscape': pm.get('competitive_landscape', ''),
                    'strategic_initiatives': pm.get('strategic_initiatives', ''),
                    'budget_cycle': pm.get('budget_cycle', ''),
                    'profile_date': '',
                    'assigned_csm': pm.get('assigned_csm', ''),
                    'csm_manager': pm.get('csm_manager', ''),
                    'executive_sponsor': pm.get('executive_sponsor', ''),
                    'mrr': pm.get('mrr', ''),
                    'primary_champion_name': pm.get('primary_champion_name', ''),
                    'primary_champion_title': pm.get('primary_champion_title', ''),
                    'primary_champion_email': pm.get('primary_champion_email', ''),
                    'primary_champion_engagement_score': pm.get('primary_champion_engagement_score', ''),
                    'last_updated': a.updated_at.isoformat() if a.updated_at else '',
                })
        results['account_business_profiles.csv'] = _write_csv(
            'account_business_profiles.csv', abp_cols, abp_rows
        )

        # ----------------------------------------------------------
        # 8. outcomes.csv (node_type=OUTCOME)
        # ----------------------------------------------------------
        out_cols = [
            'source_account_id', 'outcome_date', 'title', 'outcome_type', 'revenue_value',
            'outcome_id', 'evidence', 'confidence', 'related_decision_id',
            'source_platform',
        ]
        out_rows = []
        for n in nodes_by_type.get('OUTCOME', []):
            props = n.properties or {}
            out_rows.append({
                'source_account_id': n.account_id,
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
        results['outcomes.csv'] = _write_csv('outcomes.csv', out_cols, out_rows)

        # ----------------------------------------------------------
        # Build response
        # NOTE: decisions.csv, signal_edges.csv, industry_benchmarks.csv
        # are auto-generated by process_data() — not exported here.
        # ----------------------------------------------------------
        files_created = [
            {'file': name, 'rows': count, 'path': str(out_path / name)}
            for name, count in results.items()
            if count > 0
        ]
        total_rows = sum(results.values())
        all_files = [
            {'file': name, 'rows': count, 'path': str(out_path / name)}
            for name, count in results.items()
        ]

        return {
            'scope': 'customer',
            'customer_id': customer_id,
            'customer_name': customer.customer_name,
            'output_dir': str(out_path),
            'files_with_data': len(files_created),
            'total_files': len(all_files),
            'total_rows': total_rows,
            'files': all_files,
            'message': (
                f"Exported {total_rows} rows across {len(files_created)} files "
                f"(of {len(all_files)} total) to {out_path}. "
                f"Re-upload via upload_csv() + process_data(). "
                f"NOTE: If you cannot access these files (e.g. Claude.ai), "
                f"use download_customer_csv() instead — it returns CSV content inline."
            ),
        }


# ===================================================================
# Tool: download_customer_csv — Return CSV content inline for download
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
    common.check_mcp_enabled()
    app = common.get_flask_app()

    with app.app_context():
        import csv
        import io
        from models import (
            Customer, Account, DC2SKPI, Product,
            QualitativeSignal, ContextNode,
        )
        from extensions import db

        # Validate customer
        customer = db.session.get(Customer, int(customer_id))
        if not customer:
            raise ToolError(f"Customer {customer_id} not found.")

        # Load accounts
        accounts = Account.query.filter_by(customer_id=int(customer_id)).all()
        account_ids = [a.account_id for a in accounts]

        # Helper: build CSV string in memory
        def _csv_string(columns: list, rows: list) -> str:
            buf = io.StringIO()
            writer = csv.DictWriter(buf, fieldnames=columns, extrasaction='ignore')
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
            return buf.getvalue()

        # Map of file_type -> (generator_function)
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

        # ---- accounts ----
        if 'accounts' in requested:
            cols = [
                'source_account_id', 'customer_id', 'account_name', 'industry', 'region',
                'vertical', 'tier', 'arr', 'revenue', 'contract_start', 'contract_end',
                'renewal_date', 'csm_name', 'csm_email', 'account_status', 'uuid',
            ]
            rows = []
            for a in accounts:
                pm = a.profile_metadata or {}
                rows.append({
                    'source_account_id': a.account_id,
                    'customer_id': a.customer_id,
                    'account_name': a.account_name,
                    'industry': a.industry,
                    'region': a.region,
                    'vertical': a.vertical,
                    'tier': pm.get('tier', ''),
                    'arr': pm.get('arr', '') or (float(a.revenue) if a.revenue else ''),
                    'revenue': float(a.revenue) if a.revenue else '',
                    'contract_start': pm.get('contract_start', ''),
                    'contract_end': pm.get('contract_end', ''),
                    'renewal_date': pm.get('renewal_date', ''),
                    'csm_name': pm.get('assigned_csm', '') or pm.get('csm_name', ''),
                    'csm_email': pm.get('csm_email', ''),
                    'account_status': a.account_status,
                    'uuid': a.uuid or '',
                })
            csvs['accounts.csv'] = {'content': _csv_string(cols, rows), 'rows': len(rows)}

        # ---- kpi_measurements ----
        if 'kpi_measurements' in requested:
            cols = [
                'source_account_id', 'kpi_code', 'measured_at', 'value',
                'kpi_name', 'pillar', 'target', 'weight', 'unit', 'status',
            ]
            rows = []
            if account_ids:
                kpis = DC2SKPI.query.filter(DC2SKPI.account_id.in_(account_ids)).all()
                for k in kpis:
                    rows.append({
                        'source_account_id': k.account_id,
                        'kpi_code': k.kpi_code,
                        'measured_at': k.measured_at.isoformat() if k.measured_at else '',
                        'value': float(k.value),
                        'kpi_name': '',
                        'pillar': k.pillar or '',
                        'target': float(k.target) if k.target else '',
                        'weight': float(k.weight) if k.weight else '',
                        'unit': '',
                        'status': k.status or '',
                    })
            csvs['kpi_measurements.csv'] = {'content': _csv_string(cols, rows), 'rows': len(rows)}

        # ---- signals ----
        if 'signals' in requested:
            cols = [
                'source_account_id', 'signal_date', 'signal_type', 'content', 'sentiment',
                'signal_ref', 'sentiment_score', 'stakeholder_name', 'stakeholder_title',
                'causal_chain_ref', 'revenue_impact', 'confidence', 'source_platform',
            ]
            rows = []
            if account_ids:
                signals = QualitativeSignal.query.filter(
                    QualitativeSignal.account_id.in_(account_ids)
                ).all()
                for s in signals:
                    rows.append({
                        'source_account_id': s.account_id,
                        'signal_date': s.signal_date.isoformat() if s.signal_date else '',
                        'signal_type': s.signal_type or '',
                        'content': s.content or '',
                        'sentiment': s.sentiment or '',
                        'signal_ref': s.signal_id or '',
                        'sentiment_score': float(s.sentiment_score) if s.sentiment_score else '',
                        'stakeholder_name': '',
                        'stakeholder_title': s.stakeholder_title or '',
                        'causal_chain_ref': '',
                        'revenue_impact': '',
                        'confidence': '',
                        'source_platform': '',
                    })
            csvs['enhanced_qualitative_signals.csv'] = {'content': _csv_string(cols, rows), 'rows': len(rows)}

        # ---- products ----
        if 'products' in requested:
            cols = [
                'source_account_id', 'product_name', 'product_category', 'quantity',
                'unit_price', 'deployment_date', 'status', 'customer_id',
            ]
            rows = []
            if account_ids:
                products = Product.query.filter(Product.account_id.in_(account_ids)).all()
                for p in products:
                    rows.append({
                        'source_account_id': p.account_id,
                        'product_name': p.product_name,
                        'product_category': p.product_type or '',
                        'quantity': '',
                        'unit_price': float(p.revenue) if p.revenue else '',
                        'deployment_date': '',
                        'status': p.status or '',
                        'customer_id': p.customer_id,
                    })
            csvs['products.csv'] = {'content': _csv_string(cols, rows), 'rows': len(rows)}

        # ---- Context graph CSVs ----
        ctx_nodes = []
        if account_ids and any(t in requested for t in ['stakeholders', 'engagement_events', 'profiles', 'outcomes']):
            ctx_nodes = ContextNode.query.filter(
                ContextNode.account_id.in_(account_ids)
            ).all()

        nodes_by_type = {}
        for n in ctx_nodes:
            nodes_by_type.setdefault(n.node_type, []).append(n)

        # ---- stakeholders ----
        if 'stakeholders' in requested:
            cols = [
                'source_account_id', 'stakeholder_name', 'title', 'role', 'influence_score',
                'email', 'engagement_frequency', 'sentiment', 'department',
                'is_active', 'source_platform', 'first_observed_at',
            ]
            rows = []
            for n in nodes_by_type.get('STAKEHOLDER', []):
                props = n.properties or {}
                rows.append({
                    'source_account_id': n.account_id,
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

        # ---- engagement_events ----
        if 'engagement_events' in requested:
            cols = [
                'source_account_id', 'event_date', 'event_type', 'description',
                'stakeholder_name', 'sentiment_shift', 'channel',
                'duration_minutes', 'outcome', 'source_platform',
            ]
            rows = []
            for n in nodes_by_type.get('SIGNAL', []):
                props = n.properties or {}
                rows.append({
                    'source_account_id': n.account_id,
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

        # ---- profiles ----
        if 'profiles' in requested:
            cols = [
                'source_account_id', 'arr', 'industry', 'employee_count',
                'fiscal_year_end', 'tech_stack', 'cloud_provider',
                'competitive_landscape', 'strategic_initiatives', 'budget_cycle',
                'profile_date', 'assigned_csm', 'csm_manager', 'executive_sponsor',
                'mrr', 'primary_champion_name', 'primary_champion_title',
                'primary_champion_email', 'primary_champion_engagement_score',
                'last_updated',
            ]
            rows = []
            account_nodes = nodes_by_type.get('ACCOUNT', [])
            if account_nodes:
                for n in account_nodes:
                    props = n.properties or {}
                    rows.append({
                        'source_account_id': n.account_id,
                        'arr': props.get('arr', ''),
                        'industry': props.get('industry', ''),
                        'employee_count': props.get('employee_count', ''),
                        'fiscal_year_end': props.get('fiscal_year_end', ''),
                        'tech_stack': props.get('tech_stack', ''),
                        'cloud_provider': props.get('cloud_provider', ''),
                        'competitive_landscape': props.get('competitive_landscape', ''),
                        'strategic_initiatives': props.get('strategic_initiatives', ''),
                        'budget_cycle': props.get('budget_cycle', ''),
                        'profile_date': n.occurred_at.isoformat() if n.occurred_at else '',
                        'assigned_csm': props.get('assigned_csm', ''),
                        'csm_manager': props.get('csm_manager', ''),
                        'executive_sponsor': props.get('executive_sponsor', ''),
                        'mrr': props.get('mrr', ''),
                        'primary_champion_name': props.get('primary_champion_name', ''),
                        'primary_champion_title': props.get('primary_champion_title', ''),
                        'primary_champion_email': props.get('primary_champion_email', ''),
                        'primary_champion_engagement_score': props.get('primary_champion_engagement_score', ''),
                        'last_updated': n.updated_at.isoformat() if n.updated_at else '',
                    })
            else:
                for a in accounts:
                    pm = a.profile_metadata or {}
                    rows.append({
                        'source_account_id': a.account_id,
                        'arr': pm.get('arr', '') or (float(a.revenue) if a.revenue else ''),
                        'industry': a.industry or '',
                        'employee_count': pm.get('employee_count', ''),
                        'fiscal_year_end': pm.get('fiscal_year_end', ''),
                        'tech_stack': pm.get('tech_stack', ''),
                        'cloud_provider': pm.get('cloud_provider', ''),
                        'competitive_landscape': pm.get('competitive_landscape', ''),
                        'strategic_initiatives': pm.get('strategic_initiatives', ''),
                        'budget_cycle': pm.get('budget_cycle', ''),
                        'profile_date': '',
                        'assigned_csm': pm.get('assigned_csm', ''),
                        'csm_manager': pm.get('csm_manager', ''),
                        'executive_sponsor': pm.get('executive_sponsor', ''),
                        'mrr': pm.get('mrr', ''),
                        'primary_champion_name': pm.get('primary_champion_name', ''),
                        'primary_champion_title': pm.get('primary_champion_title', ''),
                        'primary_champion_email': pm.get('primary_champion_email', ''),
                        'primary_champion_engagement_score': pm.get('primary_champion_engagement_score', ''),
                        'last_updated': a.updated_at.isoformat() if a.updated_at else '',
                    })
            csvs['account_business_profiles.csv'] = {'content': _csv_string(cols, rows), 'rows': len(rows)}

        # ---- outcomes ----
        if 'outcomes' in requested:
            cols = [
                'source_account_id', 'outcome_date', 'title', 'outcome_type', 'revenue_value',
                'outcome_id', 'evidence', 'confidence', 'related_decision_id',
                'source_platform',
            ]
            rows = []
            for n in nodes_by_type.get('OUTCOME', []):
                props = n.properties or {}
                rows.append({
                    'source_account_id': n.account_id,
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

        # Build response
        total_rows = sum(f['rows'] for f in csvs.values())
        files_summary = [
            {'file': name, 'rows': info['rows']}
            for name, info in csvs.items()
        ]

        result = {
            'scope': 'customer',
            'customer_id': customer_id,
            'customer_name': customer.customer_name,
            'file_type': file_type,
            'total_files': len(csvs),
            'total_rows': total_rows,
            'files': files_summary,
            'message': (
                f"Downloaded {total_rows} rows across {len(csvs)} CSV(s) for "
                f"{customer.customer_name}. CSV content is in the 'csv_data' field. "
                f"Save each file using the filename as key."
            ),
            'csv_data': {
                name: info['content']
                for name, info in csvs.items()
            },
        }

        # For single file, also put content at top level for easy access
        if file_type != 'all' and len(csvs) == 1:
            fname = list(csvs.keys())[0]
            result['filename'] = fname
            result['csv_content'] = csvs[fname]['content']

        return result


# ===================================================================
# Entrypoint
# ===================================================================
if __name__ == "__main__":
    common.run_server(mcp, default_port=8004)
