# RAG Query Collections Organization - Best Practices

**Date**: December 27, 2025  
**Objective**: Propose best way to organize RAG query collections under Quantitative, Qualitative, and Historical categories

---

## Current State Analysis

### Current Organization (26 Queries in 8 Categories)

| Current Category | Count | Query Type | Nature |
|-----------------|-------|------------|--------|
| Revenue Analysis | 4 | `revenue_analysis` | Quantitative |
| Account Health | 4 | `account_analysis` | Quantitative |
| KPI Performance | 4 | `kpi_analysis` | Quantitative |
| Industry & Regional | 2 | `general` | Quantitative |
| Historical Analysis | 6 | `trend_analysis` / `temporal_analysis` | Historical |
| Monthly Revenue | 3 | Mixed | Quantitative + Historical |
| Strategic Insights | 2 | `general` | Mixed (Quantitative-driven) |
| Product Analysis | 1 | `account_analysis` | Quantitative |
| **Total** | **26** | | |

---

## Proposed Organization: Three-Tier Structure

### **Collection 1: Quantitative Queries** 📊

**Definition**: Queries based on numeric KPI data, metrics, scores, and structured data analysis.

**Characteristics**:
- Answers derived from database values (KPIs, health scores, revenue)
- Precise, measurable, factual
- Current state analysis
- Deterministic data sources

#### **1.1 Revenue & Financial Analysis** (7 queries)
- "Which accounts have the highest revenue?"
- "What is the total revenue across all accounts?"
- "Show me revenue growth analysis and trends"
- "How does revenue vary by industry?"
- "Which accounts have the highest revenue across last 4 months?"
- "Analyze revenue trends and patterns over the last 6 months"
- "Which accounts performed best each month? Show monthly rankings"

#### **1.2 Account Health & Performance** (5 queries)
- "Show me account health scores and performance"
- **"Which accounts are at risk of churn?"** ⚠️ *Risk query - Quantitative*
- "Which accounts are performing best?"
- "Show me account engagement analysis"
- "Which accounts use more than 1 product?"

#### **1.3 KPI Metrics Analysis** (4 queries)
- "What are the top performing KPIs?"
- "Show me customer satisfaction analysis"
- "How are different KPI categories performing?"
- "What are the key trends in our KPI performance?"

#### **1.4 Comparative Analysis** (2 queries)
- "How do we perform across different industries?"
- "Show me regional performance analysis"

#### **Quantitative Collection Summary**:
- **Total**: 18 queries
- **Query Types**: `revenue_analysis`, `account_analysis`, `kpi_analysis`, `general`
- **Data Sources**: PostgreSQL (KPIs, Accounts, Health Scores, Revenue)
- **Response Type**: Metrics, scores, rankings, comparisons

---

### **Collection 2: Qualitative Queries** 💬

**Definition**: Queries based on unstructured text data, sentiment, communications, and contextual analysis.

**Characteristics**:
- Answers derived from emails, meeting transcripts, notes, support tickets
- Sentiment, tone, context, themes
- Subjective interpretation
- Text analysis and NLP

#### **Current State**: ⚠️ **NOT YET IMPLEMENTED**

**Proposed Qualitative Query Categories** (To be developed):

#### **2.1 Communication Analysis** (Future)
- "What are customers saying about our product in recent emails?"
- "Analyze sentiment from meeting transcripts"
- "What concerns are customers raising in support tickets?"
- "What feedback themes emerge from customer communications?"

#### **2.2 Sentiment & Perception** (Future)
- "What is the overall sentiment trend across accounts?"
- "Which accounts show declining satisfaction in communications?"
- "What topics generate positive vs. negative feedback?"
- "Analyze tone and urgency in customer interactions"

#### **2.3 Contextual Validation** (Future)
- "Do recent communications validate the quantitative health scores?"
- "Are there qualitative signals that contradict KPI metrics?"
- "What qualitative context explains this account's low health score?"
- "Find qualitative evidence of account health improvement"

#### **2.4 Playbook & Action Context** (Future)
- "What qualitative feedback led to playbook recommendations?"
- "What did customers say before/after playbook execution?"
- "Analyze qualitative outcomes of intervention actions"
- "What themes emerge from successful playbook executions?"

