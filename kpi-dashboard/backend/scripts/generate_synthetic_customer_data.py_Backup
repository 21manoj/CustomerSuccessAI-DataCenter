#!/usr/bin/env python3
"""
DC2_S SYNTHETIC DATA GENERATOR FOR CUSTOMER ONBOARDING
======================================================
Generates realistic synthetic data for a new Data Center customer.

Outputs 6 CSV files required for onboarding:
1. accounts.csv - Account master data with profile_metadata JSON
2. kpi_measurements.csv - Monthly KPI time-series data
3. qualitative_signals.csv - Emails, meetings, escalations
4. products.csv - Product catalog
5. profiles.csv - Extended account attributes
6. customers.csv (optional) - Tenant-level data

Usage:
  python3 generate_synthetic_customer_data.py --customer-id 18 --num-accounts 10
  
  # Or with defaults:
  python3 generate_synthetic_customer_data.py
"""

import csv
import json
import random
import math
import argparse
from datetime import datetime, timedelta
from pathlib import Path
try:
    from dateutil.relativedelta import relativedelta
except ImportError:
    # Fallback if dateutil not available - use manual month calculation
    def relativedelta(months=0):
        class Relativedelta:
            def __add__(self, dt):
                year = dt.year
                month = dt.month + months
                while month > 12:
                    month -= 12
                    year += 1
                while month < 1:
                    month += 12
                    year -= 1
                return dt.replace(year=year, month=month, day=1)
        return Relativedelta()

# ============================================================
# CONFIGURATION
# ============================================================

DEFAULT_CUSTOMER_ID = 18
DEFAULT_NUM_ACCOUNTS = 10
START_DATE = datetime(2024, 1, 1)
MONTHS = 12

# Account ID formula: customer_id * 1000
# Customer 18 → accounts 18001-18010
# Customer 19 → accounts 19001-19010
def get_account_id_start(customer_id):
    return customer_id * 1000

# ============================================================
# DC2_S KPI STRUCTURE (5 Pillars)
# ============================================================

