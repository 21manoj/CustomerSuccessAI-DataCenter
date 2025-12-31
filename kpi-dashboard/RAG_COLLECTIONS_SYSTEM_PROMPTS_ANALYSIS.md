# RAG Collections System Prompts Impact Analysis

**Date**: December 27, 2025  
**Question**: If collections are broader scope than categories, would this impact system prompts?

---

## Current System Prompt Architecture

### **Current Approach: Query Type-Based Prompts**

**Hierarchy**:
```
Query Type (Specific) → System Prompt
```

**Current Query Types**:
- `revenue_analysis` → Revenue analyst prompt
- `account_analysis` → Customer success analyst prompt
- `kpi_analysis` → KPI specialist prompt
- `trend_analysis` → Trend analyst prompt
- `temporal_analysis` → Temporal analyst prompt
- `general` → General assistant prompt

**Location**: `enhanced_rag_qdrant.py` lines 444-458

**Current Implementation**:
```python
def _generate_openai_response(self, query: str, results: List[Dict], query_type: str, ...):
    # Create system prompt based on query type
    if query_type == 'revenue_analysis':
        system_prompt = """You are a business analyst specializing in KPI and revenue analysis..."""
    elif query_type == 'account_analysis':
        system_prompt = """You are a customer success analyst..."""
    elif query_type == 'kpi_analysis':
        system_prompt = """You are a KPI specialist..."""
    else:
        system_prompt = """You are a business intelligence analyst..."""
```

---

## Proposed Collection Hierarchy

### **New Hierarchy Structure**

```
Collection (Broadest) → Category (Middle) → Query Type (Specific)
```

**Proposed Collections**:
1. **Quantitative** (18 queries)
   - Categories: Revenue & Financial, Account Health, KPI Metrics, Comparative Analysis
   - Query Types: `revenue_analysis`, `account_analysis`, `kpi_analysis`, `general`

2. **Qualitative** (0 current, 12-16 future)
   - Categories: Communication Analysis, Sentiment & Perception, Contextual Validation, Playbook Context
   - Query Type: `qualitative_analysis` (new)

3. **Historical** (9 queries)
   - Categories: Comprehensive Trend Analysis, Temporal Revenue Analysis
   - Query Types: `trend_analysis`, `temporal_analysis`

---

## Impact Analysis: Collection-Level System Prompts

### **Should We Add Collection-Level Prompts?**

#### **Option A: Keep Current (Query Type Only)** ❌ **NOT RECOMMENDED**

**Current**: System prompts based on `query_type` only

**Problem**: 
- Collections represent broader data source types (Quantitative vs Qualitative vs Historical)
- Same `query_type` (e.g., `account_analysis`) can appear in multiple collections
- Missing opportunity to optimize for data source characteristics

**Example Issue**:
- Quantitative Account Analysis: "Which accounts are at risk?" → Uses health scores, KPIs
- Qualitative Account Analysis (Future): "Which accounts show risk in communications?" → Uses sentiment, text analysis
- Both could use `account_analysis` query_type, but need different prompts!

**Risk**: ⚠️ **MEDIUM** - Suboptimal prompts, especially when qualitative queries are added

---

#### **Option B: Collection-Level Prompts** ✅ **RECOMMENDED**

**Approach**: Add collection-level system prompts in addition to query_type prompts

**Hierarchy**:
```
Collection Prompt (Base) + Query Type Prompt (Specific) = Combined Prompt
```

**Benefits**:
1. ✅ **Data Source Optimization**: Prompts optimized for data source type
2. ✅ **Future-Proof**: Ready for qualitative queries with different needs
3. ✅ **Clearer Guidance**: LLM understands broader context (quantitative vs qualitative)
4. ✅ **Better Responses**: More context = better answers

---

## Proposed System Prompt Structure

### **Collection-Level Base Prompts**

#### **1. Quantitative Collection Prompt** 📊

