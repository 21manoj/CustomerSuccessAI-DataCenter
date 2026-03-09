#!/usr/bin/env python3
"""
ROI 2-Pager Report Generator
==============================
Generates a structured 2-page executive report showing CS Pulse platform
ROI achievements for a customer over the last 6 months.

Page 1: Executive Summary  — ROI headline, health distribution, revenue impact
Page 2: Account Detail     — Per-account L2 pillar breakdown, KPI highlights

Usage:
    python reports/roi_2pager.py --customer-id 48
    python reports/roi_2pager.py --customer-id 48 --format json
    python reports/roi_2pager.py --customer-id 48 --format text --output report_meridian.txt
    python reports/roi_2pager.py --all   # Generate for all customers

Requires: psycopg2 (connects to cspulse-postgres Docker container)
"""

import argparse
import json
import sys
import os
from datetime import datetime, date
from decimal import Decimal
from collections import defaultdict

# ─── DB Connection ──────────────────────────────────────────────────
def get_db_connection():
    """Connect to PostgreSQL inside Docker via localhost:5432."""
    try:
        import psycopg2
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            dbname="cs_pulse",
            user="cspulse",
            password="cspulse"
        )
        # Quick test
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        return conn
    except Exception:
        # Fallback: use docker exec (DB is inside Docker container)
        return None


