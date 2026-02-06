#!/usr/bin/env python3
import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

print("=" * 70)
print("DC2_S DATA LOADER - VERIFIED")
print("=" * 70)

engine = create_engine(os.getenv("DATABASE_URL"))

accounts_data = [
    {"account_id": 1001, "account_name": "CloudScale AI Labs", "arr": 2400000, "industry": "AI Research", "region": "US-West", "external_account_id": "CSAI-2024-001", "metadata": {"gpu_count": 256, "gpu_model": "H100", "deployment_date": "2024-01-15", "lifecycle_stage": "Growth", "health_score": 74, "csm": "Jennifer Martinez", "days_to_renewal": 180}},
    {"account_id": 1002, "account_name": "FinServe Corp", "arr": 1800000, "industry": "Financial Services", "region": "US-East", "external_account_id": "FSC-2024-002", "metadata": {"gpu_count": 192, "gpu_model": "H100", "deployment_date": "2024-02-20", "lifecycle_stage": "Maturity", "health_score": 92, "csm": "Michael Chen", "days_to_renewal": 245}},
    {"account_id": 1003, "account_name": "Quantum Research Institute", "arr": 3200000, "industry": "Scientific Research", "region": "EU-West", "external_account_id": "QRI-2024-003", "metadata": {"gpu_count": 512, "gpu_model": "H100", "deployment_date": "2023-11-10", "lifecycle_stage": "Expansion", "health_score": 88, "csm": "Sarah Williams", "days_to_renewal": 320}},
    {"account_id": 1007, "account_name": "Legacy Manufacturing", "arr": 2100000, "industry": "Manufacturing", "region": "US-Central", "external_account_id": "LM-2024-007", "metadata": {"gpu_count": 128, "gpu_model": "H100", "deployment_date": "2024-01-05", "lifecycle_stage": "Growth", "health_score": 58, "csm": "Jennifer Martinez", "days_to_renewal": 87}}
]

print("\n1. Loading accounts...")

with engine.begin() as conn:
    conn.execute(text("DELETE FROM qualitative_signals WHERE account_id IN (1001, 1002, 1003, 1007)"))
    conn.execute(text("DELETE FROM kpi_data_monthly WHERE account_id IN (1001, 1002, 1003, 1007)"))
    conn.execute(text("DELETE FROM accounts WHERE account_id IN (1001, 1002, 1003, 1007)"))
    
    for acc in accounts_data:
        conn.execute(text("""
            INSERT INTO accounts (account_id, customer_id, account_name, revenue, industry, region, account_status, external_account_id, profile_metadata)
            VALUES (:id, :cust, :name, :rev, :ind, :reg, :stat, :ext, CAST(:meta AS jsonb))
        """), {
            "id": acc["account_id"],
            "cust": 1,
            "name": acc["account_name"],
            "rev": acc["arr"],
            "ind": acc["industry"],
            "reg": acc["region"],
            "stat": "active",
            "ext": acc["external_account_id"],
            "meta": json.dumps(acc["metadata"])
        })
    
    result = conn.execute(text("SELECT COUNT(*) FROM accounts WHERE account_id IN (1001, 1002, 1003, 1007)")).fetchone()
    print("   Loaded " + str(result[0]) + " accounts")
    if result[0] != 4:
        print("   ERROR: Expected 4 accounts!")
        exit(1)

print("\n2. Loading KPI data...")

kpi_count = 0
base_date = datetime(2024, 1, 1)

