# Qualitative Signal Validation Architecture

**Date**: December 18, 2025  
**Question**: Best approach to add qualitative signals (emails, meeting transcripts) to validate quantitative data before triggering playbooks?

---

## Current State

### ✅ **Quantitative Triggers** (Currently Implemented)

Playbook triggers are based on **quantitative metrics only**:
- Health scores
- KPI thresholds (NPS < 10, CSAT < 3.6, etc.)
- Revenue/engagement metrics
- Score-based urgency calculation (0-100)

**Evaluation Flow:**
```
Quantitative Metrics → Score Calculation → Trigger Decision
```

**Example**: `evaluate_account_for_voc_sprint()`
- Checks: NPS threshold, CSAT threshold, health score, account status
- Output: `urgency_score` (0-100), `urgency_level`, `reasons`
- **No qualitative validation**

---

## Recommended Approach: **Multi-Layer Validation Architecture**

### **Option 1: Pre-Trigger Validation Layer (RECOMMENDED)**

Add a **validation layer** before triggering playbooks that combines quantitative + qualitative signals.

#### Architecture

```
Quantitative Triggers → Validation Layer → Qualitative Check → Final Decision
    (KPI metrics)          (Score ≥ 50)      (RAG Analysis)     (Trigger/Defer/Reject)
```

#### Workflow

**Step 1: Quantitative Trigger Detection** (Existing)
- Quantitative metrics cross thresholds
- `urgency_score` calculated (0-100)
- Account flagged for playbook

**Step 2: Validation Layer** (NEW)
- If `urgency_score` ≥ validation_threshold (e.g., 50):
  - **Collect qualitative signals** for that account
  - **Query RAG system** to analyze qualitative data
  - **Generate validation report**

**Step 3: Qualitative Analysis** (NEW)
- Embed emails/transcripts in Qdrant (same customer collection)
- RAG query: "Does this account show signs of [issue] based on recent communications?"
- Extract: sentiment, urgency signals, corroborating evidence

**Step 4: Combined Decision** (NEW)
- **Quantitative score**: 0-100
- **Qualitative validation**: Confirm/Contradict/Neutral
- **Final decision**: 
  - Confirm if both agree
  - Defer if qualitative contradicts
  - Flag for manual review if ambiguous

---

## Implementation Strategy

### **Phase 1: Data Storage**

#### Store Qualitative Signals

**PostgreSQL Table: `qualitative_signals`**
```sql
CREATE TABLE qualitative_signals (
    signal_id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    account_id INTEGER NOT NULL,
    signal_type VARCHAR(50),  -- 'email', 'meeting_transcript', 'support_ticket', 'note'
    source VARCHAR(100),      -- 'outlook', 'gmail', 'zoom', 'teams', 'manual'
    content TEXT,             -- Full text content
    extracted_data JSON,      -- Structured extraction (entities, sentiment, etc.)
    relevance_tags JSON,      -- ['churn_risk', 'satisfaction', 'escalation']
    sentiment_score FLOAT,    -- -1 to 1
    urgency_indicator VARCHAR(20),  -- 'high', 'medium', 'low'
    timestamp TIMESTAMP,
    created_at TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (account_id) REFERENCES accounts(account_id)
);

CREATE INDEX idx_qualitative_account_time ON qualitative_signals(account_id, timestamp);
CREATE INDEX idx_qualitative_customer_time ON qualitative_signals(customer_id, timestamp);
CREATE INDEX idx_qualitative_type ON qualitative_signals(signal_type);
```

#### Embed in Qdrant

**Add to `build_knowledge_base()` in `enhanced_rag_qdrant.py`:**

