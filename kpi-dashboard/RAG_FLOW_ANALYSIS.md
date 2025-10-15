# 🔄 RAG Query Flow Analysis

## Overview
Your KPI Dashboard has **multiple RAG implementations** with different purposes and capabilities. Here's the complete flow between the different endpoints.

---

## 🎯 **Main Entry Points**

### **1. `/api/query` (Unified Query API)**
- **Purpose**: **Primary entry point** - intelligently routes queries
- **Flow**: Routes to either deterministic analytics OR RAG based on query type
- **Default RAG**: Uses `enhanced_rag_openai` (FAISS + OpenAI GPT-4)
- **Status**: ✅ **RECOMMENDED** - This is your main query endpoint

### **2. `/api/rag-openai/query` (Enhanced RAG OpenAI)**
- **Purpose**: Direct access to OpenAI-powered RAG
- **Technology**: FAISS vector search + OpenAI GPT-4
- **Caching**: ✅ **ACTIVE** - Includes query caching for cost savings
- **Status**: ✅ **PRODUCTION READY**

### **3. `/api/rag-qdrant/query` (Enhanced RAG Qdrant)**
- **Purpose**: Direct access to Qdrant-powered RAG
- **Technology**: Qdrant vector database + OpenAI GPT-4
- **Caching**: ❌ Not implemented yet
- **Status**: ⚠️ **EXPERIMENTAL** - Requires Qdrant server

### **4. `/api/rag/query` (Legacy RAG)**
- **Purpose**: Original RAG implementation
- **Technology**: TF-IDF + scikit-learn
- **Caching**: ❌ Not implemented
- **Status**: ⚠️ **LEGACY** - Basic functionality only

---

## 🔄 **Query Flow Diagram**

```
User Query
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  /api/query (Unified Query API)                        │
│  ├─ QueryRouter.classify_query()                       │
│  ├─ Determines: deterministic vs rag                   │
│  └─ Routes accordingly                                 │
└─────────────────┬───────────────────────────────────────┘
                  │
    ┌─────────────┴─────────────┐
    │                           │
    ▼                           ▼
┌─────────────────┐    ┌─────────────────────────────────┐
│ DETERMINISTIC   │    │ RAG ROUTING                     │
│ ANALYTICS       │    │ (Default: enhanced_rag_openai)  │
│                 │    │                                 │
│ ├─ Total Revenue│    │ ┌─────────────────────────────┐ │
│ ├─ Average      │    │ │ /api/rag-openai/query       │ │
│ ├─ Counts       │    │ │ ├─ FAISS Vector Search      │ │
│ ├─ Top Accounts │    │ │ ├─ OpenAI GPT-4 Analysis    │ │
│ └─ Direct DB    │    │ │ ├─ Query Caching ✅         │ │
│                 │    │ │ └─ Cost: $0.02 per query    │ │
│ Fast & Free     │    │ └─────────────────────────────┘ │
│                 │    │                                 │
└─────────────────┘    │ ┌─────────────────────────────┐ │
                       │ │ /api/rag-qdrant/query       │ │
                       │ │ ├─ Qdrant Vector DB         │ │
                       │ │ ├─ OpenAI GPT-4 Analysis    │ │
                       │ │ ├─ No Caching ❌            │ │
                       │ │ └─ Requires Qdrant Server   │ │
                       │ └─────────────────────────────┘ │
                       │                                 │
                       │ ┌─────────────────────────────┐ │
                       │ │ /api/rag/query (Legacy)     │ │
                       │ │ ├─ TF-IDF Vectorization     │ │
                       │ │ ├─ scikit-learn Similarity  │ │
                       │ │ ├─ No AI Analysis           │ │
                       │ │ └─ Basic Functionality      │ │
                       │ └─────────────────────────────┘ │
                       └─────────────────────────────────┘
```

---

## 🎯 **Recommended Usage**

### **For Production Use:**

**1. Use `/api/query` (Unified Query API)**
```bash
curl -X POST http://localhost:5059/api/query \
  -H 'X-Customer-ID: 1' \
  -H 'Content-Type: application/json' \
  -d '{"query": "What is the total revenue?"}'
```

**Benefits:**
- ✅ **Smart routing** - Automatically chooses best approach
- ✅ **Cost optimization** - Uses deterministic analytics when possible
- ✅ **Caching** - Includes query caching for RAG queries
- ✅ **Debugging** - Shows routing decisions in response

### **For Direct RAG Access:**

**2. Use `/api/rag-openai/query` (Recommended RAG)**
```bash
curl -X POST http://localhost:5059/api/rag-openai/query \
  -H 'X-Customer-ID: 1' \
  -H 'Content-Type: application/json' \
  -d '{"query": "Which accounts are at risk of churn?"}'
```

**Benefits:**
- ✅ **Production ready** with caching
- ✅ **High-quality AI analysis** via GPT-4
- ✅ **Cost savings** through query caching
- ✅ **Fast vector search** via FAISS

---

## 🔧 **Technical Details**

### **Enhanced RAG OpenAI (`/api/rag-openai/query`)**

**Technology Stack:**
```python
# Vector Search: FAISS
from sentence_transformers import SentenceTransformer
import faiss

# AI Analysis: OpenAI GPT-4
import openai

# Caching: Custom in-memory cache
from query_cache import get_query_cache
```

