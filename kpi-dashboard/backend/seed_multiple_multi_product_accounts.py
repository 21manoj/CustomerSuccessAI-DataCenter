#!/usr/bin/env python3
"""
Seed Multiple Multi-Product Accounts

Creates 9 accounts with the same 3 products:
- Core Platform
- Mobile App
- API Gateway

50% of accounts (5 accounts) will have low adoption across 1 or more products.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app_v3_minimal import app, db
from models import Customer, Account, KPI, KPIUpload, Product, KPITimeSeries
from datetime import datetime, timedelta
import random
from werkzeug.security import generate_password_hash

# Standard product names (same across all accounts)
STANDARD_PRODUCTS = [
    {"name": "Core Platform", "sku": "SKU-CORE-PLATFORM", "type": "Platform"},
    {"name": "Mobile App", "sku": "SKU-MOBILE-APP", "type": "Application"},
    {"name": "API Gateway", "sku": "SKU-API-GATEWAY", "type": "Service"}
]

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

# Product-specific KPIs (tracked at product level)
PRODUCT_SPECIFIC_KPIS = [
    "Product Activation Rate",
    "Feature Adoption Rate",
    "Ticket Volume",
    "Support Cost per Ticket",
    "Net Revenue Retention (NRR)",
]

# Account names
ACCOUNT_NAMES = [
    "TechVenture Solutions",
    "CloudScale Industries",
    "DataFlow Systems",
    "InnovateLabs Corp",
    "Digital Dynamics Inc",
    "NextGen Technologies",
    "SmartData Solutions",
    "CloudBridge Enterprises",
    "TechMasters Group"
]

INDUSTRIES = ["Technology", "Healthcare", "Financial Services", "Retail", "Manufacturing"]
REGIONS = ["North America", "Europe", "Asia Pacific", "Latin America"]

def create_account_with_products(customer_id, account_name, account_index, has_low_adoption=False):
    """
    Create an account with the standard 3 products
    
    Args:
        customer_id: Customer ID
        account_name: Account name
        account_index: Index (0-8) to determine which products have low adoption
        has_low_adoption: Whether this account should have low adoption
    """
    
    # Create account
    account = Account(
        customer_id=customer_id,
        account_name=account_name,
        revenue=random.randint(500000, 5000000),
        industry=random.choice(INDUSTRIES),
        region=random.choice(REGIONS),
        account_status="active"
    )
    db.session.add(account)
    db.session.flush()
    
    # Create KPI upload
    kpi_upload = KPIUpload(
        customer_id=customer_id,
        account_id=account.account_id,
        user_id=1,
        version=1,
        original_filename=f"{account_name}_KPIs.xlsx"
    )
    db.session.add(kpi_upload)
    db.session.flush()
    
    # Determine which products have low adoption (if applicable)
    low_adoption_products = []
    if has_low_adoption:
        # Randomly select 1-3 products to have low adoption
        num_low = random.randint(1, 3)
        low_adoption_products = random.sample(range(3), num_low)
        print(f"    ⚠️  Low adoption products: {[STANDARD_PRODUCTS[i]['name'] for i in low_adoption_products]}")
    
    # Create products
    products = []
    for i, product_info in enumerate(STANDARD_PRODUCTS):
        product = Product(
            account_id=account.account_id,
            customer_id=customer_id,
            product_name=product_info["name"],
            product_sku=product_info["sku"],
            product_type=product_info["type"],
            revenue=random.randint(50000, 500000),
            status="active"
        )
        db.session.add(product)
        db.session.flush()
        products.append(product)
        
        # Create product-level KPIs
        product_kpis = []
        for kpi_template in KPI_TEMPLATES:
            if kpi_template["parameter"] in PRODUCT_SPECIFIC_KPIS:
                base_value = kpi_template["healthy_value"]
                
                # If this product has low adoption, use low values
                if has_low_adoption and i in low_adoption_products:
                    if "Activation" in kpi_template["parameter"] or "Adoption" in kpi_template["parameter"]:
                        # Low adoption: 20-40%
                        value = random.uniform(20, 40)
                    elif "Ticket" in kpi_template["parameter"]:
                        # High ticket volume (bad)
                        value = base_value * random.uniform(2.0, 4.0)
                    elif "Support Cost" in kpi_template["parameter"]:
                        # High support cost (bad)
                        value = base_value * random.uniform(1.5, 2.5)
                    elif "NRR" in kpi_template["parameter"]:
                        # Low NRR (bad)
                        value = random.uniform(80, 95)
                    else:
                        value = base_value * random.uniform(0.5, 0.8)
                else:
                    # Normal variance
                    variance = base_value * 0.2
                    value = base_value + random.uniform(-variance, variance)
                
                # Clamp values
                if kpi_template["unit"] == "%":
                    value = max(0, min(100, value))
                elif kpi_template["unit"] == "$":
                    value = max(0, value)
                elif kpi_template["unit"] == "days" or kpi_template["unit"] == "hours":
                    value = max(0, value)
                
                value_str = f"{value:.2f}{kpi_template['unit']}"
                
                product_kpi = KPI(
                    upload_id=kpi_upload.upload_id,
                    account_id=account.account_id,
                    product_id=product.product_id,
                    aggregation_type=None,
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
        
        db.session.add_all(product_kpis)
        db.session.flush()
    
    # Create account-level KPIs
    account_kpis = []
    for template in KPI_TEMPLATES:
        base_value = template["healthy_value"]
        
        # Handle string values (like "positive")
        if isinstance(base_value, str):
            value_str = base_value
        else:
            variance = base_value * 0.1
            value = base_value + random.uniform(-variance, variance)
            
            if template["unit"] == "%":
                value = max(0, min(100, value))
            elif template["unit"] == "$":
                value = max(0, value)
            
            value_str = f"{value:.2f}{template['unit']}"
        
        kpi = KPI(
            upload_id=kpi_upload.upload_id,
            account_id=account.account_id,
            product_id=None,
            aggregation_type=None,
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
    
    # Create account-level aggregates (weighted averages)
    aggregate_kpis = []
    for kpi_template in KPI_TEMPLATES:
        if kpi_template["parameter"] in PRODUCT_SPECIFIC_KPIS:
            # Calculate weighted average across products
            product_values = []
            product_revenues = []
            for product in products:
                product_kpi = KPI.query.filter_by(
                    account_id=account.account_id,
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
                total_revenue = sum(product_revenues)
                weighted_avg = sum(v * r for v, r in zip(product_values, product_revenues)) / total_revenue
                
                if kpi_template["unit"] == "%":
                    weighted_avg = max(0, min(100, weighted_avg))
                elif kpi_template["unit"] == "$":
                    weighted_avg = max(0, weighted_avg)
                
                aggregate_kpi = KPI(
                    upload_id=kpi_upload.upload_id,
                    account_id=account.account_id,
                    product_id=None,
                    aggregation_type="weighted_avg",
                    category=kpi_template["category"],
                    kpi_parameter=kpi_template["parameter"],
                    data=f"{weighted_avg:.2f}{kpi_template['unit']}",
                    impact_level=random.choice(["Critical", "High", "Medium", "Low"]),
                    weight=random.choice(["High", "Medium", "Low"]),
                    measurement_frequency=random.choice(["Monthly", "Quarterly"]),
                    source_review="Seed Data - Account Aggregate",
                    health_score_component=kpi_template["category"]
                )
                aggregate_kpis.append(aggregate_kpi)
    
    db.session.add_all(aggregate_kpis)
    db.session.flush()
    
    # Create time series data
    account_level_kpi_list = KPI.query.filter_by(
        account_id=account.account_id,
        product_id=None,
        aggregation_type=None
    ).limit(10).all()
    
    time_series_kpis = []
    if account_level_kpi_list:
        today = datetime.now()
        for month_offset in range(6, 0, -1):
            month_date = today - timedelta(days=30 * month_offset)
            month = month_date.month
            year = month_date.year
            
            for kpi in account_level_kpi_list:
                try:
                    data_str = kpi.data.replace('%', '').replace('$', '').strip()
                    base_value = float(data_str)
                except:
                    base_value = 50.0
                
                trend = (6 - month_offset) * 0.02
                variance = base_value * 0.15
                value = base_value * (1 + trend) + random.uniform(-variance, variance)
                
                if '%' in kpi.data or 'Rate' in kpi.kpi_parameter or 'Score' in kpi.kpi_parameter:
                    value = max(0, min(100, value))
                elif '$' in kpi.data or 'Revenue' in kpi.kpi_parameter:
                    value = max(0, value)
                
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
                    kpi_id=kpi.kpi_id,
                    account_id=account.account_id,
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
    
    return account, products, len(account_kpis), len(product_kpis) * len(products), len(aggregate_kpis), len(time_series_kpis)

def seed_multiple_accounts():
    """Seed 9 accounts with multi-product data"""
    
    with app.app_context():
        print("="*70)
        print("SEEDING 9 MULTI-PRODUCT ACCOUNTS")
        print("="*70)
        
        # Get or create customer
        customer = Customer.query.filter_by(customer_name="Seed Customer").first()
        if not customer:
            customer = Customer(
                customer_name="Seed Customer",
                domain="seedcustomer.com"
            )
            db.session.add(customer)
            db.session.flush()
        
        customer_id = customer.customer_id
        print(f"\nUsing customer: {customer.customer_name} (ID: {customer_id})")
        
        # Determine which accounts have low adoption (5 out of 9)
        low_adoption_indices = random.sample(range(9), 5)
        print(f"\nAccounts with low adoption: {[ACCOUNT_NAMES[i] for i in low_adoption_indices]}")
        print("\n" + "-"*70)
        
        results = []
        for i, account_name in enumerate(ACCOUNT_NAMES):
            has_low_adoption = i in low_adoption_indices
            print(f"\n[{i+1}/9] Creating: {account_name}")
            if has_low_adoption:
                print(f"    ⚠️  This account will have low adoption")
            
            account, products, account_kpis, product_kpis, aggregates, time_series = create_account_with_products(
                customer_id, account_name, i, has_low_adoption
            )
            
            results.append({
                'account': account,
                'products': products,
                'account_kpis': account_kpis,
                'product_kpis': product_kpis,
                'aggregates': aggregates,
                'time_series': time_series,
                'has_low_adoption': has_low_adoption
            })
            
            print(f"    ✅ Created account ID: {account.account_id}")
            print(f"       Revenue: ${account.revenue:,.0f}")
            print(f"       Products: {len(products)}")
            print(f"       Account KPIs: {account_kpis}")
            print(f"       Product KPIs: {product_kpis}")
            print(f"       Aggregates: {aggregates}")
            print(f"       Time Series: {time_series}")
        
        # Summary
        print("\n" + "="*70)
        print("SEED DATA SUMMARY")
        print("="*70)
        print(f"Total accounts created: {len(results)}")
        print(f"Accounts with low adoption: {sum(1 for r in results if r['has_low_adoption'])}")
        print(f"Accounts with normal adoption: {sum(1 for r in results if not r['has_low_adoption'])}")
        print(f"\nTotal products: {sum(len(r['products']) for r in results)}")
        print(f"Total account KPIs: {sum(r['account_kpis'] for r in results)}")
        print(f"Total product KPIs: {sum(r['product_kpis'] for r in results)}")
        print(f"Total aggregates: {sum(r['aggregates'] for r in results)}")
        print(f"Total time series records: {sum(r['time_series'] for r in results)}")
        
        print("\n" + "-"*70)
        print("ACCOUNTS WITH LOW ADOPTION:")
        print("-"*70)
        for r in results:
            if r['has_low_adoption']:
                print(f"  - {r['account'].account_name} (ID: {r['account'].account_id})")
        
        print("\n" + "-"*70)
        print("PRODUCT DISTRIBUTION:")
        print("-"*70)
        for product_info in STANDARD_PRODUCTS:
            product_count = sum(1 for r in results for p in r['products'] if p.product_name == product_info['name'])
            print(f"  - {product_info['name']}: {product_count} instances")
        
        print("="*70)
        print("\n✅ All accounts created successfully!")

def add_product_kpis_to_existing_accounts(customer_id=1):
    """
    Add product-level KPIs to existing accounts that have products in profile_metadata
    but don't have product-level KPIs yet
    """
    
    with app.app_context():
        print("="*70)
        print("ADDING PRODUCT-LEVEL KPIs TO EXISTING ACCOUNTS")
        print("="*70)
        
        # Get all accounts for the customer
        accounts = Account.query.filter_by(customer_id=customer_id).all()
        
        accounts_to_update = []
        for account in accounts:
            profile_products = account.profile_metadata.get('products_used') if account.profile_metadata else None
            if profile_products and profile_products.strip():
                # Check if they have product-level KPIs
                product_kpis = KPI.query.filter_by(account_id=account.account_id).filter(
                    KPI.product_id.isnot(None), KPI.product_id != 0
                ).count()
                if product_kpis == 0:
                    accounts_to_update.append(account)
        
        print(f"\nFound {len(accounts_to_update)} accounts that need product-level KPIs")
        
        if not accounts_to_update:
            print("✅ All accounts already have product-level KPIs!")
            return
        
        # Get or create KPI upload
        kpi_upload = KPIUpload.query.filter_by(customer_id=customer_id).order_by(KPIUpload.upload_id.desc()).first()
        if not kpi_upload:
            kpi_upload = KPIUpload(
                customer_id=customer_id,
                account_id=None,
                user_id=1,
                version=1,
                original_filename="Product_KPIs_Seed.xlsx"
            )
            db.session.add(kpi_upload)
            db.session.flush()
        
        total_product_kpis_created = 0
        
        for account in accounts_to_update:
            print(f"\n[{accounts_to_update.index(account)+1}/{len(accounts_to_update)}] Processing: {account.account_name}")
            
            profile_products = account.profile_metadata.get('products_used', '') if account.profile_metadata else ''
            product_names = [p.strip() for p in profile_products.split(',') if p.strip()]
            
            if not product_names:
                print(f"    ⚠️  No products found in profile_metadata, skipping")
                continue
            
            print(f"    Products from metadata: {', '.join(product_names)}")
            
            # Get or create products
            products = []
            for product_name in product_names:
                # Check if product already exists
                existing_product = Product.query.filter_by(
                    account_id=account.account_id,
                    product_name=product_name
                ).first()
                
                if not existing_product:
                    # Create product
                    product = Product(
                        account_id=account.account_id,
                        customer_id=customer_id,
                        product_name=product_name,
                        product_sku=f"SKU-{product_name.upper().replace(' ', '-')}",
                        product_type="Platform" if "Platform" in product_name else "Application",
                        revenue=random.randint(50000, 500000),
                        status="active"
                    )
                    db.session.add(product)
                    db.session.flush()
                    products.append(product)
                    print(f"    ✅ Created product: {product_name}")
                else:
                    products.append(existing_product)
                    print(f"    ✓ Using existing product: {product_name}")
            
            # Create product-level KPIs for each product
            for product in products:
                product_kpis = []
                for kpi_template in KPI_TEMPLATES:
                    if kpi_template["parameter"] in PRODUCT_SPECIFIC_KPIS:
                        base_value = kpi_template["healthy_value"]
                        variance = base_value * 0.15
                        value = base_value + random.uniform(-variance, variance)
                        
                        # Clamp values
                        if kpi_template["unit"] == "%":
                            value = max(0, min(100, value))
                        elif kpi_template["unit"] == "$":
                            value = max(0, value)
                        elif kpi_template["unit"] == "days" or kpi_template["unit"] == "hours":
                            value = max(0, value)
                        
                        value_str = f"{value:.2f}{kpi_template['unit']}"
                        
                        product_kpi = KPI(
                            upload_id=kpi_upload.upload_id,
                            account_id=account.account_id,
                            product_id=product.product_id,
                            aggregation_type=None,
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
                
                db.session.add_all(product_kpis)
                total_product_kpis_created += len(product_kpis)
                print(f"      ✅ Created {len(product_kpis)} KPIs for {product.product_name}")
        
        db.session.commit()
        
        print("\n" + "="*70)
        print("SUMMARY")
        print("="*70)
        print(f"✅ Updated {len(accounts_to_update)} accounts")
        print(f"✅ Created {total_product_kpis_created} product-level KPIs")
        print("="*70)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--existing":
        add_product_kpis_to_existing_accounts()
    else:
        seed_multiple_accounts()

