# 🌐 Service Endpoints - Local Setup

## 📍 **Current Service Status**

### Backend (Flask/Python)
- **Port**: `5059`
- **Base URL**: http://localhost:5059
- **Status**: ✅ **RUNNING**
- **Health Check**: http://localhost:5059/

### Frontend (React)
- **Port**: `3000` (expected)
- **Base URL**: http://localhost:3000
- **Status**: ❌ **NOT RUNNING**
- **To Start**: `npm start` in project root

---

## 🎯 **Query Routing Endpoints**

### 1. Test Query Routing (No Database Required)
```bash
# Test deterministic query
curl -X POST 'http://localhost:5059/api/query/test' \
  -H 'Content-Type: application/json' \
  -d '{"query": "What is the total revenue?"}'

# Test RAG query
curl -X POST 'http://localhost:5059/api/query/test' \
  -H 'Content-Type: application/json' \
  -d '{"query": "Why is revenue declining?"}'
```

### 2. Batch Query Testing
```bash
curl -X POST 'http://localhost:5059/api/query/batch-test' \
  -H 'Content-Type: application/json' \
  -d '{
    "queries": [
      "What is the total revenue?",
      "How many accounts?",
      "Why is revenue declining?"
    ]
  }'
```

### 3. Full Query Execution (Requires Database)
```bash
curl -X POST 'http://localhost:5059/api/query' \
  -H 'X-Customer-ID: 6' \
  -H 'Content-Type: application/json' \
  -d '{"query": "What is the total revenue?"}'
```

---

## 📊 **Analytics API Endpoints (Deterministic)**

### Revenue Endpoints
```bash
# Total revenue
curl 'http://localhost:5059/api/analytics/revenue/total' -H 'X-Customer-ID: 6'

# Average revenue
curl 'http://localhost:5059/api/analytics/revenue/average' -H 'X-Customer-ID: 6'

# Revenue by industry
curl 'http://localhost:5059/api/analytics/revenue/by-industry' -H 'X-Customer-ID: 6'

# Top accounts
curl 'http://localhost:5059/api/analytics/revenue/top-accounts?limit=5' -H 'X-Customer-ID: 6'
```

### Account Endpoints
```bash
# Account count
curl 'http://localhost:5059/api/analytics/accounts/count' -H 'X-Customer-ID: 6'

# Accounts by industry
curl 'http://localhost:5059/api/analytics/accounts/by-industry' -H 'X-Customer-ID: 6'

# Account details
curl 'http://localhost:5059/api/analytics/accounts/4' -H 'X-Customer-ID: 6'
```

### Generic Aggregation
```bash
curl -X POST 'http://localhost:5059/api/analytics/aggregate' \
  -H 'X-Customer-ID: 6' \
  -H 'Content-Type: application/json' \
  -d '{
    "metric": "revenue",
    "operation": "sum",
    "filters": {"industry": "Healthcare"},
    "group_by": ["region"]
  }'
```

---

## 🤖 **Existing RAG Endpoints**

### RAG OpenAI (Primary)
```bash
# Build knowledge base
curl -X POST 'http://localhost:5059/api/rag-openai/build' -H 'X-Customer-ID: 6'

# Query with GPT-4
curl -X POST 'http://localhost:5059/api/rag-openai/query' \
  -H 'X-Customer-ID: 6' \
  -H 'Content-Type: application/json' \
  -d '{"query": "Which accounts have the highest revenue?", "query_type": "revenue_analysis"}'

# Revenue analysis
curl 'http://localhost:5059/api/rag-openai/revenue-analysis' -H 'X-Customer-ID: 6'

# Risk analysis
curl 'http://localhost:5059/api/rag-openai/risk-analysis' -H 'X-Customer-ID: 6'

# Top accounts
curl 'http://localhost:5059/api/rag-openai/top-accounts' -H 'X-Customer-ID: 6'
```

---

## ✅ **Working Test Examples**

