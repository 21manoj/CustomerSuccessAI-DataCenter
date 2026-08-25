#!/usr/bin/env python3
"""
CS Pulse GrowthPulse — Platform Capability Matrix
====================================================
Canonical, machine-readable registry of every agent, tool, service,
engine, provider, MCP server, and API surface exposed by the platform.

Usage:
    from CS_PULSE_GROWTH_PLATFORM_MATRIX import PLATFORM_MATRIX, print_matrix
    print_matrix()                         # human-readable
    print_matrix(section='agents')         # single section
    json.dumps(PLATFORM_MATRIX)            # API / export
"""

from typing import Dict, List, Any

# ════════════════════════════════════════════════════════════════
# 1. AI AGENTS
# ════════════════════════════════════════════════════════════════

AGENTS: List[Dict[str, Any]] = [
    {
        "id": "signal-analyst",
        "name": "Signal Analyst Agent",
        "module": "agents/signal_analyst_agent.py",
        "class": "SignalAnalystAgent",
        "llm": "OpenAI GPT-4o",
        "description": "Core AI agent — ingests quantitative + qualitative signals, "
                       "predicts churn/expansion, recommends playbooks with confidence scoring",
        "capabilities": [
            "Churn risk prediction (0-100 %)",
            "Expansion opportunity scoring",
            "Health-score computation (DC2S pillar + SaaS HealthTrend)",
            "Risk / Growth driver extraction",
            "Actionable recommendation generation with priority & deadline",
            "Cost-tracked API calls with circuit-breaker resilience",
        ],
        "inputs": ["SignalData[]", "Account context", "Historical patterns"],
        "outputs": ["SignalAnalystOutput (churn_prob, expansion_prob, drivers, actions)"],
        "api_endpoints": ["POST /api/signal-analyst/analyze", "POST /api/signal-analyst/test"],
    },
    {
        "id": "decision-matrix",
        "name": "Decision Matrix Engine",
        "module": "agents/decision_matrix.py",
        "class": "DecisionMatrixResult",
        "llm": "OpenAI GPT-4o-mini (fallback: rule-based)",
        "description": "Correlates quantitative KPI trends with qualitative sentiment "
                       "to detect agreement / disagreement / conflict signals",
        "capabilities": [
            "KPI trend analysis (IMPROVING / DECLINING / STABLE)",
            "Qualitative sentiment aggregation (POSITIVE / NEGATIVE / MIXED)",
            "Data alignment detection (AGREEMENT / DISAGREEMENT / NEUTRAL)",
            "Confidence scoring with reasoning chain",
            "Rule-based fallback when LLM unavailable",
        ],
        "inputs": ["KPI values", "QualitativeSignal[]"],
        "outputs": ["DataAlignment", "TrendDirection", "SignalSentiment", "confidence"],
        "api_endpoints": [],  # called internally by Signal Analyst
    },
    {
        "id": "playbook-trigger-validator",
        "name": "Playbook Trigger Validator",
        "module": "playbook_trigger_validator.py",
        "class": "TriggerValidationResult",
        "llm": "OpenAI GPT-4o",
        "description": "LLM validation gate between KPI threshold breach and playbook "
                       "execution — prevents false-positive automation",
        "capabilities": [
            "Auto-approve high-confidence triggers",
            "Auto-reject noise / false positives",
            "Route ambiguous triggers to manual review",
        ],
        "inputs": ["Trigger conditions", "Account context", "KPI snapshot"],
        "outputs": ["TriggerValidationDecision (approved / rejected / pending_manual)"],
        "api_endpoints": ["POST /api/playbook-triggers/evaluate-all"],
    },
]


# ════════════════════════════════════════════════════════════════
# 2. AGENT SUPPORT SERVICES
# ════════════════════════════════════════════════════════════════

AGENT_SUPPORT_SERVICES: List[Dict[str, Any]] = [
    {
        "id": "signal-converter",
        "name": "Signal Converter",
        "module": "agents/signal_converter.py",
        "description": "Converts Account, KPI, DC2SKPI, AccountNote DB models into "
                       "normalized SignalData objects for the Signal Analyst",
        "functions": [
            "convert_database_models_to_signals()",
            "convert_account_to_signal_data()",
            "convert_kpi_to_signal_data()",
            "convert_dc2s_kpi_to_signal_data()",
            "convert_account_notes_to_signal_data()",
        ],
    },
    {
        "id": "qualitative-signal-converter",
        "name": "Qualitative Signal Converter",
        "module": "agents/qualitative_signal_converter.py",
        "description": "Converts QualitativeSignal DB records to SignalData with temporal "
                       "grouping (week / month / year) and sentiment extraction",
        "functions": [
            "convert_qualitative_signal_to_signal_data()",
            "convert_qualitative_signals_to_signal_data()",
        ],
    },
    {
        "id": "signal-deduplicator",
        "name": "Signal Deduplicator",
        "module": "agents/signal_deduplicator.py",
        "description": "Removes duplicate signals before LLM analysis to prevent wasted "
                       "tokens, biased weighting, and inflated costs",
        "functions": [
            "deduplicate_signals()",
            "get_signal_unique_key()",
        ],
    },
    {
        "id": "qdrant-integration",
        "name": "Qdrant Vector Integration",
        "module": "agents/qdrant_integration.py",
        "description": "Queries per-customer Qdrant collections for similarity-scored signals "
                       "across quantitative, qualitative, and historical pattern types",
        "functions": [
            "query_qdrant_for_signals()",
            "get_quantitative_signals_from_qdrant()",
            "get_qualitative_signals_from_qdrant()",
            "get_historical_patterns_from_qdrant()",
        ],
        "collection_pattern": "kpi_dashboard_vectors_customer_{customer_id}",
    },
    {
        "id": "vertical-mapper",
        "name": "Vertical Mapper",
        "module": "agents/vertical_mapper.py",
        "description": "Maps system verticals (saas / datacenter) to agent-specific type "
                       "strings and back",
        "functions": [
            "map_vertical_to_agent_type()",
            "map_agent_type_to_system()",
        ],
    },
    {
        "id": "agent-prompts",
        "name": "Prompt Library",
        "module": "agents/prompts.py",
        "description": "Builds vertical-specific system + analysis prompts for the Signal "
                       "Analyst with structured context formatting",
        "functions": [
            "get_system_prompt()",
            "get_analysis_prompt()",
            "format_quantitative_signals()",
            "format_qualitative_signals()",
            "format_historical_patterns()",
        ],
    },
]


