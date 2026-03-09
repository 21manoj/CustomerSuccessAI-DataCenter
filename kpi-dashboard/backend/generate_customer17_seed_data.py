#!/usr/bin/env python3
"""
Generate Seed Data CSV Files for Customer 17 (Data Center)
===========================================================

This script generates 5 CSV files for a new data center customer:
1. accounts.csv - Account list with metadata
2. kpis.csv - Historical KPI measurements (with date field)
3. signals.csv - Qualitative signals
4. products.csv - Product associations
5. profiles.csv - Comprehensive account profiles

Usage:
    python3 generate_customer17_seed_data.py --output-dir ./verticals/customer17-dc2_s/data
"""

import sys
import os
import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app_v3_minimal import app, db
from models import Customer, User
from werkzeug.security import generate_password_hash

# Customer 17 configuration
CUSTOMER_ID = 17
CUSTOMER_NAME = "DataCenter Solutions Inc"
CUSTOMER_EMAIL = "admin@datacenter-solutions.com"
CUSTOMER_DOMAIN = "datacenter-solutions.com"

# Account configuration
NUM_ACCOUNTS = 10
BASE_ACCOUNT_ID = 17001  # Start account IDs from 17001

# Data generation parameters
NUM_MONTHS_HISTORICAL = 12  # 12 months of historical data
START_DATE = datetime(2024, 1, 1)

# Account names and types
ACCOUNT_NAMES = [
    "AI Compute Corp", "CloudScale Dynamics", "DataForge Systems", 
    "NeuralNet Industries", "QuantumCloud Solutions", "SecureAI Labs",
    "TechVantage Data", "InnovateCompute Inc", "SmartData Enterprises",
    "FutureCompute Systems"
]

ACCOUNT_TYPES = [
    "Success Story", "Steady Performer", "Expansion Play", "Recovery",
    "Near-Miss Recovery", "Rocket Ship", "Strategic Expansion"
]

INDUSTRIES = [
    "AI/ML Research", "Financial Services", "Healthcare AI", "Autonomous Vehicles",
    "Manufacturing/Robotics", "Media & Entertainment", "Retail", "Biotechnology"
]

ACCOUNT_TIERS = ["Enterprise", "Mid-Market"]
PARTNER_IDS = ["P001", "P002", "P003", "P004"]
PARTNER_NAMES = ["TechSolutions Inc", "CloudScale Partners", "DataCenter Pros", "Quantum Resellers"]
PARTNER_TIERS = ["Strategic", "Tier 1", "Tier 2"]
DATACENTER_LOCATIONS = [
    "US-West (Oregon)", "US-East (Virginia)", "US-Central (Chicago)",
    "US-West (California)", "US-East (New York)", "US-West (Los Angeles)"
]
CSM_ASSIGNED = ["Sarah Chen", "Marcus Johnson", "Emily Rodriguez", "David Park"]

# KPI codes (DC2_S vertical KPIs) — P-format only
KPI_CODES = [
    # P1 - Deployment Velocity
    "P1-KPI1", "P1-KPI2", "P1-KPI3", "P1-KPI4", "P1-KPI5", "P1-KPI6",
    # P2 - Operational Stability
    "P2-KPI1", "P2-KPI2", "P2-KPI3", "P2-KPI4", "P2-KPI5", "P2-KPI6", "P2-KPI7",
    # P3 - AI Workload Performance
    "P3-KPI1", "P3-KPI2", "P3-KPI3", "P3-KPI4", "P3-KPI5", "P3-KPI6",
    # P4 - Channel & Partner Health
    "P4-KPI1", "P4-KPI2", "P4-KPI3", "P4-KPI4", "P4-KPI5", "P4-KPI6",
    # P5 - Expansion Readiness
    "P5-KPI1", "P5-KPI2", "P5-KPI3", "P5-KPI4", "P5-KPI5", "P5-KPI6", "P5-KPI7", "P5-KPI8"
]

# Product IDs
PRODUCT_IDS = ["PRD-001", "PRD-002", "PRD-003", "PRD-004", "PRD-005", "PRD-006", "PRD-007"]
PRODUCT_NAMES = [
    "GPU Cloud - H100", "GPU Cloud - A100", "Premium Support", "Multi-Datacenter",
    "AI Platform Suite", "Managed Services", "Training & Certification"
]

# Signal types and stakeholders
SIGNAL_TYPES = ["email", "call", "meeting", "slack"]
STAKEHOLDER_LEVELS = ["Manager", "Director", "VP", "C-suite"]
STAKEHOLDER_TITLES = [
    "Engineering Manager", "VP Engineering", "CTO", "CFO", "CEO",
    "Operations Manager", "IT Manager", "Director ML", "Director Infrastructure"
]
SENTIMENTS = ["positive", "neutral", "negative"]


