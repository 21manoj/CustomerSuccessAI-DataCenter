#!/usr/bin/env python3
"""
Agent Tool Registry — Central registry for all tools available to agents
=========================================================================
Any agent can call any registered tool by name. This is the backbone
for inter-agent communication and the agentic loop.

Design:
  - Each tool is a callable with typed input/output + description
  - Tools are registered at app startup
  - Agents discover tools via registry, not direct imports
  - Supports sync and async tools
  - Every invocation is logged for audit

This is NOT MCP — MCP is for external systems. This registry is for
internal platform tools that agents need to call.
"""

import time
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


# ============================================================
# TOOL DEFINITION
# ============================================================

class ToolCategory(str, Enum):
    FINANCIAL = "financial"
    ANALYSIS = "analysis"
    DATA_RETRIEVAL = "data_retrieval"
    ACTION = "action"
    MEMORY = "memory"


@dataclass
class ToolDefinition:
    """A registered tool that agents can call."""
    name: str
    description: str
    category: ToolCategory
    callable: Callable
    input_schema: Dict[str, str]  # param_name → type description
    output_description: str
    requires_customer_id: bool = True
    requires_account_id: bool = False


@dataclass
class ToolResult:
    """Result from a tool invocation."""
    tool_name: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    duration_ms: int = 0


# ============================================================
# REGISTRY
# ============================================================

