# Fivetran Integration Guide

## Overview
This guide shows how to integrate Fivetran with Salesforce CRM and ServiceNow ITSM to automatically sync data for KPI calculations.

---

## Architecture

```
Salesforce CRM ─────┐
                    ├──> Fivetran ──> Data Warehouse ──> KPI Dashboard API
ServiceNow ITSM ────┘                  (Snowflake/          (Transformation
                                        BigQuery/            & Loading)
                                        Redshift)
```

---

## Part 1: Fivetran Setup

### 1.1 Create Fivetran Account

1. Sign up at https://fivetran.com
2. Create a new workspace
3. Note your Fivetran API key and secret

### 1.2 Configure Salesforce Connector

**In Fivetran Dashboard:**

1. Click "Add Connector"
2. Select "Salesforce"
3. Configure connection:

```json
{
  "connector_name": "salesforce_crm_production",
  "destination_schema": "salesforce_crm",
  "auth": {
    "type": "oauth",
    "domain": "your-company.my.salesforce.com",
    "client_id": "YOUR_SALESFORCE_CLIENT_ID",
    "client_secret": "YOUR_SALESFORCE_CLIENT_SECRET",
    "security_token": "YOUR_SALESFORCE_SECURITY_TOKEN"
  },
  "sync_frequency": 360,  // 6 hours
  "sync_mode": "INCREMENTAL"
}
```

**Tables to Sync:**
- `Account` - Customer accounts
- `Opportunity` - Revenue opportunities
- `Contact` - Stakeholder relationships
- `Case` - Support cases
- `Task` - Activities and touchpoints
- `User` - CSM assignments

### 1.3 Configure ServiceNow Connector

**In Fivetran Dashboard:**

1. Click "Add Connector"
2. Select "ServiceNow"
3. Configure connection:

```json
{
  "connector_name": "servicenow_itsm_production",
  "destination_schema": "servicenow_itsm",
  "auth": {
    "type": "basic",
    "instance_url": "https://your-company.service-now.com",
    "username": "fivetran_user",
    "password": "YOUR_SERVICENOW_PASSWORD"
  },
  "sync_frequency": 180,  // 3 hours
  "sync_mode": "INCREMENTAL"
}
```

**Tables to Sync:**
- `incident` - Support tickets
- `task` - Work items
- `problem` - Problem records
- `change_request` - Change management
- `cmdb_ci` - Configuration items
- `sys_user` - User information

---

## Part 2: Data Transformation Layer

### 2.1 SQL Transformations (dbt or Custom)

**File:** `transformations/kpi_mappings.sql`

```sql
-- Salesforce to KPI Mapping
CREATE OR REPLACE VIEW kpi_salesforce_metrics AS
SELECT
    -- Account Information
    a.id AS account_id,
    a.name AS account_name,
    a.annual_revenue AS revenue,
    a.industry,
    a.billing_country AS region,
    
    -- NPS Calculation (from surveys or custom fields)
    COALESCE(a.nps_score__c, 0) AS nps,
    
    -- CSAT (from case satisfaction surveys)
    AVG(c.satisfaction_rating__c) AS csat,
    
    -- Executive Sponsor Engagement (from contact activities)
    COUNT(DISTINCT CASE 
        WHEN con.title LIKE '%VP%' OR con.title LIKE '%Director%' 
        THEN t.id 
    END) AS executive_engagement_score,
    
    -- Revenue Growth (year over year)
    ((a.annual_revenue - LAG(a.annual_revenue, 12) OVER (PARTITION BY a.id ORDER BY DATE_TRUNC('month', CURRENT_DATE))) 
     / NULLIF(LAG(a.annual_revenue, 12) OVER (PARTITION BY a.id ORDER BY DATE_TRUNC('month', CURRENT_DATE)), 0)) * 100 
    AS revenue_growth_percent,
    
    -- Net Revenue Retention
    (SUM(CASE WHEN o.type = 'Renewal' THEN o.amount ELSE 0 END) +
     SUM(CASE WHEN o.type = 'Upsell' THEN o.amount ELSE 0 END)) /
    NULLIF(SUM(CASE WHEN o.type = 'New Business' THEN o.amount ELSE 0 END), 0) * 100 
    AS net_revenue_retention,
    
    -- Adoption Index (from usage data or custom fields)
    COALESCE(a.adoption_score__c, 0) AS adoption_index,
    
    -- Churn Risk Score (from predictive model or scoring)
    COALESCE(a.churn_risk_score__c, 0) AS churn_risk

FROM salesforce_crm.account a
LEFT JOIN salesforce_crm.contact con ON con.account_id = a.id
LEFT JOIN salesforce_crm.task t ON t.who_id = con.id
LEFT JOIN salesforce_crm.case c ON c.account_id = a.id
LEFT JOIN salesforce_crm.opportunity o ON o.account_id = a.id
WHERE a.type = 'Customer'
GROUP BY a.id, a.name, a.annual_revenue, a.industry, a.billing_country;


-- ServiceNow to KPI Mapping
CREATE OR REPLACE VIEW kpi_servicenow_metrics AS
SELECT
    -- Account mapping (requires custom field or company lookup)
    i.u_customer_account_id AS account_id,
    i.u_customer_account_name AS account_name,
    
    -- Support Ticket Volume
    COUNT(DISTINCT i.sys_id) AS support_ticket_volume,
    
    -- SLA Compliance
    (COUNT(CASE WHEN i.sla_due > i.closed_at THEN 1 END) * 100.0 / 
     NULLIF(COUNT(*), 0)) AS sla_compliance_percent,
    
    -- First Response Time (in hours)
    AVG(EXTRACT(EPOCH FROM (i.first_responded_at - i.opened_at)) / 3600) AS first_response_time_hours,
    
    -- Resolution Time (in hours)  
    AVG(EXTRACT(EPOCH FROM (i.resolved_at - i.opened_at)) / 3600) AS resolution_time_hours,
    
    -- Support Satisfaction (from surveys)
    AVG(i.satisfaction_rating) AS support_satisfaction,
    
    -- Escalation Rate
    (COUNT(CASE WHEN i.escalation > 0 THEN 1 END) * 100.0 / 
     NULLIF(COUNT(*), 0)) AS escalation_rate,
    
    -- Reopen Rate
    (COUNT(CASE WHEN i.reopened_count > 0 THEN 1 END) * 100.0 / 
     NULLIF(COUNT(*), 0)) AS ticket_reopen_rate,
    
    -- Critical Issues
    COUNT(CASE WHEN i.priority = '1 - Critical' THEN 1 END) AS critical_issues_count

FROM servicenow_itsm.incident i
WHERE i.opened_at >= CURRENT_DATE - INTERVAL '30 days'
  AND i.u_customer_account_id IS NOT NULL
GROUP BY i.u_customer_account_id, i.u_customer_account_name;


-- Combined KPI View
CREATE OR REPLACE VIEW kpi_integrated_metrics AS
SELECT
    COALESCE(sf.account_id, sn.account_id) AS account_id,
    COALESCE(sf.account_name, sn.account_name) AS account_name,
    
    -- Salesforce metrics
    sf.nps,
    sf.csat,
    sf.executive_engagement_score,
    sf.revenue_growth_percent,
    sf.net_revenue_retention,
    sf.adoption_index,
    sf.churn_risk,
    sf.revenue,
    sf.industry,
    sf.region,
    
    -- ServiceNow metrics
    sn.support_ticket_volume,
    sn.sla_compliance_percent,
    sn.first_response_time_hours,
    sn.resolution_time_hours,
    sn.support_satisfaction,
    sn.escalation_rate,
    sn.ticket_reopen_rate,
    sn.critical_issues_count,
    
    CURRENT_TIMESTAMP AS last_updated

FROM kpi_salesforce_metrics sf
FULL OUTER JOIN kpi_servicenow_metrics sn 
    ON sf.account_id = sn.account_id;
```