# ════════════════════════════════════════════════════════════════
# 3. REVENUE INTELLIGENCE ENGINES
# ════════════════════════════════════════════════════════════════

REVENUE_INTELLIGENCE_ENGINES: List[Dict[str, Any]] = [
    {
        "id": "power-of-1-model",
        "name": "Power of 1 Revenue Model",
        "module": "power_of_1_model.py",
        "description": "Economic model — 1 % improvement in 6 KPI levers yields quantifiable "
                       "dollar impact with non-linear compounding, cascade effects, and scaling curves",
        "feature_flag": "revenue_intelligence",
        "metrics": [
            {"id": "TTFV",     "name": "Time to First Value",      "direction": "lower_is_better"},
            {"id": "NRR",      "name": "Net Revenue Retention",    "direction": "higher_is_better"},
            {"id": "GRR",      "name": "Gross Revenue Retention",  "direction": "higher_is_better"},
            {"id": "ticket_resolution_time", "name": "Ticket Resolution Time", "direction": "lower_is_better"},
            {"id": "product_adoption",       "name": "Product Adoption",       "direction": "higher_is_better"},
            {"id": "expansion_rate",         "name": "Expansion Rate",         "direction": "higher_is_better"},
        ],
        "capabilities": [
            "Per-metric dollar impact (direct + cascade + compounding)",
            "Non-linear scaling curves (1 % → 6 %)",
            "Portfolio-wide composite impact",
            "Work-package-level cost attribution (5 roles)",
            # Owner decision, item 20 (state-of-play.md, 2026-08-24): investment
            # scales per improvement tier (95K/247K/370K), not a flat $247K
            # across scenarios — that was the retired thesis. $247K is the
            # baseline-tier (10M-ARR, 4% improvement) reference figure.
            "Investment scales per improvement tier (95K / 247K / 370K)",
        ],
        "api_endpoints": [
            "GET /api/financial-projections/scaling-curves",
            "GET /api/financial-projections/kpi-impact/<kpi_name>",
            "GET /api/financial-projections/account/<account_id>",
            "GET /api/financial-projections/corporate",
        ],
    },
    {
        "id": "resource-capacity-model",
        "name": "Resource Capacity Model",
        "module": "resource_capacity_model.py",
        "description": "FTE pool, hourly rates, and capacity constraints for 5 CS roles — "
                       "ensures playbooks don't over-allocate and tracks utilization",
        "roles": [
            {"id": "csm",        "rate": 95,  "annual_hours": 1920, "fte": 0.92},
            {"id": "cs_ops",     "rate": 85,  "annual_hours": 1760, "fte": 0.85},
            {"id": "product",    "rate": 110, "annual_hours":  760, "fte": 0.37},
            {"id": "platform",   "rate": 120, "annual_hours":  920, "fte": 0.44},
            {"id": "leadership", "rate": 150, "annual_hours":  480, "fte": 0.23},
        ],
        "totals": {"hours": 5840, "fte": 2.81, "annual_cost": 247000},
        "capabilities": [
            "Quarterly capacity constraint checking",
            "Per-action cost calculation (cs_cost + platform_cost)",
            "Bottleneck role detection with overflow hours",
            "Customer-overridable resource pools",
        ],
    },
    {
        "id": "quarterly-checkpoints",
        "name": "Quarterly Checkpoint Engine",
        "module": "quarterly_checkpoints.py",
        "description": "Q1-Q4 roadmap targets with phase-gate validation, gap analysis, "
                       "and corrective recommendations",
        "capabilities": [
            "Per-quarter metric targets (TTFV, NRR, GRR, ticket_resolution_time, etc.)",
            "Phase-gate decisions (PASS / CONDITIONAL_PASS / FAIL)",
            "Track status (ON_TRACK / AT_RISK / OFF_TRACK / AHEAD / NOT_STARTED)",
            "Automated recommendation generation",
            "Full-year rollup assessment",
        ],
        "api_endpoints": [
            "GET /api/financial-projections/quarterly-status",
        ],
    },
    {
        "id": "portfolio-synergy-engine",
        "name": "Portfolio Synergy Engine (PE Multi-Company)",
        "module": "portfolio_synergy_engine.py",
        "description": "Models cross-company synergy uplift for PE portfolio plays — "
                       "5 synergy types with diminishing-return geometric decay curves",
        "synergy_types": [
            {"id": "shared_playbooks",  "base_lift_pct": 12, "decay": 0.85},
            {"id": "shared_resources",  "base_lift_pct":  8, "decay": 0.80},
            {"id": "vendor_leverage",   "base_lift_pct":  6, "decay": 0.75},
            {"id": "cross_sell",        "base_lift_pct": 10, "decay": 0.82},
            {"id": "benchmarking",      "base_lift_pct":  5, "decay": 0.78},
        ],
        "preset_portfolios": ["pe_3_company", "pe_5_company", "data_center"],
        "capabilities": [
            "Per-company synergy multiplier with geometric decay",
            "Standalone vs. portfolio ROI comparison",
            "Shared-resource cost reduction for later portfolio companies",
            "Synergy breakdown by type with dollar impact",
            "Serialization for API / dashboard consumption",
        ],
    },
    {
        "id": "financial-projections-api",
        "name": "Financial Projections API",
        "module": "financial_projections_api.py",
        "description": "Dual-path financial impact engine — Power of 1 when revenue_intelligence "
                       "enabled, legacy linear coefficients otherwise",
        "api_endpoints": [
            "GET /api/financial-projections/account/<account_id>",
            "GET /api/financial-projections/corporate",
            "GET /api/financial-projections/scaling-curves",
            "GET /api/financial-projections/quarterly-status",
            "GET /api/financial-projections/kpi-impact/<kpi_name>",
        ],
    },
]


# ════════════════════════════════════════════════════════════════
# 4. PLAYBOOK & ORCHESTRATION SYSTEM
# ════════════════════════════════════════════════════════════════