KPI_STRUCTURE = {
    'AI': {
        'name': 'AI Workload Performance',
        'kpis': [
            {'code': 'AI-KPI1', 'name': 'GPU Utilization', 'unit': '%', 'target': 85.0, 'operator': '>', 'range': (60.0, 95.0)},
            {'code': 'AI-KPI2', 'name': 'AI Workload Efficiency', 'unit': '%', 'target': 80.0, 'operator': '>', 'range': (50.0, 95.0)},
            {'code': 'AI-KPI3', 'name': 'Model Training Time', 'unit': 'hours', 'target': 24.0, 'operator': '<', 'range': (12.0, 72.0)},
            {'code': 'AI-KPI4', 'name': 'Inference Latency', 'unit': 'ms', 'target': 50.0, 'operator': '<', 'range': (10.0, 200.0)},
            {'code': 'AI-KPI5', 'name': 'AI Workload Success Rate', 'unit': '%', 'target': 98.0, 'operator': '>', 'range': (90.0, 100.0)},
            {'code': 'AI-KPI6', 'name': 'AI Resource Allocation', 'unit': '%', 'target': 90.0, 'operator': '>', 'range': (70.0, 100.0)},
        ]
    },
    'CH': {
        'name': 'Customer Health',
        'kpis': [
            {'code': 'CH-KPI1', 'name': 'Overall Health Score', 'unit': 'score', 'target': 85.0, 'operator': '>', 'range': (60.0, 100.0)},
            {'code': 'CH-KPI2', 'name': 'Churn Risk Score', 'unit': 'score', 'target': 20.0, 'operator': '<', 'range': (0.0, 100.0)},
            {'code': 'CH-KPI3', 'name': 'Engagement Score', 'unit': 'score', 'target': 80.0, 'operator': '>', 'range': (50.0, 100.0)},
            {'code': 'CH-KPI4', 'name': 'Support Satisfaction', 'unit': 'score', 'target': 4.5, 'operator': '>', 'range': (3.0, 5.0)},
            {'code': 'CH-KPI5', 'name': 'Product Adoption Rate', 'unit': '%', 'target': 75.0, 'operator': '>', 'range': (50.0, 95.0)},
            {'code': 'CH-KPI6', 'name': 'Time to Value', 'unit': 'days', 'target': 90.0, 'operator': '<', 'range': (30.0, 180.0)},
        ]
    },
    'DV': {
        'name': 'Deployment Velocity',
        'kpis': [
            {'code': 'DV-KPI1', 'name': 'Time to First Workload', 'unit': 'days', 'target': 14.0, 'operator': '<', 'range': (5.0, 60.0)},
            {'code': 'DV-KPI2', 'name': 'Deployment Success Rate', 'unit': '%', 'target': 95.0, 'operator': '>', 'range': (80.0, 100.0)},
            {'code': 'DV-KPI3', 'name': 'Configuration Time', 'unit': 'days', 'target': 5.0, 'operator': '<', 'range': (1.0, 20.0)},
            {'code': 'DV-KPI4', 'name': 'Onboarding Completion', 'unit': '%', 'target': 95.0, 'operator': '>', 'range': (70.0, 100.0)},
            {'code': 'DV-KPI5', 'name': 'Integration Success Rate', 'unit': '%', 'target': 90.0, 'operator': '>', 'range': (70.0, 100.0)},
            {'code': 'DV-KPI6', 'name': 'Deployment Automation', 'unit': '%', 'target': 85.0, 'operator': '>', 'range': (60.0, 100.0)},
        ]
    },
    'EX': {
        'name': 'Expansion & Growth',
        'kpis': [
            {'code': 'EX-KPI1', 'name': 'Expansion Revenue', 'unit': '$M', 'target': 2.0, 'operator': '>', 'range': (0.5, 10.0)},
            {'code': 'EX-KPI2', 'name': 'Upsell Rate', 'unit': '%', 'target': 30.0, 'operator': '>', 'range': (10.0, 60.0)},
            {'code': 'EX-KPI3', 'name': 'Cross-sell Success', 'unit': '%', 'target': 25.0, 'operator': '>', 'range': (5.0, 50.0)},
            {'code': 'EX-KPI4', 'name': 'Renewal Likelihood', 'unit': '%', 'target': 95.0, 'operator': '>', 'range': (70.0, 100.0)},
            {'code': 'EX-KPI5', 'name': 'Expansion Pipeline', 'unit': '$M', 'target': 5.0, 'operator': '>', 'range': (1.0, 20.0)},
            {'code': 'EX-KPI6', 'name': 'Contract Value Growth', 'unit': '%', 'target': 20.0, 'operator': '>', 'range': (0.0, 50.0)},
            {'code': 'EX-KPI7', 'name': 'Reference Willingness', 'unit': 'score', 'target': 4.0, 'operator': '>', 'range': (2.0, 5.0)},
            {'code': 'EX-KPI8', 'name': 'Strategic Partnership Score', 'unit': 'score', 'target': 85.0, 'operator': '>', 'range': (60.0, 100.0)},
        ]
    },
    'OS': {
        'name': 'Operational Stability',
        'kpis': [
            {'code': 'OS-KPI1', 'name': 'System Uptime', 'unit': '%', 'target': 99.9, 'operator': '>', 'range': (98.0, 100.0)},
            {'code': 'OS-KPI2', 'name': 'Mean Time to Resolution', 'unit': 'hours', 'target': 2.0, 'operator': '<', 'range': (1.0, 8.0)},
            {'code': 'OS-KPI3', 'name': 'Incident Rate', 'unit': 'count/month', 'target': 2.0, 'operator': '<', 'range': (0.0, 10.0)},
            {'code': 'OS-KPI4', 'name': 'SLA Compliance', 'unit': '%', 'target': 99.0, 'operator': '>', 'range': (95.0, 100.0)},
            {'code': 'OS-KPI5', 'name': 'Change Success Rate', 'unit': '%', 'target': 98.0, 'operator': '>', 'range': (90.0, 100.0)},
            {'code': 'OS-KPI6', 'name': 'Backup Success Rate', 'unit': '%', 'target': 100.0, 'operator': '>', 'range': (95.0, 100.0)},
            {'code': 'OS-KPI7', 'name': 'RMA Rate', 'unit': '%', 'target': 2.0, 'operator': '<', 'range': (0.0, 5.0)},
        ]
    }
}

# ============================================================
# HEALTH TRAJECTORY SCENARIOS
# ============================================================

