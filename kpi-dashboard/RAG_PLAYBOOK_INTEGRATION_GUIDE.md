# RAG + Playbook Integration Guide

## Overview
This guide shows how to enhance your RAG (Retrieval-Augmented Generation) queries in "AI Insights" using the rich data from completed playbook reports.

## Why This Matters

**Current RAG Knowledge Base:**
- KPI metrics and trends
- Account information
- Basic health scores

**Playbook Reports Add:**
- ✅ **Proven outcomes** with before/after metrics
- ✅ **Root cause analysis** from expert investigations
- ✅ **Customer quotes** and direct feedback
- ✅ **Action plans** with assigned owners
- ✅ **Risk assessments** with mitigation strategies
- ✅ **Success patterns** across accounts

---

## Integration Approaches

### **Level 1: Context Enrichment (Quick - 15 mins)**

Add playbook insights to RAG query context without changing the index.

**File:** `backend/enhanced_rag_openai.py`

```python
def get_playbook_context(self, account_id=None):
    """Get recent playbook insights for query context"""
    from models import PlaybookReport
    
    query = PlaybookReport.query.filter_by(customer_id=self.customer_id)
    if account_id:
        query = query.filter_by(account_id=account_id)
    
    reports = query.order_by(PlaybookReport.report_generated_at.desc()).limit(3).all()
    
    if not reports:
        return ""
    
    context = "\n\n=== RECENT PLAYBOOK INSIGHTS ===\n"
    for report in reports:
        data = report.report_data
        context += f"\n{data.get('playbook_name')} - {report.account_name}:\n"
        context += f"Summary: {data.get('executive_summary', '')[:200]}...\n"
        
        # Add key outcomes
        outcomes = data.get('outcomes_achieved', {})
        if outcomes:
            context += "Key outcomes:\n"
            for key, outcome in list(outcomes.items())[:2]:
                if isinstance(outcome, dict):
                    context += f"  - {key}: {outcome.get('improvement', 'N/A')} ({outcome.get('status', 'N/A')})\n"
    
    return context

# Then in your query() method, after retrieving context:
playbook_context = self.get_playbook_context(account_id)
full_context = context + playbook_context
```

### **Level 2: Index Playbook Data (Medium - 1 hour)**

Add playbook reports to your FAISS knowledge base for semantic search.

**File:** `backend/enhanced_rag_openai.py`

Add this method to `EnhancedRAGSystemOpenAI` class:

```python
def _index_playbook_reports(self):
    """Index playbook report insights into knowledge base"""
    from models import PlaybookReport
    
    print(f"Indexing playbook reports for customer {self.customer_id}...")
    
    reports = PlaybookReport.query.filter_by(
        customer_id=self.customer_id
    ).order_by(PlaybookReport.report_generated_at.desc()).limit(50).all()
    
    indexed_count = 0
    
    for report in reports:
        data = report.report_data
        playbook_name = data.get('playbook_name', 'Unknown')
        account_name = report.account_name or 'Unknown'
        
        # Index executive summary
        if data.get('executive_summary'):
            self.documents.append({
                'type': 'playbook_summary',
                'playbook': playbook_name,
                'account': account_name,
                'date': report.report_generated_at.strftime('%Y-%m-%d'),
                'content': f"Playbook: {playbook_name} for {account_name}. {data['executive_summary']}"
            })
            indexed_count += 1
        
        # Index specific outcomes
        outcomes = data.get('outcomes_achieved', {})
        for outcome_key, outcome_data in outcomes.items():
            if isinstance(outcome_data, dict):
                baseline = outcome_data.get('baseline', 'N/A')
                current = outcome_data.get('current', 'N/A')
                improvement = outcome_data.get('improvement', 'N/A')
                status = outcome_data.get('status', 'Unknown')
                
                self.documents.append({
                    'type': 'playbook_outcome',
                    'playbook': playbook_name,
                    'account': account_name,
                    'metric': outcome_key,
                    'content': f"{playbook_name} outcome for {account_name}: {outcome_key} improved from {baseline} to {current} ({improvement}). Status: {status}"
                })
                indexed_count += 1
        
        # Index next steps / recommendations
        for step in data.get('next_steps', [])[:3]:
            self.documents.append({
                'type': 'playbook_action',
                'playbook': playbook_name,
                'account': account_name,
                'content': f"Recommended action from {playbook_name} for {account_name}: {step}"
            })
            indexed_count += 1
        
        # Index VoC themes (if VoC Sprint)
        if playbook_name == 'VoC Sprint':
            for theme in data.get('themes_discovered', [])[:3]:
                theme_text = theme.get('theme', '') if isinstance(theme, dict) else str(theme)
                self.documents.append({
                    'type': 'customer_feedback',
                    'playbook': playbook_name,
                    'account': account_name,
                    'content': f"Customer feedback theme from {account_name}: {theme_text}"
                })
                indexed_count += 1
        
        # Index risk assessment (if Renewal Safeguard)
        if playbook_name == 'Renewal Safeguard':
            risk_data = data.get('risk_assessment', {})
            for risk in risk_data.get('key_risks_identified', [])[:3]:
                if isinstance(risk, dict):
                    self.documents.append({
                        'type': 'risk_assessment',
                        'playbook': playbook_name,
                        'account': account_name,
                        'content': f"Risk for {account_name}: {risk.get('risk', '')} (Severity: {risk.get('severity', 'Unknown')}, Status: {risk.get('status', 'Unknown')})"
                    })
                    indexed_count += 1
        
        # Index expansion opportunities (if Expansion Timing)
        if playbook_name == 'Expansion Timing':
            for opp in data.get('expansion_opportunities', [])[:3]:
                if isinstance(opp, dict):
                    self.documents.append({
                        'type': 'expansion_opportunity',
                        'playbook': playbook_name,
                        'account': account_name,
                        'content': f"Expansion opportunity for {account_name}: {opp.get('opportunity', '')} - {opp.get('size', '')} (Probability: {opp.get('probability', 'Unknown')})"
                    })
                    indexed_count += 1
    
    print(f"✓ Indexed {indexed_count} playbook insights from {len(reports)} reports")
    return indexed_count

# Call this in build_knowledge_base() method after indexing KPIs:
# Add this line after self._index_kpi_data():
self._index_playbook_reports()
```