#### **Qualitative Collection Summary**:
- **Current**: 0 queries (system ready for integration)
- **Future**: ~12-16 queries (estimated)
- **Query Type**: `qualitative_analysis` (new type to be created)
- **Data Sources**: PostgreSQL (`qualitative_signals`, `account_notes`, `playbook_reports`)
- **Response Type**: Themes, sentiment, context, validation, evidence

**Integration Status**: 
- ✅ Architecture defined (`QUALITATIVE_VALIDATION_ARCHITECTURE.md`)
- ⏳ Data model ready (needs implementation)
- ⏳ Query templates to be created
- ⏳ System prompts to be optimized for qualitative analysis

---

### **Collection 3: Historical Queries** 📈

**Definition**: Queries focused on temporal patterns, trends, evolution over time, and predictive analysis.

**Characteristics**:
- Time-series analysis
- Trend identification
- Historical comparisons
- Pattern recognition
- Predictive insights

#### **3.1 Comprehensive Trend Analysis** (6 queries)
- "Show me trends across all KPIs and accounts over time"
- "Show me historical trends in Time to First Value over time"
- "Show me how account performance has changed over time"
- "How have health scores evolved over time?"
- "What temporal patterns and seasonality do you see in the data?"
- "What predictions can you make based on historical trends?"

#### **3.2 Temporal Revenue Analysis** (3 queries)
- "Which accounts have the highest revenue across last 4 months?"
- "Analyze revenue trends and patterns over the last 6 months"
- "Which accounts performed best each month? Show monthly rankings"

**Note**: These overlap with Quantitative but emphasize temporal dimension.

#### **Historical Collection Summary**:
- **Total**: 9 queries (6 pure historical + 3 temporal revenue)
- **Query Types**: `trend_analysis`, `temporal_analysis`
- **Data Sources**: PostgreSQL (`kpi_time_series`, `health_trends`, historical KPI snapshots)
- **Response Type**: Trends, patterns, evolution, seasonality, predictions

---

## Risk Queries - Special Consideration ⚠️

**Current Risk Query**: 1 query
- "Which accounts are at risk of churn?" (currently in Account Health category)

### **Risk Query Classification Challenge**

Risk queries can span **multiple collections** depending on data source:

#### **Quantitative Risk** (Current)
- Based on: Health scores, KPI metrics, account status, numeric indicators
- Data Source: PostgreSQL (KPIs, health scores, account_status)
- Example: "Which accounts are at risk of churn?" (uses health scores, KPI thresholds)
- **Collection**: ✅ **Quantitative** (Current)

#### **Qualitative Risk** (Future)
- Based on: Sentiment in emails/transcripts, communication tone, support ticket themes
- Data Source: Qualitative signals, account notes, communications
- Examples (Future):
  - "Which accounts show risk signals in recent communications?"
  - "What qualitative indicators suggest churn risk?"
  - "Analyze sentiment trends for at-risk accounts"
- **Collection**: 💬 **Qualitative** (Future)

#### **Historical Risk** (Future)
- Based on: Risk trends over time, evolving risk patterns, predictive risk
- Data Source: Time-series data, historical health scores
- Examples (Future):
  - "How has churn risk evolved over time?"
  - "Which accounts are showing increasing risk trends?"
  - "Predict which accounts will be at risk next quarter"
- **Collection**: 📈 **Historical** (Future)

### **Recommended Approach for Risk Queries**

**Option 1: Separate Risk Subcategory** ✅ **RECOMMENDED**
- Create "Risk Assessment" subcategory in each collection
- Quantitative → Account Health & Performance → Risk Assessment
- Qualitative → Sentiment & Perception → Risk Indicators
- Historical → Trend Analysis → Risk Trends

**Option 2: Unified Risk Collection** (Not Recommended)
- Create separate 4th collection for Risk
- **Drawback**: Risk spans all data types, not a distinct collection

**Option 3: Cross-Collection Queries**
- Allow risk queries to pull from multiple collections
- **Drawback**: Complex to implement and organize

### **Risk Query Distribution (Recommended)**

```
📊 Quantitative Collection
└── Account Health & Performance
    └── Risk Assessment (1 current, +2 future)
        - "Which accounts are at risk of churn?" ✅ (Current)
        - "Which accounts have declining health scores?" (Future)
        - "What KPIs indicate account risk?" (Future)

💬 Qualitative Collection
└── Sentiment & Perception
    └── Risk Indicators (Future: ~4 queries)
        - "Which accounts show risk signals in communications?"
        - "What sentiment trends indicate churn risk?"
        - "Analyze communication patterns for at-risk accounts"
        - "What qualitative signals contradict health scores?"

📈 Historical Collection
└── Trend Analysis
    └── Risk Trends (Future: ~3 queries)
        - "How has churn risk evolved over time?"
        - "Which accounts show increasing risk trends?"
        - "Predict future risk based on historical patterns"
```

