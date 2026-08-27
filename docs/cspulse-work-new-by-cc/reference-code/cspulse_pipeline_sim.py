#!/usr/bin/env python3
"""
cspulse_pipeline_sim.py
=======================

A runnable teaching model of the CS Pulse `process_data()` pipeline.

Purpose
-------
Show engineers, in real database rows, how a context graph comes into existence:

    CSV load -> health scoring -> Wizard A -> Wizard B -> Wizard C -> Wizard D
             -> hot (incremental) load

...and specifically how *edges* materialise from Wizard A when no causal data
was ever uploaded.

Two modes
---------
    --mode current   Models the pipeline as it behaves today.
    --mode fixed     Models the target design: evidence_tier at write time,
                     NULL confidence for inferred edges, supersession on
                     incremental load.
    --mode compare   Runs both against separate DBs and diffs the metrics.

Everything is stdlib. No dependencies. Deterministic — no randomness, fixed
dates — so two runs produce byte-identical output.

    python3 cspulse_pipeline_sim.py --mode current
    python3 cspulse_pipeline_sim.py --mode fixed
    python3 cspulse_pipeline_sim.py --mode compare
    sqlite3 cspulse_demo_current.db 'select * from context_edges;'
"""

import argparse
import csv
import json
import os
import sqlite3
import statistics
import sys
from datetime import datetime, timedelta

# ─────────────────────────────────────────────────────────────────────────────
# Terminal rendering
# ─────────────────────────────────────────────────────────────────────────────

USE_COLOR = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def _c(code, s):
    return f"\033[{code}m{s}\033[0m" if USE_COLOR else s


BOLD = lambda s: _c("1", s)          # noqa: E731
DIM = lambda s: _c("2", s)           # noqa: E731
RED = lambda s: _c("31", s)          # noqa: E731
GRN = lambda s: _c("32", s)          # noqa: E731
YEL = lambda s: _c("33", s)          # noqa: E731
BLU = lambda s: _c("34", s)          # noqa: E731
CYN = lambda s: _c("36", s)          # noqa: E731

WIDTH = 100


def stage(n, title, subtitle=""):
    print()
    print(BOLD(CYN("━" * WIDTH)))
    print(BOLD(CYN(f"  STAGE {n} · {title}")))
    if subtitle:
        print(DIM(f"  {subtitle}"))
    print(BOLD(CYN("━" * WIDTH)))


def section(title):
    print()
    print(BOLD(f"  {title}"))
    print(DIM("  " + "─" * (WIDTH - 4)))


def note(s):
    print(DIM(f"  · {s}"))


def flag(s):
    print(RED(f"  ⚠  {s}"))


def good(s):
    print(GRN(f"  ✓  {s}"))


def table(headers, rows, widths=None, indent=2):
    """Minimal fixed-width table renderer."""
    if not rows:
        print(" " * indent + DIM("(no rows)"))
        return
    cols = len(headers)
    if widths is None:
        widths = []
        for i in range(cols):
            w = max(len(str(headers[i])), *(len(str(r[i])) for r in rows))
            widths.append(min(w, 46))
    pad = " " * indent

    def fmt(vals, styler=None):
        cells = []
        for i in range(cols):
            v = str(vals[i])
            if len(v) > widths[i]:
                v = v[: widths[i] - 1] + "…"
            cells.append(v.ljust(widths[i]))
        line = "  ".join(cells)
        return styler(line) if styler else line

    print(pad + fmt(headers, BOLD))
    print(pad + DIM("  ".join("─" * w for w in widths)))
    for r in rows:
        print(pad + fmt(r))


def rowcount_delta(conn, label, before):
    """Print per-table row counts and the delta since `before`."""
    after = table_counts(conn)
    rows = []
    for t in TABLES:
        b, a = before.get(t, 0), after.get(t, 0)
        d = a - b
        marker = GRN(f"+{d}") if d > 0 else DIM("—")
        rows.append([t, b, a, marker])
    section(label)
    table(["table", "before", "after", "Δ"], rows)
    return after


TABLES = [
    "accounts",
    "kpi_measurements",
    "qualitative_signals",
    "outcomes",
    "context_nodes",
    "context_edges",
    "customer_config",
    "calibration_history",
]


def table_counts(conn):
    return {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in TABLES}


# ─────────────────────────────────────────────────────────────────────────────
# Domain constants
# ─────────────────────────────────────────────────────────────────────────────

CUSTOMER_ID = 390
T0 = datetime(2025, 12, 1)

PILLARS = {
    "P1": "Revenue & Unit Economics",
    "P2": "Fleet Utilization & Goodput",
    "P3": "Reliability & SLA Delivery",
}

# Bootstrap (pre-Wizard-C) pillar weights. Wizard C will overwrite these.
BOOTSTRAP_WEIGHTS = {"P1": 0.34, "P2": 0.33, "P3": 0.33}

KPI_CATALOG = [
    ("gpu_util_pct", "P2"),
    ("goodput_ratio", "P2"),
    ("sla_breach_ct", "P3"),
    ("mttr_hours", "P3"),
    ("gross_margin_pct", "P1"),
    ("expansion_pipeline", "P1"),
]

# ── Wizard A: the static arc templates ───────────────────────────────────────
# NOTE FOR ENGINEERS: read the `from`/`to` fields carefully. They bind by
# POSITION ("the 2nd signal on this account"), not by meaning. That is why a
# template authored for champion_loss can land its "Champion departure…" label
# on a signal about GPU utilisation. The label travels with the template slot,
# not with the node it ends up describing.
ARC_TEMPLATES = {
    "champion_loss": {
        "phases": ["baseline", "deterioration", "crisis"],
        "edges": [
            dict(phase="baseline", frm="signal:0", to="signal:1", type="LED_TO",
                 confidence=0.65, lag_days=21,
                 label="Routine engagement before departure"),
            dict(phase="deterioration", frm="signal:1", to="signal:2", type="LED_TO",
                 confidence=0.85, lag_days=30,
                 label="Champion departure created engagement gap"),
            dict(phase="deterioration", frm="signal:2", to="outcome:0", type="CAUSED_BY",
                 confidence=0.80, lag_days=30,
                 label="Engagement gap led to usage decline"),
        ],
    },
    "infrastructure_decay": {
        "phases": ["baseline", "deterioration"],
        "edges": [
            dict(phase="baseline", frm="signal:0", to="signal:1", type="LED_TO",
                 confidence=0.70, lag_days=14,
                 label="Early reliability warning preceded degradation"),
            dict(phase="deterioration", frm="signal:1", to="outcome:0", type="CAUSED_BY",
                 confidence=0.75, lag_days=45,
                 label="Sustained degradation drove capacity risk"),
        ],
    },
    "land_and_expand": {
        "phases": ["baseline", "growth"],
        "edges": [
            dict(phase="growth", frm="signal:0", to="outcome:0", type="LED_TO",
                 confidence=0.72, lag_days=60,
                 label="Successful adoption unlocked expansion"),
        ],
    },
}

