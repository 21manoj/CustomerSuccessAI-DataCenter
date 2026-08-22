#!/usr/bin/env python3
"""
SaaS Premium API Routes
========================
Thin wrapper over the generic scorer — delegates all scoring to
utils/generic_scorer.py + saas_premium_kpi_catalog.json.

No custom scoring logic. SaaS Premium is proof that new verticals
only need a JSON catalog, not Python code.

Endpoints:
  GET  /api/saas/accounts         — List accounts with health scores
  GET  /api/saas/health-summary   — Portfolio health summary
  GET  /api/saas/kpi-catalog      — SaaS Premium KPI catalog
"""

import logging
from flask import Blueprint, jsonify

from auth_middleware import get_current_customer_id
from extensions import db
from models import Account, HealthScore, DC2SKPI
from utils.generic_scorer import score_account_health
from utils.vertical_registry import get_pillars, get_kpis
import utils.health_thresholds as ht

logger = logging.getLogger(__name__)

saas_premium_api = Blueprint('saas_premium_api', __name__)


@saas_premium_api.route('/accounts', methods=['GET'])
def list_saas_accounts():
    """List all SaaS Premium accounts with health scores."""
    try:
        customer_id = get_current_customer_id()
        if not customer_id:
            return jsonify({'error': 'Authentication required'}), 401

        accounts = Account.query.filter_by(customer_id=customer_id).all()

        result = []
        for acct in accounts:
            # Get pre-calculated health score
            hs = (HealthScore.query
                  .filter_by(account_id=acct.account_id)
                  .order_by(HealthScore.measurement_month.desc())
                  .first())

            score = float(hs.health_score) if hs else 0
            pillars = {}
            if hs and hs.contributing_pillars:
                pillars = {k: float(v) for k, v in hs.contributing_pillars.items()}

            result.append({
                'account_id': acct.account_id,
                'account_name': acct.account_name,
                'revenue': float(acct.revenue or 0),
                'health_score': round(score, 1),
                'status': ht.classify(score),
                'pillar_scores': pillars,
            })

        result.sort(key=lambda a: a['health_score'])
        return jsonify({'status': 'success', 'accounts': result})

    except Exception as e:
        logger.error(f"SaaS Premium list accounts error: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@saas_premium_api.route('/health-summary', methods=['GET'])
def saas_health_summary():
    """Portfolio-level health summary for SaaS Premium."""
    try:
        customer_id = get_current_customer_id()
        if not customer_id:
            return jsonify({'error': 'Authentication required'}), 401

        accounts = Account.query.filter_by(customer_id=customer_id).all()
        if not accounts:
            return jsonify({'status': 'success', 'account_count': 0})

        healthy = at_risk = critical = 0
        total_weighted = 0.0
        total_rev = 0.0
        total_arr = 0.0

        for acct in accounts:
            rev = float(acct.revenue or 0)
            total_arr += rev
            hs = (HealthScore.query
                  .filter_by(account_id=acct.account_id)
                  .order_by(HealthScore.measurement_month.desc())
                  .first())
            score = float(hs.health_score) if hs else 0
            total_weighted += score * rev
            total_rev += rev

            if score >= ht.healthy_min():
                healthy += 1
            elif score >= ht.at_risk_min():
                at_risk += 1
            else:
                critical += 1

        avg_health = round(total_weighted / total_rev, 1) if total_rev > 0 else 0

        return jsonify({
            'status': 'success',
            'account_count': len(accounts),
            'total_arr': round(total_arr, 2),
            'avg_health_score': avg_health,
            'healthy_count': healthy,
            'at_risk_count': at_risk,
            'critical_count': critical,
        })

    except Exception as e:
        logger.error(f"SaaS Premium health summary error: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@saas_premium_api.route('/kpi-catalog', methods=['GET'])
def saas_kpi_catalog():
    """Return the SaaS Premium KPI catalog."""
    try:
        pillars = get_pillars('saas_premium')
        kpis = get_kpis('saas_premium')
        if not pillars or not kpis:
            return jsonify({'error': 'SaaS Premium catalog not found'}), 404

        catalog = {'kpis': kpis, 'pillars': pillars}
        return jsonify({
            'status': 'success',
            'vertical': 'saas_premium',
            'kpi_count': len(kpis),
            'pillar_count': len(pillars),
            'catalog': catalog,
        })

    except Exception as e:
        logger.error(f"SaaS Premium KPI catalog error: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500
