#!/usr/bin/env python3
"""
Validate Customer 20 Data & Qdrant Integration
==============================================

Comprehensive validation of:
1. PostgreSQL data integrity
2. Qdrant collection and embeddings
3. Query performance
4. Signal Analyst integration readiness

Updated: Jan 6, 2026 (Customer 20 Production)

Usage:
    python3 04_validate_data_integrity.py
"""

import os
import sys
from sqlalchemy import create_engine, text
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
import time

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost:5432/cs_pulse_datacenter")
QDRANT_URL = os.getenv("QDRANT_URL", "https://7528cec3-24f4-4584-bee2-ca371726134a.us-east-1-1.aws.cloud.qdrant.io:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.8t-hHzNql_9C-BEBs2Pye0l942C6HbBvz7Ro_DDKEH4")

CUSTOMER_ID = 20
COLLECTION_NAME = "customer_signals"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

print("=" * 80)
print("CUSTOMER 20 DATA & QDRANT VALIDATION")
print("=" * 80)

# Validate environment
issues = []
if not DATABASE_URL:
    issues.append("DATABASE_URL")
if not QDRANT_URL:
    issues.append("QDRANT_URL")
if not QDRANT_API_KEY:
    issues.append("QDRANT_API_KEY")

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

# Embedding Model
print("\n  Embedding Model...", end=" ", flush=True)
try:
    model = SentenceTransformer(EMBEDDING_MODEL)
    embedding_dim = model.get_sentence_embedding_dimension()
    print("✅")
    print(f"    Model: {EMBEDDING_MODEL}")
    print(f"    Dimension: {embedding_dim}")
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
            if table in ["accounts", "qualitative_signals", "kpi_measurements", "account_profiles",
                        "account_health_history", "expansion_readiness_scores", "playbook_executions",
                        "account_products"]:
                # Check Customer 20 specific data
                if table == "accounts":
                    query = f"SELECT COUNT(*) FROM {table} WHERE customer_id = 20"
                elif table in ["kpi_definitions", "products", "partner_definitions"]:
                    query = f"SELECT COUNT(*) FROM {table}"
                else:
                    query = f"SELECT COUNT(*) FROM {table} WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = 20)"
            else:
                query = f"SELECT COUNT(*) FROM {table}"
                
            result = conn.execute(text(query))
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
                WHERE ap.account_id IS NULL AND a.customer_id = 20
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
                WHERE measurement_month < '2023-01-01' OR measurement_month > '2025-12-31'
            """,
            "expected": 0
        },
        {
            "name": "All signals have content",
            "query": """
                SELECT COUNT(*) FROM qualitative_signals
                WHERE content IS NULL OR TRIM(content) = ''
            """,
            "expected": 0
        }
    ]
    
    quality_issues = []
    for check in quality_checks:
        try:
            result = conn.execute(text(check["query"]))
            actual = result.scalar()
            status = "✅" if actual == check["expected"] else f"❌ ({actual} issues)"
            print(f"  {check['name']:<50} {status}")
            if actual != check["expected"]:
                quality_issues.append(f"{check['name']}: {actual} issues")
        except Exception as e:
            print(f"  {check['name']:<50} ❌ Error: {e}")
            quality_issues.append(f"{check['name']}: {e}")
    
    # Customer 20 specific checks
    print(f"\n🎯 Customer 20 Specific Checks:")
    print("─" * 80)
    
    # Account count
    result = conn.execute(text("""
        SELECT COUNT(*) FROM accounts WHERE customer_id = 20
    """))
    account_count = result.scalar()
    print(f"\n  Total Accounts: {account_count}")
    
    # Product adoption
    result = conn.execute(text("""
        SELECT 
            COUNT(DISTINCT ap.account_id) as accounts_with_products,
            COUNT(*) as total_products,
            ROUND(AVG(product_count), 1) as avg_products_per_account
        FROM (
            SELECT account_id, COUNT(*) as product_count
            FROM account_products
            WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = 20)
            GROUP BY account_id
        ) sub
        FULL OUTER JOIN account_products ap ON 1=1
        WHERE ap.account_id IN (SELECT account_id FROM accounts WHERE customer_id = 20)
    """))
    
    row = result.fetchone()
    if row and row.accounts_with_products:
        print(f"\n  Product Adoption:")
        print(f"    • Accounts with products: {row.accounts_with_products} / {account_count}")
        print(f"    • Total product usages: {row.total_products}")
        print(f"    • Avg products per account: {row.avg_products_per_account}")
    
    # Signal distribution
    result = conn.execute(text("""
        SELECT 
            signal_type,
            COUNT(*) as count
        FROM qualitative_signals
        WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = 20)
        GROUP BY signal_type
        ORDER BY count DESC
        LIMIT 10
    """))
    
    print(f"\n  Signal Types:")
    for row in result:
        print(f"    • {row.signal_type:<30} {row.count} signal(s)")

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
    print(f"\n  Run: python3 scripts/03_embed_signals_qdrant.py")
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

# Count signals
qual_results = qdrant.scroll(
    collection_name=COLLECTION_NAME,
    scroll_filter={"must": [{"key": "type", "match": {"value": "signal"}}]},
    limit=1000,
    with_payload=False
)
qual_count = len(qual_results[0])
status = "✅" if qual_count == 320 else "⚠️"
print(f"    • Signals: {qual_count:,} (expected: 320) {status}")

# Count KPI definitions
kpi_results = qdrant.scroll(
    collection_name=COLLECTION_NAME,
    scroll_filter={"must": [{"key": "type", "match": {"value": "kpi"}}]},
    limit=1000,
    with_payload=False
)
kpi_count = len(kpi_results[0])
status = "✅" if kpi_count == 34 else "⚠️"
print(f"    • KPIs: {kpi_count:,} (expected: 34) {status}")

# Test queries by account
print(f"\n  🎯 Testing Queries by Account:")
print("  ─" * 40)

test_accounts = [30000, {ACCOUNT_ID_START+2}, 10007]  # Success, churned, recovery

for account_id in test_accounts:
    account_results = qdrant.scroll(
        collection_name=COLLECTION_NAME,
        scroll_filter={"must": [
            {"key": "type", "match": {"value": "signal"}},
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

test_queries = [
    "champion risk and stakeholder turnover",
    "GPU utilization and performance metrics",
    "budget concerns and cost pressure"
]

for i, query_text in enumerate(test_queries, 1):
    print(f"\n  Query {i}: '{query_text}'")
    
    # Generate embedding
    start = time.time()
    query_embedding = model.encode([query_text])[0]
    embedding_time = time.time() - start
    
    # Search
    start = time.time()
    results = qdrant.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_embedding.tolist(),
        limit=5
    )
    search_time = time.time() - start
    
    print(f"    Timing: Embedding {embedding_time*1000:.0f}ms | Search {search_time*1000:.0f}ms")
    print(f"    Top 5 results:")
    
    for j, result in enumerate(results, 1):
        payload = result.payload
        signal_type = payload.get('type', 'unknown')
        score = result.score
        
        if signal_type == 'signal':
            content = payload.get('content', 'N/A')[:50]
            account = payload.get('account_id', 'N/A')
            sentiment = payload.get('sentiment', 'N/A')
            print(f"      {j}. [{score:.3f}] Signal (Account {account}): {content}... [{sentiment}]")
        else:
            kpi_name = payload.get('kpi_name', 'N/A')
            pillar = payload.get('pillar', 'N/A')
            print(f"      {j}. [{score:.3f}] KPI: {kpi_name} ({pillar})")

# ============================================================================
# SIGNAL ANALYST READINESS
# ============================================================================

print(f"\n{'=' * 80}")
print("SIGNAL ANALYST INTEGRATION READINESS")
print("=" * 80)

readiness_checks = [
    ("PostgreSQL connection", DATABASE_URL is not None),
    ("Qdrant connection", QDRANT_URL is not None and QDRANT_API_KEY is not None),
    ("Embedding model loaded", embedding_dim == 384),
    (f"Collection '{COLLECTION_NAME}' exists", COLLECTION_NAME in collection_names),
    ("Expected data volume", info.points_count >= 300),
    ("Embedding dimension matches", info.config.params.vectors.size == 384),
    ("All tables loaded", len(table_issues) == 0),
    ("Data quality OK", len(quality_issues) == 0),
    ("Signals have content", qual_count == 320),
    ("KPIs loaded", kpi_count == 34),
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
    print("\n🎉 Customer 20 test environment is ready!")
    print("\n📋 Next Steps:")
    print("  1. Test Signal Analyst with Customer 20 accounts")
    print("  2. Validate query patterns and accuracy")
    print("  3. Monitor performance metrics")
    print("  4. Compare results vs. other customers\n")
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
        print("  1. Re-run data loader: python3 scripts/02_load_customer20_data.py")
    if not all_ready:
        print("  2. Check environment variables and connections")
    if COLLECTION_NAME not in collection_names:
        print("  3. Run embedding script: python3 scripts/03_embed_signals_qdrant.py")
    print()
