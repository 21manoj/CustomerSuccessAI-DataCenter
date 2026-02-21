#!/usr/bin/env python3
"""
AI Agent Architecture — Master Inventory
==========================================
Maps every autonomous agent, its memory, tools, MCP connections,
and identifies the gaps.

This is the "blueprint" file — import it to power architecture dashboards,
or read it as documentation for the platform's agent layer.
"""

# ============================================================
# AGENT INVENTORY
# ============================================================
# Each agent entry: what it does, what it has, what it's missing.
#
# STATUS KEY:
#   LIVE     = in production, fully wired
#   PARTIAL  = code exists, not fully integrated
#   MOCK     = mock/stub implementation only
#   MISSING  = identified need, no code yet
#   GAP      = architectural gap (no code, no plan)

AGENT_INVENTORY = {

    # ── AGENT 1: Signal Analyst ──────────────────────────────
    "signal_analyst": {
        "display_name": "Signal Analyst Agent",
        "purpose": "Predict churn/expansion from quantitative + qualitative signals",
        "status": "LIVE",
        "files": [
            "agents/signal_analyst_agent.py",
            "agents/claude_signal_analyst_agent.py",
            "agents/signal_analyst_api.py",
        ],
        "llm_provider": {
            "openai": {"model": "gpt-4o", "status": "LIVE"},
            "anthropic": {"model": "claude-sonnet-4-5", "status": "LIVE"},
        },
        "memory": {
            "short_term": {"status": "LIVE", "via": "agent_memory.py → MemoryType.SHORT_TERM"},
            "episodic": {"status": "LIVE", "via": "agent_memory.py → MemoryType.EPISODIC"},
            "entity": {"status": "LIVE", "via": "agent_memory.py → MemoryType.ENTITY"},
            "semantic": {"status": "LIVE", "via": "agent_memory.py → Qdrant vector index"},
            "scratchpad": {"status": "LIVE", "via": "agent_memory.py → MemoryType.SCRATCHPAD"},
        },
        "tools": {
            "qdrant_signal_retrieval": {"status": "LIVE", "desc": "Fetch quant/qual/historical signals from Qdrant"},
            "health_score_calculation": {"status": "LIVE", "desc": "Calculate health scores from KPI reference ranges"},
            "decision_matrix": {"status": "LIVE", "desc": "Correlate quantitative vs qualitative signal alignment"},
            "signal_deduplication": {"status": "LIVE", "desc": "Deduplicate signals from multiple sources"},
            "signal_conversion": {"status": "LIVE", "desc": "Convert DB models (Account, KPI, Notes) to signal format"},
            "playbook_recommendation": {"status": "PARTIAL", "desc": "Recommend playbooks — scoring exists but not self-triggered"},
            "playbook_execution": {"status": "PARTIAL", "desc": "Trigger playbooks via n8n — orchestrator exists but agent doesn't self-trigger"},
            "financial_projection": {"status": "MISSING", "desc": "Agent cannot query Power of 1 impact for its recommendations"},
            "outcome_roi": {"status": "MISSING", "desc": "Agent cannot reference historical/forward ROI to justify actions"},
        },
        "mcp": {
            "salesforce": {"status": "MOCK", "desc": "Mock MCP server, not real Salesforce connection"},
            "servicenow": {"status": "MOCK", "desc": "Mock MCP server, not real ServiceNow"},
            "surveys": {"status": "MOCK", "desc": "Mock MCP server, not real survey system"},
        },
        "gaps": [
            "Agent cannot self-trigger playbooks — requires human to click",
            "Agent doesn't use financial projections to quantify its recommendations in $",
            "No planning/reasoning loop — single-shot analysis, not multi-step",
            "No self-correction — if confidence is low, doesn't gather more data",
            "MCP servers are mocks — no real external system connections",
            "No inter-agent communication — can't delegate to other agents",
        ],
    },

    # ── AGENT 2: Playbook Orchestrator ───────────────────────
    "playbook_orchestrator": {
        "display_name": "Playbook Orchestrator",
        "purpose": "Execute playbooks via n8n webhooks + action providers",
        "status": "LIVE",
        "files": [
            "playbook_orchestrator.py",
            "playbook_execution_api.py",
            "playbook_triggers_api.py",
            "playbook_recommendations_api.py",
        ],
        "llm_provider": {
            "none": {"model": "N/A", "status": "N/A — rule-based, not LLM-powered"},
        },
        "memory": {
            "execution_history": {"status": "LIVE", "via": "PlaybookExecution DB model"},
            "trigger_history": {"status": "LIVE", "via": "PlaybookTrigger last_triggered_at"},
            "outcome_learning": {"status": "PARTIAL", "via": "qdrant_feedback_loop.py exists but weak"},
        },
        "tools": {
            "n8n_webhook": {"status": "LIVE", "desc": "Hand off execution to n8n workflows"},
            "action_providers": {"status": "LIVE", "desc": "Email, Slack, Salesforce, Jira, Internal"},
            "trigger_evaluation": {"status": "LIVE", "desc": "Evaluate KPI/health-based trigger conditions"},
            "credential_vault": {"status": "LIVE", "desc": "Encrypted credential storage for providers"},
            "webhook_signing": {"status": "LIVE", "desc": "HMAC signatures for n8n callbacks"},
        },
        "mcp": {
            "none": {"status": "N/A", "desc": "Orchestrator uses direct webhooks, not MCP"},
        },
        "gaps": [
            "Not LLM-powered — pure rule-based trigger matching",
            "Cannot reason about WHICH playbook is best — just matches triggers",
            "No feedback loop to improve trigger thresholds over time",
            "No autonomous scheduling — requires trigger event or human click",
            "Doesn't incorporate Power of 1 ROI into execution priority",
        ],
    },

    # ── AGENT 3: RAG Query Agent ─────────────────────────────
    "rag_query": {
        "display_name": "RAG Query Agent",
        "purpose": "Answer natural language questions about accounts using retrieval-augmented generation",
        "status": "LIVE",
        "files": [
            "enhanced_rag_openai.py",
            "enhanced_rag_openai_api.py",
            "enhanced_rag_qdrant.py",
            "enhanced_rag_qdrant_api.py",
            "enhanced_rag_with_mcp.py",
        ],
        "llm_provider": {
            "openai": {"model": "gpt-4o", "status": "LIVE"},
        },
        "memory": {
            "conversation_history": {"status": "PARTIAL", "via": "Passed in request, not persisted"},
            "knowledge_base": {"status": "LIVE", "via": "FAISS + Qdrant indices"},
            "temporal_awareness": {"status": "LIVE", "via": "enhanced_rag_temporal.py"},
        },
        "tools": {
            "faiss_search": {"status": "LIVE", "desc": "Vector search over KPI/account knowledge base"},
            "qdrant_search": {"status": "LIVE", "desc": "Semantic search over signals, profiles, temporal data"},
            "query_classification": {"status": "LIVE", "desc": "Auto-detect query type (KPI/account/trend/general)"},
            "query_rewriting": {"status": "LIVE", "desc": "Expand and improve queries for better retrieval"},
            "temporal_analysis": {"status": "LIVE", "desc": "Trend detection, anomaly detection, seasonal analysis"},
        },
        "mcp": {
            "mcp_enhanced_rag": {"status": "PARTIAL", "desc": "Code exists (enhanced_rag_with_mcp.py) but depends on mock MCP servers"},
        },
        "gaps": [
            "Conversation history not persisted across sessions",
            "No Anthropic Claude provider — OpenAI only for synthesis",
            "MCP layer depends on mock servers",
            "Cannot call other agents (e.g., ask Signal Analyst for deeper analysis)",
            "No write-back capability — purely read-only",
        ],
    },

    # ── AGENT 4: Outcome ROI Engine ──────────────────────────
    "outcome_roi": {
        "display_name": "Outcome ROI Engine",
        "purpose": "Calculate historical proof + forward projection of CS investment ROI",
        "status": "LIVE",
        "files": [
            "outcome_roi_engine.py",
            "outcome_roi_api.py",
            "financial_projections_api.py",
            "power_of_1_model.py",
            "quarterly_checkpoints.py",
        ],
        "llm_provider": {
            "none": {"model": "N/A", "status": "N/A — deterministic computation, not LLM"},
        },
        "memory": {
            "none": {"status": "MISSING", "via": "No historical ROI tracking — recomputed each call"},
        },
        "tools": {
            "power_of_1_model": {"status": "LIVE", "desc": "6-metric economic framework with non-linear scaling"},
            "cascade_model": {"status": "LIVE", "desc": "Metric compounding flywheel (15% conservative)"},
            "scaling_scenarios": {"status": "LIVE", "desc": "1%/4%/6% scenarios with fixed investment"},
            "quarterly_checkpoints": {"status": "LIVE", "desc": "Phase-gate validation against quarterly targets"},
            "portfolio_synergy": {"status": "LIVE", "desc": "Multi-company synergy calculation"},
        },
        "mcp": {
            "none": {"status": "N/A", "desc": "Deterministic engine — no external system needs"},
        },
        "gaps": [
            "Not LLM-powered — cannot generate narrative explanations autonomously",
            "No persistent ROI history — each call is stateless recomputation",
            "Signal Analyst doesn't use this to quantify its recommendations",
            "Quarterly checkpoints aren't auto-evaluated — require manual trigger",
        ],
    },

    # ── AGENT 5: Event System ────────────────────────────────
    "event_system": {
        "display_name": "Event System (Coordination Layer)",
        "purpose": "Publish/subscribe events to coordinate agent actions",
        "status": "LIVE",
        "files": [
            "event_system.py",
        ],
        "llm_provider": {
            "none": {"model": "N/A", "status": "N/A — pure event routing"},
        },
        "memory": {
            "event_log": {"status": "MISSING", "via": "Events are fire-and-forget, not logged"},
        },
        "tools": {
            "publish": {"status": "LIVE", "desc": "Publish events to subscribers"},
            "subscribe": {"status": "LIVE", "desc": "Register callbacks per event type"},
            "priority_queue": {"status": "LIVE", "desc": "Priority-based event processing"},
        },
        "mcp": {
            "none": {"status": "N/A"},
        },
        "gaps": [
            "Events are fire-and-forget — no audit trail",
            "No event replay for debugging",
            "Limited event types — no agent-to-agent events",
            "No event schema validation",
        ],
    },

    # ── AGENT 6: Action Interface ────────────────────────────
    "action_interface": {
        "display_name": "Action Interface (Provider Layer)",
        "purpose": "Execute actions via external providers (Email, Slack, Salesforce, Jira)",
        "status": "LIVE",
        "files": [
            "action_interface_api.py",
            "providers/base.py",
            "providers/email_provider.py",
            "providers/slack_provider.py",
            "providers/salesforce_provider.py",
            "providers/jira_provider.py",
            "providers/internal_provider.py",
        ],
        "llm_provider": {
            "none": {"model": "N/A", "status": "N/A — deterministic dispatch"},
        },
        "memory": {
            "action_bindings": {"status": "LIVE", "via": "CustomerActionBinding DB model"},
            "credentials": {"status": "LIVE", "via": "IntegrationCredential encrypted vault"},
        },
        "tools": {
            "send_email": {"status": "LIVE"},
            "send_slack": {"status": "LIVE"},
            "create_jira_task": {"status": "LIVE"},
            "update_salesforce": {"status": "LIVE"},
            "log_internal": {"status": "LIVE"},
        },
        "mcp": {
            "none": {"status": "N/A", "desc": "Direct provider integrations, not via MCP"},
        },
        "gaps": [
            "No LLM-powered message generation — templates only",
            "Providers don't report back success/failure to agents",
            "No retry at the provider level (only at orchestrator level)",
        ],
    },
}