```python
# Fetch qualitative signals for the customer
qualitative_signals = QualitativeSignal.query.filter_by(
    customer_id=customer_id
).order_by(QualitativeSignal.timestamp.desc()).limit(1000).all()  # Last 1000 signals

# Create embeddings for each signal
for signal in qualitative_signals:
    signal_text = self._create_qualitative_text(signal)
    embedding = self._generate_embedding(signal_text, customer_id)
    
    qualitative_data.append({
        'signal_id': signal.signal_id,
        'account_id': signal.account_id,
        'signal_type': signal.signal_type,
        'content': signal.content,
        'sentiment_score': signal.sentiment_score,
        'urgency_indicator': signal.urgency_indicator,
        'relevance_tags': signal.relevance_tags,
        'text': signal_text,
        'embedding': embedding
    })
```

---

### **Phase 2: Validation Function**

#### Add Validation Endpoint

**New API: `/api/playbooks/validate-trigger`**

```python
def validate_playbook_trigger(account_id, playbook_id, quantitative_evaluation):
    """
    Validate quantitative trigger with qualitative signals
    
    Args:
        account_id: Account to validate
        playbook_id: Proposed playbook ('voc-sprint', etc.)
        quantitative_evaluation: Result from evaluate_account_for_*()
    
    Returns:
        {
            'quantitative_score': 75,
            'qualitative_validation': {
                'corroborates': True/False,
                'confidence': 0.0-1.0,
                'evidence': [...],
                'sentiment': 'negative'/'neutral'/'positive',
                'urgency_signals': [...]
            },
            'final_decision': 'confirm'/'defer'/'manual_review',
            'recommendation': 'Trigger playbook'/'Wait for more signals'/'Review manually'
        }
    """
```

#### Validation Query Examples

**For VoC Sprint:**
```python
validation_query = f"""
Analyze recent communications (emails, meeting transcripts) for account {account_name}.
Quantitative metrics indicate potential issues: {quantitative_reasons}

Questions:
1. Do recent communications show signs of dissatisfaction, complaints, or churn risk?
2. Are there explicit or implicit signals that corroborate these quantitative metrics?
3. What is the overall sentiment and urgency level?

Recent quantitative signals:
- Low NPS proxy: {nps_proxy}
- Low CSAT proxy: {csat_proxy}
- Health score: {health_score}

Provide evidence from communications that either:
- Corroborates these concerns (trigger playbook)
- Contradicts these concerns (defer trigger)
- Shows neutral/ambiguous signals (flag for review)
"""
```

**For Renewal Safeguard:**
```python
validation_query = f"""
Analyze recent communications for account {account_name} approaching renewal.
Quantitative metrics suggest renewal risk: {quantitative_reasons}

Questions:
1. Are there budget concerns, contract discussions, or renewal negotiations mentioned?
2. Is there positive engagement (expansion talks, feature requests) or negative signals (budget cuts, downsizing)?
3. What does sentiment analysis reveal about renewal likelihood?

Provide specific evidence from emails/meetings.
"""
```

---

### **Phase 3: Decision Logic**

#### Combined Scoring

```python
def make_trigger_decision(quantitative_score, qualitative_validation):
    """
    Combine quantitative and qualitative signals for final decision
    """
    quant_weight = 0.6  # 60% quantitative
    qual_weight = 0.4   # 40% qualitative
    
    # Qualitative score from validation
    if qualitative_validation['corroborates']:
        qual_score = qualitative_validation['confidence'] * 100
    elif qualitative_validation['contradicts']:
        qual_score = (1 - qualitative_validation['confidence']) * -50  # Negative weight
    else:  # Neutral/ambiguous
        qual_score = 50  # Neutral
    
    # Combined score
    combined_score = (
        quantitative_score * quant_weight + 
        qual_score * qual_weight
    )
    
    # Decision logic
    if combined_score >= 70 and qualitative_validation['corroborates']:
        return 'confirm'  # Strong quantitative + qualitative agreement
    elif combined_score >= 50 and qualitative_validation['confidence'] > 0.7:
        return 'confirm'  # Moderate quantitative, high qualitative confidence
    elif quantitative_score >= 70 and not qualitative_validation['corroborates']:
        return 'defer'  # Strong quantitative but qualitative doesn't support
    elif quantitative_score >= 50 and qualitative_validation['contradicts']:
        return 'defer'  # Moderate quantitative, qualitative contradicts
    else:
        return 'manual_review'  # Ambiguous, needs human review
```

