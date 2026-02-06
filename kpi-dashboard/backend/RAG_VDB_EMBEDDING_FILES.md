# RAG & Vector Database Embedding Files

**Date:** 2026-01-24  
**Purpose:** List of all files that process RAG (Retrieval-Augmented Generation) and VDB (Vector Database) embeddings

---

## 🎯 Core RAG Systems (Main Embedding Processors)

### 1. **Enhanced RAG with Qdrant (OpenAI Embeddings)**
**File:** `backend/enhanced_rag_qdrant.py`
- **Embedding Model:** OpenAI `text-embedding-3-large` (3072 dimensions)
- **Vector DB:** Qdrant Cloud
- **Key Method:** `_generate_embedding()` (line 111)
- **Purpose:** Main RAG system using OpenAI embeddings stored in Qdrant
- **Collection Format:** `kpi_dashboard_vectors_customer_{customer_id}`

### 2. **Enhanced RAG with OpenAI (FAISS)**
**File:** `backend/enhanced_rag_openai.py`
- **Embedding Model:** SentenceTransformer `all-MiniLM-L6-v2` (384 dimensions)
- **Vector DB:** FAISS (local file-based)
- **Purpose:** RAG system using local FAISS index with SentenceTransformer embeddings

### 3. **Enhanced RAG Temporal (Qdrant + SentenceTransformer)**
**File:** `backend/enhanced_rag_temporal.py`
- **Embedding Model:** SentenceTransformer `all-MiniLM-L6-v2` (384 dimensions)
- **Vector DB:** Qdrant Cloud
- **Purpose:** Temporal analysis with time-series data and monthly revenue tracking

### 4. **Enhanced RAG Historical (Qdrant + SentenceTransformer)**
**File:** `backend/enhanced_rag_historical.py`
- **Embedding Model:** SentenceTransformer `all-MiniLM-L6-v2` (384 dimensions)
- **Vector DB:** Qdrant Cloud
- **Purpose:** Historical data analysis with trends and temporal context

### 5. **Direct RAG (No Embeddings - Database-Driven)**
**File:** `backend/direct_rag_api.py`
- **Embedding Model:** None (database queries only)
- **Vector DB:** None
- **Purpose:** Current V3 system - queries database directly without embeddings
- **Note:** This is the active system that doesn't require embeddings

---

## 🔌 RAG API Endpoints

### Qdrant-Based APIs
- `backend/enhanced_rag_qdrant_api.py` - API wrapper for `enhanced_rag_qdrant.py`
- `backend/enhanced_rag_temporal_api.py` - API wrapper for `enhanced_rag_temporal.py`
- `backend/enhanced_rag_historical_api.py` - API wrapper for `enhanced_rag_historical.py`

### OpenAI/FAISS-Based APIs
- `backend/enhanced_rag_openai_api.py` - API wrapper for `enhanced_rag_openai.py`

### Other RAG APIs
- `backend/direct_rag_api.py` - Direct database queries (no embeddings)
- `backend/governance_rag_api.py` - Governance-focused RAG
- `backend/rag_api.py` - Legacy RAG API
- `backend/working_rag_api.py` - Working RAG implementation
- `backend/simple_rag_api.py` - Simple RAG implementation
- `backend/simple_working_rag_api.py` - Simple working RAG API

---

## 🤖 Signal Analyst (Embedding Processing)

### Core Files
- `backend/agents/qdrant_integration.py` - Qdrant integration for Signal Analyst
  - **Purpose:** Queries Qdrant collections for signals
  - **Collection:** `kpi_dashboard_vectors_customer_{customer_id}`
  - **Key Function:** `query_qdrant_for_signals()` (line 63)

### Signal Embedding Scripts (Per Customer)
**Location:** `backend/verticals/customer{ID}-dc2_s/scripts/`

**Common Scripts:**
- `03_embed_signals_qdrant.py` - Main embedding script (various versions)
- `03_embed_signals_qdrantv2.py` - Version 2
- `03_embed_signals_qdrantv3.py` - Version 3
- `03_embed_signals_qdrant_BATCHED.py` - Batched processing
- `03_embed_customer{ID}_OPENAI.py` - OpenAI embedding version
- `03_embed_signals_qdrant_OLD.py` - Legacy version

**Example Customer Scripts:**
- `backend/verticals/customer17-dc2_s/scripts/03_embed_signals_qdrant.py`
- `backend/verticals/customer120-dc2_s/scripts/03_embed_signals_qdrantv3.py`
- `backend/verticals/customer119-dc2_s/scripts/03_embed_signals_qdrantv3.py`
- (Many more customer-specific versions)

---

## 🔄 Migration & Utility Files

### Embedding Migration
- `backend/migrate_qdrant_to_openai_embeddings.py`
  - **Purpose:** Migrate Qdrant collections from SentenceTransformer to OpenAI embeddings
  - **Action:** Deletes old collections and rebuilds with OpenAI embeddings (3072 dims)

### Journey Embedding Scripts
**Location:** `backend/verticals/customer{ID}-dc2_s/journey/scripts/`

- `phase4/load_journey_to_qdrant_phase4.py` - Load journey data to Qdrant
- `qdrant_journey_schema.py` - Journey data schema for Qdrant
- `qdrant_field_registry.py` - Field registry for Qdrant collections

### Qdrant Collection Management
- `backend/verticals/customer{ID}-dc2_s/scripts/init_qdrant_collections.py` - Initialize collections
- `backend/verticals/customer{ID}-dc2_s/scripts/create_qdrant_indexes.py` - Create indexes

---