# ============================================================
# MEMORY SYSTEMS INVENTORY
# ============================================================

MEMORY_SYSTEMS = {
    "agent_memory": {
        "display_name": "Persistent Agent Memory",
        "status": "LIVE",
        "file": "agent_memory.py",
        "backend": "SQLAlchemy + Qdrant (optional)",
        "types": {
            "SHORT_TERM": "Current session buffer",
            "EPISODIC": "Past analysis snapshots, playbook outcomes",
            "ENTITY": "Named-entity facts (ARR, CSM, tier, contacts)",
            "SEMANTIC": "Free-form knowledge, vector-indexed in Qdrant",
            "SCRATCHPAD": "Agent working memory for multi-step reasoning",
        },
        "features": {
            "remember": "LIVE — store with importance scoring",
            "recall": "LIVE — structured filter retrieval",
            "semantic_search": "LIVE — Qdrant vector similarity",
            "entity_upsert": "LIVE — named-entity facts",
            "agent_state": "LIVE — save/load multi-step reasoning state",
            "consolidation": "LIVE — promote short-term to episodic",
            "auto_expiry": "LIVE — TTL-based pruning",
            "cross_agent_sharing": "MISSING — each agent has isolated memory",
        },
    },
    "qdrant_signals": {
        "display_name": "Qdrant Signal Store",
        "status": "LIVE",
        "backend": "Qdrant Cloud",
        "types": {
            "quantitative": "KPI values, metrics, usage data",
            "qualitative": "Support tickets, sentiment, feedback",
            "historical": "Time-series patterns, trends",
            "temporal": "Date-stamped context",
        },
    },
    "faiss_knowledge": {
        "display_name": "FAISS Knowledge Base",
        "status": "LIVE",
        "backend": "Local FAISS index",
        "types": {
            "kpi_data": "KPI definitions, values, targets",
            "account_profiles": "Account metadata, health scores",
        },
    },
    "feedback_loop": {
        "display_name": "Qdrant Feedback Loop",
        "status": "PARTIAL",
        "file": "qdrant_feedback_loop.py",
        "desc": "Captures playbook outcomes to improve future analysis",
        "gap": "Exists but not actively consumed by Signal Analyst for learning",
    },
}


