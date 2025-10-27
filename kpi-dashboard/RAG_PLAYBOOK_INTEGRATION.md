# RAG + Playbook Data Integration - Auto-Updates! 🚀

## TL;DR: **Playbook Data Automatically Included in RAG Queries**

When you query RAG, it **automatically fetches playbook insights** from the database and includes them in the AI response. No manual updates needed!

## How Playbook Data Works in RAG

### Current Implementation (V3)

```python
# backend/direct_rag_api.py - Line 252-255
def direct_query():
    # Add playbook insights context
    playbook_context = get_playbook_context(customer_id, query_text)
    if playbook_context:
        context_data.append(playbook_context)
        print(f"✓ Added playbook insights context")
```

### Key Characteristics

1. **Real-Time Database Queries**: Every RAG query fetches recent playbook reports from the database
2. **Automatic Context Enrichment**: Playbook insights are included in the AI's context automatically
3. **Account-Specific Matching**: If the query mentions an account name, it finds relevant playbooks
4. **Zero Manual Steps**: No need to manually update or link playbook data to RAG

## What Happens When You Query RAG

### Example: "Which playbooks can help improve NRR?"

#### Step 1: RAG Query Triggered
```python
# User query arrives at /api/direct-rag/query
query_text = "Which playbooks can help improve NRR?"
customer_id = 1  # Test Company
```

#### Step 2: Fetch Recent Playbook Reports
```python
# backend/direct_rag_api.py - Line 59-66
reports = PlaybookReport.query.filter_by(
    customer_id=customer_id
).order_by(
    PlaybookReport.report_generated_at.desc()
).limit(3).all()

# Returns: Last 3 playbook executions from database ✅
```

#### Step 3: Build Playbook Context
```python
# backend/direct_rag_api.py - Line 74-114
context = """
=== RECENT PLAYBOOK INSIGHTS ===
(Based on 3 recent playbook executions)

📊 VoC Sprint - TechCorp Solutions (2025-10-27):
Summary: NPS improved from 6.5 to 8.2 (+26%)...
Key Outcomes:
  • NPS Score: 6.5 → 8.2 (+26%) - Achieved
  • CSAT Score: 3.4 → 4.1 (+21%) - In Progress
  • Support Tickets: 15 → 8 (-47%) - Achieved
Priority Actions:
  1. Follow up on quarterly NPS survey
  2. Address remaining CSAT concerns
...
"""
```

#### Step 4: Include in AI Context
```python
# backend/direct_rag_api.py - Line 299
context = "\n".join(context_data)  # Includes playbook context

# Send to OpenAI
response = client.chat.completions.create(
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Context: {context}\n\nQuery: {query_text}"}
    ]
)
```

#### Step 5: AI Response Includes Playbook Insights
```json
{
  "response": "Based on recent playbook executions, the VoC Sprint has been effective... 
               NPS improved from 6.5 to 8.2. For TechCorp Solutions, consider..."
}
```

## Components That Auto-Update

### 1. **Playbook Reports** ✅
```python
# Line 59-66: Queries database directly
reports = PlaybookReport.query.filter_by(customer_id=customer_id).all()
# Automatically includes new playbook executions
```

### 2. **Account Matching** ✅
```python
# Line 38-56: Matches account names in query to relevant playbooks
accounts = Account.query.filter_by(customer_id=customer_id).all()
for account in accounts:
    if account.account_name.lower() in query_lower:
        account_id = account.account_id  # Found!
# Automatically matches new accounts
```

### 3. **Playbook Triggers** ✅
```python
# Line 269-285: Gets current alert thresholds
triggers = PlaybookTrigger.query.filter_by(customer_id=customer_id).all()
# Automatically includes updated trigger settings
```

### 4. **System Playbook Knowledge** ✅
```python
# Line 258-264: Includes system-defined playbooks
from playbook_knowledge import format_playbook_knowledge_for_rag
playbook_knowledge = format_playbook_knowledge_for_rag()
# Always includes the 5 system playbooks
```

## Real Example: MANANK LLC Playbook Integration

### Scenario: User Runs a Playbook
```python
# Execute VoC Sprint for HealthFirst Medical Group
POST /api/playbooks/recommendations/voc-sprint
# Creates PlaybookReport in database
```