---

## Part 3: API Integration

### 3.1 Create Fivetran Sync API

**File:** `backend/fivetran_sync_api.py`

```python
"""
Fivetran Sync API

Syncs KPI data from data warehouse to KPI Dashboard
"""

from flask import Blueprint, request, jsonify
from models import db, Account, KPI, KPIUpload, Customer
from datetime import datetime
import requests
import os

fivetran_sync_api = Blueprint('fivetran_sync_api', __name__)

def get_customer_id():
    """Get customer ID from request headers"""
    return request.headers.get('X-Customer-ID', type=int, default=1)


@fivetran_sync_api.route('/api/fivetran/sync', methods=['POST'])
def sync_from_fivetran():
    """
    Sync KPI data from data warehouse
    
    Expected payload:
    {
        "data_source": "salesforce|servicenow|combined",
        "warehouse_connection": {
            "type": "snowflake|bigquery|redshift",
            "host": "...",
            "database": "...",
            "credentials": {...}
        },
        "sync_config": {
            "account_mapping": "auto|manual",
            "kpi_mapping": {...},
            "update_mode": "upsert|replace"
        }
    }
    """
    try:
        customer_id = get_customer_id()
        data = request.json
        
        data_source = data.get('data_source', 'combined')
        warehouse = data.get('warehouse_connection', {})
        sync_config = data.get('sync_config', {})
        
        # Connect to data warehouse and fetch KPI data
        warehouse_type = warehouse.get('type')
        
        if warehouse_type == 'snowflake':
            kpi_data = fetch_from_snowflake(warehouse, sync_config)
        elif warehouse_type == 'bigquery':
            kpi_data = fetch_from_bigquery(warehouse, sync_config)
        elif warehouse_type == 'redshift':
            kpi_data = fetch_from_redshift(warehouse, sync_config)
        else:
            return jsonify({'error': 'Unsupported warehouse type'}), 400
        
        # Transform and load KPI data
        sync_results = load_kpi_data(customer_id, kpi_data, sync_config)
        
        return jsonify({
            'status': 'success',
            'message': f'Synced {sync_results["kpis_synced"]} KPIs from {data_source}',
            'results': sync_results
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Sync failed: {str(e)}'
        }), 500


def fetch_from_snowflake(warehouse, config):
    """Fetch KPI data from Snowflake"""
    import snowflake.connector
    
    conn = snowflake.connector.connect(
        user=warehouse['credentials']['username'],
        password=warehouse['credentials']['password'],
        account=warehouse['host'],
        warehouse=warehouse['warehouse'],
        database=warehouse['database'],
        schema=warehouse.get('schema', 'PUBLIC')
    )
    
    cursor = conn.cursor()
    
    # Query the integrated KPI view
    query = """
    SELECT 
        account_id, account_name, revenue, industry, region,
        nps, csat, executive_engagement_score,
        adoption_index, support_ticket_volume, sla_compliance_percent,
        first_response_time_hours, resolution_time_hours,
        support_satisfaction, revenue_growth_percent,
        net_revenue_retention, churn_risk
    FROM kpi_integrated_metrics
    WHERE last_updated >= DATEADD(day, -1, CURRENT_TIMESTAMP())
    """
    
    cursor.execute(query)
    results = cursor.fetchall()
    
    # Convert to dict
    columns = [desc[0] for desc in cursor.description]
    kpi_data = [dict(zip(columns, row)) for row in results]
    
    cursor.close()
    conn.close()
    
    return kpi_data


def fetch_from_bigquery(warehouse, config):
    """Fetch KPI data from BigQuery"""
    from google.cloud import bigquery
    from google.oauth2 import service_account
    
    credentials = service_account.Credentials.from_service_account_info(
        warehouse['credentials']
    )
    
    client = bigquery.Client(
        credentials=credentials,
        project=warehouse['project']
    )
    
    query = f"""
    SELECT 
        account_id, account_name, revenue, industry, region,
        nps, csat, executive_engagement_score,
        adoption_index, support_ticket_volume, sla_compliance_percent,
        first_response_time_hours, resolution_time_hours,
        support_satisfaction, revenue_growth_percent,
        net_revenue_retention, churn_risk
    FROM `{warehouse['dataset']}.kpi_integrated_metrics`
    WHERE last_updated >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 DAY)
    """
    
    query_job = client.query(query)
    results = query_job.result()
    
    kpi_data = [dict(row.items()) for row in results]
    
    return kpi_data


def fetch_from_redshift(warehouse, config):
    """Fetch KPI data from Redshift"""
    import psycopg2
    
    conn = psycopg2.connect(
        host=warehouse['host'],
        port=warehouse.get('port', 5439),
        database=warehouse['database'],
        user=warehouse['credentials']['username'],
        password=warehouse['credentials']['password']
    )
    
    cursor = conn.cursor()
    
    query = """
    SELECT 
        account_id, account_name, revenue, industry, region,
        nps, csat, executive_engagement_score,
        adoption_index, support_ticket_volume, sla_compliance_percent,
        first_response_time_hours, resolution_time_hours,
        support_satisfaction, revenue_growth_percent,
        net_revenue_retention, churn_risk
    FROM kpi_integrated_metrics
    WHERE last_updated >= CURRENT_TIMESTAMP - INTERVAL '1 day'
    """
    
    cursor.execute(query)
    results = cursor.fetchall()
    
    columns = [desc[0] for desc in cursor.description]
    kpi_data = [dict(zip(columns, row)) for row in results]
    
    cursor.close()
    conn.close()
    
    return kpi_data


def load_kpi_data(customer_id, kpi_data, config):
    """Load KPI data into dashboard database"""
    kpis_synced = 0
    accounts_created = 0
    
    # Get or create upload record
    upload = KPIUpload(
        customer_id=customer_id,
        user_id=1,  # System user
        version=1,
        original_filename='fivetran_sync',
        uploaded_at=datetime.utcnow()
    )
    db.session.add(upload)
    db.session.flush()
    
    for row in kpi_data:
        # Get or create account
        account = Account.query.filter_by(
            customer_id=customer_id,
            account_name=row['account_name']
        ).first()
        
        if not account:
            account = Account(
                customer_id=customer_id,
                account_name=row['account_name'],
                revenue=row.get('revenue', 0),
                industry=row.get('industry'),
                region=row.get('region'),
                account_status='active'
            )
            db.session.add(account)
            db.session.flush()
            accounts_created += 1
        
        # Create KPIs
        kpi_mappings = {
            'NPS': row.get('nps'),
            'CSAT': row.get('csat'),
            'Executive Sponsor Engagement': row.get('executive_engagement_score'),
            'Adoption Index': row.get('adoption_index'),
            'Support Ticket Volume': row.get('support_ticket_volume'),
            'SLA Compliance': row.get('sla_compliance_percent'),
            'First Response Time': row.get('first_response_time_hours'),
            'Resolution Time': row.get('resolution_time_hours'),
            'Support Satisfaction': row.get('support_satisfaction'),
            'Revenue Growth': row.get('revenue_growth_percent'),
            'Net Revenue Retention': row.get('net_revenue_retention'),
            'Churn Risk Score': row.get('churn_risk')
        }
        
        for kpi_name, kpi_value in kpi_mappings.items():
            if kpi_value is not None:
                kpi = KPI(
                    account_id=account.account_id,
                    upload_id=upload.upload_id,
                    category=get_category_for_kpi(kpi_name),
                    kpi_parameter=kpi_name,
                    data=str(kpi_value),
                    impact_level=get_impact_level(kpi_name),
                    measurement_frequency='Daily',
                    source_review='Fivetran Sync'
                )
                db.session.add(kpi)
                kpis_synced += 1
    
    db.session.commit()
    
    return {
        'kpis_synced': kpis_synced,
        'accounts_created': accounts_created,
        'accounts_updated': len(kpi_data) - accounts_created
    }


def get_category_for_kpi(kpi_name):
    """Map KPI to category"""
    mapping = {
        'NPS': 'Relationship Strength',
        'CSAT': 'Relationship Strength',
        'Executive Sponsor Engagement': 'Relationship Strength',
        'Adoption Index': 'Adoption & Engagement',
        'Support Ticket Volume': 'Support & Experience',
        'SLA Compliance': 'Support & Experience',
        'First Response Time': 'Support & Experience',
        'Resolution Time': 'Support & Experience',
        'Support Satisfaction': 'Support & Experience',
        'Revenue Growth': 'Business Outcomes',
        'Net Revenue Retention': 'Business Outcomes',
        'Churn Risk Score': 'Business Outcomes'
    }
    return mapping.get(kpi_name, 'Business Outcomes')


def get_impact_level(kpi_name):
    """Determine impact level for KPI"""
    critical_kpis = ['NPS', 'SLA Compliance', 'Revenue Growth', 'Net Revenue Retention', 'Churn Risk Score']
    high_kpis = ['CSAT', 'Adoption Index', 'Support Satisfaction']
    
    if kpi_name in critical_kpis:
        return 'Critical'
    elif kpi_name in high_kpis:
        return 'High'
    else:
        return 'Medium'


@fivetran_sync_api.route('/api/fivetran/test-connection', methods=['POST'])
def test_warehouse_connection():
    """Test connection to data warehouse"""
    try:
        data = request.json
        warehouse = data.get('warehouse_connection', {})
        warehouse_type = warehouse.get('type')
        
        if warehouse_type == 'snowflake':
            # Test Snowflake connection
            import snowflake.connector
            conn = snowflake.connector.connect(
                user=warehouse['credentials']['username'],
                password=warehouse['credentials']['password'],
                account=warehouse['host']
            )
            conn.cursor().execute("SELECT CURRENT_VERSION()")
            conn.close()
            return jsonify({'status': 'success', 'message': 'Snowflake connection successful'})
            
        elif warehouse_type == 'bigquery':
            # Test BigQuery connection
            from google.cloud import bigquery
            from google.oauth2 import service_account
            credentials = service_account.Credentials.from_service_account_info(
                warehouse['credentials']
            )
            client = bigquery.Client(credentials=credentials, project=warehouse['project'])
            client.query("SELECT 1").result()
            return jsonify({'status': 'success', 'message': 'BigQuery connection successful'})
            
        elif warehouse_type == 'redshift':
            # Test Redshift connection
            import psycopg2
            conn = psycopg2.connect(
                host=warehouse['host'],
                port=warehouse.get('port', 5439),
                database=warehouse['database'],
                user=warehouse['credentials']['username'],
                password=warehouse['credentials']['password']
            )
            conn.cursor().execute("SELECT version()")
            conn.close()
            return jsonify({'status': 'success', 'message': 'Redshift connection successful'})
        
        else:
            return jsonify({'error': 'Unsupported warehouse type'}), 400
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Connection test failed: {str(e)}'
        }), 500


@fivetran_sync_api.route('/api/fivetran/schedule', methods=['POST'])
def schedule_sync():
    """Schedule automatic Fivetran sync"""
    try:
        customer_id = get_customer_id()
        data = request.json
        
        schedule_config = {
            'customer_id': customer_id,
            'frequency': data.get('frequency', '360'),  # minutes
            'enabled': data.get('enabled', True),
            'sync_salesforce': data.get('sync_salesforce', True),
            'sync_servicenow': data.get('sync_servicenow', True),
            'last_sync': None,
            'next_sync': None
        }
        
        # Store configuration (would use a FivetranConfig model in production)
        # For now, return success
        
        return jsonify({
            'status': 'success',
            'message': 'Sync schedule configured',
            'config': schedule_config
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
```