# Trajectory-shape classifier bases (the third, independent classifier).
TRAJECTORY_BASE = {"crisis": 0.65, "decline": 0.60, "flat": 0.55, "recovery": 0.70}


# ─────────────────────────────────────────────────────────────────────────────
# Seed data — the "4 CSVs" of Month 1
# ─────────────────────────────────────────────────────────────────────────────
# accounts.csv, kpi_measurements.csv, enhanced_qualitative_signals.csv, outcomes.csv
# Note what is NOT here: signal_edges.csv. Causal structure is never uploaded at
# cold start. That absence is the entire reason Wizard A exists.

SEED_ACCOUNTS = [
    # (id, name, arr, renewal_offset_days, health_trajectory, pillar_offsets)
    # pillar_offsets let each pillar move independently of overall health, so
    # Wizard C has real signal to discover instead of three identical columns.
    # P3 (reliability) is the pillar that actually tracks outcome here; P1 is
    # deliberately noisy. Wizard C should find that on its own.
    (3535, "Titan Hyperscale Labs", 8_200_000, 210, [72, 61, 48, 33, 15], {"P1": +18, "P2": -4, "P3": -12}),
    (3536, "Meridian AI",           4_100_000, 150, [70, 66, 60, 54, 49], {"P1": -14, "P2": +2, "P3": -6}),
    (3537, "Quantum Labs",          2_300_000, 300, [64, 62, 59, 57, 56], {"P1": -9,  "P2": -3, "P3": +14}),
    (3538, "Apex Compute",          3_000_000, 400, [71, 76, 81, 85, 89], {"P1": -11, "P2": +3, "P3": +8}),
    (3540, "Pacific Dataworks",    12_500_000, 365, [78, 81, 83, 85, 87], {"P1": +12, "P2": -2, "P3": +9}),
    (3541, "Orion Models",          3_600_000,  90, [58, 49, 38, 27, 20], {"P1": +16, "P2": +1, "P3": -15}),
]

# signal_date offsets from T0, per account. Deliberately irregular so Wizard B
# has something real to measure against the templates' hardcoded lags.
SEED_SIGNALS = {
    3535: [
        (0,   "critical_incident",     "Critical service incident reported", "negative"),
        (7,   "support_escalation",    "Support ticket escalated to management", "negative"),
        (54,  "reserved_cluster_idle", "Reserved 1,000-GPU cluster utilization fell 65%->22%", "negative"),
        (120, "churn_averted",         "Retention plan approved, 12-month commitment", "positive"),
    ],
    3536: [
        (3,   "usage_decline",         "Sustained drop in batch job submissions", "negative"),
        (49,  "budget_pressure",       "Procurement signalled FY27 budget freeze", "negative"),
        (95,  "engagement_gap",        "No QBR held in two consecutive quarters", "negative"),
    ],
    3537: [
        (10,  "sla_breach",            "Two SLA breaches in rolling 30 days", "negative"),
        (58,  "mttr_regression",       "Mean time to repair up 40% quarter over quarter", "negative"),
        (140, "capacity_constraint",   "Requested capacity unavailable in region", "negative"),
    ],
    3538: [
        (14,  "adoption_milestone",    "Cleared 80% platform adoption threshold", "positive"),
        (70,  "expansion_interest",    "Asked for pricing on second region", "positive"),
    ],
    3540: [
        (20,  "adoption_milestone",    "Standardised on platform across three BUs", "positive"),
        (88,  "exec_sponsorship",      "CTO joined quarterly steering committee", "positive"),
    ],
    3541: [
        (2,   "champion_change",       "Primary champion left the company", "negative"),
        (46,  "engagement_gap",        "Weekly sync cancelled four times running", "negative"),
        (101, "competitor_mention",    "Evaluating an alternative provider", "negative"),
    ],
}

SEED_OUTCOMES = {
    3535: [(150, "Revenue at Risk", "revenue_at_risk", -4_100_000)],
    3536: [(160, "Downgrade Booked", "contraction", -820_000)],
    3537: [(170, "Renewal Secured", "renewal", 2_300_000)],
    3538: [(180, "Expansion Closed", "expansion", 900_000)],
    3540: [(190, "Renewal Secured", "renewal", 12_500_000)],
    3541: [(120, "Churn Confirmed", "churn", -3_600_000)],
}

# Firmographics — required columns on accounts.csv in the real schema.
ACCOUNT_META = {
    3535: ("AI Infrastructure", "US-West"),
    3536: ("AI Infrastructure", "US-East"),
    3537: ("Research Computing", "EU-Central"),
    3538: ("Financial Services", "US-East"),
    3540: ("Media & Entertainment", "APAC"),
    3541: ("AI Infrastructure", "US-West"),
}

# Hot-data payload — arrives in Month 2 once the CRM integration lands.
# Real causal edges, referenced by signal_ref exactly as signal_edges.csv does.
# Note that two of them describe node pairs Wizard A already invented an edge for.
HOT_SIGNAL_EDGES = [
    dict(frm="sig_3535_0", to="sig_3535_1", type="LED_TO", weight=1.0,
         evidence="ticket #INC-4471 escalation log", lag_days=7,
         label="Incident severity triggered management escalation"),
    dict(frm="sig_3535_1", to="sig_3535_2", type="LED_TO", weight=1.0,
         evidence="capacity planning review 2026-01-24", lag_days=47,
         label="Unresolved escalation preceded workload migration off reserved cluster"),
    dict(frm="sig_3541_0", to="sig_3541_1", type="LED_TO", weight=1.0,
         evidence="calendar export: 4 cancelled syncs", lag_days=44,
         label="Champion departure left sync cadence unowned"),
]


# ─────────────────────────────────────────────────────────────────────────────
# CSV emission — the sim's inputs are real files, not Python literals
# ─────────────────────────────────────────────────────────────────────────────
# Column sets match the platform's own get_csv_templates() schema for the
# datacenter vertical, so these files are shaped like the ones a customer
# actually uploads. Edit them and re-run to try your own scenario.

