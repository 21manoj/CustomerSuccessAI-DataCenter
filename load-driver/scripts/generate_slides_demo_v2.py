#!/usr/bin/env python3
"""
Generator for slides_demo_saas_v2_deck_aligned.json — 15-account SaaS manifest
aligned to the VP CS / CSM tutorial decks.

Target numbers (from kpi-dashboard/docs/generate_vpcs_tutorial.js):
  - 15 accounts, $48M ARR, 105% NRR
  - Distribution: 7 healthy ($22.4M) / 5 at-risk ($15.8M) / 3 critical ($9.8M)
  - Playbooks: 40 runs (PB-02:12, PB-01:8, PB-04/08:6, PB-SYS-04:4, PB-06:10)
  - Revenue Protected ~$2.1M / Expanded ~$1.4M / ROI 39.3x

Usage:
  python3 scripts/generate_slides_demo_v2.py > manifests/slides_demo_saas_v2_deck_aligned.json
"""

import json
import sys
from datetime import date, timedelta


# ──────────────────────────────────────────────────────────────
# 15-account compact spec. Health uses Nov-start, month index 0-8 maps
# to Jul..Mar (9 months). target_health is the final (Mar) value.
# ──────────────────────────────────────────────────────────────

ACCOUNTS_SPEC = [
    # name, arr, start_h, mid_h, end_h, classification, story_arc, trajectory, recovery_month, renewal
    #
    # Distribution targets (from deck): 7 healthy $22.4M / 5 at-risk $15.8M / 3 critical $9.8M = $48M
    #
    # Approach 4 tuning (Apr 19): shift ARR toward recovery accounts — more
    # dollars through the big-churn-delta zone. Cascade $3.8M→$5M, Relay
    # $3.8M→$4.5M, Vertex $2.8M→$3.5M. Compensated by trimming expansion-zone
    # accounts (Apex $6.1M→$5.3M, Summit $5.4M→$5.0M, etc.) to keep
    # $48M/7-5-3 distribution approximately intact.
    ("Drift Analytics",     1_800_000, 58, 50, 30, "critical", "silent_churn",             "declining",  None, "2026-05-15"),
    ("Cascade Health",      6_500_000, 42, 44, 82, "critical", "crisis_recovery",          "recovering", 2,    "2026-05-30"),
    ("Nimbus Logistics",    1_500_000, 45, 40, 25, "critical", "silent_churn",             "declining",  None, "2026-05-10"),
    ("Relay Healthcare",    5_000_000, 55, 48, 78, "at_risk",  "exec_sponsor_change",      "recovering", 3,    "2026-06-22"),
    ("Canopy EdTech",       4_800_000, 60, 57, 78, "at_risk",  "competitive_displacement", "recovering", 4,    "2026-07-10"),
    ("TechGrid Corp",       1_000_000, 71, 62, 45, "at_risk",  "stalled_deployment",       "declining",  None, "2026-06-30"),
    ("Vertex Media",        3_500_000, 55, 48, 80, "at_risk",  "crisis_recovery",          "recovering", 3,    "2026-06-15"),
    ("Granite Support",     1_500_000, 54, 50, 75, "at_risk",  "silent_churn",             "recovering", 4,    "2026-07-01"),
    # Healthy accts use "recovering" not "improving" — the KPI generator's
    # improving curve caps at 87→92 (5pt delta → $0 expansion revenue). A
    # recovering curve dips first then climbs 55→90 (35pt delta → big expansion).
    # Narrative still holds: "account had a scare early, CSM engaged, now thriving."
    ("Apex Dynamics",       5_300_000, 72, 76, 92, "healthy",  "expansion_champion",       "recovering", 2,    "2026-08-10"),
    ("Summit Data",         5_000_000, 68, 71, 88, "healthy",  "seasonal_surge",           "recovering", 2,    "2026-07-28"),
    ("Meridian FinTech",    3_000_000, 72, 78, 94, "healthy",  "expansion_champion",       "recovering", 2,    "2026-09-01"),
    ("Atlas Marketing",     2_500_000, 73, 74, 88, "healthy",  "land_and_expand",          "recovering", 2,    "2026-08-15"),
    ("Catalyst Logistics",  2_500_000, 72, 76, 90, "healthy",  "expansion_champion",       "recovering", 2,    "2026-09-10"),
    ("Horizon Labs",        2_700_000, 70, 72, 85, "healthy",  "land_and_expand",          "recovering", 2,    "2026-07-20"),
    ("Pinnacle Retail",     1_400_000, 71, 72, 84, "healthy",  "seasonal_surge",           "recovering", 2,    "2026-09-30"),
]