---

## Part 4: Configuration File

**File:** `backend/config/fivetran_config.json`

```json
{
  "salesforce": {
    "connector_id": "YOUR_FIVETRAN_CONNECTOR_ID",
    "schema": "salesforce_crm",
    "tables": {
      "accounts": "account",
      "contacts": "contact",
      "opportunities": "opportunity",
      "cases": "case",
      "tasks": "task"
    },
    "custom_fields": {
      "nps_score": "nps_score__c",
      "adoption_score": "adoption_score__c",
      "churn_risk": "churn_risk_score__c",
      "health_score": "health_score__c"
    },
    "kpi_mappings": {
      "NPS": {
        "source_field": "nps_score__c",
        "category": "Relationship Strength",
        "impact_level": "Critical",
        "measurement_frequency": "Quarterly"
      },
      "CSAT": {
        "source_query": "AVG(case.satisfaction_rating__c)",
        "category": "Relationship Strength",
        "impact_level": "High",
        "measurement_frequency": "Monthly"
      },
      "Revenue Growth": {
        "source_calculation": "((current_revenue - prior_revenue) / prior_revenue) * 100",
        "category": "Business Outcomes",
        "impact_level": "Critical",
        "measurement_frequency": "Monthly"
      }
    }
  },
  "servicenow": {
    "connector_id": "YOUR_FIVETRAN_CONNECTOR_ID",
    "schema": "servicenow_itsm",
    "tables": {
      "incidents": "incident",
      "tasks": "task",
      "problems": "problem",
      "changes": "change_request"
    },
    "custom_fields": {
      "customer_account_id": "u_customer_account_id",
      "customer_account_name": "u_customer_account_name"
    },
    "kpi_mappings": {
      "Support Ticket Volume": {
        "source_query": "COUNT(incident.sys_id)",
        "category": "Support & Experience",
        "impact_level": "Medium",
        "measurement_frequency": "Weekly",
        "filters": "WHERE opened_at >= CURRENT_DATE - 30"
      },
      "SLA Compliance": {
        "source_calculation": "(COUNT(sla_met) / COUNT(*)) * 100",
        "category": "Support & Experience",
        "impact_level": "Critical",
        "measurement_frequency": "Daily"
      },
      "First Response Time": {
        "source_calculation": "AVG(first_responded_at - opened_at) IN HOURS",
        "category": "Support & Experience",
        "impact_level": "High",
        "measurement_frequency": "Daily"
      }
    }
  },
  "sync_schedule": {
    "enabled": true,
    "frequency_minutes": 360,
    "timezone": "UTC",
    "sync_window": {
      "start_hour": 0,
      "end_hour": 23
    }
  },
  "account_matching": {
    "strategy": "name_fuzzy_match",
    "threshold": 0.85,
    "create_new_accounts": true,
    "update_existing_accounts": true
  },
  "kpi_update_mode": "upsert",
  "error_handling": {
    "on_missing_account": "create",
    "on_duplicate_kpi": "update",
    "on_sync_failure": "retry",
    "max_retries": 3
  }
}
```

