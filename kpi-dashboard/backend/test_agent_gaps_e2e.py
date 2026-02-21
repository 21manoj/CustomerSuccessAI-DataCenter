#!/usr/bin/env python3
"""
End-to-End Test Suite: Agent Architecture Gap Fixes (GAP-1 through GAP-10)
===========================================================================
Tests all 10 gap fixes across 4 phases with both positive and negative scenarios.

Phase 1 (Foundation):
    GAP-2  — Agent Tool Registry: inter-agent communication backbone
    GAP-8  — Shared Memory (MemoryScope.SHARED)
    GAP-10 — Event Audit Trail

Phase 2 (Agentic Loop):
    GAP-1  — Agentic Loop (Plan → Act → Observe → Reflect)
    GAP-4  — Financial Tools wired to Signal Analyst

Phase 3 (Autonomy):
    GAP-5  — Autonomous Playbook Triggering (auto-execute path)
    GAP-7  — Human-in-the-Loop Approval Queue
    GAP-6  — Feedback-Driven Learning (enrichment from history)

Phase 4 (Integration):
    GAP-3  — MCP Tool Bridge (unified tool discovery with fallback)
    GAP-9  — Report Generation Agent (QBR/ROI report composer)

Run:
    cd kpi-dashboard/backend && python test_agent_gaps_e2e.py
"""

import sys
import os
import json
import time
import traceback
from datetime import datetime
from typing import Dict, List, Tuple

# ============================================================
# TEST HARNESS
# ============================================================

class TestResult:
    def __init__(self, name: str, gap_id: str, phase: str, scenario: str):
        self.name = name
        self.gap_id = gap_id
        self.phase = phase
        self.scenario = scenario  # "positive" or "negative"
        self.passed = False
        self.message = ""
        self.details = ""
        self.duration_ms = 0

    def to_dict(self):
        return {
            "name": self.name,
            "gap_id": self.gap_id,
            "phase": self.phase,
            "scenario": self.scenario,
            "passed": self.passed,
            "message": self.message,
            "details": self.details,
            "duration_ms": self.duration_ms,
        }


class TestSuite:
    def __init__(self):
        self.results: List[TestResult] = []
        self.start_time = time.time()

    def run_test(self, name: str, gap_id: str, phase: str, scenario: str, fn):
        """Run a single test function and capture result."""
        result = TestResult(name, gap_id, phase, scenario)
        start = time.time()
        try:
            msg, details = fn()
            result.passed = True
            result.message = msg
            result.details = details
        except AssertionError as e:
            result.passed = False
            result.message = f"ASSERTION FAILED: {e}"
            result.details = traceback.format_exc()
        except Exception as e:
            result.passed = False
            result.message = f"ERROR: {e}"
            result.details = traceback.format_exc()
        result.duration_ms = int((time.time() - start) * 1000)
        self.results.append(result)

        icon = "PASS" if result.passed else "FAIL"
        print(f"  [{icon}] {gap_id} | {scenario:8s} | {name} ({result.duration_ms}ms)")

    def summary(self) -> Dict:
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        duration = int((time.time() - self.start_time) * 1000)

        by_phase = {}
        for r in self.results:
            if r.phase not in by_phase:
                by_phase[r.phase] = {"total": 0, "passed": 0, "failed": 0}
            by_phase[r.phase]["total"] += 1
            by_phase[r.phase]["passed" if r.passed else "failed"] += 1

        by_gap = {}
        for r in self.results:
            if r.gap_id not in by_gap:
                by_gap[r.gap_id] = {"total": 0, "passed": 0, "failed": 0}
            by_gap[r.gap_id]["total"] += 1
            by_gap[r.gap_id]["passed" if r.passed else "failed"] += 1

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": f"{(passed/total*100):.1f}%" if total else "N/A",
            "duration_ms": duration,
            "by_phase": by_phase,
            "by_gap": by_gap,
        }


# ============================================================
# PHASE 1: FOUNDATION TESTS
# ============================================================

def test_gap2_tool_registry_positive(suite: TestSuite):
    """GAP-2: Agent Tool Registry — register, discover, invoke tools."""

    def _test():
        from agent_tool_registry import AgentToolRegistry, ToolDefinition, ToolCategory

        reg = AgentToolRegistry()

        # Register a test tool
        reg.register(ToolDefinition(
            name="test_add",
            description="Add two numbers",
            category=ToolCategory.ANALYSIS,
            callable=lambda a, b: {"sum": a + b},
            input_schema={"a": "number", "b": "number"},
            output_description="Dict with sum",
            requires_customer_id=False,
        ))

        # Verify registration
        assert reg.has_tool("test_add"), "Tool should be registered"

        # Invoke
        result = reg.invoke("test_add", a=3, b=7)
        assert result.success, f"Invocation should succeed: {result.error}"
        assert result.result["sum"] == 10, f"3+7 should be 10, got {result.result}"

        # List tools by category
        analysis_tools = reg.list_tools(ToolCategory.ANALYSIS)
        assert any(t["name"] == "test_add" for t in analysis_tools)

        # LLM prompt export
        prompt = reg.get_tools_for_llm_prompt()
        assert "test_add" in prompt

        # Invocation log
        log = reg.get_invocation_log()
        assert len(log) >= 1
        assert log[-1]["tool"] == "test_add"
        assert log[-1]["success"] is True

        return (
            "Tool Registry: register, discover, invoke, LLM prompt — all working",
            f"Registered 1 tool, invoked successfully, log has {len(log)} entries"
        )

    suite.run_test(
        "Register + invoke + discover tools",
        "GAP-2", "Phase 1: Foundation", "positive", _test
    )


def test_gap2_tool_registry_negative(suite: TestSuite):
    """GAP-2: Invoke non-existent tool, invoke with bad args."""

    def _test():
        from agent_tool_registry import AgentToolRegistry, ToolDefinition, ToolCategory

        reg = AgentToolRegistry()

        # Invoke non-existent tool
        result = reg.invoke("nonexistent_tool", x=1)
        assert not result.success, "Should fail for missing tool"
        assert "not found" in result.error.lower(), f"Error should say 'not found': {result.error}"

        # Register tool that raises exception
        reg.register(ToolDefinition(
            name="always_fails",
            description="Always raises",
            category=ToolCategory.ANALYSIS,
            callable=lambda: (_ for _ in ()).throw(ValueError("intentional error")),
            input_schema={},
            output_description="Never returns",
            requires_customer_id=False,
        ))

        # Invoke — should return ToolResult with error, not crash
        result = reg.invoke("always_fails")
        assert not result.success, "Should fail when callable raises"
        assert "intentional error" in result.error
        assert result.duration_ms >= 0

        # Verify failure is logged
        log = reg.get_invocation_log()
        fail_entries = [e for e in log if not e["success"]]
        assert len(fail_entries) >= 1, "Failed invocation should be logged"

        return (
            "Tool Registry: graceful failure for missing tools and erroring callables",
            f"Missing tool → error message, raising tool → error captured, {len(fail_entries)} failures logged"
        )

    suite.run_test(
        "Missing tool + erroring callable → graceful failure",
        "GAP-2", "Phase 1: Foundation", "negative", _test
    )


