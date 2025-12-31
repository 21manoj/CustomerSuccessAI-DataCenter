# Current Embeddings & Vector DB Architecture

**Last Updated**: December 18, 2025

## Executive Summary

The CS Platform currently uses a **hybrid architecture** with **two primary approaches**:

1. **Active Default (Production)**: `direct_rag_api.py` - **NO vector database, NO embeddings** - Direct database queries
2. **Available Options**: Multiple vector-based RAG systems available for selection (Qdrant, FAISS, etc.)

---

## 🎯 Active/Default System: Direct RAG (No Vector DB)

### Architecture
- **System**: `direct_rag_api.py`
- **Vector Database**: ❌ **None**
- **Embeddings Model**: ❌ **None**
- **Storage**: PostgreSQL/SQLite database (direct queries)
- **Default Endpoint**: `/api/direct-rag/query`
- **Status**: ✅ **Production Active**

### How It Works

```python
# No embeddings, no vector search
def direct_query():
    # 1. Query database directly
    kpis = KPI.query.join(KPIUpload).filter(
        KPIUpload.customer_id == customer_id
    ).all()
    accounts = Account.query.filter_by(
        customer_id=customer_id
    ).all()
    
    # 2. Prepare context as plain text
    context = format_data_as_text(kpis, accounts)
    
    # 3. Send to OpenAI GPT-4
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[...context...]
    )
```

### Characteristics

| Aspect | Details |
|--------|---------|
| **Vector Search** | No - uses direct SQL queries |
| **Embeddings** | No - data sent as structured text |
| **Data Freshness** | ✅ Real-time (always current) |
| **Rebuild Required** | ❌ No - automatic updates |
| **Performance** | ~500-1000ms per query |
| **Scalability** | Good for up to 1000 accounts |
| **Storage Overhead** | Minimal (no vector indexes) |

### Advantages
- ✅ **Zero rebuilds needed** - Data automatically available
- ✅ **Always fresh** - Real-time database queries
- ✅ **Simple operations** - No vector index maintenance
- ✅ **Lower latency** - No embedding generation overhead

### Limitations
- ⚠️ **No semantic search** - Relies on OpenAI to understand context
- ⚠️ **Context size limited** - All data sent in each request
- ⚠️ **Higher token costs** - More data sent to OpenAI

---

## 📚 Available Vector-Based Systems

Although not the default, the platform includes multiple vector-based RAG systems that can be selected via the UI:

### Option 1: Qdrant Vector Database

**System**: `enhanced_rag_qdrant.py`  
**Endpoint**: `/api/rag-qdrant/query`  
**Storage**: Qdrant (local file-based or server)

#### Architecture
```python
# Embeddings Model
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
embedding_dimension = 384

# Vector Database
qdrant_client = QdrantClient(
    host='localhost',  # or local file path
    port=6333
)
collection_name = 'kpi_dashboard_vectors'
```

#### Characteristics
| Aspect | Details |
|--------|---------|
| **Embedding Model** | `all-MiniLM-L6-v2` (SentenceTransformer) |
| **Embedding Dimension** | 384 |
| **Vector Database** | Qdrant |
| **Similarity Metric** | Cosine (default) |
| **Top-K Results** | 10 (configurable) |
| **Rebuild Required** | ✅ Yes - after data updates |
| **Storage** | Local files or Qdrant server |

#### Usage Flow
```
1. Build Knowledge Base (manual)
   → Generate embeddings for all KPIs/Accounts
   → Store vectors in Qdrant
   
2. Query
   → Generate query embedding
   → Vector similarity search in Qdrant
   → Retrieve top-K relevant documents
   → Send to OpenAI with context
```

---

### Option 2: FAISS Vector Database

**System**: `enhanced_rag_openai.py`  
**Endpoint**: `/api/rag-openai/query`  
**Storage**: FAISS index files

#### Architecture
```python
# Embeddings Model
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
dimension = 384

# Vector Database
faiss_index = faiss.IndexFlatL2(384)  # L2 distance
# or
faiss_index = faiss.IndexFlatIP(384)  # Inner product
```

#### Characteristics
| Aspect | Details |
|--------|---------|
| **Embedding Model** | `all-MiniLM-L6-v2` (SentenceTransformer) |
| **Embedding Dimension** | 384 |
| **Vector Database** | FAISS (Facebook AI Similarity Search) |
| **Similarity Metric** | L2 or Inner Product |
| **Index Type** | Flat (exact search) or IVF (approximate) |
| **Rebuild Required** | ✅ Yes - after data updates |
| **Storage** | Local `.index` files |

---

### Option 3: In-Memory Vectors

**System**: `working_rag_system.py`  
**Endpoint**: `/api/rag-working/query`  
**Storage**: Python lists (in-memory)

#### Architecture
```python
# Embeddings Model
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
embedding_dimension = 384

# Storage
self.vectors = []  # List of numpy arrays
self.data = []     # List of documents
```

#### Characteristics
| Aspect | Details |
|--------|---------|
| **Embedding Model** | `all-MiniLM-L6-v2` (SentenceTransformer) |
| **Embedding Dimension** | 384 |
| **Vector Database** | In-memory Python lists |
| **Similarity Metric** | Cosine (manual calculation) |
| **Rebuild Required** | ✅ Yes - on server restart |
| **Storage** | RAM only (lost on restart) |

---

### Option 4: Temporal Analysis (Qdrant)