```python
QUANTITATIVE_BASE_PROMPT = """
You are analyzing QUANTITATIVE data from structured databases:
- KPI metrics, health scores, revenue figures, account statistics
- Numerical values, rankings, comparisons
- Precise, measurable, factual data

CRITICAL GUIDELINES:
1. Base answers STRICTLY on numeric values from the data
2. Provide specific metrics, scores, percentages, rankings
3. Use quantitative comparisons (e.g., "Account A has 45% higher revenue than Account B")
4. Avoid speculation - only use data explicitly provided
5. Cite specific numbers from the data

Data Sources: PostgreSQL (KPIs, Accounts, Health Scores, Revenue)
Response Style: Metrics-focused, precise, data-driven
"""
```

#### **2. Qualitative Collection Prompt** 💬

```python
QUALITATIVE_BASE_PROMPT = """
You are analyzing QUALITATIVE data from unstructured text sources:
- Emails, meeting transcripts, support tickets, notes
- Sentiment, tone, themes, context, communication patterns
- Subjective interpretation, textual analysis

CRITICAL GUIDELINES:
1. Analyze sentiment, tone, and underlying themes
2. Extract contextual insights from communications
3. Identify patterns and trends in qualitative feedback
4. Synthesize information from multiple text sources
5. Provide evidence-based interpretations

Data Sources: PostgreSQL (qualitative_signals, account_notes, playbook_reports)
Response Style: Theme-focused, context-aware, sentiment-driven
"""
```

#### **3. Historical Collection Prompt** 📈

```python
HISTORICAL_BASE_PROMPT = """
You are analyzing HISTORICAL and TEMPORAL data:
- Time-series data, trends over time, evolution patterns
- Seasonal patterns, predictive insights, historical comparisons
- Temporal relationships, growth trajectories

CRITICAL GUIDELINES:
1. Focus on trends, patterns, and evolution over time
2. Identify temporal relationships and seasonality
3. Compare current vs. historical performance
4. Provide predictive insights based on historical patterns
5. Highlight significant changes and trend directions

Data Sources: PostgreSQL (kpi_time_series, health_trends, historical snapshots)
Response Style: Trend-focused, temporal, predictive
"""
```

---

## Combined Prompt Strategy

### **Option 1: Hierarchical Combination** ✅ **RECOMMENDED**

```python
def _generate_openai_response(self, query: str, results: List[Dict], query_type: str, collection: str = None, ...):
    # Get collection-level base prompt
    if collection == 'quantitative':
        base_prompt = QUANTITATIVE_BASE_PROMPT
    elif collection == 'qualitative':
        base_prompt = QUALITATIVE_BASE_PROMPT
    elif collection == 'historical':
        base_prompt = HISTORICAL_BASE_PROMPT
    else:
        # Fallback: infer from query_type
        base_prompt = _infer_collection_prompt(query_type)
    
    # Get query_type-specific prompt
    if query_type == 'revenue_analysis':
        specific_prompt = "Focus on revenue drivers, account performance, and business insights."
    elif query_type == 'account_analysis':
        specific_prompt = "Focus on account health, engagement patterns, and retention strategies."
    # ... etc
    
    # Combine prompts
    system_prompt = f"{base_prompt}\n\nSPECIFIC FOCUS: {specific_prompt}"
```

**Benefits**:
- ✅ Collection provides broad context (data source type)
- ✅ Query type provides specific focus (analysis type)
- ✅ Best of both worlds

---

### **Option 2: Collection Override**

Use collection prompt only, ignore query_type

**Risk**: ⚠️ **HIGH** - Loses specificity of query_type prompts
**Recommendation**: ❌ **NOT RECOMMENDED**

---

### **Option 3: Query Type Only (Current)**

Keep current approach, ignore collections

**Risk**: ⚠️ **MEDIUM** - Suboptimal for qualitative queries, missing data source context
**Recommendation**: ❌ **NOT RECOMMENDED** (especially after qualitative queries added)

---

## Implementation Changes Required

### **1. Backend Changes** (`enhanced_rag_qdrant.py`)

#### **Change: Update `_generate_openai_response` Method**

**Current Signature** (Line ~444):
```python
def _generate_openai_response(self, query: str, results: List[Dict], query_type: str, conversation_history: List[Dict] = None) -> str:
```