# ============================================================
# MCP INTEGRATION STATUS
# ============================================================

MCP_STATUS = {
    "integration_layer": {
        "file": "mcp_integration.py",
        "status": "PARTIAL",
        "desc": "MCPIntegration class exists, depends on `mcp` SDK",
        "sdk_check": "try: from mcp import ClientSession → MCP_AVAILABLE",
    },
    "servers": {
        "salesforce": {"status": "MOCK", "file": "mcp_servers/mock_salesforce_server.py"},
        "servicenow": {"status": "MOCK", "file": "mcp_servers/mock_servicenow_server.py"},
        "surveys": {"status": "MOCK", "file": "mcp_servers/mock_survey_server.py"},
    },
    "consumers": {
        "enhanced_rag_with_mcp": {"status": "PARTIAL", "file": "enhanced_rag_with_mcp.py"},
        "signal_analyst": {"status": "MISSING", "desc": "Agent doesn't consume MCP data directly"},
    },
    "gaps": [
        "All 3 MCP servers are mocks — no real external system connections",
        "MCP SDK may not be installed (optional dependency)",
        "Only RAG uses MCP — Signal Analyst is not wired to it",
        "No MCP tool registration — agents can't discover available tools dynamically",
        "No MCP-based agent-to-agent communication",
    ],
}


