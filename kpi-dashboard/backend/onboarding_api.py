#!/usr/bin/env python3
"""
Onboarding API - Corrected to match actual database schema
"""

from flask import Blueprint, request, jsonify
from models import db, Customer, Account, CustomerConfig
from auth_middleware import get_current_user_id, get_current_customer_id
import subprocess
import os
from datetime import datetime

onboarding_api = Blueprint('onboarding_api', __name__, url_prefix='/api/onboarding')

# ============================================================================
# STEP 1: CREATE CUSTOMER
# ============================================================================

@onboarding_api.route('/create-customer', methods=['POST'])
def create_customer():
    """Create new customer account"""
    
    data = request.json
    
    customer_name = data.get('customer_name')
    
    if not customer_name:
        return jsonify({'error': 'customer_name required'}), 400
    
    try:
        # Create customer (minimal - only customer_name)
        customer = Customer(
            customer_name=customer_name
        )
        db.session.add(customer)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'customer_id': customer.customer_id,
            'customer_name': customer.customer_name
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ============================================================================
# STEP 2: INITIALIZE CONFIGURATION
# ============================================================================

@onboarding_api.route('/initialize-config', methods=['POST'])
def initialize_config():
    """Initialize customer configuration"""
    
    data = request.json
    customer_id = data.get('customer_id') or get_current_customer_id()
    
    if not customer_id:
        return jsonify({'error': 'Customer ID required'}), 400
    
    # Check if config already exists
    existing = CustomerConfig.query.filter_by(customer_id=customer_id).first()
    if existing:
        return jsonify({'error': 'Configuration already exists'}), 400
    
    try:
        # Get custom pillar weights or use defaults
        pillar_weights = data.get('pillar_weights', {
            'AI': 0.25,
            'CH': 0.20,
            'DV': 0.15,
            'EX': 0.20,
            'OS': 0.20
        })
        
        # Get enabled KPIs or use defaults
        enabled_kpis = data.get('enabled_kpis', [
            'AI-KPI1', 'AI-KPI2', 'AI-KPI3',
            'CH-KPI1', 'CH-KPI2', 'CH-KPI3',
            'DV-KPI1', 'DV-KPI2', 'DV-KPI3',
            'EX-KPI1', 'EX-KPI2', 'EX-KPI3',
            'OS-KPI1', 'OS-KPI2', 'OS-KPI3'
        ])
        
        # Create configuration
        config = CustomerConfig(
            customer_id=customer_id,
            vertical='dc2_s',
            dc2s_pillar_weights=pillar_weights,
            dc2s_enabled_kpis=enabled_kpis,
            dc2s_kpi_definitions={},
            dc2s_kpi_weights={
                'AI': {'AI-KPI1': 0.35, 'AI-KPI2': 0.35, 'AI-KPI3': 0.30},
                'CH': {'CH-KPI1': 0.40, 'CH-KPI2': 0.35, 'CH-KPI3': 0.25},
                'DV': {'DV-KPI1': 0.40, 'DV-KPI2': 0.35, 'DV-KPI3': 0.25},
                'EX': {'EX-KPI1': 0.40, 'EX-KPI2': 0.35, 'EX-KPI3': 0.25},
                'OS': {'OS-KPI1': 0.40, 'OS-KPI2': 0.35, 'OS-KPI3': 0.25}
            }
        )
        
        db.session.add(config)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'customer_id': customer_id,
            'pillar_weights': pillar_weights,
            'enabled_kpis': len(enabled_kpis)
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ============================================================================
# STEP 3: CREATE SAMPLE ACCOUNTS
# ============================================================================

