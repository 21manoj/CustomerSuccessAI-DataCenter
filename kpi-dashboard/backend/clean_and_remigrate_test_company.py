#!/usr/bin/env python3
"""
Clean and re-migrate Test Company data from old PostgreSQL
This script:
1. Deletes all Test Company data (accounts, KPIs, uploads, etc.)
2. Re-migrates from old PostgreSQL with proper account_id mapping
3. Migrates customer profile data (profile_metadata)
4. Verifies counts
"""

import os
import sys
from dotenv import load_dotenv
import psycopg2
from urllib.parse import urlparse
from flask import Flask
from extensions import db
from models import Account, KPI, KPIUpload, KPITimeSeries, HealthTrend, Product, Customer

load_dotenv('.env')

# Old PostgreSQL
OLD_PG_URL = 'postgresql://kpi_user@localhost:5432/kpi_dashboard'
# New PostgreSQL
NEW_PG_URL = os.getenv('DATABASE_URL') or os.getenv('SQLALCHEMY_DATABASE_URI')

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = NEW_PG_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

def parse_pg_url(url):
    """Parse PostgreSQL URL"""
    parsed = urlparse(url)
    params = {
        'host': parsed.hostname,
        'port': parsed.port or 5432,
        'database': parsed.path[1:],
        'user': parsed.username
    }
    if parsed.password:
        params['password'] = parsed.password
    return params

def cleanup_test_company():
    """Delete all Test Company data"""
    print("🧹 Cleaning up Test Company (customer_id=1) data...")
    
    with app.app_context():
        # Get all accounts
        accounts = Account.query.filter_by(customer_id=1).all()
        account_ids = [acc.account_id for acc in accounts]
        print(f"   Found {len(accounts)} accounts")
        
        if account_ids:
            # Delete KPIs (including those linked via uploads)
            # First get all upload_ids for this customer
            upload_ids = [u.upload_id for u in KPIUpload.query.filter_by(customer_id=1).all()]
            
            # Delete KPIs by account_id
            kpi_count = KPI.query.filter(KPI.account_id.in_(account_ids)).count()
            if kpi_count > 0:
                KPI.query.filter(KPI.account_id.in_(account_ids)).delete(synchronize_session=False)
                db.session.commit()
                print(f"   ✅ Deleted {kpi_count} KPIs")
            
            # Delete KPIs by upload_id
            if upload_ids:
                kpi_upload_count = KPI.query.filter(KPI.upload_id.in_(upload_ids)).count()
                if kpi_upload_count > 0:
                    KPI.query.filter(KPI.upload_id.in_(upload_ids)).delete(synchronize_session=False)
                    db.session.commit()
                    print(f"   ✅ Deleted {kpi_upload_count} KPIs linked to uploads")
            
            # Delete time series
            ts_count = KPITimeSeries.query.filter(KPITimeSeries.account_id.in_(account_ids)).count()
            if ts_count > 0:
                KPITimeSeries.query.filter(KPITimeSeries.account_id.in_(account_ids)).delete(synchronize_session=False)
                db.session.commit()
                print(f"   ✅ Deleted {ts_count} time series records")
            
            # Delete health trends
            ht_count = HealthTrend.query.filter(HealthTrend.account_id.in_(account_ids)).count()
            if ht_count > 0:
                HealthTrend.query.filter(HealthTrend.account_id.in_(account_ids)).delete(synchronize_session=False)
                db.session.commit()
                print(f"   ✅ Deleted {ht_count} health trends")
            
            # Delete products
            prod_count = Product.query.filter(Product.customer_id == 1).count()
            if prod_count > 0:
                Product.query.filter(Product.customer_id == 1).delete(synchronize_session=False)
                db.session.commit()
                print(f"   ✅ Deleted {prod_count} products")
        
        # Now delete uploads (KPIs are gone)
        upload_count = KPIUpload.query.filter_by(customer_id=1).count()
        if upload_count > 0:
            KPIUpload.query.filter_by(customer_id=1).delete(synchronize_session=False)
            db.session.commit()
            print(f"   ✅ Deleted {upload_count} uploads")
        
        # Delete accounts
        if account_ids:
            Account.query.filter_by(customer_id=1).delete(synchronize_session=False)
            db.session.commit()
            print(f"   ✅ Deleted {len(accounts)} accounts")
        
        print("✅ Cleanup complete!")