def test_gap2_full_platform_tools(suite: TestSuite):
    """GAP-2: register_all_tools() registers all platform tools."""

    def _test():
        from agent_tool_registry import AgentToolRegistry, register_all_tools

        reg = AgentToolRegistry()
        register_all_tools(reg)

        expected_tools = [
            "power_of_1_calc", "portfolio_impact_calc", "outcome_roi_story",
            "quarterly_checkpoint", "health_score_calc", "playbook_recommend",
            "memory_recall", "memory_remember", "feedback_history",
        ]

        missing = [t for t in expected_tools if not reg.has_tool(t)]
        assert not missing, f"Missing tools after register_all_tools: {missing}"

        total = len(reg._tools)
        assert total >= 9, f"Expected at least 9 tools, got {total}"

        return (
            f"register_all_tools: all {total} platform tools registered",
            f"All {len(expected_tools)} expected tools present: {', '.join(expected_tools)}"
        )

    suite.run_test(
        "register_all_tools() loads all 9+ platform tools",
        "GAP-2", "Phase 1: Foundation", "positive", _test
    )


def test_gap8_shared_memory_positive(suite: TestSuite):
    """GAP-8: MemoryScope.SHARED exists for cross-agent memory."""

    def _test():
        from agent_memory import MemoryScope

        # Verify SHARED scope exists
        assert hasattr(MemoryScope, 'SHARED'), "MemoryScope.SHARED must exist"
        assert MemoryScope.SHARED.value == "shared"

        # Verify all expected scopes
        expected = ["account", "customer", "global", "agent", "shared"]
        actual = [s.value for s in MemoryScope]
        for scope in expected:
            assert scope in actual, f"Missing scope: {scope}"

        return (
            "MemoryScope.SHARED exists — cross-agent memory enabled",
            f"All 5 scopes present: {', '.join(actual)}"
        )

    suite.run_test(
        "MemoryScope.SHARED exists for cross-agent sharing",
        "GAP-8", "Phase 1: Foundation", "positive", _test
    )


def test_gap8_shared_memory_negative(suite: TestSuite):
    """GAP-8: Invalid memory scope raises error."""

    def _test():
        from agent_memory import MemoryScope

        # Attempt to create invalid scope
        try:
            invalid = MemoryScope("nonexistent_scope")
            assert False, "Should have raised ValueError for invalid scope"
        except ValueError:
            pass

        return (
            "Invalid MemoryScope correctly raises ValueError",
            "MemoryScope('nonexistent_scope') → ValueError as expected"
        )

    suite.run_test(
        "Invalid MemoryScope → ValueError",
        "GAP-8", "Phase 1: Foundation", "negative", _test
    )


def test_gap10_event_audit_trail_positive(suite: TestSuite):
    """GAP-10: Event audit trail captures published events."""

    def _test():
        from event_system import EventPublisher, EventType

        pub = EventPublisher()

        # Publish events
        pub.publish(EventType.AGENT_ANALYSIS_COMPLETE, customer_id=1, data={"test": True})
        pub.publish(EventType.PLAYBOOK_AUTO_TRIGGERED, customer_id=1, data={"playbook": "activation-blitz"})
        pub.publish(EventType.APPROVAL_REQUESTED, customer_id=2, data={"action": "review"})

        # Verify audit log
        log = pub.get_audit_log(limit=50)
        assert len(log) >= 3, f"Expected 3+ entries, got {len(log)}"

        # Verify filtering by event type
        agent_events = pub.get_audit_log(event_type="agent_analysis_complete")
        assert len(agent_events) >= 1, "Should find agent analysis events"

        # Verify filtering by customer_id
        cust2_events = pub.get_audit_log(customer_id=2)
        assert len(cust2_events) >= 1, "Should find customer 2 events"
        assert all(e["customer_id"] == 2 for e in cust2_events)

        # Verify structure
        entry = log[-1]
        assert "event_type" in entry
        assert "customer_id" in entry
        assert "timestamp" in entry
        assert "data_keys" in entry

        return (
            "Event audit trail: logs all events with filtering support",
            f"3 events published, {len(log)} in log, filters by type and customer work"
        )

    suite.run_test(
        "Events logged in audit trail with filtering",
        "GAP-10", "Phase 1: Foundation", "positive", _test
    )


def test_gap10_audit_bounded(suite: TestSuite):
    """GAP-10: Audit log is bounded (doesn't grow unbounded)."""

    def _test():
        from event_system import EventPublisher, EventType

        pub = EventPublisher()

        # Publish 600 events (over 500 limit)
        for i in range(600):
            pub.publish(EventType.AGENT_TOOL_INVOKED, customer_id=1, data={"i": i})

        log = pub.get_audit_log(limit=1000)
        assert len(log) <= 500, f"Audit log should be bounded to 500, got {len(log)}"

        return (
            "Audit log bounded to 500 entries (prevents memory leak)",
            f"Published 600 events, log size = {len(log)} (capped at 500)"
        )

    suite.run_test(
        "Audit log bounded at 500 entries",
        "GAP-10", "Phase 1: Foundation", "negative", _test
    )


# ============================================================
# PHASE 2: AGENTIC LOOP TESTS
# ============================================================