HEALTH_SCENARIOS = {
    'improving': {
        'name': 'Critical → At-Risk → Healthy',
        'description': 'Account starts in crisis, receives intervention, improves steadily',
        'start_health': 55,
        'end_health': 88,
        'progression': 'linear_improvement',
        'use_case': 'Demo turnaround success story'
    },
    'declining': {
        'name': 'Healthy → At-Risk → Critical',
        'description': 'Account starts healthy but shows warning signs and declines',
        'start_health': 90,
        'end_health': 60,
        'progression': 'linear_decline',
        'use_case': 'Demo early warning detection and intervention needs'
    },
    'stable_healthy': {
        'name': 'Consistently Healthy',
        'description': 'High-performing account with minor fluctuations',
        'start_health': 88,
        'end_health': 92,
        'progression': 'stable_high',
        'use_case': 'Demo best practices and advocacy opportunities'
    },
    'stable_at_risk': {
        'name': 'Persistently At-Risk',
        'description': 'Account stuck in at-risk zone despite efforts',
        'start_health': 68,
        'end_health': 72,
        'progression': 'stable_medium',
        'use_case': 'Demo need for strategic intervention'
    },
    'volatile': {
        'name': 'Volatile / Unpredictable',
        'description': 'Account swings between healthy and at-risk',
        'start_health': 75,
        'end_health': 75,
        'progression': 'volatile',
        'use_case': 'Demo signal detection and rapid response'
    },
    'plateau_then_improve': {
        'name': 'Plateau → Breakthrough',
        'description': 'Account plateaus at-risk, then breaks through after intervention',
        'start_health': 70,
        'end_health': 86,
        'progression': 'plateau_breakthrough',
        'use_case': 'Demo impact of focused QBR or executive engagement'
    },
    'churn_risk': {
        'name': 'High Churn Risk',
        'description': 'Critical account with declining engagement',
        'start_health': 58,
        'end_health': 45,
        'progression': 'accelerating_decline',
        'use_case': 'Demo churn prevention urgency'
    },
    'new_onboarding': {
        'name': 'New Customer Onboarding',
        'description': 'Recently onboarded, steady improvement expected',
        'start_health': 62,
        'end_health': 82,
        'progression': 'onboarding_ramp',
        'use_case': 'Demo onboarding success metrics'
    }
}

# ============================================================
# SAMPLE DATA TEMPLATES
# ============================================================

COMPANY_NAMES = [
    'CloudScale AI Labs', 'DataFlow Systems', 'QuantumLeap Computing',
    'TechVanguard Inc', 'InnovateDC Solutions', 'HyperScale Networks',
    'NeuralNet Enterprises', 'CyberCore Industries', 'FusionTech Group',
    'VelocityData Corp', 'ApexCloud Systems', 'TitanCompute Inc'
]

INDUSTRIES = [
    'AI Research', 'Financial Services', 'Healthcare', 'E-commerce',
    'Manufacturing', 'Telecommunications', 'Media & Entertainment', 'Education'
]

REGIONS = ['US-West', 'US-East', 'EMEA', 'APAC', 'LATAM']

CSM_NAMES = [
    'Sarah Chen', 'Michael Rodriguez', 'Emily Watson', 'James Park',
    'Lisa Anderson', 'David Kim', 'Rachel Martinez', 'Tom Johnson'
]

PRODUCTS = [
    {'id': 'DC-GPU-H100', 'name': 'DGX H100 Systems', 'category': 'Compute'},
    {'id': 'DC-COOL-LQ', 'name': 'Liquid Cooling Solutions', 'category': 'Infrastructure'},
    {'id': 'DC-STOR-NVMe', 'name': 'NVMe Storage Arrays', 'category': 'Storage'},
    {'id': 'DC-NET-IB', 'name': 'InfiniBand Networking', 'category': 'Networking'},
    {'id': 'DC-MGMT-SW', 'name': 'Management Software Suite', 'category': 'Software'},
    {'id': 'DC-SUP-PREM', 'name': 'Premier Support', 'category': 'Services'},
    {'id': 'DC-SEC-ADV', 'name': 'Advanced Security', 'category': 'Security'},
    {'id': 'DC-MON-AI', 'name': 'AI-Powered Monitoring', 'category': 'Monitoring'}
]

SIGNAL_TEMPLATES = {
    'positive': [
        'Exceeded performance benchmarks this quarter',
        'Successful QBR with expansion discussion initiated',
        'Executive sponsor praised team collaboration',
        'Reference call completed successfully with prospect',
        'Early adoption of new AI acceleration features',
        'Positive feedback on recent infrastructure upgrade',
        'Team member completed advanced certification',
        'Successfully deployed new workload ahead of schedule'
    ],
    'neutral': [
        'Routine technical sync meeting completed',
        'Monthly business review conducted',
        'Scheduled maintenance window executed',
        'Documentation review and updates',
        'Training session on new features delivered',
        'Quarterly capacity planning review',
        'System health check completed',
        'Regular operational status update provided'
    ],
    'negative': [
        'Unexpected system downtime reported',
        'Escalation from operations team regarding performance',
        'Budget concerns raised during planning meeting',
        'Project milestone delayed due to resource constraints',
        'Support ticket unresolved >48 hours',
        'Concerns about cooling efficiency raised',
        'Security compliance audit findings',
        'Integration challenges with existing systems'
    ]
}

# ============================================================
# DATA GENERATION FUNCTIONS
# ============================================================

# ============================================================
# DATA GENERATION FUNCTIONS
# ============================================================

