#!/usr/bin/env python3
"""
Data Quality API
Provides report of common data hygiene issues and remediation helpers
"""

from flask import Blueprint, jsonify
from extensions import db
from models import Account, Product, KPI
from sqlalchemy import and_
from collections import defaultdict
import re

data_quality_api = Blueprint('data_quality_api', __name__)


def _parse_percent(value: str):
    try:
        if value is None:
            return None
        s = str(value).strip()
        if s.endswith('%'):
            s = s[:-1]
        return float(s)
    except Exception:
        return None


@data_quality_api.route('/api/data-quality/report', methods=['GET'])
def get_data_quality_report():
    """Return a summary of data hygiene issues per account."""
    accounts = Account.query.all()
    report = []

    for acct in accounts:
        issues = {
            'account_id': acct.account_id,
            'account_name': acct.account_name,
            'products_count': len(acct.products or []),
            'duplicate_account_level_params': [],
            'percent_out_of_range': [],
            'aggregates_in_primary_view': False,
        }

        # Account-level KPIs (product_id is NULL)
        account_level = KPI.query.filter(
            KPI.account_id == acct.account_id,
            KPI.product_id.is_(None)
        ).all()

        # Duplicates per parameter (considering primary view types)
        primary_types = {None, 'weighted_avg'}
        counts = defaultdict(int)
        for k in account_level:
            if k.aggregation_type in primary_types:
                counts[k.kpi_parameter] += 1
            if k.aggregation_type in {'min', 'max', 'sum', 'equal_weight'}:
                issues['aggregates_in_primary_view'] = True

            # Percent out of range simple check
            if isinstance(k.data, str) and k.data.strip().endswith('%'):
                v = _parse_percent(k.data)
                if v is not None and (v < 0 or v > 100):
                    issues['percent_out_of_range'].append({
                        'kpi_id': k.kpi_id,
                        'kpi_parameter': k.kpi_parameter,
                        'value': k.data
                    })

        issues['duplicate_account_level_params'] = [
            param for param, c in counts.items() if c > 1
        ]

        report.append(issues)

    summary = {
        'total_accounts': len(accounts),
        'accounts_with_no_products': sum(1 for r in report if r['products_count'] == 0),
        'accounts_with_duplicates': sum(1 for r in report if len(r['duplicate_account_level_params']) > 0),
        'accounts_with_out_of_range_percent': sum(1 for r in report if len(r['percent_out_of_range']) > 0),
        'accounts_with_aggregates_in_primary': sum(1 for r in report if r['aggregates_in_primary_view']),
    }

    return jsonify({
        'summary': summary,
        'details': report,
    })


@data_quality_api.route('/api/data-quality/fix/seed-missing-products', methods=['POST'])
def seed_missing_products():
    """Ensure every account has at least one product by seeding a default."""
    accounts = Account.query.all()
    created = 0
    for acct in accounts:
        if len(acct.products or []) == 0:
            p = Product(
                account_id=acct.account_id,
                customer_id=acct.customer_id,
                product_name=f"Default Product for {acct.account_name}"
            )
            db.session.add(p)
            created += 1
    if created > 0:
        db.session.commit()
    return jsonify({'status': 'success', 'created_products': created})

@data_quality_api.route('/api/data-quality/fix/dedupe-account-level', methods=['POST'])
def dedupe_account_level_kpis():
    """
    De-duplicate Account Level KPIs across ALL accounts:
    Keep a single primary row per (account_id, kpi_parameter) with precedence:
      1) aggregation_type='weighted_avg'
      2) else latest legacy (aggregation_type=NULL) by highest kpi_id
    Remove other duplicates among primary types. Aggregates (min/max/sum/equal_weight) are untouched.
    """
    primary_types = {None, 'weighted_avg'}
    removed = 0
    kept = 0
    accounts = Account.query.all()
    for acct in accounts:
        # Fetch only account-level KPIs
        rows = KPI.query.filter(
            KPI.account_id == acct.account_id,
            KPI.product_id.is_(None)
        ).all()
        # Group by kpi_parameter considering only primary types
        by_param = defaultdict(list)
        for k in rows:
            if k.aggregation_type in primary_types:
                by_param[k.kpi_parameter].append(k)
        # For each parameter decide the keeper and delete the rest
        for param, group in by_param.items():
            if not group:
                continue
            # Prefer weighted_avg
            weighted = [k for k in group if k.aggregation_type == 'weighted_avg']
            if weighted:
                # Keep the latest weighted_avg (highest kpi_id), delete other primary duplicates
                keep_one = max(weighted, key=lambda x: x.kpi_id or 0)
            else:
                # Keep latest legacy NULL
                legacy = [k for k in group if k.aggregation_type is None]
                keep_one = max(legacy, key=lambda x: x.kpi_id or 0)
            # Delete others within primary group
            for k in group:
                if k.kpi_id != keep_one.kpi_id:
                    db.session.delete(k)
                    removed += 1
            kept += 1
    if removed > 0:
        db.session.commit()
    return jsonify({'status': 'success', 'kept': kept, 'removed': removed})