def migrate_with_profile_data():
    """Migrate Test Company data including profile_metadata"""
    print("\n🔄 Starting clean migration of Test Company...")
    
    # Connect to old PostgreSQL
    old_params = parse_pg_url(OLD_PG_URL)
    old_conn = psycopg2.connect(**old_params)
    old_cursor = old_conn.cursor()
    
    # Connect to new PostgreSQL
    new_params = parse_pg_url(NEW_PG_URL)
    new_conn = psycopg2.connect(**new_params)
    new_cursor = new_conn.cursor()
    
    customer_id = 1
    
    try:
        # Step 1: Migrate accounts with profile_metadata
        print("\n📦 Migrating accounts with profile data...")
        old_cursor.execute("""
            SELECT account_id, account_name, revenue, account_status, industry, region,
                   external_account_id, profile_metadata, created_at, updated_at
            FROM accounts 
            WHERE customer_id = %s
            ORDER BY account_id
        """, (customer_id,))
        old_accounts = old_cursor.fetchall()
        
        account_id_map = {}
        accounts_migrated = 0
        
        import json as json_lib
        
        for old_acc in old_accounts:
            old_acc_id, acc_name, revenue, status, industry, region, ext_id, profile_meta, created, updated = old_acc
            
            # Convert profile_metadata to JSON string if it's a dict
            if isinstance(profile_meta, dict):
                profile_meta_json = json_lib.dumps(profile_meta)
            elif profile_meta is None:
                profile_meta_json = None
            else:
                profile_meta_json = str(profile_meta)
            
            # Check if account exists
            new_cursor.execute("""
                SELECT account_id FROM accounts 
                WHERE customer_id = %s AND account_name = %s
            """, (customer_id, acc_name))
            existing = new_cursor.fetchone()
            
            if existing:
                new_acc_id = existing[0]
                # Update profile_metadata if missing
                new_cursor.execute("""
                    UPDATE accounts 
                    SET profile_metadata = %s, external_account_id = %s,
                        revenue = %s, industry = %s, region = %s
                    WHERE account_id = %s
                """, (profile_meta_json, ext_id, revenue, industry, region, new_acc_id))
                new_conn.commit()
            else:
                # Insert new account
                new_cursor.execute("""
                    INSERT INTO accounts (customer_id, account_name, revenue, account_status,
                                        industry, region, external_account_id, profile_metadata,
                                        created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING account_id
                """, (customer_id, acc_name, revenue, status, industry, region, ext_id, profile_meta_json, created, updated))
                new_acc_id = new_cursor.fetchone()[0]
                new_conn.commit()
                accounts_migrated += 1
            
            account_id_map[old_acc_id] = new_acc_id
        
        print(f"   ✅ Migrated {accounts_migrated} new accounts, mapped {len(account_id_map)} total")
        
        # Step 2: Migrate uploads
        print("\n📦 Migrating KPI uploads...")
        old_cursor.execute("""
            SELECT upload_id, account_id, user_id, version, original_filename, 
                   uploaded_at, raw_excel, parsed_json
            FROM kpi_uploads
            WHERE customer_id = %s
            ORDER BY upload_id
        """, (customer_id,))
        old_uploads = old_cursor.fetchall()
        
        upload_id_map = {}
        uploads_migrated = 0
        
        for old_upload in old_uploads:
            old_upload_id, old_acc_id, user_id, version, filename, uploaded_at, raw_excel, parsed_json = old_upload
            
            # Map account_id
            new_acc_id = account_id_map.get(old_acc_id)
            if not new_acc_id:
                continue
            
            # Check if upload exists
            new_cursor.execute("""
                SELECT upload_id FROM kpi_uploads
                WHERE customer_id = %s AND account_id = %s AND original_filename = %s
            """, (customer_id, new_acc_id, filename))
            existing = new_cursor.fetchone()
            
            if existing:
                new_upload_id = existing[0]
            else:
                new_cursor.execute("""
                    INSERT INTO kpi_uploads (customer_id, account_id, user_id, version,
                                           original_filename, uploaded_at, raw_excel, parsed_json)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING upload_id
                """, (customer_id, new_acc_id, user_id, version, filename, uploaded_at, raw_excel, parsed_json))
                new_upload_id = new_cursor.fetchone()[0]
                new_conn.commit()
                uploads_migrated += 1
            
            upload_id_map[old_upload_id] = new_upload_id
        
        print(f"   ✅ Migrated {uploads_migrated} new uploads, mapped {len(upload_id_map)} total")
        
        # Step 3: Migrate KPIs
        print("\n📦 Migrating KPIs...")
        old_cursor.execute("""
            SELECT kpi_id, account_id, upload_id, product_id, aggregation_type, category,
                   row_index, health_score_component, weight, data, source_review,
                   kpi_parameter, impact_level, measurement_frequency, last_edited_by, last_edited_at
            FROM kpis
            WHERE account_id IN %s
        """, (tuple(account_id_map.keys()),))
        old_kpis = old_cursor.fetchall()
        
        kpis_migrated = 0
        batch_size = 100
        
        for i in range(0, len(old_kpis), batch_size):
            batch = old_kpis[i:i+batch_size]
            values = []
            
            for old_kpi in batch:
                (kpi_id, old_acc_id, old_upload_id, product_id, agg_type, category,
                 row_idx, health_comp, weight, data, source_review, kpi_param,
                 impact_level, freq, edited_by, edited_at) = old_kpi
                
                new_acc_id = account_id_map.get(old_acc_id)
                new_upload_id = upload_id_map.get(old_upload_id) if old_upload_id else None
                
                if not new_acc_id:
                    continue
                
                # Set product_id to None if it doesn't exist in new DB (avoid FK violation)
                # We'll handle product migration separately if needed
                safe_product_id = None  # Set to None for now to avoid FK issues
                
                values.append((
                    new_acc_id, new_upload_id, safe_product_id, agg_type, category,
                    row_idx, health_comp, weight, data, source_review, kpi_param,
                    impact_level, freq, edited_by, edited_at
                ))
            
            if values:
                from psycopg2.extras import execute_values
                execute_values(
                    new_cursor,
                    """
                    INSERT INTO kpis (account_id, upload_id, product_id, aggregation_type, category,
                                    row_index, health_score_component, weight, data, source_review,
                                    kpi_parameter, impact_level, measurement_frequency, last_edited_by, last_edited_at)
                    VALUES %s
                    ON CONFLICT DO NOTHING
                    """,
                    values
                )
                new_conn.commit()
                kpis_migrated += len(values)
        
        print(f"   ✅ Migrated {kpis_migrated} KPIs")
        
        # Step 4: Migrate health trends
        print("\n📦 Migrating health trends...")
        old_cursor.execute("""
            SELECT account_id, month, year, overall_health_score, product_usage_score,
                   support_score, customer_sentiment_score, business_outcomes_score,
                   relationship_strength_score, total_kpis, valid_kpis
            FROM health_trends
            WHERE account_id IN %s
        """, (tuple(account_id_map.keys()),))
        old_trends = old_cursor.fetchall()
        
        trends_migrated = 0
        for old_trend in old_trends:
            (old_acc_id, month, year, overall, prod_usage, support, sentiment,
             business, relationship, total_kpis, valid_kpis) = old_trend
            
            new_acc_id = account_id_map.get(old_acc_id)
            if not new_acc_id:
                continue
            
            new_cursor.execute("""
                INSERT INTO health_trends (account_id, customer_id, month, year,
                                         overall_health_score, product_usage_score,
                                         support_score, customer_sentiment_score,
                                         business_outcomes_score, relationship_strength_score,
                                         total_kpis, valid_kpis)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (new_acc_id, customer_id, month, year, overall, prod_usage, support,
                  sentiment, business, relationship, total_kpis, valid_kpis))
            trends_migrated += 1
        
        new_conn.commit()
        print(f"   ✅ Migrated {trends_migrated} health trends")
        
        print("\n✅ Migration complete!")
        return len(account_id_map), kpis_migrated, trends_migrated
        
    finally:
        old_conn.close()
        new_conn.close()

def verify_migration():
    """Verify migration results"""
    print("\n📊 Verifying migration...")
    
    with app.app_context():
        accounts = Account.query.filter_by(customer_id=1).all()
        account_ids = [acc.account_id for acc in accounts]
        uploads = KPIUpload.query.filter_by(customer_id=1).all()
        # Count KPIs by account_id (not filtered by upload join)
        kpis = KPI.query.filter(KPI.account_id.in_(account_ids)).all()
        trends = HealthTrend.query.filter_by(customer_id=1).all()
        
        accounts_with_profile = sum(1 for acc in accounts if acc.profile_metadata)
        
        print(f"   Accounts: {len(accounts)} (expected: 36)")
        print(f"   Accounts with profile data: {accounts_with_profile}")
        print(f"   Uploads: {len(uploads)}")
        print(f"   KPIs: {len(kpis)} (expected: ~2383)")
        print(f"   Health trends: {len(trends)}")
        
        if len(accounts) == 36:
            print("   ✅ Account count matches!")
        else:
            print(f"   ⚠️  Account count mismatch")
        
        if len(kpis) >= 2000:
            print("   ✅ KPI count looks good!")
        else:
            print(f"   ⚠️  KPI count is low")

if __name__ == '__main__':
    cleanup_test_company()
    migrate_with_profile_data()
    verify_migration()