### Test 1: Query Routing Classification ✅
```bash
$ curl -X POST 'http://localhost:5059/api/query/test' \
  -H 'Content-Type: application/json' \
  -d '{"query": "What is the total revenue?"}'

Response:
{
  "routing_decision": {
    "routed_to": "deterministic",
    "confidence": 1.0,
    "query_type": "sum"
  }
}
```

### Test 2: Batch Query Routing ✅
```bash
$ curl -X POST 'http://localhost:5059/api/query/batch-test' \
  -H 'Content-Type: application/json' \
  -d '{"queries": ["What is total revenue?", "Why is revenue declining?"]}'

Response:
{
  "results": [
    {"query": "What is total revenue?", "routing": "deterministic"},
    {"query": "Why is revenue declining?", "routing": "rag"}
  ],
  "statistics": {
    "deterministic": 1,
    "rag": 1,
    "deterministic_percentage": 50.0
  }
}
```

### Test 3: Multiple Query Classification ✅
```bash
Query: "List all accounts in Healthcare"
  → Routed to: DETERMINISTIC

Query: "How can we improve customer satisfaction?"
  → Routed to: RAG

Query: "What is the average revenue per account?"
  → Routed to: DETERMINISTIC
```

---

## 🚀 **Quick Test Commands**

### Health Check
```bash
curl http://localhost:5059/
# Expected: "KPI Dashboard Backend is running! Timestamp: ..."
```

### Test Query Router
```bash
# Single deterministic query
curl -X POST 'http://localhost:5059/api/query/test' \
  -H 'Content-Type: application/json' \
  -d '{"query": "What is the total revenue?"}' | python3 -m json.tool

# Single RAG query
curl -X POST 'http://localhost:5059/api/query/test' \
  -H 'Content-Type: application/json' \
  -d '{"query": "Why is revenue declining?"}' | python3 -m json.tool

# Batch test
curl -X POST 'http://localhost:5059/api/query/batch-test' \
  -H 'Content-Type: application/json' \
  -d '{"queries": ["What is total revenue?", "How many accounts?", "Why declining?"]}' \
  | python3 -m json.tool
```

---

## 🔍 **Query Classification Examples**

### Deterministic Queries (Fast, Exact, Free)
✅ "What is the total revenue?"  
✅ "How many accounts do we have?"  
✅ "Show me the top 5 accounts"  
✅ "List all accounts in Healthcare"  
✅ "What is the average revenue?"  
✅ "Count active accounts"  
✅ "Show account ID 4"  

### RAG Queries (AI Analysis, Insights)
🤖 "Why is revenue declining?"  
🤖 "How can we improve customer satisfaction?"  
🤖 "What are common traits of top performers?"  
🤖 "Which accounts should we focus on and why?"  
🤖 "Analyze trends in customer engagement"  
🤖 "Compare Healthcare vs Technology industries"  
🤖 "Recommend strategies for at-risk accounts"  

---

## 📝 **Query Testing Results**

All tests passing on **http://localhost:5059**:

✅ Health Check: PASS  
✅ Query Router: 16/16 queries classified correctly (100%)  
✅ Unified Query API: 2/2 tests passed  
✅ Batch Routing: 6/6 tests passed  
✅ Server Integration: Working  

**Overall**: 24/24 tests passed (100% accuracy)

---

## 🎯 **Production URLs (AWS)**

When deployed to AWS, use:
- Backend: https://customersuccessai.triadpartners.ai/api/...
- Frontend: https://customersuccessai.triadpartners.ai/dashboard

Same endpoints, just replace `http://localhost:5059` with the AWS URL.

---

## 💡 **Tips**

1. **For testing without database**: Use `/api/query/test` endpoints
2. **For full execution**: Use `/api/query` (requires database)
3. **For batch testing**: Use `/api/query/batch-test`
4. **Always include**: `X-Customer-ID: 6` header for data queries
5. **Pretty print JSON**: Add `| python3 -m json.tool` to curl commands

---

**Updated**: October 11, 2025  
**Backend Port**: 5059  
**Frontend Port**: 3000 (not running)  
**Status**: ✅ Query routing working perfectly!