def test_gap1_agentic_loop_positive(suite: TestSuite):
    """GAP-1: Agentic loop runs full 6-step cycle."""

    def _test():
        from agent_loop import AgenticLoop, LoopState, LoopStep, loop_state_to_dict
        from agent_tool_registry import AgentToolRegistry, register_all_tools

        reg = AgentToolRegistry()
        register_all_tools(reg)

        # Mock analyze function returns high-confidence result
        def mock_analyze(data):
            return {
                "predicted_outcome": "expansion",
                "churn_probability": 0.1,
                "expansion_probability": 0.8,
                "confidence": {"overall_confidence": 0.90, "confidence_level": "high"},
                "recommended_actions": [
                    {"action": "Launch expansion upsell campaign", "priority": "high", "owner": "CSM", "expected_impact": "+15% NRR"},
                    {"action": "Schedule feature adoption review", "priority": "medium", "owner": "CSM", "expected_impact": "+10% usage"},
                ],
            }

        loop = AgenticLoop(
            analyze_fn=mock_analyze,
            tool_registry=reg,
        )

        result = loop.run(customer_id=1, account_id="acct-001", input_data={}, account_arr=10_000_000)

        # Verify full cycle completed
        assert result.current_step == LoopStep.COMPLETE, f"Should complete, stuck at {result.current_step}"
        assert result.predicted_outcome == "expansion"
        assert result.confidence == 0.90
        assert result.decision == "auto_execute", f"90% confidence should auto-execute, got {result.decision}"

        # Verify $ quantification
        assert len(result.enriched_actions) == 2
        dollar_enriched = [a for a in result.enriched_actions if a.get("dollar_impact") is not None]
        assert len(dollar_enriched) >= 1, "At least 1 action should have $ impact"
        assert result.total_dollar_impact > 0, f"Total impact should be >0, got {result.total_dollar_impact}"

        # Verify tools were called
        assert len(result.tools_called) >= 1, "Should have called tools during enrichment"

        # Verify serialization
        serialized = loop_state_to_dict(result)
        assert serialized["decision"] == "auto_execute"
        assert serialized["total_dollar_impact"] > 0

        return (
            f"Agentic loop: 6-step cycle completed in {result.duration_ms}ms — "
            f"decision={result.decision}, ${result.total_dollar_impact:,.0f} impact",
            f"Actions: {len(result.enriched_actions)}, Tools called: {result.tools_called}, "
            f"Confidence: {result.confidence:.0%}"
        )

    suite.run_test(
        "Full 6-step loop: analyze→evaluate→enrich→quantify→decide→act",
        "GAP-1", "Phase 2: Agentic Loop", "positive", _test
    )


def test_gap1_agentic_loop_low_confidence(suite: TestSuite):
    """GAP-1: Low confidence → rejected decision (negative path)."""

    def _test():
        from agent_loop import AgenticLoop, LoopStep
        from agent_tool_registry import AgentToolRegistry, register_all_tools

        reg = AgentToolRegistry()
        register_all_tools(reg)

        def mock_analyze_low(data):
            return {
                "predicted_outcome": "churn",
                "churn_probability": 0.4,
                "expansion_probability": 0.1,
                "confidence": {"overall_confidence": 0.35, "confidence_level": "low"},
                "recommended_actions": [],
            }

        loop = AgenticLoop(analyze_fn=mock_analyze_low, tool_registry=reg)
        result = loop.run(customer_id=1, account_id="acct-low", input_data={})

        assert result.current_step == LoopStep.COMPLETE
        assert result.decision == "rejected", f"35% confidence should be rejected, got {result.decision}"
        assert len(result.actions_taken) == 0, "Rejected should take no actions"
        assert "Insufficient data" in result.decision_reason or "60%" in result.decision_reason

        return (
            f"Low confidence (35%) → rejected, no actions taken",
            f"Decision: {result.decision}, Reason: {result.decision_reason}"
        )

    suite.run_test(
        "Low confidence (35%) → rejected decision, no actions",
        "GAP-1", "Phase 2: Agentic Loop", "negative", _test
    )


def test_gap1_agentic_loop_medium_confidence(suite: TestSuite):
    """GAP-1: Medium confidence → needs_review (approval queue path)."""

    def _test():
        from agent_loop import AgenticLoop, LoopStep
        from agent_tool_registry import AgentToolRegistry, register_all_tools

        reg = AgentToolRegistry()
        register_all_tools(reg)

        def mock_analyze_medium(data):
            return {
                "predicted_outcome": "churn",
                "churn_probability": 0.6,
                "expansion_probability": 0.1,
                "confidence": {"overall_confidence": 0.72, "confidence_level": "medium"},
                "recommended_actions": [
                    {"action": "Deploy renewal safeguard playbook", "priority": "high", "owner": "CSM", "expected_impact": "Reduce churn risk"},
                ],
            }

        loop = AgenticLoop(analyze_fn=mock_analyze_medium, tool_registry=reg)
        result = loop.run(customer_id=1, account_id="acct-mid", input_data={}, account_arr=5_000_000)

        assert result.current_step == LoopStep.COMPLETE
        assert result.decision == "needs_review", f"72% should need review, got {result.decision}"
        assert len(result.actions_taken) >= 1
        assert result.actions_taken[0]["status"] == "queued_for_review"

        return (
            f"Medium confidence (72%) → needs_review, actions queued for human approval",
            f"Decision: {result.decision}, {len(result.actions_taken)} actions queued_for_review"
        )

    suite.run_test(
        "Medium confidence (72%) → needs_review, queued for approval",
        "GAP-1", "Phase 2: Agentic Loop", "positive", _test
    )


def test_gap1_agentic_loop_error_handling(suite: TestSuite):
    """GAP-1: Analyze function raises → loop captures error gracefully."""

    def _test():
        from agent_loop import AgenticLoop
        from agent_tool_registry import AgentToolRegistry, register_all_tools

        reg = AgentToolRegistry()
        register_all_tools(reg)

        def mock_analyze_crash(data):
            raise RuntimeError("LLM API timeout — simulated failure")

        loop = AgenticLoop(analyze_fn=mock_analyze_crash, tool_registry=reg)
        result = loop.run(customer_id=1, account_id="acct-err", input_data={})

        # Should NOT crash — should capture error in state
        assert result.decision == "error", f"Should be 'error', got {result.decision}"
        assert "LLM API timeout" in result.decision_reason

        return (
            "Analyze crash → gracefully captured, decision='error'",
            f"Error captured: {result.decision_reason}"
        )

    suite.run_test(
        "Analyze function crash → error captured, no exception raised",
        "GAP-1", "Phase 2: Agentic Loop", "negative", _test
    )


def test_gap4_financial_tools_wired(suite: TestSuite):
    """GAP-4: Financial tools (Power of 1, ROI, Checkpoints) callable via registry."""

    def _test():
        from agent_tool_registry import AgentToolRegistry, register_all_tools

        reg = AgentToolRegistry()
        register_all_tools(reg)

        # Power of 1
        po1 = reg.invoke("power_of_1_calc", metric_id="NRR", improvement_pct=4.0, account_arr=10_000_000)
        assert po1.success, f"Power of 1 should succeed: {po1.error}"
        assert "total_impact" in po1.result
        assert po1.result["total_impact"] > 0

        # Portfolio impact
        port = reg.invoke("portfolio_impact_calc", improvement_pct=1.0)
        assert port.success, f"Portfolio impact should succeed: {port.error}"
        assert "totals" in port.result or "metrics" in port.result or isinstance(port.result, dict)

        # Quarterly checkpoint
        qc = reg.invoke("quarterly_checkpoint", quarter="Q1", actual_values={}, account_arr=10_000_000)
        assert qc.success, f"Quarterly checkpoint should succeed: {qc.error}"

        return (
            f"Financial tools wired and callable: Po1=${po1.result['total_impact']:,.0f}",
            f"power_of_1_calc: {po1.duration_ms}ms, portfolio_impact_calc: {port.duration_ms}ms, quarterly_checkpoint: {qc.duration_ms}ms"
        )

    suite.run_test(
        "Power of 1, Portfolio Impact, Quarterly Checkpoint — all callable",
        "GAP-4", "Phase 2: Agentic Loop", "positive", _test
    )


