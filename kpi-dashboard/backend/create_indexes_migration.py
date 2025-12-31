#!/usr/bin/env python3
"""
Create and apply database indexes migration
Adds performance indexes for accounts, KPIs, and related tables
"""

from app import app
from extensions import db
from sqlalchemy import text

def create_indexes():
    """Create all performance indexes"""
    with app.app_context():
        print("🔨 Creating database indexes...")
        print()
        
        # Indexes for accounts table
        indexes = [
            # Account table indexes
            ("idx_accounts_customer_id", "CREATE INDEX IF NOT EXISTS idx_accounts_customer_id ON accounts(customer_id)"),
            ("idx_accounts_account_name", "CREATE INDEX IF NOT EXISTS idx_accounts_account_name ON accounts(account_name)"),
            ("idx_accounts_account_status", "CREATE INDEX IF NOT EXISTS idx_accounts_account_status ON accounts(account_status)"),
            ("idx_accounts_industry", "CREATE INDEX IF NOT EXISTS idx_accounts_industry ON accounts(industry)"),
            ("idx_accounts_region", "CREATE INDEX IF NOT EXISTS idx_accounts_region ON accounts(region)"),
            ("idx_accounts_external_account_id", "CREATE INDEX IF NOT EXISTS idx_accounts_external_account_id ON accounts(external_account_id)"),
            ("idx_accounts_created_at", "CREATE INDEX IF NOT EXISTS idx_accounts_created_at ON accounts(created_at)"),
            ("idx_account_customer_status", "CREATE INDEX IF NOT EXISTS idx_account_customer_status ON accounts(customer_id, account_status)"),
            ("idx_account_customer_industry", "CREATE INDEX IF NOT EXISTS idx_account_customer_industry ON accounts(customer_id, industry)"),
            ("idx_account_customer_region", "CREATE INDEX IF NOT EXISTS idx_account_customer_region ON accounts(customer_id, region)"),
            
            # KPI table indexes
            ("idx_kpis_upload_id", "CREATE INDEX IF NOT EXISTS idx_kpis_upload_id ON kpis(upload_id)"),
            ("idx_kpis_account_id", "CREATE INDEX IF NOT EXISTS idx_kpis_account_id ON kpis(account_id)"),
            ("idx_kpis_product_id", "CREATE INDEX IF NOT EXISTS idx_kpis_product_id ON kpis(product_id)"),
            ("idx_kpis_aggregation_type", "CREATE INDEX IF NOT EXISTS idx_kpis_aggregation_type ON kpis(aggregation_type)"),
            ("idx_kpis_category", "CREATE INDEX IF NOT EXISTS idx_kpis_category ON kpis(category)"),
            ("idx_kpis_health_score_component", "CREATE INDEX IF NOT EXISTS idx_kpis_health_score_component ON kpis(health_score_component)"),
            ("idx_kpis_kpi_parameter", "CREATE INDEX IF NOT EXISTS idx_kpis_kpi_parameter ON kpis(kpi_parameter)"),
            ("idx_kpis_impact_level", "CREATE INDEX IF NOT EXISTS idx_kpis_impact_level ON kpis(impact_level)"),
            ("idx_kpis_last_edited_at", "CREATE INDEX IF NOT EXISTS idx_kpis_last_edited_at ON kpis(last_edited_at)"),
            ("idx_kpi_account_category", "CREATE INDEX IF NOT EXISTS idx_kpi_account_category ON kpis(account_id, category)"),
            ("idx_kpi_account_parameter", "CREATE INDEX IF NOT EXISTS idx_kpi_account_parameter ON kpis(account_id, kpi_parameter)"),
            ("idx_kpi_account_aggregation", "CREATE INDEX IF NOT EXISTS idx_kpi_account_aggregation ON kpis(account_id, aggregation_type)"),
            ("idx_kpi_upload_account", "CREATE INDEX IF NOT EXISTS idx_kpi_upload_account ON kpis(upload_id, account_id)"),
            
            # KPIUpload table indexes
            ("idx_kpi_uploads_customer_id", "CREATE INDEX IF NOT EXISTS idx_kpi_uploads_customer_id ON kpi_uploads(customer_id)"),
            ("idx_kpi_uploads_account_id", "CREATE INDEX IF NOT EXISTS idx_kpi_uploads_account_id ON kpi_uploads(account_id)"),
            ("idx_kpi_uploads_user_id", "CREATE INDEX IF NOT EXISTS idx_kpi_uploads_user_id ON kpi_uploads(user_id)"),
            ("idx_kpi_uploads_uploaded_at", "CREATE INDEX IF NOT EXISTS idx_kpi_uploads_uploaded_at ON kpi_uploads(uploaded_at)"),
            ("idx_upload_customer_uploaded", "CREATE INDEX IF NOT EXISTS idx_upload_customer_uploaded ON kpi_uploads(customer_id, uploaded_at)"),
            ("idx_upload_account_uploaded", "CREATE INDEX IF NOT EXISTS idx_upload_account_uploaded ON kpi_uploads(account_id, uploaded_at)"),
            
            # HealthTrend table indexes
            ("idx_health_trends_account_id", "CREATE INDEX IF NOT EXISTS idx_health_trends_account_id ON health_trends(account_id)"),
            ("idx_health_trends_customer_id", "CREATE INDEX IF NOT EXISTS idx_health_trends_customer_id ON health_trends(customer_id)"),
            ("idx_health_trends_month", "CREATE INDEX IF NOT EXISTS idx_health_trends_month ON health_trends(month)"),
            ("idx_health_trends_year", "CREATE INDEX IF NOT EXISTS idx_health_trends_year ON health_trends(year)"),
            ("idx_health_trends_created_at", "CREATE INDEX IF NOT EXISTS idx_health_trends_created_at ON health_trends(created_at)"),
            ("idx_health_trend_account_date", "CREATE INDEX IF NOT EXISTS idx_health_trend_account_date ON health_trends(account_id, year, month)"),
            ("idx_health_trend_customer_date", "CREATE INDEX IF NOT EXISTS idx_health_trend_customer_date ON health_trends(customer_id, year, month)"),
            
            # KPITimeSeries table indexes
            ("idx_kpi_time_series_kpi_id", "CREATE INDEX IF NOT EXISTS idx_kpi_time_series_kpi_id ON kpi_time_series(kpi_id)"),
            ("idx_kpi_time_series_account_id", "CREATE INDEX IF NOT EXISTS idx_kpi_time_series_account_id ON kpi_time_series(account_id)"),
            ("idx_kpi_time_series_customer_id", "CREATE INDEX IF NOT EXISTS idx_kpi_time_series_customer_id ON kpi_time_series(customer_id)"),
            ("idx_kpi_time_series_month", "CREATE INDEX IF NOT EXISTS idx_kpi_time_series_month ON kpi_time_series(month)"),
            ("idx_kpi_time_series_year", "CREATE INDEX IF NOT EXISTS idx_kpi_time_series_year ON kpi_time_series(year)"),
            ("idx_kpi_time_series_health_status", "CREATE INDEX IF NOT EXISTS idx_kpi_time_series_health_status ON kpi_time_series(health_status)"),
            ("idx_kpi_time_series_created_at", "CREATE INDEX IF NOT EXISTS idx_kpi_time_series_created_at ON kpi_time_series(created_at)"),
            ("idx_time_series_kpi_date", "CREATE INDEX IF NOT EXISTS idx_time_series_kpi_date ON kpi_time_series(kpi_id, year, month)"),
            ("idx_time_series_account_date", "CREATE INDEX IF NOT EXISTS idx_time_series_account_date ON kpi_time_series(account_id, year, month)"),
            ("idx_time_series_customer_date", "CREATE INDEX IF NOT EXISTS idx_time_series_customer_date ON kpi_time_series(customer_id, year, month)"),
        ]
        
        created_count = 0
        skipped_count = 0
        error_count = 0
        
        for idx_name, sql in indexes:
            try:
                db.session.execute(text(sql))
                # Check if index was created
                result = db.session.execute(text(
                    f"SELECT COUNT(*) FROM pg_indexes WHERE indexname = '{idx_name}'"
                )).scalar()
                if result > 0:
                    created_count += 1
                    print(f"✅ {idx_name}")
                else:
                    skipped_count += 1
                    print(f"⏭️  {idx_name} (already exists or skipped)")
            except Exception as e:
                error_count += 1
                print(f"❌ {idx_name}: {str(e)}")
        
        # Commit all changes
        try:
            db.session.commit()
            print()
            print("="*70)
            print("📊 Index Creation Summary")
            print("="*70)
            print(f"✅ Created: {created_count}")
            print(f"⏭️  Skipped (already exists): {skipped_count}")
            print(f"❌ Errors: {error_count}")
            print(f"📝 Total: {len(indexes)}")
            print("="*70)
            
            if error_count == 0:
                print("\n✅ All indexes created successfully!")
            else:
                print(f"\n⚠️  {error_count} errors occurred. Check messages above.")
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Error committing changes: {str(e)}")
            raise

def verify_indexes():
    """Verify indexes were created"""
    with app.app_context():
        print("\n🔍 Verifying indexes...")
        print()
        
        result = db.session.execute(text("""
            SELECT 
                tablename,
                COUNT(*) as index_count
            FROM pg_indexes
            WHERE schemaname = 'public'
            AND tablename IN ('accounts', 'kpis', 'kpi_uploads', 'health_trends', 'kpi_time_series')
            GROUP BY tablename
            ORDER BY tablename
        """))
        
        print("Index counts by table:")
        for row in result:
            print(f"  ✅ {row[0]}: {row[1]} indexes")

if __name__ == '__main__':
    try:
        create_indexes()
        verify_indexes()
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        exit(1)