def create_customer_17():
    """Create customer 17 and initial user"""
    with app.app_context():
        # Check if customer already exists
        customer = Customer.query.filter_by(customer_id=CUSTOMER_ID).first()
        if customer:
            print(f"✅ Customer {CUSTOMER_ID} already exists: {customer.customer_name}")
        else:
            customer = Customer(
                customer_id=CUSTOMER_ID,
                customer_name=CUSTOMER_NAME,
                email=CUSTOMER_EMAIL,
                domain=CUSTOMER_DOMAIN
            )
            db.session.add(customer)
            db.session.flush()
            print(f"✅ Created customer {CUSTOMER_ID}: {CUSTOMER_NAME}")
        
        # Create initial user
        user = User.query.filter_by(email=CUSTOMER_EMAIL).first()
        if not user:
            user = User(
                customer_id=CUSTOMER_ID,
                user_name="admin",
                email=CUSTOMER_EMAIL,
                password_hash=generate_password_hash("DC17_Admin_2024!")
            )
            db.session.add(user)
            db.session.commit()
            print(f"✅ Created user: {CUSTOMER_EMAIL}")
        else:
            print(f"✅ User already exists: {CUSTOMER_EMAIL}")
        
        return customer


def generate_accounts_csv(output_dir):
    """Generate accounts.csv"""
    print("\n[1/5] Generating accounts.csv...")
    
    accounts = []
    for i in range(NUM_ACCOUNTS):
        account_id = BASE_ACCOUNT_ID + i
        account_name = ACCOUNT_NAMES[i]
        account_type = random.choice(ACCOUNT_TYPES)
        industry = random.choice(INDUSTRIES)
        account_tier = random.choice(ACCOUNT_TIERS)
        
        # Generate realistic ARR values based on account type
        initial_arr = random.randint(1000000, 6000000)
        
        # Adjust growth based on account type
        if account_type == "Recovery" or account_type == "Near-Miss Recovery":
            arr_growth = random.uniform(0.05, 0.50)  # 5% to 50% for recovery
        elif account_type == "Rocket Ship":
            arr_growth = random.uniform(1.0, 2.0)  # 100% to 200% for rocket ships
        elif account_type == "Success Story":
            arr_growth = random.uniform(0.5, 1.5)  # 50% to 150% for success stories
        elif account_type == "Steady Performer":
            arr_growth = random.uniform(0.05, 0.20)  # 5% to 20% for steady
        elif account_type == "Expansion Play" or account_type == "Strategic Expansion":
            arr_growth = random.uniform(0.3, 0.8)  # 30% to 80% for expansion
        else:
            arr_growth = random.uniform(-0.3, 0.5)  # Default range
        
        final_arr = max(0, int(initial_arr * (1 + arr_growth)))
        
        # Contract dates
        contract_start = START_DATE + timedelta(days=random.randint(0, 30))
        contract_end = contract_start + timedelta(days=365)
        
        # Partner info
        partner_idx = random.randint(0, len(PARTNER_IDS) - 1)
        partner_id = PARTNER_IDS[partner_idx]
        partner_name = PARTNER_NAMES[partner_idx]
        partner_tier = PARTNER_TIERS[min(partner_idx, len(PARTNER_TIERS) - 1)]
        
        # GPU count
        gpu_count = random.choice([64, 96, 128, 192, 256, 320, 384])
        datacenter_location = random.choice(DATACENTER_LOCATIONS)
        csm_assigned = random.choice(CSM_ASSIGNED)
        
        # Journey type based on account type
        journey_types = {
            "Success Story": "healthy_expansion",
            "Steady Performer": "stable",
            "Expansion Play": "strategic_expansion",
            "Recovery": "recovery",
            "Near-Miss Recovery": "recovery",
            "Rocket Ship": "rapid_growth",
            "Strategic Expansion": "strategic_expansion"
        }
        journey_type = journey_types.get(account_type, "stable")
        
        # Outcome
        if arr_growth > 0:
            outcome = f"{arr_growth*100:.1f}% growth"
        else:
            outcome = f"{abs(arr_growth)*100:.1f}% contraction"
        
        accounts.append({
            'account_id': account_id,
            'customer_id': CUSTOMER_ID,
            'account_name': account_name,
            'account_type': account_type,
            'industry': industry,
            'account_tier': account_tier,
            'initial_arr': initial_arr,
            'final_arr': final_arr,
            'contract_start_date': contract_start.strftime('%Y-%m-%d'),
            'contract_end_date': contract_end.strftime('%Y-%m-%d'),
            'partner_id': partner_id,
            'partner_name': partner_name,
            'partner_tier': partner_tier,
            'gpu_count': gpu_count,
            'datacenter_location': datacenter_location,
            'csm_assigned': csm_assigned,
            'executive_sponsor': random.choice(['', 'VP Customer Success', 'CRO', 'VP Engineering']),
            'journey_type': journey_type,
            'outcome': outcome,
            'has_narrative': random.choice([True, False])
        })
    
    # Write CSV
    csv_path = os.path.join(output_dir, 'accounts.csv')
    with open(csv_path, 'w', newline='') as f:
        if accounts:
            writer = csv.DictWriter(f, fieldnames=accounts[0].keys())
            writer.writeheader()
            writer.writerows(accounts)
    
    print(f"   ✅ Generated {len(accounts)} accounts → {csv_path}")
    return accounts