PLAYBOOK_SYSTEM: List[Dict[str, Any]] = [
    {
        "id": "playbook-orchestrator",
        "name": "Playbook Orchestrator",
        "module": "playbook_orchestrator.py",
        "description": "Executes playbooks end-to-end — resolves action bindings, dispatches "
                       "to providers, records step-level audit logs, handles n8n webhook callbacks",
        "capabilities": [
            "n8n workflow hand-off with retry policy",
            "Direct provider dispatch via Action Bindings",
            "Step-level audit logging (PlaybookStepLog)",
            "Credential decryption from vault",
            "Fallback chain (primary → fallback provider → internal)",
            "Webhook signature generation & verification",
            "Execution feedback storage to Qdrant loop",
        ],
        "api_endpoints": [
            "POST /api/playbooks/executions",
            "POST /api/playbooks/executions/<id>/steps",
            "POST /api/webhooks/playbook-callback",
        ],
    },
    {
        "id": "playbook-knowledge",
        "name": "Playbook Knowledge Base",
        "module": "playbook_knowledge.py",
        "description": "5 system playbooks with trigger conditions, expected outcomes, "
                       "KPI improvements, and use-case guidance",
        "playbooks": [
            {
                "id": "voc-sprint",
                "name": "Voice of Customer Sprint",
                "duration": "4 weeks",
                "improves": ["NPS", "CSAT", "GRR", "NRR"],
            },
            {
                "id": "activation-blitz",
                "name": "Activation Blitz",
                "duration": "4 weeks",
                "improves": ["DAU", "MAU", "product_adoption", "TTFV"],
            },
            {
                "id": "sla-stabilizer",
                "name": "SLA Stabilizer",
                "duration": "2-3 weeks",
                "improves": ["First Response Time", "MTTR", "ticket_resolution_time"],
            },
            {
                "id": "renewal-safeguard",
                "name": "Renewal Safeguard",
                "duration": "6 weeks",
                "improves": ["GRR", "NRR"],
            },
            {
                "id": "expansion-timing",
                "name": "Expansion Timing",
                "duration": "4-6 weeks",
                "improves": ["expansion_rate", "NRR"],
            },
        ],
    },
    {
        "id": "playbook-work-packages",
        "name": "Playbook → Work Package Decomposition",
        "module": "playbook_work_packages.py",
        "description": "Decomposes each playbook into costed work packages with role-level "
                       "hour tracking, bridging execution to the resource capacity model",
        "playbook_ids_supported": [
            "PB-DC-01", "PB-DC-02", "PB-DC-03", "PB-DC-04", "PB-DC-05", "PB-DC-06",
            "SaaS-PB-01", "SaaS-PB-02", "SaaS-PB-03", "SaaS-PB-04",
            "SaaS-PB-05", "SaaS-PB-06", "SaaS-PB-07", "SaaS-PB-08",
            "voc-sprint", "activation-blitz", "sla-stabilizer",
            "renewal-safeguard", "expansion-timing",
        ],
        "capabilities": [
            "Per-WP cost/hour estimation by role",
            "Actual vs. estimated variance tracking",
            "WP status lifecycle (PENDING → IN_PROGRESS → COMPLETED / BLOCKED / SKIPPED)",
            "Execution cost summary with role breakdown",
        ],
    },
    {
        "id": "playbook-triggers",
        "name": "Playbook Trigger Configuration",
        "module": "playbook_triggers_api.py",
        "description": "KPI-threshold trigger rules with optional LLM validation gate — "
                       "auto or manual execution modes",
        "api_endpoints": [
            "GET  /api/playbook-triggers",
            "POST /api/playbook-triggers",
            "POST /api/playbook-triggers/test",
            "POST /api/playbook-triggers/evaluate-all",
            "GET  /api/playbook-triggers/history",
        ],
    },
]


# ════════════════════════════════════════════════════════════════
# 5. MCP SERVERS (Model Context Protocol)
# ════════════════════════════════════════════════════════════════

MCP_SERVERS: List[Dict[str, Any]] = [
    {
        "id": "mcp-salesforce",
        "name": "Salesforce MCP Server",
        "module": "mcp_servers/mock_salesforce_server.py",
        "feature_flag": "mcp_integration",
        "description": "CRM data enrichment — accounts, opportunities, usage metrics, contracts",
        "resources": [
            {"uri": "salesforce://accounts",       "description": "Customer accounts (Name, ARR, Industry, Region, Status)"},
            {"uri": "salesforce://opportunities",   "description": "Sales opportunities (Renewal/Expansion, Amount, CloseDate, Probability)"},
            {"uri": "salesforce://usage_metrics",   "description": "Product usage (DAU, MAU, adoption, API calls, logins)"},
            {"uri": "salesforce://contracts",       "description": "Contract terms, dates, values"},
        ],
        "tools": [
            {"name": "get_account_record",    "params": ["account_id"],                     "write": False},
            {"name": "search_opportunities",  "params": ["account_id"],                     "write": False},
            {"name": "get_usage_metrics",     "params": ["account_id"],                     "write": False},
            {"name": "create_opportunity",    "params": ["account_id", "amount", "close_date"], "write": True},
        ],
    },
    {
        "id": "mcp-servicenow",
        "name": "ServiceNow MCP Server",
        "module": "mcp_servers/mock_servicenow_server.py",
        "feature_flag": "mcp_integration",
        "description": "Support ticket enrichment — incidents, SLA breaches, escalations",
        "resources": [
            {"uri": "servicenow://tickets",     "description": "All support tickets (Number, Priority, State, SLA breach)"},
            {"uri": "servicenow://sla_breaches", "description": "SLA violation tracking (breach type, duration, target)"},
            {"uri": "servicenow://escalations",  "description": "Escalated tickets (reason, escalated_to, date)"},
        ],
        "tools": [
            {"name": "create_ticket",         "params": ["account_id", "subject", "description", "priority"], "write": True},
            {"name": "update_ticket_status",  "params": ["ticket_number", "status"],                          "write": True},
        ],
    },
    {
        "id": "mcp-survey",
        "name": "Survey / VoC MCP Server",
        "module": "mcp_servers/mock_survey_server.py",
        "feature_flag": "mcp_integration",
        "description": "Qualitative feedback — NPS, CSAT, VoC interviews, CSM assessments",
        "resources": [
            {"uri": "surveys://nps_scores",       "description": "NPS survey results (score, response rate, respondent breakdown)"},
            {"uri": "surveys://csat_scores",       "description": "CSAT survey results (1-5 scale, response rate)"},
            {"uri": "surveys://interview_notes",   "description": "VoC interview transcripts (themes, qualitative feedback)"},
            {"uri": "surveys://csm_assessments",   "description": "CSM relationship assessments (strength, risk indicators)"},
        ],
        "tools": [
            {"name": "submit_nps_survey",       "params": ["account_id", "score"],  "write": True},
            {"name": "submit_csat_survey",      "params": ["account_id", "score"],  "write": True},
            {"name": "record_interview_notes",  "params": ["account_id", "notes"],  "write": True},
        ],
    },
    {
        "id": "mcp-integration-hub",
        "name": "MCP Integration Hub",
        "module": "mcp_servers/mcp_integration.py",
        "description": "Orchestrates connections to all MCP servers, fetches enriched context "
                       "per-account, and aggregates multi-source data for the RAG pipeline",
        "capabilities": [
            "connect_all(systems) — batch connect",
            "fetch_account_data(account_id, systems) — multi-source enrichment",
            "disconnect_all() — clean shutdown",
            "get_status() — connection health",
        ],
    },
]


