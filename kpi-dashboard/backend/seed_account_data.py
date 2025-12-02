#!/usr/bin/env python3
"""
Seed Data Script for Account

Creates a complete account with:
- Customer (if needed)
- Account with realistic data
- KPIs across all categories
- Optional: Products with product-level KPIs
- Historical KPI time series data

Usage:
    python3 backend/seed_account_data.py [--customer-id <id>] [--with-products]
"""

import sys
import os
import argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app_v3_minimal import app, db
from models import Customer, Account, KPI, KPIUpload, Product, KPITimeSeries
from datetime import datetime, timedelta
import random
from werkzeug.security import generate_password_hash

# KPI templates with realistic values
KPI_TEMPLATES = [
    # Relationship Strength KPIs
    {"category": "Relationship Strength", "parameter": "Net Promoter Score (NPS)", "healthy_value": 65, "unit": ""},
    {"category": "Relationship Strength", "parameter": "Customer Satisfaction (CSAT)", "healthy_value": 4.3, "unit": ""},
    {"category": "Relationship Strength", "parameter": "Executive Sponsor Engagement", "healthy_value": 85, "unit": "%"},
    {"category": "Relationship Strength", "parameter": "Champion Strength", "healthy_value": 82, "unit": "%"},
    
    # Product Usage KPIs
    {"category": "Product Usage KPI", "parameter": "Product Activation Rate", "healthy_value": 78, "unit": "%"},
    {"category": "Product Usage KPI", "parameter": "Feature Adoption Rate", "healthy_value": 72, "unit": "%"},
    {"category": "Product Usage KPI", "parameter": "Onboarding Completion Rate", "healthy_value": 88, "unit": "%"},
    {"category": "Product Usage KPI", "parameter": "Time to First Value (TTFV)", "healthy_value": 12, "unit": "days"},
    {"category": "Product Usage KPI", "parameter": "Training Participation Rate", "healthy_value": 75, "unit": "%"},
    {"category": "Product Usage KPI", "parameter": "Knowledge Base Usage", "healthy_value": 68, "unit": "%"},
    
    # Support KPIs
    {"category": "Support KPI", "parameter": "First Response Time", "healthy_value": 1.5, "unit": "hours"},
    {"category": "Support KPI", "parameter": "Mean Time to Resolution (MTTR)", "healthy_value": 4.2, "unit": "hours"},
    {"category": "Support KPI", "parameter": "Ticket Volume", "healthy_value": 15, "unit": ""},
    {"category": "Support KPI", "parameter": "Ticket Backlog", "healthy_value": 8, "unit": ""},
    {"category": "Support KPI", "parameter": "First Contact Resolution (FCR)", "healthy_value": 82, "unit": "%"},
    {"category": "Support KPI", "parameter": "Support Cost per Ticket", "healthy_value": 125, "unit": "$"},
    
    # Customer Sentiment KPIs
    {"category": "Customer Sentiment KPI", "parameter": "Customer Complaints", "healthy_value": 2, "unit": ""},
    {"category": "Customer Sentiment KPI", "parameter": "Customer sentiment Trends", "healthy_value": "positive", "unit": ""},
    
    # Business Outcomes KPIs
    {"category": "Business Outcomes KPI", "parameter": "Net Revenue Retention (NRR)", "healthy_value": 108, "unit": "%"},
    {"category": "Business Outcomes KPI", "parameter": "Gross Revenue Retention (GRR)", "healthy_value": 95, "unit": "%"},
    {"category": "Business Outcomes KPI", "parameter": "Revenue Growth", "healthy_value": 15, "unit": "%"},
    {"category": "Business Outcomes KPI", "parameter": "Expansion Revenue", "healthy_value": 250000, "unit": "$"},
    {"category": "Business Outcomes KPI", "parameter": "Upsell and Cross-sell Revenue", "healthy_value": 180000, "unit": "$"},
]

