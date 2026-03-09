#!/usr/bin/env python3
"""
Create Template CSV Files for Onboarding
=========================================

Creates downloadable template CSV files for all file types:

Core (6):
1. accounts.csv
2. kpi_measurements.csv (kpis.csv)
3. qualitative_signals.csv (signals.csv)
4. products.csv
5. account_profiles.csv (profiles.csv)
6. customers.csv

Context Graph (9):
7. stakeholders.csv
8. engagement_events.csv
9. account_business_profiles.csv
10. decisions.csv
11. outcomes.csv
12. signal_edges.csv
13. decision_evidence.csv
14. industry_benchmarks.csv
15. enhanced_qualitative_signals.csv

These templates are used by users to understand the expected structure
and format of data files for onboarding.
"""

import csv
import json
from pathlib import Path
from datetime import datetime, timedelta

# Template directory
TEMPLATE_DIR = Path(__file__).parent / "verticals" / "_template" / "templates"
TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)

def create_accounts_template():
    """Create accounts.csv template"""
    filepath = TEMPLATE_DIR / "accounts.csv"
    
    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        # Header
        writer.writerow([
            'account_id', 'customer_id', 'account_name', 'revenue',
            'industry', 'region', 'account_status', 'external_account_id',
            'profile_metadata'
        ])
        # Sample rows (2 examples)
        writer.writerow([
            '10001', '1', 'Acme Corporation - Datacenter East', '2500000.00',
            'Technology', 'North America', 'active', 'EXT-1-10001',
            '{"assigned_csm": "John Smith", "csm_manager": "Jane Doe", "onboarding_status": "completed"}'
        ])
        writer.writerow([
            '10002', '1', 'Acme Corporation - Cloud Ops', '1800000.00',
            'Technology', 'North America', 'active', 'EXT-1-10002',
            '{"assigned_csm": "John Smith", "csm_manager": "Jane Doe", "onboarding_status": "completed"}'
        ])
    
    print(f"✅ Created: {filepath}")
    return filepath

def create_kpi_measurements_template():
    """Create kpi_measurements.csv template"""
    filepath = TEMPLATE_DIR / "kpi_measurements.csv"
    
    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'account_id', 'kpi_code', 'measurement_date', 'value',
            'unit', 'source', 'notes'
        ])
        writer.writeheader()
        
        # Sample rows (3 examples showing different KPIs)
        base_date = datetime.now() - timedelta(days=30)
        writer.writerow({
            'account_id': '10001',
            'kpi_code': 'P3-KPI1',
            'measurement_date': base_date.strftime('%Y-%m-%d'),
            'value': '85.5',
            'unit': '%',
            'source': 'System Monitoring',
            'notes': 'GPU Utilization'
        })
        writer.writerow({
            'account_id': '10001',
            'kpi_code': 'P4-KPI1',
            'measurement_date': base_date.strftime('%Y-%m-%d'),
            'value': '82.0',
            'unit': 'score',
            'source': 'Health Calculator',
            'notes': 'Overall Health Score'
        })
        writer.writerow({
            'account_id': '10001',
            'kpi_code': 'P1-KPI1',
            'measurement_date': base_date.strftime('%Y-%m-%d'),
            'value': '12',
            'unit': 'days',
            'source': 'Deployment System',
            'notes': 'Time to First Workload'
        })
    
    print(f"✅ Created: {filepath}")
    return filepath