**Proposed Signature**:
```python
def _generate_openai_response(self, query: str, results: List[Dict], query_type: str, collection: str = None, conversation_history: List[Dict] = None) -> str:
```

**Risk**: 🟡 **LOW-MEDIUM**
- Adding optional parameter (backward compatible)
- Must update all callers to pass collection
- Can infer collection from query_type if not provided (backward compatible)

#### **Change: Add Collection Prompt Logic**

```python
# Collection-level base prompts
COLLECTION_PROMPTS = {
    'quantitative': QUANTITATIVE_BASE_PROMPT,
    'qualitative': QUALITATIVE_BASE_PROMPT,
    'historical': HISTORICAL_BASE_PROMPT
}

def _get_collection_prompt(self, collection: str, query_type: str) -> str:
    """Get combined collection + query_type prompt"""
    # Get base prompt
    base_prompt = COLLECTION_PROMPTS.get(collection) or self._infer_collection_from_query_type(query_type)
    
    # Get query_type specific prompt
    query_type_prompt = self._get_query_type_prompt(query_type)
    
    # Combine
    return f"{base_prompt}\n\n{query_type_prompt}"
```

**Risk**: 🟢 **LOW** - New function, doesn't break existing code

---

### **2. API Changes** (`enhanced_rag_qdrant_api.py`)

#### **Change: Pass Collection to Query Method**

**Current** (Line ~40-64):
```python
@enhanced_rag_qdrant_api.route('/api/rag-qdrant/query', methods=['POST'])
def qdrant_query():
    # ...
    query_type = data.get('query_type', 'general')
    result = rag_system.query(query_text, query_type)
```

**Proposed**:
```python
@enhanced_rag_qdrant_api.route('/api/rag-qdrant/query', methods=['POST'])
def qdrant_query():
    # ...
    query_type = data.get('query_type', 'general')
    collection = data.get('collection')  # NEW: Optional collection parameter
    result = rag_system.query(query_text, query_type, collection=collection)
```

**Risk**: 🟢 **LOW** - Optional parameter, backward compatible

---

### **3. Frontend Changes** (`RAGAnalysis.tsx`)

#### **Change: Include Collection in Query Request**

**Current**: Query request includes `query_type`

**Proposed**: Also include `collection` if available

```typescript
const response = await fetch('/api/rag-qdrant/query', {
  method: 'POST',
  body: JSON.stringify({
    query: queryText,
    query_type: template.query_type,
    collection: template.collection  // NEW
  })
});
```

**Risk**: 🟢 **LOW** - Additive change, optional parameter

---

### **4. Collection Inference Logic**

**If collection not provided, infer from query_type**:

```python
def _infer_collection_from_query_type(self, query_type: str) -> str:
    """Infer collection from query_type if not explicitly provided"""
    QUANTITATIVE_TYPES = ['revenue_analysis', 'account_analysis', 'kpi_analysis', 'general']
    HISTORICAL_TYPES = ['trend_analysis', 'temporal_analysis']
    
    if query_type in QUANTITATIVE_TYPES:
        return 'quantitative'
    elif query_type in HISTORICAL_TYPES:
        return 'historical'
    else:
        return 'quantitative'  # Default fallback
```

**Risk**: 🟢 **LOW** - Fallback logic, maintains backward compatibility

---

## Risk Assessment for System Prompt Changes

### **Overall Risk**: 🟡 **LOW-MEDIUM**

| Change Area | Risk Level | Breaking Changes | Effort |
|-------------|-----------|------------------|--------|
| **Backend Prompt Logic** | 🟢 LOW | None (optional param) | Low |
| **API Endpoint** | 🟢 LOW | None (optional param) | Low |
| **Frontend Query** | 🟢 LOW | None (additive) | Low |
| **Collection Inference** | 🟢 LOW | None (fallback) | Low |
| **Prompt Quality** | 🟡 MEDIUM | None (improvement) | Medium |

---

## Benefits of Collection-Level Prompts

### **1. Better Context for LLM**

