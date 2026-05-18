#!/usr/bin/env python3
"""One-off audit: customer 334 persona dashboards vs context graph + accounts."""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_v3_minimal import app
from extensions import db
from models import Account, HealthScore, ContextNode, ContextEdge, User
from sqlalchemy import func
from utils.context_graph import aggregate_revenue_across_accounts

CUSTOMER_ID = int(os.environ.get("CUSTOMER_ID", "334"))
EMAIL = os.environ.get("AUDIT_EMAIL", "dc2s_super@test.com")
PASSWORD = os.environ.get("AUDIT_PASSWORD", "DC2_Super_2024!")


def main():
    with app.app_context():
        accounts = Account.query.filter_by(customer_id=CUSTOMER_ID).all()
        account_ids = [a.account_id for a in accounts]
        active = [a for a in accounts if (a.account_status or "") == "active"]

        sum_revenue = sum(float(a.revenue or 0) for a in accounts)
        sum_active_rev = sum(float(a.revenue or 0) for a in active)

        cg_counts = dict(
            db.session.query(ContextNode.node_type, func.count(ContextNode.node_id))
            .filter(ContextNode.customer_id == CUSTOMER_ID)
            .group_by(ContextNode.node_type)
            .all()
        )
        edge_count = (
            ContextEdge.query.join(ContextNode, ContextNode.node_id == ContextEdge.from_node_id)
            .filter(ContextNode.customer_id == CUSTOMER_ID)
            .count()
        )
        rev_cg = aggregate_revenue_across_accounts(CUSTOMER_ID, account_ids)

        client = app.test_client()
        login_resp = client.post("/api/login", json={"email": EMAIL, "password": PASSWORD})
        if login_resp.status_code != 200:
            print(json.dumps({"error": "login failed", "status": login_resp.status_code, "body": login_resp.get_json()}))
            sys.exit(1)

        paths = [
            "/api/executive/cro-dashboard",
            "/api/executive/cfo-dashboard",
            "/api/executive/ceo-dashboard",
            "/api/v1/health-summary",
            "/api/v1/accounts",
            "/api/outcome-roi/portfolio-summary",
            "/api/v1/daily-actions",
            "/api/v1/team-capacity",
            "/api/v1/csm-scorecard",
            "/api/v1/playbook-success-metrics",
        ]
        apis = {}
        for path in paths:
            r = client.get(path)
            apis[path] = {"status": r.status_code, "body": r.get_json()}

        cro = apis["/api/executive/cro-dashboard"]["body"] or {}
        cfo = apis["/api/executive/cfo-dashboard"]["body"] or {}
        ceo = apis["/api/executive/ceo-dashboard"]["body"] or {}
        hs = apis["/api/v1/health-summary"]["body"] or {}
        roi = apis["/api/outcome-roi/portfolio-summary"]["body"] or {}

        report = {
            "customer_id": CUSTOMER_ID,
            "ground_truth": {
                "accounts": len(accounts),
                "active": len(active),
                "churned": sum(1 for a in accounts if (a.account_status or "") == "churned"),
                "sum_account_revenue": round(sum_revenue, 2),
                "sum_active_revenue": round(sum_active_rev, 2),
                "context_graph_nodes": cg_counts,
                "context_graph_edges": edge_count,
                "context_graph_revenue": rev_cg,
            },
            "apis": {p: apis[p]["status"] for p in paths},
            "cro": {
                "portfolio": cro.get("portfolio"),
                "revenue_summary": cro.get("revenue_summary"),
                "story_arcs_n": len(cro.get("story_arcs") or []),
                "early_warnings_n": len(cro.get("early_warnings") or []),
            },
            "cfo": {k: cfo.get(k) for k in list(cfo.keys())[:12]},
            "ceo": {k: ceo.get(k) for k in list(ceo.keys())[:15]},
            "health_summary": hs,
            "portfolio_roi": roi,
            "daily_actions": (apis["/api/v1/daily-actions"]["body"] or {}).get("summary"),
            "team_capacity_n": len((apis["/api/v1/team-capacity"]["body"] or {}).get("csms") or []),
        }
        print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