def create_qualitative_signals_template():
    """Create qualitative_signals.csv template"""
    filepath = TEMPLATE_DIR / "qualitative_signals.csv"
    
    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'signal_id', 'account_id', 'signal_date', 'signal_type',
            'sentiment', 'content'
        ])
        writer.writeheader()
        
        # Sample rows (3 examples)
        base_date = datetime.now() - timedelta(days=7)
        writer.writerow({
            'signal_id': '1',
            'account_id': '10001',
            'signal_date': base_date.strftime('%Y-%m-%d'),
            'signal_type': 'email',
            'sentiment': 'positive',
            'content': 'Customer expressed satisfaction with recent deployment'
        })
        writer.writerow({
            'signal_id': '2',
            'account_id': '10001',
            'signal_date': (base_date - timedelta(days=3)).strftime('%Y-%m-%d'),
            'signal_type': 'meeting',
            'sentiment': 'neutral',
            'content': 'QBR meeting scheduled for next month'
        })
        writer.writerow({
            'signal_id': '3',
            'account_id': '10001',
            'signal_date': (base_date - timedelta(days=1)).strftime('%Y-%m-%d'),
            'signal_type': 'escalation',
            'sentiment': 'negative',
            'content': 'Performance issue reported, resolved within 2 hours'
        })
    
    print(f"✅ Created: {filepath}")
    return filepath

def create_products_template():
    """Create products.csv template"""
    filepath = TEMPLATE_DIR / "products.csv"
    
    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['product_id', 'product_name', 'category', 'description'])
        writer.writeheader()
        
        # Sample rows (3 examples)
        writer.writerow({
            'product_id': '1',
            'product_name': 'AI Compute Platform',
            'category': 'Infrastructure',
            'description': 'High-performance GPU compute platform for AI workloads'
        })
        writer.writerow({
            'product_id': '2',
            'product_name': 'Data Analytics Suite',
            'category': 'Software',
            'description': 'Comprehensive analytics and reporting tools'
        })
        writer.writerow({
            'product_id': '3',
            'product_name': 'Managed Services',
            'category': 'Services',
            'description': '24/7 managed infrastructure services'
        })
    
    print(f"✅ Created: {filepath}")
    return filepath

def create_account_profiles_template():
    """Create account_profiles.csv template (profiles.csv)"""
    filepath = TEMPLATE_DIR / "account_profiles.csv"
    
    # Note: account_profiles has 100+ columns, we'll include key ones
    key_columns = [
        'account_id', 'customer_id', 'account_name', 'account_nickname',
        'industry', 'account_tier', 'initial_arr', 'final_arr',
        'contract_start_date', 'contract_end_date', 'partner_id',
        'csm_assigned', 'executive_sponsor', 'journey_type', 'outcome'
    ]
    
    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=key_columns)
        writer.writeheader()
        
        # Sample row
        writer.writerow({
            'account_id': '10001',
            'customer_id': '1',
            'account_name': 'Acme Corporation - Datacenter East',
            'account_nickname': 'Acme DC East',
            'industry': 'Technology',
            'account_tier': 'Enterprise',
            'initial_arr': '2000000',
            'final_arr': '2500000',
            'contract_start_date': '2024-01-01',
            'contract_end_date': '2025-12-31',
            'partner_id': 'PARTNER-001',
            'csm_assigned': 'John Smith',
            'executive_sponsor': 'Jane Executive',
            'journey_type': 'expansion',
            'outcome': 'success'
        })
    
    print(f"✅ Created: {filepath}")
    return filepath

def create_customers_template():
    """Create customers.csv template"""
    filepath = TEMPLATE_DIR / "customers.csv"
    
    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'customer_id', 'customer_name', 'domain', 'industry_vertical', 'created_at'
        ])
        writer.writeheader()
        
        # Sample row
        writer.writerow({
            'customer_id': '1',
            'customer_name': 'Acme Corporation',
            'domain': 'acme-corporation.com',
            'industry_vertical': 'Technology - dc2_s',
            'created_at': datetime.now().strftime('%Y-%m-%d')
        })
    
    print(f"✅ Created: {filepath}")
    return filepath

# ============================================================================
# Context Graph Templates (9 additional CSVs)
# ============================================================================