### **Risk Query Implementation Notes**

1. **Current State**: Only quantitative risk query exists
2. **Data Sources**: 
   - Quantitative: Health scores, KPI values, account_status
   - Qualitative: Emails, transcripts, notes (future)
   - Historical: Time-series health scores, KPI trends (future)
3. **Backend Functions**: `find_at_risk_accounts()` exists for quantitative risk
4. **Future Enhancement**: Risk queries can leverage multiple collections for comprehensive analysis

---

## Proposed Organization Structure

### **Option A: Strict Three-Collection Separation** ✅ **RECOMMENDED**

```
📊 Quantitative Collection (18 queries)
├── Revenue & Financial (7)
├── Account Health & Performance (5)
├── KPI Metrics (4)
└── Comparative Analysis (2)

💬 Qualitative Collection (0 current, ~12-16 future)
├── Communication Analysis (Future)
├── Sentiment & Perception (Future)
├── Contextual Validation (Future)
└── Playbook Context (Future)

📈 Historical Collection (9 queries)
├── Comprehensive Trend Analysis (6)
└── Temporal Revenue Analysis (3)
```

**Benefits**:
- ✅ Clear separation of data sources
- ✅ Easy to understand query type
- ✅ Optimized system prompts per collection
- ✅ Scalable for future qualitative queries

---

### **Option B: Hybrid Approach (Allow Overlaps)**

Some queries could belong to multiple collections:
- Monthly Revenue queries → Both Quantitative AND Historical
- Strategic Insights → Both Quantitative AND Qualitative (when qualitative is added)

**Benefits**:
- ✅ Reflects real-world query complexity
- ✅ Queries can leverage multiple data sources

**Drawbacks**:
- ❌ Less clear categorization
- ❌ Harder to organize in UI
- ❌ May confuse users

---

## Implementation Recommendations

### **1. Collection Metadata Structure**

```typescript
interface QueryCollection {
  id: string;
  name: string;
  description: string;
  category: 'quantitative' | 'qualitative' | 'historical';
  icon: string;
  color: string;
  query_type: string;
  data_sources: string[];
  example_queries: QueryTemplate[];
}

interface QueryTemplate {
  id: string;
  title: string;
  query: string;
  query_type: string;
  collection: 'quantitative' | 'qualitative' | 'historical';
  subcategory: string;
  description: string;
}
```

### **2. Query Type Mapping**

| Collection | Primary Query Types | System Prompt Focus |
|-----------|---------------------|---------------------|
| **Quantitative** | `revenue_analysis`, `account_analysis`, `kpi_analysis`, `general` | Metrics, scores, factual data |
| **Qualitative** | `qualitative_analysis` (new) | Sentiment, context, themes |
| **Historical** | `trend_analysis`, `temporal_analysis` | Trends, patterns, evolution |

### **3. UI Organization**

**Recommended Frontend Structure**:

```
┌─────────────────────────────────────────────────┐
│ RAG Query Collections                           │
├─────────────────────────────────────────────────┤
│ [📊 Quantitative] [💬 Qualitative] [📈 Historical] │
└─────────────────────────────────────────────────┘

Quantitative Tab:
├── Revenue & Financial (7 queries)
├── Account Health (5 queries)
├── KPI Metrics (4 queries)
└── Comparisons (2 queries)

Qualitative Tab:
├── Communication Analysis (Coming Soon)
├── Sentiment Analysis (Coming Soon)
└── Context Validation (Coming Soon)

Historical Tab:
├── Trend Analysis (6 queries)
└── Temporal Revenue (3 queries)
```

### **4. System Prompt Optimization**

**Quantitative Queries**:
```
You are a data analyst. Analyze numeric KPI data, metrics, and scores.
Focus on precise values, rankings, comparisons, and measurable insights.
Base answers strictly on database values.
```

**Qualitative Queries** (Future):
```
You are a communication analyst. Analyze text data, sentiment, and context.
Focus on themes, tone, sentiment, and qualitative insights.
Synthesize information from emails, transcripts, and notes.
```

