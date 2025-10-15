# 🤖 Playbook RAG/LLM Integration Points

## Overview

The playbook system has **specific steps** that integrate with RAG/LLM systems to generate intelligent insights and recommendations.

---

## 🎯 **RAG Integration Points**

### **1. VoC Sprint - RAG Brief Generation**

**Step ID**: `voc-rag-brief`  
**Step Title**: "Generate VoC Sprint Brief"  
**Type**: Automation  
**When**: Final step (after all manual work completed)

**RAG Prompt**:
```
"Generate a VoC sprint brief for {Account} using last 60 days of notes, tickets, and KPI deltas. List top 5 themes, customer quotes, and the 3 fastest actions with owners."
```

**Expected Output**:
```json
{
  "top_5_themes": "Array of theme objects with evidence",
  "customer_quotes": "Direct quotes supporting each theme",
  "fastest_actions": "3 prioritized actions with owners and timelines",
  "kpi_impact": "Expected NPS, CSAT, and sentiment improvements"
}
```

**Data Sources for RAG**:
- Last 60 days of customer notes
- Support tickets and resolutions
- KPI deltas and trends
- Interview transcripts (from earlier steps)
- QBR meeting notes

**Location in Code**:
- **File**: `src/lib/playbooks.ts`
- **Lines**: 152-169
- **Step Object**:
```typescript
{
  id: 'voc-rag-brief',
  title: 'Generate VoC Sprint Brief',
  description: 'Use RAG to generate comprehensive VoC sprint brief...',
  type: 'automation',
  data: {
    rag_prompt: "Generate a VoC sprint brief for {Account}...",
    output_format: { /* structured output */ }
  }
}
```

---

### **2. Activation Blitz - Activation Plan Generation**

**Step ID**: `activation-rag-plan`  
**Step Title**: "Generate Activation Plan"  
**Type**: Automation  
**When**: Final step (after activation activities)

**RAG Prompt**:
```
"Given {Account}'s low adoption and usage metrics, propose a 4-week activation plan with in-app steps, emails, and two KPIs to prove value by day 30."
```

**Expected Output**:
```json
{
  "activation_plan": "4-week structured activation plan",
  "in_app_steps": "Detailed in-app onboarding steps",
  "email_sequence": "Targeted email campaign sequence",
  "kpi_targets": "Two specific KPIs to prove value",
  "success_metrics": "Day 30 success measurement criteria"
}
```

**Data Sources for RAG**:
- Current adoption and usage metrics
- Feature utilization data
- User engagement patterns
- Support ticket analysis
- Customer feedback and surveys

**Location in Code**:
- **File**: `src/lib/playbooks.ts`
- **Lines**: 280-301
- **Step Object**:
```typescript
{
  id: 'activation-rag-plan',
  title: 'Generate Activation Plan',
  description: 'Use RAG to generate comprehensive 4-week activation plan...',
  type: 'automation',
  data: {
    rag_prompt: "Given {Account}'s low adoption and usage metrics...",
    output_format: { /* structured output */ }
  }
}
```

---

## 🔧 **How to Connect to RAG System**

### **Option 1: Automatic RAG Execution (When Step is Executed)**

When a step with `type: 'automation'` and `data.rag_prompt` is executed:

```typescript
// In playbook execution handler
async function executeStep(executionId, stepId) {
  const step = getStepById(stepId);
  
  if (step.type === 'automation' && step.data?.rag_prompt) {
    // This step needs RAG/LLM processing
    const ragResult = await callRAGSystem(step.data.rag_prompt, context);
    
    // Store result
    storeStepResult(executionId, stepId, ragResult);
  }
}
```

### **Option 2: Integration with Existing RAG APIs**

**Use Your Existing RAG Endpoints**:
- `/api/rag-openai/query` (OpenAI GPT-4)
- `/api/rag-qdrant/query` (Qdrant)
- `/api/rag/query` (Claude)
- `/api/query` (Unified Query API)

