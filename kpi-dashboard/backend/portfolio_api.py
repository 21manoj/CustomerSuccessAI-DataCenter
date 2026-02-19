#!/usr/bin/env python3
"""
Portfolio API — Multi-Company Integration Layer
==================================================
Provides the REST endpoints that connect the Portfolio/PortfolioMembership DB
models to the portfolio_synergy_engine calculation layer.

This is the integration layer that makes the PortCo CEO Dashboard real:
  - CRUD for portfolios and portfolio companies
  - Multi-company Power of 1 aggregation with synergy calculations
  - Configurable cost inputs and variables per portfolio
  - What-if analysis (Power of 1 slider across all 6 levers)

All data is DB-driven. No mock/hardcoded data.

Routes:
  # Portfolio CRUD
  GET    /api/portfolio                              — List portfolios
  POST   /api/portfolio                              — Create portfolio
  GET    /api/portfolio/<id>                          — Get portfolio detail
  PUT    /api/portfolio/<id>                          — Update portfolio
  DELETE /api/portfolio/<id>                          — Delete portfolio

  # Portfolio Company Management
  GET    /api/portfolio/<id>/companies                — List companies in portfolio
  POST   /api/portfolio/<id>/companies                — Add company to portfolio
  DELETE /api/portfolio/<id>/companies/<customer_id>  — Remove company

  # Multi-Company Analysis (the integration layer)
  GET    /api/portfolio/<id>/impact                   — Combined Power of 1 + synergy
  GET    /api/portfolio/<id>/power-of-1-slider        — What-if slider (1-6% across all levers)
  GET    /api/portfolio/<id>/scaling-curves            — Non-linear scaling per company + combined

  # Portfolio Settings / Configuration
  GET    /api/portfolio/<id>/config                   — Get portfolio config
  PUT    /api/portfolio/<id>/config                   — Update portfolio config
"""

from flask import Blueprint, request, jsonify
from auth_middleware import get_current_customer_id
from extensions import db
from models import (
    Portfolio, PortfolioMembership, Customer, Account, FeatureToggle as FeatureToggleModel,
)
from resolve_identifier import resolve_customer_id
from functools import wraps
from datetime import datetime
from sqlalchemy.orm.attributes import flag_modified

from portfolio_synergy_engine import (
    PortfolioCompany, analyze_portfolio, portfolio_result_to_dict,
    SynergyType, SYNERGY_CURVE,
)
from power_of_1_model import (
    POWER_OF_1_METRICS, calculate_portfolio_impact, calculate_power_of_1_impact,
    INVESTMENT_SUMMARY, SCALING_SCENARIOS, COMPOUNDING_MULTIPLIER,
)
from resource_capacity_model import (
    DEFAULT_RESOURCE_POOL, ROLE_RATES, get_resource_pool_summary,
)

portfolio_api = Blueprint('portfolio_api', __name__)


# ============================================================
# AUTH HELPER
# ============================================================

def _get_authenticated_customer_id():
    """Resolve the authenticated customer ID."""
    customer_id = get_current_customer_id()
    if not customer_id:
        return None
    return resolve_customer_id(db, customer_id)


def _check_portfolio_access(portfolio_id, customer_id):
    """Check if the customer has access to this portfolio (is a member or creator)."""
    portfolio = db.session.get(Portfolio, portfolio_id)
    if not portfolio:
        return None, jsonify({'error': 'Portfolio not found'}), 404

    membership = PortfolioMembership.query.filter_by(
        portfolio_id=portfolio_id,
        customer_id=customer_id,
    ).first()

    if not membership:
        # Check if customer created this portfolio (stored in config)
        config = portfolio.config or {}
        if str(customer_id) != str(config.get('created_by_customer_id')):
            return None, jsonify({'error': 'Access denied to this portfolio'}), 403

    return portfolio, None, None


# ============================================================
# PORTFOLIO CRUD
# ============================================================