def generate_kpis_csv(accounts, output_dir):
    """Generate kpis.csv (historical KPI measurements)"""
    print("\n[2/5] Generating kpis.csv...")
    
    kpis = []
    measurement_id_counter = 1
    
    for account in accounts:
        account_id = account['account_id']
        account_type = account['account_type']
        is_recovery = 'Recovery' in account_type
        
        # For recovery accounts, determine crisis month (typically month 2-4)
        crisis_month = random.randint(2, 4) if is_recovery else None
        recovery_start_month = crisis_month + 1 if crisis_month else None
        
        # Generate KPIs for each month
        for month_offset in range(NUM_MONTHS_HISTORICAL):
            measurement_date = START_DATE + timedelta(days=30 * month_offset)
            date_str = measurement_date.strftime('%Y-%m-%d')
            month_num = month_offset + 1
            
            # Recovery modifier: lower values during crisis, improving after
            if is_recovery and crisis_month:
                if month_num < crisis_month:
                    recovery_modifier = 1.0  # Normal
                elif month_num == crisis_month:
                    recovery_modifier = 0.6  # Crisis - 40% drop
                elif month_num <= recovery_start_month + 2:
                    recovery_modifier = 0.7 + (month_num - crisis_month) * 0.1  # Gradual recovery
                else:
                    recovery_modifier = 1.0 + (month_num - recovery_start_month - 2) * 0.05  # Above baseline
            else:
                recovery_modifier = 1.0
            
            # Generate measurements for each KPI code
            for kpi_code in KPI_CODES:
                # Generate realistic values based on KPI category
                if 'DV-' in kpi_code:  # Data Velocity
                    base_value = random.uniform(5.0, 20.0)
                    value = base_value * recovery_modifier
                    target_value = random.uniform(10.0, 25.0)
                    unit = random.choice(['days', 'hours'])
                elif 'OS-' in kpi_code:  # Operational Stability
                    if 'KPI1' in kpi_code:  # Uptime
                        base_value = random.uniform(99.0, 100.0)
                        value = max(95.0, base_value * recovery_modifier)  # Don't go below 95%
                        target_value = 99.5
                        unit = '%'
                    elif 'KPI2' in kpi_code:  # Hours
                        base_value = random.uniform(500.0, 6000.0)
                        value = base_value * recovery_modifier
                        target_value = random.uniform(500.0, 1000.0)
                        unit = 'hours'
                    else:
                        base_value = random.uniform(0.0, 10.0)
                        value = base_value * (2.0 - recovery_modifier)  # Inverse for incidents
                        target_value = random.uniform(2.0, 15.0)
                        unit = random.choice(['hours', 'minutes', 'incidents/month', '%'])
                elif 'AI-' in kpi_code:  # AI Performance
                    if 'KPI1' in kpi_code:  # Utilization
                        base_value = random.uniform(50.0, 85.0)
                        value = max(40.0, base_value * recovery_modifier)
                        target_value = 65.0
                        unit = '%'
                    else:
                        base_value = random.uniform(40.0, 60.0)
                        value = base_value * recovery_modifier
                        target_value = None
                        unit = random.choice(['hours', 'ms', 'jobs/hour', '$', '%'])
                elif 'CH-' in kpi_code:  # Customer Health
                    if 'KPI1' in kpi_code:  # NPS
                        base_value = random.uniform(70.0, 95.0)
                        value = max(50.0, base_value * recovery_modifier)
                        target_value = 75.0
                        unit = 'score'
                    elif 'KPI4' in kpi_code:  # Revenue
                        value = random.uniform(1000000.0, 10000000.0)
                        target_value = None
                        unit = '$'
                    else:
                        base_value = random.uniform(80.0, 98.0)
                        value = max(60.0, base_value * recovery_modifier)
                        target_value = random.uniform(75.0, 90.0)
                        unit = random.choice(['%', 'score', '$'])
                else:  # EX- Expansion
                    if 'KPI2' in kpi_code:  # Revenue
                        value = random.uniform(1000000.0, 10000000.0)
                        target_value = None
                        unit = '$'
                    else:
                        base_value = random.uniform(50.0, 120.0)
                        value = base_value * recovery_modifier
                        target_value = random.uniform(30.0, 110.0)
                        unit = random.choice(['%', '% MoM', 'score', 'Y/N'])
                
                # Determine health state
                if target_value:
                    if value >= target_value * 0.9:
                        health_state = 'optimal' if value >= target_value else 'healthy'
                    elif value >= target_value * 0.7:
                        health_state = 'at_risk'
                    else:
                        health_state = 'critical'
                else:
                    health_state = random.choice(['optimal', 'healthy', 'at_risk'])
                
                threshold_breached = health_state in ['at_risk', 'critical']
                
                kpis.append({
                    'measurement_id': f'M-{account_id}-{date_str}-{kpi_code}',
                    'account_id': account_id,
                    'kpi_code': kpi_code,
                    'date': date_str,  # This will be used for KPITimeSeries
                    'value': round(value, 2),
                    'target_value': round(target_value, 2) if target_value else '',
                    'health_state': health_state,
                    'threshold_breached': threshold_breached,
                    'unit': unit
                })
                measurement_id_counter += 1
    
    # Write CSV
    csv_path = os.path.join(output_dir, 'kpis.csv')
    with open(csv_path, 'w', newline='') as f:
        if kpis:
            writer = csv.DictWriter(f, fieldnames=kpis[0].keys())
            writer.writeheader()
            writer.writerows(kpis)
    
    print(f"   ✅ Generated {len(kpis)} KPI measurements → {csv_path}")
    return kpis