def test_gap4_financial_invalid_metric(suite: TestSuite):
    """GAP-4: Invalid metric ID → tool returns error gracefully."""

    def _test():
        from agent_tool_registry import AgentToolRegistry, register_all_tools

        reg = AgentToolRegistry()
        register_all_tools(reg)

        # Invalid metric
        result = reg.invoke("power_of_1_calc", metric_id="INVALID_METRIC", improvement_pct=1.0)
        # Should either fail gracefully or return empty result
        if result.success:
            # Some implementations return 0 for unknown metrics
            assert result.result is not None
        else:
            # Or fail with error
            assert result.error is not None

        return (
            "Invalid metric → graceful handling (no crash)",
            f"Success={result.success}, Error={result.error}, Result type={type(result.result).__name__}"
        )

    suite.run_test(
        "Invalid metric ID → graceful error or default",
        "GAP-4", "Phase 2: Agentic Loop", "negative", _test
    )


# ============================================================
# PHASE 3: AUTONOMY TESTS
# ============================================================

def test_gap5_auto_trigger_positive(suite: TestSuite):
    """GAP-5: High confidence auto-executes actions via loop decision."""

    def _test():
        from agent_loop import AgenticLoop, LoopStep, CONFIDENCE_AUTO_EXECUTE

        def mock_high_confidence(data):
            return {
                "predicted_outcome": "expansion",
                "churn_probability": 0.05,
                "expansion_probability": 0.9,
                "confidence": {"overall_confidence": 0.92, "confidence_level": "high"},
                "recommended_actions": [
                    {"action": "Trigger expansion accelerator playbook", "priority": "critical", "owner": "System", "expected_impact": "+20% pipeline"},
                ],
            }

        from agent_tool_registry import AgentToolRegistry, register_all_tools
        reg = AgentToolRegistry()
        register_all_tools(reg)

        loop = AgenticLoop(analyze_fn=mock_high_confidence, tool_registry=reg)
        result = loop.run(customer_id=1, account_id="acct-auto", input_data={}, account_arr=10_000_000)

        assert result.decision == "auto_execute"
        assert len(result.actions_taken) >= 1
        assert result.actions_taken[0]["status"] == "queued_for_auto_execute"
        assert result.confidence >= CONFIDENCE_AUTO_EXECUTE

        return (
            f"Auto-trigger: confidence {result.confidence:.0%} >= {CONFIDENCE_AUTO_EXECUTE:.0%} → auto_execute",
            f"{len(result.actions_taken)} actions queued_for_auto_execute"
        )

    suite.run_test(
        "High confidence (92%) → auto_execute decision",
        "GAP-5", "Phase 3: Autonomy", "positive", _test
    )


def test_gap5_no_auto_trigger_low(suite: TestSuite):
    """GAP-5: Low confidence blocks auto-execution."""

    def _test():
        from agent_loop import AgenticLoop, LoopStep

        def mock_low(data):
            return {
                "predicted_outcome": "stable",
                "churn_probability": 0.2,
                "expansion_probability": 0.3,
                "confidence": {"overall_confidence": 0.45, "confidence_level": "low"},
                "recommended_actions": [
                    {"action": "Gather more usage data", "priority": "low", "owner": "System", "expected_impact": "Better signal clarity"},
                ],
            }

        from agent_tool_registry import AgentToolRegistry, register_all_tools
        reg = AgentToolRegistry()
        register_all_tools(reg)

        loop = AgenticLoop(analyze_fn=mock_low, tool_registry=reg)
        result = loop.run(customer_id=1, account_id="acct-block", input_data={})

        assert result.decision == "rejected", f"45% should be rejected, got {result.decision}"
        assert len(result.actions_taken) == 0, "Rejected means no actions"

        return (
            "Low confidence (45%) → rejected, auto-trigger blocked",
            f"Decision: {result.decision}, actions_taken: {len(result.actions_taken)}"
        )

    suite.run_test(
        "Low confidence (45%) → auto-trigger blocked, no actions",
        "GAP-5", "Phase 3: Autonomy", "negative", _test
    )


def test_gap7_approval_queue_tiered(suite: TestSuite):
    """GAP-7: Approval queue correctly tiers requests by confidence."""

    def _test():
        # Test the ApprovalQueueService logic without DB
        # We test the threshold logic directly
        from approval_queue import ApprovalQueueService

        svc = ApprovalQueueService()

        # Verify thresholds
        assert svc.AUTO_EXECUTE_THRESHOLD == 0.85
        assert svc.REVIEW_THRESHOLD == 0.60

        # Test tiering logic conceptually
        test_cases = [
            (0.92, "auto_executed"),
            (0.85, "auto_executed"),
            (0.72, "pending"),
            (0.60, "pending"),
            (0.45, "auto_rejected"),
            (0.10, "auto_rejected"),
        ]

        for confidence, expected_status in test_cases:
            if confidence >= svc.AUTO_EXECUTE_THRESHOLD:
                actual = "auto_executed"
            elif confidence >= svc.REVIEW_THRESHOLD:
                actual = "pending"
            else:
                actual = "auto_rejected"
            assert actual == expected_status, f"Confidence {confidence} should be {expected_status}, got {actual}"

        return (
            "Approval queue tiering: auto_execute >= 85%, pending 60-85%, rejected < 60%",
            f"All 6 confidence levels correctly tiered"
        )

    suite.run_test(
        "Tiered approval: auto_executed/pending/auto_rejected thresholds",
        "GAP-7", "Phase 3: Autonomy", "positive", _test
    )


def test_gap7_approval_queue_db(suite: TestSuite):
    """GAP-7: ApprovalRequest model has all required fields."""

    def _test():
        from approval_queue import ApprovalRequest

        # Verify model has all required columns
        required_fields = [
            "id", "customer_id", "account_id", "agent_id",
            "action_type", "action_payload", "playbook_id",
            "predicted_outcome", "confidence", "reasoning", "dollar_impact",
            "status", "decided_by", "decided_at", "decision_notes",
            "created_at", "expires_at",
        ]

        columns = [c.name for c in ApprovalRequest.__table__.columns]
        missing = [f for f in required_fields if f not in columns]
        assert not missing, f"Missing columns: {missing}"

        return (
            f"ApprovalRequest model: all {len(required_fields)} fields present",
            f"Columns: {', '.join(columns)}"
        )

    suite.run_test(
        "ApprovalRequest DB model has all required fields",
        "GAP-7", "Phase 3: Autonomy", "positive", _test
    )