# ──────────────────────────────────────────────────────────────
# Playbook execution templates. Each row is (account_name, [(playbook_id,
# triggered_at_days_from_start, close_offset_days, outcome, triggered_by, note)]).
# Sum of runs must be 40 across the 5 playbook types:
#   PB-02: 12, PB-01: 8, PB-04+PB-08: 6, PB-SYS-04: 4, PB-06: 10.
# Dates measured from base 2025-07-01 (month 0 = Jul).
# Critical-recovery accts get heavy Emergency Retention stack.
# ──────────────────────────────────────────────────────────────

# Base date for day offsets
BASE = date(2025, 7, 1)


def d(month, day=1):
    """Convenience: return (month_index_from_BASE, day_of_month) → ISO date."""
    y = 2025 if month <= 6 else 2026
    m = month if month <= 6 else month - 6
    # Jul 2025 = month 7, Aug 2025 = 8, ..., Dec 2025 = 12, Jan 2026 = 1, etc.
    # We use absolute calendar months:
    return date(y, m, day).isoformat()


def D(year, month, day):
    return date(year, month, day).isoformat()


# account → list of (playbook_id, triggered_at, closed_at, outcome, triggered_by, note)
PLAYBOOK_EXECS = {
    "Drift Analytics": [
        ("PB-02", D(2025, 11,  1), D(2025, 12,  5), "escalated", "signal_analyst",
         "Silent churn intervention: champion unresponsive, escalating."),
        ("PB-02", D(2026,  1, 15), D(2026,  2, 28), "escalated", "health_drop",
         "Emergency retention: exec outreach failed, account deteriorating."),
    ],
    "Relay Healthcare": [
        ("PB-SYS-04", D(2025,  9, 15), D(2025, 10, 15), "resolved", "signal_analyst",
         "Champion recovery: new CMIO identified after original champion departed."),
        ("PB-02",     D(2025, 10, 15), D(2025, 12, 10), "resolved", "signal_analyst",
         "Emergency retention: HIPAA escalation addressed with dedicated security pod."),
        ("PB-SYS-04", D(2026,  1,  5), D(2026,  2,  5), "resolved", "csm",
         "Champion recovery round 2: strengthened exec sponsor relationship."),
        ("PB-06",     D(2026,  2, 10), D(2026,  3, 10), "resolved", "csm",
         "QBR engagement: recovery confirmed, compliance roadmap aligned."),
    ],
    "Canopy EdTech": [
        ("PB-06", D(2025, 10, 20), D(2025, 11, 20), "resolved",  "csm",
         "QBR engagement: early competitive defense, positioning review."),
        ("PB-02", D(2025, 11, 25), D(2026,  1,  5),  "resolved", "signal_analyst",
         "Emergency retention: Canvas evaluation neutralized with feature commitments."),
        ("PB-01", D(2026,  1, 10), D(2026,  2, 10), "resolved",  "signal_analyst",
         "Deployment acceleration: competitive displacement defense, feature catch-up."),
        ("PB-06", D(2026,  2, 15), D(2026,  3, 15), "resolved",  "csm",
         "QBR follow-up: roadmap alignment with VP Academic Technology."),
    ],
    "TechGrid Corp": [
        ("PB-01", D(2025, 11, 10), D(2026,  1, 10), "escalated", "health_drop",
         "Deployment acceleration: stalled integration, engineering SE assigned."),
        ("PB-02", D(2026,  1, 15), D(2026,  2, 20), "resolved",  "signal_analyst",
         "Emergency retention: workflow reactivation program, CSM high-touch."),
        ("PB-06", D(2026,  2, 25), D(2026,  3, 20), "resolved",  "csm",
         "QBR engagement: CTO realignment, adoption plan reset."),
    ],
    "Apex Dynamics": [
        ("PB-08", D(2025, 10,  5), D(2025, 11, 10), "resolved", "csm",
         "Expansion accelerator: identified 3 new departments with CEO approval."),
        ("PB-06", D(2026,  1, 10), D(2026,  2, 10), "resolved", "csm",
         "QBR engagement: expansion pipeline review, contract expansion scheduled."),
        ("PB-04", D(2026,  2, 15), D(2026,  3, 15), "resolved", "signal_analyst",
         "Capacity planning: forecast growth, provision upgrade signed."),
    ],
    "Horizon Labs": [
        ("PB-01", D(2025, 10,  1), D(2025, 11,  5), "resolved", "csm",
         "Deployment acceleration: stakeholder mapping + onboarding push."),
        ("PB-06", D(2026,  1, 20), D(2026,  2, 20), "resolved", "csm",
         "QBR engagement: goals alignment, expansion conversation opened."),
    ],
    "Summit Data": [
        ("PB-04", D(2025, 11,  1), D(2025, 12,  1), "resolved", "csm",
         "Capacity planning: seasonal surge forecasting, infra headroom added."),
        ("PB-06", D(2026,  1, 15), D(2026,  2, 15), "resolved", "csm",
         "QBR engagement: usage review, upsell pipeline qualified."),
        ("PB-08", D(2026,  2, 20), D(2026,  3, 20), "resolved", "signal_analyst",
         "Expansion accelerator: multi-region add-on signed."),
    ],
    "Meridian FinTech": [
        ("PB-08", D(2025, 10, 15), D(2025, 11, 15), "resolved", "csm",
         "Expansion accelerator: enterprise tier upgrade, 2 new product lines."),
        ("PB-06", D(2026,  1, 10), D(2026,  2,  5), "resolved", "csm",
         "QBR engagement: executive alignment, strategic roadmap."),
        ("PB-04", D(2026,  2, 15), D(2026,  3, 15), "resolved", "signal_analyst",
         "Capacity planning: growth forecast 3x, tier upgrade to enterprise."),
    ],
    "Atlas Marketing": [
        ("PB-01", D(2025, 10, 10), D(2025, 11, 10), "resolved", "csm",
         "Deployment acceleration: marketing stack integrations, onboarding boost."),
        ("PB-06", D(2026,  1, 25), D(2026,  2, 25), "resolved", "csm",
         "QBR engagement: expansion opportunity mapping."),
    ],
    "Catalyst Logistics": [
        ("PB-06", D(2025, 11,  5), D(2025, 12,  5), "resolved", "csm",
         "QBR engagement: supply chain optimization workshop."),
        ("PB-04", D(2026,  1, 10), D(2026,  2, 10), "resolved", "csm",
         "Capacity planning: fleet expansion provisioning."),
        ("PB-08", D(2026,  2, 20), D(2026,  3, 20), "resolved", "signal_analyst",
         "Expansion accelerator: multi-warehouse add-on deal signed."),
    ],
    "Pinnacle Retail": [
        ("PB-06", D(2025, 10, 15), D(2025, 11, 15), "resolved", "csm",
         "QBR engagement: peak season readiness review."),
        ("PB-06", D(2026,  2,  1), D(2026,  3,  1), "resolved", "csm",
         "QBR engagement: post-peak retro + expansion roadmap."),
    ],
    "Vertex Media": [
        ("PB-02",     D(2025,  9, 20), D(2025, 10, 30), "resolved", "signal_analyst",
         "Emergency retention: DAU freefall after platform bug, dedicated pod assigned."),
        ("PB-SYS-04", D(2025, 11,  5), D(2025, 12, 10), "resolved", "signal_analyst",
         "Champion recovery: new VP Marketing re-engaged, content strategy reset."),
        ("PB-02",     D(2026,  1, 10), D(2026,  2, 15), "resolved", "csm",
         "Emergency retention follow-up: stabilization confirmed."),
        ("PB-06",     D(2026,  2, 20), D(2026,  3, 20), "resolved", "csm",
         "QBR engagement: recovery milestones signed off, renewal committed."),
    ],
    "Granite Support": [
        ("PB-02", D(2025, 12,  1), D(2026,  1, 15), "resolved", "signal_analyst",
         "Emergency retention: ticket backlog cleared, SLA recovered."),
        ("PB-06", D(2026,  2, 15), D(2026,  3, 15), "resolved", "csm",
         "QBR engagement: support maturity plan, renewal secured."),
    ],
    "Cascade Health": [
        ("PB-02",     D(2025,  9, 10), D(2025, 10, 20), "resolved", "signal_analyst",
         "Emergency retention: HIPAA concerns, immediate compliance sprint."),
        ("PB-SYS-04", D(2025, 11, 15), D(2025, 12, 20), "resolved", "signal_analyst",
         "Champion recovery: Chief Medical Officer re-engaged after exec change."),
        ("PB-02",     D(2026,  1,  5), D(2026,  2, 10), "resolved", "csm",
         "Emergency retention continuation: infrastructure hardening."),
        ("PB-01",     D(2026,  2, 15), D(2026,  3, 15), "resolved", "csm",
         "Deployment acceleration: module re-onboarding post-recovery."),
        ("PB-06",     D(2026,  3,  1), D(2026,  3, 28), "resolved", "csm",
         "QBR engagement: recovery milestone review, renewal commitment."),
    ],
    "Nimbus Logistics": [
        ("PB-02", D(2025, 11, 15), D(2025, 12, 20), "escalated", "signal_analyst",
         "Emergency retention attempted; champion unresponsive, decline continues."),
        ("PB-02", D(2026,  1, 20), D(2026,  2, 25), "escalated", "health_drop",
         "Emergency retention round 2: terminal declining, pre-churn."),
    ],
}