---

## Architecture Options

### **Option A: Embedded Validation (RECOMMENDED)**

**Qualitative signals embedded in Qdrant** (same collection as KPIs/Accounts)

**Pros:**
- ✅ **Semantic search** - Find relevant signals automatically
- ✅ **Unified context** - All data in one vector space
- ✅ **Automatic relevance** - RAG finds most relevant signals
- ✅ **Schema-agnostic** - Works with any qualitative data format

**Cons:**
- ⚠️ Requires rebuilding knowledge base when new signals arrive
- ⚠️ Storage cost (but minimal for embeddings)

**Workflow:**
```
1. New email/transcript arrives → Store in PostgreSQL
2. Periodic job (hourly/daily) → Embed new signals into Qdrant
3. Validation query → RAG searches Qdrant for relevant signals
4. Combined analysis → Final decision
```

---

### **Option B: On-Demand Validation**

**Qualitative signals stored only in PostgreSQL**, queried on-demand

**Pros:**
- ✅ Real-time (no embedding delay)
- ✅ Full text search available
- ✅ No vector DB storage needed

**Cons:**
- ❌ Less semantic understanding
- ❌ Requires manual query construction
- ❌ May miss relevant but differently-worded signals

**Workflow:**
```
1. New email/transcript arrives → Store in PostgreSQL
2. Validation query → SQL query for recent signals
3. OpenAI analysis → Analyze retrieved signals
4. Combined analysis → Final decision
```

---

### **Option C: Hybrid Approach (BEST)**

**Use both**: Embedded for semantic search + On-demand for recent signals

**Pros:**
- ✅ Best of both worlds
- ✅ Semantic search for historical patterns
- ✅ Real-time analysis for recent signals
- ✅ Maximum validation accuracy

**Workflow:**
```
1. Quantitative trigger detected
2. Semantic search (Qdrant) → Find similar historical signals/outcomes
3. Recent signals query (PostgreSQL) → Get last 30 days of communications
4. Combined RAG analysis → Validate trigger
5. Final decision
```

---

## Recommended Implementation Plan

### **Step 1: Data Model**

Create `QualitativeSignal` model:
```python
class QualitativeSignal(db.Model):
    __tablename__ = 'qualitative_signals'
    
    signal_id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, ForeignKey('customers.customer_id'), index=True)
    account_id = db.Column(db.Integer, ForeignKey('accounts.account_id'), index=True)
    
    signal_type = db.Column(db.String(50))  # 'email', 'meeting_transcript', etc.
    source = db.Column(db.String(100))
    content = db.Column(db.Text)  # Full text
    extracted_data = db.Column(db.JSON)  # Structured data
    relevance_tags = db.Column(db.JSON)
    sentiment_score = db.Column(db.Float)
    urgency_indicator = db.Column(db.String(20))
    timestamp = db.Column(db.DateTime)
    
    __table_args__ = (
        Index('idx_qualitative_account_time', 'account_id', 'timestamp'),
    )
```

### **Step 2: Embedding Strategy**

**Add to `enhanced_rag_qdrant.py`:**

```python
def build_knowledge_base(self, customer_id: int):
    # ... existing KPI/Account embedding ...
    
    # Add qualitative signals
    from models import QualitativeSignal
    qualitative_signals = QualitativeSignal.query.filter_by(
        customer_id=customer_id
    ).order_by(QualitativeSignal.timestamp.desc()).limit(1000).all()
    
    for signal in qualitative_signals:
        signal_text = self._create_qualitative_text(signal)
        embedding = self._generate_embedding(signal_text, customer_id)
        
        qualitative_data.append({
            'signal_id': signal.signal_id,
            'account_id': signal.account_id,
            'type': 'qualitative_signal',
            'signal_type': signal.signal_type,
            'sentiment_score': signal.sentiment_score,
            'urgency': signal.urgency_indicator,
            'text': signal_text,
            'embedding': embedding
        })
    
    # Build index with all data types
    self._build_qdrant_index(kpi_data, account_data, temporal_data, qualitative_data)
```

