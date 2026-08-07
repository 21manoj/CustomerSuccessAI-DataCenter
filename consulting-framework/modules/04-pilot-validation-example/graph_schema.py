"""
Context Graph & Causal Layer — schema module.

Invented client vertical for this pilot: `regional_utility_v1` — a customer
success platform for a company that sells grid-monitoring/analytics software
to regional electric & water utility co-ops. Nodes/edges in this vertical
describe things like outage-report signals, regulatory-filing external
context, infrastructure-investment decisions, and contract
renewal/expansion/churn outcomes.

Storage choice: SQLite (stdlib `sqlite3`), not pure in-memory Python objects.
Justification:
  - Module 01's validated pattern in this same library is "ask the database,
    not the ORM" for tenant-isolation guarantees — invariants and reads in
    this module are exactly the kind of cross-cutting, `customer_id`-scoped
    query that benefits from a real query engine rather than hand-rolled
    Python filtering, which is easy to get subtly wrong per Gotcha 2
    (cross-tenant leakage through a node-ID-only read).
  - SQLite gives us real foreign keys, real indexes on `customer_id`, and a
    single obvious place (the repository functions below) through which
    every read must pass — there is no way to "accidentally" bypass the
    `customer_id` filter by reaching into a dict of nodes directly, the way
    there would be with an in-memory dict-of-objects design.
  - It's still fully self-contained (stdlib only, no server, one file on
    disk or `:memory:` for tests) — appropriate for a pilot validation that
    must not depend on the reference Postgres schema.
  - Downside acknowledged: a real deployment would use Postgres (per Module
    01's own schema) with `ContextNode`/`ContextEdge` as real FK-linked
    tables; this module's repository API is written so swapping the
    connection factory for a Postgres one requires no caller-facing changes.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Enumerated vocabularies fixed by the Data Shapes section of the spec.
# ---------------------------------------------------------------------------

NODE_TYPES = {"SIGNAL", "STAKEHOLDER", "DECISION", "OUTCOME", "EXTERNAL_CONTEXT"}

EDGE_TYPES = {
    "CAUSED_BY",
    "INDICATES",
    "LED_TO",
    "CORRELATES_WITH",
    "INVOLVES",
    "BELONGS_TO",
    "BENCHMARKED_BY",
    "SOURCED_FROM",
    "SUPERSEDES",
}

# --- Interpretation decision (spec ambiguity, see pilot report) -----------
# The spec's Build Prompt talks about "a causal edge" throughout invariants
# 1-3 ("No OUTCOME -> OUTCOME causal edge", "No causal edge where
# to_node.occurred_at < from_node.occurred_at", "...at least one inbound
# causal edge") but the Data Shapes section never defines which of the 9
# edge_type values count as "causal" versus merely associative/provenance.
# The Acceptance Criteria bullet for invariant 1 anchors specifically on
# CAUSED_BY ("Inserting a CAUSED_BY edge from an OUTCOME node to another
# OUTCOME node..."), which is the only unambiguous textual anchor in the
# whole spec. We take the narrowest defensible reading and treat CAUSED_BY
# and LED_TO as the two "causal" edge types (both denote one node bringing
# about another), and treat INDICATES/CORRELATES_WITH/INVOLVES/BELONGS_TO/
# BENCHMARKED_BY/SOURCED_FROM/SUPERSEDES as non-causal (associative,
# structural, or provenance edges that should never trip a causal-ordering
# or causal-source invariant). This decision is centralized here so every
# invariant references the same set instead of re-deriving it.
CAUSAL_EDGE_TYPES = {"CAUSED_BY", "LED_TO"}

TIERS = {1, 2, 3}

SOURCES = {"customer", "system"}

REVENUE_BUCKETS_PLACEHOLDER = {"lost", "expansion", "pipeline", "at_risk", "protected"}


def utcnow_iso() -> str:
    return datetime.utcnow().isoformat()


# ---------------------------------------------------------------------------
# Dataclasses mirroring the Data Shapes section exactly.
# ---------------------------------------------------------------------------


@dataclass
class ContextNode:
    node_id: Optional[int]
    customer_id: int
    account_id: int
    node_type: str
    node_subtype: str
    source: str  # 'customer' | 'system'
    tier: int  # 1 | 2 | 3
    properties: dict = field(default_factory=dict)
    revenue_impact: Optional[float] = None
    revenue_impact_type: Optional[str] = None
    confidence: float = 1.0
    occurred_at: str = ""  # ISO8601 — required
    expires_at: Optional[str] = None  # NULL = never expires / tier 1

    def validate(self) -> None:
        if self.node_type not in NODE_TYPES:
            raise ValueError(f"invalid node_type: {self.node_type!r}")
        if self.source not in SOURCES:
            raise ValueError(f"invalid source: {self.source!r}")
        if self.tier not in TIERS:
            raise ValueError(f"invalid tier: {self.tier!r}")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"confidence out of range: {self.confidence!r}")
        if not self.occurred_at:
            raise ValueError("occurred_at is required")
        if self.node_type != "OUTCOME" and self.revenue_impact_type is not None:
            raise ValueError("revenue_impact_type only valid on OUTCOME nodes")


@dataclass
class ContextEdge:
    edge_id: Optional[int]
    customer_id: int
    from_node_id: int
    to_node_id: int
    edge_type: str
    weight: float = 1.0
    confidence: float = 1.0
    revenue_impact: Optional[float] = None
    occurred_at: str = ""
    properties: dict = field(default_factory=dict)

    def validate(self) -> None:
        if self.edge_type not in EDGE_TYPES:
            raise ValueError(f"invalid edge_type: {self.edge_type!r}")
        if not (0.0 <= self.weight <= 1.0):
            raise ValueError(f"weight out of range: {self.weight!r}")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"confidence out of range: {self.confidence!r}")


@dataclass
class Violation:
    invariant_id: str
    severity: str
    account_id: int
    node_ids: list
    edge_ids: list
    message: str


# ---------------------------------------------------------------------------
# Repository — the ONLY way any caller reads or writes nodes/edges. Every
# function requires customer_id (Gotcha 2 / Build Prompt point 1).
# ---------------------------------------------------------------------------


class GraphStore:
    def __init__(self, db_path: str = ":memory:"):
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS context_nodes (
                node_id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                account_id INTEGER NOT NULL,
                node_type TEXT NOT NULL,
                node_subtype TEXT NOT NULL,
                source TEXT NOT NULL,
                tier INTEGER NOT NULL,
                properties TEXT NOT NULL DEFAULT '{}',
                revenue_impact REAL,
                revenue_impact_type TEXT,
                confidence REAL NOT NULL DEFAULT 1.0,
                occurred_at TEXT NOT NULL,
                expires_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_nodes_customer ON context_nodes(customer_id);
            CREATE INDEX IF NOT EXISTS idx_nodes_account ON context_nodes(customer_id, account_id);

            CREATE TABLE IF NOT EXISTS context_edges (
                edge_id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                from_node_id INTEGER NOT NULL,
                to_node_id INTEGER NOT NULL,
                edge_type TEXT NOT NULL,
                weight REAL NOT NULL DEFAULT 1.0,
                confidence REAL NOT NULL DEFAULT 1.0,
                revenue_impact REAL,
                occurred_at TEXT NOT NULL,
                properties TEXT NOT NULL DEFAULT '{}',
                FOREIGN KEY (from_node_id) REFERENCES context_nodes(node_id),
                FOREIGN KEY (to_node_id) REFERENCES context_nodes(node_id)
            );
            CREATE INDEX IF NOT EXISTS idx_edges_customer ON context_edges(customer_id);
            CREATE INDEX IF NOT EXISTS idx_edges_from ON context_edges(customer_id, from_node_id);
            CREATE INDEX IF NOT EXISTS idx_edges_to ON context_edges(customer_id, to_node_id);
            """
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    # -- writes ---------------------------------------------------------

    def add_node(self, node: ContextNode) -> int:
        node.validate()
        cur = self._conn.execute(
            """INSERT INTO context_nodes
               (customer_id, account_id, node_type, node_subtype, source, tier,
                properties, revenue_impact, revenue_impact_type, confidence,
                occurred_at, expires_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                node.customer_id,
                node.account_id,
                node.node_type,
                node.node_subtype,
                node.source,
                node.tier,
                json.dumps(node.properties),
                node.revenue_impact,
                node.revenue_impact_type,
                node.confidence,
                node.occurred_at,
                node.expires_at,
            ),
        )
        self._conn.commit()
        node.node_id = cur.lastrowid
        return node.node_id

    def add_edge(self, edge: ContextEdge) -> int:
        edge.validate()
        # Enforce tenant isolation structurally: both endpoints must belong
        # to the same customer_id as the edge itself (Gotcha 2).
        for nid in (edge.from_node_id, edge.to_node_id):
            n = self.get_node(edge.customer_id, nid)
            if n is None:
                raise ValueError(
                    f"node {nid} does not exist or does not belong to "
                    f"customer_id={edge.customer_id}"
                )
        cur = self._conn.execute(
            """INSERT INTO context_edges
               (customer_id, from_node_id, to_node_id, edge_type, weight,
                confidence, revenue_impact, occurred_at, properties)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                edge.customer_id,
                edge.from_node_id,
                edge.to_node_id,
                edge.edge_type,
                edge.weight,
                edge.confidence,
                edge.revenue_impact,
                edge.occurred_at,
                json.dumps(edge.properties),
            ),
        )
        self._conn.commit()
        edge.edge_id = cur.lastrowid
        return edge.edge_id

    # -- reads: every one takes customer_id as a required parameter -----

    def get_node(self, customer_id: int, node_id: int) -> Optional[ContextNode]:
        row = self._conn.execute(
            "SELECT * FROM context_nodes WHERE node_id = ? AND customer_id = ?",
            (node_id, customer_id),
        ).fetchone()
        return self._row_to_node(row) if row else None

    def get_nodes_for_account(self, customer_id: int, account_id: int) -> list[ContextNode]:
        rows = self._conn.execute(
            "SELECT * FROM context_nodes WHERE customer_id = ? AND account_id = ?",
            (customer_id, account_id),
        ).fetchall()
        return [self._row_to_node(r) for r in rows]

    def get_edges_for_account(self, customer_id: int, account_id: int) -> list[ContextEdge]:
        rows = self._conn.execute(
            """SELECT e.* FROM context_edges e
               JOIN context_nodes n ON n.node_id = e.from_node_id
               WHERE e.customer_id = ? AND n.customer_id = ? AND n.account_id = ?""",
            (customer_id, customer_id, account_id),
        ).fetchall()
        return [self._row_to_edge(r) for r in rows]

    def get_inbound_edges(self, customer_id: int, node_id: int) -> list[ContextEdge]:
        rows = self._conn.execute(
            "SELECT * FROM context_edges WHERE customer_id = ? AND to_node_id = ?",
            (customer_id, node_id),
        ).fetchall()
        return [self._row_to_edge(r) for r in rows]

    def get_all_edges(self, customer_id: int) -> list[ContextEdge]:
        rows = self._conn.execute(
            "SELECT * FROM context_edges WHERE customer_id = ?", (customer_id,)
        ).fetchall()
        return [self._row_to_edge(r) for r in rows]

    def get_all_nodes(self, customer_id: int) -> list[ContextNode]:
        rows = self._conn.execute(
            "SELECT * FROM context_nodes WHERE customer_id = ?", (customer_id,)
        ).fetchall()
        return [self._row_to_node(r) for r in rows]

    # -- helpers ----------------------------------------------------------

    @staticmethod
    def _row_to_node(row: sqlite3.Row) -> ContextNode:
        return ContextNode(
            node_id=row["node_id"],
            customer_id=row["customer_id"],
            account_id=row["account_id"],
            node_type=row["node_type"],
            node_subtype=row["node_subtype"],
            source=row["source"],
            tier=row["tier"],
            properties=json.loads(row["properties"]),
            revenue_impact=row["revenue_impact"],
            revenue_impact_type=row["revenue_impact_type"],
            confidence=row["confidence"],
            occurred_at=row["occurred_at"],
            expires_at=row["expires_at"],
        )

    @staticmethod
    def _row_to_edge(row: sqlite3.Row) -> ContextEdge:
        return ContextEdge(
            edge_id=row["edge_id"],
            customer_id=row["customer_id"],
            from_node_id=row["from_node_id"],
            to_node_id=row["to_node_id"],
            edge_type=row["edge_type"],
            weight=row["weight"],
            confidence=row["confidence"],
            revenue_impact=row["revenue_impact"],
            occurred_at=row["occurred_at"],
            properties=json.loads(row["properties"]),
        )