### **Level 3: Smart Query Templates (Advanced - 2 hours)**

Create intelligent query templates that automatically pull playbook insights.

**File:** `backend/query_router.py`

```python
PLAYBOOK_QUERY_PATTERNS = {
    'improvement_tracking': {
        'keywords': ['improve', 'progress', 'change', 'better', 'outcome'],
        'playbook_priority': ['voc-sprint', 'activation-blitz', 'sla-stabilizer'],
        'extract_fields': ['outcomes_achieved', 'executive_summary']
    },
    'risk_analysis': {
        'keywords': ['risk', 'churn', 'renewal', 'concern', 'issue'],
        'playbook_priority': ['renewal-safeguard', 'sla-stabilizer'],
        'extract_fields': ['risk_assessment', 'key_risks_identified']
    },
    'action_planning': {
        'keywords': ['next', 'action', 'todo', 'plan', 'priority'],
        'playbook_priority': ['all'],
        'extract_fields': ['next_steps', 'raci_matrix']
    },
    'expansion_opportunities': {
        'keywords': ['expand', 'upsell', 'opportunity', 'growth'],
        'playbook_priority': ['expansion-timing'],
        'extract_fields': ['expansion_opportunities', 'value_propositions']
    }
}
```

---

## Example Queries Enhanced by Playbook Data

### **Before (KPI-only RAG)**
**Query:** "How has Acme Corp improved?"

**Response:**
```
Based on recent KPI data, Acme Corp shows:
- NPS increased from 6 to 14
- CSAT improved to 3.6
```

### **After (With Playbook Intelligence)**
**Query:** "How has Acme Corp improved?"

**Response:**
```
Acme Corp has shown significant improvement through our VoC Sprint playbook (completed Nov 13, 2025):

📊 Measured Outcomes:
- NPS: 6.5 → 14.2 (+7.7 points, exceeding +6-10 target by 25%)
- CSAT: 3.2 → 3.6 (+0.4 points, exceeding +0.2-0.3 target)
- Ticket sentiment: Negative → Positive trend
- Renewal intent: 62% → 78% (+16%)

🎯 Root Causes Identified:
1. Pricing concerns (45% of interviews)
2. Feature gaps in reporting (30%)
3. Support response time issues (25%)

✅ Actions Taken:
1. Enhanced onboarding process (Owner: CSM Team) - COMPLETED
2. Feature request prioritized for Q1 release (Owner: Product) - PLANNED
3. Support ticket prioritization improved (Owner: Support Lead) - IMPLEMENTED

💡 Customer Quote:
"The new onboarding process addressed our main pain points. We're seeing 40% faster time-to-value."

📈 Next Steps:
- Monitor NPS weekly for sustained improvement
- Track implementation of 3 committed fixes
- Follow-up NPS survey in 45 days
```