**Integration Code Example**:
```typescript
async function executeRAGStep(step, accountData) {
  // Replace {Account} placeholder with actual account name
  const prompt = step.data.rag_prompt.replace('{Account}', accountData.account_name);
  
  // Call your existing RAG system
  const response = await fetch('/api/query', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Customer-ID': accountData.customer_id.toString()
    },
    body: JSON.stringify({
      query: prompt,
      query_type: 'playbook_generation',
      force_routing: 'rag'  // Force to RAG, not deterministic
    })
  });
  
  const result = await response.json();
  return result.answer;  // RAG-generated response
}
```

---

## 📊 **Data Flow**

### **VoC Sprint RAG Flow**:
```
Manual Steps (Weeks 1-4)
  ↓
Customer interviews conducted
Support tickets analyzed
Themes identified manually
Executive approval obtained
  ↓
[Step: voc-rag-brief] ← RAG INTEGRATION POINT
  ↓
RAG System Receives:
- Account name
- Last 60 days of notes
- Ticket data
- KPI deltas
  ↓
RAG System Generates:
- Top 5 themes (synthesized)
- Customer quotes (extracted)
- 3 fastest actions (prioritized)
- KPI impact predictions
  ↓
Output stored in step results
  ↓
Report generated with RAG insights
```

### **Activation Blitz RAG Flow**:
```
Manual Steps (Weeks 1-4)
  ↓
Walkthroughs deployed
Training conducted
Use cases published
Success stories collected
  ↓
[Step: activation-rag-plan] ← RAG INTEGRATION POINT
  ↓
RAG System Receives:
- Account name
- Adoption metrics
- Usage patterns
- Feature data
  ↓
RAG System Generates:
- 4-week activation plan
- In-app onboarding steps
- Email campaign sequence
- KPI targets for day 30
  ↓
Output stored and displayed
```

---

## 🔌 **Implementation Locations**

### **Where RAG Prompts are Defined**:
**File**: `src/lib/playbooks.ts`

**VoC Sprint RAG Step**:
```typescript
// Lines 152-169
{
  id: 'voc-rag-brief',
  title: 'Generate VoC Sprint Brief',
  type: 'automation',
  data: {
    rag_prompt: "Generate a VoC sprint brief for {Account} using last 60 days...",
    output_format: {
      top_5_themes: "Array of theme objects with evidence",
      customer_quotes: "Direct quotes supporting each theme",
      fastest_actions: "3 prioritized actions with owners and timelines",
      kpi_impact: "Expected NPS, CSAT, and sentiment improvements"
    }
  }
}
```

**Activation Blitz RAG Step**:
```typescript
// Lines 280-301
{
  id: 'activation-rag-plan',
  title: 'Generate Activation Plan',
  type: 'automation',
  data: {
    rag_prompt: "Given {Account}'s low adoption and usage metrics...",
    output_format: {
      activation_plan: "4-week structured activation plan",
      in_app_steps: "Detailed in-app onboarding steps",
      email_sequence: "Targeted email campaign sequence",
      kpi_targets: "Two specific KPIs to prove value",
      success_metrics: "Day 30 success measurement criteria"
    }
  }
}
```

---

## 🛠️ **How to Implement RAG Execution**

### **Step 1: Detect RAG Steps**

```typescript
// In your step execution handler
const isRAGStep = step.type === 'automation' && step.data?.rag_prompt;

if (isRAGStep) {
  await executeRAGStep(step, executionContext);
}
```

### **Step 2: Call RAG System**

```typescript
async function executeRAGStep(step, context) {
  // Prepare prompt with account data
  const prompt = step.data.rag_prompt
    .replace('{Account}', context.accountName || 'the account');
  
  // Call your unified query API
  const response = await fetch('/api/query', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Customer-ID': context.customerId.toString()
    },
    body: JSON.stringify({
      query: prompt,
      query_type: 'playbook_analysis',
      force_routing: 'rag',  // Force RAG, not deterministic
      context: {
        account_id: context.accountId,
        playbook_id: step.playbookId,
        step_id: step.id,
        time_range: 60  // days
      }
    })
  });
  
  const result = await response.json();
  
  // Parse RAG response according to output_format
  return parseRAGResponse(result.answer, step.data.output_format);
}
```

