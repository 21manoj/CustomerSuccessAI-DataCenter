# V3 Implementation Plan

## Overview
V3 introduces conversational AI capabilities, improved UX, and enhanced playbook integration to the Customer Success Value Management System.

---

## ✅ Completed Changes

### 1. Login Screen Update
**File:** `src/components/LoginComponent.tsx`

**Changes:**
- ✅ Removed hardcoded demo credentials display
- ✅ Added professional contact message: "For demo credentials, please email info@triadpartners.ai"
- ✅ Styled with blue highlight box for better visibility

**Impact:** More professional, secure login experience

---

### 2. Conversational RAG - Part 1 (Frontend)
**File:** `src/components/RAGAnalysis.tsx`

**Changes:**
- ✅ Added `ConversationMessage` interface for chat history
- ✅ Implemented `conversationHistory` state with localStorage persistence
- ✅ Conversation auto-loads on component mount (per customer)
- ✅ Conversation auto-saves on every update
- ✅ Auto-scroll to bottom when new messages arrive
- ✅ Modified `executeQuery` to:
  - Include last 3 conversation exchanges as context
  - Add successful queries to conversation history
  - Clear input field after sending
- ✅ Added `clearConversation()` function to reset chat

**Storage Key:** `rag_conversation_${customer_id}`

**Impact:** Users can have multi-turn conversations with AI, context is preserved across page refreshes

---

## 🚧 Pending Changes

### 3. Backend - Conversation History Support
**Files to modify:**
- `backend/direct_rag_api.py`
- `backend/enhanced_rag_openai_api.py`
- `backend/rag_qdrant_api.py` (if used)

**Required Changes:**
```python
@direct_rag_api.route('/api/direct-rag/query', methods=['POST'])
def query():
    data = request.json
    query_text = data['query']
    query_type = data.get('query_type', 'general')
    conversation_history = data.get('conversation_history', [])  # NEW
    
    # Include conversation_history in RAG prompt
    context_prompt = build_context_with_history(conversation_history, query_text)
    
    # ... rest of implementation
```

**Implementation Steps:**
1. Update all RAG query endpoints to accept `conversation_history` parameter
2. Build conversation context string from history
3. Prepend conversation context to user query or system prompt
4. Test with follow-up questions

---

### 4. UI Enhancement - Conversation Thread View
**File:** `src/components/RAGAnalysis.tsx`

**Required Changes:**
- Replace single response view with scrollable conversation thread
- Show all messages in history with timestamps
- Style user queries vs AI responses differently
- Add "Clear Conversation" button in header
- Keep quick query templates collapsible/expandable

**UI Layout:**
```
┌────────────────────────────────────────┐
│ AI Insights        [Clear Conversation]│
├────────────────────────────────────────┤
│  Quick Query Templates (collapsible)   │
├────────────────────────────────────────┤
│ ┌────────────────────────────────────┐ │
│ │  Conversation History (scrollable) │ │
│ │                                    │ │
│ │  You: Which accounts are at risk?  │ │
│ │  10:30 AM                          │ │
│ │                                    │ │
│ │  AI: Based on analysis, 3 accounts │ │
│ │  show churn risk: TechCorp...      │ │
│ │  10:30 AM                          │ │
│ │                                    │ │
│ │  You: What about TechCorp          │ │
│ │  specifically?                     │ │
│ │  10:31 AM                          │ │
│ │                                    │ │
│ │  AI: TechCorp has...               │ │
│ │  10:31 AM                          │ │
│ │                                    │ │
│ └────────────────────────────────────┘ │
│  [Type your question here...]  [Send]  │
└────────────────────────────────────────┘
```

---

### 5. Playbook Insights Integration
**Files to modify:**
- `backend/direct_rag_api.py`
- `backend/enhanced_rag_openai_api.py`

**Required Changes:**
1. Fetch active/completed playbooks for customer
2. Include playbook context in RAG queries:
   - Executed playbooks with outcomes
   - Playbook recommendations per account
   - KPI improvements from playbooks
3. Format playbook insights for AI context

**Implementation:**
```python
def get_playbook_insights(customer_id):
    # Get recent playbook executions
    executions = PlaybookExecution.query.filter_by(
        customer_id=customer_id
    ).order_by(PlaybookExecution.started_at.desc()).limit(10).all()
    
    insights = []
    for exec in executions:
        reports = PlaybookReport.query.filter_by(execution_id=exec.id).all()
        insights.append({
            'playbook': exec.playbook_type,
            'account': exec.account.name,
            'status': exec.status,
            'outcomes': [r.content for r in reports]
        })
    
    return format_playbook_context(insights)

# In RAG query:
playbook_context = get_playbook_insights(customer_id)
full_context = f"{kpi_context}\n\n{playbook_context}\n\n{conversation_context}"
```

---

### 6. Deterministic Query Detection
**Files to create/modify:**
- `backend/query_classifier.py` (new)
- `backend/direct_rag_api.py`

**Query Types to Detect:**
1. **Playbook Queries** → Query database directly
   - "Which playbooks are running?"
   - "Show me playbook results for TechCorp"
   - "What playbooks should I run?"

2. **Account Queries** → Query database directly
   - "List all accounts"
   - "Show me accounts in Technology industry"
   - "Which accounts have health score < 50?"