# ════════════════════════════════════════════════════════════════
# 6. PROVIDER ADAPTERS (Action Interface)
# ════════════════════════════════════════════════════════════════

PROVIDER_ADAPTERS: List[Dict[str, Any]] = [
    {
        "id": "provider-salesforce",
        "name": "Salesforce Provider",
        "module": "providers/salesforce_provider.py",
        "description": "CRM write-back — tasks, cases, opportunities, record updates, notes",
        "supported_actions": [
            {"action": "create_task",        "params": ["subject", "description", "status", "priority", "assignee", "due_date"]},
            {"action": "create_case",        "params": ["subject", "description", "status", "priority", "origin"]},
            {"action": "create_opportunity", "params": ["name", "account", "stage", "amount", "close_date"]},
            {"action": "update_record",      "params": ["sobject", "record_id", "fields"]},
            {"action": "add_note",           "params": ["record_id", "title", "body"]},
        ],
        "auth": "OAuth2 (access_token or client_id + client_secret + refresh_token)",
        "config": ["instance_url", "api_version (v59.0)"],
    },
    {
        "id": "provider-jira",
        "name": "Jira Provider",
        "module": "providers/jira_provider.py",
        "description": "Issue tracking — create, comment, update, transition issues",
        "supported_actions": [
            {"action": "create_issue",     "params": ["summary", "description", "issue_type", "assignee", "priority", "labels"]},
            {"action": "add_comment",      "params": ["issue_key", "comment"]},
            {"action": "update_issue",     "params": ["issue_key", "fields"]},
            {"action": "transition_issue", "params": ["issue_key", "transition_id"]},
        ],
        "auth": "API Token (email + api_token)",
        "config": ["base_url", "project_key", "issue_type"],
    },
    {
        "id": "provider-slack",
        "name": "Slack Provider",
        "module": "providers/slack_provider.py",
        "description": "Team communications — messages, alerts, channel creation",
        "supported_actions": [
            {"action": "send_message", "params": ["channel", "text"]},
            {"action": "send_alert",   "params": ["channel", "text", "emoji", "context"]},
            {"action": "post_update",  "params": ["channel", "text", "formatting"]},
            {"action": "create_channel", "params": ["name", "purpose"]},
        ],
        "auth": "Bot Token (xoxb-...)",
        "config": ["default_channel"],
    },
    {
        "id": "provider-email",
        "name": "Email Provider",
        "module": "providers/email_provider.py",
        "description": "SMTP notifications — alerts, standard email, escalations",
        "supported_actions": [
            {"action": "send_alert",      "params": ["to", "subject", "body"]},
            {"action": "send_email",      "params": ["to", "subject", "body", "cc", "bcc"]},
            {"action": "send_escalation", "params": ["to", "subject", "body", "priority"]},
        ],
        "auth": "SMTP (host, port, user, password)",
        "config": ["from_email", "from_name"],
    },
    {
        "id": "provider-internal",
        "name": "CS Pulse Internal Provider (Fallback)",
        "module": "providers/internal_provider.py",
        "description": "Default fallback for all actions when external providers unavailable",
        "supported_actions": [
            {"action": "log_event",          "params": ["event_type", "data"]},
            {"action": "create_task",        "params": ["title", "description", "assignee"]},
            {"action": "send_alert",         "params": ["message", "severity"]},
            {"action": "update_health_score", "params": ["account_id", "score"]},
            {"action": "flag_account",       "params": ["account_id", "reason"]},
            {"action": "create_note",        "params": ["account_id", "text"]},
            {"action": "schedule_review",    "params": ["account_id", "date"]},
            {"action": "trigger_workflow",   "params": ["workflow_id", "params"]},
        ],
        "auth": "None (internal)",
        "config": [],
    },
]


# ════════════════════════════════════════════════════════════════
# 7. FEEDBACK & LEARNING SYSTEM
# ════════════════════════════════════════════════════════════════

FEEDBACK_LEARNING: List[Dict[str, Any]] = [
    {
        "id": "qdrant-feedback-loop",
        "name": "Qdrant Feedback Loop + Weight Recalibration",
        "module": "qdrant_feedback_loop.py",
        "description": "Closed-loop learning — stores execution outcomes, recalibrates "
                       "signal weights with learning rate and decay curves",
        "default_weights": {
            "quantitative_signals": 0.40,
            "qualitative_signals":  0.30,
            "historical_patterns":  0.20,
            "playbook_feedback":    0.10,
        },
        "capabilities": [
            "Store execution feedback (Qdrant + DB)",
            "Per-playbook weight recalibration",
            "Learning rate-bounded adjustments",
            "Geometric decay across recalibration cycles",
            "Prediction accuracy tracking (churn + expansion)",
            "Calibration history with error reduction %",
        ],
    },
    {
        "id": "roadmap-scenario-ingest",
        "name": "Roadmap Scenario Ingest",
        "module": "roadmap_scenario_ingest.py",
        "description": "REST ingest for quarterly actuals, what-if scenarios, multi-scenario "
                       "comparison, and baseline seeding",
        "api_endpoints": [
            "POST /api/roadmap/ingest-actuals",
            "POST /api/roadmap/scenario",
            "POST /api/roadmap/compare-scenarios",
            "POST /api/roadmap/seed-baseline",
            "GET  /api/roadmap/timeline",
        ],
    },
    {
        "id": "health-score-engine",
        "name": "Health Score Engine",
        "module": "health_score_engine.py",
        "description": "Medical report-style health scoring — parses KPI values with unit "
                       "conversion, categorizes into low/medium/high against reference ranges",
        "capabilities": [
            "KPI value parsing ($, %, hours, K/M suffixes)",
            "DB-sourced reference range lookup",
            "Pillar-weighted composite scoring (DC2S: 5 pillars)",
            "Trend direction detection",
        ],
    },
    {
        "id": "health-score-storage",
        "name": "Health Score Storage Service",
        "module": "health_score_storage.py",
        "description": "Persists computed health scores to HealthTrend table for monthly "
                       "trend tracking and executive dashboards",
    },
    {
        "id": "health-rollup-subscriber",
        "name": "Health Score Rollup Subscriber",
        "module": "health_score_rollup_subscriber.py",
        "description": "Event-driven health score aggregation — KPI updates trigger "
                       "automatic health score recalculation",
    },
]