def emit_csvs(outdir):
    os.makedirs(outdir, exist_ok=True)
    written = []

    def w(name, header, rows):
        path = os.path.join(outdir, name)
        with open(path, "w", newline="") as f:
            wr = csv.writer(f)
            wr.writerow(header)
            wr.writerows(rows)
        written.append((name, len(rows)))

    # 1. accounts.csv
    rows = []
    for aid, name, arr, renew_off, _traj, _off in SEED_ACCOUNTS:
        ind, reg = ACCOUNT_META[aid]
        rows.append([aid, CUSTOMER_ID, name, ind, reg, arr,
                     (T0 + timedelta(days=renew_off)).date().isoformat()])
    w("accounts.csv",
      ["source_account_id", "customer_id", "account_name", "industry", "region",
       "arr", "renewal_date"], rows)

    # 2. kpi_measurements.csv
    rows = []
    for aid, _n, _arr, _r, traj, offsets in SEED_ACCOUNTS:
        for month, h in enumerate(traj):
            for k, (kpi_code, pillar) in enumerate(KPI_CATALOG):
                v = h + offsets[pillar] + (2.0 if k % 2 else -2.0)
                rows.append([aid, kpi_code, pillar,
                             (T0 + timedelta(days=30 * month)).date().isoformat(),
                             round(max(0.0, min(100.0, v)), 2)])
    w("kpi_measurements.csv",
      ["source_account_id", "kpi_code", "pillar", "measured_at", "value"], rows)

    # 3. enhanced_qualitative_signals.csv
    rows = []
    for aid, sigs in SEED_SIGNALS.items():
        for i, (day_off, stype, content, sentiment) in enumerate(sigs):
            rows.append([aid, f"sig_{aid}_{i}",
                         (T0 + timedelta(days=day_off)).date().isoformat(),
                         stype, content, sentiment])
    w("enhanced_qualitative_signals.csv",
      ["source_account_id", "signal_ref", "signal_date", "signal_type",
       "content", "sentiment"], rows)

    # 4. outcomes.csv
    rows = []
    for aid, outs in SEED_OUTCOMES.items():
        for day_off, title, otype, rev in outs:
            rows.append([aid, (T0 + timedelta(days=day_off)).date().isoformat(),
                         title, otype, rev])
    w("outcomes.csv",
      ["source_account_id", "outcome_date", "title", "outcome_type", "revenue_value"], rows)

    # 5. signal_edges.csv — MONTH 2+. Not part of cold start.
    rows = [[e["frm"], e["to"], e["type"], e["weight"], e["lag_days"],
             e["evidence"], e["label"], "csv_import"] for e in HOT_SIGNAL_EDGES]
    w("signal_edges.csv",
      ["from_signal_ref", "to_signal_ref", "edge_type", "weight", "lag_days",
       "evidence", "label", "source_platform"], rows)

    return written


def read_csv(outdir, name):
    with open(os.path.join(outdir, name), newline="") as f:
        return list(csv.DictReader(f))


# ─────────────────────────────────────────────────────────────────────────────
# Schema
# ─────────────────────────────────────────────────────────────────────────────

DDL = """
CREATE TABLE accounts (
    account_id      INTEGER PRIMARY KEY,
    customer_id     INTEGER NOT NULL,
    account_name    TEXT    NOT NULL,
    arr             INTEGER NOT NULL,
    renewal_date    TEXT    NOT NULL,
    health_score    REAL,
    arc_type        TEXT,
    arc_confidence  REAL
);

CREATE TABLE kpi_measurements (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id    INTEGER NOT NULL,
    kpi_code      TEXT    NOT NULL,
    pillar        TEXT    NOT NULL,
    measured_at   TEXT    NOT NULL,
    value         REAL    NOT NULL
);

CREATE TABLE qualitative_signals (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id    INTEGER NOT NULL,
    signal_ref    TEXT    NOT NULL UNIQUE,
    signal_date   TEXT    NOT NULL,
    signal_type   TEXT    NOT NULL,
    content       TEXT    NOT NULL,
    sentiment     TEXT    NOT NULL
);

CREATE TABLE outcomes (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id    INTEGER NOT NULL,
    outcome_date  TEXT    NOT NULL,
    title         TEXT    NOT NULL,
    outcome_type  TEXT    NOT NULL,
    revenue_value INTEGER NOT NULL
);

CREATE TABLE context_nodes (
    node_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id     INTEGER NOT NULL,
    account_id      INTEGER NOT NULL,
    node_type       TEXT    NOT NULL,
    node_subtype    TEXT,
    title           TEXT    NOT NULL,
    source          TEXT,              -- observed | synthetic | inferred
    tier            INTEGER,
    confidence      REAL,
    source_platform TEXT,
    source_event_id TEXT,
    properties      TEXT,
    revenue_impact  INTEGER,
    occurred_at     TEXT
);

CREATE TABLE context_edges (
    edge_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    from_node_id    INTEGER NOT NULL,
    to_node_id      INTEGER NOT NULL,
    edge_type       TEXT    NOT NULL,
    weight          REAL,
    confidence      REAL,               -- NULL for inferred edges in fixed mode
    properties      TEXT,
    source_platform TEXT,
    created_by      TEXT,
    occurred_at     TEXT,
    -- target-design columns (populated only in --mode fixed)
    evidence_tier   TEXT,               -- observed | asserted | inferred | unknown
    derivation      TEXT,
    superseded_by   INTEGER
);

CREATE TABLE customer_config (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL,
    updated_at  TEXT
);

CREATE TABLE calibration_history (
    calibration_id TEXT PRIMARY KEY,
    wizard         TEXT NOT NULL,
    calibrated_at  TEXT NOT NULL,
    payload        TEXT NOT NULL
);
"""


# ─────────────────────────────────────────────────────────────────────────────
# Edge writing — the single most important difference between the two modes
# ─────────────────────────────────────────────────────────────────────────────