# ──────────────────────────────────────────────────────────────
# Product mix by ARR (3 products per account, proportional split).
# ──────────────────────────────────────────────────────────────

def products_for(arr):
    # Core 60%, secondary 25%, tertiary 15%
    return [
        {"name": "Core Platform",   "category": "core",        "arr": round(arr * 0.60, -4)},
        {"name": "Analytics Suite", "category": "analytics",   "arr": round(arr * 0.25, -4)},
        {"name": "API Platform",    "category": "integration", "arr": arr - round(arr * 0.60, -4) - round(arr * 0.25, -4)},
    ]


# ──────────────────────────────────────────────────────────────
# Stakeholder + signal templates keyed by story arc (short, illustrative).
# ──────────────────────────────────────────────────────────────

ARC_TEMPLATES = {
    "silent_churn": {
        "stakeholders": [
            ("Amanda Foster",         "champion",           "VP Operations",         "Operations", 6, "disengaged", "none"),
            ("Priya Natarajan",       "technical_lead",     "IT Director",           "IT",         5, "neutral",    "quarterly"),
            ("Morgan Lee",            "csm",                "Customer Success Manager", "CS",       7, "concerned",  "weekly"),
        ],
        "signals": [
            ("engagement_drop",   "VP Operations Amanda Foster stopped responding to emails for 45+ days.",     "very_negative"),
            ("usage_decline",     "Weekly active users dropped 40%; core features unused per Priya's team.",    "negative"),
        ],
    },
    "exec_sponsor_change": {
        "stakeholders": [
            ("Dr. Vanessa Chen",   "former_sponsor",     "VP Clinical Ops",           "Clinical",    9, "departed",  "none"),
            ("Dr. Aisha Patel",    "executive_sponsor",  "Chief Medical Informatics Officer", "Clinical Informatics", 9, "concerned", "monthly"),
            ("Robert Kim",         "technical_lead",     "Security Architect",        "IT Security", 8, "negative",  "weekly"),
            ("Morgan Lee",         "csm",                "Customer Success Manager",  "CS",          7, "engaged",   "weekly"),
        ],
        "signals": [
            ("escalation",        "CMIO Dr. Aisha Patel escalated SSO failures to our CEO; HIPAA compliance concerns.", "very_negative"),
            ("csm_intervention",  "Dedicated security support pod deployed; weekly reviews initiated by Morgan Lee.","positive"),
        ],
    },
    "competitive_displacement": {
        "stakeholders": [
            ("Patricia Moore",    "champion",           "VP Academic Technology",    "Academic",   8, "neutral",   "quarterly"),
            ("Daniel Choi",       "influencer",         "Director Procurement",      "Finance",    6, "negative",  "monthly"),
            ("Morgan Lee",        "csm",                "Customer Success Manager",  "CS",         7, "engaged",   "weekly"),
        ],
        "signals": [
            ("competitive_eval",  "Canvas evaluation detected in procurement review.",               "very_negative"),
            ("qbr_positive",      "Post-QBR feedback positive; roadmap alignment improved.",         "positive"),
        ],
    },
    "stalled_deployment": {
        "stakeholders": [
            ("Jason Wells",       "technical_lead",     "VP Engineering",            "Engineering", 8, "concerned", "weekly"),
            ("Elena Martinez",    "executive_sponsor",  "CTO",                       "Engineering", 9, "neutral",   "monthly"),
            ("Sam Rivera",        "csm",                "Senior CSM",                "CS",          7, "focused",   "weekly"),
        ],
        "signals": [
            ("integration_stall", "API integration blocked on platform gap; launch slipped 6 wks.",  "negative"),
            ("deployment_reset",  "Dedicated SE assigned; workflow reactivation program launched.",  "positive"),
        ],
    },
    "expansion_champion": {
        "stakeholders": [
            ("Marcus Hall",       "champion",           "CEO",                       "Executive",  10, "enthusiastic", "weekly"),
            ("Linda Park",        "product_lead",       "Chief Product Officer",     "Product",     9, "positive",     "bi-weekly"),
            ("Sarah Chen",        "csm",                "Senior CSM",                "CS",          7, "engaged",      "weekly"),
        ],
        "signals": [
            ("expansion_signal",  "CEO approved 3 new departments onto the platform.",               "very_positive"),
            ("usage_spike",       "DAU up 35% Q/Q; power-user cohort tripled.",                      "positive"),
        ],
    },
    "land_and_expand": {
        "stakeholders": [
            ("Michael Reyes",     "champion",           "VP Operations",             "Operations", 8, "positive",  "monthly"),
            ("Lisa Tanaka",       "influencer",         "Director Data",             "Data",       6, "neutral",   "quarterly"),
            ("Alex Johnson",      "csm",                "Senior CSM",                "CS",          7, "engaged",   "weekly"),
        ],
        "signals": [
            ("adoption_growth",   "Feature adoption up 20% after stakeholder mapping refresh.",      "positive"),
            ("qbr_alignment",     "QBR confirmed expansion intent for next contract cycle.",         "positive"),
        ],
    },
    "seasonal_surge": {
        "stakeholders": [
            ("Rachel Greene",     "champion",           "VP Customer Success",       "Operations", 8, "positive",  "monthly"),
            ("Thomas Wright",     "executive_sponsor",  "CFO",                       "Finance",    9, "positive",  "quarterly"),
            ("Marcus Rivera",     "csm",                "Customer Success Manager",  "CS",          7, "engaged",   "weekly"),
        ],
        "signals": [
            ("seasonal_peak",     "Peak-season traffic served with 99.9% uptime.",                   "positive"),
            ("capacity_add",      "Infrastructure capacity upgrade signed for next peak.",           "positive"),
        ],
    },
    "crisis_recovery": {
        "stakeholders": [
            ("Raj Patel",         "champion",           "VP Engineering",            "Engineering", 9, "engaged",   "weekly"),
            ("Catherine Winters", "executive_sponsor",  "CTO",                       "Engineering", 10, "cautious", "monthly"),
            ("Sam Rivera",        "csm",                "Senior CSM",                "CS",          7, "focused",   "weekly"),
        ],
        "signals": [
            ("crisis_event",      "Platform outage triggered CTO Catherine Winters escalation; 48h incident.", "very_negative"),
            ("recovery_milestone","Post-incident review completed with Raj Patel; trust metrics recovering.",  "positive"),
        ],
    },
}