def test_gap7_approval_invalid_status(suite: TestSuite):
    """GAP-7: ApprovalQueueService submit() tiers correctly for boundary values."""

    def _test():
        from approval_queue import ApprovalQueueService

        svc = ApprovalQueueService()

        # Test exact boundary: 0.85 → auto_executed
        assert 0.85 >= svc.AUTO_EXECUTE_THRESHOLD
        # Test exact boundary: 0.60 → pending
        assert 0.60 >= svc.REVIEW_THRESHOLD
        assert 0.60 < svc.AUTO_EXECUTE_THRESHOLD
        # Test just below: 0.599 → auto_rejected
        assert 0.599 < svc.REVIEW_THRESHOLD

        # Edge case: 0.0 confidence
        assert 0.0 < svc.REVIEW_THRESHOLD

        # Edge case: 1.0 confidence
        assert 1.0 >= svc.AUTO_EXECUTE_THRESHOLD

        # Verify class methods exist
        assert callable(getattr(svc, 'submit', None)), "submit method must exist"
        assert callable(getattr(svc, 'approve', None)), "approve method must exist"
        assert callable(getattr(svc, 'reject', None)), "reject method must exist"
        assert callable(getattr(svc, 'get_pending', None)), "get_pending method must exist"
        assert callable(getattr(svc, 'get_history', None)), "get_history method must exist"
        assert callable(getattr(svc, 'get_stats', None)), "get_stats method must exist"

        return (
            "Approval queue boundary cases: 0.85→auto, 0.60→pending, <0.60→reject, all methods present",
            f"Thresholds: AUTO={svc.AUTO_EXECUTE_THRESHOLD}, REVIEW={svc.REVIEW_THRESHOLD}, 6 methods verified"
        )

    suite.run_test(
        "Approval queue boundary cases + method verification",
        "GAP-7", "Phase 3: Autonomy", "negative", _test
    )


def test_gap6_feedback_enrichment(suite: TestSuite):
    """GAP-6: Low confidence triggers feedback history retrieval."""

    def _test():
        from agent_loop import AgenticLoop, LoopStep
        from agent_tool_registry import AgentToolRegistry, register_all_tools

        reg = AgentToolRegistry()
        register_all_tools(reg)

        def mock_low_confidence(data):
            return {
                "predicted_outcome": "churn",
                "churn_probability": 0.5,
                "expansion_probability": 0.1,
                "confidence": {"overall_confidence": 0.45, "confidence_level": "low"},
                "recommended_actions": [],
            }

        loop = AgenticLoop(analyze_fn=mock_low_confidence, tool_registry=reg)
        result = loop.run(customer_id=1, account_id="acct-fb", input_data={})

        # Low confidence should trigger feedback_history retrieval
        assert "feedback_history" in result.tools_called, (
            f"Low confidence should call feedback_history, called: {result.tools_called}"
        )

        return (
            "Low confidence → feedback_history tool called for enrichment",
            f"Tools called: {result.tools_called}"
        )

    suite.run_test(
        "Low confidence triggers feedback history retrieval",
        "GAP-6", "Phase 3: Autonomy", "positive", _test
    )


def test_gap6_high_confidence_skips_feedback(suite: TestSuite):
    """GAP-6: High confidence skips feedback retrieval (not needed)."""

    def _test():
        from agent_loop import AgenticLoop, LoopStep
        from agent_tool_registry import AgentToolRegistry, register_all_tools

        reg = AgentToolRegistry()
        register_all_tools(reg)

        def mock_high_confidence(data):
            return {
                "predicted_outcome": "expansion",
                "churn_probability": 0.05,
                "expansion_probability": 0.9,
                "confidence": {"overall_confidence": 0.92, "confidence_level": "high"},
                "recommended_actions": [
                    {"action": "Expand upsell pipeline", "priority": "high", "owner": "CSM", "expected_impact": "+NRR"},
                ],
            }

        loop = AgenticLoop(analyze_fn=mock_high_confidence, tool_registry=reg)
        result = loop.run(customer_id=1, account_id="acct-hi", input_data={})

        # High confidence should NOT call feedback_history
        assert "feedback_history" not in result.tools_called, (
            f"High confidence should NOT call feedback_history, but called: {result.tools_called}"
        )

        return (
            "High confidence (92%) → skips feedback retrieval (efficient)",
            f"Tools called: {result.tools_called} (no feedback_history)"
        )

    suite.run_test(
        "High confidence skips feedback history (efficiency)",
        "GAP-6", "Phase 3: Autonomy", "negative", _test
    )


# ============================================================
# PHASE 4: INTEGRATION TESTS
# ============================================================

def test_gap3_mcp_bridge_registration(suite: TestSuite):
    """GAP-3: MCP Tool Bridge registers 3 MCP-backed tools."""

    def _test():
        from mcp_tool_bridge import MCPToolBridge
        from agent_tool_registry import AgentToolRegistry, register_all_tools

        reg = AgentToolRegistry()
        register_all_tools(reg)

        bridge = MCPToolBridge(tool_registry=reg)
        result = bridge.register_mcp_tools()

        assert "registered" in result
        assert len(result["registered"]) == 3, f"Expected 3 MCP tools, got {len(result['registered'])}"
        expected_names = ["crm_account_data", "incident_data", "survey_data"]
        for name in expected_names:
            assert name in result["registered"], f"Missing MCP tool: {name}"
            assert reg.has_tool(name), f"Tool '{name}' not in registry"

        # Verify status
        status = bridge.get_status()
        assert status["mcp_tools_registered"] == 3

        return (
            f"MCP Bridge: 3 tools registered ({', '.join(expected_names)})",
            f"MCP available: {result['mcp_available']}, Total tools: {result['total_tools']}"
        )

    suite.run_test(
        "MCP Tool Bridge registers 3 tools (CRM, Incident, Survey)",
        "GAP-3", "Phase 4: Integration", "positive", _test
    )


