#!/usr/bin/env python3
"""
Validate Customer 24 Data & Qdrant Integration
==============================================

Comprehensive validation of:
1. PostgreSQL data integrity
2. Qdrant collection and embeddings
3. Query performance
4. Signal Analyst integration readiness

Updated: Jan 5, 2026 (Latest Qdrant architecture)

Usage:
    python3 04_validate_data_integrity.py
"""

import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from qdrant_client import QdrantClient
from openai import OpenAI
import time

load_dotenv()

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL")
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

CUSTOMER_ID = 24
COLLECTION_NAME = f"kpi_dashboard_vectors_customer_24"
EMBEDDING_MODEL = "text-embedding-3-large"

print("=" * 80)
print("CUSTOMER 24 DATA & QDRANT VALIDATION")
print("=" * 80)

# Validate environment
issues = []
if not DATABASE_URL: issues.append("DATABASE_URL")
if not QDRANT_URL: issues.append("QDRANT_URL")
if not QDRANT_API_KEY: issues.append("QDRANT_API_KEY")
if not OPENAI_API_KEY: issues.append("OPENAI_API_KEY")

if issues:
    print(f"\n❌ Missing: {', '.join(issues)}")
    sys.exit(1)

# Initialize connections
print(f"\n{'─' * 80}")
print("CONNECTION TEST")
print("─" * 80)

# PostgreSQL
print("\n  PostgreSQL...", end=" ", flush=True)
try:
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version()"))
        version = result.scalar()
    print("✅")
    print(f"    {version.split(',')[0]}")
except Exception as e:
    print(f"❌ {e}")
    sys.exit(1)

# Qdrant
print("\n  Qdrant Cloud...", end=" ", flush=True)
try:
    qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    collections = qdrant.get_collections()
    print("✅")
    print(f"    {len(collections.collections)} collection(s)")
except Exception as e:
    print(f"❌ {e}")
    sys.exit(1)

# OpenAI
print("\n  OpenAI...", end=" ", flush=True)
try:
    openai_client = OpenAI(api_key=OPENAI_API_KEY)
    print("✅")
except Exception as e:
    print(f"❌ {e}")
    sys.exit(1)

# ============================================================================
# POSTGRESQL VALIDATION
# ============================================================================

print(f"\n{'=' * 80}")
print("POSTGRESQL DATA VALIDATION")
print("=" * 80)