def _stakeholders(arc):
    tpl = ARC_TEMPLATES.get(arc, ARC_TEMPLATES["land_and_expand"])
    return [
        {"name": n, "role": r, "title": t, "department": d,
         "influence_score": i, "sentiment": s, "engagement_frequency": f}
        for (n, r, t, d, i, s, f) in tpl["stakeholders"]
    ]


def _signals(arc, name):
    tpl = ARC_TEMPLATES.get(arc, ARC_TEMPLATES["land_and_expand"])
    # Space signals across timeline
    anchor_dates = ["2025-10-15", "2026-01-15", "2026-03-01"]
    sigs = tpl["signals"]
    out = []
    for i, (t, c, s) in enumerate(sigs):
        out.append({
            "type": t,
            "date": anchor_dates[i % len(anchor_dates)],
            "content": c,
            "sentiment": s,
        })
    return out


def _playbook_execs(name):
    rows = PLAYBOOK_EXECS.get(name, [])
    return [
        {"playbook_id": pid, "triggered_at": ta, "closed_at": ca,
         "outcome": out, "triggered_by": tb, "notes": note}
        for (pid, ta, ca, out, tb, note) in rows
    ]


def _narrative(name, start_h, end_h, arc, trajectory):
    if trajectory == "declining":
        return f"{name}: health drops from {start_h}→{end_h} via {arc.replace('_', ' ')}; no recovery intervention succeeds."
    if trajectory == "improving":
        return f"{name}: strong growth trajectory {start_h}→{end_h}, {arc.replace('_', ' ')} pattern."
    return f"{name}: {arc.replace('_', ' ')} — health dips then recovers from {start_h} low to {end_h} by March."