class AgentToolRegistry:
    """
    Central registry for all tools available to AI agents.

    Usage:
        registry = AgentToolRegistry()
        registry.register(ToolDefinition(...))
        result = registry.invoke("power_of_1_calc", improvement_pct=4.0)
    """

    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self._invocation_log: List[Dict] = []

    def register(self, tool: ToolDefinition) -> None:
        """Register a tool. Overwrites if name already exists."""
        self._tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name} [{tool.category.value}]")

    def unregister(self, name: str) -> None:
        """Remove a tool from the registry."""
        self._tools.pop(name, None)

    def list_tools(self, category: Optional[ToolCategory] = None) -> List[Dict]:
        """List all registered tools, optionally filtered by category."""
        tools = self._tools.values()
        if category:
            tools = [t for t in tools if t.category == category]
        return [
            {
                "name": t.name,
                "description": t.description,
                "category": t.category.value,
                "input_schema": t.input_schema,
                "output_description": t.output_description,
            }
            for t in tools
        ]

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        """Get a tool definition by name."""
        return self._tools.get(name)

    def has_tool(self, name: str) -> bool:
        return name in self._tools

    def invoke(self, name: str, **kwargs) -> ToolResult:
        """
        Invoke a tool by name with keyword arguments.
        Returns ToolResult with success/failure and result data.
        """
        tool = self._tools.get(name)
        if not tool:
            return ToolResult(
                tool_name=name,
                success=False,
                error=f"Tool '{name}' not found. Available: {list(self._tools.keys())}",
            )

        start = time.time()
        try:
            result = tool.callable(**kwargs)
            duration_ms = int((time.time() - start) * 1000)

            log_entry = {
                "tool": name,
                "success": True,
                "duration_ms": duration_ms,
                "timestamp": time.time(),
                "kwargs_keys": list(kwargs.keys()),
            }
            self._invocation_log.append(log_entry)
            logger.info(f"Tool invoked: {name} ({duration_ms}ms)")

            return ToolResult(
                tool_name=name,
                success=True,
                result=result,
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = int((time.time() - start) * 1000)
            log_entry = {
                "tool": name,
                "success": False,
                "error": str(e),
                "duration_ms": duration_ms,
                "timestamp": time.time(),
            }
            self._invocation_log.append(log_entry)
            logger.error(f"Tool failed: {name} — {e}")

            return ToolResult(
                tool_name=name,
                success=False,
                error=str(e),
                duration_ms=duration_ms,
            )

    def get_invocation_log(self, limit: int = 50) -> List[Dict]:
        """Return recent invocation log entries."""
        return self._invocation_log[-limit:]

    def get_tools_for_llm_prompt(self) -> str:
        """
        Format all tools as a string for injection into LLM system prompts.
        This tells the agent what tools it can request.
        """
        lines = ["Available tools:"]
        for tool in self._tools.values():
            params = ", ".join(f"{k}: {v}" for k, v in tool.input_schema.items())
            lines.append(
                f"  - {tool.name}({params}): {tool.description} → {tool.output_description}"
            )
        return "\n".join(lines)


# ============================================================
# SINGLETON INSTANCE
# ============================================================

_global_registry: Optional[AgentToolRegistry] = None


def get_tool_registry() -> AgentToolRegistry:
    """Get the global tool registry singleton."""
    global _global_registry
    if _global_registry is None:
        _global_registry = AgentToolRegistry()
    return _global_registry


# ============================================================
# REGISTER ALL PLATFORM TOOLS
# ============================================================

def register_all_tools(registry: Optional[AgentToolRegistry] = None) -> AgentToolRegistry:
    """
    Register all platform tools with the registry.
    Called at app startup.
    """
    reg = registry or get_tool_registry()

    # ── Financial Tools ──────────────────────────────────────

    def _power_of_1_calc(metric_id: str, improvement_pct: float = 1.0,
                         account_arr: Optional[float] = None) -> Dict:
        from power_of_1_model import calculate_power_of_1_impact
        return calculate_power_of_1_impact(metric_id, improvement_pct, account_arr)

    reg.register(ToolDefinition(
        name="power_of_1_calc",
        description="Calculate dollar impact of a % improvement in a Power of 1 metric",
        category=ToolCategory.FINANCIAL,
        callable=_power_of_1_calc,
        input_schema={
            "metric_id": "One of: TTFV, NRR, GRR, ticket_resolution_time, product_adoption, expansion_rate",
            "improvement_pct": "Percentage improvement (e.g., 1.0, 4.0, 6.0)",
            "account_arr": "Optional account ARR for scaling (default $10M base)",
        },
        output_description="Dict with direct_impact, compounding_impact, total_impact, roi, payback_months",
        requires_customer_id=False,
    ))

    def _portfolio_impact(improvement_pct: float = 1.0,
                          total_arr: Optional[float] = None) -> Dict:
        from power_of_1_model import calculate_portfolio_impact
        return calculate_portfolio_impact(improvement_pct, total_arr)

    reg.register(ToolDefinition(
        name="portfolio_impact_calc",
        description="Calculate total Power of 1 impact across all 6 metrics",
        category=ToolCategory.FINANCIAL,
        callable=_portfolio_impact,
        input_schema={
            "improvement_pct": "Target improvement % (1.0-6.0)",
            "total_arr": "Optional total ARR for scaling",
        },
        output_description="Dict with per-metric impacts, totals, scaling scenarios, time economics",
        requires_customer_id=False,
    ))

    def _outcome_roi_story(metric_actuals: Dict, target_improvement_pct: float = 1.0,
                           account_arr: Optional[float] = None,
                           projection_months: int = 6) -> Dict:
        from outcome_roi_engine import calculate_outcome_story
        return calculate_outcome_story(
            metric_actuals=metric_actuals,
            target_improvement_pct=target_improvement_pct,
            account_arr=account_arr,
            projection_months=projection_months,
        )

    reg.register(ToolDefinition(
        name="outcome_roi_story",
        description="Calculate historical + forward outcome ROI story",
        category=ToolCategory.FINANCIAL,
        callable=_outcome_roi_story,
        input_schema={
            "metric_actuals": "Dict of metric_id → {baseline, current}",
            "target_improvement_pct": "Forward target % (default 1.0 — Power of 1)",
            "account_arr": "Optional ARR for scaling",
            "projection_months": "Forward projection months (default 6)",
        },
        output_description="Dict with historical, forward, combined, bridge narrative",
        requires_customer_id=False,
    ))

    def _quarterly_checkpoint(quarter: str, actual_values: Dict,
                              account_arr: Optional[float] = None) -> Dict:
        from quarterly_checkpoints import assess_quarter, assessment_to_dict
        assessment = assess_quarter(quarter, actual_values, account_arr)
        return assessment_to_dict(assessment)

    reg.register(ToolDefinition(
        name="quarterly_checkpoint",
        description="Assess current metrics against quarterly targets — returns gap analysis",
        category=ToolCategory.FINANCIAL,
        callable=_quarterly_checkpoint,
        input_schema={
            "quarter": "Q1, Q2, Q3, or Q4",
            "actual_values": "Dict of metric_id → current value",
            "account_arr": "Optional ARR for dollar gap scaling",
        },
        output_description="Dict with per-metric assessment, phase gate result, recommendations",
        requires_customer_id=False,
    ))

    # ── Analysis Tools ───────────────────────────────────────

    def _health_score_calc(kpi_values: Dict, customer_id: int) -> Dict:
        """Calculate health score from KPI values using reference ranges."""
        try:
            from health_score_engine import calculate_health_scores
            return calculate_health_scores(kpi_values, customer_id)
        except ImportError:
            return {"error": "health_score_engine not available"}

    reg.register(ToolDefinition(
        name="health_score_calc",
        description="Calculate health scores from KPI values using reference ranges",
        category=ToolCategory.ANALYSIS,
        callable=_health_score_calc,
        input_schema={
            "kpi_values": "Dict of kpi_name → value",
            "customer_id": "Customer ID for loading reference ranges",
        },
        output_description="Dict with overall score, category scores, risk flags",
        requires_customer_id=True,
    ))

    def _playbook_recommend(account_id: str, customer_id: int,
                            health_score: Optional[float] = None,
                            kpi_values: Optional[Dict] = None) -> Dict:
        """Get playbook recommendations for an account.

        When kpi_values are provided (DC2S vertical), evaluates PB-01 through
        PB-06 from vertical_config.py. Otherwise falls back to generic playbooks.
        """
        try:
            from playbook_recommendations_api import get_recommendations_for_account
            return get_recommendations_for_account(
                account_id, customer_id, health_score, kpi_values=kpi_values
            )
        except (ImportError, Exception) as e:
            return {"error": str(e), "recommendations": []}

    reg.register(ToolDefinition(
        name="playbook_recommend",
        description="Get ranked playbook recommendations for an account based on health/signals",
        category=ToolCategory.ANALYSIS,
        callable=_playbook_recommend,
        input_schema={
            "account_id": "Account identifier",
            "customer_id": "Customer/tenant ID",
            "health_score": "Optional current health score (0-100)",
            "kpi_values": "Optional dict of KPI code → value for DC2S vertical evaluation",
        },
        output_description="Dict with ranked playbook recommendations and scores",
        requires_customer_id=True,
        requires_account_id=True,
    ))

    # ── Memory Tools ─────────────────────────────────────────

    def _memory_recall(customer_id: int, account_id: Optional[str] = None,
                       memory_type: Optional[str] = None,
                       namespace: Optional[str] = None,
                       limit: int = 10) -> List[Dict]:
        """Recall memories from the agent memory system."""
        try:
            from agent_memory import MemoryStore, MemoryType
            store = MemoryStore()
            results = store.recall(
                customer_id=customer_id,
                account_id=account_id,
                memory_type=MemoryType(memory_type) if memory_type else None,
                namespace=namespace,
                limit=limit,
            )
            return [
                {
                    "content": r.content,
                    "memory_type": r.memory_type,
                    "namespace": r.namespace,
                    "key": r.key,
                    "importance": r.importance,
                    "created_at": r.created_at,
                }
                for r in results
            ]
        except Exception as e:
            return [{"error": str(e)}]

    reg.register(ToolDefinition(
        name="memory_recall",
        description="Recall memories — past analyses, entity facts, playbook outcomes",
        category=ToolCategory.MEMORY,
        callable=_memory_recall,
        input_schema={
            "customer_id": "Customer/tenant ID",
            "account_id": "Optional account ID",
            "memory_type": "Optional: short_term, episodic, entity, semantic, scratchpad",
            "namespace": "Optional: customer_intelligence, signal_analyst, etc.",
            "limit": "Max results (default 10)",
        },
        output_description="List of memory entries with content, type, importance",
    ))

    def _memory_remember(customer_id: int, content: str,
                         memory_type: str = "episodic",
                         namespace: str = "customer_intelligence",
                         account_id: Optional[str] = None,
                         key: Optional[str] = None,
                         importance: float = 0.7,
                         scope: str = "shared") -> Dict:
        """Store a memory in the agent memory system."""
        try:
            from agent_memory import MemoryStore, MemoryEntry, MemoryType, MemoryScope
            store = MemoryStore()
            record_id = store.remember(MemoryEntry(
                memory_type=MemoryType(memory_type),
                scope=MemoryScope(scope),
                content=content,
                customer_id=customer_id,
                account_id=account_id,
                namespace=namespace,
                key=key,
                importance=importance,
            ))
            return {"stored": True, "record_id": record_id}
        except Exception as e:
            return {"stored": False, "error": str(e)}

    reg.register(ToolDefinition(
        name="memory_remember",
        description="Store a memory — analysis result, insight, or entity fact — for future use by any agent",
        category=ToolCategory.MEMORY,
        callable=_memory_remember,
        input_schema={
            "customer_id": "Customer/tenant ID",
            "content": "Memory content string",
            "memory_type": "episodic, entity, semantic, or scratchpad (default: episodic)",
            "namespace": "Namespace for grouping (default: customer_intelligence)",
            "account_id": "Optional account ID",
            "key": "Optional unique key for upsert",
            "importance": "0.0-1.0 importance score (default 0.7)",
            "scope": "shared, account, customer, or agent (default: shared)",
        },
        output_description="Dict with stored: bool, record_id: int",
    ))

    # ── Data Retrieval Tools ─────────────────────────────────

    def _feedback_history(customer_id: int, playbook_type: Optional[str] = None,
                          limit: int = 10) -> List[Dict]:
        """Retrieve past playbook execution outcomes for learning."""
        try:
            from qdrant_feedback_loop import get_feedback_history
            return get_feedback_history(customer_id, playbook_type, limit)
        except (ImportError, Exception) as e:
            return [{"error": str(e)}]

    reg.register(ToolDefinition(
        name="feedback_history",
        description="Retrieve past playbook execution outcomes — what worked, what didn't",
        category=ToolCategory.DATA_RETRIEVAL,
        callable=_feedback_history,
        input_schema={
            "customer_id": "Customer/tenant ID",
            "playbook_type": "Optional playbook type filter",
            "limit": "Max results (default 10)",
        },
        output_description="List of execution outcomes with success rates and KPI improvements",
    ))

    logger.info(f"Registered {len(reg._tools)} tools in AgentToolRegistry")
    return reg
