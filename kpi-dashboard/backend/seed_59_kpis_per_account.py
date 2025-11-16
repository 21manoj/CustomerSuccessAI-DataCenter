#!/usr/bin/env python3
"""
Seed exactly 59 KPIs per account for customer_id=1
One KPI per parameter, no duplicates
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask
from extensions import db
from models import Customer, Account, KPI, KPIUpload, User
from datetime import datetime
import random

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

def generate_kpi_value(template):
    """Generate a realistic KPI value based on template"""
    kpi_name = template["parameter"].lower()
    
    if "time" in kpi_name or "response" in kpi_name or "resolution" in kpi_name or "ttfv" in kpi_name:
        # Time-based metrics (hours or days)
        if "ttfv" in kpi_name:
            days = random.randint(1, 14)
            return f"{days} days"
        else:
            hours = random.randint(1, 24)
            return f"{hours} hours"
    elif "rate" in kpi_name or "percentage" in kpi_name or "completion" in kpi_name or "retention" in kpi_name or "churn" in kpi_name:
        # Percentage metrics
        percentage = random.randint(65, 98)
        return f"{percentage}%"
    elif "satisfaction" in kpi_name or "csat" in kpi_name or "nps" in kpi_name or "score" in kpi_name:
        # Satisfaction scores
        if "nps" in kpi_name:
            score = random.randint(30, 80)
            return str(score)
        else:
            score = round(random.uniform(3.5, 5.0), 1)
            return str(score)
    elif "revenue" in kpi_name or "growth" in kpi_name or "clv" in kpi_name:
        # Revenue metrics
        if "growth" in kpi_name:
            growth = random.randint(5, 25)
            return f"{growth}%"
        else:
            value = random.randint(100000, 500000)
            return f"${value:,}"
    elif "cost" in kpi_name or "savings" in kpi_name:
        # Cost metrics
        savings = random.randint(10, 100)
        return f"${savings}K"
    elif "volume" in kpi_name or "count" in kpi_name or "ticket" in kpi_name:
        # Volume metrics
        volume = random.randint(10, 200)
        return str(volume)
    elif "complaints" in kpi_name:
        # Complaints count
        count = random.randint(0, 10)
        return str(count)
    elif "roi" in kpi_name:
        # ROI percentage
        roi = random.randint(150, 300)
        return f"{roi}%"
    elif "dso" in kpi_name or "ccc" in kpi_name:
        # Days
        days = random.randint(30, 60)
        return f"{days} days"
    else:
        # Default percentage
        percentage = random.randint(70, 95)
        return f"{percentage}%"

def main():
    """Seed exactly 59 KPIs per account"""
    print("\n" + "="*70)
    print("SEEDING 59 KPIs PER ACCOUNT")
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
        
        # Get or create a user for uploads
        user = User.query.filter_by(customer_id=1).first()
        if not user:
            print("❌ No user found for customer_id=1")
            return
        
        accounts_processed = 0
        kpis_created = 0
        
        for account in accounts:
            print(f"\n📝 Processing: {account.account_name} (ID: {account.account_id})")
            
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
                    original_filename=f'{account.account_name}_59_kpis.xlsx'
                )
                db.session.add(upload)
                db.session.flush()
            
            # Create exactly 59 KPIs (one per template)
            for template in KPI_TEMPLATES:
                kpi_value = generate_kpi_value(template)
                
                kpi = KPI(
                    account_id=account.account_id,
                    upload_id=upload.upload_id,
                    category=template["category"],
                    kpi_parameter=template["parameter"],
                    data=kpi_value,
                    impact_level=template["impact_level"],
                    measurement_frequency=template["frequency"],
                    source_review="Seed Data",
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
        print("✅ SEED DATA GENERATION COMPLETE")
        print("="*70)
        print(f"\n📊 Summary:")
        print(f"   - Accounts processed: {accounts_processed}")
        print(f"   - Total KPIs created: {kpis_created}")
        print(f"   - KPIs per account: 59")
        print(f"   - Expected total: {accounts_processed * 59}")
        
        # Verify
        for account in accounts[:5]:  # Check first 5
            kpi_count = KPI.query.filter_by(account_id=account.account_id).count()
            print(f"   - {account.account_name}: {kpi_count} KPIs")
        
        print("\n✅ Done!\n")

if __name__ == "__main__":
    main()

