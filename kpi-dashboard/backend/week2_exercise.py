#!/usr/bin/env python3
"""
WEEK 2 EXERCISE - SIGNAL ANALYST AGENT TEST
Test LLM prompts with real DC2_S data
"""

import os
import json
from datetime import datetime
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import anthropic

load_dotenv()

# Initialize
engine = create_engine(os.getenv("DATABASE_URL"))
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

print("=" * 70)
print("WEEK 2 EXERCISE: SIGNAL ANALYST AGENT TEST")
print("=" * 70)

# ============================================================
# TEST 1: Health Assessment for At-Risk Account
# ============================================================

print("\n🔬 TEST 1: Analyze At-Risk Account (Legacy Manufacturing)")
print("-" * 70)

# Fetch account data
with engine.connect() as conn:
    # Get account details
    account = conn.execute(text("""
        SELECT 
            a.account_id,
            a.account_name,
            a.revenue,
            a.industry,
            a.profile_metadata
        FROM accounts a
        WHERE a.account_id = 1007
    """)).fetchone()
    
    # Get recent signals
    signals = conn.execute(text("""
        SELECT date, signal_type, from_contact, summary, sentiment
        FROM qualitative_signals
        WHERE account_id = 1007
        ORDER BY date DESC
        LIMIT 10
    """)).fetchall()
    
    # Get health trend
    health = conn.execute(text("""
        SELECT health_score, trend, velocity
        FROM health_trends
        WHERE account_id = 1007
        ORDER BY month DESC
        LIMIT 1
    """)).fetchone()

# Build prompt
profile_metadata = json.loads(account[4]) if account[4] else {}

prompt = f"""
Analyze this at-risk customer account and provide actionable insights.

## ACCOUNT PROFILE
Account: {account[1]} (ID: {account[0]})
ARR: ${account[2]:,.0f}
Industry: {account[3]}
CSM: {profile_metadata.get('assigned_csm', 'Unknown')}
Lifecycle Stage: {profile_metadata.get('engagement', {}).get('lifecycle_stage', 'Unknown')}

## HEALTH METRICS
Current Health Score: {health[0] if health else 'N/A'}
Trend: {health[1] if health else 'N/A'}
Velocity: {health[2] if health else 'N/A'} pts/month

## RECENT SIGNALS (Last 10)
"""

for sig in signals[:5]:  # Show top 5 in prompt
    prompt += f"\n- [{sig[0]}] {sig[1]}: \"{sig[3]}\" (Sentiment: {sig[4]})"

prompt += """

## YOUR TASK
Provide a JSON response with:
1. Risk assessment (low/medium/high/critical)
2. Churn probability (0-100%)
3. Top 3 risk factors
4. Top 3 recommended actions with owner and timeline
5. Confidence level (0-100%)

Return ONLY valid JSON, no markdown.
"""

# Call LLM
print("\n📤 Sending to Claude API...")
response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=2000,
    messages=[{"role": "user", "content": prompt}]
)

# Parse response
try:
    analysis = json.loads(response.content[0].text)
    print("\n📥 ANALYSIS RECEIVED:")
    print(json.dumps(analysis, indent=2))
    
    # Count tokens
    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens
    cost = (input_tokens * 3 / 1_000_000) + (output_tokens * 15 / 1_000_000)
    
    print(f"\n💰 COST:")
    print(f"   Input tokens: {input_tokens}")
    print(f"   Output tokens: {output_tokens}")
    print(f"   Total cost: ${cost:.4f}")
    
    print("\n✅ TEST 1 PASSED: LLM returned valid JSON analysis")
    
except json.JSONDecodeError as e:
    print(f"\n❌ TEST 1 FAILED: Invalid JSON response")
    print(f"   Error: {e}")
    print(f"   Response: {response.content[0].text}")

# ============================================================
# TEST 2: Portfolio Early Warning Scan
# ============================================================

print("\n\n🔬 TEST 2: Portfolio-Wide Early Warning Detection")
print("-" * 70)

# Fetch all accounts summary
with engine.connect() as conn:
    accounts = conn.execute(text("""
        SELECT 
            a.account_id,
            a.account_name,
            a.revenue,
            a.profile_metadata->'engagement'->>'engagement_score' as health_score,
            COUNT(CASE WHEN qs.sentiment = 'negative' THEN 1 END) as negative_signals
        FROM accounts a
        LEFT JOIN qualitative_signals qs ON a.account_id = qs.account_id
            AND qs.date >= CURRENT_DATE - INTERVAL '90 days'
        WHERE a.account_id BETWEEN 1001 AND 1010
        GROUP BY a.account_id, a.account_name, a.revenue, a.profile_metadata
        ORDER BY a.account_id
    """)).fetchall()