def calculate_health_at_month(scenario, month, total_months=12):
    """Calculate health score at a specific month based on scenario"""
    start = scenario['start_health']
    end = scenario['end_health']
    progression = scenario['progression']
    
    if progression == 'linear_improvement':
        # Steady linear improvement
        return start + (end - start) * (month / total_months)
    
    elif progression == 'linear_decline':
        # Steady linear decline
        return start + (end - start) * (month / total_months)
    
    elif progression == 'stable_high':
        # Minor fluctuations around high value
        import math
        base = (start + end) / 2
        fluctuation = 3 * math.sin(month * math.pi / 6)
        return base + fluctuation
    
    elif progression == 'stable_medium':
        # Minor fluctuations around medium value
        import math
        base = (start + end) / 2
        fluctuation = 2 * math.sin(month * math.pi / 4)
        return base + fluctuation
    
    elif progression == 'volatile':
        # Large swings
        import math
        base = (start + end) / 2
        fluctuation = 12 * math.sin(month * math.pi / 3)
        return max(50, min(95, base + fluctuation))
    
    elif progression == 'plateau_breakthrough':
        # Plateau for 6 months, then improve
        if month < 6:
            return start + random.uniform(-2, 2)
        else:
            # Accelerated improvement after month 6
            return start + (end - start) * ((month - 6) / 6) ** 1.5
    
    elif progression == 'accelerating_decline':
        # Decline accelerates over time
        decline_pct = (month / total_months) ** 2
        return start + (end - start) * decline_pct
    
    elif progression == 'onboarding_ramp':
        # S-curve improvement typical of onboarding
        import math
        # Sigmoid function
        x = (month / total_months) * 12 - 6  # Center sigmoid
        sigmoid = 1 / (1 + math.exp(-x))
        return start + (end - start) * sigmoid
    
    else:
        # Default to linear
        return start + (end - start) * (month / total_months)


def generate_accounts(customer_id, num_accounts, industry=None, company_name=None):
    """Generate accounts.csv with assigned health scenarios"""
    accounts = []
    account_id_start = get_account_id_start(customer_id)
    
    # Use provided industry or default to random selection
    selected_industry = industry if industry else random.choice(INDUSTRIES)
    
    # Generate account name variations from company_name if provided
    account_name_suffixes = [
        'Datacenter East', 'Cloud Ops', 'AI Lab', 'Production', 'Development',
        'HQ Operations', 'Regional Office', 'Research Center', 'Data Center West', 'Infrastructure'
    ]
    
    # Assign scenarios to accounts cyclically
    scenario_keys = list(HEALTH_SCENARIOS.keys())
    
    for i in range(num_accounts):
        account_id = account_id_start + i + 1
        
        # Assign scenario cyclically
        scenario_key = scenario_keys[i % len(scenario_keys)]
        scenario = HEALTH_SCENARIOS[scenario_key]
        
        # Current health (end state)
        current_health = scenario['end_health']
        
        # Determine lifecycle stage based on current health
        if current_health >= 85:
            lifecycle = random.choice(['expansion', 'advocacy'])
        elif current_health >= 70:
            lifecycle = random.choice(['adoption', 'value_realization'])
        else:
            lifecycle = random.choice(['onboarding', 'at_risk'])
        
        # Generate account name
        if company_name:
            account_name = f"{company_name} - {account_name_suffixes[i % len(account_name_suffixes)]}"
        else:
            account_name = COMPANY_NAMES[i % len(COMPANY_NAMES)]
        
        profile_metadata = {
            'assigned_csm': random.choice(CSM_NAMES),
            'csm_manager': random.choice(['Jennifer Kim', 'Robert Chang']),
            'account_owner': random.choice(['Alex Thompson', 'Maria Garcia']),
            'account_tier': random.choice(['Enterprise', 'Strategic', 'Commercial']),
            'products_used': random.sample([p['id'] for p in PRODUCTS], k=random.randint(3, 6)),
            'engagement': {
                'lifecycle_stage': lifecycle,
                'onboarding_status': 'completed' if current_health > 70 else 'in_progress',
                'last_qbr_date': (datetime.now() - timedelta(days=random.randint(30, 90))).strftime('%Y-%m-%d'),
                'next_qbr_date': (datetime.now() + timedelta(days=random.randint(30, 90))).strftime('%Y-%m-%d'),
                'engagement_score': int(current_health)
            },
            'champions': {
                'primary_champion': f"Dr. {random.choice(['Smith', 'Johnson', 'Williams', 'Brown', 'Davis', 'Miller'])}",
                'champion_title': random.choice(['CTO', 'VP Engineering', 'Director of Infrastructure']),
                'executive_sponsor': random.choice(['CEO', 'CFO', 'COO'])
            },
            'contract': {
                'start_date': '2024-01-01',
                'end_date': '2025-12-31',
                'contract_value': random.randint(500000, 5000000),
                'renewal_date': '2025-12-31'
            },
            'health_scenario': {
                'scenario_key': scenario_key,
                'scenario_name': scenario['name'],
                'description': scenario['description'],
                'start_health': scenario['start_health'],
                'end_health': scenario['end_health'],
                'use_case': scenario['use_case']
            }
        }
        
        accounts.append({
            'account_id': account_id,
            'customer_id': customer_id,
            'account_name': account_name,
            'revenue': random.uniform(500000, 5000000),
            'industry': selected_industry,  # Use provided industry for all accounts
            'region': random.choice(REGIONS),
            'account_status': 'active',
            'external_account_id': f'EXT-{customer_id}-{account_id}',
            'profile_metadata': profile_metadata,
            # Store scenario for KPI generation
            '_scenario': scenario,
            '_scenario_key': scenario_key
        })
    
    return accounts