**System**: `enhanced_rag_temporal.py`  
**Endpoint**: `/api/rag-temporal/query`  
**Storage**: Qdrant (time-series optimized)

#### Architecture
- Same embedding model as standard Qdrant
- Optimized for time-series data queries
- Stores temporal patterns and seasonality

---

### Option 5: Historical Analysis (Qdrant)

**System**: `enhanced_rag_historical.py`  
**Endpoint**: `/api/rag-historical/query`  
**Storage**: Qdrant (historical data)

#### Architecture
- Same embedding model as standard Qdrant
- Optimized for historical trend analysis
- Stores historical KPI and account data

---

## 🔧 Embedding Model Details

### Model: `all-MiniLM-L6-v2`

**Used in**: All vector-based RAG systems

| Property | Value |
|----------|-------|
| **Library** | SentenceTransformers |
| **Model Name** | `sentence-transformers/all-MiniLM-L6-v2` |
| **Dimensions** | 384 |
| **Language** | English |
| **Type** | BERT-based transformer |
| **Speed** | Fast (~50ms per embedding) |
| **Quality** | Good balance of speed/quality |
| **License** | Apache 2.0 |
| **Size** | ~80MB |

### Usage Example
```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L6-v2')
embedding = model.encode("Which accounts have highest revenue?")
# Returns: numpy array of shape (384,)
```

---

## 🗂️ Vector Database Comparison

| System | Vector DB | Embeddings | Rebuild Needed | Use Case |
|--------|-----------|------------|----------------|----------|
| **Direct RAG** | ❌ None | ❌ None | ❌ No | **Production default** - Real-time queries |
| **Qdrant RAG** | ✅ Qdrant | ✅ all-MiniLM-L6-v2 | ✅ Yes | Semantic search, large datasets |
| **FAISS RAG** | ✅ FAISS | ✅ all-MiniLM-L6-v2 | ✅ Yes | Fast similarity search |
| **Working RAG** | ✅ In-Memory | ✅ all-MiniLM-L6-v2 | ✅ Yes | Testing, small datasets |
| **Temporal RAG** | ✅ Qdrant | ✅ all-MiniLM-L6-v2 | ✅ Yes | Time-series analysis |
| **Historical RAG** | ✅ Qdrant | ✅ all-MiniLM-L6-v2 | ✅ Yes | Historical trends |

---

## 🎛️ Frontend Selection

Users can select the vector DB system via the RAG Analysis UI:

```typescript
// RAGAnalysis.tsx
const [vectorDb, setVectorDb] = useState<
  'working' | 'faiss' | 'qdrant' | 'historical' | 'temporal'
>('working');  // Default: 'working' = direct_rag_api

// Mapping
'working' → /api/direct-rag/query  (No vector DB)
'faiss'   → /api/rag-openai/query  (FAISS)
'qdrant'  → /api/rag-qdrant/query  (Qdrant)
'historical' → /api/rag-historical/query
'temporal'   → /api/rag-temporal/query
```

---

## 📊 Current Data Flow

### Direct RAG (Default)
```
User Query
    ↓
[direct_rag_api.py]
    ↓
SQL Query → PostgreSQL/SQLite
    ↓
Format as Text Context
    ↓
OpenAI GPT-4 API
    ↓
Response
```

### Vector-Based RAG (Optional)
```
User Query
    ↓
Generate Embedding (all-MiniLM-L6-v2)
    ↓
Vector Similarity Search (Qdrant/FAISS)
    ↓
Retrieve Top-K Documents
    ↓
Format as Context
    ↓
OpenAI GPT-4 API
    ↓
Response
```

---

## 🔄 Knowledge Base Rebuild

### Direct RAG
- ❌ **No rebuild needed**
- ✅ Data automatically available from database
- ✅ Real-time updates

### Vector-Based Systems
- ✅ **Rebuild required** after:
  - New data uploads
  - KPI updates
  - Account changes
- ⏱️ Rebuild time: ~1-5 minutes (depends on data size)
- 🔧 Manual trigger via UI or API

---

## 🚀 Performance Characteristics

| System | Query Latency | Index Size | Rebuild Time | Max Accounts |
|--------|---------------|------------|--------------|--------------|
| **Direct RAG** | 500-1000ms | 0 MB | 0 seconds | ~1000 |
| **Qdrant** | 200-500ms | ~10-50 MB | 1-3 min | ~10,000+ |
| **FAISS** | 100-300ms | ~5-20 MB | 30s-2 min | ~10,000+ |
| **In-Memory** | 50-200ms | RAM only | 10-30s | ~1,000 |

---

## 💡 Recommendations

### For Production Use
✅ **Use Direct RAG** (current default)
- Zero maintenance
- Always fresh data
- Good enough for most queries
- Lower operational complexity

### For Advanced Use Cases
Consider vector-based systems if:
- ⚡ Need sub-200ms query latency
- 🔍 Need semantic search capabilities
- 📈 Have >1000 accounts per customer
- 🎯 Want to optimize OpenAI token costs

---

## 📝 Summary

**Current Production Architecture**:
- **No vector database** - Direct database queries
- **No embeddings** - Plain text context to OpenAI
- **Real-time data** - Always current
- **Zero rebuilds** - Automatic updates

**Available but Optional**:
- Multiple vector DB options (Qdrant, FAISS, In-Memory)
- Consistent embedding model: `all-MiniLM-L6-v2` (384-dim)
- User-selectable via frontend UI