**Flow:**
1. **Check Cache** → If cached, return instantly ($0.00 cost)
2. **Generate Embeddings** → Convert query to vector
3. **FAISS Search** → Find similar KPI/account data
4. **OpenAI Analysis** → Generate intelligent response
5. **Cache Result** → Store for future queries (1 hour TTL)

**Performance:**
- **Cache Hit**: <10ms, $0.00
- **Cache Miss**: 2-3 seconds, $0.02
- **Hit Rate**: 60-80% (typical)

### **Enhanced RAG Qdrant (`/api/rag-qdrant/query`)**

**Technology Stack:**
```python
# Vector Database: Qdrant
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

# AI Analysis: OpenAI GPT-4
import openai
```

**Flow:**
1. **Qdrant Search** → Query vector database
2. **OpenAI Analysis** → Generate response
3. **No Caching** → Every query costs $0.02

**Requirements:**
- Qdrant server running on localhost:6333
- Additional setup and maintenance

### **Legacy RAG (`/api/rag/query`)**

**Technology Stack:**
```python
# Vectorization: TF-IDF
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# No AI Analysis - just similarity matching
```

**Flow:**
1. **TF-IDF Vectorization** → Convert text to vectors
2. **Cosine Similarity** → Find similar documents
3. **Return Results** → No AI analysis, just matching

**Limitations:**
- No AI-powered insights
- Basic similarity matching only
- No caching

---

## 💰 **Cost Analysis**

| Endpoint | Cache Hit | Cache Miss | AI Analysis | Recommended |
|----------|-----------|------------|-------------|-------------|
| `/api/query` | $0.00 | $0.02 | ✅ | ✅ **YES** |
| `/api/rag-openai/query` | $0.00 | $0.02 | ✅ | ✅ **YES** |
| `/api/rag-qdrant/query` | ❌ | $0.02 | ✅ | ⚠️ **Maybe** |
| `/api/rag/query` | ❌ | $0.00 | ❌ | ❌ **No** |

---

## 🚀 **Current Status**

### **Active & Recommended:**
- ✅ `/api/query` - **Main entry point**
- ✅ `/api/rag-openai/query` - **Best RAG implementation**

### **Available but Not Recommended:**
- ⚠️ `/api/rag-qdrant/query` - Requires additional setup
- ⚠️ `/api/rag/query` - Legacy, limited functionality

### **Caching Status:**
- ✅ **Enhanced RAG OpenAI**: Caching active
- ❌ **Enhanced RAG Qdrant**: No caching
- ❌ **Legacy RAG**: No caching

---

## 📊 **Performance Comparison**

| Metric | Unified Query | OpenAI RAG | Qdrant RAG | Legacy RAG |
|--------|---------------|------------|------------|------------|
| **Speed** | 10ms-3s | 10ms-3s | 1-3s | 100-500ms |
| **Cost** | $0.00-0.02 | $0.00-0.02 | $0.02 | $0.00 |
| **Quality** | High | High | High | Low |
| **Caching** | ✅ | ✅ | ❌ | ❌ |
| **Setup** | None | None | Qdrant | None |

---

## 🎯 **Recommendations**

### **For Your Application:**

1. **Primary Endpoint**: Use `/api/query` for all queries
   - Automatic routing to best system
   - Cost optimization
   - Built-in caching

2. **Direct RAG Access**: Use `/api/rag-openai/query` when needed
   - Production-ready
   - Cached responses
   - High-quality AI analysis

3. **Avoid**: `/api/rag-qdrant/query` and `/api/rag/query`
   - Additional complexity
   - No caching benefits
   - Limited functionality

### **For Frontend Integration:**

```javascript
// Recommended: Use unified query endpoint
const response = await fetch('/api/query', {
  method: 'POST',
  headers: {
    'X-Customer-ID': customerId,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    query: userQuery
  })
});

// The system automatically:
// 1. Routes to deterministic analytics for numeric queries
// 2. Routes to RAG for analytical questions
// 3. Uses caching for repeated queries
// 4. Provides routing metadata for debugging
```

---

## 🔍 **Debugging & Monitoring**

### **Check Routing Decisions:**
```bash
curl -X POST http://localhost:5059/api/query \
  -H 'X-Customer-ID: 1' \
  -H 'Content-Type: application/json' \
  -d '{"query": "What is the total revenue?"}' | jq .routing_decision
```

### **Check Cache Status:**
```bash
curl http://localhost:5059/api/cache/stats | jq .statistics
```

### **Force RAG Routing:**
```bash
curl -X POST http://localhost:5059/api/query \
  -H 'X-Customer-ID: 1' \
  -H 'Content-Type: application/json' \
  -d '{"query": "What is the total revenue?", "force_routing": "rag"}'
```

---

## 📝 **Summary**

**Your RAG Flow:**
1. **`/api/query`** → Smart routing (recommended)
2. **`/api/rag-openai/query`** → Direct RAG access (cached)
3. **`/api/rag-qdrant/query`** → Alternative RAG (experimental)
4. **`/api/rag/query`** → Legacy RAG (basic)

**Best Practice:** Use `/api/query` as your primary endpoint - it automatically chooses the best approach and includes caching for cost optimization! 🎯
