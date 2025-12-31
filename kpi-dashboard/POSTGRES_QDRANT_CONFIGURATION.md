# PostgreSQL + Qdrant Configuration

**Date**: December 18, 2025  
**Status**: ✅ Configured

## Overview

The system has been configured to:
1. **Always use PostgreSQL** (SQLite fallbacks removed)
2. **Always use Qdrant VDB** for RAG queries with OpenAI text-embedding-3-large embeddings
3. **Optimize database indexes** for faster query performance

---

## 1. PostgreSQL Enforcement

### Changes Made

#### `app.py`
- **Before**: Had SQLite fallbacks if `DATABASE_URL` was not set
- **After**: **Requires** `DATABASE_URL` environment variable
- **Validation**: Checks that `DATABASE_URL` starts with `postgresql://` or `postgres://`
- **Error**: Raises `ValueError` if PostgreSQL connection string is not provided

#### `config.py`
- **Before**: Defaulted to `sqlite:///instance/kpi_dashboard.db` if `DATABASE_URL` was not set
- **After**: **Requires** `DATABASE_URL` environment variable
- **Validation**: Enforces PostgreSQL connection string format

### Required Environment Variable

```bash
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
```

### Error Messages

If `DATABASE_URL` is not set or not PostgreSQL:
```
❌ ERROR: DATABASE_URL environment variable is required.
Please set DATABASE_URL to a PostgreSQL connection string.
Example: postgresql://user:password@localhost:5432/dbname
```

---

## 2. Qdrant VDB as Default

### Changes Made

#### `unified_query_api.py`
- **Before**: Used `enhanced_rag_openai` (FAISS-based system)
- **After**: Uses `enhanced_rag_qdrant` (Qdrant VDB with OpenAI embeddings)
- **Default**: All RAG queries now route to Qdrant VDB
- **Embedding Model**: OpenAI `text-embedding-3-large` (3072 dimensions)

### RAG Query Flow

1. Query comes to `/api/query`
2. `QueryRouter` classifies query as 'deterministic' or 'rag'
3. If 'rag', routes to `_execute_rag_query()`
4. Uses `get_qdrant_rag_system(customer_id)` from `enhanced_rag_qdrant`
5. Executes query with Qdrant vector similarity search
6. Returns results with Qdrant metadata

### Metadata

All RAG responses now include:
```json
{
  "metadata": {
    "source": "qdrant_rag_system",
    "vector_db": "Qdrant",
    "embedding_model": "text-embedding-3-large",
    "precision": "ai_generated",
    "execution_time_ms": "1000-5000",
    "cost": "$0.01-0.05",
    "ai_model": "GPT-4"
  }
}
```

---

## 3. Database Indexes for Performance

### New Indexes Added

#### Account Table
- `customer_id` - Indexed (foreign key lookups)
- `account_name` - Indexed (name searches)
- `account_status` - Indexed (status filtering)
- `industry` - Indexed (industry filtering)
- `region` - Indexed (region filtering)
- `external_account_id` - Indexed (external ID lookups)
- `created_at` - Indexed (time-based queries)
- **Composite indexes**:
  - `idx_account_customer_status` (`customer_id`, `account_status`)
  - `idx_account_customer_industry` (`customer_id`, `industry`)
  - `idx_account_customer_region` (`customer_id`, `region`)

#### KPI Table
- `upload_id` - Indexed (upload lookups)
- `account_id` - Indexed (account filtering)
- `product_id` - Indexed (product filtering)
- `aggregation_type` - Indexed (aggregation filtering)
- `category` - Indexed (category filtering)
- `health_score_component` - Indexed (health score queries)
- `kpi_parameter` - Indexed (parameter searches)
- `impact_level` - Indexed (impact filtering)
- `last_edited_at` - Indexed (time-based queries)
- **Composite indexes**:
  - `idx_kpi_account_category` (`account_id`, `category`)
  - `idx_kpi_account_parameter` (`account_id`, `kpi_parameter`)
  - `idx_kpi_account_aggregation` (`account_id`, `aggregation_type`)
  - `idx_kpi_upload_account` (`upload_id`, `account_id`)