def generate_kpi_measurements(accounts):
    """Generate kpi_measurements.csv with time-based health progression"""
    rows = []
    
    for account in accounts:
        scenario = account['_scenario']
        
        for pillar_code, pillar_data in KPI_STRUCTURE.items():
            for kpi in pillar_data['kpis']:
                # Generate monthly data with progressive health
                # CRITICAL: Only one row per (account_id, kpi_code, measurement_month) combination
                # Database has unique constraint on these three fields
                for month_offset in range(MONTHS):
                    # Use calendar months, not 30-day increments, to avoid duplicates
                    from dateutil.relativedelta import relativedelta
                    date = START_DATE + relativedelta(months=month_offset)
                    # Use first day of month for measurement_month to ensure consistency
                    measurement_month = date.replace(day=1).strftime('%Y-%m-%d')
                    
                    # Calculate health at this specific month
                    health_at_month = calculate_health_at_month(scenario, month_offset, MONTHS)
                    
                    # Determine improvement rate based on health
                    if health_at_month >= 85:
                        target_pct = 0.85  # Performing well
                    elif health_at_month >= 70:
                        target_pct = 0.70  # Meeting targets
                    else:
                        target_pct = 0.55  # Below targets
                    
                    target = kpi['target']
                    range_min, range_max = kpi['range']
                    
                    # Generate realistic value
                    if kpi['operator'] == '>':
                        value = range_min + (target - range_min) * target_pct
                    else:
                        value = range_max + (target - range_max) * target_pct
                    
                    # Add variance (more variance for volatile scenarios)
                    if scenario['progression'] == 'volatile':
                        variance = random.uniform(-0.15, 0.15)
                    else:
                        variance = random.uniform(-0.05, 0.05)
                    value = value * (1 + variance)
                    
                    # Ensure values stay within range
                    value = max(range_min, min(range_max, value))
                    
                    rows.append({
                        'account_id': account['account_id'],
                        'kpi_code': kpi['code'],
                        'measurement_month': measurement_month,
                        'value': round(value, 2),
                        'target_value': target
                    })
    
    return rows


def generate_qualitative_signals(accounts):
    """Generate qualitative_signals.csv with health-driven sentiment"""
    rows = []
    signal_id = 1  # Sequential signal ID starting from 1
    
    for account in accounts:
        scenario = account['_scenario']
        csm = account['profile_metadata']['assigned_csm']
        champion = account['profile_metadata']['champions']['primary_champion']
        
        for month_offset in range(MONTHS):
            # Use calendar months, not 30-day increments, to avoid duplicates
            try:
                from dateutil.relativedelta import relativedelta
                date = START_DATE + relativedelta(months=month_offset)
            except ImportError:
                # Fallback if dateutil not available
                date = START_DATE + timedelta(days=30*month_offset)
            
            # Calculate health at this month
            health_at_month = calculate_health_at_month(scenario, month_offset, MONTHS)
            
            # Signal frequency based on health
            signals_per_month = 10 if health_at_month >= 85 else 6 if health_at_month >= 70 else 8
            
            for _ in range(signals_per_month):
                # Sentiment distribution based on health at this time
                if health_at_month >= 85:
                    sentiment = random.choices(['positive', 'neutral', 'negative'], weights=[0.6, 0.3, 0.1])[0]
                elif health_at_month >= 70:
                    sentiment = random.choices(['positive', 'neutral', 'negative'], weights=[0.4, 0.5, 0.1])[0]
                else:
                    sentiment = random.choices(['positive', 'neutral', 'negative'], weights=[0.1, 0.3, 0.6])[0]
                
                signal_type = random.choice(['email', 'meeting', 'escalation' if sentiment == 'negative' else 'email'])
                
                rows.append({
                    'signal_id': signal_id,
                    'account_id': account['account_id'],
                    'signal_date': (date + timedelta(days=random.randint(0, 28))).strftime('%Y-%m-%d'),
                    'signal_type': signal_type,
                    'sentiment': sentiment,
                    'content': random.choice(SIGNAL_TEMPLATES[sentiment])
                })
                signal_id += 1  # Increment signal ID for next signal
    
    return rows