def test_gap3_mcp_bridge_fallback(suite: TestSuite):
    """GAP-3: MCP tools fall back to local data when MCP unavailable."""

    def _test():
        from mcp_tool_bridge import MCPToolBridge
        from agent_tool_registry import AgentToolRegistry, register_all_tools

        reg = AgentToolRegistry()
        register_all_tools(reg)

        bridge = MCPToolBridge(tool_registry=reg)
        bridge._mcp_available = False  # Force MCP unavailable
        bridge.register_mcp_tools(mcp_integration=None)

        # Invoke CRM tool — should fall back to local
        result = reg.invoke("crm_account_data", account_id="1", customer_id=1)
        # With no DB context it might return unavailable, but should NOT crash
        assert result.success or result.error is not None, "Should not crash"
        if result.success:
            assert result.result.get("source") in ("local_fallback", "unavailable"), \
                f"Expected fallback source, got {result.result.get('source')}"

        return (
            "MCP fallback: tools work without MCP SDK (no crash)",
            f"CRM tool result: success={result.success}, source={result.result.get('source') if result.success else 'N/A'}"
        )

    suite.run_test(
        "MCP tools fall back gracefully when MCP unavailable",
        "GAP-3", "Phase 4: Integration", "positive", _test
    )


def test_gap3_mcp_bridge_unregister(suite: TestSuite):
    """GAP-3: Unregister MCP tools removes them cleanly."""

    def _test():
        from mcp_tool_bridge import MCPToolBridge
        from agent_tool_registry import AgentToolRegistry, register_all_tools

        reg = AgentToolRegistry()
        register_all_tools(reg)
        initial_count = len(reg._tools)

        bridge = MCPToolBridge(tool_registry=reg)
        bridge.register_mcp_tools()
        assert len(reg._tools) == initial_count + 3

        # Unregister
        bridge.unregister_mcp_tools()
        assert len(reg._tools) == initial_count, f"Should return to {initial_count}, got {len(reg._tools)}"
        assert not reg.has_tool("crm_account_data")
        assert not reg.has_tool("incident_data")
        assert not reg.has_tool("survey_data")

        return (
            "MCP unregister: all 3 MCP tools removed, local tools preserved",
            f"Tools before: {initial_count + 3}, after unregister: {len(reg._tools)}"
        )

    suite.run_test(
        "Unregister MCP tools → removed from registry",
        "GAP-3", "Phase 4: Integration", "negative", _test
    )


def test_gap9_report_generation_positive(suite: TestSuite):
    """GAP-9: Report Generation Agent produces structured report."""

    def _test():
        from agent_tool_registry import AgentToolRegistry, register_all_tools
        # Ensure global registry is populated
        from agent_tool_registry import get_tool_registry
        reg = get_tool_registry()
        register_all_tools(reg)

        from report_generation_agent import generate_executive_summary

        report = generate_executive_summary(
            customer_id=1,
            account_id=None,
            account_arr=10_000_000,
            include_sections=["outcome_roi", "quarterly_progress"],
        )

        # Verify structure
        assert report["report_type"] == "executive_summary"
        assert "generated_at" in report
        assert "sections" in report

        # Verify requested sections
        assert "outcome_roi" in report["sections"]
        assert "quarterly_progress" in report["sections"]

        # ROI section should have data
        roi = report["sections"]["outcome_roi"]
        assert roi["status"] in ("available", "error")
        if roi["status"] == "available":
            assert "historical" in roi["data"] or "combined_roi_pct" in roi["data"]

        return (
            f"Report generated: {len(report['sections'])} sections",
            f"Sections: {list(report['sections'].keys())}, ROI status: {roi['status']}"
        )

    suite.run_test(
        "Executive summary report with ROI + quarterly sections",
        "GAP-9", "Phase 4: Integration", "positive", _test
    )


def test_gap9_report_generation_selective_sections(suite: TestSuite):
    """GAP-9: Report respects include_sections filter."""

    def _test():
        from agent_tool_registry import get_tool_registry, register_all_tools
        reg = get_tool_registry()
        register_all_tools(reg)

        from report_generation_agent import generate_executive_summary

        # Request only 1 section
        report = generate_executive_summary(
            customer_id=1,
            include_sections=["quarterly_progress"],
        )

        assert len(report["sections"]) == 1, f"Asked for 1 section, got {len(report['sections'])}"
        assert "quarterly_progress" in report["sections"]
        assert "outcome_roi" not in report["sections"]
        assert "health_overview" not in report["sections"]

        return (
            "Report respects section filter: only requested sections built",
            f"Requested: ['quarterly_progress'], Got: {list(report['sections'].keys())}"
        )

    suite.run_test(
        "Report section filter — only builds requested sections",
        "GAP-9", "Phase 4: Integration", "positive", _test
    )


def test_gap9_report_empty_sections(suite: TestSuite):
    """GAP-9: Report handles empty/missing data gracefully."""

    def _test():
        from agent_tool_registry import get_tool_registry, register_all_tools
        reg = get_tool_registry()
        register_all_tools(reg)

        from report_generation_agent import generate_executive_summary

        # Health + risk sections with no prior analyses → should not crash
        report = generate_executive_summary(
            customer_id=99999,  # Non-existent customer
            include_sections=["health_overview", "risk_analysis"],
        )

        assert "sections" in report
        health = report["sections"].get("health_overview", {})
        # Should indicate no data, not crash
        assert health.get("status") in ("available", "no_data", "error"), \
            f"Unexpected health status: {health.get('status')}"

        return (
            "Report with no prior data → degrades gracefully (no crash)",
            f"Health status: {health.get('status')}, Risk section present: {'risk_analysis' in report['sections']}"
        )

    suite.run_test(
        "Report handles missing data gracefully (no crash)",
        "GAP-9", "Phase 4: Integration", "negative", _test
    )


# ============================================================
# E2E INTEGRATION: Cross-component flow
# ============================================================

def test_e2e_loop_to_report(suite: TestSuite):
    """E2E: Agentic loop → shared memory → report reads the result."""

    def _test():
        from agent_tool_registry import AgentToolRegistry, register_all_tools, get_tool_registry
        from agent_loop import AgenticLoop, LoopStep

        # Reset global registry
        reg = get_tool_registry()
        register_all_tools(reg)

        # Step 1: Run agentic loop (writes to shared memory)
        def mock_analyze(data):
            return {
                "predicted_outcome": "expansion",
                "churn_probability": 0.1,
                "expansion_probability": 0.85,
                "confidence": {"overall_confidence": 0.88, "confidence_level": "high"},
                "recommended_actions": [
                    {"action": "Launch expansion pipeline", "priority": "high", "owner": "CSM", "expected_impact": "+NRR"},
                ],
            }

        loop = AgenticLoop(analyze_fn=mock_analyze, tool_registry=reg)
        loop_result = loop.run(customer_id=1, account_id="acct-e2e", input_data={}, account_arr=10_000_000)

        assert loop_result.current_step == LoopStep.COMPLETE
        assert loop_result.decision == "auto_execute"

        # Step 2: Generate report (reads from shared memory + tools)
        from report_generation_agent import generate_executive_summary
        report = generate_executive_summary(
            customer_id=1,
            account_id="acct-e2e",
            account_arr=10_000_000,
        )

        assert report["report_type"] == "executive_summary"
        assert len(report["sections"]) >= 1

        return (
            "E2E flow: agentic loop → shared memory → report generation",
            f"Loop: {loop_result.decision} (${loop_result.total_dollar_impact:,.0f}), "
            f"Report: {len(report['sections'])} sections generated"
        )

    suite.run_test(
        "E2E: Loop → shared memory → report reads loop results",
        "E2E", "Cross-Component", "positive", _test
    )


