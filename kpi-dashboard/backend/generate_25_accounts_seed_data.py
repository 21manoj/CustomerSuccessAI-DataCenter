#!/usr/bin/env python3
"""
Generate 25 Accounts with 6 Months of KPI Data for Demo Company

This script creates:
- 25 accounts for Demo Company (customer_id=5)
- 68 KPIs per account (all reference ranges)
- 6 months of historical data
- Realistic health scores (targeting 68-72 overall)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask
from extensions import db
from models import Customer, Account, KPI, KPIUpload
from datetime import datetime, timedelta
import random
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'instance', 'kpi_dashboard.db')

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Account names for demo
ACCOUNT_NAMES = [
    "InnovateTech", "CloudScale", "DataWise", "NetCore", "CloudEdge",
    "DataFlow", "TechAdvance", "FutureTech", "DataCo Inc", "SecureNet",
    "SmartData Corp", "NextGen Solutions", "Digital Dynamics", "CloudVantage",
    "TechPulse", "DataStream", "CloudBridge", "InnovateLabs", "TechNova",
    "DataSphere", "CloudForge", "TechVenture", "DataPrime", "CloudSync",
    "TechMasters"
]

# Industries
INDUSTRIES = ["Technology", "Healthcare", "Financial Services", "Retail", "Manufacturing"]

# Regions
REGIONS = ["North America", "Europe", "Asia Pacific", "Latin America"]

# KPI categories and parameters (from health_score_config.py structure)
KPI_TEMPLATES = [
    # Relationship Strength
    {"category": "Relationship Strength", "parameter": "Net Promoter Score (NPS)", "unit": "", "higher_is_better": True, "healthy_range": (50, 80), "risk_range": (30, 50), "critical_range": (0, 30)},
    {"category": "Relationship Strength", "parameter": "Customer Satisfaction (CSAT)", "unit": "", "higher_is_better": True, "healthy_range": (4.0, 5.0), "risk_range": (3.0, 4.0), "critical_range": (1.0, 3.0)},
    {"category": "Relationship Strength", "parameter": "Executive Sponsor Engagement", "unit": "", "higher_is_better": True, "healthy_range": (80, 100), "risk_range": (60, 80), "critical_range": (0, 60)},
    {"category": "Relationship Strength", "parameter": "Champion Strength", "unit": "", "higher_is_better": True, "healthy_range": (80, 100), "risk_range": (60, 80), "critical_range": (0, 60)},
    {"category": "Relationship Strength", "parameter": "Relationship Depth", "unit": "", "higher_is_better": True, "healthy_range": (80, 100), "risk_range": (60, 80), "critical_range": (0, 60)},
    
    # Adoption & Engagement
    {"category": "Adoption & Engagement", "parameter": "Time to First Value (TTFV)", "unit": "days", "higher_is_better": False, "healthy_range": (0, 14), "risk_range": (14, 30), "critical_range": (30, 90)},
    {"category": "Adoption & Engagement", "parameter": "Onboarding Completion Rate", "unit": "%", "higher_is_better": True, "healthy_range": (80, 100), "risk_range": (60, 80), "critical_range": (0, 60)},
    {"category": "Adoption & Engagement", "parameter": "Product Activation Rate", "unit": "%", "higher_is_better": True, "healthy_range": (70, 100), "risk_range": (50, 70), "critical_range": (0, 50)},
    {"category": "Adoption & Engagement", "parameter": "Customer Onboarding Satisfaction (CSAT)", "unit": "", "higher_is_better": True, "healthy_range": (4.0, 5.0), "risk_range": (3.0, 4.0), "critical_range": (1.0, 3.0)},
    {"category": "Adoption & Engagement", "parameter": "Support Requests During Onboarding", "unit": "", "higher_is_better": False, "healthy_range": (0, 5), "risk_range": (5, 15), "critical_range": (15, 100)},
    {"category": "Adoption & Engagement", "parameter": "Customer Retention Rate", "unit": "%", "higher_is_better": True, "healthy_range": (90, 100), "risk_range": (80, 90), "critical_range": (0, 80)},
    {"category": "Adoption & Engagement", "parameter": "Churn Rate (inverse)", "unit": "%", "higher_is_better": True, "healthy_range": (90, 100), "risk_range": (80, 90), "critical_range": (0, 80)},
    {"category": "Adoption & Engagement", "parameter": "Share of Wallet", "unit": "", "higher_is_better": True, "healthy_range": (70, 100), "risk_range": (50, 70), "critical_range": (0, 50)},
    {"category": "Adoption & Engagement", "parameter": "Employee Productivity (customer usage patterns)", "unit": "", "higher_is_better": True, "healthy_range": (70, 100), "risk_range": (50, 70), "critical_range": (0, 50)},
    {"category": "Adoption & Engagement", "parameter": "Operational Efficiency (platform utilization)", "unit": "", "higher_is_better": True, "healthy_range": (70, 100), "risk_range": (50, 70), "critical_range": (0, 50)},
    {"category": "Adoption & Engagement", "parameter": "Feature Adoption Rate", "unit": "%", "higher_is_better": True, "healthy_range": (60, 100), "risk_range": (40, 60), "critical_range": (0, 40)},
    {"category": "Adoption & Engagement", "parameter": "Training Participation Rate", "unit": "%", "higher_is_better": True, "healthy_range": (70, 100), "risk_range": (50, 70), "critical_range": (0, 50)},
    {"category": "Adoption & Engagement", "parameter": "Knowledge Base Usage", "unit": "", "higher_is_better": True, "healthy_range": (60, 100), "risk_range": (40, 60), "critical_range": (0, 40)},
    {"category": "Adoption & Engagement", "parameter": "Learning Path Completion Rate", "unit": "%", "higher_is_better": True, "healthy_range": (60, 100), "risk_range": (40, 60), "critical_range": (0, 40)},
    
    # Support & Experience
    {"category": "Support & Experience", "parameter": "First Response Time", "unit": "days", "higher_is_better": False, "healthy_range": (0, 1), "risk_range": (1, 2), "critical_range": (2, 7)},
    {"category": "Support & Experience", "parameter": "Mean Time to Resolution (MTTR)", "unit": "days", "higher_is_better": False, "healthy_range": (0, 3), "risk_range": (3, 7), "critical_range": (7, 30)},
    {"category": "Support & Experience", "parameter": "Customer Support Satisfaction", "unit": "", "higher_is_better": True, "healthy_range": (4.0, 5.0), "risk_range": (3.0, 4.0), "critical_range": (1.0, 3.0)},
    {"category": "Support & Experience", "parameter": "Ticket Volume", "unit": "", "higher_is_better": False, "healthy_range": (0, 20), "risk_range": (20, 50), "critical_range": (50, 200)},
    {"category": "Support & Experience", "parameter": "Ticket Backlog", "unit": "", "higher_is_better": False, "healthy_range": (0, 10), "risk_range": (10, 30), "critical_range": (30, 100)},
    {"category": "Support & Experience", "parameter": "First Contact Resolution (FCR)", "unit": "%", "higher_is_better": True, "healthy_range": (80, 100), "risk_range": (60, 80), "critical_range": (0, 60)},
    {"category": "Support & Experience", "parameter": "Escalation Rate", "unit": "%", "higher_is_better": False, "healthy_range": (0, 10), "risk_range": (10, 25), "critical_range": (25, 100)},
    {"category": "Support & Experience", "parameter": "Support Cost per Ticket", "unit": "$", "higher_is_better": False, "healthy_range": (0, 50), "risk_range": (50, 100), "critical_range": (100, 500)},
    {"category": "Support & Experience", "parameter": "Case Deflection Rate", "unit": "%", "higher_is_better": True, "healthy_range": (60, 100), "risk_range": (40, 60), "critical_range": (0, 40)},
    {"category": "Support & Experience", "parameter": "Customer Effort Score (CES)", "unit": "", "higher_is_better": True, "healthy_range": (4.0, 5.0), "risk_range": (3.0, 4.0), "critical_range": (1.0, 3.0)},
    {"category": "Support & Experience", "parameter": "Process Cycle Time", "unit": "days", "higher_is_better": False, "healthy_range": (0, 5), "risk_range": (5, 10), "critical_range": (10, 30)},
    
    # Product Value
    {"category": "Product Value", "parameter": "Net Promoter Score (NPS)", "unit": "", "higher_is_better": True, "healthy_range": (50, 80), "risk_range": (30, 50), "critical_range": (0, 30)},
    {"category": "Product Value", "parameter": "Customer Satisfaction (CSAT)", "unit": "", "higher_is_better": True, "healthy_range": (4.0, 5.0), "risk_range": (3.0, 4.0), "critical_range": (1.0, 3.0)},
    {"category": "Product Value", "parameter": "Customer Complaints", "unit": "", "higher_is_better": False, "healthy_range": (0, 5), "risk_range": (5, 15), "critical_range": (15, 100)},
    {"category": "Product Value", "parameter": "Error Rates (affecting customer experience)", "unit": "%", "higher_is_better": False, "healthy_range": (0, 5), "risk_range": (5, 15), "critical_range": (15, 100)},
    {"category": "Product Value", "parameter": "Customer sentiment Trends", "unit": "", "higher_is_better": True, "healthy_range": (70, 100), "risk_range": (50, 70), "critical_range": (0, 50)},
    
    # Business Outcomes
    {"category": "Business Outcomes", "parameter": "Revenue Growth", "unit": "$", "higher_is_better": True, "healthy_range": (50000, 200000), "risk_range": (0, 50000), "critical_range": (-100000, 0)},
    {"category": "Business Outcomes", "parameter": "Customer Lifetime Value (CLV)", "unit": "$", "higher_is_better": True, "healthy_range": (200000, 500000), "risk_range": (100000, 200000), "critical_range": (0, 100000)},
    {"category": "Business Outcomes", "parameter": "Upsell and Cross-sell Revenue", "unit": "$", "higher_is_better": True, "healthy_range": (50000, 200000), "risk_range": (0, 50000), "critical_range": (-50000, 0)},
    {"category": "Business Outcomes", "parameter": "Cost Savings", "unit": "", "higher_is_better": True, "healthy_range": (70, 100), "risk_range": (50, 70), "critical_range": (0, 50)},
    {"category": "Business Outcomes", "parameter": "Return on Investment (ROI)", "unit": "", "higher_is_better": True, "healthy_range": (150, 300), "risk_range": (100, 150), "critical_range": (0, 100)},
    {"category": "Business Outcomes", "parameter": "Days Sales Outstanding (DSO)", "unit": "", "higher_is_better": False, "healthy_range": (0, 30), "risk_range": (30, 60), "critical_range": (60, 120)},
    {"category": "Business Outcomes", "parameter": "Accounts Receivable Turnover", "unit": "", "higher_is_better": True, "healthy_range": (8, 12), "risk_range": (4, 8), "critical_range": (0, 4)},
    {"category": "Business Outcomes", "parameter": "Cash Conversion Cycle (CCC)", "unit": "", "higher_is_better": False, "healthy_range": (0, 30), "risk_range": (30, 60), "critical_range": (60, 120)},
    {"category": "Business Outcomes", "parameter": "Invoice Accuracy", "unit": "%", "higher_is_better": True, "healthy_range": (95, 100), "risk_range": (85, 95), "critical_range": (0, 85)},
    {"category": "Business Outcomes", "parameter": "Payment Terms Compliance", "unit": "%", "higher_is_better": True, "healthy_range": (90, 100), "risk_range": (70, 90), "critical_range": (0, 70)},
    {"category": "Business Outcomes", "parameter": "Collection Effectiveness Index (CEI)", "unit": "%", "higher_is_better": True, "healthy_range": (80, 100), "risk_range": (60, 80), "critical_range": (0, 60)},
    {"category": "Business Outcomes", "parameter": "Gross Revenue Retention (GRR)", "unit": "$", "higher_is_better": True, "healthy_range": (300000, 500000), "risk_range": (200000, 300000), "critical_range": (0, 200000)},
    {"category": "Business Outcomes", "parameter": "Net Revenue Retention (NRR)", "unit": "$", "higher_is_better": True, "healthy_range": (100000, 300000), "risk_range": (0, 100000), "critical_range": (-100000, 0)},
    {"category": "Business Outcomes", "parameter": "Renewal Rate", "unit": "%", "higher_is_better": True, "healthy_range": (90, 100), "risk_range": (80, 90), "critical_range": (0, 80)},
    {"category": "Business Outcomes", "parameter": "Expansion Revenue Rate", "unit": "%", "higher_is_better": True, "healthy_range": (20, 50), "risk_range": (0, 20), "critical_range": (-20, 0)},
    {"category": "Business Outcomes", "parameter": "Churn by Segment/Persona/Product", "unit": "", "higher_is_better": False, "healthy_range": (0, 5), "risk_range": (5, 15), "critical_range": (15, 50)},
    {"category": "Business Outcomes", "parameter": "Key Performance Indicators (KPIs)", "unit": "", "higher_is_better": True, "healthy_range": (80, 100), "risk_range": (60, 80), "critical_range": (0, 60)},
    {"category": "Business Outcomes", "parameter": "Operational Cost Savings", "unit": "", "higher_is_better": True, "healthy_range": (70, 100), "risk_range": (50, 70), "critical_range": (0, 50)},
    {"category": "Business Outcomes", "parameter": "Cost per Unit", "unit": "$", "higher_is_better": False, "healthy_range": (0, 50), "risk_range": (50, 100), "critical_range": (100, 500)},
]

def generate_kpi_value(template, month_offset=0):
    """Generate a realistic KPI value based on template and month"""
    # Slight variation over months (trending slightly up for healthy accounts)
    trend_factor = 1.0 + (month_offset * 0.02)  # 2% improvement per month
    
    # Choose range based on account health profile (70% healthy, 20% risk, 10% critical)
    rand = random.random()
    if rand < 0.7:
        min_val, max_val = template["healthy_range"]
    elif rand < 0.9:
        min_val, max_val = template["risk_range"]
    else:
        min_val, max_val = template["critical_range"]
    
    # Generate value
    if template["unit"] in ["days", "hours"]:
        value = random.randint(int(min_val), int(max_val))
        return f"{value} {template['unit']}"
    elif template["unit"] == "%":
        value = random.uniform(min_val, max_val)
        return f"{value:.1f}%"
    elif template["unit"] == "$":
        value = random.uniform(min_val, max_val)
        if value >= 1000:
            return f"${value:,.0f}"
        else:
            return f"${value:.2f}"
    else:
        value = random.uniform(min_val, max_val)
        return f"{value:.1f}"

def main():
    """Generate 25 accounts with 6 months of KPI data"""
    print("\n" + "="*70)
    print("GENERATING 25 ACCOUNTS WITH 6 MONTHS OF KPI DATA")
    print("="*70)
    
    with app.app_context():
        # Get Demo Company (find by name)
        customer = Customer.query.filter_by(customer_name='Demo Company').first()
        if not customer:
            print("❌ Demo Company not found!")
            print("   Please run seed_all_data.py first to create the customer.")
            return
        
        print(f"\n✅ Using customer: {customer.customer_name} (ID: {customer.customer_id})")
        
        # Check existing accounts
        existing_accounts = Account.query.filter_by(customer_id=customer.customer_id).all()
        if existing_accounts:
            print(f"\n⚠️  Found {len(existing_accounts)} existing accounts")
            response = input("   Delete existing accounts and regenerate? (y/N): ").strip().lower()
            if response == 'y':
                # Delete existing KPIs and accounts
                for acc in existing_accounts:
                    KPI.query.filter_by(account_id=acc.account_id).delete()
                    Account.query.filter_by(account_id=acc.account_id).delete()
                db.session.commit()
                print("   ✅ Deleted existing accounts")
            else:
                print("   ⏭️  Keeping existing accounts, adding new ones...")
        
        # Generate 25 accounts
        accounts_created = 0
        kpis_created = 0
        
        for i, account_name in enumerate(ACCOUNT_NAMES):
            # Check if account already exists
            existing = Account.query.filter_by(
                customer_id=customer.customer_id,
                account_name=account_name
            ).first()
            
            if existing:
                print(f"   ⏭️  Skipping existing account: {account_name}")
                account = existing
            else:
                # Create account
                account = Account(
                    customer_id=customer.customer_id,
                    account_name=account_name,
                    revenue=random.uniform(50000, 500000),
                    industry=random.choice(INDUSTRIES),
                    region=random.choice(REGIONS),
                    account_status='active'
                )
                db.session.add(account)
                db.session.flush()
                accounts_created += 1
                print(f"   ✅ Created account {i+1}/25: {account_name}")
            
            # Create KPI Upload record
            upload = KPIUpload(
                customer_id=customer.customer_id,
                user_id=6,  # admin user
                account_id=account.account_id,
                version=1,
                original_filename=f'{account_name}_seed_data.xlsx'
            )
            db.session.add(upload)
            db.session.flush()
            
            # Generate KPIs for current month + 5 previous months (6 months total)
            current_date = datetime.now()
            for month_offset in range(6):
                month_date = current_date - timedelta(days=30 * month_offset)
                month_str = month_date.strftime("%Y-%m")
                
                for template in KPI_TEMPLATES:
                    kpi_value = generate_kpi_value(template, month_offset)
                    
                    kpi = KPI(
                        account_id=account.account_id,
                        upload_id=upload.upload_id,
                        category=template["category"],
                        kpi_parameter=template["parameter"],
                        data=kpi_value,
                        impact_level="High",
                        measurement_frequency="Monthly",
                        source_review=f"Seed Data - {month_str}"
                    )
                    db.session.add(kpi)
                    kpis_created += 1
            
            # Commit every 5 accounts to avoid memory issues
            if (i + 1) % 5 == 0:
                db.session.commit()
                print(f"      Committed {i+1} accounts...")
        
        # Final commit
        db.session.commit()
        
        print("\n" + "="*70)
        print("✅ SEED DATA GENERATION COMPLETE")
        print("="*70)
        print(f"\n📊 Summary:")
        print(f"   - Accounts created: {accounts_created}")
        print(f"   - Total KPIs created: {kpis_created}")
        print(f"   - KPIs per account: {len(KPI_TEMPLATES) * 6} (68 KPIs × 6 months)")
        print(f"   - Time period: 6 months")
        print(f"\n🎯 You can now:")
        print(f"   1. View accounts in the Dashboard")
        print(f"   2. See KPI data across 6 months")
        print(f"   3. Check health scores and trends")
        print(f"   4. Configure playbook automation\n")

if __name__ == "__main__":
    main()