@portfolio_api.route('/api/portfolio', methods=['GET'])
def list_portfolios():
    """List all portfolios the current customer belongs to."""
    customer_id = _get_authenticated_customer_id()
    if not customer_id:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        # Find portfolios where this customer is a member
        memberships = PortfolioMembership.query.filter_by(customer_id=customer_id).all()
        portfolio_ids = [m.portfolio_id for m in memberships]

        # Also find portfolios created by this customer
        all_portfolios = Portfolio.query.filter(
            (Portfolio.portfolio_id.in_(portfolio_ids)) | (Portfolio.enabled == True)
        ).all()

        results = []
        for p in all_portfolios:
            member_count = PortfolioMembership.query.filter_by(portfolio_id=p.portfolio_id).count()
            total_arr = _get_portfolio_total_arr(p.portfolio_id)
            results.append({
                **p.to_dict(),
                'company_count': member_count,
                'total_arr': total_arr,
            })

        return jsonify({'portfolios': results, 'count': len(results)})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@portfolio_api.route('/api/portfolio', methods=['POST'])
def create_portfolio():
    """Create a new portfolio."""
    customer_id = _get_authenticated_customer_id()
    if not customer_id:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        data = request.get_json()
        if not data or not data.get('portfolio_name'):
            return jsonify({'error': 'portfolio_name is required'}), 400

        config = data.get('config', {})
        config['created_by_customer_id'] = customer_id

        # Store cost overrides in config
        if 'cost_inputs' in data:
            config['cost_inputs'] = data['cost_inputs']
        if 'synergy_overrides' in data:
            config['synergy_overrides'] = data['synergy_overrides']
        if 'role_rate_overrides' in data:
            config['role_rate_overrides'] = data['role_rate_overrides']

        portfolio = Portfolio(
            portfolio_name=data['portfolio_name'],
            portfolio_type=data.get('portfolio_type', 'pe_fund'),
            description=data.get('description'),
            total_aum=data.get('total_aum'),
            investment_thesis=data.get('investment_thesis'),
            config=config,
            enabled=True,
        )
        db.session.add(portfolio)
        db.session.flush()

        # Auto-add the creating customer as a member
        membership = PortfolioMembership(
            portfolio_id=portfolio.portfolio_id,
            customer_id=customer_id,
            status='owned',
            role='creator',
        )
        db.session.add(membership)

        # Add initial companies if provided
        if 'companies' in data:
            for comp in data['companies']:
                comp_customer_id = comp.get('customer_id')
                if comp_customer_id and comp_customer_id != customer_id:
                    mem = PortfolioMembership(
                        portfolio_id=portfolio.portfolio_id,
                        customer_id=comp_customer_id,
                        status=comp.get('status', 'owned'),
                        vertical=comp.get('vertical'),
                        role=comp.get('role', 'platform'),
                        acquisition_date=datetime.fromisoformat(comp['acquisition_date']) if comp.get('acquisition_date') else None,
                    )
                    db.session.add(mem)

        db.session.commit()

        return jsonify({
            'portfolio_id': portfolio.portfolio_id,
            'message': 'Portfolio created',
            'portfolio': portfolio.to_dict(),
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@portfolio_api.route('/api/portfolio/<int:portfolio_id>', methods=['GET'])
def get_portfolio(portfolio_id):
    """Get detailed portfolio info with all companies."""
    customer_id = _get_authenticated_customer_id()
    if not customer_id:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        portfolio = db.session.get(Portfolio, portfolio_id)
        if not portfolio:
            return jsonify({'error': 'Portfolio not found'}), 404

        companies = _get_portfolio_companies(portfolio_id)
        total_arr = sum(c['arr'] for c in companies)

        return jsonify({
            **portfolio.to_dict(),
            'companies': companies,
            'company_count': len(companies),
            'total_arr': total_arr,
            'config': portfolio.config or {},
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@portfolio_api.route('/api/portfolio/<int:portfolio_id>', methods=['PUT'])
def update_portfolio(portfolio_id):
    """Update portfolio details."""
    customer_id = _get_authenticated_customer_id()
    if not customer_id:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        portfolio = db.session.get(Portfolio, portfolio_id)
        if not portfolio:
            return jsonify({'error': 'Portfolio not found'}), 404

        data = request.get_json()
        if data.get('portfolio_name'):
            portfolio.portfolio_name = data['portfolio_name']
        if data.get('description') is not None:
            portfolio.description = data['description']
        if data.get('total_aum') is not None:
            portfolio.total_aum = data['total_aum']
        if data.get('investment_thesis') is not None:
            portfolio.investment_thesis = data['investment_thesis']

        # Merge config updates
        config = dict(portfolio.config or {})  # Copy to ensure mutation detection
        if 'cost_inputs' in data:
            config['cost_inputs'] = data['cost_inputs']
        if 'synergy_overrides' in data:
            config['synergy_overrides'] = data['synergy_overrides']
        if 'role_rate_overrides' in data:
            config['role_rate_overrides'] = data['role_rate_overrides']
        portfolio.config = config
        flag_modified(portfolio, 'config')

        db.session.commit()
        return jsonify({'message': 'Portfolio updated', 'portfolio': portfolio.to_dict()})

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@portfolio_api.route('/api/portfolio/<int:portfolio_id>', methods=['DELETE'])
def delete_portfolio(portfolio_id):
    """Delete a portfolio and its memberships."""
    customer_id = _get_authenticated_customer_id()
    if not customer_id:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        portfolio = db.session.get(Portfolio, portfolio_id)
        if not portfolio:
            return jsonify({'error': 'Portfolio not found'}), 404

        PortfolioMembership.query.filter_by(portfolio_id=portfolio_id).delete()
        db.session.delete(portfolio)
        db.session.commit()

        return jsonify({'message': 'Portfolio deleted'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ============================================================
# COMPANY MANAGEMENT
# ============================================================

@portfolio_api.route('/api/portfolio/<int:portfolio_id>/companies', methods=['GET'])
def list_portfolio_companies(portfolio_id):
    """List all companies in a portfolio with their ARR and account counts."""
    customer_id = _get_authenticated_customer_id()
    if not customer_id:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        companies = _get_portfolio_companies(portfolio_id)
        return jsonify({
            'portfolio_id': portfolio_id,
            'companies': companies,
            'count': len(companies),
            'total_arr': sum(c['arr'] for c in companies),
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@portfolio_api.route('/api/portfolio/<int:portfolio_id>/companies', methods=['POST'])
def add_portfolio_company(portfolio_id):
    """Add a company (customer) to a portfolio."""
    customer_id = _get_authenticated_customer_id()
    if not customer_id:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        portfolio = db.session.get(Portfolio, portfolio_id)
        if not portfolio:
            return jsonify({'error': 'Portfolio not found'}), 404

        data = request.get_json()
        target_customer_id = data.get('customer_id')
        if not target_customer_id:
            return jsonify({'error': 'customer_id is required'}), 400

        # Check if already a member
        existing = PortfolioMembership.query.filter_by(
            portfolio_id=portfolio_id,
            customer_id=target_customer_id,
        ).first()
        if existing:
            return jsonify({'error': 'Company already in portfolio'}), 409

        # Verify the customer exists
        customer = db.session.get(Customer, target_customer_id)
        if not customer:
            return jsonify({'error': f'Customer {target_customer_id} not found'}), 404

        membership = PortfolioMembership(
            portfolio_id=portfolio_id,
            customer_id=target_customer_id,
            status=data.get('status', 'owned'),
            vertical=data.get('vertical', customer.vertical),
            role=data.get('role', 'platform'),
            acquisition_date=datetime.fromisoformat(data['acquisition_date']) if data.get('acquisition_date') else None,
        )
        db.session.add(membership)
        db.session.commit()

        return jsonify({
            'message': f'{customer.customer_name} added to portfolio',
            'membership': membership.to_dict(),
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@portfolio_api.route('/api/portfolio/<int:portfolio_id>/companies/<int:target_customer_id>', methods=['DELETE'])
def remove_portfolio_company(portfolio_id, target_customer_id):
    """Remove a company from a portfolio."""
    customer_id = _get_authenticated_customer_id()
    if not customer_id:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        deleted = PortfolioMembership.query.filter_by(
            portfolio_id=portfolio_id,
            customer_id=target_customer_id,
        ).delete()

        if not deleted:
            return jsonify({'error': 'Company not found in portfolio'}), 404

        db.session.commit()
        return jsonify({'message': 'Company removed from portfolio'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ============================================================
# MULTI-COMPANY IMPACT ANALYSIS (THE INTEGRATION LAYER)
# ============================================================

@portfolio_api.route('/api/portfolio/<int:portfolio_id>/impact', methods=['GET'])
def get_portfolio_impact(portfolio_id):
    """
    Combined Power of 1 + Synergy impact for all companies in the portfolio.

    This is the endpoint that replaces the mock data in the PortCo CEO Dashboard.
    It runs analyze_portfolio() from the synergy engine using real DB data.

    Query params:
        improvement_pct: float (default 1.0) — applied across all companies
    """
    customer_id = _get_authenticated_customer_id()
    if not customer_id:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        portfolio = db.session.get(Portfolio, portfolio_id)
        if not portfolio:
            return jsonify({'error': 'Portfolio not found'}), 404

        improvement_pct = request.args.get('improvement_pct', 1.0, type=float)

        # Build PortfolioCompany list from DB
        companies = _build_portfolio_company_list(portfolio_id, improvement_pct)
        if not companies:
            return jsonify({
                'error': 'No companies in portfolio',
                'portfolio_id': portfolio_id,
            }), 404

        # Apply any config overrides from portfolio settings
        config = portfolio.config or {}
        cost_inputs = config.get('cost_inputs', {})

        # Run the synergy engine with real data
        result = analyze_portfolio(portfolio.portfolio_name, companies)
        result_dict = portfolio_result_to_dict(result)

        # Add portfolio metadata
        result_dict['portfolio_id'] = portfolio_id
        result_dict['improvement_pct'] = improvement_pct
        result_dict['investment_summary'] = _get_investment_summary(config)
        result_dict['cost_inputs'] = cost_inputs

        return jsonify(result_dict)

    except Exception as e:
        import traceback
        print(f"Portfolio impact error: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500


@portfolio_api.route('/api/portfolio/<int:portfolio_id>/power-of-1-slider', methods=['GET'])
def power_of_1_slider(portfolio_id):
    """
    What-if analysis: slide improvement_pct from 0.5% to 6% and see combined
    ROI across all portfolio companies with synergies.

    Returns data points at 0.5% increments for a smooth slider curve.
    """
    customer_id = _get_authenticated_customer_id()
    if not customer_id:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        portfolio = db.session.get(Portfolio, portfolio_id)
        if not portfolio:
            return jsonify({'error': 'Portfolio not found'}), 404

        slider_points = []

        for pct_x10 in range(5, 65, 5):  # 0.5% to 6.0% in 0.5% steps
            pct = pct_x10 / 10.0
            companies = _build_portfolio_company_list(portfolio_id, pct)
            if not companies:
                continue

            result = analyze_portfolio(portfolio.portfolio_name, companies)

            slider_points.append({
                'improvement_pct': pct,
                'company_count': result.company_count,
                'total_arr': result.total_arr,
                'standalone_impact': result.standalone_total_impact,
                'synergy_impact': result.synergy_total_impact,
                'portfolio_total_impact': result.portfolio_total_impact,
                'standalone_roi': result.standalone_roi,
                'portfolio_roi': result.portfolio_roi,
                'synergy_uplift_pct': result.synergy_uplift_pct,
                'investment': result.synergy_adjusted_investment,
                'payback_months': result.payback_months,
            })

        # Also compute per-metric breakdown at the requested percentage
        requested_pct = request.args.get('improvement_pct', 1.0, type=float)
        per_metric = {}
        for metric_id in POWER_OF_1_METRICS:
            metric_points = []
            for pct_x10 in [10, 20, 40, 60]:
                pct = pct_x10 / 10.0
                impact = calculate_power_of_1_impact(metric_id, pct)
                metric_points.append({
                    'improvement_pct': pct,
                    'total_impact': impact['total_impact'],
                    'roi': impact['roi'],
                    'display_name': impact['display_name'],
                })
            per_metric[metric_id] = metric_points

        return jsonify({
            'portfolio_id': portfolio_id,
            'portfolio_name': portfolio.portfolio_name,
            'slider_points': slider_points,
            'per_metric_curves': per_metric,
            'investment_summary': _get_investment_summary(portfolio.config or {}),
        })

    except Exception as e:
        import traceback
        print(f"Slider error: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500


@portfolio_api.route('/api/portfolio/<int:portfolio_id>/scaling-curves', methods=['GET'])
def portfolio_scaling_curves(portfolio_id):
    """
    Non-linear scaling curves per company + combined portfolio.
    Shows the exponential ROI thesis visually.
    """
    customer_id = _get_authenticated_customer_id()
    if not customer_id:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        portfolio = db.session.get(Portfolio, portfolio_id)
        if not portfolio:
            return jsonify({'error': 'Portfolio not found'}), 404

        # Per-company scaling curves
        memberships = PortfolioMembership.query.filter_by(portfolio_id=portfolio_id).all()
        company_curves = {}

        for mem in memberships:
            customer = db.session.get(Customer, mem.customer_id)
            if not customer:
                continue

            accounts = Account.query.filter_by(customer_id=mem.customer_id).all()
            total_arr = sum(float(a.revenue) for a in accounts if a.revenue) or None

            curves = []
            for pct_x10 in range(5, 65, 5):
                pct = pct_x10 / 10.0
                result = calculate_portfolio_impact(pct, total_arr)
                curves.append({
                    'improvement_pct': pct,
                    'total_impact': result['totals']['total_impact'],
                    'roi': result['totals']['roi'],
                    'investment': result['totals']['investment'],
                })

            company_curves[str(mem.customer_id)] = {
                'customer_name': customer.customer_name,
                'arr': float(total_arr or 0),
                'curves': curves,
            }

        # Combined portfolio curve
        portfolio_curves = []
        for pct_x10 in range(5, 65, 5):
            pct = pct_x10 / 10.0
            companies = _build_portfolio_company_list(portfolio_id, pct)
            if companies:
                result = analyze_portfolio(portfolio.portfolio_name, companies)
                portfolio_curves.append({
                    'improvement_pct': pct,
                    'standalone_impact': result.standalone_total_impact,
                    'synergy_impact': result.synergy_total_impact,
                    'portfolio_total_impact': result.portfolio_total_impact,
                    'portfolio_roi': result.portfolio_roi,
                    'synergy_uplift_pct': result.synergy_uplift_pct,
                })

        return jsonify({
            'portfolio_id': portfolio_id,
            'company_curves': company_curves,
            'portfolio_curves': portfolio_curves,
            'scenarios': SCALING_SCENARIOS,
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================
# PORTFOLIO CONFIGURATION
# ============================================================

@portfolio_api.route('/api/portfolio/<int:portfolio_id>/config', methods=['GET'])
def get_portfolio_config(portfolio_id):
    """Get portfolio configuration (cost inputs, synergy overrides, role rates)."""
    customer_id = _get_authenticated_customer_id()
    if not customer_id:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        portfolio = db.session.get(Portfolio, portfolio_id)
        if not portfolio:
            return jsonify({'error': 'Portfolio not found'}), 404

        config = portfolio.config or {}

        # Return config with defaults filled in
        return jsonify({
            'portfolio_id': portfolio_id,
            'cost_inputs': config.get('cost_inputs', {
                'total_investment': INVESTMENT_SUMMARY['total_investment'],
                'cs_initiatives': INVESTMENT_SUMMARY['cs_initiatives'],
                'platform_cost': INVESTMENT_SUMMARY['platform_cost'],
            }),
            'role_rate_overrides': config.get('role_rate_overrides', ROLE_RATES),
            'synergy_overrides': config.get('synergy_overrides', {
                st.value: {
                    'base_lift_pct': curve['base_lift_pct'],
                    'decay_rate': curve['decay_rate'],
                }
                for st, curve in SYNERGY_CURVE.items()
            }),
            'default_improvement_pct': config.get('default_improvement_pct', 1.0),
            'resource_pool': get_resource_pool_summary(),
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@portfolio_api.route('/api/portfolio/<int:portfolio_id>/config', methods=['PUT'])
def update_portfolio_config(portfolio_id):
    """Update portfolio configuration."""
    customer_id = _get_authenticated_customer_id()
    if not customer_id:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        portfolio = db.session.get(Portfolio, portfolio_id)
        if not portfolio:
            return jsonify({'error': 'Portfolio not found'}), 404

        data = request.get_json()
        config = dict(portfolio.config or {})  # Copy to ensure mutation detection

        if 'cost_inputs' in data:
            config['cost_inputs'] = data['cost_inputs']
        if 'role_rate_overrides' in data:
            config['role_rate_overrides'] = data['role_rate_overrides']
        if 'synergy_overrides' in data:
            config['synergy_overrides'] = data['synergy_overrides']
        if 'default_improvement_pct' in data:
            config['default_improvement_pct'] = data['default_improvement_pct']

        portfolio.config = config
        flag_modified(portfolio, 'config')
        db.session.commit()

        return jsonify({'message': 'Configuration updated', 'config': config})

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ============================================================
# INTERNAL HELPERS
# ============================================================

def _get_portfolio_companies(portfolio_id):
    """Get all companies in a portfolio with their ARR from the DB."""
    memberships = PortfolioMembership.query.filter_by(portfolio_id=portfolio_id).all()
    companies = []

    for mem in memberships:
        customer = db.session.get(Customer, mem.customer_id)
        if not customer:
            continue

        accounts = Account.query.filter_by(customer_id=mem.customer_id).all()
        total_arr = sum(float(a.revenue) for a in accounts if a.revenue)
        account_count = len(accounts)

        companies.append({
            'customer_id': mem.customer_id,
            'customer_name': customer.customer_name,
            'arr': total_arr,
            'account_count': account_count,
            'vertical': mem.vertical or customer.vertical,
            'status': mem.status,
            'role': mem.role,
            'acquisition_date': mem.acquisition_date.isoformat() if mem.acquisition_date else None,
            'synergies_identified': mem.synergies_identified,
            'synergies_realized': mem.synergies_realized,
            'synergy_value': float(mem.synergy_value or 0),
            'membership': mem.to_dict(),
        })

    return companies


def _get_portfolio_total_arr(portfolio_id):
    """Sum ARR across all companies in a portfolio."""
    memberships = PortfolioMembership.query.filter_by(portfolio_id=portfolio_id).all()
    total = 0
    for mem in memberships:
        accounts = Account.query.filter_by(customer_id=mem.customer_id).all()
        total += sum(float(a.revenue) for a in accounts if a.revenue)
    return total


def _build_portfolio_company_list(portfolio_id, improvement_pct=1.0):
    """
    Build a list of PortfolioCompany objects from DB data for the synergy engine.
    Sorts by ARR descending (most mature/largest first for synergy ordering).
    """
    memberships = PortfolioMembership.query.filter_by(portfolio_id=portfolio_id).all()
    companies = []

    for mem in memberships:
        customer = db.session.get(Customer, mem.customer_id)
        if not customer:
            continue

        accounts = Account.query.filter_by(customer_id=mem.customer_id).all()
        total_arr = sum(float(a.revenue) for a in accounts if a.revenue)

        if total_arr <= 0:
            continue

        maturity = 'mature' if total_arr >= 50_000_000 else 'growth' if total_arr >= 10_000_000 else 'emerging'

        companies.append(PortfolioCompany(
            company_id=str(mem.customer_id),
            company_name=customer.customer_name,
            arr=total_arr,
            improvement_pct=improvement_pct,
            maturity_level=maturity,
            vertical=mem.vertical or customer.vertical or 'general',
        ))

    # Sort by ARR descending — largest company gets position 0 (no synergy)
    companies.sort(key=lambda c: c.arr, reverse=True)
    return companies


def _get_investment_summary(config):
    """Build investment summary, applying config overrides if present."""
    cost_inputs = config.get('cost_inputs', {})
    return {
        'total_investment': cost_inputs.get('total_investment', INVESTMENT_SUMMARY['total_investment']),
        'cs_initiatives': cost_inputs.get('cs_initiatives', INVESTMENT_SUMMARY['cs_initiatives']),
        'platform_cost': cost_inputs.get('platform_cost', INVESTMENT_SUMMARY['platform_cost']),
        'total_hours': INVESTMENT_SUMMARY['total_hours'],
        'total_fte': INVESTMENT_SUMMARY['total_fte'],
    }