# ════════════════════════════════════════════════════════════════
# 8. RAG & SEARCH SERVICES
# ════════════════════════════════════════════════════════════════

RAG_SERVICES: List[Dict[str, Any]] = [
    {
        "id": "rag-qdrant",
        "name": "Qdrant Vector RAG",
        "module": "enhanced_rag_qdrant_api.py",
        "description": "Vector-similarity search over signals, KPIs, notes stored in Qdrant "
                       "with per-customer collection isolation",
        "api_endpoints": [
            "POST /api/rag-qdrant/build",
            "POST /api/rag-qdrant/query",
            "GET  /api/rag-qdrant/revenue-analysis",
            "GET  /api/rag-qdrant/risk-analysis",
            "GET  /api/rag-qdrant/status",
        ],
    },
    {
        "id": "rag-openai",
        "name": "OpenAI-Powered RAG",
        "module": "enhanced_rag_openai_api.py",
        "description": "Natural-language query answering powered by OpenAI embeddings + "
                       "GPT completion over retrieved context",
    },
    {
        "id": "rag-temporal",
        "name": "Temporal RAG",
        "module": "enhanced_rag_temporal_api.py",
        "description": "Time-aware retrieval — queries historical patterns within date "
                       "ranges for trend analysis",
    },
    {
        "id": "rag-historical",
        "name": "Historical Pattern RAG",
        "module": "enhanced_rag_historical_api.py",
        "description": "Retrieves similar historical outcomes (churn / expansion / stable) "
                       "for pattern-based prediction augmentation",
    },
    {
        "id": "direct-rag",
        "name": "Direct RAG API",
        "module": "direct_rag_api.py",
        "description": "Direct vector search with conversation history support — lightweight "
                       "retrieval without LLM completion",
    },
    {
        "id": "governance-rag",
        "name": "Governance RAG",
        "module": "governance_rag_api.py",
        "description": "Retrieves governance rules and compliance constraints for playbook "
                       "validation and audit",
    },
]


# ════════════════════════════════════════════════════════════════
# 9. REST API SURFACE (by domain)
# ════════════════════════════════════════════════════════════════

REST_API_SURFACE: Dict[str, List[Dict[str, Any]]] = {
    "Account & Customer Management": [
        {"endpoint": "GET/POST /api/account-snapshots",                "module": "account_snapshot_api.py"},
        {"endpoint": "GET /api/accounts, GET /api/accounts/<id>",      "module": "customer_management_api.py"},
        {"endpoint": "GET /api/customer-profile/<id>",                 "module": "customer_profile_api.py"},
        {"endpoint": "GET /api/customer-performance/<id>",             "module": "customer_performance_summary_api.py"},
    ],
    "KPI & Data": [
        {"endpoint": "GET/POST /api/kpis",                            "module": "kpi_api.py"},
        {"endpoint": "GET /api/kpi-reference",                        "module": "kpi_reference_api.py"},
        {"endpoint": "GET /api/kpi-reference-ranges",                 "module": "kpi_reference_ranges_api.py"},
        {"endpoint": "GET /api/product-analytics",                    "module": "product_analytics_api.py"},
        {"endpoint": "GET /api/time-series",                          "module": "time_series_api.py"},
    ],
    "Health Scoring": [
        {"endpoint": "GET /api/health-status/<account_id>",           "module": "health_status_api.py"},
        {"endpoint": "GET /api/health-trends",                        "module": "health_trend_api.py"},
        {"endpoint": "GET /api/dc2s-scores",                          "module": "dc2s_scores_api.py"},
    ],
    "Financial Projections": [
        {"endpoint": "GET /api/financial-projections/*",              "module": "financial_projections_api.py"},
        {"endpoint": "GET /api/revenue-intelligence/*",               "module": "revenue_intelligence_api.py"},
    ],
    "Playbook Execution": [
        {"endpoint": "CRUD /api/playbooks/executions",                "module": "playbook_execution_api.py"},
        {"endpoint": "GET/POST /api/playbook-triggers",               "module": "playbook_triggers_api.py"},
        {"endpoint": "GET /api/playbook-recommendations",             "module": "playbook_recommendations_api.py"},
        {"endpoint": "GET /api/playbook-reports",                     "module": "playbook_reports_api.py"},
    ],
    "Action Interface & Providers": [
        {"endpoint": "CRUD /api/action-bindings",                     "module": "action_interface_api.py"},
        {"endpoint": "CRUD /api/credentials",                         "module": "action_interface_api.py"},
        {"endpoint": "POST /api/webhooks/playbook-callback",          "module": "action_interface_api.py"},
        {"endpoint": "GET /api/providers",                            "module": "action_interface_api.py"},
        {"endpoint": "GET/POST /api/workflow/config",                 "module": "workflow_config_api.py"},
    ],
    "RAG & AI": [
        {"endpoint": "POST /api/signal-analyst/analyze",              "module": "agents/signal_analyst_api.py"},
        {"endpoint": "POST /api/rag-qdrant/query",                    "module": "enhanced_rag_qdrant_api.py"},
        {"endpoint": "POST /api/rag/query",                           "module": "direct_rag_api.py"},
    ],
    "Roadmap & Scenarios": [
        {"endpoint": "POST /api/roadmap/ingest-actuals",              "module": "roadmap_scenario_ingest.py"},
        {"endpoint": "POST /api/roadmap/scenario",                    "module": "roadmap_scenario_ingest.py"},
        {"endpoint": "POST /api/roadmap/compare-scenarios",           "module": "roadmap_scenario_ingest.py"},
        {"endpoint": "GET  /api/roadmap/timeline",                    "module": "roadmap_scenario_ingest.py"},
    ],
    "Data Management & Quality": [
        {"endpoint": "POST /api/upload",                              "module": "upload_api.py"},
        {"endpoint": "GET /api/data-quality/report",                  "module": "data_quality_api.py"},
        {"endpoint": "POST /api/data-management/*",                   "module": "data_management_api.py"},
    ],
    "Admin & Observability": [
        {"endpoint": "GET /api/admin/*",                              "module": "admin_api.py"},
        {"endpoint": "GET /api/observability/*",                      "module": "observability.py"},
        {"endpoint": "GET /api/activity-log",                         "module": "activity_log_api.py"},
        {"endpoint": "GET/PUT /api/settings/features",                "module": "feature_toggle_api.py"},
    ],
    "Onboarding & Registration": [
        {"endpoint": "POST /api/register",                            "module": "registration_api.py"},
        {"endpoint": "POST /api/login",                               "module": "auth (inline)"},
        {"endpoint": "POST /api/onboarding/create",                   "module": "onboarding_api.py"},
    ],
    "Journey & Visualization": [
        {"endpoint": "GET /api/journey/<account_id>",                 "module": "journey_api.py"},
        {"endpoint": "GET /api/journey-viz/<account_id>",             "module": "journey_viz_api.py"},
    ],
}