with engine.connect() as conn:
    # Table counts
    print("\n📊 Table Record Counts:")
    print(f"{'Table':<35} {'Actual':>10} {'Expected':>10} {'Status':>8}")
    print("─" * 65)
    
    expected = {
        "customers": 1,
        "partner_definitions": 4,
        "accounts": 10,
        "account_profiles": 10,
        "kpi_definitions": 34,
        "kpi_measurements": 3696,
        "qualitative_signals": 320,
        "account_health_history": 113,
        "expansion_readiness_scores": 113,
        "playbook_executions": 28,
        "products": 7,
        "account_products": 24
    }
    
    table_issues = []
    for table, exp in expected.items():
        try:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
            actual = result.scalar()
            status = "✅" if actual == exp else "⚠️"
            print(f"{table:<35} {actual:>10,} {exp:>10,} {status:>8}")
            if actual != exp:
                table_issues.append(f"{table}: {actual} != {exp}")
        except Exception as e:
            print(f"{table:<35} {'ERROR':>10} {exp:>10,} {'❌':>8}")
            table_issues.append(f"{table}: {e}")
    
    # Data quality checks
    print(f"\n🔍 Data Quality Checks:")
    print("─" * 80)
    
    quality_checks = [
        {
            "name": "All accounts have profiles",
            "query": """
                SELECT COUNT(*) FROM accounts a
                LEFT JOIN account_profiles ap ON a.account_id = ap.account_id
                WHERE ap.account_id IS NULL
            """,
            "expected": 0
        },
        {
            "name": "All KPI measurements have definitions",
            "query": """
                SELECT COUNT(*) FROM kpi_measurements k
                LEFT JOIN kpi_definitions d ON k.kpi_code = d.kpi_code
                WHERE d.kpi_code IS NULL
            """,
            "expected": 0
        },
        {
            "name": "All qualitative signals have valid accounts",
            "query": """
                SELECT COUNT(*) FROM qualitative_signals q
                LEFT JOIN accounts a ON q.account_id = a.account_id
                WHERE a.account_id IS NULL
            """,
            "expected": 0
        },
        {
            "name": "All account products have valid products",
            "query": """
                SELECT COUNT(*) FROM account_products ap
                LEFT JOIN products p ON ap.product_id = p.product_id
                WHERE p.product_id IS NULL
            """,
            "expected": 0
        },
        {
            "name": "Date ranges are valid (2023-2025)",
            "query": """
                SELECT COUNT(*) FROM kpi_measurements
                WHERE measurement_date < '2023-01-01' OR measurement_date > '2025-12-31'
            """,
            "expected": 0
        }
    ]
    
    quality_issues = []
    for check in quality_checks:
        result = conn.execute(text(check["query"]))
        actual = result.scalar()
        status = "✅" if actual == check["expected"] else f"❌ ({actual} issues)"
        print(f"  {check['name']:<50} {status}")
        if actual != check["expected"]:
            quality_issues.append(f"{check['name']}: {actual} issues")
    
    # Customer 24 specific checks
    print(f"\n🎯 Customer 24 Specific Checks:")
    print("─" * 80)
    
    # Journey distribution
    result = conn.execute(text("""
        SELECT journey_type, COUNT(*) as count
        FROM account_profiles ap
        JOIN accounts a ON ap.account_id = a.account_id
        GROUP BY journey_type
        ORDER BY count DESC
    """))
    
    print(f"\n  Journey Types:")
    journey_count = 0
    for row in result:
        print(f"    • {row.journey_type:<30} {row.count} account(s)")
        journey_count += 1
    
    if journey_count != 10:
        quality_issues.append(f"Journey types: {journey_count} unique (expected 10)")
    
    # Health score distribution
    result = conn.execute(text("""
        SELECT 
            CASE 
                WHEN overall_health_score >= 90 THEN 'Excellent (90-100)'
                WHEN overall_health_score >= 80 THEN 'Healthy (80-89)'
                WHEN overall_health_score >= 65 THEN 'Fair (65-79)'
                WHEN overall_health_score >= 50 THEN 'At Risk (50-64)'
                ELSE 'Critical (<50)'
            END as health_band,
            COUNT(*) as count
        FROM account_profiles ap
        JOIN accounts a ON ap.account_id = a.account_id
        GROUP BY health_band
        ORDER BY MIN(overall_health_score) DESC
    """))
    
    print(f"\n  Health Score Distribution:")
    for row in result:
        print(f"    • {row.health_band:<25} {row.count} account(s)")
    
    # Product adoption
    result = conn.execute(text("""
        SELECT 
            COUNT(DISTINCT account_id) as accounts_with_products,
            COUNT(*) as total_products,
            AVG(product_count) as avg_products_per_account
        FROM (
            SELECT account_id, COUNT(*) as product_count
            FROM account_products
            GROUP BY account_id
        ) sub
    """))
    
    row = result.fetchone()
    print(f"\n  Product Adoption:")
    print(f"    • Accounts with products: {row.accounts_with_products} / 10")
    print(f"    • Total product usages: {row.total_products}")
    print(f"    • Avg products per account: {row.avg_products_per_account:.1f}")

# ============================================================================
# QDRANT VALIDATION
# ============================================================================

print(f"\n{'=' * 80}")
print("QDRANT COLLECTION VALIDATION")
print("=" * 80)

# Check collection exists
print(f"\n  Collection: {COLLECTION_NAME}")
collections = qdrant.get_collections().collections
collection_names = [c.name for c in collections]

if COLLECTION_NAME not in collection_names:
    print(f"  ❌ Collection does not exist!")
    print(f"\n  Run: python3 03_embed_signals_qdrant.py")
    sys.exit(1)

print(f"  ✅ Collection exists")

# Get collection info
info = qdrant.get_collection(COLLECTION_NAME)
print(f"\n  📊 Collection Details:")
print(f"    • Points: {info.points_count:,}")
print(f"    • Vector dimension: {info.config.params.vectors.size}")
print(f"    • Distance metric: {info.config.params.vectors.distance}")

# Expected counts
expected_points = 320 + 34  # 320 signals + 34 KPIs = 354
if info.points_count == expected_points:
    print(f"    • Status: ✅ Expected count ({expected_points})")
else:
    print(f"    • Status: ⚠️  Expected {expected_points}, got {info.points_count}")

# Test queries by type
print(f"\n  🔍 Testing Queries by Type:")
print("  ─" * 40)

# Count qualitative signals
qual_results = qdrant.scroll(
    collection_name=COLLECTION_NAME,
    scroll_filter={"must": [{"key": "type", "match": {"value": "qualitative_signal"}}]},
    limit=1000,
    with_payload=False
)
qual_count = len(qual_results[0])
print(f"    • Qualitative signals: {qual_count:,} (expected: 320)")

# Count KPI definitions
kpi_results = qdrant.scroll(
    collection_name=COLLECTION_NAME,
    scroll_filter={"must": [{"key": "type", "match": {"value": "kpi_definition"}}]},
    limit=1000,
    with_payload=False
)
kpi_count = len(kpi_results[0])
print(f"    • KPI definitions: {kpi_count:,} (expected: 34)")

