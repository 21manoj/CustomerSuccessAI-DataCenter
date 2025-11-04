"""
Customer Registration API

Allows new customers to self-register and create their own accounts
"""

from flask import Blueprint, request, jsonify
from auth_middleware import get_current_customer_id, get_current_user_id
from models import db, Customer, User, CustomerConfig
from werkzeug.security import generate_password_hash
import json
import re

registration_api = Blueprint('registration_api', __name__)

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    """Validate password strength"""
    if len(password) < 6:
        return False, "Password must be at least 6 characters"
    return True, "Password valid"

@registration_api.route('/api/register', methods=['POST'])
def register_customer():
    """Register a new customer and create initial user"""
    try:
        data = request.json
        
        # Required fields
        company_name = data.get('company_name', '').strip()
        admin_name = data.get('admin_name', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        phone = data.get('phone', '').strip()
        
        # Validation
        if not company_name:
            return jsonify({'error': 'Company name is required'}), 400
        
        if not admin_name:
            return jsonify({'error': 'Admin name is required'}), 400
        
        if not email:
            return jsonify({'error': 'Email is required'}), 400
        
        if not validate_email(email):
            return jsonify({'error': 'Invalid email format'}), 400
        
        if not password:
            return jsonify({'error': 'Password is required'}), 400
        
        valid, msg = validate_password(password)
        if not valid:
            return jsonify({'error': msg}), 400
        
        # Extract email domain for multi-tenant identification
        email_domain = email.split('@')[1].lower()
        
        # Check for duplicate company name
        existing_customer = Customer.query.filter_by(customer_name=company_name).first()
        if existing_customer:
            return jsonify({'error': 'Company name already registered'}), 409
        
        # Check for duplicate domain
        existing_domain = Customer.query.filter_by(domain=email_domain).first()
        if existing_domain:
            return jsonify({'error': f'A company with email domain {email_domain} is already registered'}), 409
        
        # Check for duplicate email (globally unique)
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return jsonify({'error': 'Email already registered'}), 409
        
        # Create customer with domain identification
        customer = Customer(
            customer_name=company_name,
            email=data.get('company_email', email),
            phone=phone,
            domain=email_domain
        )
        db.session.add(customer)
        db.session.flush()
        
        customer_id = customer.customer_id
        
        # Create admin user
        user = User(
            customer_id=customer_id,
            user_name=admin_name,
            email=email,
            password_hash=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.flush()
        
        # Create default customer configuration (check if exists first)
        existing_config = CustomerConfig.query.filter_by(customer_id=customer_id).first()
        if not existing_config:
            default_weights = {
                'Relationship Strength': 0.20,
                'Adoption & Engagement': 0.25,
                'Support & Experience': 0.20,
                'Product Value': 0.20,
                'Business Outcomes': 0.15
            }
            
            config = CustomerConfig(
                customer_id=customer_id,
                kpi_upload_mode='account_rollup',
                category_weights=json.dumps(default_weights),
                master_file_name=None
            )
            db.session.add(config)
        
        # Create default playbook triggers
        from models import PlaybookTrigger
        
        trigger_configs = {
            'voc': {
                'nps_threshold': 10,
                'csat_threshold': 3.6,
                'churn_risk_threshold': 0.30,
                'health_score_drop_threshold': 10,
                'churn_mentions_threshold': 2
            },
            'activation': {
                'adoption_index_threshold': 60,
                'active_users_threshold': 50,
                'dau_mau_threshold': 0.25,
                'feature_usage_threshold': 0.40
            },
            'sla': {
                'sla_breach_threshold': 5,
                'response_time_multiplier': 2.0,
                'escalation_trend': 'increasing',
                'reopen_rate_threshold': 0.20
            },
            'renewal': {
                'renewal_window_days': 90,
                'health_score_threshold': 70,
                'engagement_trend': 'declining',
                'champion_status': 'departed'
            },
            'expansion': {
                'health_score_threshold': 80,
                'adoption_threshold': 0.85,
                'usage_limit_percentage': 0.80,
                'budget_window': 'open'
            }
        }
        
        for playbook_type, config_data in trigger_configs.items():
            # Check if trigger already exists
            existing_trigger = PlaybookTrigger.query.filter_by(
                customer_id=customer_id,
                playbook_type=playbook_type
            ).first()
            
            if not existing_trigger:
                trigger = PlaybookTrigger(
                    customer_id=customer_id,
                    playbook_type=playbook_type,
                    trigger_config=json.dumps(config_data),
                    auto_trigger_enabled=True
                )
                db.session.add(trigger)
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Registration successful',
            'customer_id': customer_id,
            'user_id': user.user_id,
            'email': email,
            'company_name': company_name
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'error': f'Registration failed: {str(e)}'
        }), 500

@registration_api.route('/api/register/add-user', methods=['POST'])
def add_user_to_customer():
    """Add a new user to an existing customer"""
    try:
        data = request.json
        
        # Required fields
        customer_domain = data.get('domain', '').strip()  # Email domain
        user_name = data.get('user_name', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        
        # Validation
        if not customer_domain:
            return jsonify({'error': 'Customer domain is required'}), 400
        
        if not validate_email(email):
            return jsonify({'error': 'Invalid email format'}), 400
        
        valid, msg = validate_password(password)
        if not valid:
            return jsonify({'error': msg}), 400
        
        # Find customer by domain
        customer = Customer.query.filter_by(domain=customer_domain).first()
        if not customer:
            return jsonify({'error': f'No customer found with domain {customer_domain}'}), 404
        
        # Check if email already exists globally
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return jsonify({'error': 'Email already registered'}), 409
        
        # Check if username already exists for this customer
        existing_username = User.query.filter_by(
            customer_id=customer.customer_id,
            user_name=user_name
        ).first()
        if existing_username:
            return jsonify({'error': f'Username {user_name} already exists for this customer'}), 409
        
        # Create user
        user = User(
            customer_id=customer.customer_id,
            user_name=user_name,
            email=email,
            password_hash=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'User added successfully',
            'user_id': user.user_id,
            'customer_id': customer.customer_id,
            'customer_name': customer.customer_name,
            'email': email
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'error': f'Failed to add user: {str(e)}'
        }), 500


@registration_api.route('/api/register/check-availability', methods=['POST'])
def check_availability():
    """Check if company name or email is available"""
    try:
        data = request.json
        company_name = data.get('company_name', '').strip()
        email = data.get('email', '').strip()
        
        result = {
            'company_name_available': True,
            'email_available': True
        }
        
        if company_name:
            existing = Customer.query.filter_by(customer_name=company_name).first()
            result['company_name_available'] = existing is None
        
        if email:
            existing = User.query.filter_by(email=email).first()
            result['email_available'] = existing is None
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