class EdgeWriter:
    """
    current mode : a bare INSERT. Any caller can write any edge, with any
                   confidence, and nothing records what warrant it has.
    fixed   mode : the only sanctioned constructor. evidence_tier is NOT NULL
                   and must be declared by the caller; inferred edges write
                   confidence = NULL.
    """

    def __init__(self, conn, mode):
        self.conn = conn
        self.mode = mode

    def write(self, frm, to, etype, *, confidence, properties, source_platform,
              created_by, evidence_tier, derivation, weight=1.0, occurred_at=None):
        if self.mode == "fixed":
            if evidence_tier not in ("observed", "asserted", "inferred", "unknown"):
                raise ValueError(f"evidence_tier must be declared, got {evidence_tier!r}")
            if evidence_tier == "inferred":
                # Nothing was computed, so no number is emitted. The typed
                # plausibility travels in properties under its own name.
                properties = dict(properties or {})
                if confidence is not None:
                    properties["template_plausibility"] = confidence
                confidence = None
            cols = ("from_node_id,to_node_id,edge_type,weight,confidence,properties,"
                    "source_platform,created_by,occurred_at,evidence_tier,derivation")
            vals = (frm, to, etype, weight, confidence, json.dumps(properties or {}),
                    source_platform, created_by, occurred_at, evidence_tier, derivation)
            ph = ",".join("?" * 11)
        else:
            cols = ("from_node_id,to_node_id,edge_type,weight,confidence,properties,"
                    "source_platform,created_by,occurred_at")
            vals = (frm, to, etype, weight, confidence, json.dumps(properties or {}),
                    source_platform, created_by, occurred_at)
            ph = ",".join("?" * 9)
        cur = self.conn.execute(f"INSERT INTO context_edges ({cols}) VALUES ({ph})", vals)
        return cur.lastrowid