### **Step 3: Store RAG Results**

```typescript
// Store in step results
const stepResult = {
  stepId: step.id,
  status: 'completed',
  completedAt: new Date().toISOString(),
  data: {
    rag_generated: true,
    prompt_used: step.data.rag_prompt,
    rag_response: ragResult,
    model_used: 'GPT-4' // or Claude, etc.
  }
};

// Add to execution results
execution.results.push(stepResult);
```

---

## 📋 **RAG Steps Summary**

| Playbook | Step ID | Step Name | RAG Prompt | Output |
|----------|---------|-----------|------------|--------|
| VoC Sprint | `voc-rag-brief` | Generate VoC Sprint Brief | "Generate VoC sprint brief for {Account}..." | 5 themes, quotes, 3 actions |
| Activation Blitz | `activation-rag-plan` | Generate Activation Plan | "Given {Account}'s low adoption..." | 4-week plan, steps, emails, KPIs |
| SLA Stabilizer | TBD | TBD | TBD | TBD |
| Renewal Safeguard | TBD | TBD | TBD | TBD |
| Expansion Timing | TBD | TBD | TBD | TBD |

---

## 🎯 **Current Status**

### **✅ RAG Integration Points Defined**:
- VoC Sprint: RAG brief generation (step 12/12)
- Activation Blitz: Activation plan generation (step 9/9)

### **⏳ Implementation Needed**:
1. Add RAG step execution handler
2. Connect to existing `/api/query` endpoint
3. Parse RAG responses
4. Display RAG-generated content in reports
5. Add RAG execution indicators in UI

### **🔧 Recommended Approach**:
1. When user clicks an "automation" step with RAG prompt
2. Show loading indicator: "Generating with AI..."
3. Call `/api/query` with the step's RAG prompt
4. Parse response into structured format
5. Display in step results
6. Include in comprehensive report

---

## 💡 **Integration Example**

```typescript
// In Playbooks.tsx or playbook-manager.ts
async function handleExecuteStep(executionId, stepId) {
  const step = getStepById(stepId);
  
  // Check if this is a RAG step
  if (step.type === 'automation' && step.data?.rag_prompt) {
    // Show loading
    setStepExecuting(stepId);
    
    try {
      // Get execution context
      const execution = getExecution(executionId);
      const accountName = execution.context?.accountName || 'the account';
      
      // Prepare RAG query
      const prompt = step.data.rag_prompt.replace('{Account}', accountName);
      
      // Call RAG system
      const ragResponse = await fetch('/api/query', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Customer-ID': execution.customerId.toString()
        },
        body: JSON.stringify({
          query: prompt,
          force_routing: 'rag'
        })
      });
      
      const ragResult = await ragResponse.json();
      
      // Store result
      const stepResult = {
        stepId,
        status: 'completed',
        completedAt: new Date().toISOString(),
        data: {
          rag_generated: true,
          rag_response: ragResult.answer,
          sources: ragResult.result?.relevant_results
        }
      };
      
      // Update execution
      await updateStepResult(executionId, stepResult);
      
      // Show success
      alert('AI-generated brief created successfully!');
      
    } catch (error) {
      console.error('RAG step failed:', error);
      alert('Failed to generate AI brief');
    }
  } else {
    // Regular step execution
    await normalStepExecution(executionId, stepId);
  }
}
```

---

## 🎯 **Summary**

### **RAG/LLM Integration Points**:

**Current (Implemented)**:
- ✅ **2 playbooks** have RAG steps defined
- ✅ **RAG prompts** are stored in step data
- ✅ **Output formats** are specified
- ✅ **Step type** is marked as 'automation'

**To Complete Integration**:
- ⏳ Add handler to detect RAG steps
- ⏳ Call `/api/query` when RAG step is executed
- ⏳ Parse and store RAG responses
- ⏳ Display RAG-generated content
- ⏳ Include RAG insights in reports

**The infrastructure is ready - just need to connect the step execution to your existing RAG endpoints!** 🚀