def create_stakeholders_template():
    """Create stakeholders.csv template"""
    filepath = TEMPLATE_DIR / "stakeholders.csv"
    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'account_id', 'stakeholder_name', 'title', 'role',
            'influence_score', 'email', 'engagement_frequency', 'sentiment',
            'department', 'is_active'
        ])
        writer.writeheader()
        writer.writerow({
            'account_id': '10001', 'stakeholder_name': 'Sarah Chen',
            'title': 'VP Infrastructure', 'role': 'champion',
            'influence_score': '0.85', 'email': 'schen@acme.com',
            'engagement_frequency': 'weekly', 'sentiment': 'positive',
            'department': 'Engineering', 'is_active': 'true'
        })
        writer.writerow({
            'account_id': '10001', 'stakeholder_name': 'James Park',
            'title': 'CTO', 'role': 'decision_maker',
            'influence_score': '0.95', 'email': 'jpark@acme.com',
            'engagement_frequency': 'monthly', 'sentiment': 'neutral',
            'department': 'Technology', 'is_active': 'true'
        })
    print(f"  Created: {filepath}")
    return filepath


def create_engagement_events_template():
    """Create engagement_events.csv template"""
    filepath = TEMPLATE_DIR / "engagement_events.csv"
    base_date = datetime.now() - timedelta(days=14)
    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'account_id', 'event_date', 'event_type', 'description',
            'stakeholder_name', 'sentiment_shift', 'channel',
            'duration_minutes', 'outcome'
        ])
        writer.writeheader()
        writer.writerow({
            'account_id': '10001', 'event_date': base_date.strftime('%Y-%m-%d'),
            'event_type': 'qbr', 'description': 'Quarterly business review',
            'stakeholder_name': 'Sarah Chen', 'sentiment_shift': '+0.1',
            'channel': 'video', 'duration_minutes': '60', 'outcome': 'expansion_discussed'
        })
        writer.writerow({
            'account_id': '10001',
            'event_date': (base_date + timedelta(days=7)).strftime('%Y-%m-%d'),
            'event_type': 'technical_review', 'description': 'GPU cluster performance review',
            'stakeholder_name': 'James Park', 'sentiment_shift': '+0.05',
            'channel': 'in_person', 'duration_minutes': '45', 'outcome': 'issue_resolved'
        })
    print(f"  Created: {filepath}")
    return filepath


def create_account_business_profiles_template():
    """Create account_business_profiles.csv template"""
    filepath = TEMPLATE_DIR / "account_business_profiles.csv"
    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'account_id', 'arr', 'industry', 'employee_count',
            'fiscal_year_end', 'tech_stack', 'cloud_provider',
            'competitive_landscape', 'strategic_initiatives'
        ])
        writer.writeheader()
        writer.writerow({
            'account_id': '10001', 'arr': '2500000', 'industry': 'Technology',
            'employee_count': '5000', 'fiscal_year_end': 'December',
            'tech_stack': 'NVIDIA DGX, VMware, Kubernetes',
            'cloud_provider': 'hybrid', 'competitive_landscape': 'CoreWeave, Lambda Labs',
            'strategic_initiatives': 'AI training expansion, multi-cloud migration'
        })
    print(f"  Created: {filepath}")
    return filepath


def create_decisions_template():
    """Create decisions.csv template"""
    filepath = TEMPLATE_DIR / "decisions.csv"
    base_date = datetime.now() - timedelta(days=30)
    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'account_id', 'decision_date', 'title', 'decision_maker_role',
            'chosen_option', 'options_considered', 'revenue_impact',
            'risk_level', 'outcome_description', 'confidence'
        ])
        writer.writeheader()
        writer.writerow({
            'account_id': '10001', 'decision_date': base_date.strftime('%Y-%m-%d'),
            'title': 'GPU Cluster Expansion',
            'decision_maker_role': 'CTO', 'chosen_option': 'Scale existing cluster',
            'options_considered': 'Scale existing; New vendor; Cloud migration',
            'revenue_impact': '500000', 'risk_level': 'medium',
            'outcome_description': 'Approved 40% capacity increase',
            'confidence': '0.85'
        })
    print(f"  Created: {filepath}")
    return filepath