# ============================================================
# TOOL REGISTRY — What tools exist for agents to use
# ============================================================

TOOL_REGISTRY = {
    # Data retrieval tools
    "qdrant_signal_fetch": {"status": "LIVE", "agents": ["signal_analyst", "rag_query"]},
    "faiss_knowledge_search": {"status": "LIVE", "agents": ["rag_query"]},
    "health_score_calc": {"status": "LIVE", "agents": ["signal_analyst"]},
    "kpi_lookup": {"status": "LIVE", "agents": ["rag_query"]},
    "account_snapshot": {"status": "LIVE", "agents": []},
    "time_series_query": {"status": "LIVE", "agents": ["rag_query"]},

    # Analysis tools
    "decision_matrix": {"status": "LIVE", "agents": ["signal_analyst"]},
    "signal_deduplication": {"status": "LIVE", "agents": ["signal_analyst"]},
    "temporal_analysis": {"status": "LIVE", "agents": ["rag_query"]},
    "power_of_1_calc": {"status": "LIVE", "agents": []},  # NOT wired to any agent
    "outcome_roi_calc": {"status": "LIVE", "agents": []},  # NOT wired to any agent
    "quarterly_checkpoint": {"status": "LIVE", "agents": []},  # NOT wired to any agent

    # Action tools
    "playbook_trigger": {"status": "LIVE", "agents": ["playbook_orchestrator"]},
    "playbook_execute": {"status": "LIVE", "agents": ["playbook_orchestrator"]},
    "send_email": {"status": "LIVE", "agents": ["action_interface"]},
    "send_slack": {"status": "LIVE", "agents": ["action_interface"]},
    "create_jira_task": {"status": "LIVE", "agents": ["action_interface"]},
    "update_salesforce": {"status": "LIVE", "agents": ["action_interface"]},

    # Missing tools
    "web_search": {"status": "MISSING", "agents": [], "desc": "No external web search capability"},
    "calendar_scheduling": {"status": "MISSING", "agents": [], "desc": "No calendar integration"},
    "document_generation": {"status": "MISSING", "agents": [], "desc": "No QBR/report auto-generation"},
    "approval_workflow": {"status": "MISSING", "agents": [], "desc": "No human-in-the-loop approval"},
}