def generate_signals_csv(accounts, output_dir):
    """Generate signals.csv (qualitative signals)"""
    print("\n[3/5] Generating signals.csv...")
    
    signals = []
    signal_id_counter = 1
    
    for account in accounts:
        account_id = account['account_id']
        account_type = account['account_type']
        is_recovery = 'Recovery' in account_type
        
        # For recovery accounts, determine crisis period
        if is_recovery:
            crisis_start = START_DATE + timedelta(days=random.randint(30, 90))  # Month 1-3
            crisis_end = crisis_start + timedelta(days=random.randint(30, 60))  # 1-2 month crisis
            recovery_period = crisis_end + timedelta(days=random.randint(30, 90))  # Recovery phase
            num_signals = random.randint(20, 30)  # More signals for recovery accounts
        else:
            crisis_start = None
            crisis_end = None
            recovery_period = None
            num_signals = random.randint(15, 25)
        
        for i in range(num_signals):
            # Random date within the year
            days_offset = random.randint(0, 365)
            signal_date = START_DATE + timedelta(days=days_offset)
            
            signal_type = random.choice(SIGNAL_TYPES)
            stakeholder_level = random.choice(STAKEHOLDER_LEVELS)
            stakeholder_title = random.choice(STAKEHOLDER_TITLES)
            
            # For recovery accounts, sentiment depends on timing
            if is_recovery and crisis_start and crisis_end:
                if signal_date < crisis_start:
                    # Pre-crisis: mostly neutral/positive
                    sentiment = random.choice(['positive', 'neutral'])
                elif crisis_start <= signal_date <= crisis_end:
                    # Crisis period: mostly negative
                    sentiment = random.choice(['negative', 'negative', 'negative', 'neutral'])
                elif signal_date <= recovery_period:
                    # Recovery period: mixed, trending positive
                    sentiment = random.choice(['positive', 'positive', 'neutral', 'negative'])
                else:
                    # Post-recovery: mostly positive
                    sentiment = random.choice(['positive', 'positive', 'neutral'])
            else:
                # Normal accounts: random sentiment
                sentiment = random.choice(SENTIMENTS)
            
            # Generate content based on sentiment
            if sentiment == 'positive':
                content_templates = [
                    "Budget approved for growth",
                    "Expansion approved for Q{q}",
                    "Champion advocating for more investment",
                    "Great QBR, discussing expansion",
                    "Want to add more GPUs",
                    "Thinking about additional use cases",
                    "Recovery plan working well",
                    "Performance improvements noted"
                ]
                sentiment_score = random.uniform(0.5, 1.0)
            elif sentiment == 'negative':
                content_templates = [
                    "Concerns about performance",
                    "Budget constraints mentioned",
                    "Evaluating alternatives",
                    "Support ticket escalation",
                    "Technical issues reported",
                    "Critical incident occurred",
                    "Service degradation reported",
                    "Churn risk discussed"
                ]
                sentiment_score = random.uniform(-1.0, -0.3)
            else:
                content_templates = [
                    "Technical review meeting",
                    "Regular check-in call",
                    "Checking in on project status",
                    "Training session completed",
                    "Status update meeting",
                    "Recovery plan discussion"
                ]
                sentiment_score = random.uniform(-0.3, 0.3)
            
            content = random.choice(content_templates)
            if '{q}' in content:
                quarter = (signal_date.month - 1) // 3 + 1
                content = content.replace('{q}', str(quarter))
            
            # Keywords
            keywords = []
            if 'expansion' in content.lower():
                keywords.append('expansion')
            if 'budget' in content.lower():
                keywords.append('budget')
            if sentiment == 'positive':
                keywords.append('growth')
            if 'recovery' in content.lower() or 'crisis' in content.lower():
                keywords.append('recovery')
            
            signals.append({
                'signal_id': f'SIG-{account_id}-{signal_date.strftime("%Y-%m-%d")}-{signal_id_counter}',
                'account_id': account_id,
                'signal_date': signal_date.strftime('%Y-%m-%d'),
                'signal_type': signal_type,
                'stakeholder_level': stakeholder_level,
                'stakeholder_title': stakeholder_title,
                'content': content,
                'sentiment': sentiment,
                'sentiment_score': round(sentiment_score, 2),
                'keywords': ','.join(keywords) if keywords else '',
                'is_narrative_signal': random.choice([True, False])
            })
            signal_id_counter += 1
    
    # Write CSV
    csv_path = os.path.join(output_dir, 'signals.csv')
    with open(csv_path, 'w', newline='') as f:
        if signals:
            writer = csv.DictWriter(f, fieldnames=signals[0].keys())
            writer.writeheader()
            writer.writerows(signals)
    
    print(f"   ✅ Generated {len(signals)} signals → {csv_path}")
    return signals


