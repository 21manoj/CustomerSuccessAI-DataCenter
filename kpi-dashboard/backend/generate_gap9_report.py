#!/usr/bin/env python3
"""
GAP-9 Report Generation — Full E2E with Synthetic Data
========================================================
Seeds the agentic loop with all 10 sample accounts, populates shared memory,
then generates a complete executive summary report with every section populated.

Run:
    cd kpi-dashboard/backend && python generate_gap9_report.py
"""

import json
import sys
import os
import time
from datetime import datetime

# ============================================================
# STEP 1: Seed agentic loop with 10 sample accounts
# ============================================================

def seed_agentic_loop():
    """Run the agentic loop on all 10 sample accounts with realistic signals."""
    from agent_tool_registry import AgentToolRegistry, register_all_tools, get_tool_registry
    from agent_loop import AgenticLoop, LoopStep, loop_state_to_dict
    from sample_accounts import SAMPLE_ACCOUNTS

    reg = get_tool_registry()
    register_all_tools(reg)

    # Synthetic signal analyst outputs for each account tier
    SIGNAL_PROFILES = {
        "healthy": lambda acct: {
            "predicted_outcome": "expansion",
            "churn_probability": round(0.05 + (100 - acct["expected_health"]) * 0.002, 3),
            "expansion_probability": round(acct["expected_health"] / 100 * 0.95, 3),
            "confidence": {
                "overall_confidence": round(min(0.95, acct["expected_health"] / 100 + 0.08), 2),
                "confidence_level": "high",
            },
            "recommended_actions": [
                {
                    "action": f"Launch expansion upsell campaign for {acct['account_name']}",
                    "priority": "high",
                    "owner": "CSM",
                    "expected_impact": f"+15% NRR growth on ${acct['profile_metadata'].get('arr', 0):,.0f} ARR",
                },
                {
                    "action": f"Schedule feature adoption review — GPU utilization at {acct['kpi_values'].get('P3-KPI1', 'N/A')}%",
                    "priority": "medium",
                    "owner": "CSM",
                    "expected_impact": "+10% product adoption",
                },
            ],
        },
        "risk": lambda acct: {
            "predicted_outcome": "churn" if acct["expected_health"] < 65 else "stable",
            "churn_probability": round(max(0.3, (100 - acct["expected_health"]) / 100), 3),
            "expansion_probability": round(max(0.05, acct["expected_health"] / 100 - 0.35), 3),
            "confidence": {
                "overall_confidence": round(0.60 + (acct["expected_health"] - 50) * 0.005, 2),
                "confidence_level": "medium",
            },
            "recommended_actions": [
                {
                    "action": f"Deploy renewal safeguard playbook — {acct['account_name']} health at {acct['expected_health']}",
                    "priority": "critical",
                    "owner": "CSM",
                    "expected_impact": f"Protect ${acct['profile_metadata'].get('arr', acct['profile_metadata'].get('deployment_value', 0)):,.0f} retention",
                },
                {
                    "action": f"Accelerate support ticket resolution — RMA rate at {acct['kpi_values'].get('P2-KPI1', 'N/A')}%",
                    "priority": "high",
                    "owner": "Support",
                    "expected_impact": "-30% ticket resolution time",
                },
            ],
        },
        "critical": lambda acct: {
            "predicted_outcome": "churn",
            "churn_probability": round(max(0.5, (100 - acct["expected_health"]) / 100), 3),
            "expansion_probability": 0.05,
            "confidence": {
                "overall_confidence": round(max(0.35, acct["expected_health"] / 100 - 0.10), 2),
                "confidence_level": "low",
            },
            "recommended_actions": [
                {
                    "action": f"URGENT: Onboard executive sponsor — {acct['account_name']} at critical {acct['expected_health']} health",
                    "priority": "critical",
                    "owner": "VP CS",
                    "expected_impact": f"Save ${acct['profile_metadata'].get('deployment_value', 0):,.0f} deployment",
                },
                {
                    "action": f"SLA stabilizer: GPU utilization at {acct['kpi_values'].get('P3-KPI1', 'N/A')}% — needs intervention",
                    "priority": "critical",
                    "owner": "Technical CSM",
                    "expected_impact": "+20% GPU utilization, retention safeguard",
                },
                {
                    "action": f"Escalate ticket backlog — RMA rate {acct['kpi_values'].get('P2-KPI1', 'N/A')}% exceeds threshold",
                    "priority": "high",
                    "owner": "Support Lead",
                    "expected_impact": "-50% ticket resolution time",
                },
            ],
        },
    }

    results = []
    total_arr = 0

    for acct in SAMPLE_ACCOUNTS:
        health = acct["expected_health"]
        status = acct["expected_status"]
        acct_name = acct["account_name"]
        acct_id = str(acct["account_id"])
        arr = acct["profile_metadata"].get("arr", acct["profile_metadata"].get("deployment_value", 1_000_000))
        total_arr += arr

        # Determine tier
        if health >= 80:
            tier = "healthy"
        elif health >= 55:
            tier = "risk"
        else:
            tier = "critical"

        profile_fn = SIGNAL_PROFILES[tier]
        signal_data = profile_fn(acct)

        def make_analyze_fn(data):
            return lambda input_data: data

        loop = AgenticLoop(
            analyze_fn=make_analyze_fn(signal_data),
            tool_registry=reg,
        )

        state = loop.run(
            customer_id=1,
            account_id=acct_id,
            input_data=acct["kpi_values"],
            account_arr=arr,
        )

        results.append({
            "account_name": acct_name,
            "account_id": acct_id,
            "tier": tier,
            "health": health,
            "arr": arr,
            "predicted_outcome": state.predicted_outcome,
            "confidence": state.confidence,
            "decision": state.decision,
            "total_dollar_impact": state.total_dollar_impact,
            "total_action_cost": state.total_action_cost,
            "actions_count": len(state.enriched_actions),
            "tools_called": state.tools_called,
            "enriched_actions": state.enriched_actions,
            "duration_ms": state.duration_ms,
        })

    return results, total_arr