@onboarding_api.route('/create-sample-accounts', methods=['POST'])
def create_sample_accounts():
    """Create sample accounts for customer"""
    
    data = request.json
    customer_id = data.get('customer_id') or get_current_customer_id()
    num_accounts = data.get('num_accounts', 3)
    industry = data.get('industry', 'Technology')
    
    if not customer_id:
        return jsonify({'error': 'Customer ID required'}), 400
    
    try:
        customer = Customer.query.get(customer_id)
        if not customer:
            return jsonify({'error': 'Customer not found'}), 404
        
        accounts = []
        environments = ['Production', 'Staging', 'Development']
        
        for i in range(num_accounts):
            env = environments[i % len(environments)]
            
            # Use actual Account model fields
            account = Account(
                customer_id=customer_id,
                account_name=f'{customer.customer_name}-{env}',
                industry=industry,           # ✅ Field exists
                vertical='dc2_s',            # ✅ Field exists
                region='us-west-2',          # ✅ Field exists
                account_status='active'      # ✅ Field exists
            )
            db.session.add(account)
            accounts.append(account)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'accounts': [
                {
                    'account_id': a.account_id,
                    'account_name': a.account_name,
                    'industry': a.industry,
                    'vertical': a.vertical
                }
                for a in accounts
            ]
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ============================================================================
# STEP 4: GENERATE INITIAL DATA
# ============================================================================

@onboarding_api.route('/generate-initial-data', methods=['POST'])
def generate_initial_data():
    """Generate initial sample data using config-aware generator"""
    
    data = request.json
    customer_id = data.get('customer_id') or get_current_customer_id()
    months = data.get('months', 12)
    
    if not customer_id:
        return jsonify({'error': 'Customer ID required'}), 400
    
    # Verify prerequisites
    customer = Customer.query.get(customer_id)
    if not customer:
        return jsonify({'error': 'Customer not found'}), 404
    
    config = CustomerConfig.query.filter_by(customer_id=customer_id).first()
    if not config:
        return jsonify({'error': 'Configuration not initialized'}), 400
    
    accounts = Account.query.filter_by(customer_id=customer_id).all()
    if not accounts:
        return jsonify({'error': 'No accounts found'}), 400
    
    account_ids = [str(a.account_id) for a in accounts]
    
    # Run data generator
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    generator_path = os.path.join(backend_dir, 'scripts', 'generate_synthetic_dc2s_data.py')
    
    if not os.path.exists(generator_path):
        return jsonify({'error': f'Generator not found: {generator_path}'}), 500
    
    cmd = [
        'python3',
        generator_path,
        '--customer-id', str(customer_id),
        '--accounts', ','.join(account_ids),
        '--months', str(months),
        '--start-date', '2024-01-01'
    ]
    
    print(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=300,
            cwd=backend_dir
        )
        
        print(f"✅ Data generation successful")
        
        return jsonify({
            'success': True,
            'message': 'Data generated successfully',
            'customer_id': customer_id,
            'accounts': len(account_ids),
            'months': months
        })
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Data generation failed: {e.stderr}")
        return jsonify({
            'success': False,
            'error': 'Data generation failed',
            'details': e.stderr
        }), 500
    
    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'error': 'Data generation timed out'
        }), 500
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================================
# STEP 5: CALCULATE SCORES
# ============================================================================