### **Step 3: Validation Function**

**New file: `playbook_validation_api.py`:**

```python
def validate_playbook_trigger(account_id, playbook_id, quantitative_evaluation):
    """
    Validate quantitative trigger with qualitative RAG analysis
    """
    account = Account.query.get(account_id)
    
    # Build validation query based on playbook type
    validation_query = build_validation_query(
        account, 
        playbook_id, 
        quantitative_evaluation
    )
    
    # Query RAG system for qualitative validation
    rag_system = get_qdrant_rag_system(customer_id)
    
    # Filter to account-specific qualitative signals
    validation_result = rag_system.query(
        validation_query,
        query_type='validation',
        account_filter=account_id  # Filter to this account's signals
    )
    
    # Analyze validation result
    qualitative_validation = analyze_validation_result(
        validation_result,
        quantitative_evaluation
    )
    
    # Make combined decision
    final_decision = make_trigger_decision(
        quantitative_evaluation['urgency_score'],
        qualitative_validation
    )
    
    return {
        'quantitative': quantitative_evaluation,
        'qualitative_validation': qualitative_validation,
        'final_decision': final_decision,
        'recommendation': get_recommendation(final_decision)
    }
```

---

## Integration Points

### **1. Playbook Recommendation Flow**

**Current:**
```
Quantitative Metrics → evaluate_account_for_*() → Recommendation
```

**Enhanced:**
```
Quantitative Metrics → evaluate_account_for_*() 
    ↓ (if score ≥ threshold)
Qualitative Validation → validate_playbook_trigger() 
    ↓
Final Decision (Confirm/Defer/Review)
```

### **2. Trigger Evaluation**

**Update `playbook_triggers_api.py`:**

```python
@playbook_triggers_api.route('/api/playbooks/triggers/evaluate', methods=['POST'])
def evaluate_triggers_with_validation():
    """
    Evaluate triggers with qualitative validation
    """
    data = request.json
    account_id = data.get('account_id')
    playbook_id = data.get('playbook_id')
    require_validation = data.get('require_validation', True)
    
    # Step 1: Quantitative evaluation (existing)
    quantitative_eval = evaluate_account_for_playbook(account_id, playbook_id)
    
    # Step 2: Qualitative validation (NEW)
    if require_validation and quantitative_eval['urgency_score'] >= 50:
        validation = validate_playbook_trigger(
            account_id, 
            playbook_id, 
            quantitative_eval
        )
        return jsonify(validation)
    else:
        return jsonify({
            'quantitative': quantitative_eval,
            'qualitative_validation': None,
            'final_decision': 'confirm' if quantitative_eval['urgency_score'] >= 70 else 'defer',
            'note': 'Validation skipped (low urgency or disabled)'
        })
```

---

## Data Ingestion Strategy

### **Email Integration**

**Options:**
1. **Email API Integration** (Outlook, Gmail APIs)
   - Real-time webhooks for new emails
   - Filter by account domain/contacts
   - Extract email content, metadata

2. **Email Parsing Service**
   - Forward emails to parsing endpoint
   - Extract: sender, recipient, subject, body, attachments
   - Link to account via email domain matching

### **Meeting Transcript Integration**

**Options:**
1. **Calendar/Meeting APIs** (Zoom, Teams, Google Meet)
   - Webhook for completed meetings
   - Fetch transcript via API
   - Link to account via participant emails

2. **Manual Upload**
   - UI for uploading transcripts
   - Extract: participants, date, transcript text

### **Processing Pipeline**

```
1. Ingest → Store raw content in PostgreSQL
2. Extract → Use OpenAI/NLP to extract:
   - Sentiment (-1 to 1)
   - Entities (account mentions, key topics)
   - Urgency indicators
   - Relevance tags
3. Embed → Add to Qdrant knowledge base
4. Index → Store metadata in PostgreSQL
```