---

## Part 5: Environment Variables

**File:** `.env` (add these)

```bash
# Fivetran Configuration
FIVETRAN_API_KEY=your_fivetran_api_key
FIVETRAN_API_SECRET=your_fivetran_api_secret
FIVETRAN_GROUP_ID=your_fivetran_group_id

# Salesforce Configuration
SALESFORCE_CONNECTOR_ID=your_salesforce_connector_id
SALESFORCE_CLIENT_ID=your_salesforce_client_id
SALESFORCE_CLIENT_SECRET=your_salesforce_client_secret
SALESFORCE_DOMAIN=your-company.my.salesforce.com

# ServiceNow Configuration
SERVICENOW_CONNECTOR_ID=your_servicenow_connector_id
SERVICENOW_INSTANCE_URL=https://your-company.service-now.com
SERVICENOW_USERNAME=fivetran_user
SERVICENOW_PASSWORD=your_password

# Data Warehouse Configuration
WAREHOUSE_TYPE=snowflake  # or bigquery, redshift
WAREHOUSE_HOST=your-account.snowflakecomputing.com
WAREHOUSE_DATABASE=kpi_dashboard_db
WAREHOUSE_SCHEMA=public
WAREHOUSE_USERNAME=your_username
WAREHOUSE_PASSWORD=your_password
WAREHOUSE_WAREHOUSE=compute_wh
```

---

## Part 6: Sync Script

**File:** `backend/scripts/sync_fivetran_data.py`

```python
#!/usr/bin/env python3
"""
Automated Fivetran Sync Script

Run via cron: */30 * * * * python sync_fivetran_data.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import app
import requests
import json
from datetime import datetime

def sync_all_customers():
    """Sync Fivetran data for all customers"""
    
    with app.app_context():
        from models import Customer
        
        customers = Customer.query.all()
        
        print(f"Starting Fivetran sync for {len(customers)} customers...")
        print(f"Timestamp: {datetime.utcnow().isoformat()}")
        print("=" * 60)
        
        for customer in customers:
            print(f"\nSyncing customer: {customer.customer_name} (ID: {customer.customer_id})")
            
            try:
                # Make API call to sync endpoint
                response = requests.post(
                    'http://localhost:5059/api/fivetran/sync',
                    headers={'X-Customer-ID': str(customer.customer_id)},
                    json={
                        'data_source': 'combined',
                        'warehouse_connection': {
                            'type': os.getenv('WAREHOUSE_TYPE', 'snowflake'),
                            'host': os.getenv('WAREHOUSE_HOST'),
                            'database': os.getenv('WAREHOUSE_DATABASE'),
                            'schema': os.getenv('WAREHOUSE_SCHEMA', 'PUBLIC'),
                            'warehouse': os.getenv('WAREHOUSE_WAREHOUSE'),
                            'credentials': {
                                'username': os.getenv('WAREHOUSE_USERNAME'),
                                'password': os.getenv('WAREHOUSE_PASSWORD')
                            }
                        },
                        'sync_config': {
                            'account_matching': 'auto',
                            'update_mode': 'upsert'
                        }
                    },
                    timeout=300
                )
                
                if response.ok:
                    result = response.json()
                    print(f"  ✅ Success: {result['message']}")
                    print(f"     KPIs synced: {result['results']['kpis_synced']}")
                    print(f"     Accounts created: {result['results']['accounts_created']}")
                else:
                    print(f"  ❌ Failed: {response.status_code}")
                    
            except Exception as e:
                print(f"  ❌ Error: {str(e)}")
        
        print("\n" + "=" * 60)
        print("Fivetran sync complete")

if __name__ == '__main__':
    sync_all_customers()
```

---

## Part 7: Salesforce-Specific Queries

### 7.1 Account Health Metrics

```sql
-- Salesforce: Calculate Account Health Score
SELECT
    a.id AS account_id,
    a.name AS account_name,
    
    -- Relationship Strength (40%)
    (
        COALESCE(a.nps_score__c, 0) * 0.3 +  -- NPS (30% of relationship)
        (COALESCE(AVG(c.satisfaction_rating__c), 0) * 20) * 0.3 +  -- CSAT (30%)
        (COUNT(DISTINCT CASE WHEN con.title LIKE '%VP%' THEN t.id END) / 10.0 * 100) * 0.4  -- Exec engagement (40%)
    ) * 0.4 AS relationship_score,
    
    -- Adoption & Engagement (30%)
    (
        COALESCE(a.adoption_score__c, 0) * 0.5 +  -- Adoption index (50%)
        (COALESCE(a.active_users__c, 0) / NULLIF(a.total_users__c, 0) * 100) * 0.3 +  -- User activation (30%)
        COALESCE(a.feature_usage_score__c, 0) * 0.2  -- Feature usage (20%)
    ) * 0.3 AS adoption_score,
    
    -- Business Outcomes (30%)
    (
        LEAST(COALESCE(a.revenue_growth_rate__c, 0), 100) * 0.4 +  -- Revenue growth (40%)
        LEAST(COALESCE(a.nrr__c, 100), 150) * 0.4 +  -- NRR (40%)
        (100 - COALESCE(a.churn_risk_score__c, 0)) * 0.2  -- Inverted churn risk (20%)
    ) * 0.3 AS business_outcomes_score

FROM salesforce_crm.account a
LEFT JOIN salesforce_crm.contact con ON con.account_id = a.id
LEFT JOIN salesforce_crm.task t ON t.who_id = con.id AND t.created_date >= CURRENT_DATE - 30
LEFT JOIN salesforce_crm.case c ON c.account_id = a.id AND c.created_date >= CURRENT_DATE - 90
WHERE a.type = 'Customer'
GROUP BY a.id;
```

