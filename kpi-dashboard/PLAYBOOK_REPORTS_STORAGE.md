# Playbook Execution Reports Storage & Continuous Learning

**Date**: December 18, 2025

## Summary

Playbook execution reports are stored in **PostgreSQL** but are **NOT currently embedded in the Qdrant vector database**. They are queried **on-demand** during RAG queries for context enrichment, but not part of the vector knowledge base.

---

## Storage Location

### 1. **PostgreSQL Database**

Playbook reports are stored in the `playbook_reports` table:

```sql
Table: playbook_reports
- report_id (Primary Key)
- execution_id (Foreign Key → playbook_executions)
- customer_id (Indexed)
- account_id (Indexed)
- playbook_id (Indexed)
- playbook_name
- account_name
- status
- report_data (JSON) ← Full report stored here
- duration
- steps_completed
- total_steps
- started_at
- completed_at
- report_generated_at
- created_at
- updated_at
```

**Key Field**: `report_data` (JSON column)
- Contains complete report with:
  - Executive summary
  - Outcomes achieved
  - Next steps
  - RACI assignments
  - Exit criteria
  - Metrics and improvements

**Related Table**: `playbook_executions`
- Stores execution data as JSON in `execution_data` column
- Has one-to-one relationship with `PlaybookReport`

---

## Current Integration Status

### ✅ **On-Demand Query Integration** (Implemented)

Playbook reports are **queried on-demand** from PostgreSQL during RAG queries:

#### **1. Direct RAG API** (`direct_rag_api.py`)

Function: `get_playbook_context(customer_id, query_text)`
- Queries `PlaybookReport` table
- Filters by `customer_id` and optionally `account_id`
- Gets last 3 reports ordered by `report_generated_at`
- Extracts: executive summary, outcomes, next steps
- Returns formatted context string for RAG prompts

#### **2. Enhanced RAG OpenAI** (`enhanced_rag_openai.py`)

Method: `_get_playbook_context(account_id)`
- Similar implementation
- Queries `PlaybookReport` table
- Adds playbook insights to RAG context

#### **3. Account Snapshots** (`account_snapshot_api.py`)

- Stores `recent_playbook_report_ids` in AccountSnapshot
- References last 3 reports per account
- Used when building snapshot context for RAG

---

### ❌ **Vector Database Integration** (NOT Implemented)

**Playbook reports are NOT embedded in Qdrant vector database:**

- ✅ KPI data → Embedded in Qdrant
- ✅ Account data → Embedded in Qdrant  
- ✅ Temporal/Revenue data → Embedded in Qdrant
- ❌ Playbook reports → **NOT embedded, only queried on-demand**

**Current Flow:**
1. RAG query comes in
2. Qdrant search finds relevant KPIs/Accounts
3. **Separately** queries PostgreSQL for playbook reports
4. Combines both contexts in OpenAI prompt
5. Generates response

---

## Why Not Embedded?

### Current Architecture

The system uses a **hybrid approach**:
- **Structured data** (KPIs, Accounts) → Qdrant vectors for semantic search
- **Execution results** (Playbook reports) → PostgreSQL for precise queries

### Advantages of Current Approach

✅ **Fresh Data**: Always queries latest reports  
✅ **Precise Filtering**: Can filter by account_id, playbook_id, status  
✅ **Rich JSON**: Full report data preserved in JSON format  
✅ **No Duplication**: Single source of truth in PostgreSQL  

### Disadvantages

❌ **Not Searchable via Vector Similarity**: Can't find reports semantically  
❌ **Limited Context Window**: Only last 3 reports included  
❌ **Query Overhead**: Extra database query per RAG request  
❌ **No Learning from Historical Reports**: Can't learn patterns from old reports  

---

## Continuous Learning Integration

### Current Status: ⚠️ **Partial Integration**

The `continuous_learning.py` system exists but:

1. **Does NOT use playbook reports** for learning
2. Only tracks:
   - Query performance metrics
   - User feedback (helpful/not helpful)
   - Response relevance scores
3. **Missing**: Playbook outcome analysis for learning

### What Continuous Learning Could Do (Future)

If integrated, continuous learning could:

1. **Analyze Playbook Success Patterns**:
   - Which playbooks work best for which account types
   - KPI improvements achieved by playbook type
   - Time-to-outcome patterns

2. **Improve Recommendations**:
   - Learn which playbooks are most effective
   - Suggest playbooks based on successful historical patterns
   - Refine trigger thresholds based on outcomes

3. **Update Knowledge Base**:
   - Embed successful playbook outcomes into Qdrant
   - Create vectors from executive summaries and outcomes
   - Enable semantic search of playbook results

---

## How Reports Are Used in RAG

### Current Flow