def generate_products(customer_id=None):
    """Generate products.csv with database-compatible columns"""
    products_list = []
    
    for idx, product in enumerate(PRODUCTS, start=1):
        products_list.append({
            'product_id': idx,  # Sequential ID starting from 1
            'product_name': product['name'],  # Rename from 'name'
            'customer_id': customer_id,  # Add customer_id
            'account_id': None  # Products are customer-level, not account-level
        })
    
    return products_list


def generate_profiles(accounts):
    """Generate profiles.csv (extended account attributes)"""
    profiles = []
    
    for account in accounts:
        profiles.append({
            'account_id': account['account_id'],
            'account_name': account['account_name'],
            'csm_name': account['profile_metadata']['assigned_csm'],
            'health_score': account['profile_metadata']['engagement']['engagement_score'],
            'lifecycle_stage': account['profile_metadata']['engagement']['lifecycle_stage'],
            'arr': account['revenue'],
            'num_licenses': random.randint(50, 500),
            'deployment_type': random.choice(['On-Premise', 'Hybrid', 'Cloud']),
            'data_center_size': random.choice(['Small', 'Medium', 'Large', 'Enterprise'])
        })
    
    return profiles


def generate_customers_csv(customer_id, company_name=None, industry=None):
    """Generate customers.csv (tenant-level) - matches database schema"""
    customer_name = company_name if company_name else f'Customer {customer_id}'
    domain = f"{customer_name.lower().replace(' ', '-').replace(',', '')}.com" if company_name else f'customer{customer_id}.com'
    
    # Map to database schema: industry_vertical combines industry and vertical
    industry_val = industry if industry else 'Technology'
    industry_vertical = f"{industry_val} - dc2_s"
    
    return [{
        'customer_id': customer_id,
        'customer_name': customer_name,
        'domain': domain,
        'industry_vertical': industry_vertical,  # Database expects industry_vertical, not separate industry/vertical
        'created_at': datetime.now().strftime('%Y-%m-%d')
        # Note: 'status' column doesn't exist in database schema
    }]


def generate_demo_manifest(accounts):
    """Generate demo_manifest.md - Guide for which accounts to use for demos"""
    lines = [
        "# Demo Account Manifest",
        "",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"Total Accounts: {len(accounts)}",
        "",
        "## 🎯 Quick Reference: Which Account for Which Demo?",
        ""
    ]
    
    # Group accounts by scenario
    scenario_groups = {}
    for account in accounts:
        scenario_key = account['_scenario_key']
        if scenario_key not in scenario_groups:
            scenario_groups[scenario_key] = []
        scenario_groups[scenario_key].append(account)
    
    # Document each scenario
    for scenario_key, accts in scenario_groups.items():
        scenario = HEALTH_SCENARIOS[scenario_key]
        lines.append(f"### {scenario['name']}")
        lines.append(f"**Use Case:** {scenario['use_case']}")
        lines.append(f"**Pattern:** {scenario['description']}")
        lines.append(f"**Health Range:** {scenario['start_health']} → {scenario['end_health']}")
        lines.append("")
        
        for acc in accts:
            lines.append(f"- **Account {acc['account_id']}** - {acc['account_name']}")
            lines.append(f"  - ARR: ${acc['revenue']:,.0f}")
            lines.append(f"  - Industry: {acc['industry']}")
            lines.append(f"  - CSM: {acc['profile_metadata']['assigned_csm']}")
            lines.append(f"  - Region: {acc['region']}")
        lines.append("")
    
    # Add demo scenarios section
    lines.extend([
        "---",
        "",
        "## 🎬 Demo Scenarios",
        "",
        "### Scenario 1: Turnaround Success Story",
        "**Objective:** Show how CS Pulse detected early warnings and facilitated recovery",
        ""
    ])
    
    improving_accounts = [acc for acc in accounts if acc['_scenario_key'] == 'improving']
    if improving_accounts:
        acc = improving_accounts[0]
        lines.extend([
            f"**Use Account:** {acc['account_id']} - {acc['account_name']}",
            "**Demo Flow:**",
            "1. Show Month 1-3: Critical health signals (red flags)",
            "2. Show intervention: Escalation, QBR scheduling",
            "3. Show Month 6-9: Improvement trends",
            "4. Show Month 12: Healthy state achieved",
            ""
        ])
    
    lines.extend([
        "### Scenario 2: Early Warning Detection",
        "**Objective:** Show how CS Pulse catches declining accounts before churn",
        ""
    ])
    
    declining_accounts = [acc for acc in accounts if acc['_scenario_key'] == 'declining']
    if declining_accounts:
        acc = declining_accounts[0]
        lines.extend([
            f"**Use Account:** {acc['account_id']} - {acc['account_name']}",
            "**Demo Flow:**",
            "1. Show Month 1-3: Healthy baseline",
            "2. Show Month 4-6: First warning signs (yellow flags)",
            "3. Show Month 8-10: Declining engagement",
            "4. Show recommended interventions",
            ""
        ])
    
    lines.extend([
        "### Scenario 3: Best-in-Class Account",
        "**Objective:** Show advocacy opportunities and expansion potential",
        ""
    ])
    
    healthy_accounts = [acc for acc in accounts if acc['_scenario_key'] == 'stable_healthy']
    if healthy_accounts:
        acc = healthy_accounts[0]
        lines.extend([
            f"**Use Account:** {acc['account_id']} - {acc['account_name']}",
            "**Demo Flow:**",
            "1. Show consistent high health scores",
            "2. Show positive signal patterns",
            "3. Show reference readiness",
            "4. Show expansion pipeline indicators",
            ""
        ])
    
    # Add health score legend
    lines.extend([
        "---",
        "",
        "## 📊 Health Score Legend",
        "",
        "| Score Range | Status | Color | Action |",
        "|-------------|--------|-------|--------|",
        "| 85-100 | Healthy | 🟢 Green | Expand, Advocate |",
        "| 70-84 | At-Risk | 🟡 Yellow | Monitor, Engage |",
        "| 0-69 | Critical | 🔴 Red | Intervene, Escalate |",
        ""
    ])
    
    # Add KPI structure
    lines.extend([
        "---",
        "",
        "## 📈 KPI Structure (5 Pillars)",
        ""
    ])
    
    for pillar_code, pillar_data in KPI_STRUCTURE.items():
        lines.append(f"### {pillar_code}: {pillar_data['name']}")
        lines.append(f"**KPIs:** {len(pillar_data['kpis'])}")
        lines.append("")
        for kpi in pillar_data['kpis'][:3]:  # Show first 3 as examples
            lines.append(f"- {kpi['code']}: {kpi['name']} (Target: {kpi['operator']} {kpi['target']} {kpi['unit']})")
        if len(pillar_data['kpis']) > 3:
            lines.append(f"- ... and {len(pillar_data['kpis']) - 3} more")
        lines.append("")
    
    return "\n".join(lines)