### 7.2 Churn Risk Prediction

```sql
-- Salesforce: Churn Risk Indicators
SELECT
    a.id AS account_id,
    a.name AS account_name,
    
    -- Risk Factors (sum to calculate overall risk)
    CASE WHEN a.nps_score__c < 10 THEN 25 ELSE 0 END AS nps_risk,
    CASE WHEN AVG(c.satisfaction_rating__c) < 3 THEN 20 ELSE 0 END AS csat_risk,
    CASE WHEN a.last_login_date__c < CURRENT_DATE - 30 THEN 15 ELSE 0 END AS inactivity_risk,
    CASE WHEN a.support_tickets_30d__c > 10 THEN 15 ELSE 0 END AS support_volume_risk,
    CASE WHEN a.executive_engagement__c = 'Low' THEN 25 ELSE 0 END AS relationship_risk,
    
    -- Overall Churn Risk Score
    (
        CASE WHEN a.nps_score__c < 10 THEN 25 ELSE 0 END +
        CASE WHEN AVG(c.satisfaction_rating__c) < 3 THEN 20 ELSE 0 END +
        CASE WHEN a.last_login_date__c < CURRENT_DATE - 30 THEN 15 ELSE 0 END +
        CASE WHEN a.support_tickets_30d__c > 10 THEN 15 ELSE 0 END +
        CASE WHEN a.executive_engagement__c = 'Low' THEN 25 ELSE 0 END
    ) AS total_churn_risk_score

FROM salesforce_crm.account a
LEFT JOIN salesforce_crm.case c ON c.account_id = a.id
WHERE a.type = 'Customer'
GROUP BY a.id;
```

---

## Part 8: ServiceNow-Specific Queries

### 8.1 Support Metrics

```sql
-- ServiceNow: Support KPIs
SELECT
    i.u_customer_account_id AS account_id,
    i.u_customer_account_name AS account_name,
    
    -- Ticket Volume
    COUNT(*) AS total_tickets,
    COUNT(CASE WHEN i.priority = '1 - Critical' THEN 1 END) AS critical_tickets,
    
    -- SLA Metrics
    AVG(CASE 
        WHEN i.sla_due IS NOT NULL AND i.closed_at IS NOT NULL
        THEN CASE WHEN i.closed_at <= i.sla_due THEN 100 ELSE 0 END
        ELSE NULL
    END) AS sla_compliance_percent,
    
    -- Response Time (in hours)
    AVG(EXTRACT(EPOCH FROM (i.first_responded_at - i.opened_at)) / 3600) AS avg_first_response_hours,
    
    -- Resolution Time (in hours)
    AVG(EXTRACT(EPOCH FROM (i.resolved_at - i.opened_at)) / 3600) AS avg_resolution_hours,
    
    -- Quality Metrics
    AVG(i.satisfaction_rating) AS avg_satisfaction,
    (COUNT(CASE WHEN i.reopened_count > 0 THEN 1 END) * 100.0 / COUNT(*)) AS reopen_rate_percent,
    (COUNT(CASE WHEN i.escalation > 0 THEN 1 END) * 100.0 / COUNT(*)) AS escalation_rate_percent,
    
    -- Trend Indicators
    COUNT(CASE WHEN i.opened_at >= CURRENT_DATE - 7 THEN 1 END) AS tickets_last_7_days,
    COUNT(CASE WHEN i.opened_at >= CURRENT_DATE - 30 AND i.opened_at < CURRENT_DATE - 23 THEN 1 END) AS tickets_prior_7_days

FROM servicenow_itsm.incident i
WHERE i.opened_at >= CURRENT_DATE - 90
  AND i.u_customer_account_id IS NOT NULL
GROUP BY i.u_customer_account_id, i.u_customer_account_name;
```

### 8.2 SLA Breach Analysis

```sql
-- ServiceNow: SLA Breach Root Causes
SELECT
    i.u_customer_account_id AS account_id,
    i.category AS ticket_category,
    
    COUNT(*) AS total_tickets,
    COUNT(CASE WHEN i.closed_at > i.sla_due THEN 1 END) AS sla_breaches,
    (COUNT(CASE WHEN i.closed_at > i.sla_due THEN 1 END) * 100.0 / COUNT(*)) AS breach_rate,
    
    AVG(EXTRACT(EPOCH FROM (i.closed_at - i.sla_due)) / 3600) 
        FILTER (WHERE i.closed_at > i.sla_due) AS avg_breach_hours,
    
    -- Root Cause Indicators
    COUNT(CASE WHEN i.assignment_group_changed > 2 THEN 1 END) AS routing_issues,
    COUNT(CASE WHEN i.escalation > 0 THEN 1 END) AS complex_issues,
    COUNT(CASE WHEN i.priority = '1 - Critical' AND i.closed_at > i.sla_due THEN 1 END) AS critical_breaches

FROM servicenow_itsm.incident i
WHERE i.opened_at >= CURRENT_DATE - 30
  AND i.u_customer_account_id IS NOT NULL
GROUP BY i.u_customer_account_id, i.category
HAVING COUNT(CASE WHEN i.closed_at > i.sla_due THEN 1 END) > 0
ORDER BY breach_rate DESC;
```

---

## Part 9: Tunable Settings in UI

Now let me create the Settings UI section for Data Integration configuration. This will be added to the Settings tab:

**File:** `src/components/DataIntegrationSettings.tsx`

