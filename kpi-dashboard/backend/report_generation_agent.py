#!/usr/bin/env python3
"""
Report Generation Agent — AI-powered QBR/ROI report composer
==============================================================
Composes executive reports from:
  - Health score data (health_score_engine)
  - Outcome ROI (outcome_roi_engine) — historical + forward
  - Signal Analyst output (risk/growth drivers)
  - Playbook execution outcomes
  - Quarterly checkpoint status

Output: structured JSON that the frontend renders.
(No PDF/PPTX generation — frontend handles rendering.)

This agent uses the Tool Registry to pull data from other agents.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# ============================================================
# REPORT SECTIONS
# ============================================================

def generate_executive_summary(
    customer_id: int,
    account_id: Optional[str] = None,
    account_arr: Optional[float] = None,
    include_sections: Optional[List[str]] = None,
) -> Dict:
    """
    Generate a complete executive summary report.

    Sections:
      1. Health Overview — current health score + trend
      2. Outcome ROI — historical proof + forward projection
      3. Risk Analysis — top risk/growth drivers
      4. Playbook Status — what's running, what worked
      5. Quarterly Progress — checkpoint vs targets
      6. Recommendations — prioritized next actions with $ impact

    Returns structured JSON for frontend rendering.
    """
    from agent_tool_registry import get_tool_registry

    registry = get_tool_registry()
    sections = include_sections or [
        "health_overview", "outcome_roi", "risk_analysis",
        "playbook_status", "quarterly_progress", "recommendations",
    ]

    report = {
        "report_type": "executive_summary",
        "generated_at": datetime.utcnow().isoformat(),
        "customer_id": customer_id,
        "account_id": account_id,
        "sections": {},
    }

    # ── Section 1: Health Overview ───────────────────────────
    if "health_overview" in sections:
        report["sections"]["health_overview"] = _build_health_section(
            registry, customer_id, account_id
        )

    # ── Section 2: Outcome ROI ───────────────────────────────
    if "outcome_roi" in sections:
        report["sections"]["outcome_roi"] = _build_roi_section(
            registry, account_arr
        )

    # ── Section 3: Risk Analysis ─────────────────────────────
    if "risk_analysis" in sections:
        report["sections"]["risk_analysis"] = _build_risk_section(
            registry, customer_id, account_id
        )

    # ── Section 4: Playbook Status ───────────────────────────
    if "playbook_status" in sections:
        report["sections"]["playbook_status"] = _build_playbook_section(
            registry, customer_id
        )

    # ── Section 5: Quarterly Progress ────────────────────────
    if "quarterly_progress" in sections:
        report["sections"]["quarterly_progress"] = _build_quarterly_section(
            registry, account_arr
        )

    # ── Section 6: Recommendations ───────────────────────────
    if "recommendations" in sections:
        report["sections"]["recommendations"] = _build_recommendations_section(
            registry, customer_id, account_id, account_arr
        )

    return report


# ============================================================
# SECTION BUILDERS
# ============================================================

def _build_health_section(registry, customer_id, account_id) -> Dict:
    """Build the health overview section."""
    section = {
        "title": "Health Overview",
        "status": "available",
        "data": {},
    }

    # Pull from shared memory for latest analysis
    memory_result = registry.invoke(
        "memory_recall",
        customer_id=customer_id,
        account_id=account_id,
        namespace="customer_intelligence",
        limit=1,
    )

    if memory_result.success and memory_result.result:
        latest = memory_result.result[0] if memory_result.result else {}
        try:
            content = json.loads(latest.get("content", "{}"))
            section["data"] = {
                "predicted_outcome": content.get("predicted_outcome"),
                "confidence": content.get("confidence"),
                "total_dollar_impact": content.get("total_dollar_impact"),
                "last_analysis": content.get("timestamp"),
            }
        except (json.JSONDecodeError, TypeError):
            section["data"]["note"] = "No recent analysis available"
    else:
        section["status"] = "no_data"
        section["data"]["note"] = "No health data available. Run Signal Analyst first."

    return section


def _build_roi_section(registry, account_arr) -> Dict:
    """Build the outcome ROI section — historical + forward."""
    section = {
        "title": "Outcome ROI",
        "status": "available",
        "data": {},
    }

    # Use demo data for ROI calculation (works without DB)
    from outcome_roi_api import DEMO_HISTORICAL_ACTUALS
    roi_result = registry.invoke(
        "outcome_roi_story",
        metric_actuals=DEMO_HISTORICAL_ACTUALS,
        target_improvement_pct=1.0,
        account_arr=account_arr,
    )

    if roi_result.success:
        story = roi_result.result
        section["data"] = {
            "historical": {
                "total_impact": story["historical"]["summary"]["total_impact"],
                "investment": story["historical"]["summary"]["total_investment"],
                "roi_pct": story["historical"]["summary"]["roi_pct"],
                "revenue_protected": story["historical"]["summary"]["revenue_protected"],
                "revenue_expanded": story["historical"]["summary"]["revenue_expanded"],
            },
            "forward": {
                "total_impact": story["forward"]["summary"]["total_impact"],
                "investment": story["forward"]["summary"]["total_investment"],
                "roi_pct": story["forward"]["summary"]["roi_pct"],
                "revenue_protected": story["forward"]["summary"]["revenue_protected"],
                "revenue_expanded": story["forward"]["summary"]["revenue_expanded"],
            },
            "combined_roi_pct": story["combined"]["combined_roi_pct"],
            "narrative": story["bridge"]["narrative"],
        }
    else:
        section["status"] = "error"
        section["data"]["error"] = roi_result.error

    return section


def _build_risk_section(registry, customer_id, account_id) -> Dict:
    """Build the risk analysis section from shared memory."""
    section = {
        "title": "Risk & Growth Analysis",
        "status": "available",
        "data": {"risk_drivers": [], "growth_drivers": []},
    }

    memory_result = registry.invoke(
        "memory_recall",
        customer_id=customer_id,
        account_id=account_id,
        namespace="customer_intelligence",
        memory_type="episodic",
        limit=3,
    )

    if memory_result.success and memory_result.result:
        for entry in memory_result.result:
            try:
                content = json.loads(entry.get("content", "{}"))
                if content.get("predicted_outcome") == "churn":
                    section["data"]["risk_drivers"].append({
                        "outcome": content.get("predicted_outcome"),
                        "confidence": content.get("confidence"),
                        "dollar_at_risk": content.get("total_dollar_impact"),
                    })
                elif content.get("predicted_outcome") == "expansion":
                    section["data"]["growth_drivers"].append({
                        "outcome": content.get("predicted_outcome"),
                        "confidence": content.get("confidence"),
                        "dollar_opportunity": content.get("total_dollar_impact"),
                    })
            except (json.JSONDecodeError, TypeError):
                continue

    return section


def _build_playbook_section(registry, customer_id) -> Dict:
    """Build the playbook execution status section."""
    section = {
        "title": "Playbook Execution Status",
        "status": "available",
        "data": {"recent_outcomes": [], "success_rate": None},
    }

    feedback_result = registry.invoke(
        "feedback_history",
        customer_id=customer_id,
        limit=5,
    )

    if feedback_result.success and isinstance(feedback_result.result, list):
        outcomes = feedback_result.result
        section["data"]["recent_outcomes"] = outcomes

        resolved = sum(1 for o in outcomes if o.get("outcome") == "resolved")
        total = len(outcomes)
        if total > 0:
            section["data"]["success_rate"] = round(resolved / total * 100, 1)
    else:
        section["data"]["note"] = "No playbook execution history yet"

    return section


def _build_quarterly_section(registry, account_arr) -> Dict:
    """Build the quarterly checkpoint progress section."""
    section = {
        "title": "Quarterly Progress",
        "status": "available",
        "data": {},
    }

    try:
        from quarterly_checkpoints import get_current_quarter_from_date
        quarter = get_current_quarter_from_date()
    except ImportError:
        quarter = "Q1"

    checkpoint_result = registry.invoke(
        "quarterly_checkpoint",
        quarter=quarter,
        actual_values={},
        account_arr=account_arr,
    )

    if checkpoint_result.success:
        section["data"] = {
            "current_quarter": quarter,
            "assessment": checkpoint_result.result,
        }
    else:
        section["status"] = "error"
        section["data"]["error"] = checkpoint_result.error

    return section


def _build_recommendations_section(registry, customer_id, account_id, account_arr) -> Dict:
    """Build the prioritized recommendations section with $ impact."""
    section = {
        "title": "Prioritized Recommendations",
        "status": "available",
        "data": {"recommendations": []},
    }

    # Get playbook recommendations
    if account_id:
        rec_result = registry.invoke(
            "playbook_recommend",
            account_id=account_id,
            customer_id=customer_id,
        )
        if rec_result.success and isinstance(rec_result.result, dict):
            recs = rec_result.result.get("recommendations", [])
            section["data"]["recommendations"] = recs[:5]

    # Enrich top recommendations with $ impact
    for rec in section["data"]["recommendations"]:
        playbook = rec.get("playbook_id", "")
        # Map playbooks to Power of 1 metrics
        PLAYBOOK_METRIC_MAP = {
            "activation-blitz": "TTFV",
            "expansion-accelerator": "NRR",
            "voc-sprint": "NRR",
            "renewal-safeguard": "GRR",
            "sla-stabilizer": "ticket_resolution_time",
        }
        metric_id = PLAYBOOK_METRIC_MAP.get(playbook)
        if metric_id:
            po1_result = registry.invoke(
                "power_of_1_calc",
                metric_id=metric_id,
                improvement_pct=1.0,
                account_arr=account_arr,
            )
            if po1_result.success and isinstance(po1_result.result, dict):
                rec["dollar_impact_per_pct"] = po1_result.result.get("total_impact")

    return section


# ============================================================
# API BLUEPRINT
# ============================================================

from flask import Blueprint, request as flask_request, jsonify
from auth_middleware import get_current_customer_id

report_generation_api = Blueprint('report_generation_api', __name__)


@report_generation_api.route('/api/reports/executive-summary', methods=['GET'])
def get_executive_summary():
    """Generate an executive summary report."""
    customer_id = get_current_customer_id()
    if not customer_id:
        return jsonify({'error': 'Authentication required'}), 401

    account_id = flask_request.args.get('account_id')
    arr = flask_request.args.get('arr', type=float)

    report = generate_executive_summary(
        customer_id=customer_id,
        account_id=account_id,
        account_arr=arr,
    )

    return jsonify(report)


@report_generation_api.route('/api/reports/executive-summary/demo', methods=['GET'])
def get_demo_executive_summary():
    """Generate a demo executive summary — no auth required."""
    report = generate_executive_summary(
        customer_id=1,
        account_id=None,
        account_arr=10_000_000,
    )
    report["demo_mode"] = True
    return jsonify(report)