# Test queries by account
print(f"\n  🎯 Testing Queries by Account:")
print("  ─" * 40)

test_accounts = [34000, {ACCOUNT_ID_START+2}, 10007]  # Success, churned, recovery

for account_id in test_accounts:
    account_results = qdrant.scroll(
        collection_name=COLLECTION_NAME,
        scroll_filter={"must": [
            {"key": "type", "match": {"value": "qualitative_signal"}},
            {"key": "account_id", "match": {"value": account_id}}
        ]},
        limit=1000,
        with_payload=False
    )
    count = len(account_results[0])
    print(f"    • Account {account_id}: {count:,} signals")

# ============================================================================
# SEMANTIC SEARCH VALIDATION
# ============================================================================

print(f"\n{'=' * 80}")
print("SEMANTIC SEARCH VALIDATION")
print("=" * 80)

test_queries_detail = [
    {
        "query": "champion risk and stakeholder turnover",
        "expected_types": ["qualitative_signal"],
        "expected_keywords": ["champion", "turnover", "risk"]
    },
    {
        "query": "GPU utilization and performance metrics",
        "expected_types": ["kpi_definition"],
        "expected_keywords": ["GPU", "utilization", "performance"]
    },
    {
        "query": "budget concerns and cost pressure",
        "expected_types": ["qualitative_signal"],
        "expected_keywords": ["budget", "cost", "pressure"]
    }
]

for i, test in enumerate(test_queries_detail, 1):
    print(f"\n  Query {i}: '{test['query']}'")
    
    # Generate embedding
    start = time.time()
    response = openai_client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=test["query"]
    )
    embedding_time = time.time() - start
    
    # Search
    start = time.time()
    results = qdrant.search(
        collection_name=COLLECTION_NAME,
        query_vector=response.data[0].embedding,
        limit=5
    )
    search_time = time.time() - start
    
    print(f"    Timing: Embedding {embedding_time*1000:.0f}ms | Search {search_time*1000:.0f}ms")
    print(f"    Top 5 results:")
    
    for j, result in enumerate(results, 1):
        payload = result.payload
        signal_type = payload.get('type', 'unknown')
        score = result.score
        
        if signal_type == 'qualitative_signal':
            subject = payload.get('subject', 'N/A')[:40]
            account = payload.get('account_name', 'N/A')
            print(f"      {j}. [{score:.3f}] Signal: {subject}... (Account: {account})")
        else:
            kpi_name = payload.get('kpi_name', 'N/A')
            category = payload.get('category', 'N/A')
            print(f"      {j}. [{score:.3f}] KPI: {kpi_name} ({category})")

# ============================================================================
# SIGNAL ANALYST READINESS
# ============================================================================

print(f"\n{'=' * 80}")
print("SIGNAL ANALYST INTEGRATION READINESS")
print("=" * 80)

readiness_checks = [
    ("PostgreSQL connection", DATABASE_URL is not None),
    ("Qdrant connection", QDRANT_URL is not None),
    ("OpenAI API key", OPENAI_API_KEY is not None),
    (f"Collection '{COLLECTION_NAME}' exists", COLLECTION_NAME in collection_names),
    ("Expected data volume", info.points_count >= 300),
    ("Embedding dimension matches", info.config.params.vectors.size == 3072),
    ("All tables loaded", len(table_issues) == 0),
    ("Data quality OK", len(quality_issues) == 0),
]

print(f"\n  Checklist:")
all_ready = True
for check, status in readiness_checks:
    symbol = "✅" if status else "❌"
    print(f"    {symbol} {check}")
    if not status:
        all_ready = False

# Final summary
print(f"\n{'=' * 80}")
if all_ready and len(table_issues) == 0 and len(quality_issues) == 0:
    print("✅ ALL VALIDATIONS PASSED")
    print("=" * 80)
    print("\n🎉 Customer 24 test environment is ready!")
    print("\n📋 Next Steps:")
    print("  1. Test Signal Analyst with Customer 24 accounts")
    print("  2. Validate query patterns and accuracy")
    print("  3. Monitor performance metrics")
    print("  4. Compare results vs. Customer 5 (production)\n")
else:
    print("⚠️  VALIDATION ISSUES DETECTED")
    print("=" * 80)
    
    if table_issues:
        print("\n❌ Table Issues:")
        for issue in table_issues:
            print(f"  • {issue}")
    
    if quality_issues:
        print("\n❌ Quality Issues:")
        for issue in quality_issues:
            print(f"  • {issue}")
    
    print("\n📋 Recommended Actions:")
    if table_issues:
        print("  1. Re-run data loader: python3 02_load_customer24_data.py")
    if not all_ready:
        print("  2. Check environment variables and connections")
    if COLLECTION_NAME not in collection_names:
        print("  3. Run embedding script: python3 03_embed_signals_qdrant.py")
    print()