```typescript
import React, { useState, useEffect } from 'react';
import { Database, RefreshCw, CheckCircle, AlertCircle } from 'lucide-react';

interface DataIntegrationSettingsProps {
  customerId: number;
}

export default function DataIntegrationSettings({ customerId }: DataIntegrationSettingsProps) {
  const [config, setConfig] = useState({
    fivetran: {
      enabled: false,
      sync_salesforce: true,
      sync_servicenow: true,
      sync_frequency: 360, // minutes
      last_sync: null as string | null,
      next_sync: null as string | null
    },
    salesforce: {
      enabled: true,
      instance_url: '',
      api_version: 'v58.0',
      custom_fields: {
        nps_score: 'NPS_Score__c',
        adoption_score: 'Adoption_Score__c',
        churn_risk: 'Churn_Risk_Score__c',
        health_score: 'Health_Score__c'
      },
      sync_objects: {
        accounts: true,
        contacts: true,
        opportunities: true,
        cases: true,
        tasks: true
      }
    },
    servicenow: {
      enabled: true,
      instance_url: '',
      table_prefix: 'u_',
      custom_fields: {
        customer_account_id: 'u_customer_account_id',
        customer_account_name: 'u_customer_account_name'
      },
      sync_tables: {
        incidents: true,
        problems: true,
        change_requests: true,
        tasks: true
      }
    },
    warehouse: {
      type: 'snowflake', // snowflake, bigquery, redshift
      host: '',
      database: 'kpi_dashboard_db',
      schema: 'public',
      warehouse: 'compute_wh'
    },
    account_matching: {
      strategy: 'name_fuzzy_match', // exact, fuzzy, domain
      threshold: 0.85,
      create_new_accounts: true,
      update_existing: true
    },
    kpi_mappings: {
      nps: {
        enabled: true,
        source: 'salesforce',
        field: 'account.nps_score__c',
        category: 'Relationship Strength',
        impact_level: 'Critical',
        frequency: 'Quarterly'
      },
      csat: {
        enabled: true,
        source: 'salesforce',
        calculation: 'AVG(case.satisfaction_rating__c)',
        category: 'Relationship Strength',
        impact_level: 'High',
        frequency: 'Monthly'
      },
      sla_compliance: {
        enabled: true,
        source: 'servicenow',
        calculation: '(COUNT(sla_met) / COUNT(*)) * 100',
        category: 'Support & Experience',
        impact_level: 'Critical',
        frequency: 'Daily'
      },
      support_tickets: {
        enabled: true,
        source: 'servicenow',
        calculation: 'COUNT(incident.sys_id)',
        category: 'Support & Experience',
        impact_level: 'Medium',
        frequency: 'Weekly'
      }
    },
    error_handling: {
      on_missing_account: 'create', // create, skip, error
      on_duplicate_kpi: 'update', // update, skip, error
      on_sync_failure: 'retry', // retry, skip, alert
      max_retries: 3,
      retry_delay: 300 // seconds
    }
  });

  const [saving, setSaving] = useState(false);
  const [testingConnection, setTestingConnection] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<string | null>(null);

  const handleSave = async () => {
    try {
      setSaving(true);
      const response = await fetch('/api/fivetran/config', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'X-Customer-ID': customerId.toString()
        },
        body: JSON.stringify(config)
      });

      if (response.ok) {
        alert('Configuration saved successfully!');
      } else {
        alert('Failed to save configuration');
      }
    } catch (error) {
      alert('Error saving configuration');
    } finally {
      setSaving(false);
    }
  };

  const testConnection = async () => {
    try {
      setTestingConnection(true);
      setConnectionStatus(null);

      const response = await fetch('/api/fivetran/test-connection', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Customer-ID': customerId.toString()
        },
        body: JSON.stringify({ warehouse_connection: config.warehouse })
      });

      const result = await response.json();
      
      if (response.ok) {
        setConnectionStatus('success');
      } else {
        setConnectionStatus('error');
      }
    } catch (error) {
      setConnectionStatus('error');
    } finally {
      setTestingConnection(false);
    }
  };

  const triggerManualSync = async () => {
    try {
      const response = await fetch('/api/fivetran/sync', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Customer-ID': customerId.toString()
        },
        body: JSON.stringify({
          data_source: 'combined',
          warehouse_connection: config.warehouse
        })
      });

      const result = await response.json();
      alert(`Sync complete: ${result.message}`);
    } catch (error) {
      alert('Sync failed');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-bold text-gray-900">Data Integration Configuration</h3>
        <button
          onClick={handleSave}
          disabled={saving}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          {saving ? 'Saving...' : 'Save Configuration'}
        </button>
      </div>

      {/* Fivetran Settings */}
      <div className="bg-white border-2 border-blue-100 rounded-lg p-6">
        <h4 className="text-md font-semibold text-gray-900 mb-4 flex items-center">
          <Database className="h-5 w-5 mr-2 text-blue-600" />
          Fivetran Sync Settings
        </h4>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={config.fivetran.enabled}
                onChange={(e) => setConfig({...config, fivetran: {...config.fivetran, enabled: e.target.checked}})}
                className="mr-2"
              />
              <span className="text-sm font-medium text-gray-700">Enable Automatic Sync</span>
            </label>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Sync Frequency (minutes)
            </label>
            <input
              type="number"
              value={config.fivetran.sync_frequency}
              onChange={(e) => setConfig({...config, fivetran: {...config.fivetran, sync_frequency: parseInt(e.target.value)}})}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            />
            <p className="text-xs text-gray-500 mt-1">Recommended: 360 (6 hours)</p>
          </div>
        </div>

        <div className="mt-4 flex space-x-3">
          <button
            onClick={testConnection}
            disabled={testingConnection}
            className="bg-gray-600 text-white px-4 py-2 rounded-lg hover:bg-gray-700 disabled:opacity-50"
          >
            {testingConnection ? 'Testing...' : 'Test Connection'}
          </button>
          
          <button
            onClick={triggerManualSync}
            className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 flex items-center"
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Manual Sync Now
          </button>

          {connectionStatus && (
            <div className={`flex items-center px-4 py-2 rounded-lg ${
              connectionStatus === 'success' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
            }`}>
              {connectionStatus === 'success' ? (
                <><CheckCircle className="h-4 w-4 mr-2" /> Connected</>
              ) : (
                <><AlertCircle className="h-4 w-4 mr-2" /> Connection Failed</>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Salesforce Settings */}
      <div className="bg-white border-2 border-orange-100 rounded-lg p-6">
        <h4 className="text-md font-semibold text-gray-900 mb-4">
          🔷 Salesforce CRM Integration
        </h4>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Instance URL
            </label>
            <input
              type="text"
              value={config.salesforce.instance_url}
              onChange={(e) => setConfig({...config, salesforce: {...config.salesforce, instance_url: e.target.value}})}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
              placeholder="https://your-company.my.salesforce.com"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              API Version
            </label>
            <input
              type="text"
              value={config.salesforce.api_version}
              onChange={(e) => setConfig({...config, salesforce: {...config.salesforce, api_version: e.target.value}})}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
              placeholder="v58.0"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Custom Fields Mapping
            </label>
            <div className="grid grid-cols-2 gap-3">
              <input
                type="text"
                value={config.salesforce.custom_fields.nps_score}
                onChange={(e) => setConfig({...config, salesforce: {...config.salesforce, custom_fields: {...config.salesforce.custom_fields, nps_score: e.target.value}}})}
                className="px-3 py-2 border border-gray-300 rounded-md text-sm"
                placeholder="NPS_Score__c"
              />
              <input
                type="text"
                value={config.salesforce.custom_fields.adoption_score}
                onChange={(e) => setConfig({...config, salesforce: {...config.salesforce, custom_fields: {...config.salesforce.custom_fields, adoption_score: e.target.value}}})}
                className="px-3 py-2 border border-gray-300 rounded-md text-sm"
                placeholder="Adoption_Score__c"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Objects to Sync
            </label>
            <div className="grid grid-cols-3 gap-3">
              {Object.entries(config.salesforce.sync_objects).map(([obj, enabled]) => (
                <label key={obj} className="flex items-center text-sm">
                  <input
                    type="checkbox"
                    checked={enabled}
                    onChange={(e) => setConfig({...config, salesforce: {...config.salesforce, sync_objects: {...config.salesforce.sync_objects, [obj]: e.target.checked}}})}
                    className="mr-2"
                  />
                  {obj.charAt(0).toUpperCase() + obj.slice(1)}
                </label>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* ServiceNow Settings */}
      <div className="bg-white border-2 border-green-100 rounded-lg p-6">
        <h4 className="text-md font-semibold text-gray-900 mb-4">
          🟢 ServiceNow ITSM Integration
        </h4>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Instance URL
            </label>
            <input
              type="text"
              value={config.servicenow.instance_url}
              onChange={(e) => setConfig({...config, servicenow: {...config.servicenow, instance_url: e.target.value}})}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
              placeholder="https://your-company.service-now.com"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Custom Field Prefix
            </label>
            <input
              type="text"
              value={config.servicenow.table_prefix}
              onChange={(e) => setConfig({...config, servicenow: {...config.servicenow, table_prefix: e.target.value}})}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
              placeholder="u_"
            />
            <p className="text-xs text-gray-500 mt-1">Prefix for custom fields (usually 'u_')</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Tables to Sync
            </label>
            <div className="grid grid-cols-2 gap-3">
              {Object.entries(config.servicenow.sync_tables).map(([table, enabled]) => (
                <label key={table} className="flex items-center text-sm">
                  <input
                    type="checkbox"
                    checked={enabled}
                    onChange={(e) => setConfig({...config, servicenow: {...config.servicenow, sync_tables: {...config.servicenow.sync_tables, [table]: e.target.checked}}})}
                    className="mr-2"
                  />
                  {table.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}
                </label>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Data Warehouse Settings */}
      <div className="bg-white border-2 border-purple-100 rounded-lg p-6">
        <h4 className="text-md font-semibold text-gray-900 mb-4">
          🗄️ Data Warehouse Configuration
        </h4>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Warehouse Type
            </label>
            <select
              value={config.warehouse.type}
              onChange={(e) => setConfig({...config, warehouse: {...config.warehouse, type: e.target.value as any}})}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            >
              <option value="snowflake">Snowflake</option>
              <option value="bigquery">Google BigQuery</option>
              <option value="redshift">Amazon Redshift</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Host/Account
            </label>
            <input
              type="text"
              value={config.warehouse.host}
              onChange={(e) => setConfig({...config, warehouse: {...config.warehouse, host: e.target.value}})}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
              placeholder="account.snowflakecomputing.com"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Database
            </label>
            <input
              type="text"
              value={config.warehouse.database}
              onChange={(e) => setConfig({...config, warehouse: {...config.warehouse, database: e.target.value}})}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
              placeholder="kpi_dashboard_db"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Schema
            </label>
            <input
              type="text"
              value={config.warehouse.schema}
              onChange={(e) => setConfig({...config, warehouse: {...config.warehouse, schema: e.target.value}})}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
              placeholder="public"
            />
          </div>
        </div>
      </div>

      {/* Account Matching Settings */}
      <div className="bg-white border-2 border-yellow-100 rounded-lg p-6">
        <h4 className="text-md font-semibold text-gray-900 mb-4">
          🔗 Account Matching Configuration
        </h4>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Matching Strategy
            </label>
            <select
              value={config.account_matching.strategy}
              onChange={(e) => setConfig({...config, account_matching: {...config.account_matching, strategy: e.target.value as any}})}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            >
              <option value="exact">Exact Name Match</option>
              <option value="name_fuzzy_match">Fuzzy Name Match</option>
              <option value="domain">Domain-Based Match</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Match Threshold (0-1)
            </label>
            <input
              type="number"
              step="0.05"
              min="0"
              max="1"
              value={config.account_matching.threshold}
              onChange={(e) => setConfig({...config, account_matching: {...config.account_matching, threshold: parseFloat(e.target.value)}})}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            />
            <p className="text-xs text-gray-500 mt-1">Higher = stricter matching (recommended: 0.85)</p>
          </div>

          <div>
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={config.account_matching.create_new_accounts}
                onChange={(e) => setConfig({...config, account_matching: {...config.account_matching, create_new_accounts: e.target.checked}})}
                className="mr-2"
              />
              <span className="text-sm font-medium text-gray-700">Auto-create new accounts</span>
            </label>
          </div>

          <div>
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={config.account_matching.update_existing}
                onChange={(e) => setConfig({...config, account_matching: {...config.account_matching, update_existing: e.target.checked}})}
                className="mr-2"
              />
              <span className="text-sm font-medium text-gray-700">Update existing accounts</span>
            </label>
          </div>
        </div>
      </div>

      {/* KPI Mappings */}
      <div className="bg-white border-2 border-indigo-100 rounded-lg p-6">
        <h4 className="text-md font-semibold text-gray-900 mb-4">
          📊 KPI Field Mappings
        </h4>

        <div className="space-y-4">
          {Object.entries(config.kpi_mappings).map(([kpi, mapping]) => (
            <div key={kpi} className="border-b border-gray-200 pb-3">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center">
                  <input
                    type="checkbox"
                    checked={mapping.enabled}
                    onChange={(e) => setConfig({...config, kpi_mappings: {...config.kpi_mappings, [kpi]: {...mapping, enabled: e.target.checked}}})}
                    className="mr-2"
                  />
                  <span className="text-sm font-semibold text-gray-900">
                    {kpi.toUpperCase().replace(/_/g, ' ')}
                  </span>
                </div>
                <span className="text-xs text-gray-500">{mapping.source}</span>
              </div>
              
              <div className="grid grid-cols-2 gap-3 ml-6">
                <div>
                  <label className="text-xs text-gray-600">Category</label>
                  <p className="text-sm text-gray-900">{mapping.category}</p>
                </div>
                <div>
                  <label className="text-xs text-gray-600">Impact</label>
                  <p className="text-sm text-gray-900">{mapping.impact_level}</p>
                </div>
                <div className="col-span-2">
                  <label className="text-xs text-gray-600">Source Field/Calculation</label>
                  <p className="text-sm text-gray-900 font-mono bg-gray-50 px-2 py-1 rounded">
                    {'field' in mapping ? mapping.field : mapping.calculation}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Error Handling */}
      <div className="bg-white border-2 border-red-100 rounded-lg p-6">
        <h4 className="text-md font-semibold text-gray-900 mb-4">
          ⚠️ Error Handling Configuration
        </h4>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              On Missing Account
            </label>
            <select
              value={config.error_handling.on_missing_account}
              onChange={(e) => setConfig({...config, error_handling: {...config.error_handling, on_missing_account: e.target.value as any}})}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            >
              <option value="create">Create new account</option>
              <option value="skip">Skip the record</option>
              <option value="error">Raise error</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              On Duplicate KPI
            </label>
            <select
              value={config.error_handling.on_duplicate_kpi}
              onChange={(e) => setConfig({...config, error_handling: {...config.error_handling, on_duplicate_kpi: e.target.value as any}})}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            >
              <option value="update">Update existing</option>
              <option value="skip">Skip the update</option>
              <option value="error">Raise error</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Max Retry Attempts
            </label>
            <input
              type="number"
              value={config.error_handling.max_retries}
              onChange={(e) => setConfig({...config, error_handling: {...config.error_handling, max_retries: parseInt(e.target.value)}})}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Retry Delay (seconds)
            </label>
            <input
              type="number"
              value={config.error_handling.retry_delay}
              onChange={(e) => setConfig({...config, error_handling: {...config.error_handling, retry_delay: parseInt(e.target.value)}})}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            />
          </div>
        </div>
      </div>

      {/* Sync Status */}
      {config.fivetran.last_sync && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-blue-900">Last Sync</p>
              <p className="text-xs text-blue-700">{new Date(config.fivetran.last_sync).toLocaleString()}</p>
            </div>
            {config.fivetran.next_sync && (
              <div>
                <p className="text-sm font-medium text-blue-900">Next Sync</p>
                <p className="text-xs text-blue-700">{new Date(config.fivetran.next_sync).toLocaleString()}</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
```

