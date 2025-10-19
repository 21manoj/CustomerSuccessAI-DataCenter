# V3 Testing Plan

## Test Environment
- **Local:** http://localhost:3000
- **Backend:** http://localhost:5059
- **Branch:** feature/v3-enhancements

---

## Test Scenarios

### 1. Login Screen Tests

#### Test 1.1: New Login Message
**Steps:**
1. Open http://localhost:3000
2. Verify login screen shows

**Expected:**
- ✅ Bottom of login form shows blue box
- ✅ Text reads: "For demo credentials, please email info@triadpartners.ai"
- ✅ Email link is clickable (mailto:info@triadpartners.ai)
- ✅ No hardcoded credentials shown

**Actual:** _____

---

### 2. Conversation UI Tests

#### Test 2.1: First Conversation
**Steps:**
1. Login as test@test.com / test123
2. Go to "AI Insights" tab
3. Type: "Which accounts have highest revenue?"
4. Press Enter

**Expected:**
- ✅ Message appears on right side (blue bubble)
- ✅ Loading indicator shows ("AI is thinking...")
- ✅ AI response appears on left side (gray bubble)
- ✅ Message shows timestamp
- ✅ Input field clears after sending
- ✅ Conversation auto-scrolls to bottom

**Actual:** _____

#### Test 2.2: Follow-up Questions (Context Awareness)
**Steps:**
1. After Test 2.1, ask: "Tell me more about the first one"
2. Observe response

**Expected:**
- ✅ AI understands "the first one" refers to top revenue account from previous query
- ✅ Response is contextually relevant
- ✅ Both messages visible in thread

**Actual:** _____

#### Test 2.3: Conversation Persistence - Page Refresh
**Steps:**
1. After having 2-3 exchanges, refresh the page (F5)
2. Navigate back to "AI Insights" tab

**Expected:**
- ✅ All conversation history loads from localStorage
- ✅ Messages display in correct order
- ✅ Timestamps preserved
- ✅ Can continue conversation where left off

**Actual:** _____

#### Test 2.4: Conversation Persistence - Tab Navigation
**Steps:**
1. Have 2-3 exchanges in AI Insights
2. Navigate to "Customer Success Performance Console" tab
3. Navigate to "Playbooks" tab
4. Navigate back to "AI Insights"

**Expected:**
- ✅ Conversation history still visible
- ✅ No messages lost
- ✅ Can continue conversation

**Actual:** _____

#### Test 2.5: Clear Conversation
**Steps:**
1. Have 3-4 exchanges
2. Click "Clear Conversation" button

**Expected:**
- ✅ All messages disappear
- ✅ Empty state shown ("Start a conversation")
- ✅ Input field ready for new query
- ✅ localStorage cleared

**Actual:** _____

#### Test 2.6: Multiple Customers
**Steps:**
1. Login as test@test.com, have conversation
2. Logout
3. Login as acme@acme.com, have different conversation
4. Logout
5. Login as test@test.com again

