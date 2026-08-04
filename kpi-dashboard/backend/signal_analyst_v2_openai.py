#!/usr/bin/env python3
"""Signal Analyst V2 - Dual Collection Vector Search (OpenAI)
Modified to analyze all accounts for customer 5 and output to analyst.out"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from qdrant_client import QdrantClient
from openai import OpenAI
import anthropic

try:
    from utils.llm_budget_controller import can_call as _budget_can_call, record_usage as _budget_record
except Exception:
    _budget_can_call = None
    _budget_record = None

load_dotenv()

# Output file
OUTPUT_FILE = "analyst.out"

# Redirect stdout to both file and console
class TeeOutput:
    def __init__(self, *files):
        self.files = files
    
    def write(self, obj):
        for f in self.files:
            f.write(obj)
            f.flush()
    
    def flush(self):
        for f in self.files:
            f.flush()

# Open output file
output_file = open(OUTPUT_FILE, 'w', encoding='utf-8')
original_stdout = sys.stdout
sys.stdout = TeeOutput(original_stdout, output_file)

print("=" * 70)
print("SIGNAL ANALYST V2 - BATCH ANALYSIS FOR ALL ACCOUNTS")
print("=" * 70)
print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"Output file: {OUTPUT_FILE}")
print()

# Initialize
engine = create_engine(os.getenv("DATABASE_URL"))
qdrant = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY"),
)
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
claude_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

CUSTOMER_ID = 5
KPI_COLLECTION = "kpi_dashboard_vectors_customer_5"
SIGNALS_COLLECTION = "kpi_dashboard_signals_customer_1"
EMBEDDING_MODEL = "text-embedding-3-large"

# Get all accounts for customer 5
print("=" * 70)
print("FETCHING ACCOUNTS FOR CUSTOMER", CUSTOMER_ID)
print("=" * 70)

with engine.connect() as conn:
    accounts = conn.execute(text("""
        SELECT account_id, account_name, revenue, industry, region
        FROM accounts
        WHERE customer_id = :customer_id
        ORDER BY account_id
    """), {"customer_id": CUSTOMER_ID}).fetchall()

print(f"\nFound {len(accounts)} accounts to analyze\n")

# Track totals
total_cost = 0.0
successful_analyses = 0
failed_analyses = 0

def analyze_account(ACCOUNT_ID, account):
    """Analyze a single account and return the result"""
    print("\n" + "=" * 70)
    print(f"ANALYZING ACCOUNT {ACCOUNT_ID}: {account.account_name}")
    print("=" * 70)

    print(f"\nAccount: {account.account_name}")
    print(f"ARR: ${account.revenue:,.2f}")
    print(f"Industry: {account.industry}")

    print("\n" + "-" * 70)
    print("SMART RETRIEVAL: VECTOR SEARCH")
    print("-" * 70)
    
    # Create search query based on account context
    search_query = "account health risks concerns performance issues budget constraints"
    print(f"\nSearch query: '{search_query}'")

    # Generate query embedding
    query_response = openai_client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=search_query
    )
    query_embedding = query_response.data[0].embedding

    # Search 1: Find relevant signals
    print("\n1. Searching signals collection...")
    try:
        # Get more results, then filter by account_id in Python (no index required)
        search_results = qdrant.query_points(
            collection_name=SIGNALS_COLLECTION,
            query=query_embedding,
            limit=30,  # Get more results to filter by account_id
            with_payload=True
        )
        # Filter by account_id and score threshold, then limit to top 5
        signal_results = []
        total_points = len(search_results.points) if search_results.points else 0
        print(f"   Retrieved {total_points} points from Qdrant")
        
        for point in search_results.points:
            if hasattr(point, 'payload') and point.payload:
                payload_account_id = point.payload.get('account_id')
                score = point.score if hasattr(point, 'score') else 0
                # Account ID might be stored as string or int - normalize comparison
                if payload_account_id == ACCOUNT_ID or str(payload_account_id) == str(ACCOUNT_ID):
                    # Lower threshold to 0.3 to get more results (cosine similarity can vary)
                    if score > 0.3:  # Similarity threshold (lowered further)
                        signal_results.append(point)
        
        # Sort by score descending and take top 5
        signal_results = sorted(signal_results, key=lambda x: getattr(x, 'score', 0), reverse=True)[:5]
        
        print(f"   Found {len(signal_results)} relevant signals for account {ACCOUNT_ID}")
        
        for i, result in enumerate(signal_results):
            score = result.score if hasattr(result, 'score') else 0
            payload = result.payload
            subject = payload.get('subject', 'N/A') if payload else 'N/A'
            print(f"   {i+1}. Score: {round(score, 3)} - {subject}")
    except Exception as e:
        print(f"   Warning: Could not search signals collection: {e}")
        signal_results = []

    # Search 2: Find similar KPI patterns (optional - if you want to use existing collection)
    print("\n2. Searching KPI patterns collection...")
    try:
        # Get more results, then filter by account_id in Python (no index required)
        search_results = qdrant.query_points(
            collection_name=KPI_COLLECTION,
            query=query_embedding,
            limit=30,  # Get more results to filter by account_id
            with_payload=True
        )
        # Filter by account_id and score threshold, then limit to top 5
        kpi_results = []
        for point in search_results.points:
            if hasattr(point, 'payload') and point.payload:
                payload_account_id = point.payload.get('account_id')
                # Account ID might be stored as string or int - normalize comparison
                if payload_account_id == ACCOUNT_ID or str(payload_account_id) == str(ACCOUNT_ID):
                    score = point.score if hasattr(point, 'score') else 0
                    # Lower threshold to 0.5 to get more results (cosine similarity can vary)
                    if score > 0.5:  # Similarity threshold (lowered from 0.7)
                        kpi_results.append(point)
        
        # Sort by score descending and take top 5
        kpi_results = sorted(kpi_results, key=lambda x: getattr(x, 'score', 0), reverse=True)[:5]
        
        print(f"   Found {len(kpi_results)} relevant KPI patterns")
    except Exception as e:
        print(f"   Warning: Could not search KPI collection: {e}")
        kpi_results = []

    # Also get recent KPIs from PostgreSQL for current values
    print("\n3. Getting recent KPI values from PostgreSQL...")
    with engine.connect() as conn:
        recent_kpis = conn.execute(text("""
            SELECT kpi_code, value, target, measured_at
            FROM dc2s_kpis
            WHERE account_id = :id
            ORDER BY measured_at DESC
            LIMIT 6
        """), {"id": ACCOUNT_ID}).fetchall()
        print(f"   Retrieved {len(recent_kpis)} recent KPI measurements")

    print("\n" + "-" * 70)
    print("BUILDING ANALYSIS PROMPT")
    print("-" * 70)

    # Build comprehensive prompt
    prompt_parts = []
    prompt_parts.append("You are a Customer Success AI analyzing account health for a Data Center GPU hardware company.")
    prompt_parts.append("")
    prompt_parts.append("ACCOUNT INFORMATION:")
    prompt_parts.append(f"- Name: {account.account_name}")
    prompt_parts.append(f"- ARR: ${account.revenue:,.2f}")
    prompt_parts.append(f"- Industry: {account.industry}")
    prompt_parts.append("")

    # Add recent KPI values
    prompt_parts.append("CURRENT KPI STATUS:")
    for kpi in recent_kpis:
        status = "ABOVE TARGET" if kpi.value >= kpi.target else "BELOW TARGET"
        prompt_parts.append(f"{kpi.kpi_code}: {round(kpi.value, 1)} (target: {round(kpi.target, 1)}) - {status}")

    # Add vector-searched signals
    if signal_results:
        prompt_parts.append("\nMOST RELEVANT CUSTOMER SIGNALS (vector search):")
        for result in signal_results:
            p = result.payload if hasattr(result, 'payload') else {}
            score = result.score if hasattr(result, 'score') else getattr(result, 'distance', 0)
            prompt_parts.append(f"\n[{p.get('date', 'N/A')}] {p.get('signal_type', 'N/A').upper()}")
            prompt_parts.append(f"Subject: {p.get('subject', 'N/A')}")
            prompt_parts.append(f"Summary: {p.get('summary', 'N/A')}")
            prompt_parts.append(f"Sentiment: {p.get('sentiment', 'N/A')} | Priority: {p.get('priority', 'N/A')}")
            prompt_parts.append(f"Relevance: {round(score, 3)}")

    prompt_parts.append("\nANALYSIS REQUIRED:")
    prompt_parts.append("1. Overall health status (Healthy/At-Risk/Critical)")
    prompt_parts.append("2. Top 3 risk factors with evidence")
    prompt_parts.append("3. Specific actions for CSM (next 7 days)")
    prompt_parts.append("4. Estimated churn risk percentage")
    prompt_parts.append("")
    prompt_parts.append("Provide concise, actionable recommendations.")

    prompt = "\n".join(prompt_parts)

    # Estimate tokens
    token_count_approx = len(prompt.split())
    print(f"\nPrompt size: ~{token_count_approx} words")

    print("\n" + "-" * 70)
    print("CALLING CLAUDE API...")
    print("-" * 70)

    # Budget check (fail-open)
    try:
        if _budget_can_call and not _budget_can_call(0, 'signal_analyst'):
            print("Budget limit reached — skipping LLM call")
            return {'account_id': ACCOUNT_ID, 'success': False, 'error': 'budget_exceeded'}
    except Exception:
        pass

    response = claude_client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )

    # Calculate costs
    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens

    # Record usage (fail-open)
    try:
        if _budget_record:
            _budget_record(0, 'signal_analyst',
                           tokens_in=input_tokens, tokens_out=output_tokens,
                           model='claude-sonnet-4-6')
    except Exception:
        pass
    claude_cost = (input_tokens * 0.000003) + (output_tokens * 0.000015)
    embedding_cost = (query_response.usage.total_tokens / 1_000_000) * 0.13

    account_cost = claude_cost + embedding_cost

    print("\nAPI Usage:")
    print(f"  OpenAI embedding tokens: {query_response.usage.total_tokens}")
    print(f"  Claude input tokens: {input_tokens}")
    print(f"  Claude output tokens: {output_tokens}")
    print(f"  Embedding cost: ${round(embedding_cost, 5)}")
    print(f"  Claude cost: ${round(claude_cost, 5)}")
    print(f"  Total cost: ${round(account_cost, 5)}")

    print("\n" + "-" * 70)
    print("SIGNAL ANALYST RECOMMENDATIONS:")
    print("-" * 70)
    analysis_text = response.content[0].text
    print(analysis_text)
    
    print("\n" + "-" * 70)
    print("ANALYSIS SUMMARY:")
    print("-" * 70)
    print(f"  PostgreSQL KPIs: {len(recent_kpis)} current values")
    print(f"  Vector search signals: {len(signal_results)} most relevant")
    print(f"  Analysis cost: ${account_cost:.5f}")
    
    return {
        'account_id': ACCOUNT_ID,
        'account_name': account.account_name,
        'success': True,
        'cost': account_cost,
        'kpi_count': len(recent_kpis),
        'signal_count': len(signal_results),
        'analysis': analysis_text
    }

# Main loop: Analyze all accounts
print("\n" + "=" * 70)
print("STARTING BATCH ANALYSIS")
print("=" * 70)

results = []
for i, account in enumerate(accounts, 1):
    try:
        print(f"\n\n{'#' * 70}")
        print(f"# ACCOUNT {i} of {len(accounts)}")
        print(f"{'#' * 70}")
        
        result = analyze_account(account.account_id, account)
        results.append(result)
        successful_analyses += 1
        total_cost += result['cost']
        
    except Exception as e:
        print(f"\n❌ ERROR analyzing account {account.account_id} ({account.account_name}): {e}")
        import traceback
        traceback.print_exc()
        failed_analyses += 1
        results.append({
            'account_id': account.account_id,
            'account_name': account.account_name,
            'success': False,
            'error': str(e)
        })

# Final summary
print("\n\n" + "=" * 70)
print("BATCH ANALYSIS COMPLETE")
print("=" * 70)
print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"\nSummary:")
print(f"  Total accounts analyzed: {len(accounts)}")
print(f"  Successful: {successful_analyses}")
print(f"  Failed: {failed_analyses}")
print(f"  Total cost: ${total_cost:.5f}")
print(f"\nPer-account average cost: ${(total_cost/successful_analyses if successful_analyses > 0 else 0):.5f}")

print("\n" + "=" * 70)
print("ACCOUNT-BY-ACCOUNT SUMMARY")
print("=" * 70)
for result in results:
    if result.get('success'):
        print(f"\nAccount {result['account_id']}: {result['account_name']}")
        print(f"  ✅ Success | KPIs: {result['kpi_count']} | Signals: {result['signal_count']} | Cost: ${result['cost']:.5f}")
    else:
        print(f"\nAccount {result['account_id']}: {result['account_name']}")
        print(f"  ❌ Failed: {result.get('error', 'Unknown error')}")

# Close output file and restore stdout
output_file.close()
sys.stdout = original_stdout

print(f"\n✅ Analysis complete! Results saved to {OUTPUT_FILE}")
print(f"   Total cost: ${total_cost:.5f}")
print(f"   Successful analyses: {successful_analyses}/{len(accounts)}")
