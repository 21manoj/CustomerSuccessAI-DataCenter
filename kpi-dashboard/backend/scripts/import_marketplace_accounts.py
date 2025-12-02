#!/usr/bin/env python3
"""
Import DCMarketPlace customer account CSV and seed Accounts + basic account-level KPIs.

CSV expected headers (as provided):
  customer_id,company_name,signup_date,customer_segment,instances_rented_30d,
  avg_host_quality_score,interruptible_pct,on_demand_pct,reserved_pct,
  avg_price_vs_market,monthly_spend,contract_value_annual,csm_assigned,
  industry,use_case,health_score,churn_risk,expansion_potential,
  host_switches_30d,days_since_last_rental,support_tickets_30d

Maps to:
  Account(account_name=company_name, revenue=contract_value_annual, industry, region='Global', account_status='active')
  KPIUpload(version=1, original_filename=<csv name>, customer_id, account_id, user_id)
  KPI (account-level) for selected metrics:
    - Health Score (category='Business Outcomes KPI', kpi_parameter='Health Score', data=health_score)
    - Monthly Spend (category='Business Outcomes KPI', kpi_parameter='Monthly Recurring Revenue', data='$<monthly_spend>')
    - Annual Contract Value (category='Business Outcomes KPI', kpi_parameter='Annual Contract Value', data='$<contract_value_annual>')
    - Average Host Quality Score (category='Support & Experience', kpi_parameter='Average Host Quality Score', data=<avg_host_quality_score>)
    - Interruptible % (category='Product Usage KPI', kpi_parameter='Interruptible %', data=f'{interruptible_pct}%')
    - On-demand % (category='Product Usage KPI', kpi_parameter='On-demand %', data=f'{on_demand_pct}%')
    - Reserved % (category='Product Usage KPI', kpi_parameter='Reserved %', data=f'{reserved_pct}%')
    - Host Switches (30d) (category='Support KPI', kpi_parameter='Host Switches (30d)', data=<host_switches_30d>)
    - Days Since Last Rental (category='Adoption & Engagement', kpi_parameter='Days Since Last Rental', data=<days_since_last_rental>)
    - Use Case (category='Product Usage KPI', kpi_parameter='Primary Use Case', data=<use_case>)
    - Customer Segment (category='Relationship Strength KPI', kpi_parameter='Customer Segment', data=<customer_segment>)

Also logs an ActivityLog 'account_create' with signup_date and csm_assigned in details.
"""
import argparse
import os
import pandas as pd
from datetime import datetime
from werkzeug.utils import secure_filename

from app_v3_minimal import app
from models import db, Customer, User, Account, KPIUpload, KPI
from activity_logging import activity_logger