def create_outcomes_template():
    """Create outcomes.csv template"""
    filepath = TEMPLATE_DIR / "outcomes.csv"
    base_date = datetime.now() - timedelta(days=15)
    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'account_id', 'outcome_date', 'title', 'outcome_type',
            'revenue_value', 'evidence', 'confidence',
            'related_decision_id'
        ])
        writer.writeheader()
        writer.writerow({
            'account_id': '10001', 'outcome_date': base_date.strftime('%Y-%m-%d'),
            'title': 'Expansion deal signed',
            'outcome_type': 'expansion', 'revenue_value': '500000',
            'evidence': 'SOW signed after GPU cluster performance improvement',
            'confidence': '1.0', 'related_decision_id': 'DEC-001'
        })
        writer.writerow({
            'account_id': '10001',
            'outcome_date': (base_date + timedelta(days=5)).strftime('%Y-%m-%d'),
            'title': 'Contract renewal at higher tier',
            'outcome_type': 'retention', 'revenue_value': '2500000',
            'evidence': 'Auto-renewed with 10% uplift',
            'confidence': '0.95', 'related_decision_id': ''
        })
    print(f"  Created: {filepath}")
    return filepath


def create_signal_edges_template():
    """Create signal_edges.csv template"""
    filepath = TEMPLATE_DIR / "signal_edges.csv"
    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'from_signal_ref', 'to_signal_ref', 'edge_type', 'weight',
            'confidence', 'lag_days', 'revenue_impact', 'evidence'
        ])
        writer.writeheader()
        writer.writerow({
            'from_signal_ref': 'SIG-001', 'to_signal_ref': 'SIG-002',
            'edge_type': 'caused_by', 'weight': '0.8',
            'confidence': '0.75', 'lag_days': '7',
            'revenue_impact': '250000',
            'evidence': 'Performance issue led to escalation'
        })
        writer.writerow({
            'from_signal_ref': 'SIG-003', 'to_signal_ref': 'DEC-001',
            'edge_type': 'influenced', 'weight': '0.9',
            'confidence': '0.85', 'lag_days': '14',
            'revenue_impact': '500000',
            'evidence': 'Positive QBR feedback influenced expansion decision'
        })
    print(f"  Created: {filepath}")
    return filepath


def create_decision_evidence_template():
    """Create decision_evidence.csv template"""
    filepath = TEMPLATE_DIR / "decision_evidence.csv"
    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'decision_ref', 'evidence_type', 'evidence_description',
            'kpi_code', 'kpi_value', 'signal_ref', 'timestamp', 'confidence'
        ])
        writer.writeheader()
        writer.writerow({
            'decision_ref': 'DEC-001', 'evidence_type': 'kpi_improvement',
            'evidence_description': 'GPU utilization improved 15% after optimization',
            'kpi_code': 'P3-KPI1', 'kpi_value': '92.5',
            'signal_ref': '', 'timestamp': datetime.now().strftime('%Y-%m-%d'),
            'confidence': '0.9'
        })
        writer.writerow({
            'decision_ref': 'DEC-001', 'evidence_type': 'stakeholder_feedback',
            'evidence_description': 'VP Infrastructure confirmed value in QBR',
            'kpi_code': '', 'kpi_value': '',
            'signal_ref': 'SIG-003', 'timestamp': datetime.now().strftime('%Y-%m-%d'),
            'confidence': '0.85'
        })
    print(f"  Created: {filepath}")
    return filepath