with engine.begin() as conn:
    for acc in accounts_data:
        for m in range(12):
            md = base_date + timedelta(days=30*m)
            
            if acc["account_id"] == 1007:
                gpu_util = 78.0 - (m * 2.0)
            else:
                gpu_util = 85.0 - (m * 0.5)
            
            conn.execute(text("""
                INSERT INTO kpi_data_monthly (account_id, kpi_code, value, target, month)
                VALUES (:aid, :code, :val, :tgt, :mo)
            """), {
                "aid": acc["account_id"],
                "code": "P3-KPI1",
                "val": gpu_util,
                "tgt": 65.0,
                "mo": md.strftime("%Y-%m")
            })
            kpi_count += 1
            
            if acc["account_id"] == 1007:
                rma_rate = 1.8 + (m * 0.15)
            else:
                rma_rate = 1.5 + (m * 0.05)
            
            conn.execute(text("""
                INSERT INTO kpi_data_monthly (account_id, kpi_code, value, target, month)
                VALUES (:aid, :code, :val, :tgt, :mo)
            """), {
                "aid": acc["account_id"],
                "code": "P2-KPI1",
                "val": rma_rate,
                "tgt": 2.6,
                "mo": md.strftime("%Y-%m")
            })
            kpi_count += 1

print("   Loaded " + str(kpi_count) + " KPI records")

print("\n3. Loading qualitative signals...")

signals = [
    {"account_id": 1007, "date": "2024-11-15", "signal_type": "email", "from_contact": "Sarah Chen (CFO)", "to_contact": "Jennifer Martinez (CSM)", "subject": "Q4 Budget Review", "summary": "CFO requesting budget cuts. Board pushing 15% IT reduction.", "sentiment": "negative", "priority": "high", "keywords": json.dumps(["budget cuts", "reduce spend"])},
    {"account_id": 1002, "date": "2024-12-01", "signal_type": "meeting", "from_contact": "David Park (CTO)", "to_contact": "Michael Chen (CSM)", "subject": "Capacity Planning", "summary": "GPU at 94%, workload growing 15%/month. Need more capacity.", "sentiment": "positive", "priority": "high", "keywords": json.dumps(["expansion", "capacity"])}
]

with engine.begin() as conn:
    for sig in signals:
        conn.execute(text("""
            INSERT INTO qualitative_signals (account_id, date, signal_type, from_contact, to_contact, subject, summary, sentiment, priority, keywords)
            VALUES (:aid, :dt, :typ, :fr, :to, :subj, :summ, :sent, :pri, CAST(:kw AS jsonb))
        """), {
            "aid": sig["account_id"],
            "dt": sig["date"],
            "typ": sig["signal_type"],
            "fr": sig["from_contact"],
            "to": sig["to_contact"],
            "subj": sig["subject"],
            "summ": sig["summary"],
            "sent": sig["sentiment"],
            "pri": sig["priority"],
            "kw": sig["keywords"]
        })

print("   Loaded " + str(len(signals)) + " signals")

print("\n" + "=" * 70)
print("VERIFICATION:")
print("=" * 70)

with engine.connect() as conn:
    accounts = conn.execute(text("SELECT account_id, account_name FROM accounts WHERE account_id IN (1001, 1002, 1003, 1007) ORDER BY account_id")).fetchall()
    print("\nAccounts loaded:")
    for acc in accounts:
        print("  ID " + str(acc.account_id) + ": " + acc.account_name)
    
    kpis = conn.execute(text("SELECT account_id, COUNT(*) as cnt FROM kpi_data_monthly WHERE account_id IN (1001, 1002, 1003, 1007) GROUP BY account_id ORDER BY account_id")).fetchall()
    print("\nKPI records per account:")
    for k in kpis:
        print("  Account " + str(k.account_id) + ": " + str(k.cnt) + " KPIs")
    
    sigs = conn.execute(text("SELECT account_id, COUNT(*) as cnt FROM qualitative_signals WHERE account_id IN (1001, 1002, 1003, 1007) GROUP BY account_id ORDER BY account_id")).fetchall()
    print("\nSignals per account:")
    for s in sigs:
        print("  Account " + str(s.account_id) + ": " + str(s.cnt) + " signals")

print("\n" + "=" * 70)
print("DATA LOAD COMPLETE AND VERIFIED!")
print("=" * 70)