### Next RAG Query (No Action Required!)
```python
# User asks: "What has been done for HealthFirst Medical Group?"
# RAG automatically includes the playbook execution in context

context = """
📊 VoC Sprint - HealthFirst Medical Group (2025-01-27):
Summary: NPS survey distributed, CSAT issues identified...
Key Outcomes:
  • NPS Score: 5.2 → TBD
  • CSAT Score: 3.1 → TBD irritating progress
  • Support Tickets: 45 → 32 (-29%)
Priority Actions:
  1. Schedule follow-up customer interview
  2. Review recent CSAT tickets
...
"""
```

### AI Response
```json
{
  "response": "For HealthFirst Medical Group, we recently executed a VoC Sprint playbook. 
               The playbook has reduced support tickets by 29% (from 45 to 32), but NPS and 
               CSAT are still in progress. The priority actions are to schedule a follow-up 
               interview and review recent CSAT tickets."
}
```

## Integration Points

### Three Levels of Playbook Context

#### 1. **Recent Playbook Executions** (Level 1)
```python
# backend/direct_rag_api.py - Line 31-120
def get_playbook_context(customer_id, query_text):
    """Get recent playbook insights for context enrichment"""
    reports = PlaybookReport.query.filter_by(customer_id=customer_id).limit(3).all()
    # Returns: Last 3 playbook executions with outcomes
```

**What's Included:**
- Playbook name
- Account name
- Execution date
- Executive summary
- Key outcomes achieved
- Priority next steps

#### 2. **System Playbook Knowledge** (Level 2)
```python
# backend/playbook_knowledge.py
def format_playbook_knowledge_for_rag():
    """Returns system-defined playbook descriptions"""
    return """
    VoC Sprint: Improve NPS by addressing customer feedback...
    Activation Blitz: Boost user adoption metrics...
    ...
    """
```

**What's Included:**
- 5 system playbooks
- Which KPIs each playbook impacts
- When to use each playbook

#### 3. **Playbook Trigger Thresholds** (Level 3)
```python
# backend/direct_rag_api.py - Line 266-285
triggers = PlaybookTrigger.query.filter_by(customer_id=customer_id).all()
# Returns: Current alert thresholds for automated triggering
```

**What's Included:**
- NPS threshold for VoC Sprint
- CSAT threshold for VoC Sprint
- Adoption thresholds for Activation Blitz
- Renewal probability for Renewal Safeguard
- Etc.

## Benefits for SaaS

### Advantages

✅ **Zero Manual Linking**: No need to manually link playbooks to RAG  
✅ **Auto-Sync**: New playbook executions automatically available in next RAG query  
✅ **Real-Time Context**: AI always has latest playbook insights  
✅ **Evidence-Based Recommendations**: AI can cite actual playbook outcomes  
✅ **Account-Specific Answers**: Matches account names to relevant playbooks  

### Data Flow

```
Execute Playbook
    ↓
Creates PlaybookReport in DB
    ↓
Next RAG Query
    ↓
Queries PlaybookReport Table
    ↓
Includes in AI Context
    ↓
AI Cites Actual Playbook Results ✅
```

## When Would You NEED Manual Updates?

### Only for Code Changes

Manual updates only needed if:
- ❌ You change playbook report structure
- ❌ You modify context enrichment logic
- ❌ You add new playbook types

### NOT for Data Updates

Never needed for:
- ✅ New playbook executions
- ✅ Updated playbook reports
- ✅ New playbook triggers
- ✅ Account-specific playbook matching

## Best Practices

### ✅ Do This

```python
# Just execute playbook and query RAG
POST /api/playbooks/recommendations/voc-sprint
# Next RAG query automatically includes this execution
POST /api/direct-rag/query
{"query": "What playbooks have been run for TechCorp Solutions?"}
# Returns: Recent VoC Sprint execution details
```

### ❌ Don't Do This

```bash
# Don't manually link playbooks to RAG (not needed)
curl -X POST /api/rag/link-playbooks
# System queries database directly on every RAG query
```

## Summary

**Playbook data is automatically integrated into RAG queries** from the database. The system queries recent `PlaybookReport` records, matches account names from the query, includes relevant insights in the AI's context, and generates responses that cite actual playbook outcomes.

**Execute playbook → Query RAG → Insights included automatically** 🎉

No manual "Link Playbooks to RAG" button needed!
