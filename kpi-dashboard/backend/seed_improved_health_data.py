#!/usr/bin/env python3
"""
Seed improved KPI data with better health score distribution
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

def generate_kpi_value_for_health(template, target_health_score):
    """
    Generate KPI value that will contribute to target health score
    target_health_score: 0-100 (aim for this overall health)
    """
    kpi_name = template["parameter"].lower()
    
    # Adjust base value based on target health
    # Higher health = better values, lower health = worse values
    health_factor = target_health_score / 100.0
    
    if "time" in kpi_name or "response" in kpi_name or "resolution" in kpi_name or "ttfv" in kpi_name:
        # Time-based metrics (lower is better)
        if "ttfv" in kpi_name:
            # TTFV: 0-7 days (good), 8-30 (medium), 31+ (bad)
            if health_factor > 0.8:
                days = random.randint(1, 5)  # Excellent
            elif health_factor > 0.6:
                days = random.randint(6, 15)  # Good
            elif health_factor > 0.4:
                days = random.randint(16, 25)  # Medium
            else:
                days = random.randint(26, 45)  # Poor
            return f"{days} days"
        else:
            # Response/Resolution time in hours (lower is better)
            if health_factor > 0.8:
                hours = random.randint(1, 4)  # Excellent
            elif health_factor > 0.6:
                hours = random.randint(5, 12)  # Good
            elif health_factor > 0.4:
                hours = random.randint(13, 20)  # Medium
            else:
                hours = random.randint(21, 48)  # Poor
            return f"{hours} hours"
    
    elif "rate" in kpi_name or "percentage" in kpi_name or "completion" in kpi_name or "retention" in kpi_name or "churn" in kpi_name:
        # Percentage metrics (higher is better)
        if health_factor > 0.8:
            percentage = random.randint(85, 98)  # Excellent
        elif health_factor > 0.6:
            percentage = random.randint(70, 84)  # Good
        elif health_factor > 0.4:
            percentage = random.randint(55, 69)  # Medium
        else:
            percentage = random.randint(30, 54)  # Poor
        return f"{percentage}%"
    
    elif "satisfaction" in kpi_name or "csat" in kpi_name or "nps" in kpi_name or "score" in kpi_name:
        # Satisfaction scores
        if "nps" in kpi_name:
            # NPS: -100 to 100, typically 30-80
            if health_factor > 0.8:
                score = random.randint(60, 80)  # Excellent
            elif health_factor > 0.6:
                score = random.randint(40, 59)  # Good
            elif health_factor > 0.4:
                score = random.randint(20, 39)  # Medium
            else:
                score = random.randint(0, 19)  # Poor
            return str(score)
        else:
            # CSAT: 1-5 scale
            if health_factor > 0.8:
                score = round(random.uniform(4.5, 5.0), 1)  # Excellent
            elif health_factor > 0.6:
                score = round(random.uniform(4.0, 4.4), 1)  # Good
            elif health_factor > 0.4:
                score = round(random.uniform(3.5, 3.9), 1)  # Medium
            else:
                score = round(random.uniform(2.5, 3.4), 1)  # Poor
            return str(score)
    
    elif "revenue" in kpi_name or "growth" in kpi_name or "clv" in kpi_name:
        # Revenue metrics
        if "growth" in kpi_name:
            # Growth percentage
            if health_factor > 0.8:
                growth = random.randint(15, 30)  # Excellent
            elif health_factor > 0.6:
                growth = random.randint(8, 14)  # Good
            elif health_factor > 0.4:
                growth = random.randint(2, 7)  # Medium
            else:
                growth = random.randint(-5, 1)  # Poor/Declining
            return f"{growth}%"
        else:
            # Revenue value
            base_value = 200000
            value = int(base_value * (0.5 + health_factor * 1.5))  # Scale with health
            return f"${value:,}"
    
    elif "cost" in kpi_name or "savings" in kpi_name:
        # Cost metrics (savings - higher is better)
        if health_factor > 0.8:
            savings = random.randint(60, 100)  # Excellent
        elif health_factor > 0.6:
            savings = random.randint(40, 59)  # Good
        elif health_factor > 0.4:
            savings = random.randint(20, 39)  # Medium
        else:
            savings = random.randint(5, 19)  # Poor
        return f"${savings}K"
    
    elif "volume" in kpi_name or "count" in kpi_name or "ticket" in kpi_name:
        # Volume metrics (lower is better for tickets)
        if health_factor > 0.8:
            volume = random.randint(5, 30)  # Excellent (low volume)
        elif health_factor > 0.6:
            volume = random.randint(31, 80)  # Good
        elif health_factor > 0.4:
            volume = random.randint(81, 150)  # Medium
        else:
            volume = random.randint(151, 300)  # Poor (high volume)
        return str(volume)
    
    elif "complaints" in kpi_name:
        # Complaints count (lower is better)
        if health_factor > 0.8:
            count = random.randint(0, 2)  # Excellent
        elif health_factor > 0.6:
            count = random.randint(3, 5)  # Good
        elif health_factor > 0.4:
            count = random.randint(6, 10)  # Medium
        else:
            count = random.randint(11, 20)  # Poor
        return str(count)
    
    elif "roi" in kpi_name:
        # ROI percentage (higher is better)
        if health_factor > 0.8:
            roi = random.randint(250, 350)  # Excellent
        elif health_factor > 0.6:
            roi = random.randint(200, 249)  # Good
        elif health_factor > 0.4:
            roi = random.randint(150, 199)  # Medium
        else:
            roi = random.randint(100, 149)  # Poor
        return f"{roi}%"
    
    elif "dso" in kpi_name or "ccc" in kpi_name:
        # Days (lower is better)
        if health_factor > 0.8:
            days = random.randint(20, 35)  # Excellent
        elif health_factor > 0.6:
            days = random.randint(36, 45)  # Good
        elif health_factor > 0.4:
            days = random.randint(46, 55)  # Medium
        else:
            days = random.randint(56, 75)  # Poor
        return f"{days} days"
    
    else:
        # Default percentage (higher is better)
        if health_factor > 0.8:
            percentage = random.randint(80, 95)  # Excellent
        elif health_factor > 0.6:
            percentage = random.randint(65, 79)  # Good
        elif health_factor > 0.4:
            percentage = random.randint(50, 64)  # Medium
        else:
            percentage = random.randint(30, 49)  # Poor
        return f"{percentage}%"

def assign_target_health_scores(num_accounts=36):
    """
    Assign target health scores to accounts based on distribution:
    15% Critical (<40), 50% At Risk (40-60), 30% Moderate (60-80), 5% Healthy (80+)
    """
    scores = []
    
    # 15% Critical = 5 accounts (health 20-39)
    for _ in range(5):
        scores.append(random.randint(20, 39))
    
    # 50% At Risk = 18 accounts (health 40-60)
    for _ in range(18):
        scores.append(random.randint(40, 60))
    
    # 30% Moderate = 11 accounts (health 60-80)
    for _ in range(11):
        scores.append(random.randint(60, 80))
    
    # 5% Healthy = 2 accounts (health 80-95)
    for _ in range(2):
        scores.append(random.randint(80, 95))
    
    # Shuffle to randomize
    random.shuffle(scores)
    return scores

def calculate_revenue_from_health(health_score):
    """Calculate revenue based on health score (higher health = higher revenue)"""
    # Base revenue range: $100K - $5M
    # Scale with health: health 20 = ~$100K, health 95 = ~$5M
    base_min = 100000
    base_max = 5000000
    
    # Linear scaling
    factor = (health_score - 20) / (95 - 20)  # Normalize to 0-1
    revenue = base_min + (base_max - base_min) * factor
    
    # Add some randomness
    revenue = revenue * random.uniform(0.8, 1.2)
    
    return round(revenue, 2)

def get_account_status_from_health(health_score):
    """Get account status based on health score"""
    if health_score < 40:
        return "Churn"  # Critical
    elif health_score < 60:
        return "Active"  # At Risk
    else:
        return "Expansion"  # Moderate and Healthy

def main():
    """Seed improved KPI data with target health distribution"""
    print("\n" + "="*70)
    print("SEEDING IMPROVED KPI DATA WITH TARGET HEALTH DISTRIBUTION")
    print("="*70)
    print("Target Distribution:")
    print("  - 15% Critical (<40): 5 accounts")
    print("  - 50% At Risk (40-60): 18 accounts")
    print("  - 30% Moderate (60-80): 11 accounts")
    print("  - 5% Healthy (80+): 2 accounts")
    print("="*70)
    
    with app.app_context():
        # Get customer
        customer = Customer.query.filter_by(customer_id=1).first()
        if not customer:
            print("❌ Customer ID 1 not found!")
            return
        
        print(f"\n✅ Using customer: {customer.customer_name} (ID: {customer.customer_id})")
        
        # Get all accounts for this customer
        accounts = Account.query.filter_by(customer_id=1).all()
        print(f"\n📊 Found {len(accounts)} accounts")
        
        if len(accounts) < 36:
            print(f"⚠️  Warning: Only {len(accounts)} accounts found, expected 36")
        
        # Assign target health scores
        target_scores = assign_target_health_scores(len(accounts))
        
        # Get or create a user for uploads
        user = User.query.filter_by(customer_id=1).first()
        if not user:
            print("❌ No user found for customer_id=1")
            return
        
        # Delete existing KPIs for this customer
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
            
            # Update account revenue and status based on health
            new_revenue = calculate_revenue_from_health(target_health)
            new_status = get_account_status_from_health(target_health)
            account.revenue = new_revenue
            account.account_status = new_status
            print(f"   Revenue: ${new_revenue:,.2f}, Status: {new_status}")
            
            # Create or get KPI Upload record
            upload = KPIUpload.query.filter_by(
                customer_id=1,
                account_id=account.account_id
            ).first()
            
            if not upload:
                upload = KPIUpload(
                    customer_id=1,
                    user_id=user.user_id,
                    account_id=account.account_id,
                    version=1,
                    original_filename=f'{account.account_name}_improved_kpis.xlsx'
                )
                db.session.add(upload)
                db.session.flush()
            
            # Create exactly 59 account-level KPIs with values targeting health score
            for template in KPI_TEMPLATES:
                kpi_value = generate_kpi_value_for_health(template, target_health)
                
                kpi = KPI(
                    account_id=account.account_id,
                    upload_id=upload.upload_id,
                    product_id=None,  # Account-level
                    aggregation_type=None,  # Account-level
                    category=template["category"],
                    kpi_parameter=template["parameter"],
                    data=kpi_value,
                    impact_level=template["impact_level"],
                    measurement_frequency=template["frequency"],
                    source_review="Improved Seed Data",
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
        
        print("\n" + "="*70)
        print("✅ IMPROVED SEED DATA GENERATION COMPLETE")
        print("="*70)
        print(f"\n📊 Summary:")
        print(f"   - Accounts processed: {accounts_processed}")
        print(f"   - Total KPIs created: {kpis_created}")
        print(f"   - KPIs per account: 59 (account-level)")
        print(f"   - Expected total: {accounts_processed * 59}")
        
        # Show health distribution
        print(f"\n📈 Health Score Distribution:")
        critical = sum(1 for s in target_scores if s < 40)
        at_risk = sum(1 for s in target_scores if 40 <= s < 60)
        moderate = sum(1 for s in target_scores if 60 <= s < 80)
        healthy = sum(1 for s in target_scores if s >= 80)
        print(f"   - Critical (<40): {critical} accounts")
        print(f"   - At Risk (40-60): {at_risk} accounts")
        print(f"   - Moderate (60-80): {moderate} accounts")
        print(f"   - Healthy (80+): {healthy} accounts")
        
        print("\n✅ Done!\n")

if __name__ == "__main__":
    main()