def generate_products_csv(accounts, output_dir):
    """Generate products.csv (product associations)"""
    print("\n[4/5] Generating products.csv...")
    
    products = []
    
    for account in accounts:
        account_id = account['account_id']
        account_type = account['account_type']
        is_recovery = 'Recovery' in account_type
        
        # Each account has 1-3 products
        num_products = random.randint(1, 3)
        selected_products = random.sample(list(zip(PRODUCT_IDS, PRODUCT_NAMES)), num_products)
        
        # For recovery accounts, Premium Support is often added during crisis
        if is_recovery and 'PRD-003' not in [p[0] for p in selected_products]:
            # Add Premium Support for recovery accounts
            selected_products.append(('PRD-003', 'Premium Support'))
        
        for product_id, product_name in selected_products:
            # Primary product (GPU Cloud)
            is_primary = 'GPU Cloud' in product_name
            
            if is_primary:
                quantity = account['gpu_count']
                # Recovery accounts have lower initial utilization
                if is_recovery:
                    utilization = random.uniform(45.0, 70.0)  # Lower for recovery
                else:
                    utilization = random.uniform(60.0, 85.0)
                monthly_spend = quantity * random.uniform(2000.0, 4500.0)
            else:
                quantity = account['gpu_count'] if 'Support' in product_name or 'Platform' in product_name else 1
                utilization = None
                monthly_spend = random.uniform(20000.0, 200000.0)
            
            # For recovery accounts, Premium Support added during crisis (month 2-3)
            if is_recovery and product_name == 'Premium Support':
                adoption_date_obj = datetime.strptime(account['contract_start_date'], '%Y-%m-%d')
                adoption_date_obj = adoption_date_obj + timedelta(days=random.randint(30, 90))
                adoption_date = adoption_date_obj.strftime('%Y-%m-%d')
            else:
                adoption_date = account['contract_start_date']
            
            status = 'Active'
            usage_level = random.choice(['Heavy', 'Medium', 'Low', 'Active'])
            
            # Satisfaction scores: lower for recovery accounts, especially early products
            if is_recovery:
                if product_name == 'Premium Support':
                    # Premium Support added during crisis - higher satisfaction (helped recovery)
                    satisfaction_score = round(random.uniform(8.5, 9.5), 1)
                elif is_primary:
                    # Primary product - lower satisfaction initially, improving
                    satisfaction_score = round(random.uniform(6.5, 8.5), 1)
                else:
                    # Other products - moderate satisfaction
                    satisfaction_score = round(random.uniform(7.0, 8.5), 1)
            else:
                satisfaction_score = round(random.uniform(7.0, 9.5), 1)
            
            # Notes for recovery accounts
            if is_recovery and product_name == 'Premium Support':
                notes = f'Added DURING CRISIS. Critical for recovery. {account["account_name"]}'
            elif is_recovery and is_primary:
                notes = f'{product_name} for {account["account_name"]}. Recovery in progress.'
            else:
                notes = f'{product_name} for {account["account_name"]}'
            
            products.append({
                'account_id': account_id,
                'product_id': product_id,
                'product_name': product_name,
                'quantity': quantity,
                'adoption_date': adoption_date,
                'status': status,
                'usage_level': usage_level,
                'utilization_percent': round(utilization, 1) if utilization else '',
                'monthly_spend': round(monthly_spend, 2) if monthly_spend else '',
                'satisfaction_score': satisfaction_score,
                'primary_product': is_primary,
                'expansion_potential': random.choice(['High', 'Medium', 'Low', 'Very Low']),
                'churn_risk': 'High' if is_recovery and not is_primary else random.choice(['Very Low', 'Low', 'Medium', 'High']),
                'last_usage_date': '2024-12-31',
                'feature_adoption_rate': random.randint(50, 100) if not is_recovery else random.randint(40, 85),
                'notes': notes
            })
    
    # Write CSV
    csv_path = os.path.join(output_dir, 'products.csv')
    with open(csv_path, 'w', newline='') as f:
        if products:
            writer = csv.DictWriter(f, fieldnames=products[0].keys())
            writer.writeheader()
            writer.writerows(products)
    
    print(f"   ✅ Generated {len(products)} product associations → {csv_path}")
    return products


