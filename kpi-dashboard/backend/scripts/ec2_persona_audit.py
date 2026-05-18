#!/usr/bin/env python3
"""EC2 persona + context-graph audit — JSON only on stdout."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CUSTOMER_ID = int(os.environ.get("CUSTOMER_ID", "334"))
EMAIL = os.environ.get("AUDIT_EMAIL", "dc2s_super@test.com")
PASSWORD = os.environ.get("AUDIT_PASSWORD", "DC2_Super_2024!")


def main():
    # Suppress app startup prints
    import io
    from contextlib import redirect_stdout, redirect_stderr

    buf = io.StringIO()
    with redirect_stdout(buf), redirect_stderr(buf):
        from app_v3_minimal import app
        from extensions import db
        from models import Account, ContextNode, ContextEdge
        from sqlalchemy import func
        from utils.context_graph import aggregate_revenue_across_accounts

        issues = []
        results = {"customer_id": CUSTOMER_ID, "endpoints": {}, "checks": {}, "issues": issues}

        with app.app_context():
            accounts = Account.query.filter_by(customer_id=CUSTOMER_ID).all()
            account_ids = [a.account_id for a in accounts]
            sum_rev = round(sum(float(a.revenue or 0) for a in accounts), 2)

            cg_nodes = dict(
                db.session.query(ContextNode.node_type, func.count(ContextNode.node_id))
                .filter(ContextNode.customer_id == CUSTOMER_ID)
                .group_by(ContextNode.node_type)
                .all()
            )
            cg_rev = aggregate_revenue_across_accounts(CUSTOMER_ID, account_ids)

            results["ground_truth"] = {
                "accounts": len(accounts),
                "sum_revenue": sum_rev,
                "context_nodes": cg_nodes,
                "context_revenue": cg_rev,
            }

            client = app.test_client()
            login = client.post("/api/login", json={"email": EMAIL, "password": PASSWORD})
            results["login"] = login.status_code
            if login.status_code != 200:
                issues.append(f"LOGIN failed: {login.status_code}")
                print(json.dumps(results, indent=2))
                return

            paths = [
                ("cro", "/api/executive/cro-dashboard"),
                ("cfo", "/api/executive/cfo-dashboard"),
                ("ceo", "/api/executive/ceo-dashboard"),
                ("health_summary", "/api/v1/health-summary"),
                ("accounts", "/api/v1/accounts"),
                ("portfolio_roi", "/api/outcome-roi/portfolio-summary"),
                ("daily_actions", "/api/v1/daily-actions"),
                ("team_capacity", "/api/v1/team-capacity"),
                ("csm_scorecard", "/api/v1/csm-scorecard"),
                ("playbook_metrics", "/api/v1/playbook-success-metrics"),
                ("health_history", "/api/v1/health-score-history?months=12"),
                ("revenue_timeline", "/api/executive/revenue-timeline?account_id=3225"),
            ]

            for key, path in paths:
                r = client.get(path)
                body = r.get_json(silent=True) or {}
                results["endpoints"][key] = {"status": r.status_code, "error": body.get("error")}

            cro = client.get("/api/executive/cro-dashboard").get_json(silent=True) or {}
            cfo = client.get("/api/executive/cfo-dashboard").get_json(silent=True) or {}
            ceo = client.get("/api/executive/ceo-dashboard").get_json(silent=True) or {}
            hs = client.get("/api/v1/health-summary").get_json(silent=True) or {}
            roi = client.get("/api/outcome-roi/portfolio-summary").get_json(silent=True) or {}
            pb = client.get("/api/v1/playbook-success-metrics").get_json(silent=True) or {}

            def rev_summary(j):
                return j.get("revenue_summary") or j.get("portfolio_summary") or {}

            cro_rs = rev_summary(cro)
            ceo_ps = ceo.get("portfolio_summary") or {}

            results["metrics"] = {
                "total_arr": {
                    "accounts_sum": sum_rev,
                    "health_summary": hs.get("total_arr"),
                    "ceo": ceo_ps.get("total_arr"),
                    "roi": roi.get("total_arr"),
                    "cro": cro_rs.get("total_arr") or cro.get("portfolio", {}).get("total_arr"),
                },
                "revenue_at_risk": {
                    "context_graph": cg_rev.get("revenue_at_risk"),
                    "ceo": ceo_ps.get("revenue_at_risk"),
                    "roi": roi.get("revenue_at_risk"),
                    "cro": cro_rs.get("revenue_at_risk"),
                },
                "nrr": {
                    "ceo": ceo_ps.get("nrr"),
                    "roi": roi.get("nrr") or roi.get("net_revenue_retention"),
                    "cfo_grr": cfo.get("grr_projection"),
                },
                "cro": {
                    "story_arcs": len(cro.get("story_arcs") or []),
                    "early_warnings": len(cro.get("early_warnings") or []),
                    "accounts": len(cro.get("accounts") or cro.get("account_summaries") or []),
                },
                "cfo": {
                    "automation_rate": cfo.get("automation_rate"),
                    "efficiency_score": cfo.get("efficiency_score"),
                },
                "playbook_ids": list((pb.get("playbooks") or {}).keys())[:8],
                "health_distribution": hs.get("health_distribution"),
            }

            # Checks
            if results["endpoints"]["cro"]["status"] != 200:
                issues.append(f"CRO dashboard HTTP {results['endpoints']['cro']['status']}: {results['endpoints']['cro'].get('error')}")

            arr_vals = [v for v in results["metrics"]["total_arr"].values() if v is not None]
            if len(set(str(round(float(x), 0)) for x in arr_vals if x != "")) > 1:
                issues.append(f"Total ARR mismatch across APIs: {results['metrics']['total_arr']}")

            rar = results["metrics"]["revenue_at_risk"]
            cg_rar = cg_rev.get("revenue_at_risk")
            for name, val in [("ceo", rar.get("ceo")), ("roi", rar.get("roi")), ("cro", rar.get("cro"))]:
                if val is not None and cg_rar and abs(float(val) - float(cg_rar)) > 1:
                    issues.append(f"revenue_at_risk {name}={val} != context_graph {cg_rar}")

            nrr = results["metrics"]["nrr"]
            if nrr.get("ceo") and nrr.get("roi") and abs(float(nrr["ceo"]) - float(nrr["roi"])) > 5:
                issues.append(f"NRR mismatch CEO={nrr['ceo']} vs ROI={nrr['roi']}")

            pbs = results["metrics"]["playbook_ids"]
            if any(p.startswith("PB-DC") for p in pbs):
                issues.append(f"SaaS tenant has DC playbook IDs in metrics: {pbs}")

            if results["metrics"]["cfo"]["automation_rate"] == 0 and results["metrics"]["cfo"]["efficiency_score"] == 0:
                issues.append("CFO automation_rate and efficiency_score both 0")

            for key, ep in results["endpoints"].items():
                if ep["status"] not in (200, 404):
                    if key not in ("revenue_timeline",) or ep["status"] >= 500:
                        issues.append(f"{key} HTTP {ep['status']}")

            results["pass"] = len(issues) == 0

    print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()
