# Gap Fix Plan — AI Agent Architecture
## Fixing the 11 Gaps Across Agents, MCP, Memory & Tools

---

## Context Assessment

### What I have full context for:
- Signal Analyst agent internals (analyze → LLM → parse → return)
- Agent memory system (5 types, SQL+Qdrant, full API)
- Power of 1 / Outcome ROI engine (all computation functions)
- Playbook orchestrator + trigger system
- Event system (pub/sub, priority queue)
- Action interface + 5 providers
- MCP integration layer + 3 mock servers
- Feedback loop + weight recalibration

### What does NOT need external dependencies:
- GAP-1 (Agentic loop) — pure code, wraps existing agent
- GAP-2 (Agent-to-agent) — tool registry, wires existing functions
- GAP-4 (Financial tools) — tools exist, just need registration
- GAP-5 (Auto-trigger) — wire Signal Analyst → Orchestrator
- GAP-6 (Feedback learning) — feedback loop exists, needs consumption
- GAP-7 (Approval workflow) — new DB model + API
- GAP-8 (Shared memory) — extend existing memory scope
- GAP-10 (Event audit) — new DB model + write-on-publish

### What is blocked by external dependencies:
- GAP-3 (Real MCP servers) — needs Salesforce/ServiceNow API credentials
- GAP-9 (Doc generation) — needs PDF/PPTX library + LLM templates
- GAP-11 (Calendar agent) — needs calendar API integration

---

## Phased Plan

### Phase 1: Wire the Unwired (LOW effort, HIGH demo value)
**Estimated: ~45 min | Files: 3-4 | Risk: LOW**

Fixes: **GAP-4** (financial tools) + **GAP-8** (shared memory) + **GAP-10** (event audit)

**1a. Agent Tool Registry** — `agent_tool_registry.py`
- Central registry where any agent can call any tool by name
- Register: `power_of_1_calc`, `outcome_roi_calc`, `quarterly_checkpoint`,
  `health_score_calc`, `playbook_recommend`, `memory_recall`, `memory_remember`
- Each tool = a function with typed input/output + description
- This is the backbone that enables GAP-2 (inter-agent) too

**1b. Shared Memory Namespace** — Edit `agent_memory.py`
- Add `SHARED = "shared"` to MemoryScope enum
- Convention: namespace=`customer_intelligence` for cross-agent facts
- Signal Analyst writes "account X is at-risk, $105K exposure"
- Orchestrator reads it when deciding playbook priority

**1c. Event Audit Trail** — Edit `event_system.py`
- Add `EventLog` DB model (event_type, customer_id, payload, timestamp)
- Write to DB on every `publish()` call
- Add `GET /api/events/log` endpoint for debugging

---

### Phase 2: Agentic Loop (HIGH effort, HIGH value)
**Estimated: ~60 min | Files: 2-3 | Risk: MEDIUM**

Fixes: **GAP-1** (agentic loop) + **GAP-2** (agent-to-agent)

**2a. ReAct Agent Loop** — `agent_loop.py`
- Wraps any agent (starting with Signal Analyst) in a Plan→Act→Observe→Reflect cycle
- Steps:
  1. **Analyze**: Run Signal Analyst (existing single-shot)
  2. **Evaluate**: Check confidence. If LOW → gather more data
  3. **Enrich**: Call tools (financial projection, memory recall, Qdrant search)
  4. **Quantify**: Call Power of 1 to put $ on every recommendation
  5. **Decide**: If confidence > threshold → proceed. Else → flag for review
  6. **Act or Escalate**: Auto-trigger playbook OR queue for human approval
- Uses AgentState (already in agent_memory.py) for persistence between steps
- Uses Tool Registry (Phase 1a) for tool invocation

**2b. Wire Signal Analyst → Tool Registry**
- Extend SignalAnalystAgent with `available_tools` from registry
- After initial analysis, agent can call tools to enrich its output
- Every RecommendedAction now includes `estimated_dollar_impact`

---

### Phase 3: Autonomous Execution (MEDIUM effort, HIGH value)
**Estimated: ~45 min | Files: 3-4 | Risk: MEDIUM**

Fixes: **GAP-5** (auto-trigger) + **GAP-6** (feedback learning) + **GAP-7** (approval workflow)

