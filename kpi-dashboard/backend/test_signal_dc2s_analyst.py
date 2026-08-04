#!/usr/bin/env python3
"""Signal Analyst Test - Using Correct Schema"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import anthropic

load_dotenv()

print("=" * 70)
print("SIGNAL ANALYST TEST: Account 1007 (Legacy Manufacturing)")
print("=" * 70)

engine = create_engine(os.getenv("DATABASE_URL"))
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

ACCOUNT_ID = 1007

print("\nFetching account data...")

with engine.connect() as conn:
    # Get account info
    account = conn.execute(text("""
        SELECT account_id, account_name, revenue, industry, region
        FROM accounts
        WHERE account_id = :id
    """), {"id": ACCOUNT_ID}).fetchone()
    
    if not account:
        print("Account not found!")
        exit(1)
    
    print("\nAccount: " + account.account_name)
    print("ARR: $" + str(account.revenue))
    print("Industry: " + account.industry)
    
    # Get KPI trends (last 12 months)
    kpis = conn.execute(text("""
        SELECT kpi_code, value, target, measured_at
        FROM dc2s_kpis
        WHERE account_id = :id
        ORDER BY measured_at DESC
        LIMIT 24
    """), {"id": ACCOUNT_ID}).fetchall()
    
    print("KPI data points: " + str(len(kpis)))
    
    # Get qualitative signals
    signals = conn.execute(text("""
        SELECT date, signal_type, from_contact, subject, summary, sentiment, priority
        FROM qualitative_signals
        WHERE account_id = :id
        ORDER BY date DESC
    """), {"id": ACCOUNT_ID}).fetchall()
    
    print("Qualitative signals: " + str(len(signals)))

# Build analysis prompt
prompt_parts = []
prompt_parts.append("You are a Customer Success AI analyzing account health for a Data Center GPU hardware company.")
prompt_parts.append("")
prompt_parts.append("ACCOUNT INFORMATION:")
prompt_parts.append("- Name: " + account.account_name)
prompt_parts.append("- Industry: " + account.industry)
prompt_parts.append("- ARR: $" + str(account.revenue))
prompt_parts.append("- Region: " + account.region)
prompt_parts.append("")
prompt_parts.append("KPI TRENDS (Last 12 months):")

# Group KPIs by code
kpi_groups = {}
for kpi in kpis:
    if kpi.kpi_code not in kpi_groups:
        kpi_groups[kpi.kpi_code] = []
    kpi_groups[kpi.kpi_code].append({
        'date': kpi.measured_at,
        'value': float(kpi.value),
        'target': float(kpi.target)
    })

for code in sorted(kpi_groups.keys()):
    prompt_parts.append("\n" + code + ":")
    data = sorted(kpi_groups[code], key=lambda x: x['date'], reverse=True)
    for point in data[:6]:
        status = "ABOVE TARGET" if point['value'] >= point['target'] else "BELOW TARGET"
        date_str = point['date'].strftime("%Y-%m-%d")
        prompt_parts.append("  " + date_str + ": " + str(round(point['value'], 1)) + " (target: " + str(round(point['target'], 1)) + ") - " + status)

prompt_parts.append("\nQUALITATIVE SIGNALS:")
for sig in signals:
    prompt_parts.append("\n[" + str(sig.date) + "] " + sig.signal_type.upper())
    prompt_parts.append("From: " + sig.from_contact)
    prompt_parts.append("Subject: " + sig.subject)
    prompt_parts.append("Summary: " + sig.summary)
    prompt_parts.append("Sentiment: " + sig.sentiment + " | Priority: " + sig.priority)

prompt_parts.append("\nANALYSIS REQUIRED:")
prompt_parts.append("1. What is the overall health status of this account (Healthy/At-Risk/Critical)?")
prompt_parts.append("2. What are the top 3 risk factors or concerns?")
prompt_parts.append("3. What specific actions should the CSM take in the next 7 days?")
prompt_parts.append("4. What is the estimated churn risk percentage?")
prompt_parts.append("")
prompt_parts.append("Provide a concise, actionable analysis focused on what the CSM should do immediately.")

prompt = "\n".join(prompt_parts)

print("\n" + "=" * 70)
print("CALLING SIGNAL ANALYST AI...")
print("=" * 70)

response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=2000,
    messages=[{"role": "user", "content": prompt}]
)

print("\n" + "=" * 70)
print("SIGNAL ANALYST RECOMMENDATIONS:")
print("=" * 70)
print(response.content[0].text)
print("\n" + "=" * 70)
print("TEST COMPLETE!")
print("=" * 70)