def create_account_seed_data(customer_id=None, account_name=None, with_products=False, num_products=3):
    """
    Create seed data for an account
    
    Args:
        customer_id: Optional customer ID (creates new customer if None)
        account_name: Optional account name (defaults to "Seed Account")
        with_products: Whether to create products with product-level KPIs
        num_products: Number of products to create (if with_products=True)
    """
    
    with app.app_context():
        print("="*70)
        print("SEEDING ACCOUNT DATA")
        print("="*70)
        
        # Step 1: Get or create customer
        print("\n[1/6] Setting up customer...")
        if customer_id:
            customer = Customer.query.get(customer_id)
            if not customer:
                print(f"   ❌ Customer {customer_id} not found")
                return False
            print(f"   ✅ Using existing customer: {customer.customer_name} (ID: {customer.customer_id})")
        else:
            # Create new customer
            customer = Customer.query.filter_by(customer_name="Seed Customer").first()
            if not customer:
                customer = Customer(
                    customer_name="Seed Customer",
                    domain="seedcustomer.com"
                )
                db.session.add(customer)
                db.session.flush()
                print(f"   ✅ Created new customer: {customer.customer_name} (ID: {customer.customer_id})")
            else:
                print(f"   ✅ Using existing customer: {customer.customer_name} (ID: {customer.customer_id})")
        
        customer_id = customer.customer_id
        
        # Step 2: Create account
        print("\n[2/6] Creating account...")
        account_name = account_name or "Seed Account"
        
        # Check if account already exists
        existing_account = Account.query.filter_by(
            customer_id=customer_id,
            account_name=account_name
        ).first()
        
        if existing_account:
            print(f"   ⚠️  Account '{account_name}' already exists (ID: {existing_account.account_id})")
            account = existing_account
        else:
            account = Account(
                customer_id=customer_id,
                account_name=account_name,
                revenue=random.randint(500000, 5000000),  # $500K - $5M
                industry=random.choice(["Technology", "Healthcare", "Financial Services", "Retail", "Manufacturing"]),
                region=random.choice(["North America", "Europe", "Asia Pacific", "Latin America"]),
                account_status="active"
            )
            db.session.add(account)
            db.session.flush()
            print(f"   ✅ Created account: {account.account_name} (ID: {account.account_id})")
            print(f"      Revenue: ${account.revenue:,.0f}")
            print(f"      Industry: {account.industry}")
            print(f"      Region: {account.region}")
        
        account_id = account.account_id
        
        # Step 3: Create KPI Upload
        print("\n[3/6] Creating KPI upload...")
        kpi_upload = KPIUpload(
            customer_id=customer_id,
            account_id=account_id,
            user_id=1,  # Default user
            version=1,
            original_filename=f"{account_name}_KPIs.xlsx"
        )
        db.session.add(kpi_upload)
        db.session.flush()
        print(f"   ✅ Created KPI upload (ID: {kpi_upload.upload_id})")
        
        # Step 4: Create account-level KPIs
        print("\n[4/6] Creating account-level KPIs...")
        account_kpis = []
        
        for template in KPI_TEMPLATES:
            # Add some variance to make it realistic
            base_value = template["healthy_value"]
            if isinstance(base_value, (int, float)):
                variance = base_value * 0.1  # 10% variance
                value = base_value + random.uniform(-variance, variance)
                if template["unit"] == "%":
                    value = max(0, min(100, value))  # Clamp to 0-100
                elif template["unit"] == "$":
                    value = max(0, value)  # No negative revenue
                value_str = f"{value:.2f}{template['unit']}"
            else:
                value_str = str(base_value)
            
            kpi = KPI(
                upload_id=kpi_upload.upload_id,
                account_id=account_id,
                product_id=None,  # Account-level
                aggregation_type=None,  # Legacy/primary
                category=template["category"],
                kpi_parameter=template["parameter"],
                data=value_str,
                impact_level=random.choice(["Critical", "High", "Medium", "Low"]),
                weight=random.choice(["High", "Medium", "Low"]),
                measurement_frequency=random.choice(["Monthly", "Quarterly", "Weekly"]),
                source_review="Seed Data",
                health_score_component=template["category"]
            )
            account_kpis.append(kpi)
        
        db.session.add_all(account_kpis)
        db.session.flush()
        print(f"   ✅ Created {len(account_kpis)} account-level KPIs")
        
        # Step 5: Create products (if requested)
        products = []
        if with_products:
            print("\n[5/6] Creating products with product-level KPIs...")
            
            product_names = ["Core Platform", "Mobile App", "API Gateway", "Analytics Suite", "Integration Hub"]
            
            for i in range(min(num_products, len(product_names))):
                product_name = product_names[i]
                
                # Check if product exists
                existing_product = Product.query.filter_by(
                    account_id=account_id,
                    product_name=product_name
                ).first()
                
                if existing_product:
                    product = existing_product
                    print(f"   ⚠️  Product '{product_name}' already exists (ID: {product.product_id})")
                else:
                    product = Product(
                        account_id=account_id,
                        customer_id=customer_id,
                        product_name=product_name,
                        product_sku=f"SKU-{product_name.upper().replace(' ', '-')}",
                        product_type=random.choice(["Platform", "Application", "Service", "Tool"]),
                        revenue=random.randint(50000, 500000),  # $50K - $500K per product
                        status="active"
                    )
                    db.session.add(product)
                    db.session.flush()
                    print(f"   ✅ Created product: {product_name} (ID: {product.product_id})")
                
                products.append(product)
                
                # Create product-level KPIs for product-specific KPIs
                product_specific_kpis = [
                    "Product Activation Rate",
                    "Feature Adoption Rate",
                    "Ticket Volume",
                    "Support Cost per Ticket",
                    "Net Revenue Retention (NRR)",
                ]
                
                product_kpis = []
                for kpi_template in KPI_TEMPLATES:
                    if kpi_template["parameter"] in product_specific_kpis:
                        # Product-specific value (may differ from account aggregate)
                        base_value = kpi_template["healthy_value"]
                        if isinstance(base_value, (int, float)):
                            variance = base_value * 0.2  # 20% variance for products
                            value = base_value + random.uniform(-variance, variance)
                            if kpi_template["unit"] == "%":
                                value = max(0, min(100, value))
                            elif kpi_template["unit"] == "$":
                                value = max(0, value)
                            value_str = f"{value:.2f}{kpi_template['unit']}"
                        else:
                            value_str = str(base_value)
                        
                        product_kpi = KPI(
                            upload_id=kpi_upload.upload_id,
                            account_id=account_id,
                            product_id=product.product_id,  # Product-level
                            aggregation_type=None,  # Product KPIs have aggregation_type=NULL
                            category=kpi_template["category"],
                            kpi_parameter=kpi_template["parameter"],
                            data=value_str,
                            impact_level=random.choice(["Critical", "High", "Medium", "Low"]),
                            weight=random.choice(["High", "Medium", "Low"]),
                            measurement_frequency=random.choice(["Monthly", "Quarterly"]),
                            source_review="Seed Data - Product Level",
                            health_score_component=kpi_template["category"]
                        )
                        product_kpis.append(product_kpi)
                
                if product_kpis:
                    db.session.add_all(product_kpis)
                    db.session.flush()
                    print(f"      Created {len(product_kpis)} product-level KPIs for {product_name}")
            
            # Create account-level aggregates (weighted averages)
            print("\n   Creating account-level aggregates...")
            for kpi_template in KPI_TEMPLATES:
                if kpi_template["parameter"] in product_specific_kpis:
                    # Calculate weighted average across products
                    product_values = []
                    product_revenues = []
                    for product in products:
                        product_kpi = KPI.query.filter_by(
                            account_id=account_id,
                            product_id=product.product_id,
                            kpi_parameter=kpi_template["parameter"]
                        ).first()
                        if product_kpi and product.revenue:
                            try:
                                value_str = product_kpi.data.replace(kpi_template["unit"], "").strip()
                                value = float(value_str)
                                product_values.append(value)
                                product_revenues.append(float(product.revenue))
                            except:
                                pass
                    
                    if product_values and product_revenues:
                        # Weighted average
                        total_revenue = sum(product_revenues)
                        weighted_avg = sum(v * r for v, r in zip(product_values, product_revenues)) / total_revenue
                        
                        if kpi_template["unit"] == "%":
                            weighted_avg = max(0, min(100, weighted_avg))
                        elif kpi_template["unit"] == "$":
                            weighted_avg = max(0, weighted_avg)
                        
                        aggregate_kpi = KPI(
                            upload_id=kpi_upload.upload_id,
                            account_id=account_id,
                            product_id=None,  # Account-level
                            aggregation_type="weighted_avg",  # Aggregate
                            category=kpi_template["category"],
                            kpi_parameter=kpi_template["parameter"],
                            data=f"{weighted_avg:.2f}{kpi_template['unit']}",
                            impact_level=random.choice(["Critical", "High", "Medium", "Low"]),
                            weight=random.choice(["High", "Medium", "Low"]),
                            measurement_frequency=random.choice(["Monthly", "Quarterly"]),
                            source_review="Seed Data - Account Aggregate",
                            health_score_component=kpi_template["category"]
                        )
                        db.session.add(aggregate_kpi)
            
            db.session.flush()
            print(f"   ✅ Created account-level aggregates")
        else:
            print("\n[5/6] Skipping products (use --with-products to enable)")
        
        # Step 6: Create historical time series data
        print("\n[6/6] Creating historical time series data...")
        time_series_kpis = []
        
        # Get account-level KPIs for time series
        account_level_kpi_list = KPI.query.filter_by(
            account_id=account_id,
            product_id=None,
            aggregation_type=None  # Primary account-level KPIs only
        ).limit(10).all()
        
        if account_level_kpi_list:
            # Create 6 months of historical data
            today = datetime.now()
            for month_offset in range(6, 0, -1):  # Last 6 months
                month_date = today - timedelta(days=30 * month_offset)
                month = month_date.month
                year = month_date.year
                
                for kpi in account_level_kpi_list:
                    # Parse current KPI value
                    try:
                        data_str = kpi.data.replace('%', '').replace('$', '').strip()
                        base_value = float(data_str)
                    except:
                        base_value = 50.0  # Default
                    
                    # Add trend (slight improvement over time)
                    trend = (6 - month_offset) * 0.02  # 2% improvement per month
                    variance = base_value * 0.15
                    value = base_value * (1 + trend) + random.uniform(-variance, variance)
                    
                    # Clamp values appropriately
                    if '%' in kpi.data or 'Rate' in kpi.kpi_parameter or 'Score' in kpi.kpi_parameter:
                        value = max(0, min(100, value))
                    elif '$' in kpi.data or 'Revenue' in kpi.kpi_parameter:
                        value = max(0, value)
                    
                    # Determine health status based on value
                    if value >= 70:
                        health_status = "Healthy"
                        health_score = min(100, value + random.uniform(-5, 5))
                    elif value >= 50:
                        health_status = "Risk"
                        health_score = value + random.uniform(-10, 10)
                    else:
                        health_status = "Critical"
                        health_score = max(0, value + random.uniform(-15, 15))
                    
                    time_series = KPITimeSeries(
                        kpi_id=kpi.kpi_id,  # Link to actual KPI
                        account_id=account_id,
                        customer_id=customer_id,
                        month=month,
                        year=year,
                        value=float(value),
                        health_status=health_status,
                        health_score=max(0, min(100, health_score))
                    )
                    time_series_kpis.append(time_series)
            
            db.session.add_all(time_series_kpis)
            db.session.commit()
            print(f"   ✅ Created {len(time_series_kpis)} time series records (6 months)")
        else:
            print("   ⚠️  No account-level KPIs found, skipping time series")
        
        # Summary
        print("\n" + "="*70)
        print("SEED DATA SUMMARY")
        print("="*70)
        print(f"Customer: {customer.customer_name} (ID: {customer.customer_id})")
        print(f"Account: {account.account_name} (ID: {account.account_id})")
        print(f"  Revenue: ${account.revenue:,.0f}")
        print(f"  Industry: {account.industry}")
        print(f"  Region: {account.region}")
        print(f"\nKPIs Created:")
        print(f"  - Account-level KPIs: {len(account_kpis)}")
        
        if with_products:
            total_product_kpis = sum(
                KPI.query.filter_by(account_id=account_id, product_id=product.product_id).count()
                for product in products
            )
            aggregate_kpis = KPI.query.filter_by(
                account_id=account_id,
                product_id=None,
                aggregation_type="weighted_avg"
            ).count()
            print(f"  - Product-level KPIs: {total_product_kpis}")
            print(f"  - Account aggregates: {aggregate_kpis}")
            print(f"\nProducts Created: {len(products)}")
            for product in products:
                print(f"  - {product.product_name} (ID: {product.product_id}, Revenue: ${product.revenue:,.0f})")
        
        print(f"  - Time series records: {len(time_series_kpis)}")
        print("="*70)
        
        return True

def main():
    parser = argparse.ArgumentParser(description='Seed account data')
    parser.add_argument('--customer-id', type=int, help='Customer ID (creates new customer if not provided)')
    parser.add_argument('--account-name', type=str, help='Account name (defaults to "Seed Account")')
    parser.add_argument('--with-products', action='store_true', help='Create products with product-level KPIs')
    parser.add_argument('--num-products', type=int, default=3, help='Number of products to create (default: 3)')
    
    args = parser.parse_args()
    
    try:
        success = create_account_seed_data(
            customer_id=args.customer_id,
            account_name=args.account_name,
            with_products=args.with_products,
            num_products=args.num_products
        )
        
        if success:
            print("\n✅ Seed data created successfully!")
            return 0
        else:
            print("\n❌ Failed to create seed data")
            return 1
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())