**3a. Approval Queue** — `approval_queue.py` + `approval_api.py`
- DB model: `ApprovalRequest` (agent_id, action, confidence, status, reviewer)
- Tiered logic:
  - confidence >= 0.85 → AUTO_EXECUTE (with audit log)
  - confidence 0.60-0.85 → PENDING_APPROVAL (notify CSM via Slack/email)
  - confidence < 0.60 → AUTO_REJECT (log reason)
- API: `GET /api/approvals/pending`, `POST /api/approvals/:id/approve|reject`

**3b. Signal Analyst → Auto-Trigger Pipeline**
- After agentic loop completes (Phase 2):
  - If recommended_action includes playbook → create ApprovalRequest
  - If auto-approved → call PlaybookOrchestrator.trigger_execution()
  - Store execution in shared memory for other agents

**3c. Feedback-Informed Analysis**
- Before Signal Analyst runs, pull feedback from `qdrant_feedback_loop`:
  - "Last time we ran renewal-safeguard on similar accounts, 70% resolved"
  - "expansion-accelerator has 85% success rate for accounts with this profile"
- Inject into system prompt as historical context
- After playbook completes, store outcome → closes the loop

---

### Phase 4: MCP + Document Generation (MEDIUM effort, MEDIUM value)
**Estimated: ~45 min | Files: 3-4 | Risk: MEDIUM**

Fixes: **GAP-3** (MCP scaffolding) + **GAP-9** (doc generation)

**4a. MCP Server Interface Hardening**
- Can't build real Salesforce/ServiceNow without credentials
- BUT can: build proper MCP tool registration so agents discover tools dynamically
- Create `mcp_tool_registry.py` that exposes MCP tools alongside local tools
- When MCP is unavailable → graceful fallback to local data (already exists)
- When MCP is available → tools auto-register from connected servers

**4b. QBR/Report Generation Agent** — `report_generation_agent.py`
- LLM-powered agent that composes reports from:
  - Health score data (from health_score_engine)
  - Outcome ROI (from outcome_roi_engine) — historical + forward
  - Signal Analyst output (risk/growth drivers)
  - Playbook execution outcomes
- Output: structured JSON that frontend renders as a report
- NOT PDF generation (avoids heavy dependency) — frontend renders

---

## Time Estimate Summary

| Phase | Gaps Fixed | Effort | Risk | What Ships |
|-------|-----------|--------|------|------------|
| **Phase 1** | GAP-4, 8, 10 | ~45 min | LOW | Tool registry, shared memory, event audit |
| **Phase 2** | GAP-1, 2 | ~60 min | MED | Agentic loop, inter-agent tools, $ in every recommendation |
| **Phase 3** | GAP-5, 6, 7 | ~45 min | MED | Auto-trigger, approval queue, feedback learning |
| **Phase 4** | GAP-3, 9 | ~45 min | MED | MCP hardening, report generation agent |
| **Total** | **10 of 11** | **~3.5 hrs** | | GAP-11 (calendar) deferred — needs external API |

---

## What Gets Deferred

- **GAP-11 (Calendar/Scheduling)**: Needs external calendar API credentials. Not buildable without Google Calendar / O365 integration keys.
- **Real MCP server connections** (part of GAP-3): Can build the scaffolding and tool registration, but actual Salesforce/ServiceNow connections need API credentials that are external dependencies.

---

## Execution Order

Phase 1 → Phase 2 → Phase 3 → Phase 4

Phase 1 is prerequisite for Phase 2 (tool registry needed for agentic loop).
Phase 2 is prerequisite for Phase 3 (agentic loop needed for auto-trigger).
Phase 4 is independent but benefits from all prior phases.

---

## Key Architecture Decisions

1. **Tool Registry pattern** (not MCP for internal tools): Internal tools use a simple Python registry. MCP is for external systems only. This avoids over-engineering.

2. **ReAct loop, not full autonomy**: The agentic loop follows Observe→Think→Act→Reflect but always has a confidence gate. No unbounded loops.

3. **Approval queue, not blind execution**: High-confidence actions auto-execute. Low-confidence gets human review. This is the right balance for CS operations.

4. **Shared memory via namespace convention**: No new infrastructure. Just a `SHARED` scope + `customer_intelligence` namespace in existing memory system.

5. **Reports as structured JSON, not PDF**: Frontend renders. Avoids heavy server-side PDF dependencies. Can add PDF export later.