## 📊 Embedding Generation Methods

### OpenAI Embeddings (3072 dimensions)
**Used in:** `enhanced_rag_qdrant.py`
```python
def _generate_embedding(self, text: str, customer_id: int = None) -> List[float]:
    """Generate embedding using OpenAI's text-embedding-3-large model"""
    client = self._get_openai_client(customer_id)
    response = client.embeddings.create(
        model='text-embedding-3-large',
        input=text
    )
    return response.data[0].embedding
```

### SentenceTransformer Embeddings (384 dimensions)
**Used in:** `enhanced_rag_openai.py`, `enhanced_rag_temporal.py`, `enhanced_rag_historical.py`
```python
from sentence_transformers import SentenceTransformer
self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
embedding = self.embedding_model.encode(text)
```

---

## 🗄️ Vector Database Systems

### Qdrant Cloud (Primary VDB)
- **Connection:** Via `QDRANT_URL` and `QDRANT_API_KEY` environment variables
- **Collections:** Per-customer collections for tenant isolation
- **Format:** `kpi_dashboard_vectors_customer_{customer_id}`
- **Dimension:** 3072 (OpenAI) or 384 (SentenceTransformer)
- **Distance Metric:** Cosine similarity

### FAISS (Local VDB)
- **Storage:** Local file system (`./faiss_index`)
- **Dimension:** 384 (SentenceTransformer)
- **Used in:** `enhanced_rag_openai.py`

---

## 🔍 Key Embedding Processing Functions

### In `enhanced_rag_qdrant.py`:
- `_generate_embedding()` (line 111) - Generate OpenAI embeddings
- `build_knowledge_base()` (line 178) - Build Qdrant collection with embeddings
- `query()` (line ~400) - Query with embeddings

### In `enhanced_rag_openai.py`:
- `build_knowledge_base()` (line 43) - Build FAISS index with embeddings
- `query()` - Query with embeddings

### In Customer Embedding Scripts:
- `embed_signals()` - Generate embeddings for signals
- `load_to_qdrant()` - Load embeddings to Qdrant
- `batch_embed()` - Batch processing of embeddings

---

## 📝 Current Active System

### **Direct RAG (No Embeddings)**
**File:** `backend/direct_rag_api.py`
- **Status:** ✅ **ACTIVE** (V3 system)
- **Embeddings:** None
- **Vector DB:** None
- **Method:** Direct database queries
- **Advantage:** No rebuilds needed, always fresh data

### **Legacy Systems (Require Embeddings)**
- `enhanced_rag_qdrant.py` - Requires Qdrant rebuilds
- `enhanced_rag_openai.py` - Requires FAISS rebuilds
- `enhanced_rag_temporal.py` - Requires Qdrant rebuilds
- `enhanced_rag_historical.py` - Requires Qdrant rebuilds

---

## 🎯 Summary by Purpose

### **RAG Query Processing:**
1. `enhanced_rag_qdrant.py` - OpenAI embeddings → Qdrant
2. `enhanced_rag_openai.py` - SentenceTransformer → FAISS
3. `enhanced_rag_temporal.py` - SentenceTransformer → Qdrant (temporal)
4. `enhanced_rag_historical.py` - SentenceTransformer → Qdrant (historical)
5. `direct_rag_api.py` - No embeddings (database queries)

### **Signal Embedding:**
1. `agents/qdrant_integration.py` - Query Qdrant for signals
2. `verticals/customer{ID}/scripts/03_embed_signals_qdrant*.py` - Generate signal embeddings

### **Knowledge Base Building:**
1. `enhanced_rag_qdrant.py` - `build_knowledge_base()` method
2. `enhanced_rag_openai.py` - `build_knowledge_base()` method
3. Customer embedding scripts - Build per-customer collections

### **Migration:**
1. `migrate_qdrant_to_openai_embeddings.py` - Migrate to OpenAI embeddings

---

## 🔧 Environment Variables Required

### For OpenAI Embeddings:
- `OPENAI_API_KEY` - OpenAI API key

### For Qdrant Cloud:
- `QDRANT_URL` - Qdrant Cloud URL
- `QDRANT_API_KEY` - Qdrant Cloud API key

### For SentenceTransformer:
- No API key needed (local model)

---

## 📚 Related Documentation

- `RAG_SYSTEM_EXPLANATION.md` - RAG system architecture
- `ENHANCED_RAG_SYSTEM.md` - Enhanced RAG documentation
- `RAG_FLOW_ANALYSIS.md` - RAG flow analysis
- `agents/SIGNAL_ANALYST_ARCHITECTURE.md` - Signal Analyst architecture

---

## 🎯 Quick Reference

| File | Embedding Model | Vector DB | Dimensions | Status |
|------|----------------|-----------|------------|--------|
| `enhanced_rag_qdrant.py` | OpenAI text-embedding-3-large | Qdrant Cloud | 3072 | Legacy |
| `enhanced_rag_openai.py` | SentenceTransformer all-MiniLM-L6-v2 | FAISS | 384 | Legacy |
| `enhanced_rag_temporal.py` | SentenceTransformer all-MiniLM-L6-v2 | Qdrant Cloud | 384 | Legacy |
| `enhanced_rag_historical.py` | SentenceTransformer all-MiniLM-L6-v2 | Qdrant Cloud | 384 | Legacy |
| `direct_rag_api.py` | None | None | N/A | ✅ Active |
| `agents/qdrant_integration.py` | Uses existing embeddings | Qdrant Cloud | 3072/384 | Active |

---

**Last Updated:** 2026-01-24