# ════════════════════════════════════════════════════════════════
# 10. FRONTEND SURFACES
# ════════════════════════════════════════════════════════════════

FRONTEND_SURFACES: List[Dict[str, Any]] = [
    # ── Platform shells ──
    {"id": "dc-platform",         "component": "DCPlatform",          "route": "/dc-dashboard/*",      "tabs": 7,
     "description": "Data Center platform — Exec Dashboard, Tenants, Signal Analyst, RAG, Admin, Data Integration, Settings"},
    {"id": "saas-platform",       "component": "CSPlatform",          "route": "/saas-dashboard",      "tabs": 6,
     "description": "SaaS platform — Dashboard, Playbooks, Reports, Analytics, Settings"},
    {"id": "executive-dashboard", "component": "ExecutiveDashboard",  "route": "/executive-dashboard",
     "description": "Cross-vertical exec view — Health Score tab + Data Quality tab"},

    # ── Core features ──
    {"id": "signal-analyst-ui",   "component": "SignalAnalyst",       "route": "(embedded tab)",
     "description": "AI account analysis — churn/expansion probability, risk drivers, recommended actions"},
    {"id": "rag-analysis-ui",     "component": "RAGAnalysis",         "route": "(embedded tab)",
     "description": "Natural-language retrieval — revenue, churn, expansion, CSM queries with MCP enrichment"},
    {"id": "playbooks-ui",        "component": "Playbooks",           "route": "(embedded tab)",
     "description": "Browse, start, and track 5 system playbooks per account"},
    {"id": "playbook-reports-ui", "component": "PlaybookReports",     "route": "(embedded tab)",
     "description": "Execution reports, outcomes, step completion tracking"},

    # ── Journey & Visualization ──
    {"id": "journey-dashboard",   "component": "JourneyDashboardV3",  "route": "/journey/:accountId",
     "description": "4-view journey — Health Overview, Qualitative Signals, Signal Analyst, Correlation Analysis"},
    {"id": "journey-visualizer",  "component": "JourneyVisualizer",   "route": "/journey-visualizer",
     "description": "Wizard A synthetic journey visualization with pattern distribution"},

    # ── Admin ──
    {"id": "admin-dashboard",     "component": "AdminDashboard",      "route": "(embedded tab)",
     "description": "Wizard B pattern insights + Wizard C weight calibration"},

    # ── Data ──
    {"id": "data-integration",    "component": "DCDataIntegration",   "route": "(embedded tab)",
     "description": "Upload (drag-drop), upload history, template downloads"},
    {"id": "onboarding-wizard",   "component": "OnboardingWizard",    "route": "/onboarding",
     "description": "9-step onboarding: Account → Business → Pillars → Events → Criteria → Sources → Review → Team → Training"},

    # ── Settings ──
    {"id": "dc-settings",         "component": "DCSettings",          "route": "(embedded tab)",
     "description": "7 sub-tabs: Pillar Weights, KPI Ranges, Events, Data Quality, Config, Integrations, Users"},
    {"id": "openai-key-settings", "component": "OpenAIKeySettings",   "route": "(settings modal)",
     "description": "Configure OpenAI API key for RAG system"},
    {"id": "n8n-settings",        "component": "N8NWorkflowSettings", "route": "(settings modal)",
     "description": "Configure n8n workflow automation"},
    {"id": "governance-settings", "component": "GovernanceSettings",  "route": "(settings modal)",
     "description": "Governance and compliance rule management"},
    {"id": "playbook-automation", "component": "PlaybookAutomationSettings", "route": "(settings modal)",
     "description": "Playbook trigger thresholds and automation rules"},
]


# ════════════════════════════════════════════════════════════════
# 11. OBSERVABILITY & INFRASTRUCTURE
# ════════════════════════════════════════════════════════════════

OBSERVABILITY: List[Dict[str, Any]] = [
    {
        "id": "observability-api",
        "name": "Observability API",
        "module": "observability.py",
        "api_endpoints": [
            "GET /api/observability/executions",
            "GET /api/observability/steps",
            "GET /api/observability/cost-analytics",
            "GET /api/observability/calibration",
            "GET /api/observability/health",
        ],
    },
    {
        "id": "cost-tracker",
        "name": "API Cost Tracker",
        "module": "utils/cost_tracker.py",
        "description": "Tracks OpenAI + third-party API costs per customer per call "
                       "(provider, model, tokens_in/out, cost_usd, execution_time_ms)",
    },
    {
        "id": "circuit-breaker",
        "name": "Circuit Breaker + Retry",
        "module": "utils/error_handling.py",
        "description": "Production hardening — configurable failure threshold circuit breaker, "
                       "OpenAI retry decorator, performance logging",
    },
    {
        "id": "activity-logger",
        "name": "Activity Logger",
        "module": "activity_logging.py",
        "description": "Audit trail for all user actions across the platform",
    },
    {
        "id": "celery-worker",
        "name": "Celery Background Workers",
        "module": "celery_app.py",
        "description": "Background task queue for long-running operations "
                       "(health rollups, bulk recalibration, report generation)",
    },
]


# ════════════════════════════════════════════════════════════════
# 12. DATA LAYER (DATABASE TABLES)
# ════════════════════════════════════════════════════════════════