#### KPIUpload Table
- `customer_id` - Indexed (customer filtering)
- `account_id` - Indexed (account filtering)
- `user_id` - Indexed (user filtering)
- `uploaded_at` - Indexed (time-based queries)
- **Composite indexes**:
  - `idx_upload_customer_uploaded` (`customer_id`, `uploaded_at`)
  - `idx_upload_account_uploaded` (`account_id`, `uploaded_at`)

#### HealthTrend Table
- `account_id` - Indexed (account filtering)
- `customer_id` - Indexed (customer filtering)
- `month` - Indexed (month filtering)
- `year` - Indexed (year filtering)
- `created_at` - Indexed (time-based queries)
- **Composite indexes**:
  - `idx_health_trend_account_date` (`account_id`, `year`, `month`)
  - `idx_health_trend_customer_date` (`customer_id`, `year`, `month`)

#### KPITimeSeries Table
- `kpi_id` - Indexed (KPI filtering)
- `account_id` - Indexed (account filtering)
- `customer_id` - Indexed (customer filtering)
- `month` - Indexed (month filtering)
- `year` - Indexed (year filtering)
- `created_at` - Indexed (time-based queries)
- **Composite indexes**:
  - `idx_time_series_kpi_date` (`kpi_id`, `year`, `month`)
  - `idx_time_series_account_date` (`account_id`, `year`, `month`)
  - `idx_time_series_customer_date` (`customer_id`, `year`, `month`)

### Performance Benefits

These indexes will significantly improve query performance for:
- ✅ Customer-scoped queries (multi-tenant filtering)
- ✅ Account lookups and filtering
- ✅ KPI searches by parameter, category, or account
- ✅ Time-series queries (month/year filtering)
- ✅ Health score trend analysis
- ✅ Upload history queries

---

## Migration Steps

To apply these changes:

1. **Set DATABASE_URL** environment variable (if not already set):
   ```bash
   export DATABASE_URL=postgresql://user:password@localhost:5432/dbname
   ```

2. **Run database migrations** to create new indexes:
   ```bash
   cd kpi-dashboard/backend
   flask db migrate -m "Add performance indexes for accounts KPIs and related tables"
   flask db upgrade
   ```

3. **Restart the backend server**:
   ```bash
   python3 app.py
   ```

4. **Verify configuration**:
   - Check that server starts without SQLite fallback warnings
   - Verify Qdrant queries work via `/api/query` endpoint
   - Monitor query performance improvements

---

## Testing

### Verify PostgreSQL Enforcement

```bash
# Should fail if DATABASE_URL is not set
unset DATABASE_URL
python3 app.py
# Expected: ValueError with instructions to set DATABASE_URL

# Should fail if DATABASE_URL is not PostgreSQL
export DATABASE_URL=sqlite:///test.db
python3 app.py
# Expected: ValueError indicating PostgreSQL is required
```

### Verify Qdrant as Default

```python
# Test query routing
import requests
response = requests.post('http://localhost:8001/api/query', json={
    'query': 'What are the top performing accounts?'
}, headers={'X-Customer-ID': '1'})

data = response.json()
assert data['metadata']['vector_db'] == 'Qdrant'
assert data['metadata']['embedding_model'] == 'text-embedding-3-large'
```

### Verify Indexes

```sql
-- Check indexes on accounts table
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'accounts';

-- Check indexes on kpis table
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'kpis';

-- Check query plans for performance
EXPLAIN ANALYZE 
SELECT * FROM accounts WHERE customer_id = 1 AND account_status = 'active';
```

---

## Summary

✅ **PostgreSQL**: Now required, no SQLite fallbacks  
✅ **Qdrant VDB**: Default RAG system with OpenAI embeddings  
✅ **Database Indexes**: Comprehensive indexing for optimal performance  

The system is now configured for production-grade performance with PostgreSQL and Qdrant vector database.