```
1. User Query → RAG System
2. Vector Search (Qdrant) → Finds relevant KPIs/Accounts
3. On-Demand Query (PostgreSQL) → Gets last 3 playbook reports
4. Context Assembly:
   - Qdrant results (semantic matches)
   - Playbook reports (structured data)
5. OpenAI Prompt → Combined context
6. Response Generation
```

### Example Context Built

```
=== RECENT PLAYBOOK INSIGHTS ===
(Based on 3 recent playbook executions)

📊 VoC Sprint - TechVision (2025-12-15):
Summary: Successfully completed VoC Sprint with 15 point NPS improvement...
Key Outcomes:
  • NPS: 25 → 40 (+15 points) - Completed
  • CSAT: 3.2 → 4.1 (+0.9 points) - Completed
  • Churn Risk: 45% → 28% (-17%) - Completed
Priority Actions:
  1. Implement top 3 value actions
  2. Schedule quarterly business review

📊 Activation Blitz - CloudPrime (2025-12-10):
...
```

---

## Recommendations for Full Continuous Learning

### Option 1: Embed Reports in Qdrant (Recommended)

**Benefits:**
- ✅ Semantic search of playbook outcomes
- ✅ Can find similar successful playbooks
- ✅ Learn patterns from historical data
- ✅ Better recommendations based on outcomes

**Implementation:**
```python
def build_knowledge_base(self, customer_id: int):
    # ... existing KPI/Account embedding ...
    
    # Add playbook reports to knowledge base
    reports = PlaybookReport.query.filter_by(
        customer_id=customer_id,
        status='completed'
    ).order_by(PlaybookReport.completed_at.desc()).limit(100).all()
    
    for report in reports:
        report_text = self._create_playbook_report_text(report)
        embedding = self._generate_embedding(report_text, customer_id)
        
        point = PointStruct(
            id=point_id,
            vector=embedding,
            payload={
                'type': 'playbook_report',
                'customer_id': customer_id,
                'report_id': report.report_id,
                'execution_id': report.execution_id,
                'playbook_id': report.playbook_id,
                'account_id': report.account_id,
                'outcomes': report.report_data.get('outcomes_achieved', {}),
                'text': report_text
            }
        )
        points.append(point)
```

### Option 2: Enhanced On-Demand Queries

**Benefits:**
- ✅ Keep current architecture
- ✅ Add intelligence to report selection
- ✅ Filter by success metrics

**Implementation:**
```python
def get_playbook_context(customer_id, query_text, min_success_rate=0.7):
    # Query successful playbooks only
    reports = PlaybookReport.query.filter_by(
        customer_id=customer_id,
        status='completed'
    ).filter(
        PlaybookReport.report_data['success_indicators'].astext.cast(Integer) > 70
    ).order_by(...).limit(5).all()
```

### Option 3: Hybrid Approach

- Embed **successful** playbook reports in Qdrant
- Query **recent** reports on-demand
- Best of both worlds

---

## Current Database Schema

### PlaybookReport Table

```python
class PlaybookReport(db.Model):
    __tablename__ = 'playbook_reports'
    
    # Primary Key
    report_id = db.Column(db.Integer, primary_key=True)
    
    # Foreign Keys
    execution_id = db.Column(db.String(36), ForeignKey('playbook_executions.execution_id'))
    customer_id = db.Column(db.Integer, ForeignKey('customers.customer_id'), index=True)
    account_id = db.Column(db.Integer, ForeignKey('accounts.account_id'), index=True)
    
    # Playbook Info
    playbook_id = db.Column(db.String(50), index=True)  # 'voc-sprint', etc.
    playbook_name = db.Column(db.String(100))
    account_name = db.Column(db.String(200))
    status = db.Column(db.String(20))  # 'completed', 'failed', 'in-progress'
    
    # Report Data (JSON)
    report_data = db.Column(db.JSON, nullable=False)  # Full report
    
    # Metadata
    duration = db.Column(db.String(50))
    steps_completed = db.Column(db.Integer)
    total_steps = db.Column(db.Integer)
    
    # Timestamps
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    report_generated_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime)
    
    # Indexes
    __table_args__ = (
        Index('idx_customer_playbook', 'customer_id', 'playbook_id'),
        Index('idx_account_playbook', 'account_id', 'playbook_id'),
    )
```

---

## Summary

### ✅ **Currently Stored**

- **Location**: PostgreSQL `playbook_reports` table
- **Format**: JSON in `report_data` column
- **Access**: On-demand queries during RAG
- **Integration**: Context enrichment for RAG prompts

### ❌ **NOT Currently**

- **Embedded in Qdrant**: Reports are not vectorized
- **Used for Continuous Learning**: Not analyzed for patterns
- **Semantically Searchable**: Can't find similar outcomes via vector search

### 🔄 **Recommendation**

For true continuous learning, consider embedding successful playbook reports into Qdrant to enable:
- Semantic search of playbook outcomes
- Pattern learning from historical successes
- Better recommendations based on similar successful playbooks