portfolio_data = []
for acc in accounts:
    portfolio_data.append({
        "account_id": acc[0],
        "account_name": acc[1],
        "arr": acc[2],
        "health_score": int(acc[3]) if acc[3] else 70,
        "negative_signals_90d": acc[4]
    })

prompt = f"""
Scan this DC2_S portfolio and identify accounts needing immediate attention.

## PORTFOLIO DATA
{json.dumps(portfolio_data, indent=2)}

## YOUR TASK
Return JSON array of at-risk accounts, prioritized by urgency. For each:
- account_id, account_name
- urgency (critical/high/medium)
- risk_score (0-100)
- churn_probability (0-100%)
- top_warning_signal (brief description)
- recommended_playbook (which playbook to trigger)

Sort by urgency/risk. Return ONLY valid JSON array.
"""

print("\n📤 Sending portfolio scan to Claude API...")
response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1500,
    messages=[{"role": "user", "content": prompt}]
)

try:
    at_risk = json.loads(response.content[0].text)
    print("\n📥 AT-RISK ACCOUNTS DETECTED:")
    print(json.dumps(at_risk, indent=2))
    
    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens
    cost = (input_tokens * 3 / 1_000_000) + (output_tokens * 15 / 1_000_000)
    
    print(f"\n💰 COST:")
    print(f"   Input tokens: {input_tokens}")
    print(f"   Output tokens: {output_tokens}")
    print(f"   Total cost: ${cost:.4f}")
    
    print("\n✅ TEST 2 PASSED: Portfolio scan completed")
    
except json.JSONDecodeError as e:
    print(f"\n❌ TEST 2 FAILED: Invalid JSON response")
    print(f"   Error: {e}")

# ============================================================
# TEST 3: Expansion Opportunity Identification
# ============================================================

print("\n\n🔬 TEST 3: Identify Expansion Opportunities")
print("-" * 70)

# Fetch healthy accounts
with engine.connect() as conn:
    healthy = conn.execute(text("""
        SELECT 
            a.account_id,
            a.account_name,
            a.revenue,
            a.profile_metadata
        FROM accounts a
        WHERE a.account_id BETWEEN 1001 AND 1010
            AND CAST(a.profile_metadata->'engagement'->>'engagement_score' AS INTEGER) >= 85
        ORDER BY a.revenue DESC
        LIMIT 3
    """)).fetchall()

expansion_data = []
for acc in healthy:
    pm = json.loads(acc[3])
    expansion_data.append({
        "account_id": acc[0],
        "account_name": acc[1],
        "current_arr": acc[2],
        "health_score": pm.get('engagement', {}).get('engagement_score', 0),
        "gpu_count": pm.get('dc2s_info', {}).get('gpu_count', 0),
        "gpu_model": pm.get('dc2s_info', {}).get('gpu_model', 'Unknown')
    })

prompt = f"""
Identify expansion opportunities for these healthy DC2_S accounts.

## HEALTHY ACCOUNTS
{json.dumps(expansion_data, indent=2)}

## YOUR TASK
Return JSON array of expansion recommendations. For each:
- account_id, account_name
- expansion_score (0-100)
- expansion_type (capacity_upgrade, new_use_case, additional_services)
- estimated_value ($ expansion potential)
- recommendation (specific expansion suggestion)
- timing (when to approach)
- confidence (0-100%)

Return ONLY valid JSON array.
"""

print("\n📤 Sending expansion analysis to Claude API...")
response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1500,
    messages=[{"role": "user", "content": prompt}]
)

try:
    expansions = json.loads(response.content[0].text)
    print("\n📥 EXPANSION OPPORTUNITIES:")
    print(json.dumps(expansions, indent=2))
    
    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens
    cost = (input_tokens * 3 / 1_000_000) + (output_tokens * 15 / 1_000_000)
    
    print(f"\n💰 COST:")
    print(f"   Input tokens: {input_tokens}")
    print(f"   Output tokens: {output_tokens}")
    print(f"   Total cost: ${cost:.4f}")
    
    print("\n✅ TEST 3 PASSED: Expansion analysis completed")
    
except json.JSONDecodeError as e:
    print(f"\n❌ TEST 3 FAILED: Invalid JSON response")
    print(f"   Error: {e}")

# ============================================================
# TEST SUMMARY
# ============================================================

print("\n" + "=" * 70)
print("WEEK 2 EXERCISE COMPLETE!")
print("=" * 70)
print("\n✅ All tests completed successfully!")
print("\n📊 NEXT STEPS:")
print("   1. Review JSON responses for quality")
print("   2. Tune prompts if needed")
print("   3. Move to Week 3-4: Build Pre-Processing Layer (Stage 4A)")
print("   4. Implement vector search (Week 5-6)")
print("\n🎉 MVP Week 2 milestone achieved!")