def import_csv(file_path: str, customer_name: str, user_name: str):
    with app.app_context():
        customer = Customer.find_by_name(customer_name) if hasattr(Customer, 'find_by_name') else None
        if customer is None:
            # fallback lookup
            customer = Customer.query.filter_by(customer_name=customer_name).first()
        if customer is None:
            raise RuntimeError(f"Customer '{customer_name}' not found. Please create it first.")
        user = User.query.filter_by(customer_id=customer.customer_id, user_name=user_name).first()
        if user is None:
            # fallback: allow global username lookup
            user = User.query.filter_by(user_name=user_name).first()
        if user is None:
            raise RuntimeError(f"User '{user_name}' not found. Create the user before importing.")
        df = pd.read_csv(file_path, dtype=str, on_bad_lines='skip', engine='python')
        df = df.fillna("")
        created_accounts = 0
        updated_accounts = 0
        created_kpis = 0
        created_products = 0

        upload_filename = os.path.basename(file_path)
        for _, row in df.iterrows():
            company = str(row.get('company_name') or '').strip()
            if not company:
                continue
            # create account
            # Parse numeric fields safely
            def to_float(v):
                try:
                    s = str(v).strip()
                    if s == "" or s.lower() == "nan":
                        return 0.0
                    # strip currency and commas
                    s = s.replace("$", "").replace(",", "")
                    return float(s)
                except Exception:
                    return 0.0
            revenue_annual = to_float(row.get('contract_value_annual'))
            monthly_spend = to_float(row.get('monthly_spend'))
            avg_host_quality = to_float(row.get('avg_host_quality_score'))
            interruptible_pct = row.get('interruptible_pct')
            on_demand_pct = row.get('on_demand_pct')
            reserved_pct = row.get('reserved_pct')
            avg_price_vs_market = row.get('avg_price_vs_market')
            host_switches = to_float(row.get('host_switches_30d'))
            days_since = to_float(row.get('days_since_last_rental'))
            support_tickets = to_float(row.get('support_tickets_30d'))

            # upsert account by name
            account = Account.query.filter_by(customer_id=customer.customer_id, account_name=company).first()
            if account:
                # update select fields if provided
                if monthly_spend:
                    account.revenue = monthly_spend
                if str(row.get('industry') or ''):
                    account.industry = str(row.get('industry') or '')
                if str(row.get('region') or ''):
                    account.region = str(row.get('region') or 'Global')
                updated_accounts += 1
            else:
                account = Account(
                    customer_id=customer.customer_id,
                    account_name=company,
                    revenue= monthly_spend,
                    account_status='active',
                    industry=str(row.get('industry') or ''),
                    region=str(row.get('region') or 'Global')
                )
                db.session.add(account)
                db.session.flush()
                created_accounts += 1
            # ensure product from use_case exists for DCMP (use case as unique product)
            use_case = str(row.get('use_case') or '').strip()
            product_for_use_case = None
            if use_case:
                from models import Product
                existing_product = Product.query.filter_by(
                    customer_id=customer.customer_id,
                    account_id=account.account_id,
                    product_name=use_case
                ).first()
                if existing_product:
                    product_for_use_case = existing_product
                else:
                    prod = Product(
                        customer_id=customer.customer_id,
                        account_id=account.account_id,
                        product_name=use_case,
                        product_type='Use Case',
                        revenue=monthly_spend,
                        status='active'
                    )
                    db.session.add(prod)
                    db.session.flush()
                    product_for_use_case = prod
                    created_products += 1

            # create upload
            upload = KPIUpload(
                customer_id=customer.customer_id,
                account_id=account.account_id,
                user_id=user.user_id,
                uploaded_at=datetime.utcnow(),
                version=1,
                original_filename=upload_filename
            )
            db.session.add(upload)
            db.session.flush()

            def add_kpi(param: str, category: str, data, impact='Medium', freq='Monthly', source='Marketplace', kpi_name=None, product_id=None):
                nonlocal created_kpis
                if data is None or (isinstance(data, str) and data == ""):
                    return
                k = KPI(
                    upload_id=upload.upload_id,
                    account_id=account.account_id,
                    product_id=product_id,
                    aggregation_type=None,
                    category=category,
                    row_index=None,
                    health_score_component=None,
                    kpi_parameter=param if kpi_name is None else kpi_name,
                    weight=None,
                    data=str(data),
                    source_review=source,
                    impact_level=impact,
                    measurement_frequency=freq
                )
                db.session.add(k)
                created_kpis += 1

            # KPIs from CSV (dynamic) - account level
            add_kpi('Health Score', 'Business Outcomes KPI', row.get('health_score'), 'Medium')
            add_kpi('Monthly Recurring Revenue', 'Business Outcomes KPI', f"${row.get('monthly_spend')}", 'Medium')
            add_kpi('Annual Contract Value', 'Business Outcomes KPI', f"${row.get('contract_value_annual')}", 'Medium', 'Yearly')
            add_kpi('Average Host Quality Score', 'Support & Experience', row.get('avg_host_quality_score'), 'Medium')
            add_kpi('Interruptible %', 'Product Usage KPI', f"{row.get('interruptible_pct')}%", 'Medium')
            add_kpi('On-demand %', 'Product Usage KPI', f"{row.get('on_demand_pct')}%", 'Medium')
            add_kpi('Reserved %', 'Product Usage KPI', f"{row.get('reserved_pct')}%", 'Medium')
            add_kpi('Instances Rented (30d)', 'Product Usage KPI', row.get('instances_rented_30d'), 'Medium')
            add_kpi('Host Switches (30d)', 'Support KPI', row.get('host_switches_30d'), 'Medium')
            add_kpi('Support Tickets (30d)', 'Support KPI', row.get('support_tickets_30d'), 'Medium')
            add_kpi('Days Since Last Rental', 'Adoption & Engagement', row.get('days_since_last_rental'), 'Medium')
            # Only dynamic KPIs (exclude static profile fields like segment/use_case/csm)
            add_kpi('Price vs Market %', 'Business Outcomes KPI', f"{avg_price_vs_market}%", 'Medium')
            # qualitative indicators as categorical KPIs (account level)
            if str(row.get('churn_risk') or '').strip():
                add_kpi('Churn Risk Level', 'Customer Sentiment KPI', str(row.get('churn_risk')).strip(), 'Medium', 'Monthly')
            if str(row.get('expansion_potential') or '').strip():
                add_kpi('Expansion Potential Level', 'Business Outcomes KPI', str(row.get('expansion_potential')).strip(), 'Medium', 'Quarterly')

            # If we have a use-case product, also create product-level KPIs for Product Health
            if product_for_use_case:
                pid = product_for_use_case.product_id
                add_kpi('Health Score', 'Business Outcomes KPI', row.get('health_score'), 'Medium', product_id=pid)
                add_kpi('Instances Rented (30d)', 'Product Usage KPI', row.get('instances_rented_30d'), 'Medium', product_id=pid)
                add_kpi('Average Host Quality Score', 'Support & Experience', row.get('avg_host_quality_score'), 'Medium', product_id=pid)
                add_kpi('Interruptible %', 'Product Usage KPI', f"{row.get('interruptible_pct')}%", 'Medium', product_id=pid)
                add_kpi('On-demand %', 'Product Usage KPI', f"{row.get('on_demand_pct')}%", 'Medium', product_id=pid)
                add_kpi('Reserved %', 'Product Usage KPI', f"{row.get('reserved_pct')}%", 'Medium', product_id=pid)
                add_kpi('Price vs Market %', 'Business Outcomes KPI', f"{avg_price_vs_market}%", 'Medium', product_id=pid)
                add_kpi('Host Switches (30d)', 'Support KPI', row.get('host_switches_30d'), 'Medium', product_id=pid)
                add_kpi('Support Tickets (30d)', 'Support KPI', row.get('support_tickets_30d'), 'Medium', product_id=pid)
                add_kpi('Days Since Last Rental', 'Adoption & Engagement', row.get('days_since_last_rental'), 'Medium', product_id=pid)

            # activity log: account_create with signup_date / csm
            try:
                activity_logger.log_account_update(
                    customer_id=customer.customer_id,
                    user_id=user.user_id,
                    account_id=account.account_id,
                    changed_fields=['created', 'signup_date', 'customer_segment', 'csm_assigned'],
                    before_values={},
                    after_values={
                        'created': True,
                        'signup_date': str(row.get('signup_date')),
                        'customer_segment': str(row.get('customer_segment')),
                        'csm_assigned': str(row.get('csm_assigned'))
                    }
                )
            except Exception as e:
                print(f"Warning: failed to log activity for {company}: {e}")

        db.session.commit()
        print(f"✅ Imported {created_accounts} new, updated {updated_accounts} accounts; created {created_kpis} KPIs and {created_products} products for customer '{customer.customer_name}' (id={customer.customer_id})")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="Path to seed_marketplace_customers.csv")
    parser.add_argument("--customer", default="DCMarketPlace", help="Customer name")
    parser.add_argument("--user", default="DCMP1", help="Username to attribute uploads")
    args = parser.parse_args()
    import_csv(args.file, args.customer, args.user)


if __name__ == "__main__":
    main()