**Expected:**
- ✅ Test Company conversation restored (not ACME's)
- ✅ Each customer has separate conversation history
- ✅ No cross-contamination

**Actual:** _____

---

### 3. Playbook Insights Tests

#### Test 3.1: Playbook in Response
**Steps:**
1. Run a playbook first (e.g., VoC Sprint for any account)
2. Ask: "Which playbooks have been executed?"

**Expected:**
- ✅ AI mentions specific playbook names
- ✅ Includes account names
- ✅ Shows dates
- ✅ Badge shows "✓ Enhanced with Playbook Insights"

**Actual:** _____

#### Test 3.2: Playbook Recommendations
**Steps:**
1. Ask: "Which playbooks can improve NRR?"

**Expected:**
- ✅ AI recommends ONLY system playbooks:
  - Renewal Safeguard
  - Expansion Timing
- ✅ Explains why these help NRR
- ✅ NO generic playbook names

**Actual:** _____

---

### 4. Conversation Context Tests

#### Test 4.1: Pronoun Resolution
**Steps:**
1. Ask: "Which accounts are at risk?"
2. Follow up: "What about the second one?"
3. Follow up: "How can I help them?"

**Expected:**
- ✅ Q2 response discusses the second account from Q1
- ✅ Q3 response provides help for that same account
- ✅ Context maintained across 3 turns

**Actual:** _____

#### Test 4.2: Topic Continuation
**Steps:**
1. Ask: "Show me NPS trends"
2. Follow up: "Why is it declining?"
3. Follow up: "What should I do?"

**Expected:**
- ✅ Q2 discusses NPS decline (knows "it" = NPS)
- ✅ Q3 provides actions for NPS (knows context)
- ✅ Recommendations reference earlier data

**Actual:** _____

---

### 5. Query Classifier Tests

#### Test 5.1: Deterministic Query (Fast)
**Steps:**
1. Ask: "List all accounts"
2. Measure response time

**Expected:**
- ✅ Response within 0.5 seconds (database query)
- ✅ Lists all accounts with details
- ✅ No "AI is thinking" delay

**Actual:** _____

#### Test 5.2: Analytical Query (RAG)
**Steps:**
1. Ask: "Why is TechCorp's health declining?"
2. Measure response time

**Expected:**
- ✅ Response takes 2-5 seconds (OpenAI call)
- ✅ Shows "AI is thinking..." while processing
- ✅ Provides analytical insights, not just data

**Actual:** _____

---

### 6. UX Tests

#### Test 6.1: Keyboard Shortcuts
**Steps:**
1. Type a message
2. Press Enter (should send)
3. Type a message
4. Press Shift+Enter (should create new line, not send)
5. Press Enter (should send)

**Expected:**
- ✅ Enter sends message
- ✅ Shift+Enter creates new line
- ✅ Help text visible: "Press Enter to send, Shift+Enter for new line"

**Actual:** _____

#### Test 6.2: Long Conversations
**Steps:**
1. Have 10+ exchanges
2. Observe scrolling behavior

**Expected:**
- ✅ Conversation area scrolls
- ✅ Auto-scrolls to newest message
- ✅ Can manually scroll up to see history
- ✅ Quick templates remain visible

**Actual:** _____

#### Test 6.3: Empty States
**Steps:**
1. Clear conversation
2. Observe empty state

**Expected:**
- ✅ Shows MessageSquare icon (faded)
- ✅ Text: "Start a conversation"
- ✅ Subtext: "Ask questions about your accounts, KPIs, or playbooks"

**Actual:** _____

---

### 7. Data Source Badge Tests

#### Test 7.1: Playbook Enhanced Badge
**Steps:**
1. Run a playbook for TechCorp
2. Ask: "What playbooks have run for TechCorp?"

**Expected:**
- ✅ Response shows green badge: "✓ Enhanced with Playbook Insights"
- ✅ AI mentions specific playbook execution

**Actual:** _____

#### Test 7.2: MCP Badges (if enabled)
**Steps:**
1. Enable MCP in Advanced Settings
2. Ask any question

**Expected:**
- ✅ Shows source badges (Database, Salesforce, ServiceNow, Surveys)
- ✅ Only enabled systems shown

**Actual:** _____

---

### 8. Error Handling Tests

#### Test 8.1: Empty Query
**Steps:**
1. Click "Send" without typing anything

**Expected:**
- ✅ Button is disabled
- ✅ Nothing happens

**Actual:** _____

#### Test 8.2: Backend Down
**Steps:**
1. Stop backend server
2. Try to send a message

**Expected:**
- ✅ Error message shown
- ✅ Conversation history preserved
- ✅ Can retry after backend restarts

**Actual:** _____

---

### 9. Integration Tests

#### Test 9.1: Full User Journey
**Steps:**
1. Login
2. Ask: "Which accounts are at risk?"
3. AI responds with 3 accounts
4. Ask: "Tell me about TechCorp"
5. AI provides TechCorp details
6. Ask: "What playbooks should I run?"
7. AI recommends playbooks
8. Navigate to Playbooks tab
9. Start recommended playbook
10. Navigate back to AI Insights

**Expected:**
- ✅ Conversation preserved throughout
- ✅ Context maintained across all questions
- ✅ Playbook recommendation is actionable
- ✅ After playbook starts, can ask "What did I just start?"

**Actual:** _____

---

### 10. Performance Tests

#### Test 10.1: Conversation Load Time
**Steps:**
1. Create 20-message conversation
2. Refresh page
3. Measure load time

**Expected:**
- ✅ Loads within 1 second
- ✅ All 20 messages visible
- ✅ No lag when scrolling

**Actual:** _____

---

## Bug Tracking

| Bug ID | Description | Severity | Status |
|--------|-------------|----------|--------|
| | | | |

---

## Test Results Summary

**Date:** _____  
**Tester:** _____  
**Build:** feature/v3-enhancements  

| Category | Tests Passed | Tests Failed | Pass Rate |
|----------|-------------|--------------|-----------|
| Login Screen | _ / 1 | _ | _% |
| Conversation UI | _ / 6 | _ | _% |
| Playbook Insights | _ / 2 | _ | _% |
| Conversation Context | _ / 2 | _ | _% |
| Query Classifier | _ / 2 | _ | _% |
| UX | _ / 3 | _ | _% |
| Data Sources | _ / 2 | _ | _% |
| Error Handling | _ / 2 | _ | _% |
| Integration | _ / 1 | _ | _% |
| Performance | _ / 1 | _ | _% |

**Total:** _ / 22 tests passed

**Recommendation:** [ ] Ready for Production  [ ] Needs Fixes

---

## Deployment Checklist

After all tests pass:

- [ ] All tests green
- [ ] No console errors in browser
- [ ] No backend errors in logs
- [ ] Performance acceptable (< 5s for RAG queries)
- [ ] Conversation persists correctly
- [ ] Multiple customers work independently
- [ ] Build succeeds
- [ ] Documentation updated
- [ ] Git pushed to remote
- [ ] Ready for AWS deployment

