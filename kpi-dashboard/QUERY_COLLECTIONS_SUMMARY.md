# RAG Query Collections & Types

**Date**: December 18, 2025

## Overview

The RAG system supports multiple query types and collections organized by category and analysis type.

---

## Query Type Categories

### 1. **Query Type System**

The system uses `query_type` to optimize responses. Current query types:

#### Defined Query Types

1. **`general`** - Default for general-purpose queries
2. **`revenue_analysis`** - Revenue and financial performance queries
3. **`account_analysis`** - Account health, engagement, and performance queries
4. **`kpi_analysis`** - KPI performance and metric analysis queries
5. **`trend_analysis`** - Historical trends and temporal patterns
6. **`temporal_analysis`** - Time-series and seasonal pattern analysis

#### Query Router Types (from query_router.py)

Additional granular types used by QueryRouter:
- `why_how` - Causal analysis queries ("why", "how can")
- `recommendation` - Recommendation and suggestion queries
- `analysis` - General analytical queries
- `comparison` - Comparative analysis queries
- `pattern_recognition` - Pattern and trend identification
- `strategic` - Strategic planning and prioritization queries

---

## Query Template Collections

### 26 Pre-Defined Query Templates (from test_all_rag_templates.py)

Organized into 8 categories:

#### 1. **Revenue Analysis** (4 queries)
- `revenue_analysis` type
- Focus: Revenue metrics, financial performance, growth analysis
- Examples:
  - "Which accounts have the highest revenue?"
  - "What is the total revenue across all accounts?"
  - "Show me revenue growth analysis and trends"
  - "How does revenue vary by industry?"

#### 2. **Account Health** (4 queries)
- `account_analysis` type
- Focus: Account performance, health scores, risk assessment
- Examples:
  - "Show me account health scores and performance"
  - "Which accounts are at risk of churn?"
  - "Which accounts are performing best?"
  - "Show me account engagement analysis"

#### 3. **KPI Performance** (4 queries)
- `kpi_analysis` type
- Focus: KPI metrics, category performance, trends
- Examples:
  - "What are the top performing KPIs?"
  - "Show me customer satisfaction analysis"
  - "How are different KPI categories performing?"
  - "What are the key trends in our KPI performance?"

#### 4. **Industry & Regional Analysis** (2 queries)
- `general` type
- Focus: Cross-industry and regional comparisons
- Examples:
  - "How do we perform across different industries?"
  - "Show me regional performance analysis"

#### 5. **Historical Analysis** (6 queries)
- `trend_analysis` / `temporal_analysis` types
- Focus: Historical trends, evolution, patterns, predictions
- Examples:
  - "Show me trends across all KPIs and accounts over time"
  - "Show me historical trends in Time to First Value over time"
  - "Show me how account performance has changed over time"
  - "How have health scores evolved over time?"
  - "What temporal patterns and seasonality do you see in the data?"
  - "What predictions can you make based on historical trends?"

#### 6. **Monthly Revenue Analysis** (3 queries)
- `revenue_analysis` / `trend_analysis` / `account_analysis` types
- Focus: Monthly revenue breakdowns and trends
- Examples:
  - "Which accounts have the highest revenue across last 4 months?"
  - "Analyze revenue trends and patterns over the last 6 months"
  - "Which accounts performed best each month? Show monthly rankings"

#### 7. **Strategic Insights** (2 queries)
- `general` type
- Focus: Strategic recommendations and opportunities
- Examples:
  - "What strategic recommendations do you have for improving our business?"
  - "What growth opportunities do you see in our data?"

#### 8. **Product Analysis** (1 query)
- `account_analysis` type
- Focus: Multi-product account analysis
- Examples:
  - "Which accounts use more than 1 product?"

---

## Query Type Detection

### Auto-Detection (enhanced_rag_qdrant_api.py)

The system can auto-detect query types based on keywords:

```python
def _detect_query_type(query_text: str) -> str:
    """Auto-detect query type based on keywords"""
    query_lower = query_text.lower()
    
    if 'revenue' in query_lower or 'financial' in query_lower:
        return 'revenue_analysis'
    elif 'account' in query_lower and ('health' in query_lower or 'performance' in query_lower):
        return 'account_analysis'
    elif 'kpi' in query_lower or 'metric' in query_lower:
        return 'kpi_analysis'
    elif 'trend' in query_lower or 'historical' in query_lower or 'over time' in query_lower:
        return 'trend_analysis'
    elif 'pattern' in query_lower or 'seasonal' in query_lower:
        return 'temporal_analysis'
    else:
        return 'general'
```

---

## Query Type-Specific System Prompts

Different query types use optimized system prompts for better responses:

### `revenue_analysis`
```
You are a business analyst specializing in KPI and revenue analysis. 
Analyze the provided KPI and account data to answer questions about revenue, 
growth, and business performance.
Focus on revenue drivers, account performance, and business insights. 
Provide specific metrics and actionable recommendations.
```

### `account_analysis`
```
You are a customer success analyst. 
Analyze account performance, engagement, and health scores to provide insights 
about customer relationships and risk assessment.
Focus on account health, engagement patterns, and retention strategies.
```

### `kpi_analysis`
```
You are a KPI specialist. 
Analyze KPI performance, trends, and impact levels to provide insights about 
business metrics and recommendations.
```

### `general` (default)
```
You are an AI assistant helping analyze customer success data. 
Use the provided context to answer questions accurately and provide insights.
```

---

## Query Collection Statistics

| Category | Count | Query Types |
|----------|-------|-------------|
| Revenue Analysis | 4 | `revenue_analysis` |
| Account Health | 4 | `account_analysis` |
| KPI Performance | 4 | `kpi_analysis` |
| Industry & Regional | 2 | `general` |
| Historical Analysis | 6 | `trend_analysis`, `temporal_analysis` |
| Monthly Revenue | 3 | `revenue_analysis`, `trend_analysis`, `account_analysis` |
| Strategic Insights | 2 | `general` |
| Product Analysis | 1 | `account_analysis` |
| **Total** | **26** | **6 unique types** |

---

## Usage

### API Endpoints

1. **Primary Endpoint**: `/api/rag-qdrant/query`
   - Accepts `query_type` parameter (optional, auto-detected if not provided)
   - Example:
     ```json
     {
       "query": "Which accounts have the highest revenue?",
       "query_type": "revenue_analysis"
     }
     ```

2. **Unified Endpoint**: `/api/query`
   - Routes to deterministic analytics or RAG
   - Auto-classifies query type
   - Uses QueryRouter for intelligent routing

### Query Templates

All 26 query templates are defined in `test_all_rag_templates.py` and can be:
- Used for testing
- Referenced for example queries
- Extended with additional templates

---

## Extensibility

### Adding New Query Types

1. Add query type to `_detect_query_type()` function
2. Add system prompt in `_generate_openai_response()` method
3. Add query templates to `RAG_TEMPLATES` list (optional)

### Adding New Query Collections

1. Add new category to `RAG_TEMPLATES`
2. Specify appropriate `query_type`
3. Test with `test_all_rag_templates.py`

---

## Summary

✅ **6 Query Types**: `general`, `revenue_analysis`, `account_analysis`, `kpi_analysis`, `trend_analysis`, `temporal_analysis`

✅ **26 Pre-Defined Templates**: Organized into 8 categories

✅ **Auto-Detection**: System automatically detects query type from keywords

✅ **Type-Specific Prompts**: Optimized system prompts for each query type

✅ **Extensible**: Easy to add new query types and templates

