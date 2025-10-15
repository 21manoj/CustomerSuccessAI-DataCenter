# 🔧 Quick Integration Code

## Add to `backend/app.py`

### Step 1: Add Imports (after line 46)

Add these two lines after the existing imports:

```python
from best_practices_api import best_practices_api

# ADD THESE TWO LINES:
from analytics_api import analytics_api
from unified_query_api import unified_query_api
```

### Step 2: Register Blueprints (after line 94)

Add these two lines after the existing blueprint registrations:

```python
app.register_blueprint(best_practices_api)

# ADD THESE TWO LINES:
app.register_blueprint(analytics_api)
app.register_blueprint(unified_query_api)

@app.route('/')
def home():
```

---

## Complete Diff

```diff
# backend/app.py

from financial_projections_api import financial_projections_api
from best_practices_api import best_practices_api
+ from analytics_api import analytics_api
+ from unified_query_api import unified_query_api

# ... (other code)

app.register_blueprint(financial_projections_api)
app.register_blueprint(best_practices_api)
+ app.register_blueprint(analytics_api)
+ app.register_blueprint(unified_query_api)

@app.route('/')
def home():
```

---

## Verification Commands

### 1. Start Backend
```bash
cd /Users/manojgupta/kpi-dashboard/backend
python3 app.py
```

### 2. Test Endpoints

#### Test Analytics API
```bash
# Total revenue
curl -X GET 'http://localhost:5054/api/analytics/revenue/total' \
  -H 'X-Customer-ID: 6'

# Account count
curl -X GET 'http://localhost:5054/api/analytics/accounts/count' \
  -H 'X-Customer-ID: 6'
```

#### Test Unified Query API
```bash
# Deterministic query
curl -X POST 'http://localhost:5054/api/query' \
  -H 'X-Customer-ID: 6' \
  -H 'Content-Type: application/json' \
  -d '{"query": "What is the total revenue?"}'

# RAG query  
curl -X POST 'http://localhost:5054/api/query' \
  -H 'X-Customer-ID: 6' \
  -H 'Content-Type: application/json' \
  -d '{"query": "Why is revenue declining?"}'

# Test routing (no execution)
curl -X POST 'http://localhost:5054/api/query/test' \
  -H 'Content-Type: application/json' \
  -d '{"query": "How many accounts do we have?"}'
```

---

## AWS Deployment

Once tested locally, deploy to AWS:

```bash
# From project root
./build-production.sh

# Or manually
docker build -f Dockerfile.production -t kpi-dashboard:latest .
```

---

## Expected Output

### Analytics API Response
```json
{
  "query_type": "revenue_total",
  "customer_id": 6,
  "result": {
    "total_revenue": 43700000.0,
    "formatted": "$43,700,000.00"
  },
  "metadata": {
    "source": "deterministic_analytics",
    "calculation": "SUM(revenue)",
    "precision": "exact"
  }
}
```

### Unified Query API Response (Deterministic)
```json
{
  "original_query": "What is the total revenue?",
  "answer": "The total revenue is $43,700,000.00.",
  "result": {
    "total_revenue": 43700000.0,
    "formatted": "$43,700,000.00"
  },
  "routing_decision": {
    "routed_to": "deterministic",
    "confidence": 1.0,
    "query_type": "sum",
    "reason": "Routed to deterministic analytics...",
    "scores": {"deterministic": 11.0, "rag": 0.0}
  },
  "metadata": {
    "source": "deterministic_analytics",
    "precision": "exact",
    "execution_time_ms": "<200",
    "cost": "$0.00"
  }
}
```

### Test Routing Response
```json
{
  "query": "How many accounts do we have?",
  "routing_decision": {
    "routed_to": "deterministic",
    "confidence": 1.0,
    "query_type": "count",
    "extracted_params": {"operation": "count"},
    "scores": {"deterministic": 8.0, "rag": 0.0},
    "reason": "Routed to deterministic analytics because..."
  },
  "metadata": {
    "test_mode": true,
    "execution_skipped": true
  }
}
```

---

## Quick Reference

### Deterministic Queries → Analytics API
- "What is the total revenue?"
- "How many accounts do we have?"
- "Show me the top 5 accounts"
- "What is the average revenue?"
- "List all accounts in Healthcare"

### RAG Queries → AI Analysis
- "Why is revenue declining?"
- "How can we improve satisfaction?"
- "What are common traits of top performers?"
- "Which accounts should we focus on?"
- "Analyze trends in engagement"

---

That's it! Just add 4 lines to `app.py` and you're ready to go! 🚀

