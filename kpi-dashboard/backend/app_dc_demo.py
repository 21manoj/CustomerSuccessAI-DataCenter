#!/usr/bin/env python3
"""
Lightweight DC2_S Demo App
Only loads the endpoints needed for the DC vertical demo:
  - Login/Register
  - DC2S API (/api/dc2s/*)
  - Signal Analyst API

Avoids heavy RAG/ML dependencies (sentence-transformers, chromadb, etc.)
"""

from flask import Flask, request, jsonify
from flask_migrate import Migrate
from flask_cors import CORS
from flask_session import Session
from flask_login import LoginManager, login_user, logout_user, current_user
from extensions import db

import datetime
import secrets
import os
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

# Load environment variables
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(dotenv_path=os.path.join(basedir, '.env'))

app = Flask(__name__)

# Database
database_url = os.getenv('DATABASE_URL')
if not database_url:
    raise ValueError("DATABASE_URL required")
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', secrets.token_hex(32))

# Session config
app.config['SESSION_TYPE'] = 'sqlalchemy'
app.config['SESSION_PERMANENT'] = True
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_KEY_PREFIX'] = 'cs_session:'
app.config['SESSION_COOKIE_NAME'] = 'cs_session'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = None
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(hours=8)

# CORS
CORS(app, origins=[
    'http://localhost:8005', 'http://localhost:3000',
    'http://127.0.0.1:8005', 'http://127.0.0.1:3000',
], supports_credentials=True)

# Init extensions
db.init_app(app)
migrate = Migrate(app, db)

with app.app_context():
    db.create_all()

app.config['SESSION_SQLALCHEMY'] = db
try:
    Session(app)
except Exception as e:
    print(f"Session init: {e}")

# Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.session_protection = 'strong'

import models
from models import Customer, User, Account, DC2SKPI, QualitativeSignal, CustomerConfig

@login_manager.user_loader
def load_user(user_id):
    try:
        user = db.session.get(User, int(user_id))
        if user:
            db.session.refresh(user)
        return user
    except Exception:
        return None

# Auth middleware (simplified — only protect /api/dc2s/*)
@app.before_request
def check_auth():
    public = ['/api/login', '/api/register', '/api/test', '/']
    if request.path in public or not request.path.startswith('/api/'):
        return None
    is_auth = current_user.is_authenticated() if callable(getattr(current_user, 'is_authenticated', None)) else getattr(current_user, 'is_authenticated', False)
    if not is_auth:
        return jsonify({'error': 'Authentication required', 'login_url': '/api/login'}), 401

# ============================================================
# ROUTES
# ============================================================

@app.route('/')
def home():
    return jsonify({'status': 'CS Pulse DC Demo running', 'timestamp': datetime.datetime.now().isoformat()})

@app.route('/api/test')
def test():
    return jsonify({'status': 'ok'})

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    vertical = data.get('vertical', 'saas')

    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({'message': 'Invalid email or password'}), 401

    login_user(user, remember=True)

    customer = Customer.query.filter_by(customer_id=user.customer_id).first()
    user_vertical = user.vertical or vertical
    frontend_vertical = 'datacenter' if user_vertical == 'dc2_s' else user_vertical

    return jsonify({
        'customer_id': user.customer_id,
        'user_id': user.user_id,
        'user_name': user.user_name,
        'email': user.email,
        'vertical': frontend_vertical,
        'user': {
            'customer_id': user.customer_id,
            'user_id': user.user_id,
            'user_name': user.user_name,
            'email': user.email,
            'customer_name': customer.customer_name if customer else 'Unknown',
        }
    }), 200