3. **KPI Queries** → Query database directly
   - "What is the NPS for TechCorp?"
   - "Show me churn risk across all accounts"
   - "List KPIs for Financial Services accounts"

4. **Analytical Queries** → Use RAG/AI
   - "Why is TechCorp's health declining?"
   - "What should I do about low NPS?"
   - "How can I improve customer satisfaction?"

**Implementation:**
```python
class QueryClassifier:
    def classify(self, query: str) -> dict:
        query_lower = query.lower()
        
        # Deterministic patterns
        if any(word in query_lower for word in ['list', 'show me', 'which accounts', 'all accounts']):
            return {'type': 'database', 'subtype': 'account_list'}
        
        if any(word in query_lower for word in ['what is', 'current value', 'score for']):
            return {'type': 'database', 'subtype': 'kpi_lookup'}
        
        if any(word in query_lower for word in ['playbook', 'running', 'executed']):
            return {'type': 'database', 'subtype': 'playbook_query'}
        
        # Analytical patterns
        if any(word in query_lower for word in ['why', 'how', 'should', 'recommend', 'improve']):
            return {'type': 'rag', 'subtype': 'analytical'}
        
        return {'type': 'rag', 'subtype': 'general'}

# In RAG API:
classifier = QueryClassifier()
query_class = classifier.classify(query_text)

if query_class['type'] == 'database':
    return execute_database_query(query_text, query_class['subtype'])
else:
    return execute_rag_query(query_text, conversation_history)
```

---

### 7. Enhanced Response Formatting
**File:** `src/components/RAGAnalysis.tsx`

**Improvements:**
- Parse markdown formatting from AI responses
- Show data sources (Database, Playbooks, Historical Analysis)
- Add quick action buttons for relevant queries:
  - "Start Playbook" (if AI recommends one)
  - "View Account" (if discussing specific account)
  - "View KPI Details" (if discussing specific KPI)

---

## 📋 Testing Checklist

### Frontend Testing:
- [ ] Login page shows new email message
- [ ] Conversation persists across page refreshes
- [ ] Conversation persists across tab navigation
- [ ] Clear conversation button works
- [ ] Auto-scroll works for new messages
- [ ] Multiple customers have separate conversations

### Backend Testing:
- [ ] Conversation history is included in RAG context
- [ ] Follow-up questions work correctly
- [ ] Playbook insights are included in responses
- [ ] Deterministic queries return instant results
- [ ] Analytical queries use RAG/AI properly

### Integration Testing:
- [ ] Ask: "Which accounts are at risk?" → DB query (instant)
- [ ] Ask: "Why is TechCorp at risk?" → RAG query (with playbook context)
- [ ] Ask: "What should I do?" → RAG recommends playbook
- [ ] Navigate to Playbooks tab and back → conversation persists
- [ ] Start new session → conversation history loads

---

## 🚀 Deployment Steps

### 1. Local Testing
```bash
# Frontend
cd /Users/manojgupta/kpi-dashboard
npm start

# Backend
./venv/bin/python backend/run_server.py

# Test all scenarios in checklist
```

### 2. Build Production
```bash
# Build React app
npm run build

# Test production build
serve -s build -p 3000
```

### 3. Deploy to AWS EC2 (V3)
```bash
# Create deployment package
tar -czf kpi-dashboard-v3.tar.gz \
  backend/ \
  build/ \
  migrations/ \
  Maturity-Framework-KPI-loveable.xlsx \
  .env \
  requirements.txt

# Upload to EC2
scp -i kpi-dashboard-key.pem kpi-dashboard-v3.tar.gz ec2-user@3.84.178.121:/home/ec2-user/

# SSH and deploy
ssh -i kpi-dashboard-key.pem ec2-user@3.84.178.121
cd /home/ec2-user
tar -xzf kpi-dashboard-v3.tar.gz -C kpi-dashboard-v3/
cd kpi-dashboard-v3

# Stop V2, start V3
docker stop kpi-dashboard-v2 kpi-dashboard-frontend-v2
docker build -t kpi-dashboard:v3 .
docker run -d --name kpi-dashboard-v3 \
  -p 8090:8080 \
  -v $(pwd)/instance:/app/instance \
  --restart unless-stopped \
  kpi-dashboard:v3

# Update Nginx to point to port 8090
# Test at https://customervaluesystem.triadpartners.ai
```

---

## 💡 Future Enhancements (V4)

1. **Voice Input:** Use Web Speech API for voice queries
2. **Export Conversations:** Download chat history as PDF
3. **Shared Conversations:** Share specific Q&A with team
4. **Suggested Follow-ups:** AI suggests next questions
5. **Multi-language Support:** Translate conversations
6. **Conversation Branching:** Fork conversation at any point
7. **Conversation Templates:** Save common query sequences

---

## 📊 Success Metrics

- **User Engagement:** % of users using conversational features
- **Query Success Rate:** % of queries answered satisfactorily
- **Response Time:** Average time for deterministic vs RAG queries
- **Playbook Adoption:** % increase in playbook starts from AI recommendations
- **Session Length:** Increase in average questions per session

---

**Status:** 🟡 In Progress (30% complete)  
**Branch:** `feature/v3-enhancements`  
**Target Release:** After V3 testing complete