DATABASE_TABLES: List[Dict[str, str]] = [
    {"table": "accounts",                    "model": "Account",                 "purpose": "Customer account records"},
    {"table": "kpis",                        "model": "KPI",                     "purpose": "SaaS KPI values"},
    {"table": "dc2s_kpis",                   "model": "DC2SKPI",                 "purpose": "Data Center KPIs (pillar, weight, status)"},
    {"table": "health_trends",               "model": "HealthTrend",             "purpose": "Monthly health score history"},
    {"table": "qualitative_signals",         "model": "QualitativeSignal",       "purpose": "Survey / interview / email signals"},
    {"table": "account_notes",               "model": "AccountNote",             "purpose": "Manual CSM observations"},
    {"table": "customers",                   "model": "Customer",                "purpose": "Tenant records"},
    {"table": "customer_configs",            "model": "CustomerConfig",          "purpose": "Per-tenant settings and vertical"},
    {"table": "playbook_executions",         "model": "PlaybookExecution",       "purpose": "Playbook execution state machine"},
    {"table": "playbook_reports",            "model": "PlaybookReport",          "purpose": "Execution outcome reports"},
    {"table": "playbook_triggers",           "model": "PlaybookTrigger",         "purpose": "Auto-trigger configuration"},
    {"table": "playbook_step_log",           "model": "PlaybookStepLog",         "purpose": "Per-step audit trail"},
    {"table": "customer_action_bindings",    "model": "CustomerActionBinding",   "purpose": "Action → provider routing"},
    {"table": "integration_credentials",     "model": "IntegrationCredential",   "purpose": "Encrypted credential vault"},
    {"table": "crm_field_mappings",          "model": "CRMFieldMapping",         "purpose": "CS Pulse ↔ CRM field mapping"},
    {"table": "customer_contacts",           "model": "CustomerContact",         "purpose": "Contact role mapping for playbooks"},
    {"table": "customer_workflow_configs",    "model": "CustomerWorkflowConfig",  "purpose": "n8n / workflow system config"},
    {"table": "feature_toggles",             "model": "FeatureToggle",           "purpose": "Per-customer feature flags"},
    {"table": "query_audits",                "model": "QueryAudit",              "purpose": "RAG query audit log"},
    {"table": "weight_calibration_history",  "model": "WeightCalibrationHistory","purpose": "Weight recalibration snapshots"},
    {"table": "status_updates",              "model": "StatusUpdate",            "purpose": "Change audit trail"},
]


# ════════════════════════════════════════════════════════════════
# 13. EXTERNAL INTEGRATIONS SUMMARY
# ════════════════════════════════════════════════════════════════

EXTERNAL_INTEGRATIONS: List[Dict[str, Any]] = [
    {"system": "OpenAI",      "purpose": "LLM analysis + embeddings",   "models": ["gpt-4o", "gpt-4o-mini"], "auth": "API Key"},
    {"system": "Qdrant",      "purpose": "Vector embedding store",       "protocol": "gRPC / REST",          "auth": "Direct client"},
    {"system": "Salesforce",  "purpose": "CRM read + write-back",        "protocol": "REST API v59.0",       "auth": "OAuth2"},
    {"system": "Jira",        "purpose": "Issue tracking",               "protocol": "REST API v3",          "auth": "API Token"},
    {"system": "Slack",       "purpose": "Team communications",          "protocol": "Web API",              "auth": "Bot Token"},
    {"system": "ServiceNow",  "purpose": "Support ticket data",          "protocol": "MCP (mock)",           "auth": "OAuth (planned)"},
    {"system": "n8n",         "purpose": "Workflow automation",           "protocol": "Webhook + REST",       "auth": "API Key + HMAC"},
    {"system": "SMTP",        "purpose": "Email notifications",          "protocol": "SMTP/TLS",             "auth": "SMTP credentials"},
    {"system": "SQLite/PG",   "purpose": "Primary data store",           "protocol": "SQLAlchemy ORM",       "auth": "Connection string"},
]


# ════════════════════════════════════════════════════════════════
# 14. FEATURE FLAGS
# ════════════════════════════════════════════════════════════════

FEATURE_FLAGS: List[Dict[str, str]] = [
    {"flag": "revenue_intelligence", "gates": "Power of 1 model, scaling curves, non-linear ROI, quarterly checkpoints"},
    {"flag": "mcp_integration",      "gates": "MCP server connections, enriched RAG queries, multi-source context"},
    {"flag": "playbook_automation",  "gates": "Auto-trigger evaluation, LLM validation gate"},
    {"flag": "signal_analyst",       "gates": "AI-powered account analysis, churn/expansion predictions"},
]


# ════════════════════════════════════════════════════════════════
# COMPOSITE MATRIX
# ════════════════════════════════════════════════════════════════

PLATFORM_MATRIX: Dict[str, Any] = {
    "platform": "CS Pulse GrowthPulse",
    "version": "3.0",
    "verticals": ["SaaS", "Data Center (DC2S)"],
    "sections": {
        "ai_agents":                  AGENTS,
        "agent_support_services":     AGENT_SUPPORT_SERVICES,
        "revenue_intelligence":       REVENUE_INTELLIGENCE_ENGINES,
        "playbook_system":            PLAYBOOK_SYSTEM,
        "mcp_servers":                MCP_SERVERS,
        "provider_adapters":          PROVIDER_ADAPTERS,
        "feedback_learning":          FEEDBACK_LEARNING,
        "rag_services":               RAG_SERVICES,
        "rest_api_surface":           REST_API_SURFACE,
        "frontend_surfaces":          FRONTEND_SURFACES,
        "observability":              OBSERVABILITY,
        "database_tables":            DATABASE_TABLES,
        "external_integrations":      EXTERNAL_INTEGRATIONS,
        "feature_flags":              FEATURE_FLAGS,
    },
    "totals": {
        "ai_agents":              3,
        "agent_support_services": 6,
        "revenue_engines":        5,
        "playbook_types":         5,
        "mcp_servers":            3,
        "mcp_resources":          11,
        "mcp_tools":              9,
        "provider_adapters":      5,
        "provider_actions":       25,
        "rag_services":           6,
        "api_endpoint_groups":    50,
        "frontend_surfaces":      16,
        "database_tables":        21,
        "external_integrations":  9,
        "feature_flags":          4,
    },
}


# ════════════════════════════════════════════════════════════════
# HUMAN-READABLE PRINTER
# ════════════════════════════════════════════════════════════════