def query_via_docker(sql):
    """Execute SQL via docker exec and return parsed rows."""
    import subprocess
    result = subprocess.run(
        ["docker", "exec", "cspulse-postgres", "psql", "-U", "cspulse",
         "-d", "cs_pulse", "-t", "-A", "-F", "|", "-c", sql],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0:
        print(f"DB Error: {result.stderr.strip()}", file=sys.stderr)
        return []
    rows = []
    for line in result.stdout.strip().split("\n"):
        if line.strip():
            rows.append(line.split("|"))
    return rows


def query_db(sql, conn=None):
    """Execute SQL and return rows as list of tuples."""
    if conn:
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        cur.close()
        return rows
    else:
        return [tuple(row) for row in query_via_docker(sql)]


# ─── Data Extraction ────────────────────────────────────────────────

HEALTH_THRESHOLDS = {"healthy_min": 70, "at_risk_min": 50}

def classify(score):
    score = float(score) if score else 0
    if score >= HEALTH_THRESHOLDS["healthy_min"]:
        return "healthy"
    elif score >= HEALTH_THRESHOLDS["at_risk_min"]:
        return "at_risk"
    else:
        return "critical"


def fetch_customer_data(customer_id, conn=None):
    """Fetch all relevant data for the ROI 2-pager."""
    data = {}

    # 1. Customer info
    rows = query_db(f"""
        SELECT customer_id, customer_name, uuid, vertical, created_at
        FROM customers WHERE customer_id = {customer_id}
    """, conn)
    if not rows:
        return None
    data["customer"] = {
        "id": rows[0][0],
        "name": rows[0][1],
        "uuid": rows[0][2],
        "vertical": rows[0][3],
        "created_at": str(rows[0][4]),
    }

    # 2. Accounts
    rows = query_db(f"""
        SELECT account_id, account_name, revenue, account_status, industry, region
        FROM accounts WHERE customer_id = {customer_id}
        ORDER BY account_id
    """, conn)
    accounts = []
    for r in rows:
        accounts.append({
            "id": int(r[0]),
            "name": str(r[1]),
            "revenue": float(r[2]) if r[2] else 0,
            "status": str(r[3]),
            "industry": str(r[4]) if r[4] else "",
            "region": str(r[5]) if r[5] else "",
        })
    data["accounts"] = accounts
    data["total_arr"] = sum(a["revenue"] for a in accounts)
    data["account_count"] = len(accounts)

    # 3. Health scores (latest month per account)
    rows = query_db(f"""
        SELECT hs.account_id, hs.measurement_month, hs.health_score, hs.health_status,
               hs.trend, hs.change_from_last_month
        FROM health_scores hs
        JOIN accounts a ON hs.account_id = a.account_id
        WHERE a.customer_id = {customer_id}
        ORDER BY hs.measurement_month DESC, hs.account_id
    """, conn)
    health_by_account = {}
    months_seen = set()
    for r in rows:
        acct_id = int(r[0])
        month = str(r[1])
        months_seen.add(month)
        if acct_id not in health_by_account:
            health_by_account[acct_id] = []
        health_by_account[acct_id].append({
            "month": month,
            "score": float(r[2]) if r[2] else 0,
            "status": str(r[3]),
            "trend": str(r[4]) if r[4] else "",
            "change": float(r[5]) if r[5] else 0,
        })
    data["health_by_account"] = health_by_account
    data["months_available"] = sorted(months_seen)

    # 4. Pillar scores (latest month per account)
    rows = query_db(f"""
        SELECT ps.account_id, ps.measurement_month, ps.pillar_code, ps.pillar_score, ps.pillar_status
        FROM pillar_scores ps
        JOIN accounts a ON ps.account_id = a.account_id
        WHERE a.customer_id = {customer_id}
        ORDER BY ps.account_id, ps.measurement_month DESC, ps.pillar_code
    """, conn)
    pillars_by_account = defaultdict(list)
    for r in rows:
        pillars_by_account[int(r[0])].append({
            "month": str(r[1]),
            "pillar": str(r[2]),
            "score": float(r[3]) if r[3] else 0,
            "status": str(r[4]),
        })
    data["pillars_by_account"] = dict(pillars_by_account)

    # 5. KPI scores (latest month per account) — top/bottom performers
    rows = query_db(f"""
        SELECT ks.account_id, ks.kpi_code, ks.kpi_value, ks.kpi_target, ks.kpi_score, ks.kpi_status
        FROM kpi_scores ks
        JOIN accounts a ON ks.account_id = a.account_id
        WHERE a.customer_id = {customer_id}
        ORDER BY ks.account_id, ks.kpi_code
    """, conn)
    kpis_by_account = defaultdict(list)
    for r in rows:
        kpis_by_account[int(r[0])].append({
            "kpi_code": str(r[1]),
            "value": float(r[2]) if r[2] else 0,
            "target": float(r[3]) if r[3] else 0,
            "score": float(r[4]) if r[4] else 0,
            "status": str(r[5]),
        })
    data["kpis_by_account"] = dict(kpis_by_account)

    # 6. ROI snapshots
    rows = query_db(f"""
        SELECT snapshot_date, improvement_pct, historical_roi_pct, historical_impact,
               historical_investment, forward_roi_pct, forward_impact, forward_investment,
               combined_roi_pct, total_arr
        FROM roi_snapshots
        WHERE customer_id = {customer_id}
        ORDER BY snapshot_date, improvement_pct
    """, conn)
    roi_snapshots = []
    for r in rows:
        roi_snapshots.append({
            "date": str(r[0]),
            "improvement_pct": float(r[1]) if r[1] else 0,
            "historical_roi": float(r[2]) if r[2] else 0,
            "historical_impact": float(r[3]) if r[3] else 0,
            "historical_investment": float(r[4]) if r[4] else 0,
            "forward_roi": float(r[5]) if r[5] else 0,
            "forward_impact": float(r[6]) if r[6] else 0,
            "forward_investment": float(r[7]) if r[7] else 0,
            "combined_roi": float(r[8]) if r[8] else 0,
            "total_arr": float(r[9]) if r[9] else 0,
        })
    data["roi_snapshots"] = roi_snapshots

    # 7. Playbook executions
    rows = query_db(f"""
        SELECT pe.execution_id, pe.account_id, pe.playbook_id, pe.status,
               pe.started_at, pe.completed_at,
               a.account_name
        FROM playbook_executions pe
        JOIN accounts a ON pe.account_id = a.account_id
        WHERE pe.customer_id = {customer_id}
        ORDER BY pe.started_at DESC
    """, conn)
    playbook_execs = []
    for r in rows:
        playbook_execs.append({
            "execution_id": str(r[0]),
            "account_id": int(r[1]),
            "playbook_id": str(r[2]),
            "status": str(r[3]),
            "started_at": str(r[4]),
            "completed_at": str(r[5]) if r[5] else "",
            "account_name": str(r[6]),
        })
    data["playbook_executions"] = playbook_execs

    # 8. Customer config (enabled pillars/KPIs)
    rows = query_db(f"""
        SELECT config_key, config_value
        FROM customer_configs
        WHERE customer_id = {customer_id}
        AND config_key IN ('dc2s_pillar_weights', 'enabled_kpis', 'enabled_pillars')
    """, conn)
    config = {}
    for r in rows:
        try:
            config[str(r[0])] = json.loads(str(r[1]))
        except (json.JSONDecodeError, TypeError):
            config[str(r[0])] = str(r[1])
    data["config"] = config

    return data


# ─── Report Generation ──────────────────────────────────────────────

PILLAR_NAMES = {
    "AI": "AI & Analytics Intelligence",
    "OS": "Operational Stability",
    "DV": "Deployment Velocity",
    "CH": "Customer Health Engagement",
    "EX": "Experience & Expansion",
}

PLAYBOOK_NAMES = {
    "PB-01": "Deployment Acceleration",
    "PB-02": "RMA Prevention",
    "PB-03": "GPU Optimization",
    "PB-04": "Capacity Planning",
    "PB-05": "Health Monitoring",
    "PB-06": "Customer Engagement",
}


def fmt_dollar(amount):
    """Format dollar amount."""
    if amount >= 1_000_000:
        return f"${amount/1_000_000:,.1f}M"
    elif amount >= 1_000:
        return f"${amount/1_000:,.0f}K"
    else:
        return f"${amount:,.0f}"


def fmt_pct(pct):
    """Format percentage."""
    return f"{pct:+.1f}%" if pct != 0 else "0.0%"


def health_icon(status):
    """Return emoji for health status."""
    return {"healthy": "🟢", "at_risk": "🟡", "critical": "🔴", "warning": "🟡"}.get(status, "⚪")


def generate_text_report(data):
    """Generate the 2-pager text report."""
    lines = []
    w = 80  # width

    customer = data["customer"]
    accounts = data["accounts"]
    total_arr = data["total_arr"]
    health = data["health_by_account"]
    pillars = data["pillars_by_account"]
    kpis = data["kpis_by_account"]
    roi = data["roi_snapshots"]
    playbooks = data["playbook_executions"]

    # ╔══════════════════════════════════════════════════════════════╗
    # ║  PAGE 1: EXECUTIVE SUMMARY                                  ║
    # ╚══════════════════════════════════════════════════════════════╝

    lines.append("=" * w)
    lines.append(f"  CS PULSE — ROI ACHIEVEMENT REPORT")
    lines.append(f"  {customer['name']}")
    lines.append(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("=" * w)
    lines.append("")

    # ── Section 1: Customer Overview ──
    lines.append("┌" + "─" * (w-2) + "┐")
    lines.append(f"│  {'PAGE 1: EXECUTIVE SUMMARY':^{w-4}}  │")
    lines.append("├" + "─" * (w-2) + "┤")
    lines.append(f"│  Customer:     {customer['name']:<{w-19}} │")
    lines.append(f"│  Total ARR:    {fmt_dollar(total_arr):<{w-19}} │")
    lines.append(f"│  Accounts:     {data['account_count']:<{w-19}} │")
    lines.append(f"│  Vertical:     {customer.get('vertical', 'dc2_s'):<{w-19}} │")
    period_str = f"{data['months_available'][0]} → {data['months_available'][-1]}" if data['months_available'] else "N/A"
    lines.append(f"│  Period:       {period_str:<{w-19}} │")
    lines.append("└" + "─" * (w-2) + "┘")
    lines.append("")

    # ── Section 2: Health Distribution ──
    lines.append("─── HEALTH SCORE DISTRIBUTION " + "─" * (w - 31))
    healthy_accts = []
    at_risk_accts = []
    critical_accts = []
    all_scores = []

    for acct in accounts:
        acct_health = health.get(acct["id"], [])
        if acct_health:
            latest = acct_health[0]  # already sorted DESC
            score = latest["score"]
            all_scores.append(score)
            cls = classify(score)
            if cls == "healthy":
                healthy_accts.append(acct)
            elif cls == "at_risk":
                at_risk_accts.append(acct)
            else:
                critical_accts.append(acct)

    avg_score = sum(all_scores) / len(all_scores) if all_scores else 0
    # Revenue-weighted average
    rev_weighted = sum(
        s * a["revenue"] for s, a in zip(all_scores, accounts) if a["revenue"]
    ) / total_arr if total_arr else 0

    n = len(accounts)
    lines.append(f"")
    lines.append(f"  Portfolio Health (L4):  {rev_weighted:.1f}  (revenue-weighted)")
    lines.append(f"  Simple Average (L3):   {avg_score:.1f}")
    lines.append(f"")
    lines.append(f"  🟢 Healthy  (≥70):  {len(healthy_accts):>3} accounts  │  {fmt_dollar(sum(a['revenue'] for a in healthy_accts)):>10} ARR")
    lines.append(f"  🟡 At-Risk  (50-69): {len(at_risk_accts):>3} accounts  │  {fmt_dollar(sum(a['revenue'] for a in at_risk_accts)):>10} ARR")
    lines.append(f"  🔴 Critical (<50):   {len(critical_accts):>3} accounts  │  {fmt_dollar(sum(a['revenue'] for a in critical_accts)):>10} ARR")
    lines.append(f"")

    # Revenue at risk
    rev_at_risk = sum(a["revenue"] for a in at_risk_accts) + sum(a["revenue"] for a in critical_accts)
    lines.append(f"  ⚠️  Revenue at Risk:  {fmt_dollar(rev_at_risk)}  ({rev_at_risk/total_arr*100:.1f}% of portfolio)")
    lines.append(f"  ✅ Revenue Protected: {fmt_dollar(total_arr - rev_at_risk)}  ({(total_arr-rev_at_risk)/total_arr*100:.1f}% of portfolio)")
    lines.append("")

    # ── Section 3: ROI Summary ──
    if roi:
        lines.append("─── ROI ANALYSIS " + "─" * (w - 18))
        lines.append("")

        # Historical ROI (same across all improvement targets)
        hist_roi = roi[0]["historical_roi"]
        hist_impact = roi[0]["historical_impact"]
        hist_invest = roi[0]["historical_investment"]

        lines.append(f"  HISTORICAL ROI (Realized)")
        lines.append(f"  ────────────────────────")
        lines.append(f"  Total Impact:      {fmt_dollar(hist_impact)}")
        lines.append(f"  Total Investment:  {fmt_dollar(hist_invest)}")
        lines.append(f"  ROI:               {hist_roi:.1f}%")
        lines.append(f"  For Every $1 Invested → ${hist_impact/hist_invest:.2f} Returned" if hist_invest > 0 else "")
        lines.append("")

        lines.append(f"  FORWARD ROI (Projected, by Target Improvement)")
        lines.append(f"  ──────────────────────────────────────────────")
        lines.append(f"  {'Target %':>10} {'Investment':>12} {'Impact':>12} {'ROI':>8} {'Combined':>10}")
        lines.append(f"  {'─'*10} {'─'*12} {'─'*12} {'─'*8} {'─'*10}")
        for snap in roi:
            lines.append(
                f"  {snap['improvement_pct']:>9.1f}% "
                f"{fmt_dollar(snap['forward_investment']):>12} "
                f"{fmt_dollar(snap['forward_impact']):>12} "
                f"{snap['forward_roi']:>7.1f}% "
                f"{snap['combined_roi']:>9.1f}%"
            )
        lines.append("")
    else:
        lines.append("─── ROI ANALYSIS " + "─" * (w - 18))
        lines.append("  No ROI snapshots available yet. Enable Revenue Intelligence to generate.")
        lines.append("")

    # ── Section 4: Playbook Activity ──
    if playbooks:
        lines.append("─── PLAYBOOK ACTIVITY " + "─" * (w - 22))
        lines.append("")
        completed = [p for p in playbooks if p["status"] == "completed"]
        running = [p for p in playbooks if p["status"] in ("running", "in_progress")]
        lines.append(f"  Total Executions: {len(playbooks)}  │  Completed: {len(completed)}  │  Running: {len(running)}")
        lines.append("")
        if playbooks[:5]:
            lines.append(f"  {'Playbook':<25} {'Account':<30} {'Status':<12}")
            lines.append(f"  {'─'*25} {'─'*30} {'─'*12}")
            for p in playbooks[:5]:
                pb_name = PLAYBOOK_NAMES.get(p["playbook_id"], p["playbook_id"])
                acct_name = p["account_name"][:28]
                lines.append(f"  {pb_name:<25} {acct_name:<30} {p['status']:<12}")
            if len(playbooks) > 5:
                lines.append(f"  ... and {len(playbooks)-5} more")
        lines.append("")

    lines.append("")
    lines.append("─" * w)
    lines.append(f"{'END OF PAGE 1':^{w}}")
    lines.append("─" * w)
    lines.append("\f")  # Form feed / page break

    # ╔══════════════════════════════════════════════════════════════╗
    # ║  PAGE 2: ACCOUNT DETAIL                                     ║
    # ╚══════════════════════════════════════════════════════════════╝

    lines.append("")
    lines.append("┌" + "─" * (w-2) + "┐")
    lines.append(f"│  {'PAGE 2: ACCOUNT-LEVEL DETAIL (L2 / L3)':^{w-4}}  │")
    lines.append("├" + "─" * (w-2) + "┤")
    lines.append(f"│  {customer['name'] + ' — Per-Account Health & Pillar Breakdown':<{w-4}}  │")
    lines.append("└" + "─" * (w-2) + "┘")
    lines.append("")

    # ── Section 5: Account Health Table ──
    lines.append("─── ACCOUNT HEALTH SCORES (L3) " + "─" * (w - 32))
    lines.append("")

    # Sort by health score ascending (worst first)
    acct_scores = []
    for acct in accounts:
        acct_health = health.get(acct["id"], [])
        score = acct_health[0]["score"] if acct_health else 0
        status = classify(score)
        acct_scores.append((acct, score, status))
    acct_scores.sort(key=lambda x: x[1])

    header = f"  {'#':>2} {'Account Name':<35} {'Revenue':>10} {'Score':>6} {'Status':>9}"
    lines.append(header)
    lines.append(f"  {'─'*2} {'─'*35} {'─'*10} {'─'*6} {'─'*9}")
    for i, (acct, score, status) in enumerate(acct_scores, 1):
        icon = health_icon(status)
        short_name = acct["name"][:33]
        lines.append(
            f"  {i:>2} {short_name:<35} {fmt_dollar(acct['revenue']):>10} {score:>5.1f} {icon} {status:<8}"
        )
    lines.append("")

    # ── Section 6: Pillar Breakdown for Critical/At-Risk Accounts ──
    lines.append("─── PILLAR BREAKDOWN (L2) — At-Risk & Critical Accounts " + "─" * max(0, w - 57))
    lines.append("")

    risk_accounts = [x for x in acct_scores if x[2] in ("at_risk", "critical")]
    if not risk_accounts:
        lines.append("  ✅ All accounts are healthy! No at-risk or critical accounts.")
    else:
        for acct, score, status in risk_accounts[:10]:  # Top 10 worst
            icon = health_icon(status)
            lines.append(f"  {icon} {acct['name']}  (Score: {score:.1f}, ARR: {fmt_dollar(acct['revenue'])})")

            acct_pillars = pillars.get(acct["id"], [])
            if acct_pillars:
                # Get latest month only
                latest_month = acct_pillars[0]["month"]
                month_pillars = [p for p in acct_pillars if p["month"] == latest_month]
                month_pillars.sort(key=lambda p: p["score"])

                for p in month_pillars:
                    p_icon = health_icon(classify(p["score"]))
                    p_name = PILLAR_NAMES.get(p["pillar"], p["pillar"])
                    bar_len = int(p["score"] / 100 * 30)
                    bar = "█" * bar_len + "░" * (30 - bar_len)
                    lines.append(f"     {p['pillar']:>3} {p_name:<30} {p_icon} {p['score']:>5.1f}  {bar}")

            # KPI highlights — worst 3 KPIs
            acct_kpis = kpis.get(acct["id"], [])
            if acct_kpis:
                worst_kpis = sorted(acct_kpis, key=lambda k: k["score"])[:3]
                lines.append(f"     ⚠️  Worst KPIs:")
                for k in worst_kpis:
                    lines.append(f"        {k['kpi_code']:<10} Score: {k['score']:>5.1f}  Value: {k['value']:>8.1f}  Target: {k['target']:>6.1f}")
            lines.append("")

    # ── Section 7: Top-Performing Accounts ──
    lines.append("─── TOP PERFORMERS " + "─" * (w - 20))
    lines.append("")
    healthy_sorted = sorted(
        [x for x in acct_scores if x[2] == "healthy"],
        key=lambda x: x[1], reverse=True
    )
    if healthy_sorted:
        for acct, score, status in healthy_sorted[:5]:
            lines.append(f"  🟢 {acct['name']:<35} Score: {score:.1f}  ARR: {fmt_dollar(acct['revenue'])}")
            acct_kpis_list = kpis.get(acct["id"], [])
            if acct_kpis_list:
                best_kpis = sorted(acct_kpis_list, key=lambda k: k["score"], reverse=True)[:3]
                best_str = ", ".join(f"{k['kpi_code']}={k['score']:.0f}" for k in best_kpis)
                lines.append(f"     Best KPIs: {best_str}")
    else:
        lines.append("  No healthy accounts yet.")
    lines.append("")

    # ── Section 8: KPI Portfolio Analysis ──
    lines.append("─── KPI PORTFOLIO ANALYSIS " + "─" * (w - 28))
    lines.append("")

    all_kpi_scores = defaultdict(list)
    for acct_id, kpi_list in kpis.items():
        for k in kpi_list:
            all_kpi_scores[k["kpi_code"]].append(k["score"])

    if all_kpi_scores:
        kpi_avgs = []
        for code, scores in all_kpi_scores.items():
            avg = sum(scores) / len(scores)
            kpi_avgs.append((code, avg, len(scores)))
        kpi_avgs.sort(key=lambda x: x[1])

        lines.append("  Bottom 5 KPIs (by avg score across all accounts):")
        for code, avg, count in kpi_avgs[:5]:
            bar_len = int(avg / 100 * 25)
            bar = "█" * bar_len + "░" * (25 - bar_len)
            lines.append(f"    {code:<10} Avg: {avg:>5.1f}  {bar}  ({count} accounts)")

        lines.append("")
        lines.append("  Top 5 KPIs (by avg score across all accounts):")
        for code, avg, count in kpi_avgs[-5:]:
            bar_len = int(avg / 100 * 25)
            bar = "█" * bar_len + "░" * (25 - bar_len)
            lines.append(f"    {code:<10} Avg: {avg:>5.1f}  {bar}  ({count} accounts)")

    lines.append("")

    # ── Section 9: Config Summary ──
    config = data.get("config", {})
    if config:
        lines.append("─── CONFIGURATION " + "─" * (w - 19))
        lines.append("")
        enabled_pillars = config.get("enabled_pillars", [])
        pillar_weights = config.get("dc2s_pillar_weights", {})
        enabled_kpis = config.get("enabled_kpis", [])
        if enabled_pillars:
            pillar_str = ", ".join(f"{p} ({PILLAR_NAMES.get(p, p)[:20]})" for p in enabled_pillars)
            lines.append(f"  Enabled Pillars: {pillar_str}")
        if pillar_weights:
            wt_str = ", ".join(f"{k}={v}" for k, v in pillar_weights.items())
            lines.append(f"  Pillar Weights:  {wt_str}")
        if enabled_kpis:
            lines.append(f"  Enabled KPIs:    {len(enabled_kpis)} KPIs across {len(enabled_pillars) if enabled_pillars else '?'} pillars")
        lines.append("")

    # ── Footer ──
    lines.append("─" * w)
    lines.append(f"{'END OF PAGE 2':^{w}}")
    lines.append("─" * w)
    lines.append("")
    lines.append(f"  Report generated by CS Pulse Load Driver")
    lines.append(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"  Customer ID: {customer['id']} | {customer['name']}")

    return "\n".join(lines)


def generate_json_report(data):
    """Generate a structured JSON report for programmatic consumption."""

    customer = data["customer"]
    accounts = data["accounts"]
    total_arr = data["total_arr"]
    health = data["health_by_account"]
    pillars = data["pillars_by_account"]
    kpis = data["kpis_by_account"]
    roi = data["roi_snapshots"]
    playbooks = data["playbook_executions"]

    # Compute health distribution
    healthy_accts, at_risk_accts, critical_accts = [], [], []
    all_scores = []
    for acct in accounts:
        acct_health = health.get(acct["id"], [])
        if acct_health:
            score = acct_health[0]["score"]
            all_scores.append(score)
            cls = classify(score)
            if cls == "healthy": healthy_accts.append(acct)
            elif cls == "at_risk": at_risk_accts.append(acct)
            else: critical_accts.append(acct)

    avg_score = sum(all_scores) / len(all_scores) if all_scores else 0
    rev_weighted = sum(
        s * a["revenue"] for s, a in zip(all_scores, accounts) if a["revenue"]
    ) / total_arr if total_arr else 0

    rev_at_risk = sum(a["revenue"] for a in at_risk_accts) + sum(a["revenue"] for a in critical_accts)

    # Per-account detail
    account_details = []
    for acct in accounts:
        acct_health = health.get(acct["id"], [])
        score = acct_health[0]["score"] if acct_health else 0
        acct_pillars = pillars.get(acct["id"], [])
        acct_kpis = kpis.get(acct["id"], [])

        # Pillar summary
        pillar_summary = {}
        if acct_pillars:
            latest_month = acct_pillars[0]["month"]
            for p in acct_pillars:
                if p["month"] == latest_month:
                    pillar_summary[p["pillar"]] = {
                        "score": p["score"],
                        "status": classify(p["score"]),
                    }

        # KPI summary (worst and best)
        worst_kpis = sorted(acct_kpis, key=lambda k: k["score"])[:3] if acct_kpis else []
        best_kpis = sorted(acct_kpis, key=lambda k: k["score"], reverse=True)[:3] if acct_kpis else []

        account_details.append({
            "account_id": acct["id"],
            "account_name": acct["name"],
            "revenue": acct["revenue"],
            "health_score": score,
            "health_status": classify(score),
            "pillars": pillar_summary,
            "worst_kpis": worst_kpis,
            "best_kpis": best_kpis,
        })

    # Sort by health score ascending
    account_details.sort(key=lambda x: x["health_score"])

    report = {
        "report_type": "roi_2pager",
        "generated_at": datetime.now().isoformat(),
        "customer": customer,
        "summary": {
            "total_arr": total_arr,
            "account_count": len(accounts),
            "portfolio_health_l4": round(rev_weighted, 1),
            "simple_avg_l3": round(avg_score, 1),
            "health_distribution": {
                "healthy": {"count": len(healthy_accts), "arr": sum(a["revenue"] for a in healthy_accts)},
                "at_risk": {"count": len(at_risk_accts), "arr": sum(a["revenue"] for a in at_risk_accts)},
                "critical": {"count": len(critical_accts), "arr": sum(a["revenue"] for a in critical_accts)},
            },
            "revenue_at_risk": rev_at_risk,
            "revenue_at_risk_pct": round(rev_at_risk / total_arr * 100, 1) if total_arr else 0,
        },
        "roi": {
            "snapshots": roi,
            "historical_roi_pct": roi[0]["historical_roi"] if roi else None,
            "historical_impact": roi[0]["historical_impact"] if roi else None,
            "forward_scenarios": [
                {
                    "improvement_pct": s["improvement_pct"],
                    "investment": s["forward_investment"],
                    "impact": s["forward_impact"],
                    "roi_pct": s["forward_roi"],
                }
                for s in roi
            ] if roi else [],
        },
        "playbook_executions": {
            "total": len(playbooks),
            "completed": len([p for p in playbooks if p["status"] == "completed"]),
            "recent": playbooks[:5],
        },
        "accounts": account_details,
        "config": data.get("config", {}),
    }

    return json.dumps(report, indent=2, default=str)


# ─── Main ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="CS Pulse ROI 2-Pager Report Generator")
    parser.add_argument("--customer-id", type=int, help="Customer ID to generate report for")
    parser.add_argument("--all", action="store_true", help="Generate reports for all customers")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    parser.add_argument("--output", type=str, help="Output file path (default: stdout)")
    parser.add_argument("--list", action="store_true", help="List all customers")
    args = parser.parse_args()

    conn = get_db_connection()

    if args.list:
        rows = query_db("""
            SELECT c.customer_id, c.customer_name,
                   (SELECT COUNT(*) FROM accounts WHERE customer_id=c.customer_id) as accts,
                   (SELECT COUNT(*) FROM roi_snapshots WHERE customer_id=c.customer_id) as roi
            FROM customers c ORDER BY c.customer_id
        """, conn)
        print(f"\n{'ID':>4} {'Customer':>30} {'Accounts':>10} {'ROI Snaps':>10}")
        print(f"{'─'*4} {'─'*30} {'─'*10} {'─'*10}")
        for r in rows:
            print(f"{r[0]:>4} {str(r[1]):>30} {r[2]:>10} {r[3]:>10}")
        print()
        return

    if args.all:
        rows = query_db("SELECT customer_id FROM customers ORDER BY customer_id", conn)
        customer_ids = [int(r[0]) for r in rows]
    elif args.customer_id:
        customer_ids = [args.customer_id]
    else:
        parser.error("Specify --customer-id or --all or --list")
        return

    for cid in customer_ids:
        data = fetch_customer_data(cid, conn)
        if not data:
            print(f"⚠️  No data found for customer {cid}", file=sys.stderr)
            continue

        if args.format == "json":
            report = generate_json_report(data)
        else:
            report = generate_text_report(data)

        if args.output:
            if args.all:
                # Per-customer file
                base, ext = os.path.splitext(args.output)
                outfile = f"{base}_cust{cid}{ext}"
            else:
                outfile = args.output
            with open(outfile, "w") as f:
                f.write(report)
            print(f"✅ Report saved: {outfile}")
        else:
            print(report)
            if args.all and cid != customer_ids[-1]:
                print("\n" + "═" * 80 + "\n")

    if conn:
        conn.close()


if __name__ == "__main__":
    main()