def create_industry_benchmarks_template():
    """Create industry_benchmarks.csv template"""
    filepath = TEMPLATE_DIR / "industry_benchmarks.csv"
    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'kpi_code', 'benchmark_source', 'industry_p50',
            'industry_p25', 'industry_p75', 'account_percentile',
            'sample_size', 'benchmark_date'
        ])
        writer.writeheader()
        writer.writerow({
            'kpi_code': 'P3-KPI1', 'benchmark_source': 'Industry Report 2025',
            'industry_p50': '78.0', 'industry_p25': '65.0',
            'industry_p75': '88.0', 'account_percentile': '82',
            'sample_size': '150', 'benchmark_date': '2025-06-01'
        })
        writer.writerow({
            'kpi_code': 'P1-KPI1', 'benchmark_source': 'Industry Report 2025',
            'industry_p50': '14', 'industry_p25': '21',
            'industry_p75': '7', 'account_percentile': '65',
            'sample_size': '120', 'benchmark_date': '2025-06-01'
        })
    print(f"  Created: {filepath}")
    return filepath


def create_enhanced_signals_template():
    """Create enhanced_qualitative_signals.csv template"""
    filepath = TEMPLATE_DIR / "enhanced_qualitative_signals.csv"
    base_date = datetime.now() - timedelta(days=7)
    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'account_id', 'signal_date', 'signal_type', 'content',
            'sentiment', 'sentiment_score', 'stakeholder_name',
            'stakeholder_title', 'causal_chain_ref', 'revenue_impact',
            'confidence'
        ])
        writer.writeheader()
        writer.writerow({
            'account_id': '10001', 'signal_date': base_date.strftime('%Y-%m-%d'),
            'signal_type': 'champion_signal',
            'content': 'VP Infrastructure advocates for expanded deployment in leadership meeting',
            'sentiment': 'positive', 'sentiment_score': '0.9',
            'stakeholder_name': 'Sarah Chen', 'stakeholder_title': 'VP Infrastructure',
            'causal_chain_ref': 'SIG-001→SIG-003', 'revenue_impact': '500000',
            'confidence': '0.85'
        })
        writer.writerow({
            'account_id': '10001',
            'signal_date': (base_date + timedelta(days=3)).strftime('%Y-%m-%d'),
            'signal_type': 'risk_signal',
            'content': 'Competitor demo scheduled with procurement team',
            'sentiment': 'negative', 'sentiment_score': '-0.6',
            'stakeholder_name': 'James Park', 'stakeholder_title': 'CTO',
            'causal_chain_ref': '', 'revenue_impact': '-2500000',
            'confidence': '0.7'
        })
    print(f"  Created: {filepath}")
    return filepath


def main():
    """Create all template files (core + context graph)"""
    print("=" * 70)
    print("Creating Template CSV Files for Onboarding")
    print("=" * 70)
    print()

    # Core templates (6)
    print("Core Data Templates:")
    core_templates = {
        'accounts': create_accounts_template,
        'kpi_measurements': create_kpi_measurements_template,
        'qualitative_signals': create_qualitative_signals_template,
        'products': create_products_template,
        'account_profiles': create_account_profiles_template,
        'customers': create_customers_template
    }

    created = []
    for name, func in core_templates.items():
        try:
            filepath = func()
            created.append((name, filepath))
        except Exception as e:
            print(f"  Failed to create {name} template: {e}")

    # Context graph templates (9)
    print()
    print("Context Graph Templates:")
    context_graph_templates = {
        'stakeholders': create_stakeholders_template,
        'engagement_events': create_engagement_events_template,
        'account_business_profiles': create_account_business_profiles_template,
        'decisions': create_decisions_template,
        'outcomes': create_outcomes_template,
        'signal_edges': create_signal_edges_template,
        'decision_evidence': create_decision_evidence_template,
        'industry_benchmarks': create_industry_benchmarks_template,
        'enhanced_signals': create_enhanced_signals_template,
    }

    for name, func in context_graph_templates.items():
        try:
            filepath = func()
            created.append((name, filepath))
        except Exception as e:
            print(f"  Failed to create {name} template: {e}")

    print()
    print("=" * 70)
    print(f"Created {len(created)} template files")
    print("=" * 70)
    print()
    print("Template files location:")
    print(f"  {TEMPLATE_DIR}")
    print()
    print("Files created:")
    for name, filepath in created:
        print(f"  - {name}: {filepath.name}")

    return created

if __name__ == '__main__':
    main()