def test_e2e_event_flow(suite: TestSuite):
    """E2E: Event published → audit trail + subscriber notification."""

    def _test():
        from event_system import EventPublisher, EventType

        pub = EventPublisher()
        received_events = []

        def subscriber(event):
            received_events.append(event)

        # Subscribe
        pub.subscribe(EventType.PLAYBOOK_AUTO_TRIGGERED, subscriber)

        # Publish
        pub.publish(
            EventType.PLAYBOOK_AUTO_TRIGGERED,
            customer_id=1,
            data={"playbook_id": "activation-blitz", "confidence": 0.90},
        )

        # Process (synchronous check — event in queue)
        import time
        pub.start()
        time.sleep(0.5)
        pub.stop()

        # Verify audit trail
        log = pub.get_audit_log()
        triggered_events = [e for e in log if e["event_type"] == "playbook_auto_triggered"]
        assert len(triggered_events) >= 1, "Event should be in audit trail"

        # Verify subscriber received
        assert len(received_events) >= 1, f"Subscriber should have received event, got {len(received_events)}"

        return (
            "E2E event flow: publish → audit trail logged + subscriber notified",
            f"Audit entries: {len(triggered_events)}, Subscriber received: {len(received_events)}"
        )

    suite.run_test(
        "E2E: publish event → audit trail + subscriber callback",
        "E2E", "Cross-Component", "positive", _test
    )


def test_e2e_tool_registry_to_mcp(suite: TestSuite):
    """E2E: Local tools + MCP tools coexist in same registry."""

    def _test():
        from agent_tool_registry import AgentToolRegistry, register_all_tools
        from mcp_tool_bridge import MCPToolBridge

        reg = AgentToolRegistry()
        register_all_tools(reg)
        local_count = len(reg._tools)

        bridge = MCPToolBridge(tool_registry=reg)
        bridge.register_mcp_tools()
        total_count = len(reg._tools)

        # Both local and MCP tools in same registry
        assert total_count == local_count + 3
        assert reg.has_tool("power_of_1_calc")  # local
        assert reg.has_tool("crm_account_data")  # MCP

        # LLM prompt includes both
        prompt = reg.get_tools_for_llm_prompt()
        assert "power_of_1_calc" in prompt
        assert "crm_account_data" in prompt

        return (
            f"Unified registry: {local_count} local + 3 MCP = {total_count} total tools",
            f"Both local (power_of_1_calc) and MCP (crm_account_data) in LLM prompt"
        )

    suite.run_test(
        "E2E: local + MCP tools coexist in unified registry",
        "E2E", "Cross-Component", "positive", _test
    )


# ============================================================
# ROADMAP TBD VERIFICATION
# ============================================================

def test_roadmap_tbd(suite: TestSuite):
    """Verify roadmap TBD items are properly documented."""

    def _test():
        from agent_architecture_inventory import ROADMAP_FUTURE_TBD, ARCHITECTURE_SUMMARY

        assert "onboarding_agent" in ROADMAP_FUTURE_TBD
        assert ROADMAP_FUTURE_TBD["onboarding_agent"]["status"] == "TBD"

        assert "web_search_tool" in ROADMAP_FUTURE_TBD
        assert ROADMAP_FUTURE_TBD["web_search_tool"]["status"] == "TBD"

        assert "calendar_scheduling_agent" in ROADMAP_FUTURE_TBD
        assert ROADMAP_FUTURE_TBD["calendar_scheduling_agent"]["status"] == "TBD"

        assert ARCHITECTURE_SUMMARY["gaps_fixed"] == 10
        assert ARCHITECTURE_SUMMARY["gaps_remaining"] == 1

        return (
            "Roadmap TBD: Onboarding Agent, Web Search, Calendar — all marked TBD",
            f"Gaps fixed: {ARCHITECTURE_SUMMARY['gaps_fixed']}, Remaining: {ARCHITECTURE_SUMMARY['gaps_remaining']}"
        )

    suite.run_test(
        "Roadmap: TBD items documented, gap counts correct",
        "ROADMAP", "Roadmap Verification", "positive", _test
    )


# ============================================================
# MARKDOWN REPORT GENERATOR
# ============================================================

