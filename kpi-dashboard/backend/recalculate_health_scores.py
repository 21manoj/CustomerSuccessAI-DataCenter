#!/usr/bin/env python3
"""
Recalculate health scores for all Test Company accounts
This ensures health scores are properly calculated from KPI data
"""

import os
from dotenv import load_dotenv
from flask import Flask
from extensions import db
from models import Account, KPI, HealthTrend, Customer
from health_score_engine import HealthScoreEngine
from datetime import datetime

load_dotenv('.env')

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

def recalculate_health_scores(customer_id=1):
    """Recalculate health scores for all accounts"""
    print(f"🔄 Recalculating health scores for customer_id={customer_id}...")
    
    with app.app_context():
        customer = Customer.query.get(customer_id)
        if not customer:
            print(f"❌ Customer {customer_id} not found")
            return
        
        accounts = Account.query.filter_by(customer_id=customer_id).all()
        print(f"   Found {len(accounts)} accounts")
        
        current_month = datetime.now().month
        current_year = datetime.now().year
        
        recalculated = 0
        skipped = 0
        
        for account in accounts:
            # Get KPIs for this account
            kpis = KPI.query.filter_by(account_id=account.account_id).all()
            
            if not kpis:
                skipped += 1
                continue
            
            # Group KPIs by category
            categories = {}
            for kpi in kpis:
                cat = kpi.category
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append({
                    'kpi_parameter': kpi.kpi_parameter,
                    'data': kpi.data,
                    'impact_level': kpi.impact_level,
                    'category': kpi.category,
                    'weight': kpi.weight
                })
            
            # Calculate category scores
            category_scores = []
            for category, kpis_list in categories.items():
                if kpis_list:
                    try:
                        cat_score = HealthScoreEngine.calculate_category_health_score(kpis_list, category, customer_id)
                        category_scores.append(cat_score)
                    except Exception as e:
                        print(f"   ⚠️  Error calculating score for {account.account_name}, category {category}: {e}")
                        continue
            
            # Calculate overall score
            if category_scores:
                overall = HealthScoreEngine.calculate_overall_health_score(category_scores)
                overall_score = overall.get('overall_score', 0)
                
                # Extract category scores
                product_usage = next((cs.get('score', 0) for cs in category_scores if 'Product Usage' in cs.get('category', '')), 0)
                support = next((cs.get('score', 0) for cs in category_scores if 'Support' in cs.get('category', '')), 0)
                customer_sentiment = next((cs.get('score', 0) for cs in category_scores if 'Customer Sentiment' in cs.get('category', '')), 0)
                business_outcomes = next((cs.get('score', 0) for cs in category_scores if 'Business Outcomes' in cs.get('category', '')), 0)
                relationship_strength = next((cs.get('score', 0) for cs in category_scores if 'Relationship Strength' in cs.get('category', '')), 0)
                
                # Update or create health trend
                trend = HealthTrend.query.filter_by(
                    account_id=account.account_id,
                    customer_id=customer_id,
                    month=current_month,
                    year=current_year
                ).first()
                
                if trend:
                    trend.overall_health_score = overall_score
                    trend.product_usage_score = product_usage
                    trend.support_score = support
                    trend.customer_sentiment_score = customer_sentiment
                    trend.business_outcomes_score = business_outcomes
                    trend.relationship_strength_score = relationship_strength
                    trend.total_kpis = len(kpis)
                    trend.valid_kpis = len([k for k in kpis if k.data and str(k.data).strip() and str(k.data) != '0'])
                else:
                    trend = HealthTrend(
                        account_id=account.account_id,
                        customer_id=customer_id,
                        month=current_month,
                        year=current_year,
                        overall_health_score=overall_score,
                        product_usage_score=product_usage,
                        support_score=support,
                        customer_sentiment_score=customer_sentiment,
                        business_outcomes_score=business_outcomes,
                        relationship_strength_score=relationship_strength,
                        total_kpis=len(kpis),
                        valid_kpis=len([k for k in kpis if k.data and str(k.data).strip() and str(k.data) != '0'])
                    )
                    db.session.add(trend)
                
                recalculated += 1
        
        db.session.commit()
        print(f"\n✅ Recalculated {recalculated} health scores")
        print(f"   Skipped {skipped} accounts (no KPIs)")
        
        # Show sample scores
        trends = HealthTrend.query.filter_by(customer_id=customer_id, month=current_month, year=current_year).all()
        if trends:
            scores = [float(t.overall_health_score) for t in trends if t.overall_health_score]
            if scores:
                print(f"\n📊 Health Score Statistics:")
                print(f"   Min: {min(scores):.1f}")
                print(f"   Max: {max(scores):.1f}")
                print(f"   Avg: {sum(scores)/len(scores):.1f}")
                if all(s == 50.0 for s in scores):
                    print("   ⚠️  All scores are 50 - may need to check KPI data")

if __name__ == '__main__':
    recalculate_health_scores(1)