---

## **Quick Implementation Steps**

### **Step 1: Add Helper Method (5 mins)**

Add to `backend/enhanced_rag_openai.py`:

```python
def get_playbook_insights_summary(self, account_id=None):
    """Get a formatted summary of recent playbook insights"""
    from models import PlaybookReport
    
    query = PlaybookReport.query.filter_by(customer_id=self.customer_id)
    if account_id:
        query = query.filter_by(account_id=account_id)
    
    reports = query.order_by(PlaybookReport.report_generated_at.desc()).limit(5).all()
    
    if not reports:
        return None
    
    summary = {
        'total_reports': len(reports),
        'reports': []
    }
    
    for report in reports:
        data = report.report_data
        summary['reports'].append({
            'playbook': data.get('playbook_name'),
            'account': report.account_name,
            'date': report.report_generated_at.strftime('%Y-%m-%d'),
            'summary': data.get('executive_summary', '')[:150],
            'key_outcome': self._extract_key_outcome(data.get('outcomes_achieved', {})),
            'top_next_step': data.get('next_steps', ['None'])[0] if data.get('next_steps') else 'None'
        })
    
    return summary

def _extract_key_outcome(self, outcomes):
    """Extract the most impactful outcome"""
    for key, value in outcomes.items():
        if isinstance(value, dict) and value.get('status') in ['Exceeded', 'Achieved']:
            return f"{key}: {value.get('improvement', 'Improved')}"
    return "Multiple outcomes achieved"
```

### **Step 2: Integrate into Query (5 mins)**

In your `query()` method, add before calling OpenAI:

```python
# Add playbook intelligence
playbook_insights = self.get_playbook_insights_summary(account_id)

if playbook_insights:
    system_prompt += f"\n\nYou also have access to recent playbook execution insights:\n{json.dumps(playbook_insights, indent=2)}"
    system_prompt += "\nUse these playbook insights to provide concrete, evidence-based answers with specific metrics and action plans."
```

### **Step 3: Test** (5 mins)

```bash
# Restart backend
cd /Users/manojgupta/kpi-dashboard && ./venv/bin/python backend/run_server.py

# Test queries in AI Insights:
1. "What improvements have we made?"
2. "Which accounts need attention?"
3. "Show me recent success stories"
4. "What are our top priorities?"
```

---

## **Advanced: Account-Specific Context**

For account-specific queries, add account filtering:

```python
def enhance_account_query(self, query_text, account_id):
    """Enhance query with account-specific playbook context"""
    from models import PlaybookReport
    
    # Get playbook reports for this account
    reports = PlaybookReport.query.filter_by(
        customer_id=self.customer_id,
        account_id=account_id
    ).order_by(PlaybookReport.report_generated_at.desc()).limit(3).all()
    
    if not reports:
        return query_text
    
    enriched_query = f"{query_text}\n\nConsider these recent playbook executions:\n"
    
    for report in reports:
        data = report.report_data
        enriched_query += f"- {data.get('playbook_name')}: {data.get('executive_summary', '')[:100]}...\n"
    
    return enriched_query
```

---

## **Monitoring Impact**

Track the effectiveness of playbook-enhanced RAG:

```python
# Add to query caching:
cache_entry = {
    'query': query_text,
    'response': response,
    'used_playbook_data': True if playbook_insights else False,
    'playbook_count': len(playbook_insights['reports']) if playbook_insights else 0,
    'timestamp': datetime.utcnow().isoformat()
}
```

---

## **Benefits**

✅ **Richer Answers** - Evidence-based responses with specific metrics  
✅ **Action-Oriented** - Concrete next steps with owners  
✅ **Historical Context** - Learn from past successful interventions  
✅ **Pattern Recognition** - Identify what works across accounts  
✅ **Risk Detection** - Proactive alerts based on playbook triggers  
✅ **Outcome Tracking** - Measure impact of interventions  

---

## **Next Steps**

1. **Start with Level 1** (Context Enrichment) - 15 minutes, immediate impact
2. **Add Level 2** (Index Reports) - 1 hour, comprehensive search
3. **Test thoroughly** - Try various query types
4. **Monitor usage** - Track which queries benefit most
5. **Iterate** - Refine based on user feedback

All the data is already there in your `playbook_reports` table - you just need to surface it! 🚀