@onboarding_api.route('/calculate-initial-scores', methods=['POST'])
def calculate_initial_scores():
    """Calculate initial health scores"""
    
    data = request.json
    customer_id = data.get('customer_id') or get_current_customer_id()
    
    if not customer_id:
        return jsonify({'error': 'Customer ID required'}), 400
    
    try:
        from utils.score_calculator import ScoreCalculator
        from datetime import date
        
        calculator = ScoreCalculator(customer_id)
        measurement_month = date(2024, 12, 1)
        
        accounts = Account.query.filter_by(customer_id=customer_id).all()
        
        results = []
        for account in accounts:
            try:
                result = calculator.calculate_scores_for_account(
                    account.account_id,
                    measurement_month
                )
                
                if result and result.get('health_score'):
                    results.append({
                        'account_id': account.account_id,
                        'account_name': account.account_name,
                        'health_score': float(result['health_score']['health_score']),
                        'status': result['health_score']['health_status']
                    })
            except Exception as e:
                print(f"Error calculating scores for account {account.account_id}: {e}")
        
        return jsonify({
            'success': True,
            'customer_id': customer_id,
            'accounts_scored': len(results),
            'results': results
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================================
# COMPLETE ONBOARDING (ALL STEPS)
# ============================================================================

@onboarding_api.route('/complete', methods=['POST'])
def complete_onboarding():
    """
    Complete end-to-end onboarding
    
    Steps:
    1. Create customer
    2. Initialize config
    3. Create sample accounts
    4. Generate initial data
    5. Calculate initial scores
    """
    
    data = request.json
    
    customer_name = data.get('customer_name')
    industry = data.get('industry', 'Technology')
    
    if not customer_name:
        return jsonify({'error': 'customer_name required'}), 400
    
    try:
        # Step 1: Create customer
        print(f"\n1️⃣  Creating customer: {customer_name}")
        customer = Customer(
            customer_name=customer_name
        )
        db.session.add(customer)
        db.session.commit()
        customer_id = customer.customer_id
        print(f"   ✅ Customer created (ID: {customer_id})")
        
        # Step 2: Initialize config
        print(f"\n2️⃣  Initializing configuration")
        config = CustomerConfig(
            customer_id=customer_id,
            vertical='dc2_s',
            dc2s_pillar_weights={
                'AI': 0.25, 'CH': 0.20, 'DV': 0.15, 'EX': 0.20, 'OS': 0.20
            },
            dc2s_enabled_kpis=[
                'AI-KPI1', 'AI-KPI2', 'AI-KPI3',
                'CH-KPI1', 'CH-KPI2', 'CH-KPI3',
                'DV-KPI1', 'DV-KPI2', 'DV-KPI3',
                'EX-KPI1', 'EX-KPI2', 'EX-KPI3',
                'OS-KPI1', 'OS-KPI2', 'OS-KPI3'
            ],
            dc2s_kpi_definitions={},
            dc2s_kpi_weights={
                'AI': {'AI-KPI1': 0.35, 'AI-KPI2': 0.35, 'AI-KPI3': 0.30},
                'CH': {'CH-KPI1': 0.40, 'CH-KPI2': 0.35, 'CH-KPI3': 0.25},
                'DV': {'DV-KPI1': 0.40, 'DV-KPI2': 0.35, 'DV-KPI3': 0.25},
                'EX': {'EX-KPI1': 0.40, 'EX-KPI2': 0.35, 'EX-KPI3': 0.25},
                'OS': {'OS-KPI1': 0.40, 'OS-KPI2': 0.35, 'OS-KPI3': 0.25}
            }
        )
        db.session.add(config)
        db.session.commit()
        print(f"   ✅ Configuration initialized")
        
        # Step 3: Create accounts (using correct Account fields)
        print(f"\n3️⃣  Creating sample accounts")
        accounts = []
        for i, env in enumerate(['Production', 'Staging', 'Development']):
            account = Account(
                customer_id=customer_id,
                account_name=f'{customer_name}-{env}',
                industry=industry,          # ✅ Correct field
                vertical='dc2_s',           # ✅ Correct field
                region='us-west-2',         # ✅ Correct field
                account_status='active'     # ✅ Correct field
            )
            db.session.add(account)
            accounts.append(account)
        
        db.session.commit()
        account_ids = [a.account_id for a in accounts]
        print(f"   ✅ Created {len(accounts)} accounts")
        
        # Step 4: Generate data
        print(f"\n4️⃣  Generating sample data")
        
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        cmd = [
            'python3',
            os.path.join(backend_dir, 'scripts', 'generate_synthetic_dc2s_data.py'),
            '--customer-id', str(customer_id),
            '--accounts', ','.join(str(aid) for aid in account_ids),
            '--months', '12'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, cwd=backend_dir)
        
        if result.returncode != 0:
            raise Exception(f"Data generation failed: {result.stderr}")
        
        print(f"   ✅ Data generated")
        
        # Step 5: Calculate scores
        print(f"\n5️⃣  Calculating initial scores")
        from utils.score_calculator import ScoreCalculator
        from datetime import date
        
        calculator = ScoreCalculator(customer_id)
        measurement_month = date(2024, 12, 1)
        
        for account_id in account_ids:
            calculator.calculate_scores_for_account(account_id, measurement_month)
        
        print(f"   ✅ Scores calculated")
        
        return jsonify({
            'success': True,
            'customer_id': customer_id,
            'customer_name': customer_name,
            'accounts': len(account_ids),
            'industry': industry,
            'message': 'Onboarding complete!',
            'next_steps': [
                'Login to system',
                'Configure KPIs at /dc-dashboard/settings',
                'View dashboard at /dc-dashboard'
            ]
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Onboarding failed: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            'success': False,
            'error': 'Onboarding failed',
            'details': str(e)
        }), 500