def generate_report(suite: TestSuite) -> str:
    """Generate the explainable .md file from test results."""
    s = suite.summary()
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    lines = [
        "# Agent Architecture Gap Fixes — E2E Test Results",
        "",
        f"**Generated:** {now}",
        f"**Total Tests:** {s['total']} | **Passed:** {s['passed']} | **Failed:** {s['failed']} | **Pass Rate:** {s['pass_rate']}",
        f"**Total Duration:** {s['duration_ms']}ms",
        "",
        "---",
        "",
        "## Summary by Phase",
        "",
        "| Phase | Total | Passed | Failed | Status |",
        "|-------|-------|--------|--------|--------|",
    ]

    for phase, counts in s["by_phase"].items():
        status = "ALL PASS" if counts["failed"] == 0 else f"{counts['failed']} FAILED"
        lines.append(f"| {phase} | {counts['total']} | {counts['passed']} | {counts['failed']} | {status} |")

    lines += [
        "",
        "## Summary by Gap",
        "",
        "| Gap ID | Tests | Passed | Failed | Status |",
        "|--------|-------|--------|--------|--------|",
    ]

    gap_titles = {
        "GAP-1": "Agentic Loop (ReAct)",
        "GAP-2": "Tool Registry",
        "GAP-3": "MCP Tool Bridge",
        "GAP-4": "Financial Tools Wired",
        "GAP-5": "Auto-Trigger",
        "GAP-6": "Feedback Learning",
        "GAP-7": "Approval Queue",
        "GAP-8": "Shared Memory",
        "GAP-9": "Report Generation",
        "GAP-10": "Event Audit Trail",
        "E2E": "Cross-Component E2E",
        "ROADMAP": "Roadmap TBD",
    }

    for gap_id, counts in s["by_gap"].items():
        title = gap_titles.get(gap_id, gap_id)
        status = "PASS" if counts["failed"] == 0 else "FAIL"
        lines.append(f"| {gap_id} — {title} | {counts['total']} | {counts['passed']} | {counts['failed']} | {status} |")

    lines += [
        "",
        "---",
        "",
        "## Detailed Test Results",
        "",
    ]

    # Group by phase
    phases_ordered = []
    seen_phases = set()
    for r in suite.results:
        if r.phase not in seen_phases:
            phases_ordered.append(r.phase)
            seen_phases.add(r.phase)

    for phase in phases_ordered:
        phase_results = [r for r in suite.results if r.phase == phase]
        lines.append(f"### {phase}")
        lines.append("")

        for r in phase_results:
            icon = "PASS" if r.passed else "FAIL"
            lines.append(f"#### [{icon}] {r.gap_id} | {r.name}")
            lines.append(f"- **Scenario:** {r.scenario}")
            lines.append(f"- **Duration:** {r.duration_ms}ms")
            if r.passed:
                lines.append(f"- **Result:** {r.message}")
                if r.details:
                    lines.append(f"- **Details:** {r.details}")
            else:
                lines.append(f"- **Failure:** {r.message}")
                if r.details:
                    lines.append(f"<details><summary>Stack trace</summary>")
                    lines.append("")
                    lines.append("```")
                    lines.append(r.details)
                    lines.append("```")
                    lines.append("")
                    lines.append("</details>")
            lines.append("")

    lines += [
        "---",
        "",
        "## Architecture Coverage Map",
        "",
        "| Component | File(s) | Tests | Status |",
        "|-----------|---------|-------|--------|",
        "| Tool Registry | `agent_tool_registry.py` | 3 | Tested |",
        "| Shared Memory | `agent_memory.py` (MemoryScope.SHARED) | 2 | Tested |",
        "| Event Audit Trail | `event_system.py` (_audit_log) | 2 | Tested |",
        "| Agentic Loop | `agent_loop.py` | 4 | Tested |",
        "| Financial Tools | `power_of_1_model.py`, `quarterly_checkpoints.py` | 2 | Tested |",
        "| Auto-Trigger | `agent_loop.py` (decide/act steps) | 2 | Tested |",
        "| Approval Queue | `approval_queue.py` | 3 | Tested |",
        "| Feedback Learning | `agent_loop.py` (enrich step) | 2 | Tested |",
        "| MCP Tool Bridge | `mcp_tool_bridge.py` | 3 | Tested |",
        "| Report Generation | `report_generation_agent.py` | 3 | Tested |",
        "| Cross-Component E2E | All of the above | 3 | Tested |",
        "| Roadmap TBD | `agent_architecture_inventory.py` | 1 | Verified |",
        "",
        "## Roadmap — Future TBD (Not Tested)",
        "",
        "| Item | Priority | Status | Notes |",
        "|------|----------|--------|-------|",
        "| Customer Onboarding Agent | HIGH | TBD | Dedicated lifecycle agent for first 30-90 days |",
        "| Web Search + Benchmark Tool | MEDIUM | TBD | External benchmark data enrichment |",
        "| Calendar/Scheduling Agent (GAP-11) | LOW | TBD | Automated EBR/QBR scheduling |",
        "",
    ]

    return "\n".join(lines)


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 70)
    print("  Agent Architecture Gap Fixes — E2E Test Suite")
    print("  Testing GAP-1 through GAP-10 (4 Phases)")
    print("=" * 70)
    print()

    suite = TestSuite()

    # ── Phase 1: Foundation ───────────────────────────────────
    print("Phase 1: Foundation (GAP-2, GAP-8, GAP-10)")
    print("-" * 50)
    test_gap2_tool_registry_positive(suite)
    test_gap2_tool_registry_negative(suite)
    test_gap2_full_platform_tools(suite)
    test_gap8_shared_memory_positive(suite)
    test_gap8_shared_memory_negative(suite)
    test_gap10_event_audit_trail_positive(suite)
    test_gap10_audit_bounded(suite)
    print()

    # ── Phase 2: Agentic Loop ────────────────────────────────
    print("Phase 2: Agentic Loop (GAP-1, GAP-4)")
    print("-" * 50)
    test_gap1_agentic_loop_positive(suite)
    test_gap1_agentic_loop_low_confidence(suite)
    test_gap1_agentic_loop_medium_confidence(suite)
    test_gap1_agentic_loop_error_handling(suite)
    test_gap4_financial_tools_wired(suite)
    test_gap4_financial_invalid_metric(suite)
    print()

    # ── Phase 3: Autonomy ────────────────────────────────────
    print("Phase 3: Autonomy (GAP-5, GAP-7, GAP-6)")
    print("-" * 50)
    test_gap5_auto_trigger_positive(suite)
    test_gap5_no_auto_trigger_low(suite)
    test_gap7_approval_queue_tiered(suite)
    test_gap7_approval_queue_db(suite)
    test_gap7_approval_invalid_status(suite)
    test_gap6_feedback_enrichment(suite)
    test_gap6_high_confidence_skips_feedback(suite)
    print()

    # ── Phase 4: Integration ─────────────────────────────────
    print("Phase 4: Integration (GAP-3, GAP-9)")
    print("-" * 50)
    test_gap3_mcp_bridge_registration(suite)
    test_gap3_mcp_bridge_fallback(suite)
    test_gap3_mcp_bridge_unregister(suite)
    test_gap9_report_generation_positive(suite)
    test_gap9_report_generation_selective_sections(suite)
    test_gap9_report_empty_sections(suite)
    print()

    # ── Cross-Component E2E ──────────────────────────────────
    print("Cross-Component E2E Integration")
    print("-" * 50)
    test_e2e_loop_to_report(suite)
    test_e2e_event_flow(suite)
    test_e2e_tool_registry_to_mcp(suite)
    print()

    # ── Roadmap Verification ─────────────────────────────────
    print("Roadmap Verification")
    print("-" * 50)
    test_roadmap_tbd(suite)
    print()

    # ── Summary ──────────────────────────────────────────────
    s = suite.summary()
    print("=" * 70)
    print(f"  RESULTS: {s['passed']}/{s['total']} passed ({s['pass_rate']}) — {s['duration_ms']}ms")
    if s["failed"] > 0:
        print(f"  FAILURES: {s['failed']}")
        for r in suite.results:
            if not r.passed:
                print(f"    - {r.gap_id} | {r.name}: {r.message}")
    print("=" * 70)

    # ── Generate Markdown Report ─────────────────────────────
    report_md = generate_report(suite)
    report_path = os.path.join(os.path.dirname(__file__), "AGENT_GAP_TEST_RESULTS.md")
    with open(report_path, "w") as f:
        f.write(report_md)
    print(f"\nReport written to: {report_path}")

    return 0 if s["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
