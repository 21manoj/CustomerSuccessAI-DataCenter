#!/usr/bin/env python3
"""
MCP Tool Bridge — Unified tool discovery across local + MCP tools
==================================================================
Agents don't need to know whether a tool is local or MCP-backed.
They call tools by name through the AgentToolRegistry.

When MCP servers are connected, their tools auto-register alongside
local tools. When MCP is unavailable, agents still work with local data.

This bridges GAP-3 (MCP hardening) by:
  1. Auto-discovering tools from connected MCP servers
  2. Registering them into AgentToolRegistry with graceful fallback
  3. Providing a unified interface for agents
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ============================================================
# MCP TOOL BRIDGE
# ============================================================

class MCPToolBridge:
    """
    Bridges MCP server tools into the AgentToolRegistry.

    On connect: discovers MCP tools → registers as local tools
    On disconnect: unregisters MCP tools, local tools still work
    """

    def __init__(self, tool_registry=None):
        from agent_tool_registry import get_tool_registry, ToolDefinition, ToolCategory
        self.registry = tool_registry or get_tool_registry()
        self._mcp_tools: List[str] = []  # Track registered MCP tool names
        self._mcp_available = False

        try:
            from mcp import ClientSession, StdioServerParameters
            self._mcp_available = True
        except ImportError:
            logger.info("MCP SDK not installed — bridge will use fallback data only")

    def register_mcp_tools(self, mcp_integration=None) -> Dict:
        """
        Discover and register tools from connected MCP servers.

        If MCP is unavailable, registers fallback tools that return
        static/local data with a clear 'source: local_fallback' flag.
        """
        from agent_tool_registry import ToolDefinition, ToolCategory

        registered = []

        # ── Salesforce / CRM Tool ────────────────────────────
        def _crm_account_data(account_id: str, customer_id: int) -> Dict:
            """Fetch CRM data for an account — MCP or fallback."""
            if self._mcp_available and mcp_integration:
                try:
                    loop = asyncio.new_event_loop()
                    data = loop.run_until_complete(
                        mcp_integration.fetch_account_data(account_id, systems=['salesforce'])
                    )
                    loop.close()
                    return {"source": "mcp_salesforce", "data": data}
                except Exception as e:
                    logger.warning(f"MCP Salesforce fetch failed, using fallback: {e}")

            # Fallback: pull from local DB
            try:
                from extensions import db
                from models import Account
                account = Account.query.filter_by(
                    account_id=int(account_id), customer_id=customer_id
                ).first()
                if account:
                    return {
                        "source": "local_fallback",
                        "data": {
                            "account_id": account.account_id,
                            "name": account.name,
                            "revenue": float(account.revenue) if account.revenue else None,
                            "health_score": account.health_score,
                            "status": account.status,
                        },
                    }
            except Exception as e:
                logger.warning(f"Local DB fallback failed: {e}")

            return {"source": "unavailable", "data": {}}

        self.registry.register(ToolDefinition(
            name="crm_account_data",
            description="Fetch CRM/Salesforce data for an account (MCP with local fallback)",
            category=ToolCategory.DATA_RETRIEVAL,
            callable=_crm_account_data,
            input_schema={"account_id": "Account ID", "customer_id": "Customer ID"},
            output_description="Dict with source (mcp_salesforce/local_fallback) and account data",
            requires_customer_id=True,
            requires_account_id=True,
        ))
        self._mcp_tools.append("crm_account_data")
        registered.append("crm_account_data")

        # ── ServiceNow / Incident Tool ───────────────────────
        def _incident_data(account_id: str, customer_id: int) -> Dict:
            """Fetch incident/ticket data — MCP or fallback."""
            if self._mcp_available and mcp_integration:
                try:
                    loop = asyncio.new_event_loop()
                    data = loop.run_until_complete(
                        mcp_integration.fetch_account_data(account_id, systems=['servicenow'])
                    )
                    loop.close()
                    return {"source": "mcp_servicenow", "data": data}
                except Exception as e:
                    logger.warning(f"MCP ServiceNow fetch failed: {e}")

            # Fallback: count tickets from local DB
            try:
                from models import AccountNote
                notes = AccountNote.query.filter_by(account_id=int(account_id)).all()
                ticket_count = sum(1 for n in notes if 'ticket' in (n.note_type or '').lower())
                return {
                    "source": "local_fallback",
                    "data": {"ticket_count": ticket_count, "total_notes": len(notes)},
                }
            except Exception as e:
                logger.warning(f"Local DB fallback failed: {e}")

            return {"source": "unavailable", "data": {}}

        self.registry.register(ToolDefinition(
            name="incident_data",
            description="Fetch incident/ticket data from ServiceNow (MCP with local fallback)",
            category=ToolCategory.DATA_RETRIEVAL,
            callable=_incident_data,
            input_schema={"account_id": "Account ID", "customer_id": "Customer ID"},
            output_description="Dict with source and incident/ticket data",
            requires_customer_id=True,
            requires_account_id=True,
        ))
        self._mcp_tools.append("incident_data")
        registered.append("incident_data")

        # ── Survey / NPS Tool ────────────────────────────────
        def _survey_data(account_id: str, customer_id: int) -> Dict:
            """Fetch NPS/CSAT survey data — MCP or fallback."""
            if self._mcp_available and mcp_integration:
                try:
                    loop = asyncio.new_event_loop()
                    data = loop.run_until_complete(
                        mcp_integration.fetch_account_data(account_id, systems=['surveys'])
                    )
                    loop.close()
                    return {"source": "mcp_surveys", "data": data}
                except Exception as e:
                    logger.warning(f"MCP Survey fetch failed: {e}")

            # Fallback: pull from qualitative signals
            try:
                from models import QualitativeSignal
                signals = QualitativeSignal.query.filter_by(
                    account_id=int(account_id), customer_id=customer_id
                ).order_by(QualitativeSignal.created_at.desc()).limit(5).all()
                return {
                    "source": "local_fallback",
                    "data": {
                        "signals": [
                            {"type": s.signal_type, "value": s.signal_value, "date": s.created_at.isoformat() if s.created_at else None}
                            for s in signals
                        ],
                    },
                }
            except Exception as e:
                logger.warning(f"Local DB fallback failed: {e}")

            return {"source": "unavailable", "data": {}}

        self.registry.register(ToolDefinition(
            name="survey_data",
            description="Fetch NPS/CSAT survey data (MCP with local fallback)",
            category=ToolCategory.DATA_RETRIEVAL,
            callable=_survey_data,
            input_schema={"account_id": "Account ID", "customer_id": "Customer ID"},
            output_description="Dict with source and survey/NPS data",
            requires_customer_id=True,
            requires_account_id=True,
        ))
        self._mcp_tools.append("survey_data")
        registered.append("survey_data")

        logger.info(f"MCP Tool Bridge: registered {len(registered)} tools (MCP available: {self._mcp_available})")
        return {
            "registered": registered,
            "mcp_available": self._mcp_available,
            "total_tools": len(self.registry._tools),
        }

    def unregister_mcp_tools(self) -> None:
        """Remove all MCP-registered tools from the registry."""
        for name in self._mcp_tools:
            self.registry.unregister(name)
        self._mcp_tools.clear()
        logger.info("MCP Tool Bridge: all MCP tools unregistered")

    def get_status(self) -> Dict:
        """Get MCP bridge status."""
        return {
            "mcp_available": self._mcp_available,
            "mcp_tools_registered": len(self._mcp_tools),
            "mcp_tool_names": self._mcp_tools,
            "total_registry_tools": len(self.registry._tools),
        }
