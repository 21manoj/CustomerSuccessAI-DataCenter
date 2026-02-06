#!/usr/bin/env python3
"""Load DC2_S mock data directly into PostgreSQL"""

import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

print("=" * 60)
print("DC2_S DATA LOADER")
print("=" * 60)

# Connect to PostgreSQL
engine = create_engine(os.getenv("DATABASE_URL"))
conn = engine.connect()

# Mock accounts data
accounts_data = [
    {
        "account_id": 1001,
        "account_name": "CloudScale AI Labs",
        "arr": 2400000,
        "industry": "AI Research",
        "region": "US-West",
        "external_account_id": "CSAI-2024-001",
        "metadata": {
            "gpu_count": 256,
            "gpu_model": "H100",
            "deployment_date": "2024-01-15",
            "lifecycle_stage": "Growth",
            "health_score": 74,
            "csm": "Jennifer Martinez",
            "days_to_renewal": 180
        }
    },
    {
        "account_id": 1002,
        "account_name": "FinServe Corp",
        "arr": 1800000,
        "industry": "Financial Services",
        "region": "US-East",
        "external_account_id": "FSC-2024-002",
        "metadata": {
            "gpu_count": 192,
            "gpu_model": "H100",
            "deployment_date": "2024-02-20",
            "lifecycle_stage": "Maturity",
            "health_score": 92,
            "csm": "Michael Chen",
            "days_to_renewal": 245
        }
    },
    {
        "account_id": 1003,
        "account_name": "Quantum Research Institute",
        "arr": 3200000,
        "industry": "Scientific Research",
        "region": "EU-West",
        "external_account_id": "QRI-2024-003",
        "metadata": {
            "gpu_count": 512,
            "gpu_model": "H100",
            "deployment_date": "2023-11-10",
            "lifecycle_stage": "Expansion",
            "health_score": 88,
            "csm": "Sarah Williams",
            "days_to_renewal": 320
        }
    },
    {
        "account_id": 1007,
        "account_name": "Legacy Manufacturing",
        "arr": 2100000,
        "industry": "Manufacturing",
        "region": "US-Central",
        "external_account_id": "LM-2024-007",
        "metadata": {
            "gpu_count": 128,
            "gpu_model": "H100",
            "deployment_date": "2024-01-05",
            "lifecycle_stage": "Growth",
            "health_score": 58,
            "csm": "Jennifer Martinez",
            "days_to_renewal": 87
        }
    }
]

print("\n📊 Loading accounts data...")

for account in accounts_data:
    params = {
        'id': account['account_id'],
        'customer_id': 1,
        'name': account['account_name'],
        'revenue': account['arr'],
        'industry': account['industry'],
        'region': account['region'],
        'status': 'active',
        'external_id': account['external_account_id'],
        'metadata': json.dumps(account['metadata'])
    }
    
    conn.execute(text("""
        INSERT INTO accounts (
          account_id, customer_id, account_name, revenue,
            industry, region, account_status, external_account_id,
            profile_metadata
        ) VALUES (
            :id, :customer_id, :name, :revenue,
            :industry, :region, :status, :external_id,
            :metadata::jsonb
        )
        ON CONFLICT (account_id) DO UPDATE SET
            account_name = EXCLUDED.account_name,
            revenue = EXCLUDED.revenue,
            profile_metadata = EXCLUDED.profile_metadata
    """), params)

conn.commit()
print(f"   ✅oaded {len(accounts_data)} accounts")

print("\n📊 Loading KPI data...")

kpi_count = 0
base_date = datetime(2024, 1, 1)

for account in accounts_data:
    for month in range(12):
        month_date = base_date + timedelta(days=30 * month)
        
        kpis = [
            {
                'account_id': account['account_id'],
                'kpi_code': 'P3-KPI1',
                'value': 78.0 - (mth * 2.0),
                'target': 65.0,
                'month': month_date.strftime('%Y-%m')
            },
            {
                'account_id': account['account_id'],
                'kpi_code': 'P2-KPI1',
                'value': 1.8 + (month * 0.15),
                'target': 2.6,
                'month': month_date.strftime('%Y-%m')
            }
        ]
        
        for kpi in kpis:
            conn.execute(text("""
                INSERT INTO kpi_data_monthly (
                    account_id, kpi_code, value, target, month
                ) VALUES (
                    :account_id, :kpi_code, :value, :target, :month
                )
                ON CONFLICT (account_id, kpi_code, month) DO UPDATE SET
                    value = EXCLUDED.value
            """), kpi)
            kpi_count += 1

conn.commit()
print(f"   ✅ Loaded {kpi_count} KPI records")

print("\n📊 Loading qualitative signals...")

signals = [
    {
        'account_id': 1007,
        'date': '2024-11-15',
        'signal_type': 'email',
        'from_contact': 'Sarah Chen (CFO)',
        'to_contact': 'Jennifer Martinez (CSM)',
        'subject': 'Q4 Budget Review - Infrastructure Spend',
        'summary': 'CFO requesting budget cuts discussion. Board pushing 15% IT reduction.',
        'iment': 'negative',
        'priority': 'high',
        'keywords': json.dumps(['budget cuts', 'reduce spend', 'board pressure'])
    },
    {
        'account_id': 1002,
        'date': '2024-12-01',
        'signal_type': 'meeting',
        'from_contact': 'David Park (CTO)',
        'to_contact': 'Michael Chen (CSM)',
        'subject': 'Capacity Planning Discussion',
        'summary': 'CTO mentioned GPU utilization at 94%, workload growing 15%/month.',
        'sentiment': 'positive',
        'priority': 'high',
        'keywords': json.dumps(['expansion', 'capacity', 'growth'])
    }
]

for signal in signals:
    conn.execute(text("""
        INSERT INTO qualitative_signals (
            account_id, date, signal_type, from_contact, to_contact,
            subject, summary, sentiment, priority, keywords
        ) VALUES (
            :account_id, :date, :signal_type, :from_contact, :to_contact,
            :subject, :summary, :sentiment, :priority, :keywords::jsonb
        )
    """), signal)

conn.commit()
print(f"   ✅ Loaded {len(signals)} qualitative signals")

print("\n" + "=" * 60)
print("✅ DATA LOAD COMPLETE!")
print("=" * 60)
print(f"\nLoaded:")
print(f"  • {len(accounts_data)} DC2_S accounts")
print(f"  • {kpi_count} KPI data points")
print(f"  • {len(signals)} qualitative signals")

conn.close()