# ============================================================
# CSV WRITING FUNCTIONS
# ============================================================

def write_accounts_csv(accounts, output_dir):
    """Write accounts.csv"""
    filepath = output_dir / 'accounts.csv'
    
    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'account_id', 'customer_id', 'account_name', 'revenue',
            'industry', 'region', 'account_status', 'external_account_id',
            'profile_metadata_json'
        ])
        
        for acc in accounts:
            writer.writerow([
                acc['account_id'],
                acc['customer_id'],
                acc['account_name'],
                f"{acc['revenue']:.2f}",
                acc['industry'],
                acc['region'],
                acc['account_status'],
                acc['external_account_id'],
                json.dumps(acc['profile_metadata'])
            ])
    
    print(f"✅ Generated: {filepath.name} ({len(accounts)} accounts)")


def write_kpi_measurements_csv(measurements, output_dir):
    """Write kpi_measurements.csv"""
    filepath = output_dir / 'kpi_measurements.csv'
    
    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=measurements[0].keys())
        writer.writeheader()
        writer.writerows(measurements)
    
    print(f"✅ Generated: {filepath.name} ({len(measurements)} measurements)")


def write_qualitative_signals_csv(signals, output_dir):
    """Write qualitative_signals.csv"""
    filepath = output_dir / 'qualitative_signals.csv'
    
    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=signals[0].keys())
        writer.writeheader()
        writer.writerows(signals)
    
    print(f"✅ Generated: {filepath.name} ({len(signals)} signals)")


def write_products_csv(products, output_dir):
    """Write products.csv"""
    filepath = output_dir / 'products.csv'
    
    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['id', 'name', 'category'])
        writer.writeheader()
        writer.writerows(products)
    
    print(f"✅ Generated: {filepath.name} ({len(products)} products)")


def write_profiles_csv(profiles, output_dir):
    """Write profiles.csv"""
    filepath = output_dir / 'profiles.csv'
    
    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=profiles[0].keys())
        writer.writeheader()
        writer.writerows(profiles)
    
    print(f"✅ Generated: {filepath.name} ({len(profiles)} profiles)")


def write_customers_csv(customers, output_dir):
    """Write customers.csv"""
    filepath = output_dir / 'customers.csv'
    
    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=customers[0].keys())
        writer.writeheader()
        writer.writerows(customers)
    
    print(f"✅ Generated: {filepath.name} ({len(customers)} customer)")