def print_matrix(section: str = None):
    """Print the platform matrix in human-readable format."""

    SEPARATOR = "─" * 72

    def _header(title: str):
        print(f"\n{'═' * 72}")
        print(f"  {title}")
        print(f"{'═' * 72}")

    def _print_agents():
        _header("AI AGENTS")
        for a in AGENTS:
            print(f"\n  [{a['id']}] {a['name']}")
            print(f"  LLM: {a['llm']}")
            print(f"  {a['description']}")
            print(f"  Capabilities:")
            for c in a['capabilities']:
                print(f"    - {c}")
            if a.get('api_endpoints'):
                print(f"  Endpoints: {', '.join(a['api_endpoints'])}")

    def _print_agent_support():
        _header("AGENT SUPPORT SERVICES")
        for s in AGENT_SUPPORT_SERVICES:
            print(f"\n  [{s['id']}] {s['name']}")
            print(f"  Module: {s['module']}")
            print(f"  {s['description']}")

    def _print_revenue():
        _header("REVENUE INTELLIGENCE ENGINES")
        for e in REVENUE_INTELLIGENCE_ENGINES:
            print(f"\n  [{e['id']}] {e['name']}")
            print(f"  Module: {e['module']}")
            if e.get('feature_flag'):
                print(f"  Feature flag: {e['feature_flag']}")
            print(f"  {e['description']}")
            if e.get('capabilities'):
                for c in e['capabilities']:
                    print(f"    - {c}")

    def _print_playbooks():
        _header("PLAYBOOK & ORCHESTRATION SYSTEM")
        for p in PLAYBOOK_SYSTEM:
            print(f"\n  [{p['id']}] {p['name']}")
            print(f"  Module: {p['module']}")
            print(f"  {p['description']}")
            if p.get('playbooks'):
                for pb in p['playbooks']:
                    print(f"    [{pb['id']}] {pb['name']} ({pb['duration']}) -> {', '.join(pb['improves'])}")

    def _print_mcp():
        _header("MCP SERVERS (Model Context Protocol)")
        for m in MCP_SERVERS:
            print(f"\n  [{m['id']}] {m['name']}")
            if m.get('resources'):
                print(f"  Resources ({len(m['resources'])}):")
                for r in m['resources']:
                    print(f"    {r['uri']}  — {r['description']}")
            if m.get('tools'):
                print(f"  Tools ({len(m['tools'])}):")
                for t in m['tools']:
                    rw = "WRITE" if t['write'] else "READ"
                    print(f"    {t['name']}({', '.join(t['params'])})  [{rw}]")

    def _print_providers():
        _header("PROVIDER ADAPTERS (Action Interface)")
        for p in PROVIDER_ADAPTERS:
            print(f"\n  [{p['id']}] {p['name']}")
            print(f"  Auth: {p['auth']}")
            print(f"  Actions ({len(p['supported_actions'])}):")
            for a in p['supported_actions']:
                print(f"    {a['action']}({', '.join(a['params'])})")

    def _print_feedback():
        _header("FEEDBACK & LEARNING SYSTEM")
        for f in FEEDBACK_LEARNING:
            print(f"\n  [{f['id']}] {f['name']}")
            print(f"  Module: {f['module']}")
            if f.get('description'):
                print(f"  {f['description']}")

    def _print_rag():
        _header("RAG & SEARCH SERVICES")
        for r in RAG_SERVICES:
            print(f"\n  [{r['id']}] {r['name']}")
            print(f"  {r['description']}")
            if r.get('api_endpoints'):
                for ep in r['api_endpoints']:
                    print(f"    {ep}")

    def _print_api():
        _header("REST API SURFACE")
        for domain, endpoints in REST_API_SURFACE.items():
            print(f"\n  {domain}:")
            for ep in endpoints:
                print(f"    {ep['endpoint']:<55} ({ep['module']})")

    def _print_frontend():
        _header("FRONTEND SURFACES")
        for f in FRONTEND_SURFACES:
            route = f.get('route', '')
            print(f"\n  [{f['id']}] {f['component']}  {route}")
            print(f"  {f['description']}")

    def _print_observability():
        _header("OBSERVABILITY & INFRASTRUCTURE")
        for o in OBSERVABILITY:
            print(f"\n  [{o['id']}] {o['name']}")
            if o.get('description'):
                print(f"  {o['description']}")

    def _print_db():
        _header("DATABASE TABLES")
        print(f"  {'Table':<35} {'Model':<30} Purpose")
        print(f"  {SEPARATOR}")
        for t in DATABASE_TABLES:
            print(f"  {t['table']:<35} {t['model']:<30} {t['purpose']}")

    def _print_integrations():
        _header("EXTERNAL INTEGRATIONS")
        print(f"  {'System':<15} {'Purpose':<35} {'Auth'}")
        print(f"  {SEPARATOR}")
        for i in EXTERNAL_INTEGRATIONS:
            print(f"  {i['system']:<15} {i['purpose']:<35} {i['auth']}")

    def _print_totals():
        _header("PLATFORM TOTALS")
        for k, v in PLATFORM_MATRIX['totals'].items():
            label = k.replace('_', ' ').title()
            print(f"  {label:<30} {v}")

    printers = {
        'agents':           _print_agents,
        'agent_support':    _print_agent_support,
        'revenue':          _print_revenue,
        'playbooks':        _print_playbooks,
        'mcp':              _print_mcp,
        'providers':        _print_providers,
        'feedback':         _print_feedback,
        'rag':              _print_rag,
        'api':              _print_api,
        'frontend':         _print_frontend,
        'observability':    _print_observability,
        'db':               _print_db,
        'integrations':     _print_integrations,
        'totals':           _print_totals,
    }

    print(f"\n{'█' * 72}")
    print(f"  CS PULSE GROWTHPULSE — PLATFORM CAPABILITY MATRIX")
    print(f"  Version {PLATFORM_MATRIX['version']}  |  Verticals: {', '.join(PLATFORM_MATRIX['verticals'])}")
    print(f"{'█' * 72}")

    if section and section in printers:
        printers[section]()
    else:
        for printer in printers.values():
            printer()

    print(f"\n{'█' * 72}")
    print(f"  END OF MATRIX")
    print(f"{'█' * 72}\n")


# ════════════════════════════════════════════════════════════════
# CLI
# ════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    import sys
    section = sys.argv[1] if len(sys.argv) > 1 else None
    print_matrix(section)
