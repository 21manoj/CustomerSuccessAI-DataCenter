#!/usr/bin/env python3
"""
Data Quality API
Provides report of common data hygiene issues and remediation helpers.
Includes KPI range validation: discrepancies between uploaded KPI values
and defined reference ranges (DC2_S KPI definitions).
"""

from flask import Blueprint, jsonify
from extensions import db
from models import Account, Product, KPI, DC2SKPI
from sqlalchemy import and_, text
from auth_middleware import get_current_customer_id
from collections import defaultdict
import re

data_quality_api = Blueprint('data_quality_api', __name__)


def _get_dc2s_kpi_ranges():
    """Load DC2_S KPI definitions and return (valid_min, valid_max) per kpi_code (union of healthy/risk/critical)."""
    try:
        from verticals.dc2_s.kpi_definitions import DC2S_KPIS
    except ImportError:
        return {}
    out = {}
    for kpi_code, defn in DC2S_KPIS.items():
        ranges = defn.get('ranges') or {}
        mins, maxs = [], []
        for band in ('healthy', 'risk', 'critical'):
            r = ranges.get(band, {})
            if isinstance(r.get('min'), (int, float)):
                mins.append(float(r['min']))
            if isinstance(r.get('max'), (int, float)):
                maxs.append(float(r['max']))
        if mins and maxs:
            out[kpi_code] = {'min': min(mins), 'max': max(maxs), 'name': defn.get('name', kpi_code), 'unit': defn.get('unit', '')}
    return out


def _normalize_kpi_code(kpi_code, dc2s_codes):
    """Validate kpi_code exists in dc2s_codes. Returns kpi_code or None."""
    return kpi_code if kpi_code in dc2s_codes else None


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
    customer_id = get_current_customer_id()
    if not customer_id:
        return jsonify({'error': 'Customer ID required'}), 400
    accounts = Account.query.filter_by(customer_id=int(customer_id)).all()
    report = []

    for acct in accounts:
        issues = {
            'account_id': acct.account_id,
            'account_name': acct.account_name,
            'products_count': 0,
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


@data_quality_api.route('/api/data-quality/kpi-range-discrepancies', methods=['GET'])
def get_kpi_range_discrepancies():
    """
    GET /api/data-quality/kpi-range-discrepancies
    Returns KPI measurements that fall outside defined reference ranges (DC2_S).
    Tenant-scoped: only customer's accounts. Use to ensure nothing enters the system
    (onboarding or manual CSV) that disagrees with KPI ranges.
    """
    try:
        customer_id = get_current_customer_id()
        if not customer_id:
            return jsonify({'status': 'error', 'message': 'Authentication required'}), 401
        customer_id = int(customer_id)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 401

    ranges_map = _get_dc2s_kpi_ranges()
    if not ranges_map:
        return jsonify({
            'summary': {'total_checked': 0, 'out_of_range_count': 0, 'accounts_affected': 0},
            'discrepancies': [],
            'message': 'No DC2_S KPI range definitions available'
        })

    # dc2s_kpis for this customer's accounts
    account_ids = db.session.query(Account.account_id).filter(Account.customer_id == customer_id).all()
    account_ids = [a[0] for a in account_ids]
    if not account_ids:
        return jsonify({
            'summary': {'total_checked': 0, 'out_of_range_count': 0, 'accounts_affected': 0},
            'discrepancies': []
        })

    kpis = DC2SKPI.query.filter(DC2SKPI.account_id.in_(account_ids)).all()
    account_names = {a.account_id: a.account_name for a in Account.query.filter(Account.account_id.in_(account_ids)).all()}

    discrepancies = []
    for row in kpis:
        try:
            val = float(row.value)
        except (TypeError, ValueError):
            discrepancies.append({
                'account_id': row.account_id,
                'account_name': account_names.get(row.account_id, ''),
                'kpi_code': row.kpi_code,
                'kpi_name': row.kpi_code,
                'value': str(row.value),
                'expected_min': None,
                'expected_max': None,
                'unit': '',
                'severity': 'invalid_value'
            })
            continue
        lookup = _normalize_kpi_code(row.kpi_code, ranges_map) or row.kpi_code
        r = ranges_map.get(lookup)
        if not r:
            continue
        lo, hi = r['min'], r['max']
        if val < lo or val > hi:
            discrepancies.append({
                'account_id': row.account_id,
                'account_name': account_names.get(row.account_id, ''),
                'kpi_code': row.kpi_code,
                'kpi_name': r.get('name', row.kpi_code),
                'value': val,
                'expected_min': lo,
                'expected_max': hi,
                'unit': r.get('unit', ''),
                'severity': 'out_of_range'
            })

    accounts_affected = len({d['account_id'] for d in discrepancies})
    return jsonify({
        'summary': {
            'total_checked': len(kpis),
            'out_of_range_count': len(discrepancies),
            'accounts_affected': accounts_affected
        },
        'discrepancies': discrepancies
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