@app.route('/api/logout', methods=['POST'])
def logout():
    logout_user()
    return jsonify({'message': 'Logged out'}), 200

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    phone = data.get('phone')
    password = data.get('password')
    if not all([name, email, password]):
        return jsonify({'message': 'Name, email, password required'}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({'message': 'Email already registered'}), 400
    customer = Customer(customer_name=name, email=email, phone=phone or '')
    db.session.add(customer)
    db.session.flush()
    user = User(customer_id=customer.customer_id, user_name=name, email=email,
                password_hash=generate_password_hash(password))
    db.session.add(user)
    db.session.commit()
    return jsonify({'customer_id': customer.customer_id, 'user_id': user.user_id}), 201

# ============================================================
# DC2S API
# ============================================================
from verticals.dc2_s.api_routes import dc2s_api
app.register_blueprint(dc2s_api, url_prefix='/api/dc2s')

# ============================================================
# ADDITIONAL DC2S ENDPOINTS (signals, health-trends, portfolio)
# ============================================================

@app.route('/api/dc2s/signals/<int:account_id>', methods=['GET'])
def get_signals(account_id):
    """Get qualitative signals for an account."""
    customer_id = current_user.customer_id
    account = Account.query.filter_by(
        account_id=account_id, customer_id=customer_id, vertical='dc2_s'
    ).first()
    if not account:
        return jsonify({'error': 'Account not found'}), 404

    limit = request.args.get('limit', 50, type=int)
    signals = QualitativeSignal.query.filter_by(
        account_id=account_id
    ).order_by(QualitativeSignal.signal_date.desc()).limit(limit).all()

    return jsonify({
        'account_id': account_id,
        'account_name': account.account_name,
        'signals': [s.to_dict() for s in signals],
        'total': len(signals),
    })

@app.route('/api/dc2s/signals/all', methods=['GET'])
def get_all_signals():
    """Get recent signals across all DC2S accounts."""
    customer_id = current_user.customer_id
    accounts = Account.query.filter_by(customer_id=customer_id, vertical='dc2_s').all()
    account_ids = [a.account_id for a in accounts]
    account_names = {a.account_id: a.account_name for a in accounts}

    if not account_ids:
        return jsonify({'signals': [], 'total': 0})

    limit = request.args.get('limit', 100, type=int)
    signals = QualitativeSignal.query.filter(
        QualitativeSignal.account_id.in_(account_ids)
    ).order_by(QualitativeSignal.signal_date.desc()).limit(limit).all()

    result = []
    for s in signals:
        d = s.to_dict()
        d['account_name'] = account_names.get(s.account_id, 'Unknown')
        result.append(d)

    # Summary stats
    sentiment_counts = {'positive': 0, 'negative': 0, 'neutral': 0}
    for s in signals:
        sentiment_counts[s.sentiment] = sentiment_counts.get(s.sentiment, 0) + 1

    return jsonify({
        'signals': result,
        'total': len(result),
        'sentiment_summary': sentiment_counts,
    })

@app.route('/api/dc2s/health-trends/<int:account_id>', methods=['GET'])
def get_health_trends(account_id):
    """Get weekly health score trends from KPI history."""
    customer_id = current_user.customer_id
    account = Account.query.filter_by(
        account_id=account_id, customer_id=customer_id, vertical='dc2_s'
    ).first()
    if not account:
        return jsonify({'error': 'Account not found'}), 404

    from verticals.dc2_s.api_routes import calculate_kpi_health

    # Get all KPIs grouped by measured_at
    all_kpis = DC2SKPI.query.filter_by(
        account_id=account_id
    ).order_by(DC2SKPI.measured_at.asc()).all()

    # Group by week (measured_at)
    weeks = {}
    for kpi in all_kpis:
        week_key = kpi.measured_at.strftime('%Y-%m-%d')
        if week_key not in weeks:
            weeks[week_key] = {}
        weeks[week_key][kpi.kpi_code] = float(kpi.value)

    # Calculate health for each week
    trends = []
    prev_score = None
    for week_date, kpi_values in sorted(weeks.items()):
        overall, pillar_scores = calculate_kpi_health(kpi_values, customer_id=customer_id)
        meta = calculate_kpi_health._last_metadata
        change = round(overall - prev_score, 1) if prev_score is not None else 0
        prev_score = overall
        trends.append({
            'date': week_date,
            'health_score': round(overall, 1),
            'change': change,
            'attach_rate': meta['attach_rate'],
            'confidence': meta['confidence'],
            'pillar_scores': {k: round(v, 1) for k, v in pillar_scores.items()},
        })

    return jsonify({
        'account_id': account_id,
        'account_name': account.account_name,
        'trends': trends,
        'total_weeks': len(trends),
    })

@app.route('/api/dc2s/portfolio', methods=['GET'])
def get_portfolio_summary():
    """Get portfolio-level summary for executive dashboard."""
    customer_id = current_user.customer_id
    from verticals.dc2_s.api_routes import calculate_kpi_health

    accounts = Account.query.filter_by(
        customer_id=customer_id, vertical='dc2_s'
    ).all()

    account_summaries = []
    healthy_count = 0
    risk_count = 0
    critical_count = 0
    total_arr = 0
    arr_at_risk = 0

    for account in accounts:
        kpis = DC2SKPI.query.filter_by(
            account_id=account.account_id
        ).order_by(DC2SKPI.measured_at.desc()).all()

        latest_kpis = {}
        if kpis:
            latest_time = kpis[0].measured_at
            latest_kpis = {
                k.kpi_code: float(k.value) for k in kpis if k.measured_at == latest_time
            }

        health, pillar_scores = calculate_kpi_health(latest_kpis, customer_id=customer_id)
        meta = calculate_kpi_health._last_metadata

        revenue = float(account.revenue) if account.revenue else 0
        total_arr += revenue

        if health >= 75:
            status = 'healthy'
            healthy_count += 1
        elif health >= 40:
            status = 'risk'
            risk_count += 1
            arr_at_risk += revenue
        else:
            status = 'critical'
            critical_count += 1
            arr_at_risk += revenue

        # Get recent signals for this account
        recent_signals = QualitativeSignal.query.filter_by(
            account_id=account.account_id
        ).order_by(QualitativeSignal.signal_date.desc()).limit(5).all()

        neg_signals = [s for s in recent_signals if s.sentiment == 'negative']

        account_summaries.append({
            'account_id': account.account_id,
            'account_name': account.account_name,
            'health_score': round(health, 1),
            'status': status,
            'confidence': meta['confidence'],
            'attach_rate': meta['attach_rate'],
            'revenue': revenue,
            'industry': account.industry,
            'region': account.region,
            'pillar_scores': {k: round(v, 1) for k, v in pillar_scores.items()},
            'recent_negative_signals': len(neg_signals),
            'pattern_type': (account.profile_metadata or {}).get('primary_workload', 'N/A'),
        })

    # Sort: critical first, then risk, then healthy
    status_order = {'critical': 0, 'risk': 1, 'healthy': 2}
    account_summaries.sort(key=lambda a: (status_order.get(a['status'], 3), -a['health_score']))

    avg_health = sum(a['health_score'] for a in account_summaries) / len(account_summaries) if account_summaries else 0

    return jsonify({
        'total_accounts': len(accounts),
        'healthy_count': healthy_count,
        'at_risk_count': risk_count,
        'critical_count': critical_count,
        'total_arr': total_arr,
        'arr_at_risk': arr_at_risk,
        'avg_health_score': round(avg_health, 1),
        'accounts': account_summaries,
    })

@app.route('/api/accounts', methods=['GET'])
def get_accounts_compat():
    """SaaS-compatible /api/accounts endpoint that returns DC2S accounts when vertical is dc2_s."""
    customer_id = current_user.customer_id
    accounts = Account.query.filter_by(customer_id=customer_id, vertical='dc2_s').all()
    return jsonify([{
        'account_id': a.account_id,
        'account_name': a.account_name,
        'revenue': float(a.revenue) if a.revenue else 0,
        'status': a.account_status,
        'industry': a.industry,
        'region': a.region,
    } for a in accounts])

@app.route('/api/health-trends', methods=['GET'])
def get_health_trends_compat():
    """SaaS-compatible /api/health-trends for DC2S."""
    customer_id = current_user.customer_id
    from verticals.dc2_s.api_routes import calculate_kpi_health

    accounts = Account.query.filter_by(customer_id=customer_id, vertical='dc2_s').all()
    result = []

    for account in accounts:
        kpis = DC2SKPI.query.filter_by(
            account_id=account.account_id
        ).order_by(DC2SKPI.measured_at.desc()).all()

        latest_kpis = {}
        if kpis:
            latest_time = kpis[0].measured_at
            latest_kpis = {k.kpi_code: float(k.value) for k in kpis if k.measured_at == latest_time}

        health, _ = calculate_kpi_health(latest_kpis, customer_id=customer_id)

        result.append({
            'account_id': account.account_id,
            'account_name': account.account_name,
            'overall_health_score': round(health, 1),
        })

    return jsonify(result)


# ============================================================
# DC2S CONFIG ENDPOINTS (for Settings UI)
# ============================================================

# Pillar code mapping: DB (AI/CH/DV/EX/OS) <-> Catalog (P3/P4/P1/P5/P2)
CATALOG_TO_DB = {'P1': 'DV', 'P2': 'OS', 'P3': 'AI', 'P4': 'CH', 'P5': 'EX'}
DB_TO_CATALOG = {v: k for k, v in CATALOG_TO_DB.items()}

@app.route('/api/dc2s/config/', methods=['GET'])
def get_dc2s_config():
    """Get customer config for settings UI."""
    customer_id = current_user.customer_id
    from verticals.dc2_s.kpi_definitions import DC2S_KPIS, DC2S_PILLARS
    from verticals.dc2_s.pillar_weights import BOOTSTRAP_L2_WEIGHTS

    config = CustomerConfig.query.filter_by(customer_id=customer_id).first()

    # Build pillar weights in DB naming (AI/CH/DV/EX/OS)
    pillar_weights = {}
    if config and config.dc2s_pillar_weights:
        for p_code, weight in config.dc2s_pillar_weights.items():
            db_code = CATALOG_TO_DB.get(p_code, p_code)
            pillar_weights[db_code] = weight
    else:
        for p_code, info in DC2S_PILLARS.items():
            db_code = CATALOG_TO_DB.get(p_code, p_code)
            pillar_weights[db_code] = info['weight_l2']

    # Build KPI definitions
    kpi_defs = {}
    kpi_weights = {}
    enabled_kpis = []
    for code, d in DC2S_KPIS.items():
        enabled_kpis.append(code)
        target_raw = d.get('target', {})
        target_val = target_raw.get('value') if isinstance(target_raw, dict) else target_raw
        operator = target_raw.get('operator', '>') if isinstance(target_raw, dict) else '>'

        kpi_defs[code] = {
            'pillar': d['pillar'],
            'name': d['name'],
            'description': d.get('description', ''),
            'unit': d.get('unit', ''),
            'target': target_val,
            'operator': operator,
            'range': [0, 100],
            'thresholds': {
                'excellent': d.get('ranges', {}).get('healthy', {}),
                'good': d.get('ranges', {}).get('risk', {}),
                'warning': d.get('ranges', {}).get('risk', {}),
                'critical': d.get('ranges', {}).get('critical', {}),
            },
            'kpi_source_type': d.get('kpi_source_type', 'raw'),
            'higher_is_better': d.get('higher_is_better', True),
        }

        pillar = d['pillar']
        if pillar not in kpi_weights:
            kpi_weights[pillar] = {}
        kpi_weights[pillar][code] = d.get('weight_l1', 0)

    return jsonify({
        'customer_id': customer_id,
        'is_default': config is None,
        'weights_source': 'bootstrap',
        'weights_updated_at': config.updated_at.isoformat() if config and config.updated_at else None,
        'pillar_weights': pillar_weights,
        'enabled_kpis': enabled_kpis,
        'kpi_definitions': kpi_defs,
        'kpi_overrides': config.dc2s_kpi_overrides if config and config.dc2s_kpi_overrides else {},
        'kpi_weights': kpi_weights,
        'updated_at': config.updated_at.isoformat() if config and config.updated_at else None,
    })

@app.route('/api/dc2s/config/', methods=['PUT'])
def update_dc2s_config():
    """Update customer config."""
    customer_id = current_user.customer_id
    data = request.get_json()

    config = CustomerConfig.query.filter_by(customer_id=customer_id).first()
    if not config:
        config = CustomerConfig(customer_id=customer_id, vertical='dc2_s')
        db.session.add(config)

    if 'pillar_weights' in data:
        # Convert DB naming to catalog naming for storage
        catalog_weights = {}
        for db_code, weight in data['pillar_weights'].items():
            cat_code = DB_TO_CATALOG.get(db_code, db_code)
            catalog_weights[cat_code] = weight
        config.dc2s_pillar_weights = catalog_weights

    if 'kpi_overrides' in data:
        config.dc2s_kpi_overrides = data['kpi_overrides']
    if 'enabled_kpis' in data:
        config.dc2s_enabled_kpis = data['enabled_kpis']

    db.session.commit()
    return jsonify({'status': 'ok', 'message': 'Configuration updated'})

@app.route('/api/dc2s/config/pillar-weights', methods=['PUT'])
def update_pillar_weights():
    """Update pillar weights specifically."""
    customer_id = current_user.customer_id
    data = request.get_json()
    weights = data.get('weights', {})

    config = CustomerConfig.query.filter_by(customer_id=customer_id).first()
    if not config:
        config = CustomerConfig(customer_id=customer_id, vertical='dc2_s')
        db.session.add(config)

    # Convert DB naming to catalog naming
    catalog_weights = {}
    for db_code, weight in weights.items():
        cat_code = DB_TO_CATALOG.get(db_code, db_code)
        catalog_weights[cat_code] = weight
    config.dc2s_pillar_weights = catalog_weights

    db.session.commit()
    return jsonify({'status': 'ok', 'message': 'Pillar weights updated'})

@app.route('/api/dc2s/config/kpi-ranges', methods=['GET'])
def get_kpi_ranges():
    """Get KPI reference ranges for the KPI Ranges settings tab."""
    from verticals.dc2_s.kpi_definitions import DC2S_KPIS

    ranges = {}
    for code, d in DC2S_KPIS.items():
        r = d.get('ranges', {})
        ranges[code] = {
            'kpi_code': code,
            'name': d['name'],
            'pillar': d['pillar'],
            'unit': d.get('unit', ''),
            'higher_is_better': d.get('higher_is_better', True),
            'healthy': r.get('healthy', {}),
            'risk': r.get('risk', {}),
            'critical': r.get('critical', {}),
        }

    return jsonify({'ranges': ranges, 'total': len(ranges)})

@app.route('/api/dc2s/config/weight-history', methods=['GET'])
def get_weight_history():
    """Get weight change history (placeholder for now)."""
    return jsonify({'history': [], 'total': 0})

@app.route('/api/dc2s/scores/account/<int:account_id>/latest', methods=['GET'])
def get_latest_scores(account_id):
    """Get latest L1/L2/L3 scores for an account (KPIDetails fallback)."""
    customer_id = current_user.customer_id
    from verticals.dc2_s.api_routes import calculate_kpi_health

    account = Account.query.filter_by(
        account_id=account_id, customer_id=customer_id, vertical='dc2_s'
    ).first()
    if not account:
        return jsonify({'error': 'Account not found'}), 404

    kpis = DC2SKPI.query.filter_by(account_id=account_id).order_by(DC2SKPI.measured_at.desc()).all()
    latest_kpis = {}
    if kpis:
        latest_time = kpis[0].measured_at
        latest_kpis = {k.kpi_code: float(k.value) for k in kpis if k.measured_at == latest_time}

    health, pillar_scores = calculate_kpi_health(latest_kpis, customer_id=customer_id)
    meta = calculate_kpi_health._last_metadata

    return jsonify({
        'account_id': account_id,
        'overall_health': round(health, 1),
        'pillar_scores': {k: round(v, 1) for k, v in pillar_scores.items()},
        'pillar_details': meta.get('pillar_details', {}),
        'attach_rate': meta['attach_rate'],
        'confidence': meta['confidence'],
    })

# ============================================================
# SESSION / JOURNEY ENDPOINTS
# ============================================================

@app.route('/api/session/status', methods=['GET'])
def session_status():
    """Check session status for frontend pre-flight."""
    is_auth = current_user.is_authenticated() if callable(getattr(current_user, 'is_authenticated', None)) else getattr(current_user, 'is_authenticated', False)
    if is_auth:
        return jsonify({
            'authenticated': True,
            'user_id': current_user.user_id,
            'customer_id': current_user.customer_id,
            'email': current_user.email,
            'vertical': current_user.vertical or 'dc2_s',
        })
    return jsonify({'authenticated': False}), 401

@app.route('/api/journey/<int:account_id>', methods=['GET'])
def get_journey_data(account_id):
    """Get journey timeline data for JourneyDashboardV3."""
    customer_id = current_user.customer_id
    from verticals.dc2_s.api_routes import calculate_kpi_health

    account = Account.query.filter_by(
        account_id=account_id, customer_id=customer_id, vertical='dc2_s'
    ).first()
    if not account:
        return jsonify({'error': 'Account not found'}), 404

    # Get all KPIs grouped by week
    all_kpis = DC2SKPI.query.filter_by(account_id=account_id).order_by(DC2SKPI.measured_at.asc()).all()
    weeks = {}
    for kpi in all_kpis:
        week_key = kpi.measured_at.strftime('%Y-%m-%d')
        if week_key not in weeks:
            weeks[week_key] = {}
        weeks[week_key][kpi.kpi_code] = float(kpi.value)

    # Calculate health per week
    health_timeline = []
    prev_score = None
    for week_date, kpi_values in sorted(weeks.items()):
        health, pillar_scores = calculate_kpi_health(kpi_values, customer_id=customer_id)
        meta = calculate_kpi_health._last_metadata

        if health >= 75:
            status = 'healthy'
        elif health >= 40:
            status = 'risk'
        else:
            status = 'critical'

        change = round(health - prev_score, 1) if prev_score is not None else 0
        prev_score = health

        health_timeline.append({
            'date': week_date,
            'week': len(health_timeline) + 1,
            'health_score': round(health, 1),
            'status': status,
            'change': change,
            'pillar_scores': {k: round(v, 1) for k, v in pillar_scores.items()},
            'kpi_count': meta['kpis_present'],
        })

    # Get signals for this account
    signals = QualitativeSignal.query.filter_by(account_id=account_id).order_by(
        QualitativeSignal.signal_date.asc()
    ).all()
    signal_timeline = [s.to_dict() for s in signals]

    return jsonify({
        'account_id': account_id,
        'account_name': account.account_name,
        'health_timeline': health_timeline,
        'signals': signal_timeline,
        'total_weeks': len(health_timeline),
        'total_signals': len(signal_timeline),
    })

@app.route('/api/signal-analyst/analyze', methods=['POST'])
def analyze_signals():
    """Signal analysis endpoint (simplified for demo — returns pattern-based insights)."""
    data = request.get_json()
    account_id = data.get('account_id')
    customer_id = current_user.customer_id

    if not account_id:
        return jsonify({'error': 'account_id required'}), 400

    account = Account.query.filter_by(
        account_id=int(account_id), customer_id=customer_id, vertical='dc2_s'
    ).first()
    if not account:
        return jsonify({'error': 'Account not found'}), 404

    # Get recent signals
    recent_signals = QualitativeSignal.query.filter_by(
        account_id=int(account_id)
    ).order_by(QualitativeSignal.signal_date.desc()).limit(20).all()

    pos = sum(1 for s in recent_signals if s.sentiment == 'positive')
    neg = sum(1 for s in recent_signals if s.sentiment == 'negative')
    neu = sum(1 for s in recent_signals if s.sentiment == 'neutral')
    total = len(recent_signals)

    # Generate insights based on signal patterns
    insights = []
    if neg > pos:
        insights.append({
            'type': 'warning',
            'title': 'Negative Signal Trend',
            'description': f'{neg} of {total} recent signals are negative. This indicates potential dissatisfaction.',
            'recommended_action': 'Schedule executive check-in to address concerns.',
        })
    if pos > neg * 2:
        insights.append({
            'type': 'opportunity',
            'title': 'Strong Positive Engagement',
            'description': f'{pos} of {total} recent signals are positive. Customer is highly engaged.',
            'recommended_action': 'Explore expansion opportunities and schedule QBR.',
        })
    if total < 5:
        insights.append({
            'type': 'info',
            'title': 'Limited Signal Data',
            'description': 'Insufficient signals for reliable analysis. Increase touchpoints.',
            'recommended_action': 'Schedule regular check-ins to build signal history.',
        })

    sentiment_trend = 'positive' if pos > neg else ('negative' if neg > pos else 'neutral')

    return jsonify({
        'account_id': account_id,
        'account_name': account.account_name,
        'analysis': {
            'sentiment_trend': sentiment_trend,
            'positive_count': pos,
            'negative_count': neg,
            'neutral_count': neu,
            'total_signals': total,
            'insights': insights,
            'confidence': 'high' if total >= 10 else ('medium' if total >= 5 else 'low'),
        },
    })

# ============================================================
# ADMIN/WIZARD COMPAT ENDPOINTS
# ============================================================

@app.route('/api/admin/wizard-c/weights/current', methods=['GET'])
def get_wizard_weights():
    """Compat endpoint for Settings weight display."""
    customer_id = current_user.customer_id
    from verticals.dc2_s.pillar_weights import BOOTSTRAP_L2_WEIGHTS

    config = CustomerConfig.query.filter_by(customer_id=customer_id).first()
    weights = {}
    if config and config.dc2s_pillar_weights:
        for p_code, w in config.dc2s_pillar_weights.items():
            db_code = CATALOG_TO_DB.get(p_code, p_code)
            weights[db_code] = w
    else:
        for p_code, w in BOOTSTRAP_L2_WEIGHTS.items():
            db_code = CATALOG_TO_DB.get(p_code, p_code)
            weights[db_code] = w

    return jsonify({'weights': weights, 'source': 'bootstrap'})


if __name__ == '__main__':
    port = int(os.getenv('PORT', 8001))
    print(f"\nCS Pulse DC Demo Server")
    print(f"  Backend: http://localhost:{port}")
    print(f"  Login: demo@cspulse.ai / demo123")
    print(f"  DC2S API: http://localhost:{port}/api/dc2s/*")
    app.run(debug=True, host='0.0.0.0', port=port)