**Historical Queries**:
```
You are a trend analyst. Analyze temporal patterns and evolution.
Focus on trends, seasonality, historical comparisons, and predictions.
Use time-series data to identify patterns over time.
```

---

## Migration Strategy

### **Phase 1: Reorganize Existing Queries** (Current 26 queries)

1. **Quantitative Collection** (18 queries):
   - Revenue Analysis (4) → Revenue & Financial
   - Account Health (4) → Account Health & Performance
   - KPI Performance (4) → KPI Metrics
   - Industry/Regional (2) → Comparative Analysis
   - Monthly Revenue (3) → Temporal Revenue (Historical overlap)
   - Product Analysis (1) → Account Health & Performance

2. **Historical Collection** (9 queries):
   - Historical Analysis (6) → Comprehensive Trend Analysis
   - Monthly Revenue (3) → Temporal Revenue Analysis

**Note**: Monthly Revenue queries appear in both (with different emphasis)

### **Phase 2: Add Qualitative Collection** (Future)

1. Implement qualitative data model
2. Build qualitative query templates
3. Add qualitative system prompts
4. Integrate with existing RAG system

---

## Query Distribution Analysis

### Current Distribution:
- **Quantitative**: 18 queries (69%)
- **Historical**: 9 queries (35%)
- **Qualitative**: 0 queries (0%)
- **Overlap**: 1 query (Monthly Revenue appears in both)

### Target Distribution (After Qualitative Implementation):
- **Quantitative**: 18 queries (~50%)
- **Qualitative**: ~12-16 queries (~35%)
- **Historical**: 9 queries (~25%)
- **Overlap**: Flexible based on query nature

---

## Best Practices

### **1. Collection Naming Convention**

Use clear, descriptive names:
- ✅ `quantitative_revenue_analysis`
- ✅ `qualitative_sentiment_analysis`
- ✅ `historical_trend_analysis`
- ❌ `collection1`, `type_a`, `cat_1`

### **2. Query Template Structure**

Each query template should include:
```python
{
    'id': 'quantitative_revenue_top_accounts',
    'title': 'Top Revenue Accounts',
    'query': 'Which accounts have the highest revenue?',
    'collection': 'quantitative',
    'subcategory': 'revenue_financial',
    'query_type': 'revenue_analysis',
    'data_sources': ['accounts', 'kpis', 'health_scores'],
    'description': 'Identify accounts with highest revenue using quantitative metrics'
}
```

### **3. System Prompt Per Collection**

Optimize system prompts for each collection:
- Quantitative: Focus on precision, metrics, numbers
- Qualitative: Focus on sentiment, themes, context
- Historical: Focus on trends, patterns, evolution

### **4. UI Organization**

- Use clear visual separation (tabs, sections)
- Group by subcategory within collections
- Show query count per collection
- Highlight "Coming Soon" for qualitative queries

---

## Recommendations Summary

### ✅ **Recommended Approach**

1. **Organize into 3 Collections**: Quantitative, Qualitative, Historical
2. **Use Option A**: Strict separation (clearer for users)
3. **Handle Overlaps**: Monthly Revenue can appear in both Quantitative and Historical with different emphasis
4. **Future-Proof**: Structure ready for Qualitative queries
5. **Clear Metadata**: Add collection field to query templates
6. **Optimized Prompts**: Different system prompts per collection

### **Implementation Priority**

1. **High Priority**: Reorganize existing 26 queries into Quantitative (18) and Historical (9)
2. **Medium Priority**: Update UI to reflect new organization
3. **Low Priority**: Plan Qualitative collection structure (implementation pending)

### **Breaking Changes**

**Minimal**: 
- Adding `collection` field to query templates (backward compatible)
- Reorganizing UI presentation (doesn't break functionality)
- No API changes required

---

## Next Steps (When Ready to Implement)

1. ✅ Update query template structure to include `collection` field
2. ✅ Reorganize `QUERY_TEMPLATES` array in `test_all_rag_templates.py`
3. ✅ Update UI component (`RAGAnalysis.tsx`) to group by collection
4. ✅ Add collection-specific system prompts
5. ✅ Update documentation (`QUERY_COLLECTIONS_SUMMARY.md`)
6. ⏳ Plan Qualitative query templates (after qualitative data integration)

---

**Status**: 📋 **ASSESSMENT COMPLETE** - No changes made, recommendations provided

