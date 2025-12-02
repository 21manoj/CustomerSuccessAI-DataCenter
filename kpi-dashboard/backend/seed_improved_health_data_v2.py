#!/usr/bin/env python3
"""
Seed improved KPI data with better health score distribution
V2: Uses actual health score calculation to ensure correct scores
Target: 15% Critical, 50% At Risk, 30% Moderate, 5% Healthy
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask
from extensions import db
from models import Customer, Account, KPI, KPIUpload, User, Product
from datetime import datetime
import random
import math
from health_score_engine import HealthScoreEngine
from health_score_config import get_kpi_reference_range

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'instance', 'kpi_dashboard.db')

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Define the exact 59 KPIs
KPI_TEMPLATES = [
    # Product Usage KPI (14 KPIs)
    {"category": "Product Usage KPI", "parameter": "Time to First Value (TTFV)", "impact_level": "High", "frequency": "Weekly"},
    {"category": "Product Usage KPI", "parameter": "Onboarding Completion Rate", "impact_level": "High", "frequency": "Monthly"},
    {"category": "Product Usage KPI", "parameter": "Product Activation Rate", "impact_level": "High", "frequency": "Monthly"},
    {"category": "Product Usage KPI", "parameter": "Customer Onboarding Satisfaction (CSAT)", "impact_level": "High", "frequency": "Monthly"},
    {"category": "Product Usage KPI", "parameter": "Support Requests During Onboarding", "impact_level": "Medium", "frequency": "Monthly"},
    {"category": "Product Usage KPI", "parameter": "Customer Retention Rate", "impact_level": "High", "frequency": "Monthly"},
    {"category": "Product Usage KPI", "parameter": "Churn Rate (inverse)", "impact_level": "High", "frequency": "Monthly"},
    {"category": "Product Usage KPI", "parameter": "Share of Wallet", "impact_level": "Medium", "frequency": "Quarterly"},
    {"category": "Product Usage KPI", "parameter": "Employee Productivity (customer usage patterns)", "impact_level": "Medium", "frequency": "Quarterly"},
    {"category": "Product Usage KPI", "parameter": "Operational Efficiency (platform utilization)", "impact_level": "Medium", "frequency": "Quarterly"},
    {"category": "Product Usage KPI", "parameter": "Feature Adoption Rate", "impact_level": "High", "frequency": "Monthly"},
    {"category": "Product Usage KPI", "parameter": "Training Participation Rate", "impact_level": "Medium", "frequency": "Monthly"},
    {"category": "Product Usage KPI", "parameter": "Knowledge Base Usage", "impact_level": "Medium", "frequency": "Monthly"},
    {"category": "Product Usage KPI", "parameter": "Learning Path Completion Rate", "impact_level": "Medium", "frequency": "Monthly"},
    
    # Support KPI (11 KPIs)
    {"category": "Support KPI", "parameter": "First Response Time", "impact_level": "High", "frequency": "Daily"},
    {"category": "Support KPI", "parameter": "Mean Time to Resolution (MTTR)", "impact_level": "High", "frequency": "Daily"},
    {"category": "Support KPI", "parameter": "Customer Support Satisfaction", "impact_level": "High", "frequency": "Monthly"},
    {"category": "Support KPI", "parameter": "Ticket Volume", "impact_level": "Medium", "frequency": "Daily"},
    {"category": "Support KPI", "parameter": "Ticket Backlog", "impact_level": "Medium", "frequency": "Daily"},
    {"category": "Support KPI", "parameter": "First Contact Resolution (FCR)", "impact_level": "High", "frequency": "Monthly"},
    {"category": "Support KPI", "parameter": "Escalation Rate", "impact_level": "Medium", "frequency": "Monthly"},
    {"category": "Support KPI", "parameter": "Support Cost per Ticket", "impact_level": "Low", "frequency": "Monthly"},
    {"category": "Support KPI", "parameter": "Case Deflection Rate", "impact_level": "Medium", "frequency": "Monthly"},
    {"category": "Support KPI", "parameter": "Customer Effort Score (CES)", "impact_level": "High", "frequency": "Monthly"},
    {"category": "Support KPI", "parameter": "Process Cycle Time", "impact_level": "Medium", "frequency": "Monthly"},
    
    # Customer Sentiment KPI (5 KPIs)
    {"category": "Customer Sentiment KPI", "parameter": "Net Promoter Score (NPS)", "impact_level": "High", "frequency": "Quarterly"},
    {"category": "Customer Sentiment KPI", "parameter": "Customer Satisfaction (CSAT)", "impact_level": "High", "frequency": "Monthly"},
    {"category": "Customer Sentiment KPI", "parameter": "Customer Complaints", "impact_level": "High", "frequency": "Daily"},
    {"category": "Customer Sentiment KPI", "parameter": "Error Rates (affecting customer experience)", "impact_level": "Medium", "frequency": "Daily"},
    {"category": "Customer Sentiment KPI", "parameter": "Customer sentiment Trends", "impact_level": "High", "frequency": "Monthly"},
    
    # Business Outcomes KPI (19 KPIs)
    {"category": "Business Outcomes KPI", "parameter": "Revenue Growth", "impact_level": "High", "frequency": "Quarterly"},
    {"category": "Business Outcomes KPI", "parameter": "Customer Lifetime Value (CLV)", "impact_level": "High", "frequency": "Quarterly"},
    {"category": "Business Outcomes KPI", "parameter": "Upsell and Cross-sell Revenue", "impact_level": "High", "frequency": "Monthly"},
    {"category": "Business Outcomes KPI", "parameter": "Cost Savings", "impact_level": "Medium", "frequency": "Quarterly"},
    {"category": "Business Outcomes KPI", "parameter": "Return on Investment (ROI)", "impact_level": "High", "frequency": "Quarterly"},
    {"category": "Business Outcomes KPI", "parameter": "Days Sales Outstanding (DSO)", "impact_level": "Medium", "frequency": "Monthly"},
    {"category": "Business Outcomes KPI", "parameter": "Accounts Receivable Turnover", "impact_level": "Medium", "frequency": "Monthly"},
    {"category": "Business Outcomes KPI", "parameter": "Cash Conversion Cycle (CCC)", "impact_level": "Medium", "frequency": "Monthly"},
    {"category": "Business Outcomes KPI", "parameter": "Invoice Accuracy", "impact_level": "Low", "frequency": "Monthly"},
    {"category": "Business Outcomes KPI", "parameter": "Payment Terms Compliance", "impact_level": "Medium", "frequency": "Monthly"},
    {"category": "Business Outcomes KPI", "parameter": "Collection Effectiveness Index (CEI)", "impact_level": "Medium", "frequency": "Monthly"},
    {"category": "Business Outcomes KPI", "parameter": "Gross Revenue Retention (GRR)", "impact_level": "High", "frequency": "Quarterly"},
    {"category": "Business Outcomes KPI", "parameter": "Net Revenue Retention (NRR)", "impact_level": "High", "frequency": "Quarterly"},
    {"category": "Business Outcomes KPI", "parameter": "Renewal Rate", "impact_level": "High", "frequency": "Quarterly"},
    {"category": "Business Outcomes KPI", "parameter": "Expansion Revenue Rate", "impact_level": "High", "frequency": "Quarterly"},
    {"category": "Business Outcomes KPI", "parameter": "Churn by Segment/Persona/Product", "impact_level": "High", "frequency": "Monthly"},
    {"category": "Business Outcomes KPI", "parameter": "Key Performance Indicators (KPIs)", "impact_level": "High", "frequency": "Monthly"},
    {"category": "Business Outcomes KPI", "parameter": "Operational Cost Savings", "impact_level": "Medium", "frequency": "Quarterly"},
    {"category": "Business Outcomes KPI", "parameter": "Cost per Unit", "impact_level": "Medium", "frequency": "Monthly"},
    
    # Relationship Strength KPI (10 KPIs)
    {"category": "Relationship Strength KPI", "parameter": "Business Review Frequency", "impact_level": "Medium", "frequency": "Quarterly"},
    {"category": "Relationship Strength KPI", "parameter": "Account Engagement Score", "impact_level": "High", "frequency": "Monthly"},
    {"category": "Relationship Strength KPI", "parameter": "Churn Risk Flags Triggered", "impact_level": "High", "frequency": "Weekly"},
    {"category": "Relationship Strength KPI", "parameter": "Service Level Agreements (SLAs) compliance", "impact_level": "High", "frequency": "Monthly"},
    {"category": "Relationship Strength KPI", "parameter": "On-time Delivery Rates", "impact_level": "Medium", "frequency": "Monthly"},
    {"category": "Relationship Strength KPI", "parameter": "Benchmarking Results", "impact_level": "Medium", "frequency": "Quarterly"},
    {"category": "Relationship Strength KPI", "parameter": "Regulatory Compliance", "impact_level": "Medium", "frequency": "Quarterly"},
    {"category": "Relationship Strength KPI", "parameter": "Audit Results", "impact_level": "Low", "frequency": "Quarterly"},
    {"category": "Relationship Strength KPI", "parameter": "Cross-functional Task Completion", "impact_level": "Medium", "frequency": "Monthly"},
    {"category": "Relationship Strength KPI", "parameter": "Process Improvement Velocity", "impact_level": "Low", "frequency": "Quarterly"},
]

def get_value_for_health_range(template, target_health_score):
    """
    Generate KPI value that will produce the target health score
    Uses reference ranges to determine what value maps to what score
    """
    kpi_name = template["parameter"]
    ref_range = get_kpi_reference_range(kpi_name)
    ranges = ref_range.get("ranges", {})
    higher_is_better = ref_range.get("higher_is_better", True)
    unit = ref_range.get("unit", "%")
    
    # Determine which range we need based on target health
    # Health score mapping: 0-33 (low/critical), 34-66 (medium/at risk), 67-100 (high/healthy)
    # But we want: <40 (critical), 40-60 (at risk), 60-80 (moderate), 80+ (healthy)
    
    if target_health_score < 40:
        # Critical - use low range
        range_def = ranges.get("low", {"min": 0, "max": 50})
        if higher_is_better:
            # Lower values are worse
            value = random.uniform(range_def["min"], range_def["min"] + (range_def["max"] - range_def["min"]) * 0.3)
        else:
            # Higher values are worse (for time-based, etc.)
            value = random.uniform(range_def["min"] + (range_def["max"] - range_def["min"]) * 0.7, range_def["max"])
    elif target_health_score < 60:
        # At Risk - use medium range
        range_def = ranges.get("medium", {"min": 51, "max": 80})
        if higher_is_better:
            value = random.uniform(range_def["min"], range_def["min"] + (range_def["max"] - range_def["min"]) * 0.5)
        else:
            value = random.uniform(range_def["min"] + (range_def["max"] - range_def["min"]) * 0.5, range_def["max"])
    elif target_health_score < 80:
        # Moderate - use high range, lower end
        range_def = ranges.get("high", {"min": 81, "max": 100})
        if higher_is_better:
            value = random.uniform(range_def["min"], range_def["min"] + (range_def["max"] - range_def["min"]) * 0.4)
        else:
            value = random.uniform(range_def["max"] - (range_def["max"] - range_def["min"]) * 0.4, range_def["max"])
    else:
        # Healthy - use high range, upper end
        range_def = ranges.get("high", {"min": 81, "max": 100})
        if higher_is_better:
            value = random.uniform(range_def["min"] + (range_def["max"] - range_def["min"]) * 0.6, range_def["max"])
        else:
            value = random.uniform(range_def["min"], range_def["min"] + (range_def["max"] - range_def["min"]) * 0.4)
    
    # Format value based on unit
    if unit == "days":
        return f"{int(value)} days"
    elif unit == "hours":
        return f"{int(value)} hours"
    elif unit == "score":
        if "nps" in kpi_name.lower():
            return str(int(value))
        else:
            return f"{value:.1f}"
    elif unit == "%":
        return f"{int(value)}%"
    elif "$" in unit or "K" in unit or "M" in unit:
        if value >= 1000000:
            return f"${int(value/1000000)}M"
        elif value >= 1000:
            return f"${int(value/1000)}K"
        else:
            return f"${int(value)}"
    else:
        return f"{int(value)}"

def assign_target_health_scores(num_accounts=36):
    """Assign target health scores to accounts"""
    scores = []
    # 15% Critical = 5 accounts (20-39)
    for _ in range(5):
        scores.append(random.randint(20, 39))
    # 50% At Risk = 18 accounts (40-60)
    for _ in range(18):
        scores.append(random.randint(40, 60))
    # 30% Moderate = 11 accounts (60-80)
    for _ in range(11):
        scores.append(random.randint(60, 80))
    # 5% Healthy = 2 accounts (80-95)
    for _ in range(2):
        scores.append(random.randint(80, 95))
    random.shuffle(scores)
    return scores

def calculate_revenue_from_health(health_score):
    """Calculate revenue based on health score"""
    base_min = 100000
    base_max = 5000000
    factor = (health_score - 20) / (95 - 20)
    revenue = base_min + (base_max - base_min) * factor
    revenue = revenue * random.uniform(0.8, 1.2)
    return round(revenue, 2)

def get_account_status_from_health(health_score):
    """Get account status based on health score"""
    if health_score < 40:
        return "Churn"
    elif health_score < 60:
        return "Active"
    else:
        return "Expansion"

def calculate_actual_health_score(account_id):
    """Calculate actual health score for an account using HealthScoreEngine"""
    from models import KPI as KPIModel
    account_kpis = KPIModel.query.filter_by(account_id=account_id).all()
    if not account_kpis:
        return 0
    
    # Convert KPIs to dict format
    kpi_dicts = []
    for kpi in account_kpis:
        kpi_dicts.append({
            'kpi_parameter': kpi.kpi_parameter,
            'data': kpi.data,
            'impact_level': kpi.impact_level,
            'category': kpi.category,
            'weight': kpi.weight
        })
    
    # Group by category
    categories = {}
    for kpi in kpi_dicts:
        cat = kpi['category']
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(kpi)
    
    # Calculate category scores
    category_scores = []
    for category, kpis in categories.items():
        if kpis:
            cat_score = HealthScoreEngine.calculate_category_health_score(kpis, category, 1)
            category_scores.append(cat_score)
    
    # Calculate overall
    if category_scores:
        overall = HealthScoreEngine.calculate_overall_health_score(category_scores)
        return overall.get('overall_score', 0)
    return 0

def main():
    """Seed improved KPI data with target health distribution"""
    print("\n" + "="*70)
    print("SEEDING IMPROVED KPI DATA V2 (Using Actual Health Calculation)")
    print("="*70)
    
    with app.app_context():
        customer = Customer.query.filter_by(customer_id=1).first()
        if not customer:
            print("❌ Customer ID 1 not found!")
            return
        
        print(f"\n✅ Using customer: {customer.customer_name} (ID: {customer.customer_id})")
        
        accounts = Account.query.filter_by(customer_id=1).all()
        print(f"\n📊 Found {len(accounts)} accounts")
        
        if len(accounts) < 36:
            print(f"⚠️  Warning: Only {len(accounts)} accounts found, expected 36")
        
        target_scores = assign_target_health_scores(len(accounts))
        user = User.query.filter_by(customer_id=1).first()
        if not user:
            print("❌ No user found for customer_id=1")
            return
        
        # Delete existing KPIs
        print("\n🗑️  Deleting existing KPIs...")
        existing_kpis = KPI.query.join(Account).filter(Account.customer_id == 1).all()
        for kpi in existing_kpis:
            db.session.delete(kpi)
        db.session.commit()
        print(f"   ✅ Deleted {len(existing_kpis)} existing KPIs")
        
        accounts_processed = 0
        kpis_created = 0
        
        # Process each account
        for idx, account in enumerate(accounts):
            target_health = target_scores[idx] if idx < len(target_scores) else random.randint(40, 60)
            
            print(f"\n📝 Processing: {account.account_name} (ID: {account.account_id})")
            print(f"   Target Health Score: {target_health}")
            
            # Update account revenue and status
            new_revenue = calculate_revenue_from_health(target_health)
            new_status = get_account_status_from_health(target_health)
            account.revenue = new_revenue
            account.account_status = new_status
            print(f"   Revenue: ${new_revenue:,.2f}, Status: {new_status}")
            
            # Create KPI Upload
            upload = KPIUpload.query.filter_by(customer_id=1, account_id=account.account_id).first()
            if not upload:
                upload = KPIUpload(
                    customer_id=1,
                    user_id=user.user_id,
                    account_id=account.account_id,
                    version=1,
                    original_filename=f'{account.account_name}_improved_kpis_v2.xlsx'
                )
                db.session.add(upload)
                db.session.flush()
            
            # Create 59 KPIs using reference ranges
            for template in KPI_TEMPLATES:
                kpi_value = get_value_for_health_range(template, target_health)
                
                kpi = KPI(
                    account_id=account.account_id,
                    upload_id=upload.upload_id,
                    product_id=None,
                    aggregation_type=None,
                    category=template["category"],
                    kpi_parameter=template["parameter"],
                    data=kpi_value,
                    impact_level=template["impact_level"],
                    measurement_frequency=template["frequency"],
                    source_review="Improved Seed Data V2",
                    weight=round(random.uniform(0.05, 0.25), 2)
                )
                db.session.add(kpi)
                kpis_created += 1
            
            accounts_processed += 1
            
            # Commit every 5 accounts
            if accounts_processed % 5 == 0:
                db.session.commit()
                print(f"   ✅ Committed {accounts_processed} accounts...")
        
        # Final commit
        db.session.commit()
        
        # Verify actual health scores
        print("\n📊 Verifying actual health scores...")
        health_distribution = {"Critical": 0, "At Risk": 0, "Moderate": 0, "Healthy": 0}
        actual_scores = []
        
        for account in accounts:
            actual_score = calculate_actual_health_score(account.account_id)
            actual_scores.append(actual_score)
            if actual_score < 40:
                health_distribution["Critical"] += 1
            elif actual_score < 60:
                health_distribution["At Risk"] += 1
            elif actual_score < 80:
                health_distribution["Moderate"] += 1
            else:
                health_distribution["Healthy"] += 1
        
        avg_health = sum(actual_scores) / len(actual_scores) if actual_scores else 0
        
        print("\n" + "="*70)
        print("✅ IMPROVED SEED DATA GENERATION COMPLETE")
        print("="*70)
        print(f"\n📊 Summary:")
        print(f"   - Accounts processed: {accounts_processed}")
        print(f"   - Total KPIs created: {kpis_created}")
        print(f"   - Average health score: {avg_health:.1f}")
        print(f"\n📈 Actual Health Score Distribution:")
        print(f"   - Critical (<40): {health_distribution['Critical']} accounts")
        print(f"   - At Risk (40-60): {health_distribution['At Risk']} accounts")
        print(f"   - Moderate (60-80): {health_distribution['Moderate']} accounts")
        print(f"   - Healthy (80+): {health_distribution['Healthy']} accounts")
        print("\n✅ Done!\n")

if __name__ == "__main__":
    main()