---

## Validation Query Templates

### **VoC Sprint Validation**

```
Analyze recent communications for {account_name}.

Quantitative metrics indicate potential customer dissatisfaction:
- Low NPS proxy: {nps_score}
- Low CSAT proxy: {csat_score}  
- Health score decline: {health_score}
- Account status: {status}

Based on recent emails, meeting transcripts, and support interactions:

1. Do communications show explicit complaints, dissatisfaction, or churn signals?
2. Are there implicit concerns (missed meetings, delayed responses, tone changes)?
3. What is the sentiment trend over the last 30 days?
4. Are there positive signals that contradict the quantitative metrics?

Provide:
- Corroborating evidence (if found)
- Contradicting evidence (if found)
- Overall validation confidence (0-1)
- Recommendation: Trigger VoC Sprint / Defer / Manual Review
```

### **Renewal Safeguard Validation**

```
Analyze recent communications for {account_name} (renewal in {days} days).

Quantitative metrics suggest renewal risk:
- Health score: {health_score}
- Engagement decline detected
- Account status: {status}

Based on recent communications:

1. Are there discussions about contract renewal, budget, or expansion?
2. What is the sentiment around the relationship and product value?
3. Are there positive signals (expansion talks, feature requests) or negative (budget cuts, downsizing)?
4. What does communication frequency and engagement level indicate?

Provide validation with specific evidence.
```

---

## Decision Matrix

### **Combined Scoring Logic**

| Quantitative Score | Qualitative Corroborates | Confidence | Decision | Action |
|-------------------|-------------------------|------------|----------|--------|
| ≥ 70 | Yes | High (>0.7) | **Confirm** | Auto-trigger |
| ≥ 70 | Yes | Medium (0.5-0.7) | **Confirm** | Auto-trigger with monitoring |
| ≥ 70 | Neutral | Any | **Manual Review** | Flag for CSM review |
| ≥ 70 | No | High (>0.7) | **Defer** | Wait 7 days, re-evaluate |
| 50-69 | Yes | High (>0.7) | **Confirm** | Auto-trigger |
| 50-69 | Yes | Medium | **Manual Review** | CSM decision |
| 50-69 | Neutral/No | Any | **Defer** | Monitor only |
| < 50 | Any | Any | **Defer** | Below threshold |

---

## Benefits of This Approach

### ✅ **Reduces False Positives**
- Quantitative metrics might flag accounts incorrectly
- Qualitative validation confirms or rejects triggers
- Prevents unnecessary playbook executions

### ✅ **Increases Confidence**
- Quantitative + Qualitative = Higher confidence
- Evidence-based decisions
- Better resource allocation

### ✅ **Learning Opportunity**
- Track validation accuracy over time
- Learn which signals are most predictive
- Improve threshold tuning

### ✅ **Scalable Architecture**
- Works with existing Qdrant/RAG infrastructure
- Schema-agnostic (any qualitative data format)
- Automatic semantic understanding

---

## Recommended Next Steps

### **Phase 1: Proof of Concept**
1. Create `QualitativeSignal` model
2. Manual ingestion (upload sample emails/transcripts)
3. Embed in Qdrant
4. Build validation function
5. Test with 1-2 accounts

### **Phase 2: Integration**
1. Add validation endpoint
2. Integrate with playbook trigger evaluation
3. Update UI to show validation results
4. Add manual review workflow

### **Phase 3: Automation**
1. Email API integration
2. Meeting transcript API integration
3. Automated ingestion pipeline
4. Continuous learning from validation outcomes

---

## Summary

**Best Approach**: **Hybrid Multi-Layer Validation**

1. **Store** qualitative signals in PostgreSQL
2. **Embed** in Qdrant for semantic search
3. **Validate** quantitative triggers with RAG queries
4. **Combine** scores for final decision
5. **Learn** from validation outcomes over time

This approach leverages your existing Qdrant + OpenAI infrastructure while adding a validation layer that significantly improves playbook trigger accuracy.

