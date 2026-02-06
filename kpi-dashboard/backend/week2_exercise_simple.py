#!/usr/bin/env python3
import os
import json
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import anthropic

load_dotenv()

print("=" * 70)
print("WEEK 2 EXERCISE: SIGNAL ANALYST AGENT TEST")
print("=" * 70)

engine = create_engine(os.getenv("DATABASE_URL"))
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

ACCOUNT_ID = 1007

print("\nAnalyzing Account " + str(ACCOUNT_ID))
print("-" * 70)

with engine.connect() as conn:
    query = "SELECT account_id, account_name, revenue, industry, region, profile_metadata FROM accounts WHERE account_id = :id"
    account = conn.execute(text(query), {"id": ACCOUNT_ID}).fetchone()
    
    if not account:
        print("Account not found!")
        exit(1)
    
    metadata = {}
    if account.profile_metadata:
        metadata = json.loads(account.profile_metadata)
    
    print("\nAccount: " + account.account_name)
    print("ARR: $" + str(account.revenue))
    print("Health Score: " + str(metadata.get('health_score', 'N/A')))
    print("Days to Renewal: " + str(metadata.get('days_to_renewal', 'N/A')))
    
    query2 = "SELECT kpi_code, month, value, target FROM kpi_data_monthly WHERE account_id = :id ORDER BY month DESC LIMIT 12"
    kpis = conn.execute(text(query2), {"id": ACCOUNT_ID}).fetchall()
    
    print("\nKPI Trends: " + str(len(kpis)) + " data points")
    
    query3 = "SELECT date, signal_type, from_contact, subject, summary, sentiment, priority FROM qualitative_signals WHERE account_id = :id ORDER BY date DESC"
    signals = conn.execute(text(query3), {"id": ACCOUNT_ID}).fetchall()
    
    print("Qualitative Signals: " + str(len(signals)) + " found")
    for sig in signals:
        print("  [" + sig.signal_type + "] " + sig.subject + " - " + sig.sentiment)

prompt = "You are a Customer Success AI analyzing account health.\n\n"
prompt += "ACCOUNT: " + account.account_name + "\n"
prompt += "- Industry: " + account.industry + "\n"
prompt += "- ARR: $" + str(account.revenue) + "\n"
prompt += "- Health Score: " + str(metadata.get('health_score')) + "/100\n"
prompt += "- Days to Renewal: " + str(metadata.get('days_to_renewal')) + "\n"
prompt += "- CSM: " + str(metadata.get('csm')) + "\n\n"
prompt += "KPI TRENDS:\n"

kpi_summary = {}
for kpi in kpis:
    if kpi.kpi_code not in kpi_summary:
        kpi_summary[kpi.kpi_code] = []
    kpi_data = {
        'month': kpi.month,
        'value': float(kpi.value),
        'target': float(kpi.target)
    }
    kpi_summary[kpi.kpi_code].append(kpi_data)

for code in kpi_summary:
    prompt += "\n" + code + ":\n"
    data_list = kpi_summary[code]
    for p in data_list[:6]:
        status = "OK" if p['value'] >= p['target'] else "ALERT"
        prompt += "  " + p['month'] + ": " + str(round(p['value'], 1)) + " (target: " + str(round(p['target'], 1)) + ") " + status + "\n"

prompt += "\nQUALITATIVE SIGNALS:\n"
for sig in signals:
    prompt += "\n[" + str(sig.date) + "] " + sig.signal_type + ": " + sig.subject + "\n"
    prompt += "From: " + sig.from_contact + "\n"
    prompt += "Summary: " + sig.summary + "\n"
    prompt += "Sentiment: " + sig.sentiment + "\n"

prompt += "\nANALYSIS REQUIRED:\n"
prompt += "1. Assess health and risk level\n"
prompt += "2. Identify top 3 risk factors\n"
prompt += "3. Provide actionable recommendations\n"
prompt += "4. Estimate churn probability\n\n"
prompt += "Be concise and actionable."

print("\n" + "=" * 70)
print("CALLING SIGNAL ANALYST...")
print("=" * 70)

response = client.messages.create(
    model="claude-sonnet-4-20250514",
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