# ============================================================
# STEP 2: Generate the full report
# ============================================================

def generate_full_report(loop_results, total_arr):
    """Generate executive summary + portfolio-level report."""
    from agent_tool_registry import get_tool_registry, register_all_tools
    from report_generation_agent import generate_executive_summary
    from outcome_roi_api import DEMO_HISTORICAL_ACTUALS

    reg = get_tool_registry()

    # Generate per-section report (uses shared memory populated by loop)
    report = generate_executive_summary(
        customer_id=1,
        account_id=None,
        account_arr=total_arr,
    )

    return report


# ============================================================
# STEP 3: Render as markdown
# ============================================================

def render_markdown(loop_results, report, total_arr):
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    lines = [
        "# CS Pulse GrowthPulse — Executive Summary Report",
        "",
        f"**Generated:** {now}  ",
        f"**Customer ID:** 1  ",
        f"**Portfolio ARR:** ${total_arr:,.0f}  ",
        f"**Accounts Analyzed:** {len(loop_results)}  ",
        "",
        "---",
        "",
        "## 1. Portfolio Health Overview",
        "",
    ]

    # Summarize from loop results
    healthy = [r for r in loop_results if r["tier"] == "healthy"]
    at_risk = [r for r in loop_results if r["tier"] == "risk"]
    critical = [r for r in loop_results if r["tier"] == "critical"]

    auto_executed = [r for r in loop_results if r["decision"] == "auto_execute"]
    needs_review = [r for r in loop_results if r["decision"] == "needs_review"]
    rejected = [r for r in loop_results if r["decision"] == "rejected"]

    total_impact = sum(r["total_dollar_impact"] for r in loop_results)
    total_cost = sum(r["total_action_cost"] for r in loop_results)
    portfolio_roi = ((total_impact - total_cost) / total_cost * 100) if total_cost > 0 else 0

    lines += [
        "| Metric | Value |",
        "|--------|-------|",
        f"| Healthy Accounts | {len(healthy)} ({sum(r['arr'] for r in healthy):,.0f} ARR) |",
        f"| At-Risk Accounts | {len(at_risk)} ({sum(r['arr'] for r in at_risk):,.0f} ARR) |",
        f"| Critical Accounts | {len(critical)} ({sum(r['arr'] for r in critical):,.0f} ARR) |",
        f"| Total $ Impact (all actions) | ${total_impact:,.0f} |",
        f"| Total $ Cost (all actions) | ${total_cost:,.0f} |",
        f"| Portfolio Action ROI | {portfolio_roi:,.1f}% |",
        f"| Auto-Executed Actions | {len(auto_executed)} accounts |",
        f"| Queued for Review | {len(needs_review)} accounts |",
        f"| Rejected (low confidence) | {len(rejected)} accounts |",
        "",
        "---",
        "",
        "## 2. Per-Account Agentic Loop Results",
        "",
        "| Account | Health | ARR | Predicted | Confidence | Decision | $ Impact | $ Cost | ROI | Actions |",
        "|---------|--------|-----|-----------|------------|----------|----------|--------|-----|---------|",
    ]

    for r in sorted(loop_results, key=lambda x: x["health"], reverse=True):
        acct_roi = ((r['total_dollar_impact'] - r['total_action_cost']) / r['total_action_cost'] * 100) if r['total_action_cost'] > 0 else 0
        lines.append(
            f"| {r['account_name']} | {r['health']} | ${r['arr']:,.0f} | "
            f"{r['predicted_outcome']} | {r['confidence']:.0%} | "
            f"{r['decision']} | ${r['total_dollar_impact']:,.0f} | "
            f"${r['total_action_cost']:,.0f} | {acct_roi:.0f}% | {r['actions_count']} |"
        )

    lines += [
        "",
        "---",
        "",
        "## 3. Enriched Actions with $ Impact (Power of 1)",
        "",
    ]

    for r in loop_results:
        if not r["enriched_actions"]:
            continue
        lines.append(f"### {r['account_name']} ({r['tier'].upper()} — {r['decision']})")
        lines.append("")
        lines.append("| Action | Priority | Po1 Metric | $ Impact | $ Cost | ROI |")
        lines.append("|--------|----------|------------|----------|--------|-----|")
        for a in r["enriched_actions"]:
            action_text = a.get("action", "N/A")
            if len(action_text) > 80:
                action_text = action_text[:77] + "..."
            metric = a.get("power_of_1_metric") or "—"
            dollar = f"${a['dollar_impact']:,.0f}" if a.get("dollar_impact") else "—"
            cost = f"${a['action_cost']:,.0f}" if a.get("action_cost") else "—"
            roi = f"{a['action_roi']:.0%}" if a.get("action_roi") is not None else "—"
            priority = a.get("priority", "—")
            lines.append(f"| {action_text} | {priority} | {metric} | {dollar} | {cost} | {roi} |")
        lines.append("")

    # ── Section 4: Outcome ROI ────────────────────────────────
    roi = report["sections"].get("outcome_roi", {})
    if roi.get("status") == "available" and roi.get("data"):
        d = roi["data"]
        lines += [
            "---",
            "",
            "## 4. Outcome ROI — Historical + Forward Projection",
            "",
            "| Period | Total Impact | Investment (from resource rates) | ROI % | Revenue Protected | Revenue Expanded |",
            "|--------|-------------|----------------------------------|-------|-------------------|------------------|",
        ]
        hist = d.get("historical", {})
        fwd = d.get("forward", {})
        lines.append(
            f"| Historical (6 months) | ${hist.get('total_impact', 0):,.0f} | "
            f"${hist.get('investment', 0):,.0f} | "
            f"{hist.get('roi_pct', 0):.0f}% | ${hist.get('revenue_protected', 0):,.0f} | "
            f"${hist.get('revenue_expanded', 0):,.0f} |"
        )
        lines.append(
            f"| Forward (6 months) | ${fwd.get('total_impact', 0):,.0f} | "
            f"${fwd.get('investment', 0):,.0f} | "
            f"{fwd.get('roi_pct', 0):.0f}% | ${fwd.get('revenue_protected', 0):,.0f} | "
            f"${fwd.get('revenue_expanded', 0):,.0f} |"
        )
        lines += [
            "",
            f"**Combined ROI:** {d.get('combined_roi_pct', 0):.0f}%  ",
            f"**Narrative:** {d.get('narrative', 'N/A')}",
            "",
        ]

    # ── Section 5: Quarterly Progress ─────────────────────────
    qp = report["sections"].get("quarterly_progress", {})
    if qp.get("status") == "available" and qp.get("data"):
        assess = qp["data"].get("assessment", {})
        lines += [
            "---",
            "",
            f"## 5. Quarterly Progress — {qp['data'].get('current_quarter', 'Q?')} ({assess.get('label', '')})",
            "",
            f"**Overall Status:** {assess.get('overall_status', 'N/A')}  ",
            f"**Phase Gate:** {assess.get('phase_gate', 'N/A')}  ",
            "",
        ]
        metrics = assess.get("metrics", [])
        if metrics:
            lines.append("| Metric | Target | Actual | Gap | Status | $ Impact of Gap |")
            lines.append("|--------|--------|--------|-----|--------|-----------------|")
            for m in metrics:
                actual = m.get("actual_value")
                actual_str = f"{actual}" if actual is not None else "not started"
                gap_dollars = m.get("dollar_impact_of_gap", 0)
                lines.append(
                    f"| {m.get('display_name', m.get('metric_id'))} | "
                    f"{m.get('target_value', 'N/A')} | {actual_str} | "
                    f"{m.get('gap_pct', 0)}% | {m.get('status', 'N/A')} | "
                    f"${gap_dollars:,.0f} |"
                )
            lines.append("")
        recs = assess.get("recommendations", [])
        if recs:
            lines.append("**Recommendations:**")
            for rec in recs:
                lines.append(f"- {rec}")
            lines.append("")

    # ── Section 6: Risk & Growth Drivers ──────────────────────
    risk = report["sections"].get("risk_analysis", {})
    if risk.get("data"):
        rd = risk["data"]
        lines += [
            "---",
            "",
            "## 6. Risk & Growth Drivers (from Shared Memory)",
            "",
        ]
        if rd.get("growth_drivers"):
            lines.append("### Growth Drivers")
            lines.append("| Predicted | Confidence | $ Opportunity |")
            lines.append("|-----------|------------|---------------|")
            for g in rd["growth_drivers"]:
                lines.append(
                    f"| {g.get('outcome')} | {g.get('confidence', 0):.0%} | "
                    f"${g.get('dollar_opportunity', 0):,.0f} |"
                )
            lines.append("")
        if rd.get("risk_drivers"):
            lines.append("### Risk Drivers")
            lines.append("| Predicted | Confidence | $ At Risk |")
            lines.append("|-----------|------------|-----------|")
            for r_d in rd["risk_drivers"]:
                lines.append(
                    f"| {r_d.get('outcome')} | {r_d.get('confidence', 0):.0%} | "
                    f"${r_d.get('dollar_at_risk', 0):,.0f} |"
                )
            lines.append("")

    # ── Section 7: Decision Distribution ──────────────────────
    lines += [
        "---",
        "",
        "## 7. Agentic Decision Distribution",
        "",
        "| Decision | Count | Accounts | Total $ Impact | Total $ Cost | Net ROI |",
        "|----------|-------|----------|----------------|--------------|---------|",
    ]

    for decision, group in [("auto_execute", auto_executed), ("needs_review", needs_review), ("rejected", rejected)]:
        names = ", ".join(r["account_name"] for r in group) if group else "—"
        impact = sum(r["total_dollar_impact"] for r in group)
        cost = sum(r["total_action_cost"] for r in group)
        roi = ((impact - cost) / cost * 100) if cost > 0 else 0
        lines.append(f"| {decision} | {len(group)} | {names} | ${impact:,.0f} | ${cost:,.0f} | {roi:.0f}% |")

    lines += [
        "",
        "---",
        "",
        "## 8. Tools Called Across All Loops",
        "",
    ]
    all_tools = {}
    for r in loop_results:
        for t in r["tools_called"]:
            all_tools[t] = all_tools.get(t, 0) + 1
    lines.append("| Tool | Invocations |")
    lines.append("|------|-------------|")
    for tool, count in sorted(all_tools.items(), key=lambda x: -x[1]):
        lines.append(f"| `{tool}` | {count} |")
    lines.append("")

    # ── Footer ────────────────────────────────────────────────
    lines += [
        "---",
        "",
        "*Report generated by GAP-9 Report Generation Agent using data from:*",
        "- *GAP-1: Agentic Loop (6-step ReAct cycle)*",
        "- *GAP-2: Tool Registry (inter-agent tool calls)*",
        "- *GAP-4: Financial Tools (Power of 1 $ quantification)*",
        "- *GAP-5: Auto-Trigger (confidence-based autonomous execution)*",
        "- *GAP-6: Feedback Learning (enrichment from history)*",
        "- *GAP-8: Shared Memory (cross-agent intelligence)*",
        "- *GAP-10: Event Audit Trail (event logging)*",
        "",
    ]

    return "\n".join(lines)


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 70)
    print("  GAP-9 Report Generation — Full E2E with 10 Sample Accounts")
    print("=" * 70)
    print()

    # Step 1: Seed agentic loop
    print("Step 1: Running agentic loop on 10 sample accounts...")
    start = time.time()
    loop_results, total_arr = seed_agentic_loop()
    loop_time = time.time() - start
    print(f"  Done: {len(loop_results)} accounts processed in {loop_time:.1f}s")
    for r in loop_results:
        print(f"    {r['account_name']:30s} | health={r['health']:5.1f} | "
              f"decision={r['decision']:15s} | impact=${r['total_dollar_impact']:>10,.0f} | "
              f"cost=${r['total_action_cost']:>10,.0f}")
    print()

    # Step 2: Generate report
    print("Step 2: Generating executive summary report...")
    report = generate_full_report(loop_results, total_arr)
    print(f"  Done: {len(report['sections'])} sections generated")
    print()

    # Step 3: Render markdown
    print("Step 3: Rendering markdown report...")
    md = render_markdown(loop_results, report, total_arr)

    outpath = os.path.join(os.path.dirname(__file__), "GAP9_EXECUTIVE_SUMMARY_REPORT.md")
    with open(outpath, "w") as f:
        f.write(md)
    print(f"  Written to: {outpath}")
    print()
    print("=" * 70)
    print(f"  Complete. Portfolio: ${total_arr:,.0f} ARR across {len(loop_results)} accounts")
    print("=" * 70)


if __name__ == "__main__":
    main()