def write_demo_manifest(manifest_content, output_dir):
    """Write DEMO_MANIFEST.md"""
    filepath = output_dir / 'DEMO_MANIFEST.md'
    
    with open(filepath, 'w') as f:
        f.write(manifest_content)
    
    print(f"✅ Generated: {filepath.name} (Demo guide)")


# ============================================================
# MAIN EXECUTION
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description='Generate synthetic customer data for DC2_S onboarding',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate data for customer 18 with 10 accounts
  python3 generate_synthetic_customer_data.py --customer-id 18 --num-accounts 10
  
  # Generate with custom output directory
  python3 generate_synthetic_customer_data.py --customer-id 18 --output-dir /path/to/output
  
  # Quick test with 3 accounts
  python3 generate_synthetic_customer_data.py --customer-id 99 --num-accounts 3

Output Files:
  1. accounts.csv - Account master data
  2. kpi_measurements.csv - Monthly KPI time-series
  3. qualitative_signals.csv - Emails, meetings, escalations
  4. products.csv - Product catalog
  5. profiles.csv - Extended account attributes
  6. customers.csv - Tenant-level data
        """
    )
    
    parser.add_argument(
        '--customer-id',
        type=int,
        default=DEFAULT_CUSTOMER_ID,
        help=f'Customer ID (default: {DEFAULT_CUSTOMER_ID})'
    )
    parser.add_argument(
        '--num-accounts',
        type=int,
        default=DEFAULT_NUM_ACCOUNTS,
        help=f'Number of accounts to generate (default: {DEFAULT_NUM_ACCOUNTS})'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default=None,
        help='Output directory (default: ./customer<ID>_synthetic_data)'
    )
    
    args = parser.parse_args()
    
    # Set output directory
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = Path(f'./customer{args.customer_id}_synthetic_data')
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Print header
    print("\n" + "="*70)
    print(f"DC2_S SYNTHETIC DATA GENERATOR")
    print("="*70)
    print(f"Customer ID: {args.customer_id}")
    print(f"Accounts: {args.num_accounts}")
    print(f"Account ID Range: {get_account_id_start(args.customer_id) + 1} - {get_account_id_start(args.customer_id) + args.num_accounts}")
    print(f"Output: {output_dir}")
    print(f"Time Period: {START_DATE.strftime('%Y-%m-%d')} to {(START_DATE + timedelta(days=30*MONTHS)).strftime('%Y-%m-%d')}")
    print("="*70)
    print()
    
    # Generate data
    print("🚀 Generating data...")
    print()
    
    # Get optional parameters from command line (for backward compatibility)
    company_name = getattr(args, 'company_name', None)
    industry = getattr(args, 'industry', None)
    
    accounts = generate_accounts(args.customer_id, args.num_accounts, industry=industry, company_name=company_name)
    kpi_measurements = generate_kpi_measurements(accounts)
    signals = generate_qualitative_signals(accounts)
    products = generate_products(customer_id=args.customer_id)
    profiles = generate_profiles(accounts)
    customers = generate_customers_csv(args.customer_id, company_name=company_name, industry=industry)
    demo_manifest = generate_demo_manifest(accounts, company_name=company_name)
    
    # Write CSV files
    write_accounts_csv(accounts, output_dir)
    write_kpi_measurements_csv(kpi_measurements, output_dir)
    write_qualitative_signals_csv(signals, output_dir)
    write_products_csv(products, output_dir)
    write_profiles_csv(profiles, output_dir)
    write_customers_csv(customers, output_dir)
    write_demo_manifest(demo_manifest, output_dir)
    
    # Print summary
    print()
    print("="*70)
    print("✅ GENERATION COMPLETE!")
    print("="*70)
    print(f"📁 Files saved to: {output_dir.absolute()}")
    print()
    print("📋 Generated Files:")
    print("  • accounts.csv - Account master data")
    print("  • kpi_measurements.csv - Monthly KPI time-series")  
    print("  • qualitative_signals.csv - Signals and events")
    print("  • products.csv - Product catalog")
    print("  • profiles.csv - Account attributes")
    print("  • customers.csv - Tenant data")
    print("  • DEMO_MANIFEST.md - 🌟 Demo guide (READ THIS FIRST!)")
    print()
    print("🎯 Next Steps:")
    print(f"  1. Read DEMO_MANIFEST.md to see which accounts to use for demos")
    print(f"  2. Copy CSV files to backend/verticals/customer{args.customer_id}-dc2_s/data/")
    print(f"  3. Run the data loading script")
    print(f"  4. Generate journey data with Wizard A")
    print("="*70)
    print()


if __name__ == '__main__':
    main()