def generate_profiles_csv(accounts, output_dir):
    """Generate profiles.csv (comprehensive account profiles)"""
    print("\n[5/5] Generating profiles.csv...")
    
    profiles = []
    
    for account in accounts:
        account_id = account['account_id']
        account_name = account['account_name']
        
        # Calculate derived fields
        arr_growth_amount = account['final_arr'] - account['initial_arr']
        arr_growth_percent = (arr_growth_amount / account['initial_arr'] * 100) if account['initial_arr'] > 0 else 0
        
        # Generate comprehensive profile
        profile = {
            'account_id': account_id,
            'customer_id': CUSTOMER_ID,
            'account_name': account_name,
            'account_nickname': account['account_type'],
            'industry': account['industry'],
            'industry_subcategory': f"{account['industry']} - {random.choice(['Research', 'Development', 'Production'])}",
            'account_tier': account['account_tier'],
            'company_size': random.choice(['Small (50-100 employees)', 'Medium (100-500 employees)', 'Large (500+ employees)']),
            'annual_revenue': random.randint(20000000, 300000000),
            'employee_count': random.randint(100, 2000),
            'initial_arr': account['initial_arr'],
            'current_arr': account['final_arr'],
            'arr_growth_amount': int(arr_growth_amount),
            'arr_growth_percent': round(arr_growth_percent, 1),
            'expansion_count': 1 if arr_growth_amount > 0 else 0,
            'total_expansion_value': int(arr_growth_amount) if arr_growth_amount > 0 else 0,
            'average_expansion_value': int(arr_growth_amount) if arr_growth_amount > 0 else 0,
            'contraction_count': 1 if arr_growth_amount < 0 else 0,
            'lifetime_value_3yr': int(account['final_arr'] * 3),
            'contract_start_date': account['contract_start_date'],
            'contract_end_date': account['contract_end_date'],
            'contract_term_months': 12,
            'renewal_likelihood': random.randint(60, 98),
            'contract_type': 'Enterprise Agreement' if account['account_tier'] == 'Enterprise' else 'Standard Agreement',
            'payment_terms': 'Annual',
            'billing_frequency': 'Annual',
            'overall_health_score': random.randint(55, 99),
            'health_score_trend': random.choice(['Improving', 'Stable', 'Declining']),
            'health_score_trajectory': random.choice(['Excellent', 'Healthy Stable', 'Recovery', 'At Risk']),
            'nps_score': random.randint(5, 10),
            'nps_trend': random.choice(['Improving', 'Stable', 'Declining']),
            'csat_score': round(random.uniform(7.0, 9.5), 1),
            'executive_engagement_level': random.choice(['Very High', 'High', 'Medium', 'Low']),
            'champion_strength': random.choice(['Very Strong', 'Strong', 'Moderate', 'Weak']),
            'champion_name': f"{random.choice(['Dr.', 'Mr.', 'Ms.'])} {random.choice(['Smith', 'Johnson', 'Williams', 'Brown', 'Jones'])} ({random.choice(['VP', 'Director', 'Manager'])} {random.choice(['Engineering', 'Operations', 'IT'])})",
            'champion_tenure_months': random.randint(6, 48),
            'champion_risk': random.choice(['Very Low', 'Low', 'Medium', 'High']),
            'csm_assigned': account['csm_assigned'],
            'account_executive': 'Michael Chen',
            'solutions_architect': 'David Kumar',
            'executive_sponsor': account.get('executive_sponsor', ''),
            'executive_sponsor_engagement': random.choice(['Very High', 'High', 'Medium', 'None']) if account.get('executive_sponsor') else 'None',
            'qbr_frequency': random.choice(['Quarterly', 'Monthly', 'Never scheduled']),
            'qbrs_completed_ytd': random.randint(0, 4),
            'last_qbr_date': '2024-12-15' if random.random() > 0.3 else '',
            'next_qbr_date': '2025-03-15' if random.random() > 0.3 else '',
            'gpu_count_initial': account['gpu_count'],
            'gpu_count_current': account['gpu_count'] + random.randint(0, 128),
            'gpu_type': random.choice(['NVIDIA H100', 'NVIDIA A100']),
            'datacenter_location': account['datacenter_location'],
            'datacenter_count': random.randint(1, 2),
            'average_gpu_utilization': round(random.uniform(50.0, 85.0), 1),
            'utilization_trend': random.choice(['Stable High', 'Recovering', 'Stable', 'Declining']),
            'workload_types': random.choice(['AI Training, LLM Fine-tuning', 'Financial Modeling, Risk Analysis', 'Medical Imaging, Diagnostic AI', 'Autonomous Driving, Simulation']),
            'primary_use_case': random.choice(['Large Language Model Research', 'High-Frequency Trading Models', 'AI-Powered Medical Diagnostics', 'Self-Driving Vehicle AI Training']),
            'technical_complexity': random.choice(['High', 'Very High', 'Medium']),
            'partner_id': account['partner_id'],
            'partner_name': account['partner_name'],
            'partner_tier': account['partner_tier'],
            'partner_satisfaction': round(random.uniform(6.0, 9.5), 1),
            'partner_engagement_level': random.choice(['Excellent', 'Good', 'Poor']),
            'partner_value_delivered': random.choice(['Very High', 'High', 'Medium', 'Low']),
            'journey_type': account['journey_type'],
            'journey_phase': random.choice(['Growth & Partnership', 'Recovery & Stabilization', 'Rapid Expansion', 'Steady State', 'At Risk']),
            'customer_maturity': random.choice(['Advanced', 'Intermediate', 'Early']),
            'adoption_stage': random.choice(['Full Production', 'Production', 'Struggling', 'Failed Adoption']),
            'time_to_value_days': random.randint(10, 25),
            'time_to_production_days': random.randint(15, 35),
            'onboarding_completion': random.randint(70, 100),
            'feature_adoption_rate': random.randint(50, 95),
            'playbook_executions_count': random.randint(0, 10),
            'playbook_success_rate': random.randint(70, 100),
            'proactive_interventions': random.randint(2, 10),
            'reactive_interventions': random.randint(0, 5),
            'escalations_ytd': random.randint(0, 3),
            'support_tickets_ytd': random.randint(0, 20),
            'p1_incidents_ytd': random.randint(0, 2),
            'average_resolution_time_hours': round(random.uniform(2.0, 20.0), 1),
            'churn_risk_level': random.choice(['Very Low', 'Low', 'Medium', 'High']),
            'churn_risk_score': random.randint(2, 75),
            'expansion_opportunity': random.choice(['High', 'Medium', 'Low', 'None']),
            'expansion_readiness_score': random.randint(0, 90),
            'competitive_risk': random.choice(['Low', 'Medium', 'High']),
            'competitive_threats': random.choice(['', 'AWS', 'AWS (dormant)', 'AWS (active discussions)']),
            'budget_risk': random.choice(['Low', 'Medium', 'High', 'Critical']),
            'champion_risk_level': random.choice(['Very Low', 'Low', 'Medium', 'High']),
            'strategic_account': random.choice([True, False]),
            'reference_customer': random.choice([True, False]),
            'case_study_approved': random.choice([True, False]),
            'logo_usage_approved': random.choice([True, False]),
            'innovation_partner': random.choice([True, False]),
            'advisory_board_member': random.choice([True, False]),
            'co_marketing_opportunities': random.choice([True, False]),
            'previous_vendor': random.choice(['', 'AWS', 'On-premises', 'On-premises + AWS (hybrid)']),
            'competitive_wins': random.randint(0, 5),
            'competitive_losses': random.randint(0, 2),
            'win_reasons': random.choice(['', 'Better performance, proactive support', 'Lower latency, better performance', 'Healthcare expertise, HIPAA compliance']),
            'differentiation': random.choice(['', 'Proactive capacity planning, executive engagement', 'Financial services expertise', 'Healthcare AI specialization']),
            'monthly_active_users': random.randint(10, 200),
            'power_users_count': random.randint(5, 50),
            'platform_login_frequency': random.choice(['Daily', 'Weekly', 'Monthly']),
            'api_usage_volume': random.choice(['Very High', 'High', 'Medium', 'Low']),
            'training_sessions_completed': random.randint(2, 25),
            'certification_count': random.randint(0, 20),
            'payment_history': random.choice(['Excellent', 'Good', 'Poor']),
            'payment_timeliness': random.randint(90, 100),
            'days_sales_outstanding': random.randint(0, 30),
            'credit_risk': random.choice(['None', 'Low', 'Medium']),
            'budget_approved_next_year': random.choice([True, False]),
            'budget_amount_next_year': random.randint(2000000, 15000000) if random.random() > 0.3 else 0,
            'first_value_milestone_date': account['contract_start_date'],
            'first_expansion_date': account['contract_start_date'] if arr_growth_amount > 0 else '',
            'strategic_partnership_date': '',
            'reference_customer_date': '',
            'key_strengths': random.choice(['Strong technical team', 'Clear strategy', 'Excellent partnership', 'Proactive engagement']),
            'key_risks': random.choice(['', 'Q2 health dip', 'No executive sponsor', 'Moderate champion strength']),
            'success_factors': random.choice(['Proactive expansion planning', 'Executive sponsorship', 'Strong partner', 'Recovery playbooks executed']),
            'expansion_pipeline': random.choice(['', '$3M Phase 3 expansion budgeted', 'Potential $400K expansion in Q2 2025']),
            'executive_summary': f"{account_name} - {account['account_type']}. {arr_growth_percent:.1f}% ARR change.",
            'narrative_available': random.choice([True, False]),
            'proof_point_category': random.choice(['Proactive Expansion Success', 'Recovery Success', 'Rapid Growth Success', 'Steady Growth'])
        }
        
        profiles.append(profile)
    
    # Write CSV
    csv_path = os.path.join(output_dir, 'profiles.csv')
    with open(csv_path, 'w', newline='') as f:
        if profiles:
            writer = csv.DictWriter(f, fieldnames=profiles[0].keys())
            writer.writeheader()
            writer.writerows(profiles)
    
    print(f"   ✅ Generated {len(profiles)} account profiles → {csv_path}")
    return profiles


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate seed data CSV files for Customer 17')
    parser.add_argument('--output-dir', type=str, default='./verticals/customer17-dc2_s/data',
                        help='Output directory for CSV files (default: ./verticals/customer17-dc2_s/data)')
    parser.add_argument('--create-customer', action='store_true',
                        help='Create customer 17 in database')
    
    args = parser.parse_args()
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"📁 Output directory: {output_dir.absolute()}")
    
    # Create customer if requested
    if args.create_customer:
        create_customer_17()
    
    # Generate CSV files
    print("\n" + "=" * 70)
    print("GENERATING SEED DATA CSV FILES FOR CUSTOMER 17")
    print("=" * 70)
    
    accounts = generate_accounts_csv(output_dir)
    kpis = generate_kpis_csv(accounts, output_dir)
    signals = generate_signals_csv(accounts, output_dir)
    products = generate_products_csv(accounts, output_dir)
    profiles = generate_profiles_csv(accounts, output_dir)
    
    print("\n" + "=" * 70)
    print("✅ GENERATION COMPLETE")
    print("=" * 70)
    print(f"\nGenerated files in: {output_dir.absolute()}")
    print(f"  - accounts.csv: {len(accounts)} accounts")
    print(f"  - kpis.csv: {len(kpis)} KPI measurements")
    print(f"  - signals.csv: {len(signals)} qualitative signals")
    print(f"  - products.csv: {len(products)} product associations")
    print(f"  - profiles.csv: {len(profiles)} account profiles")
    print(f"\nAccount IDs: {BASE_ACCOUNT_ID} to {BASE_ACCOUNT_ID + len(accounts) - 1}")
    print(f"\nTo create customer 17 in database, run:")
    print(f"  python3 generate_customer17_seed_data.py --create-customer")


if __name__ == '__main__':
    main()