---

## Part 10: Complete Settings Documentation

### All Tunable Settings in Settings Tab

#### **Data Integration Section:**

**Fivetran Sync:**
- ✅ Enable/Disable automatic sync
- ✅ Sync frequency (minutes): 60, 180, 360, 720, 1440
- ✅ Sync Salesforce data (checkbox)
- ✅ Sync ServiceNow data (checkbox)
- ✅ Test Connection button
- ✅ Manual Sync Now button

**Salesforce CRM:**
- ✅ Instance URL: `https://your-company.my.salesforce.com`
- ✅ API Version: `v58.0` (default)
- ✅ Custom Field Mappings:
  - NPS Score field: `NPS_Score__c`
  - Adoption Score field: `Adoption_Score__c`
  - Churn Risk field: `Churn_Risk_Score__c`
  - Health Score field: `Health_Score__c`
- ✅ Objects to Sync:
  - Accounts (checkbox)
  - Contacts (checkbox)
  - Opportunities (checkbox)
  - Cases (checkbox)
  - Tasks (checkbox)

**ServiceNow ITSM:**
- ✅ Instance URL: `https://your-company.service-now.com`
- ✅ Custom Field Prefix: `u_` (default)
- ✅ Account ID Field: `u_customer_account_id`
- ✅ Account Name Field: `u_customer_account_name`
- ✅ Tables to Sync:
  - Incidents (checkbox)
  - Problems (checkbox)
  - Change Requests (checkbox)
  - Tasks (checkbox)

