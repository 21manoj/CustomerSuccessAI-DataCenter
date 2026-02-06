#!/usr/bin/env python3
"""Load DC2_S mock data"""

import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

print("=" * 60)
print("DC2_S DATA LOADER")
print("=" * 60)

engine = create_engine(os.getenv("DATABASE_URL"))

accounts_data = [
    {"account_id": 1001, "account_name": "CloudScale AI Labs", "arr": 2400000, "industry": "AI Research", "region": "US-West", "external_account_id": "CSAI-2024-001", "metadata": {"gpu_count": 256, "gpu_model": "H100", "deployment_date": "2024-01-15", "lifecycle_stage": "Growth", "health_score": 74, "csm": "Jennifer Martinez", "days_to_renewal": 180}},
    {"account_id": 1002, "account_name": "FinServe Corp", "arr": 1800000, "industry": "Financial Services", "region": "US-East", "external_account_id": "FSC-2024-002", "metadata": {"gpu_count": 192, "gpu_model": "H100", "deployment_date": "2024-02-20", "lifecycle_stage": "Maturity", "health_score": 92, "csm": "Michael Chen", "days_to_renewal": 245}},
    {"account_id": 1003, "account_name": "Quantum Research", "arr": 3200000, "industry": "Scientific Research", "region": "EU-West", "external_account_id": "QRI-2024-003", "metadata": {"gpu_count": 512, "gpu_model": "H100", "deployment_date": "2023-11-10", "lifecycle_stage": "Expansion", "health_score": 88, "csm": "Sarah Williams", "days_to_renewal": 320}},
    {"account_id": 1007, "account_name": "Legacy Manufacturing", "arr": 2100000, "industry": "Manufacturing", "region": "US-Central", "external_account_id": "LM-2024-007", "metadata": {"gpu_count": 128, "gpu_model": "H100", "deployment_date": "2024-01-05", "lifecycle_stage": "Growth", "health_score": 58, "csm": "Jennifer Martinez", "days_to_renewal": 87}}
]

print("\n📊 Loading accounts...")
with engine.begin() as conn:
    for acc in accounts_data:
        conn.execute(text("""
            INSERT INTO accounts (account_id, customer_id, account_name, revenue, industry, region, account_status, external_account_id, profile_metadata)
            VALUES (:id, :cust, :name, :rev, :ind, :reg, :stat, :ext, CAST(:meta AS jsonb))
            ON CONFLICT (account_id) DO UPDATE SET account_name = EXCLUDED.account_name, revenue = EXCLUDED.revenue, profile_metadata = EXCLUDED.profile_metadata
        """), {"id": acc["account_id"], "cust": 1, "name": acc["account_name"], "rev": acc["arr"], "ind": acc["industry"], "reg": acc["regn"], "stat": "active", "ext": acc["external_account_id"], "meta": json.dumps(acc["metadata"])})

print(f"   ✅ Loaded {len(accounts_data)} accounts")

print("\n📊 Loading KPIs...")
kpi_count = 0
base_date = datetime(2024, 1, 1)
with engine.begin() as conn:
    for acc in accounts_data:
        for m in range(12):
            md = base_date + timedelta(days=30*m)
            for kpi in [{"account_id": acc["account_id"], "kpi_code": "P3-KPI1", "value": 78.0-(m*2.0), "target": 65.0, "month": md.strftime("%Y-%m")}, {"account_id": acc["account_id"], "kpi_code": "P2-KPI1", "value": 1.8+(m*0.15), "target": 2.6, "month": md.strftime("%Y-%m")}]:
                conn.execute(text("INSERT INTO kpi_data_monthly (account_kpi_code, value, target, month) VALUES (:aid, :code, :val, :tgt, :mo) ON CONFLICT (account_id, kpi_code, month) DO UPDATE SET value = EXCLUDED.value"), {"aid": kpi["account_id"], "code": kpi["kpi_code"], "val": kpi["value"], "tgt": kpi["target"], "mo": kpi["month"]})
                kpi_count += 1

print(f"   ✅ Loaded {kpi_count} KPI records")

print("\n📊 Loading signals...")
signals = [
    {"account_id": 1007, "date": "2024-11-15", "signal_type": "email", "from_contact": "Sarah Chen CFO", "to_contact": "Jennifer Martinez CSM", "subject": "Q4 Budget Review", "summary": "CFO requesting budget cuts", "sentiment": "negativepriority": "high", "keywords": json.dumps(["budget cuts"])},
    {"account_id": 1002, "date": "2024-12-01", "signal_type": "meeting", "from_contact": "David Park CTO", "to_contact": "Michael Chen CSM", "subject": "Capacity Planning", "summary": "GPU at 94 percent growing", "sentiment": "positive", "priority": "high", "keywords": json.dumps(["expansion"])}
]

with engine.begin() as conn:
    for sig in signals:
        conn.execute(text("INSERT INTO qualitative_signals (account_id, date, signal_type, from_contact, to_contact, subject, summary, sentiment, priority, keywords) VALUES (:aid, :dt, :typ, :fr, :to, :subj, :summ, :sent, :pri, CAST(:kw AS jsonb))"), {"aid": sig["account_id"], "dt": sig["date"], "typ": sig["signal_type"], "fr": sig["from_contact"], "to": sig["to_contact"], "subj": sig["subject"], "summ": sig["summary"], "sent": sig["sentiment"], "pri": sig["priority"], "kw": sig["keywords"]})

print(f"   ✅ Loaded {len(signals)} signals")
print("\n" + "="*60)
print("✅ COMPLETE!")
print("="*60)