def build_account(spec):
    (name, arr, start_h, mid_h, end_h, classification, arc, trajectory, recovery_m, renewal) = spec
    acct = {
        "name": name,
        "arr": arr,
        "target_health": end_h,
        "classification": classification,
        "story_arc": arc,
        "partner_tier": "tier_1" if arr >= 3_000_000 else "direct",
        "renewal_date": renewal,
        "narrative": _narrative(name, start_h, end_h, arc, trajectory),
        "kpi_trajectory": trajectory,
        "products": products_for(arr),
        "stakeholders": _stakeholders(arc),
        "key_signals": _signals(arc, name),
        "playbook_executions": _playbook_execs(name),
    }
    if recovery_m is not None:
        acct["recovery_start_month"] = recovery_m
    return acct


def build_manifest():
    accounts = [build_account(s) for s in ACCOUNTS_SPEC]
    total_arr = sum(a["arr"] for a in accounts)

    return {
        "manifest_version": "2.0",
        "customer": {
            "name": "Slide Deck SaaS Demo v2",
            "domain": "phoenix-saas-v2.com",
            "vertical": "saas_premium",
            "admin_email": "admin@slidedeck-demo-v2.com",
            "admin_name": "Phoenix Admin v2",
            "total_arr": total_arr,
            "description": (
                "15-account SaaS portfolio aligned to VP CS + CSM tutorial decks "
                "(kpi-dashboard/docs/*Tutorial.pptx). 7 healthy / 5 at-risk / 3 critical, "
                "$48M ARR, 44 playbook runs. Validated on EC2 customer 382 (Apr 19 2026): "
                "$1.71M protected + $1.35M expanded = $3.07M total return (88% of "
                "deck target $3.5M), ROI 11.4x. Regenerate via: "
                "python3 scripts/generate_slides_demo_v2.py > "
                "manifests/slides_demo_saas_v2_deck_aligned.json"
            ),
        },
        "time_range": {
            "start": "2025-07-01",
            "end": "2026-03-31",
            "frequency": "weekly",
            "data_points_per_kpi": 39,
        },
        "kpis": {
            "selection": "starter_9",
            "count": 9,
            "codes": [
                "P1-KPI1", "P1-KPI2", "P1-KPI4",
                "P2-KPI1", "P2-KPI3",
                "P3-KPI1", "P3-KPI3",
                "P5-KPI1", "P5-KPI5",
            ],
        },
        "context_graph": {
            "stakeholders_per_account": 2,
            "events_per_account": 3,
            "include_decisions": True,
            "include_outcomes": True,
            "include_signal_edges": True,
            "include_benchmarks": True,
        },
        "lifecycle_events": {
            # Events that shape KPI generation (not playbook firings)
            "Drift Analytics":  {"event": "churn",  "event_month": 8, "delta_pct": -100},
            "Nimbus Logistics": {"event": "churn",  "event_month": 9, "delta_pct": -100},
            "Meridian FinTech": {"event": "expand", "event_month": 6, "delta_pct": 25},
            "Apex Dynamics":    {"event": "expand", "event_month": 7, "delta_pct": 20},
            "Catalyst Logistics": {"event": "expand", "event_month": 7, "delta_pct": 15},
            "Summit Data":      {"event": "expand", "event_month": 7, "delta_pct": 15},
        },
        "accounts": accounts,
    }


def _totals(manifest):
    total_arr = sum(a["arr"] for a in manifest["accounts"])
    by_cls = {}
    for a in manifest["accounts"]:
        k = a["classification"]
        by_cls[k] = by_cls.get(k, {"count": 0, "arr": 0})
        by_cls[k]["count"] += 1
        by_cls[k]["arr"] += a["arr"]
    pb_runs = {}
    for a in manifest["accounts"]:
        for pb in a.get("playbook_executions", []):
            k = pb["playbook_id"]
            pb_runs[k] = pb_runs.get(k, 0) + 1
    return total_arr, by_cls, pb_runs


if __name__ == "__main__":
    m = build_manifest()
    total_arr, by_cls, pb_runs = _totals(m)
    sys.stderr.write(f"# accounts: {len(m['accounts'])}\n")
    sys.stderr.write(f"# total ARR: ${total_arr:,}\n")
    for k, v in sorted(by_cls.items()):
        sys.stderr.write(f"# {k}: {v['count']} accts, ${v['arr']:,}\n")
    sys.stderr.write(f"# playbook runs: {sum(pb_runs.values())} total — {pb_runs}\n")
    json.dump(m, sys.stdout, indent=2)