# ============================================================
# GAP ANALYSIS — Ranked by impact
# ============================================================

GAPS = {
    "critical": [
        {
            "id": "GAP-1",
            "title": "No Agentic Loop (Plan → Act → Observe → Reflect)",
            "current": "Signal Analyst is single-shot: input → LLM → output. No iteration.",
            "needed": "Multi-step reasoning: analyze → plan → act → observe result → adjust",
            "impact": "Agent can't self-correct when confidence is low or data is insufficient",
            "effort": "HIGH — requires agent loop framework (ReAct/Plan-and-Solve pattern)",
        },
        {
            "id": "GAP-2",
            "title": "No Agent-to-Agent Communication",
            "current": "Each agent operates in isolation. Signal Analyst can't ask ROI Engine for $ impact.",
            "needed": "Agent bus / tool registry where agents can invoke each other",
            "impact": "Signal Analyst recommendations lack $ quantification. Playbooks don't know ROI.",
            "effort": "MEDIUM — wire tools as callable functions + shared context",
        },
        {
            "id": "GAP-3",
            "title": "MCP Servers Are All Mocks",
            "current": "3 mock servers (Salesforce, ServiceNow, Surveys). No real connections.",
            "needed": "Real MCP server implementations or direct API integrations",
            "impact": "Platform has no real-time external data — relies entirely on uploaded CSVs",
            "effort": "HIGH — each server needs auth, pagination, rate limiting, error handling",
        },
    ],
    "high": [
        {
            "id": "GAP-4",
            "title": "Financial Tools Not Wired to Agents",
            "current": "Power of 1, Outcome ROI, Quarterly Checkpoints exist but no agent calls them",
            "needed": "Register as callable tools for Signal Analyst and Playbook Orchestrator",
            "impact": "Every agent recommendation should say 'this action is worth $X'",
            "effort": "LOW — tools exist, just need function registration",
        },
        {
            "id": "GAP-5",
            "title": "No Autonomous Playbook Triggering",
            "current": "Playbooks require human click or timer-based trigger evaluation",
            "needed": "Signal Analyst → confidence > threshold → auto-trigger playbook",
            "impact": "24/7 autonomous intervention vs waiting for human review",
            "effort": "MEDIUM — needs confidence thresholds + approval workflow",
        },
        {
            "id": "GAP-6",
            "title": "No Feedback-Driven Learning",
            "current": "Feedback loop captures outcomes but agent doesn't learn from them",
            "needed": "Post-playbook outcome → adjust future trigger thresholds + recommendations",
            "impact": "Agent doesn't improve over time — same recommendations regardless of history",
            "effort": "MEDIUM — needs outcome correlation + memory-informed prompts",
        },
        {
            "id": "GAP-7",
            "title": "No Human-in-the-Loop Approval",
            "current": "Agent either acts autonomously (risky) or requires full manual trigger (slow)",
            "needed": "Tiered approval: low-confidence → human review, high-confidence → auto-execute",
            "impact": "Blocks autonomous operation for high-stakes actions",
            "effort": "MEDIUM — needs approval queue + notification system",
        },
    ],
    "medium": [
        {
            "id": "GAP-8",
            "title": "Cross-Agent Memory Sharing",
            "current": "Each agent has isolated memory (per agent_id). No shared knowledge.",
            "needed": "Shared 'customer intelligence' namespace readable by all agents",
            "impact": "Signal Analyst learnings not available to Playbook Orchestrator",
            "effort": "LOW — extend MemoryScope with SHARED + namespace conventions",
        },
        {
            "id": "GAP-9",
            "title": "No Document/Report Generation Agent",
            "current": "QBR decks, ROI reports, executive summaries are manual",
            "needed": "Agent that composes QBR deck from health + ROI + signal data",
            "impact": "3.5 hrs/QBR saved (per AUTOMATION_TIMELINE data)",
            "effort": "MEDIUM — LLM + template system + PDF/PPTX generation",
        },
        {
            "id": "GAP-10",
            "title": "Event Audit Trail",
            "current": "Events are fire-and-forget. No logging or replay.",
            "needed": "Event log table + replay capability for debugging",
            "impact": "Can't debug why an agent didn't act or acted incorrectly",
            "effort": "LOW — add EventLog DB model + write on publish",
        },
        {
            "id": "GAP-11",
            "title": "No Scheduling/Calendar Agent",
            "current": "No calendar integration for CSM meeting scheduling",
            "needed": "Calendar MCP server + scheduling tool for agents",
            "impact": "CSM still manually schedules EBRs, QBRs, check-ins",
            "effort": "MEDIUM — calendar API integration + MCP server",
        },
    ],
}