def add_node(conn, account_id, node_type, subtype, title, *, source, tier,
             confidence, source_platform, source_event_id, properties=None,
             revenue_impact=None, occurred_at=None):
    cur = conn.execute(
        """INSERT INTO context_nodes
           (customer_id,account_id,node_type,node_subtype,title,source,tier,
            confidence,source_platform,source_event_id,properties,revenue_impact,occurred_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (CUSTOMER_ID, account_id, node_type, subtype, title, source, tier, confidence,
         source_platform, source_event_id, json.dumps(properties or {}),
         revenue_impact, occurred_at))
    return cur.lastrowid


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 1 — cold-start CSV load
# ─────────────────────────────────────────────────────────────────────────────

COLD_START_FILES = ["accounts.csv", "kpi_measurements.csv",
                    "enhanced_qualitative_signals.csv", "outcomes.csv"]


def stage1_cold_load(conn, csvdir):
    stage(1, "COLD START — load the four Month-1 CSVs",
          " · ".join(COLD_START_FILES))
    before = table_counts(conn)

    section("Input files on disk")
    rows = []
    for name in sorted(os.listdir(csvdir)):
        path = os.path.join(csvdir, name)
        n = sum(1 for _ in open(path)) - 1
        used = GRN("loaded now") if name in COLD_START_FILES else YEL("held back → Month 2")
        rows.append([name, n, os.path.getsize(path), used])
    table(["file", "data rows", "bytes", "stage"], rows)

    for r in read_csv(csvdir, "accounts.csv"):
        conn.execute(
            "INSERT INTO accounts (account_id,customer_id,account_name,arr,renewal_date) "
            "VALUES (?,?,?,?,?)",
            (int(r["source_account_id"]), int(r["customer_id"]), r["account_name"],
             int(r["arr"]), r["renewal_date"]))

    for r in read_csv(csvdir, "kpi_measurements.csv"):
        conn.execute(
            "INSERT INTO kpi_measurements (account_id,kpi_code,pillar,measured_at,value) "
            "VALUES (?,?,?,?,?)",
            (int(r["source_account_id"]), r["kpi_code"], r["pillar"],
             r["measured_at"], float(r["value"])))

    for r in read_csv(csvdir, "enhanced_qualitative_signals.csv"):
        conn.execute(
            "INSERT INTO qualitative_signals "
            "(account_id,signal_ref,signal_date,signal_type,content,sentiment) "
            "VALUES (?,?,?,?,?,?)",
            (int(r["source_account_id"]), r["signal_ref"], r["signal_date"],
             r["signal_type"], r["content"], r["sentiment"]))

    for r in read_csv(csvdir, "outcomes.csv"):
        conn.execute(
            "INSERT INTO outcomes (account_id,outcome_date,title,outcome_type,revenue_value) "
            "VALUES (?,?,?,?,?)",
            (int(r["source_account_id"]), r["outcome_date"], r["title"],
             r["outcome_type"], int(r["revenue_value"])))
    conn.commit()

    rowcount_delta(conn, "Rows written by the CSV load", before)
    flag("signal_edges.csv exists on disk but is NOT part of Month-1 onboarding. "
         "No causal structure was uploaded.")
    note("context_nodes and context_edges are still empty. Nothing causal exists yet —")
    note("which is precisely the gap Wizard A was built to fill.")


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 2 — health scoring (L1 -> L2 -> L3)
# ─────────────────────────────────────────────────────────────────────────────

def load_weights(conn):
    row = conn.execute("SELECT value FROM customer_config WHERE key='pillar_weights'").fetchone()
    return json.loads(row[0]) if row else dict(BOOTSTRAP_WEIGHTS)


def stage2_health_scoring(conn, label="STAGE 2"):
    stage(2, "HEALTH SCORING — L1 (KPI) → L2 (pillar) → L3 (account)",
          "Weights come from customer_config if Wizard C has run; bootstrap values otherwise.")
    weights = load_weights(conn)
    src = "customer_config (Wizard C)" if conn.execute(
        "SELECT 1 FROM customer_config WHERE key='pillar_weights'").fetchone() else "bootstrap"
    note(f"weight source: {src}  →  {weights}")

    rows = []
    for aid, name, *_ in SEED_ACCOUNTS:
        pillar_scores = {}
        for p in PILLARS:
            vals = [r[0] for r in conn.execute(
                "SELECT value FROM kpi_measurements WHERE account_id=? AND pillar=? "
                "ORDER BY measured_at DESC LIMIT ?", (aid, p, len(KPI_CATALOG)))]
            pillar_scores[p] = round(statistics.fmean(vals), 2) if vals else 0.0
        health = round(sum(pillar_scores[p] * weights[p] for p in PILLARS), 2)
        conn.execute("UPDATE accounts SET health_score=? WHERE account_id=?", (health, aid))
        status = ("critical" if health < 50 else "at_risk" if health < 70 else "healthy")
        colour = RED if health < 50 else YEL if health < 70 else GRN
        rows.append([aid, name, pillar_scores["P1"], pillar_scores["P2"],
                     pillar_scores["P3"], colour(f"{health:.1f}"), colour(status)])
    conn.commit()
    section("Account health after rollup")
    table(["account_id", "name", "P1", "P2", "P3", "health", "status"], rows)
    return weights


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 3 — WIZARD A
# ─────────────────────────────────────────────────────────────────────────────

def classify_arc(conn, aid):
    """Rule cascade — deterministic, no LLM. Returns (arc_type, matched_rule)."""
    sigs = [r[0] for r in conn.execute(
        "SELECT signal_type FROM qualitative_signals WHERE account_id=? ORDER BY signal_date", (aid,))]
    health = conn.execute("SELECT health_score FROM accounts WHERE account_id=?", (aid,)).fetchone()[0]

    # R1..R5 — order matters, first match wins. This is the cascade.
    if any(s in ("champion_change", "champion_loss", "stakeholder_departure") for s in sigs):
        return "champion_loss", "R1 champion signal present"
    if any(s in ("sla_breach", "mttr_regression", "critical_incident") for s in sigs):
        return "infrastructure_decay", "R2 reliability signal present"
    if any(s in ("adoption_milestone", "expansion_interest") for s in sigs) and health >= 70:
        return "land_and_expand", "R3 adoption signal + healthy"
    if health < 50:
        return "champion_loss", "R4 fallback: low health with no matching signal"
    return "land_and_expand", "R5 default"


def classify_trajectory(conn, aid):
    """
    The THIRD, independent classifier — pure health-trajectory shape matching.
    Unrelated to the rule cascade above and to ARC_TEMPLATES. It can, and does,
    disagree with classify_arc().
    """
    traj = dict((a[0], a[4]) for a in SEED_ACCOUNTS)[aid]
    drop = traj[0] - traj[-1]
    if drop >= 45:
        pattern = "crisis"
    elif drop >= 15:
        pattern = "decline"
    elif drop <= -15:
        pattern = "recovery"
    else:
        pattern = "flat"
    base = TRAJECTORY_BASE[pattern]
    delta = min(0.45, abs(drop) / 100.0)      # genuinely computed term
    return pattern, round(min(1.0, base + delta), 2)   # note the clamp


def stage3_wizard_a(conn, writer, mode):
    stage(3, "WIZARD A — arc classification + edge generation",
          "Per-account. Deductive: apply a stored template to one account. This is the cold-start bootstrap.")
    before = table_counts(conn)

    # 3a. Promote signals and outcomes into context nodes.
    for aid, *_ in [(a[0],) for a in SEED_ACCOUNTS]:
        for sid, ref, sdate, stype, content, sentiment in conn.execute(
                "SELECT id,signal_ref,signal_date,signal_type,content,sentiment "
                "FROM qualitative_signals WHERE account_id=? ORDER BY signal_date", (aid,)):
            add_node(conn, aid, "SIGNAL", stype, content,
                     source="observed", tier=2, confidence=1.0,
                     source_platform="csv_import", source_event_id=ref,
                     properties={"sentiment": sentiment, "signal_ref": ref}, occurred_at=sdate)
        for oid, odate, title, otype, rev in conn.execute(
                "SELECT id,outcome_date,title,outcome_type,revenue_value "
                "FROM outcomes WHERE account_id=? ORDER BY outcome_date", (aid,)):
            add_node(conn, aid, "OUTCOME", otype, title,
                     source="observed", tier=1, confidence=1.0,
                     source_platform="csv_import", source_event_id=f"outcome:{otype}",
                     properties={"evidence": ""},          # <- empty evidence, tier 1, confidence 1
                     revenue_impact=rev, occurred_at=odate)
    conn.commit()

    section("3a · signals and outcomes promoted to context_nodes")
    note("csv_import rows are written as source='observed', tier=1 for OUTCOMEs, confidence=1.0")
    flag("A customer-uploaded assertion is being recorded as 'observed'. "
         "Note the empty evidence string on tier-1 revenue OUTCOMEs.")

    # 3b. Classify + generate edges.
    class_rows, edge_rows, mismatches = [], [], []
    for aid, name, *_ in SEED_ACCOUNTS:
        arc, rule = classify_arc(conn, aid)
        pattern, conf = classify_trajectory(conn, aid)
        conn.execute("UPDATE accounts SET arc_type=?, arc_confidence=? WHERE account_id=?",
                     (arc, conf, aid))

        # The arc_detection node — written by the trajectory classifier, and it
        # carries a DIFFERENT arc label than the edges will.
        add_node(conn, aid, "SIGNAL", "arc_detection", f"Arc Detected: {pattern}",
                 source="synthetic", tier=2, confidence=1.0,
                 source_platform=None,                       # <- untagged, as in production
                 source_event_id=None,
                 properties={"arc_type": pattern, "confidence": conf, "triggered_by": "wizard_a"},
                 occurred_at=T0.date().isoformat())

        class_rows.append([aid, name, rule, arc, f"{pattern} ({conf})"])

        # Template edge generation — binds by POSITION, not by meaning.
        sig_nodes = conn.execute(
            "SELECT node_id,title,node_subtype FROM context_nodes WHERE account_id=? "
            "AND node_type='SIGNAL' AND node_subtype!='arc_detection' ORDER BY occurred_at", (aid,)).fetchall()
        out_nodes = conn.execute(
            "SELECT node_id,title FROM context_nodes WHERE account_id=? AND node_type='OUTCOME' "
            "ORDER BY occurred_at", (aid,)).fetchall()

        for tmpl in ARC_TEMPLATES[arc]["edges"]:
            def resolve(slot):
                kind, idx = slot.split(":")
                pool = sig_nodes if kind == "signal" else out_nodes
                return pool[int(idx)] if int(idx) < len(pool) else None
            a_node, b_node = resolve(tmpl["frm"]), resolve(tmpl["to"])
            if not a_node or not b_node:
                continue
            writer.write(
                a_node[0], b_node[0], tmpl["type"],
                confidence=tmpl["confidence"],
                properties={"label": tmpl["label"], "arc_type": arc, "arc_phase": tmpl["phase"],
                            "lag_days_asserted": tmpl["lag_days"]},
                source_platform="wizard_a", created_by="arc_edge_generator",
                evidence_tier="inferred", derivation="wizard_a.arc_template")
            edge_rows.append([aid, f"{a_node[2] or 'outcome'}", tmpl["type"],
                              tmpl["label"][:44], tmpl["confidence"]])
            # Does the template label bear any relation to what it connects?
            keywords = {"champion": ("champion",), "engagement": ("engagement", "sync", "qbr"),
                        "adoption": ("adoption",), "reliability": ("sla", "mttr", "incident")}
            lab = tmpl["label"].lower()
            for theme, keys in keywords.items():
                if theme in lab:
                    blob = f"{a_node[1]} {b_node[1]}".lower()
                    if not any(k in blob for k in keys):
                        mismatches.append([aid, tmpl["label"][:38], a_node[1][:34], b_node[1][:30]])
                    break
    conn.commit()

    section("3b · arc classification — two classifiers, one account")
    table(["account_id", "name", "cascade rule", "classify_arc() → EDGES", "trajectory → arc_detection NODE"],
          class_rows)
    flag("Two classifiers run on every account and they do not share a vocabulary — "
         "one emits arc types (champion_loss…), the other emits trajectory shapes (crisis…).")
    flag("They are therefore not reconcilable, not merely in disagreement. The arc_detection NODE "
         "carries one label and the generated EDGES carry the other, on every single account.")

    section("3c · edges generated from ARC_TEMPLATES")
    table(["account_id", "from node subtype", "type", "template label", "conf"], edge_rows)

    if mismatches:
        section("3d · template labels vs. the nodes they actually connect")
        table(["account_id", "template label", "from node", "to node"], mismatches)
        flag(f"{len(mismatches)} edges carry a narrative unrelated to the events they join. "
             "Templates bind by POSITION (signal:1), not by meaning.")

    rowcount_delta(conn, "Rows written by Wizard A", before)
    print_metrics(conn, mode, "after Wizard A (cold start)")


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 4 — WIZARD B
# ─────────────────────────────────────────────────────────────────────────────

def stage4_wizard_b(conn):
    stage(4, "WIZARD B — pattern analysis across the portfolio",
          "Cross-account. Inductive: derive patterns from many accounts. Requires >= 5 accounts.")
    n = conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
    note(f"account count = {n} — threshold is 5, so Wizard B runs.")

    # 4a. Early-warning patterns: which signal types precede a negative outcome?
    warn = {}
    for aid, in conn.execute("SELECT account_id FROM accounts"):
        neg = conn.execute(
            "SELECT COUNT(*) FROM outcomes WHERE account_id=? AND revenue_value<0", (aid,)).fetchone()[0]
        for (stype,) in conn.execute(
                "SELECT signal_type FROM qualitative_signals WHERE account_id=?", (aid,)):
            d = warn.setdefault(stype, [0, 0])
            d[0] += 1
            d[1] += 1 if neg else 0
    rows = sorted(([k, v[0], v[1], f"{v[1] / v[0]:.0%}"] for k, v in warn.items()),
                  key=lambda r: (-float(r[3].rstrip('%')), r[0]))[:8]
    section("4a · early-warning patterns (signal type → negative outcome rate)")
    table(["signal_type", "occurrences", "with neg. outcome", "rate"], rows)
    flag("Almost every rate is 100% on n=1. The >=5-account threshold lets Wizard B run, but it "
         "does not make the output meaningful —")
    flag("these 'patterns' carry no provenance and no sample size, and Wizard D consumes them "
         "downstream as if they were established.")

    # 4b. Archetypes by trajectory shape.
    arche = {}
    for aid, name, *_ , traj in [(a[0], a[1], a[2], a[3], a[4]) for a in SEED_ACCOUNTS]:
        drop = traj[0] - traj[-1]
        k = "collapsing" if drop >= 45 else "eroding" if drop >= 15 else \
            "compounding" if drop <= -15 else "stable"
        arche.setdefault(k, []).append(name)
    section("4b · account archetypes")
    table(["archetype", "n", "accounts"],
          [[k, len(v), ", ".join(v)] for k, v in sorted(arche.items())])

    # 4c. THE POINT. Measure the real lag, then compare it to what A asserted.
    observed = []
    for aid, in conn.execute("SELECT account_id FROM accounts"):
        dates = [datetime.fromisoformat(d) for (d,) in conn.execute(
            "SELECT signal_date FROM qualitative_signals WHERE account_id=? ORDER BY signal_date", (aid,))]
        observed += [(b - a).days for a, b in zip(dates, dates[1:])]
    med = statistics.median(observed) if observed else 0
    asserted = sorted({e["lag_days"] for t in ARC_TEMPLATES.values() for e in t["edges"]})
    section("4c · observed signal-to-signal lag vs. the lags Wizard A asserts")
    table(["metric", "value"],
          [["observed lags (n)", len(observed)],
           ["observed median lag", f"{med:.0f} days"],
           ["observed range", f"{min(observed)}–{max(observed)} days"],
           ["lag_days hardcoded in ARC_TEMPLATES", ", ".join(str(x) for x in asserted)]])
    flag("Wizard B has just measured the real lag distribution. Wizard A will keep asserting "
         "its hardcoded values on the next run. Nothing carries B's finding back to A's templates —")
    flag("the pipeline has a learning engine and an asserting engine, wired in a line, not a loop.")

    conn.execute("INSERT INTO calibration_history (calibration_id,wizard,calibrated_at,payload) "
                 "VALUES (?,?,?,?)",
                 ("wizB-0001", "B", T0.isoformat(),
                  json.dumps({"observed_median_lag_days": med, "archetypes": list(arche)})))
    conn.commit()


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 5 — WIZARD C
# ─────────────────────────────────────────────────────────────────────────────

def stage5_wizard_c(conn):
    stage(5, "WIZARD C — weight calibration",
          "Correlate pillar scores with realised outcomes; rewrite pillar weights in customer_config.")
    old = load_weights(conn)
    corr = {}
    for p in PILLARS:
        xs, ys = [], []
        for aid, in conn.execute("SELECT account_id FROM accounts"):
            v = [r[0] for r in conn.execute(
                "SELECT value FROM kpi_measurements WHERE account_id=? AND pillar=? "
                "ORDER BY measured_at DESC LIMIT 6", (aid, p))]
            rev = conn.execute(
                "SELECT COALESCE(SUM(revenue_value),0) FROM outcomes WHERE account_id=?",
                (aid,)).fetchone()[0]
            if v:
                xs.append(statistics.fmean(v))
                ys.append(1.0 if rev > 0 else 0.0)
        try:
            corr[p] = abs(statistics.correlation(xs, ys)) if len(set(xs)) > 1 else 0.0
        except Exception:
            corr[p] = 0.0
    total = sum(corr.values()) or 1.0
    new = {p: round(corr[p] / total, 3) for p in PILLARS}
    drift = sum(abs(new[p] - old[p]) for p in PILLARS)

    section("5a · discovered weights")
    table(["pillar", "name", "|corr| with success", "old weight", "new weight", "Δ"],
          [[p, PILLARS[p], f"{corr[p]:.3f}", old[p], new[p],
            f"{new[p] - old[p]:+.3f}"] for p in PILLARS])
    conn.execute("INSERT OR REPLACE INTO customer_config (key,value,updated_at) VALUES (?,?,?)",
                 ("pillar_weights", json.dumps(new), T0.isoformat()))
    conn.execute("INSERT INTO calibration_history (calibration_id,wizard,calibrated_at,payload) "
                 "VALUES (?,?,?,?)",
                 ("wizC-0001", "C", T0.isoformat(),
                  json.dumps({"weights": new, "l1_drift": round(drift, 3)})))
    conn.commit()
    note(f"total weight drift from bootstrap: {drift:.3f}")
    note("Health scores are now stale — every account must be rescored against the new weights.")
    return new


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 6 — WIZARD D
# ─────────────────────────────────────────────────────────────────────────────

def stage6_wizard_d(conn):
    stage(6, "WIZARD D — predictor calibration + forward NRR",
          "Fit health → churn probability on realised outcomes, then forecast forward.")
    obs = []
    for aid, h in conn.execute("SELECT account_id,health_score FROM accounts"):
        churned = conn.execute(
            "SELECT COUNT(*) FROM outcomes WHERE account_id=? AND outcome_type IN "
            "('churn','contraction')", (aid,)).fetchone()[0] > 0
        obs.append((h, 1.0 if churned else 0.0))
    hs = [o[0] for o in obs]
    lo, hi = min(hs), max(hs)
    # Deliberately simple monotone calibration — the point is the provenance, not the model.
    def p_churn(h):
        if hi == lo:
            return 0.5
        return round(max(0.02, min(0.95, 1.0 - (h - lo) / (hi - lo))), 3)

    rows = []
    for aid, name, arr, *_ in SEED_ACCOUNTS:
        h = conn.execute("SELECT health_score FROM accounts WHERE account_id=?", (aid,)).fetchone()[0]
        pc = p_churn(h)
        expand = round(0.12 * (1 - pc), 3)
        nrr = round((1 - pc) * (1 + expand) * 100, 1)
        rows.append([aid, name, f"{h:.1f}", pc, f"{nrr:.1f}%", f"${arr:,.0f}"])
    section("6a · per-account forward NRR (12mo)")
    table(["account_id", "name", "health", "p(churn)", "expected NRR", "ARR"], rows)

    tot_arr = sum(a[2] for a in SEED_ACCOUNTS)
    weighted = sum(float(r[4].rstrip('%')) * a[2] for r, a in zip(rows, SEED_ACCOUNTS)) / tot_arr
    note(f"ARR-weighted portfolio NRR: {weighted:.1f}%   (basis: ${tot_arr:,.0f} portfolio ARR)")
    conn.execute("INSERT INTO calibration_history (calibration_id,wizard,calibrated_at,payload) "
                 "VALUES (?,?,?,?)",
                 ("wizD-0001", "D", T0.isoformat(),
                  json.dumps({"arr_weighted_nrr": round(weighted, 1), "n_obs": len(obs)})))
    conn.commit()
    flag("This number is now downstream of Wizard B's patterns and Wizard C's weights — "
         "neither of which has any provenance record at all.")


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 7 — HOT DATA
# ─────────────────────────────────────────────────────────────────────────────

def stage7_hot_load(conn, writer, mode, csvdir):
    stage(7, "HOT DATA — incremental load (signal_edges.csv arrives in Month 2)",
          "Real, evidence-backed causal edges finally show up. What happens to the invented ones?")
    before = table_counts(conn)
    rows, superseded = [], 0

    hot = read_csv(csvdir, "signal_edges.csv")
    section("signal_edges.csv — resolved by signal_ref, not by position")
    table(["from_signal_ref", "to_signal_ref", "edge_type", "lag_days", "evidence"],
          [[h["from_signal_ref"], h["to_signal_ref"], h["edge_type"], h["lag_days"],
            h["evidence"][:40]] for h in hot])

    for he in hot:
        def node_for(ref):
            r = conn.execute(
                "SELECT node_id,title,account_id FROM context_nodes WHERE source_event_id=? "
                "AND node_type='SIGNAL'", (ref,)).fetchone()
            return r
        a_node, b_node = node_for(he["from_signal_ref"]), node_for(he["to_signal_ref"])
        if not a_node or not b_node:
            flag(f"unresolved signal_ref: {he['from_signal_ref']} → {he['to_signal_ref']}")
            continue
        aid = a_node[2]
        he = dict(he, type=he["edge_type"], label=he["label"],
                  evidence=he["evidence"], lag_days=int(he["lag_days"]))

        existing = conn.execute(
            "SELECT edge_id,confidence,properties FROM context_edges "
            "WHERE from_node_id=? AND to_node_id=? AND edge_type=? AND superseded_by IS NULL",
            (a_node[0], b_node[0], he["type"])).fetchall()

        new_id = writer.write(
            a_node[0], b_node[0], he["type"],
            confidence=0.95,
            properties={"label": he["label"], "evidence": he["evidence"],
                        "lag_days_observed": he["lag_days"]},
            source_platform="csv_import", created_by="signal_edges_ingest",
            evidence_tier="observed", derivation="csv.signal_edges")

        if mode == "fixed":
            for eid, _, _ in existing:
                conn.execute("UPDATE context_edges SET superseded_by=? WHERE edge_id=?", (new_id, eid))
                superseded += 1

        for eid, conf, props in existing:
            p = json.loads(props)
            rows.append([aid, f"{a_node[0]}→{b_node[0]}", "wizard_a (template)",
                         p.get("label", "")[:40], conf,
                         GRN("superseded") if mode == "fixed" else RED("still live")])
        rows.append([aid, f"{a_node[0]}→{b_node[0]}", "csv_import (observed)",
                     he["label"][:40], 0.95, GRN("new")])
    conn.commit()

    section("7a · collisions between uploaded edges and Wizard A's inventions")
    table(["account_id", "node pair", "source", "label", "conf", "state"], rows)

    if mode == "current":
        flag("Both edges survive. Same node pair, same edge_type, two contradictory labels, "
             "two confidences. There is no supersession path —")
        flag("the scaffolding is never removed when the building arrives. "
             "get_causal_chain() will return this node pair twice.")
        dupes = conn.execute(
            "SELECT COUNT(*) FROM (SELECT from_node_id,to_node_id,edge_type FROM context_edges "
            "GROUP BY 1,2,3 HAVING COUNT(*)>1)").fetchone()[0]
        note(f"duplicated (from,to,type) triples in the graph: {dupes}")
    else:
        good(f"{superseded} template edges marked superseded_by the observed edge that replaced them.")
        good("Evidence Density rises because fabricated claims are retired, not merely diluted.")

    rowcount_delta(conn, "Rows written by the incremental load", before)
    print_metrics(conn, mode, "after hot load")


# ─────────────────────────────────────────────────────────────────────────────
# Metrics
# ─────────────────────────────────────────────────────────────────────────────

def compute_metrics(conn, mode):
    live = "WHERE superseded_by IS NULL" if mode == "fixed" else ""
    total = conn.execute(f"SELECT COUNT(*) FROM context_edges {live}").fetchone()[0]
    if mode == "fixed":
        obs = conn.execute("SELECT COUNT(*) FROM context_edges WHERE superseded_by IS NULL "
                           "AND evidence_tier='observed'").fetchone()[0]
        inf = conn.execute("SELECT COUNT(*) FROM context_edges WHERE superseded_by IS NULL "
                           "AND evidence_tier='inferred'").fetchone()[0]
        with_deriv = conn.execute("SELECT COUNT(*) FROM context_edges WHERE superseded_by IS NULL "
                                  "AND evidence_tier='inferred' AND derivation IS NOT NULL").fetchone()[0]
    else:
        obs = conn.execute("SELECT COUNT(*) FROM context_edges "
                           "WHERE source_platform='csv_import'").fetchone()[0]
        inf = total - obs
        with_deriv = 0
    density = (obs / total * 100) if total else 0.0
    deriv = (with_deriv / inf * 100) if inf else 0.0
    return dict(total=total, observed=obs, inferred=inf, density=density, derivation=deriv)


def print_metrics(conn, mode, when):
    m = compute_metrics(conn, mode)
    section(f"Metrics · {when}")
    dcol = RED if m["density"] < 25 else YEL if m["density"] < 60 else GRN
    table(["metric", "value"],
          [["live causal edges", m["total"]],
           ["observed", m["observed"]],
           ["inferred", m["inferred"]],
           [BOLD("Evidence Density"), dcol(f"{m['density']:.1f}%")],
           [BOLD("Derivation Completeness"), f"{m['derivation']:.1f}%"]])


# ─────────────────────────────────────────────────────────────────────────────
# Driver
# ─────────────────────────────────────────────────────────────────────────────

def run(mode, db_path, csvdir="demo_csv", quiet=False, regen=True):
    if regen or not os.path.isdir(csvdir):
        written = emit_csvs(csvdir)
    else:
        written = None
    if os.path.exists(db_path):
        os.remove(db_path)
    conn = sqlite3.connect(db_path)
    conn.executescript(DDL)
    writer = EdgeWriter(conn, mode)

    if not quiet:
        print()
        print(BOLD(BLU("╔" + "═" * (WIDTH - 2) + "╗")))
        print(BOLD(BLU("║") + BOLD(f"  CS Pulse · process_data() simulation · mode = {mode}".ljust(WIDTH - 2)) + BOLD(BLU("║"))))
        print(BOLD(BLU("║") + DIM(f"  database: {db_path}   inputs: {csvdir}/".ljust(WIDTH - 2)) + BOLD(BLU("║"))))
        print(BOLD(BLU("╚" + "═" * (WIDTH - 2) + "╝")))
        stage(0, "SCHEMA", f"{len(TABLES)} tables created, all empty")
        table(["table", "rows"], [[t, 0] for t in TABLES])

        stage1_cold_load(conn, csvdir)
        stage2_health_scoring(conn)
        stage3_wizard_a(conn, writer, mode)
        stage4_wizard_b(conn)
        stage5_wizard_c(conn)
        stage2_health_scoring(conn)          # rescore with calibrated weights
        stage6_wizard_d(conn)
        stage7_hot_load(conn, writer, mode, csvdir)

        print()
        print(BOLD(CYN("━" * WIDTH)))
        print(BOLD(f"  Done. Inspect the rows:  sqlite3 {db_path} 'select * from context_edges;'"))
        print(BOLD(CYN("━" * WIDTH)))
        print()
    else:
        stage1_cold_load(conn, csvdir); stage2_health_scoring(conn)
        stage3_wizard_a(conn, writer, mode); stage4_wizard_b(conn)
        stage5_wizard_c(conn); stage2_health_scoring(conn)
        stage6_wizard_d(conn); stage7_hot_load(conn, writer, mode, csvdir)

    m = compute_metrics(conn, mode)
    conn.close()
    return m


def main():
    ap = argparse.ArgumentParser(description="CS Pulse process_data() pipeline simulation")
    ap.add_argument("--mode", choices=["current", "fixed", "compare"], default="current")
    ap.add_argument("--db", default=None, help="sqlite output path")
    ap.add_argument("--csv-dir", default="demo_csv", help="where the input CSVs live")
    ap.add_argument("--keep-csv", action="store_true",
                    help="do not regenerate the CSVs — use whatever is already in --csv-dir "
                         "(edit the files and re-run to try your own scenario)")
    ap.add_argument("--emit-csv-only", action="store_true",
                    help="write the input CSVs and exit without running the pipeline")
    args = ap.parse_args()

    if args.emit_csv_only:
        for name, n in emit_csvs(args.csv_dir):
            print(f"{args.csv_dir}/{name:38s} {n:5d} data rows")
        return

    if args.mode == "compare":
        import io, contextlib
        results = {}
        for m in ("current", "fixed"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                results[m] = run(m, f"cspulse_demo_{m}.db", args.csv_dir,
                                 quiet=True, regen=not args.keep_csv)
        print()
        print(BOLD(BLU("  CURRENT vs FIXED — same inputs, same wizards, different write discipline")))
        print()
        table(["metric", "current", "fixed", "Δ"],
              [["live causal edges", results["current"]["total"], results["fixed"]["total"],
                results["fixed"]["total"] - results["current"]["total"]],
               ["observed", results["current"]["observed"], results["fixed"]["observed"], ""],
               ["inferred", results["current"]["inferred"], results["fixed"]["inferred"], ""],
               ["Evidence Density", f"{results['current']['density']:.1f}%",
                f"{results['fixed']['density']:.1f}%",
                f"{results['fixed']['density'] - results['current']['density']:+.1f} pts"],
               ["Derivation Completeness", f"{results['current']['derivation']:.1f}%",
                f"{results['fixed']['derivation']:.1f}%", ""]])
        print()
        note("The fixed run has FEWER live edges — superseded template edges are retired,")
        note("not deleted. They remain in the table with superseded_by set, for audit.")
        print()
    else:
        run(args.mode, args.db or f"cspulse_demo_{args.mode}.db", args.csv_dir,
            regen=not args.keep_csv)


if __name__ == "__main__":
    main()