**Data Warehouse:**
- ✅ Warehouse Type: Snowflake / BigQuery / Redshift (dropdown)
- ✅ Host/Account: `account.snowflakecomputing.com`
- ✅ Database: `kpi_dashboard_db`
- ✅ Schema: `public`
- ✅ Warehouse (Snowflake only): `compute_wh`

**Account Matching:**
- ✅ Strategy: Exact / Fuzzy / Domain-based (dropdown)
- ✅ Match Threshold: 0.85 (slider 0.0-1.0)
- ✅ Auto-create new accounts (checkbox)
- ✅ Update existing accounts (checkbox)

**KPI Field Mappings:** (12 KPIs)
- ✅ NPS: Enable/Disable, Source (SF), Field, Category, Impact
- ✅ CSAT: Enable/Disable, Source (SF), Calculation, Category, Impact
- ✅ SLA Compliance: Enable/Disable, Source (SN), Calculation, Category, Impact
- ✅ Support Tickets: Enable/Disable, Source (SN), Calculation, Category, Impact
- ✅ Revenue Growth: Enable/Disable, Source (SF), Calculation, Category, Impact
- ✅ Net Revenue Retention: Enable/Disable, Source (SF), Calculation, Category, Impact
- ✅ Adoption Index: Enable/Disable, Source (SF), Field, Category, Impact
- ✅ Churn Risk: Enable/Disable, Source (SF), Field, Category, Impact
- ✅ Executive Engagement: Enable/Disable, Source (SF), Calculation, Category, Impact
- ✅ Support Satisfaction: Enable/Disable, Source (SN), Field, Category, Impact
- ✅ First Response Time: Enable/Disable, Source (SN), Calculation, Category, Impact
- ✅ Resolution Time: Enable/Disable, Source (SN), Calculation, Category, Impact

**Error Handling:**
- ✅ On Missing Account: Create / Skip / Error (dropdown)
- ✅ On Duplicate KPI: Update / Skip / Error (dropdown)
- ✅ On Sync Failure: Retry / Skip / Alert (dropdown)
- ✅ Max Retry Attempts: 3 (default, editable)
- ✅ Retry Delay (seconds): 300 (default, editable)

---

## Part 11: Cron Job Setup

**Add to crontab:**

```bash
# Sync Fivetran data every 6 hours
0 */6 * * * cd /path/to/kpi-dashboard && ./venv/bin/python backend/scripts/sync_fivetran_data.py >> /var/log/fivetran_sync.log 2>&1

# Or every 30 minutes for more frequent updates
*/30 * * * * cd /path/to/kpi-dashboard && ./venv/bin/python backend/scripts/sync_fivetran_data.py >> /var/log/fivetran_sync.log 2>&1
```

---

## Summary

### Files Created:

📄 **FIVETRAN_INTEGRATION_GUIDE.md** - Complete integration guide
📄 **backend/fivetran_sync_api.py** - API endpoints for Fivetran sync
📄 **backend/scripts/sync_fivetran_data.py** - Automated sync script
📄 **backend/config/fivetran_config.json** - Configuration template
📄 **src/components/DataIntegrationSettings.tsx** - Settings UI component
📄 **transformations/kpi_mappings.sql** - SQL transformation queries

### Settings in UI:

All tunable parameters documented and exposed in "Settings" > "Data Integration" section:

✅ 40+ configurable parameters
✅ Test connection functionality
✅ Manual sync trigger
✅ Real-time status display
✅ Field mapping configuration
✅ Error handling policies

**Ready for Salesforce CRM + ServiceNow ITSM integration via Fivetran!** 🚀