# ============================================================
# ARCHITECTURE SUMMARY — For dashboards / presentations
# ============================================================

ARCHITECTURE_SUMMARY = {
    "total_agents": 7,  # +1 Report Generation Agent
    "llm_powered_agents": 2,  # Signal Analyst + RAG Query
    "rule_based_components": 5,  # Orchestrator, ROI Engine, Event System, Action Interface, Report Gen
    "memory_systems": 4,  # Agent Memory, Qdrant Signals, FAISS, Feedback Loop
    "memory_types": 5,  # Short-term, Episodic, Entity, Semantic, Scratchpad
    "memory_scopes": 5,  # Account, Customer, Global, Agent, Shared (cross-agent)
    "tools_available": 12,  # 9 local (tool registry) + 3 MCP-bridged
    "tools_wired_to_agents": 12,  # All tools now in registry and callable by any agent
    "tools_unwired": 0,
    "mcp_servers": 3,
    "mcp_servers_real": 0,  # All mocks — real connections need API credentials
    "mcp_bridged_with_fallback": 3,  # CRM, Incident, Survey — graceful local fallback
    "action_providers": 5,  # Email, Slack, Salesforce, Jira, Internal
    "llm_providers": 2,  # OpenAI, Anthropic
    "gaps_fixed": 10,  # GAP-1 through GAP-10
    "gaps_remaining": 1,  # GAP-11: Calendar/Scheduling
    "gaps_total": 11,
}


# ============================================================
# PRODUCT ROADMAP — Future TBD
# ============================================================

ROADMAP_FUTURE_TBD = {
    "onboarding_agent": {
        "title": "Customer Onboarding Agent (#7)",
        "status": "TBD",
        "priority": "HIGH",
        "description": (
            "Dedicated agent for new customer lifecycle (first 30-90 days). "
            "Owns TTFV (Time to First Value) metric. Auto-triggers activation-blitz "
            "playbook post-onboarding. Graduates customer to Signal Analyst for "
            "steady-state monitoring."
        ),
        "lifecycle": "Customer Created → Provision → Activation-Blitz → Track TTFV → Graduate",
        "depends_on": ["agent_tool_registry", "agent_loop", "approval_queue"],
        "existing_pieces": [
            "onboarding_api_v2_config_aware.py — V2 API with 13-field wizard",
            "OnboardingWizard.main.tsx — 8-step frontend (NOT wired to backend)",
            "activation-blitz playbook — exists in playbook_knowledge.py",
            "OnboardingOptimizer.js — ejouurnal TTFV optimizer (reference)",
        ],
    },
    "web_search_tool": {
        "title": "Web Search + Industry Benchmark Tool",
        "status": "TBD",
        "priority": "MEDIUM",
        "description": (
            "Tool registered in AgentToolRegistry that enables any agent or customer "
            "to search for fresh industry benchmark data. Connects benchmark gaps to "
            "Power of 1 dollar impact."
        ),
        "layers": {
            "layer_1_internal": "Benchmark Compare — uses existing IndustryBenchmarks table (27 records)",
            "layer_2_external": "Web Search — Brave/SerpAPI for fresh data enrichment",
        },
        "depends_on": ["agent_tool_registry", "IndustryBenchmarks table"],
        "existing_pieces": [
            "IndustryBenchmarks DB model — percentile-based comparison",
            "import_benchmarks.py — CSV/JSON/Excel import tool",
            "sample_industry_benchmarks.csv — 27 KPI-industry records",
            "power_of_1_model.py — dollar impact calculation for benchmark gaps",
        ],
    },
    "calendar_scheduling_agent": {
        "title": "Calendar/Scheduling Agent (GAP-11)",
        "status": "TBD",
        "priority": "LOW",
        "description": "Calendar MCP server + scheduling tool for automated EBR/QBR scheduling.",
        "depends_on": ["mcp_tool_bridge", "external calendar API credentials"],
    },
}