**Current**: LLM knows query type (e.g., "revenue analysis") but not data source type

**With Collections**: LLM knows:
- Data source: Quantitative (numbers) vs Qualitative (text) vs Historical (time-series)
- Analysis style: Metrics-focused vs Theme-focused vs Trend-focused
- Data characteristics: Precise vs Interpretive vs Temporal

**Result**: ✅ More accurate, context-appropriate responses

---

### **2. Future-Proof for Qualitative Queries**

**Current Problem**: When qualitative queries are added, they'll need different prompts but may use same query_type

**Example**:
- Quantitative: "Which accounts are at risk?" (uses health scores)
- Qualitative: "Which accounts are at risk?" (uses sentiment from emails)

**With Collections**: 
- Quantitative collection → "Analyze numeric health scores..."
- Qualitative collection → "Analyze sentiment and communication patterns..."

**Result**: ✅ Same query_type, different prompts based on collection

---

### **3. Clearer User Expectations**

**Collection-Level Prompts Signal**:
- Quantitative: "You'll get metrics and numbers"
- Qualitative: "You'll get sentiment and themes"
- Historical: "You'll get trends and patterns"

**Result**: ✅ Better user experience, clearer response types

---

## Implementation Recommendation

### ✅ **YES, Collections SHOULD Impact System Prompts**

**Recommended Approach**: **Option 1 - Hierarchical Combination**

1. **Collection-Level Base Prompt**: Provides data source context
2. **Query Type-Specific Prompt**: Provides analysis focus
3. **Combined Prompt**: Best of both worlds

**Implementation Strategy**:

1. **Phase 1**: Add collection parameter (optional, backward compatible)
2. **Phase 2**: Add collection inference logic (fallback)
3. **Phase 3**: Implement collection-level prompts
4. **Phase 4**: Combine with query_type prompts
5. **Phase 5**: Test and validate improved response quality

---

## Code Changes Summary

### **Files to Modify**:

1. **`enhanced_rag_qdrant.py`**:
   - Add collection parameter to `_generate_openai_response`
   - Add `COLLECTION_PROMPTS` dictionary
   - Add `_get_collection_prompt` method
   - Add `_infer_collection_from_query_type` method
   - Update prompt generation logic

2. **`enhanced_rag_qdrant_api.py`**:
   - Add `collection` parameter to query endpoint
   - Pass collection to `rag_system.query()`

3. **`enhanced_rag_qdrant.py` (query method)**:
   - Add collection parameter to `query()` method
   - Pass collection to `_generate_openai_response`

4. **`RAGAnalysis.tsx`** (Frontend):
   - Include `collection` in query request (optional)

### **Lines of Code**: ~100-150 lines

---

## Risk Mitigation

### **Backward Compatibility Strategy**

1. ✅ **Optional Parameter**: Collection is optional everywhere
2. ✅ **Inference Fallback**: If not provided, infer from query_type
3. ✅ **Default Behavior**: Without collection, use current query_type prompts
4. ✅ **Gradual Rollout**: Test with collection, fallback without

### **Testing Strategy**

1. ✅ **Unit Tests**: Test collection prompt generation
2. ✅ **Integration Tests**: Test with and without collection parameter
3. ✅ **Response Quality Tests**: Compare responses with/without collection prompts
4. ✅ **Backward Compatibility Tests**: Verify existing queries still work

---

## Conclusion

### ✅ **YES, Collections Should Impact System Prompts**

**Reasoning**:
1. Collections represent broader data source types (quantitative vs qualitative vs historical)
2. Same query_type may need different prompts based on collection
3. Better context for LLM = better responses
4. Future-proof for qualitative queries
5. Low risk implementation (optional parameter, backward compatible)

**Recommendation**: **Implement collection-level prompts with hierarchical combination**

**Risk**: 🟡 **LOW-MEDIUM** - Well-managed with backward compatibility

**Benefit**: ✅ **HIGH** - Improved response quality, especially for qualitative queries

---

**Status**: 📋 **ANALYSIS COMPLETE** - No changes made, recommendations provided

