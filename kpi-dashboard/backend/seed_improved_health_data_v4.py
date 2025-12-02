#!/usr/bin/env python3
"""
Seed improved KPI data with better health score distribution
V4: Uses HealthScoreEngine to reverse-engineer values that produce target scores
Target: 15% Critical (5 accounts), 50% At Risk (18 accounts), 30% Moderate (11 accounts), 5% Healthy (2 accounts)
Average: 60-70
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
    {"category": "Support KPI", "parameter": "Support Ticket Volume", "impact_level": "Medium", "frequency": "Daily"},
    {"category": "Support KPI", "parameter": "Support Cost per Ticket", "impact_level": "Medium", "frequency": "Monthly"},
    {"category": "Support KPI", "parameter": "Customer Support Satisfaction (CSAT)", "impact_level": "High", "frequency": "Monthly"},
    {"category": "Support KPI", "parameter": "First Contact Resolution Rate", "impact_level": "High", "frequency": "Monthly"},
    {"category": "Support KPI", "parameter": "Support Escalation Rate", "impact_level": "Medium", "frequency": "Monthly"},
    {"category": "Support KPI", "parameter": "Support Team Efficiency", "impact_level": "Medium", "frequency": "Monthly"},
    {"category": "Support KPI", "parameter": "Knowledge Base Article Usage", "impact_level": "Low", "frequency": "Monthly"},
    {"category": "Support KPI", "parameter": "Self-Service Resolution Rate", "impact_level": "Medium", "frequency": "Monthly"},
    {"category": "Support KPI", "parameter": "Support Channel Mix", "impact_level": "Low", "frequency": "Quarterly"},
    
    # Business Outcomes KPI (12 KPIs)
    {"category": "Business Outcomes KPI", "parameter": "Net Revenue Retention (NRR)", "impact_level": "High", "frequency": "Quarterly"},
    {"category": "Business Outcomes KPI", "parameter": "Gross Revenue Retention (GRR)", "impact_level": "High", "frequency": "Quarterly"},
    {"category": "Business Outcomes KPI", "parameter": "Customer Lifetime Value (CLV)", "impact_level": "High", "frequency": "Quarterly"},
    {"category": "Business Outcomes KPI", "parameter": "Revenue Growth Rate", "impact_level": "High", "frequency": "Quarterly"},
    {"category": "Business Outcomes KPI", "parameter": "Expansion Revenue", "impact_level": "High", "frequency": "Quarterly"},
    {"category": "Business Outcomes KPI", "parameter": "Contract Renewal Rate", "impact_level": "High", "frequency": "Quarterly"},
    {"category": "Business Outcomes KPI", "parameter": "Upsell Rate", "impact_level": "Medium", "frequency": "Quarterly"},
    {"category": "Business Outcomes KPI", "parameter": "Cross-sell Rate", "impact_level": "Medium", "frequency": "Quarterly"},
    {"category": "Business Outcomes KPI", "parameter": "Average Contract Value (ACV)", "impact_level": "Medium", "frequency": "Quarterly"},
    {"category": "Business Outcomes KPI", "parameter": "Time to Value", "impact_level": "Medium", "frequency": "Quarterly"},
    {"category": "Business Outcomes KPI", "parameter": "ROI Realization", "impact_level": "High", "frequency": "Quarterly"},
    {"category": "Business Outcomes KPI", "parameter": "Cost Savings", "impact_level": "Medium", "frequency": "Quarterly"},
    
    # Customer Sentiment KPI (11 KPIs)
    {"category": "Customer Sentiment KPI", "parameter": "Net Promoter Score (NPS)", "impact_level": "High", "frequency": "Quarterly"},
    {"category": "Customer Sentiment KPI", "parameter": "Customer Satisfaction Score (CSAT)", "impact_level": "High", "frequency": "Monthly"},
    {"category": "Customer Sentiment KPI", "parameter": "Customer Effort Score (CES)", "impact_level": "High", "frequency": "Monthly"},
    {"category": "Customer Sentiment KPI", "parameter": "Customer Health Score", "impact_level": "High", "frequency": "Monthly"},
    {"category": "Customer Sentiment KPI", "parameter": "Product Satisfaction", "impact_level": "High", "frequency": "Monthly"},
    {"category": "Customer Sentiment KPI", "parameter": "Support Satisfaction", "impact_level": "Medium", "frequency": "Monthly"},
    {"category": "Customer Sentiment KPI", "parameter": "Feature Request Frequency", "impact_level": "Low", "frequency": "Monthly"},
    {"category": "Customer Sentiment KPI", "parameter": "Customer Complaints", "impact_level": "High", "frequency": "Monthly"},
    {"category": "Customer Sentiment KPI", "parameter": "Customer Testimonials", "impact_level": "Low", "frequency": "Quarterly"},
    {"category": "Customer Sentiment KPI", "parameter": "Customer References", "impact_level": "Medium", "frequency": "Quarterly"},
    {"category": "Customer Sentiment KPI", "parameter": "Customer Advocacy", "impact_level": "Medium", "frequency": "Quarterly"},
    
    # Relationship Strength KPI (11 KPIs)
    {"category": "Relationship Strength KPI", "parameter": "Executive Engagement Score", "impact_level": "High", "frequency": "Quarterly"},
    {"category": "Relationship Strength KPI", "parameter": "Strategic Meeting Frequency", "impact_level": "Medium", "frequency": "Quarterly"},
    {"category": "Relationship Strength KPI", "parameter": "Account Manager Relationship Quality", "impact_level": "High", "frequency": "Quarterly"},
    {"category": "Relationship Strength KPI", "parameter": "Multi-threaded Relationships", "impact_level": "Medium", "frequency": "Quarterly"},
    {"category": "Relationship Strength KPI", "parameter": "Contract Negotiation Health", "impact_level": "High", "frequency": "Quarterly"},
    {"category": "Relationship Strength KPI", "parameter": "Partnership Opportunities", "impact_level": "Medium", "frequency": "Quarterly"},
    {"category": "Relationship Strength KPI", "parameter": "Joint Business Planning", "impact_level": "Medium", "frequency": "Quarterly"},
    {"category": "Relationship Strength KPI", "parameter": "Audit Results", "impact_level": "Low", "frequency": "Quarterly"},
    {"category": "Relationship Strength KPI", "parameter": "Cross-functional Task Completion", "impact_level": "Medium", "frequency": "Monthly"},
    {"category": "Relationship Strength KPI", "parameter": "Process Improvement Velocity", "impact_level": "Low", "frequency": "Quarterly"},
]

def find_value_for_target_score(kpi_name, target_score, ref_range):
    """
    Find a value that will produce approximately target_score (0-100)
    Uses binary search to find the right value
    """
    ranges = ref_range.get("ranges", {})
    higher_is_better = ref_range.get("higher_is_better", True)
    unit = ref_range.get("unit", "%")
    
    # Get range boundaries
    if higher_is_better:
        min_val = ranges.get("low", {}).get("min", 0)
        max_val = ranges.get("high", {}).get("max", 100)
    else:
        min_val = ranges.get("high", {}).get("min", 0)
        max_val = ranges.get("low", {}).get("max", 100)
    
    # Binary search for value that produces target_score
    low = min_val
    high = max_val
    best_value = (low + high) / 2
    best_score_diff = float('inf')
    
    for _ in range(50):  # Max 50 iterations
        test_value = (low + high) / 2
        health_info = HealthScoreEngine.calculate_health_status(test_value, kpi_name)
        actual_score = health_info['score']
        
        score_diff = abs(actual_score - target_score)
        if score_diff < best_score_diff:
            best_score_diff = score_diff
            best_value = test_value
        
        if actual_score < target_score:
            if higher_is_better:
                low = test_value
            else:
                high = test_value
        else:
            if higher_is_better:
                high = test_value
            else:
                low = test_value
        
        if score_diff < 1.0:  # Close enough
            break
    
    # Add small randomness
    best_value = best_value * random.uniform(0.98, 1.02)
    
    # Format based on unit
    if unit == "days":
        return f"{max(1, int(best_value))} days"
    elif unit == "hours":
        return f"{max(1, int(best_value))} hours"
    elif unit == "$":
        if best_value >= 1000000:
            return f"${best_value/1000000:.2f}M"
        elif best_value >= 1000:
            return f"${best_value/1000:.2f}K"
        else:
            return f"${best_value:.2f}"
    else:  # percentage or count
        return f"{best_value:.2f}%"

def get_value_for_target_score(template, target_score):
    """
    Generate KPI value that will produce approximately target_score
    """
    kpi_name = template["parameter"]
    ref_range = HealthScoreEngine.get_kpi_reference_range_from_db(kpi_name)
    if not ref_range:
        ref_range = get_kpi_reference_range(kpi_name)
    
    return find_value_for_target_score(kpi_name, target_score, ref_range)

def assign_target_health_scores(num_accounts, target_avg=65):
    """
    Assign target health scores to accounts to achieve distribution:
    15% Critical (5), 50% At Risk (18), 30% Moderate (11), 5% Healthy (2)
    Average should be around 60-70
    """
    scores = []
    
    # 15% Critical (<70) = 5 accounts (55-68) - below 70 threshold
    for _ in range(5):
        scores.append(random.randint(55, 68))
    
    # 50% At Risk (70-79) = 18 accounts (70-78)
    for _ in range(18):
        scores.append(random.randint(70, 78))
    
    # 30% Moderate (60-80) = 11 accounts - split: 6 in Critical range, 5 in Healthy range
    for _ in range(6):  # Some in Critical range (60-69)
        scores.append(random.randint(60, 69))
    for _ in range(5):  # Some in Healthy range (80-82)
        scores.append(random.randint(80, 82))
    
    # 5% Healthy (>=80) = 2 accounts (80-85)
    for _ in range(2):
        scores.append(random.randint(80, 85))
    
    # Adjust to hit target average (65), but don't over-adjust
    current_avg = sum(scores) / len(scores) if scores else 0
    adjustment = (target_avg - current_avg) * 0.5  # Only apply 50% of adjustment
    
    # Apply adjustment, but keep within category bounds
    adjusted_scores = []
    for s in scores:
        adjusted = s + adjustment
        # Keep in reasonable bounds
        adjusted = max(20, min(95, adjusted))
        adjusted_scores.append(adjusted)
    
    random.shuffle(adjusted_scores)
    return adjusted_scores

def calculate_account_health_score(account_id, customer_id):
    """Calculate actual health score for an account using HealthScoreEngine"""
    kpis = KPI.query.filter_by(account_id=account_id).all()
    if not kpis:
        return 0
    
    # Group by category
    categories = {}
    for kpi in kpis:
        cat = kpi.category
        if cat not in categories:
            categories[cat] = []
        categories[cat].append({
            'kpi_parameter': kpi.kpi_parameter,
            'data': kpi.data,
            'impact_level': kpi.impact_level,
            'category': kpi.category
        })
    
    # Calculate category scores
    category_scores = []
    for category, kpis_list in categories.items():
        if kpis_list:
            cat_score = HealthScoreEngine.calculate_category_health_score(kpis_list, category, customer_id)
            category_scores.append(cat_score)
    
    # Calculate overall score
    if category_scores:
        overall = HealthScoreEngine.calculate_overall_health_score(category_scores)
        return overall.get('overall_score', 0)
    return 0

def main():
    with app.app_context():
        customer = Customer.query.filter_by(customer_name='Test Company').first()
        if not customer:
            print("❌ Test Company not found")
            return
        
        customer_id = customer.customer_id
        accounts = Account.query.filter_by(customer_id=customer_id).all()
        
        if len(accounts) != 36:
            print(f"❌ Expected 36 accounts, found {len(accounts)}")
            return
        
        print("🗑️  Deleting existing KPIs...")
        # Delete only account-level KPIs (preserve product-level KPIs)
        for account in accounts:
            # Only delete account-level KPIs (product_id is None)
            KPI.query.filter_by(account_id=account.account_id, product_id=None).delete()
        db.session.commit()
        
        print("📊 Generating improved seed data...")
        target_scores = assign_target_health_scores(36, target_avg=65)
        
        # Create upload record
        user = User.query.filter_by(customer_id=customer_id).first()
        if not user:
            print("❌ No user found for customer")
            return
        
        kpi_upload = KPIUpload(
            customer_id=customer_id,
            account_id=None,  # Account-level upload
            user_id=user.user_id,
            version=1,
            original_filename="seed_improved_health_data_v4"
        )
        db.session.add(kpi_upload)
        db.session.commit()
        
        # Generate KPIs for each account
        for idx, account in enumerate(accounts):
            target_score = target_scores[idx]
            
            # For each KPI, generate a value that contributes to target_score
            # Account for category/impact weighting - need higher individual KPI scores
            # to achieve target overall score
            kpi_targets = []
            for template in KPI_TEMPLATES:
                # Boost target to compensate for weighting effects
                # Adjust boost based on target range - reduced to lower overall average
                if target_score < 70:
                    boost = 4  # Critical accounts need small boost
                elif target_score < 80:
                    boost = 3  # At Risk accounts need minimal boost
                else:
                    boost = 4  # Healthy accounts need small boost
                
                kpi_target = target_score + boost + random.uniform(-2, 2)
                kpi_target = max(45, min(88, kpi_target))  # Keep in reasonable range
                kpi_targets.append(kpi_target)
            
            # Create KPIs
            for template, kpi_target in zip(KPI_TEMPLATES, kpi_targets):
                value_str = get_value_for_target_score(template, kpi_target)
                
                kpi = KPI(
                    upload_id=kpi_upload.upload_id,
                    account_id=account.account_id,
                    product_id=None,  # Account-level
                    aggregation_type=None,
                    category=template["category"],
                    kpi_parameter=template["parameter"],
                    data=value_str,
                    impact_level=template["impact_level"],
                    weight=round(random.uniform(0.05, 0.25), 2),
                    measurement_frequency=template["frequency"]
                )
                db.session.add(kpi)
            
            db.session.commit()
            
            # Verify actual health score
            actual_score = calculate_account_health_score(account.account_id, customer_id)
            print(f"  {account.account_name}: Target={target_score:.1f}, Actual={actual_score:.1f}")
        
        # Final verification
        print("\n" + "="*70)
        print("✅ IMPROVED SEED DATA GENERATION COMPLETE")
        print("="*70)
        
        all_scores = []
        for account in accounts:
            score = calculate_account_health_score(account.account_id, customer_id)
            all_scores.append(score)
        
        avg_score = sum(all_scores) / len(all_scores) if all_scores else 0
        # Match dashboard categories: Critical <70, At Risk 70-79, Healthy >=80
        critical = sum(1 for s in all_scores if s < 70)
        at_risk = sum(1 for s in all_scores if 70 <= s < 80)
        moderate = sum(1 for s in all_scores if 60 <= s < 80)  # For reference
        healthy = sum(1 for s in all_scores if s >= 80)
        
        print(f"\n📊 Summary:")
        print(f"   - Accounts processed: {len(accounts)}")
        print(f"   - Total KPIs created: {len(KPI_TEMPLATES) * len(accounts)}")
        print(f"   - Average health score: {avg_score:.1f}")
        print(f"\n📈 Actual Health Score Distribution:")
        print(f"   - Critical (<70): {critical} accounts")
        print(f"   - At Risk (70-79): {at_risk} accounts")
        print(f"   - Healthy (80+): {healthy} accounts")
        print(f"   - Moderate (60-80, for reference): {moderate} accounts")
        print("\n✅ Done!\n")

if __name__ == '__main__':
    main()

