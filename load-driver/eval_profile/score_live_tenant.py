"""Score a LIVE eval-profile tenant — what the real platform (Tier1 LLM
inference, Wizard A) actually built in the context graph, diffed against
ground_truth.json. This is the half score_run.py cannot do: score_run.py
runs my own ported PC/FCI against my own generated CSVs, a closed loop that
never touches the platform. This script reads the platform's own inferred
structure back out of Postgres and asks the actual question this whole
effort exists to answer.

Requires an SSH tunnel to the EC2 Postgres (same pattern used throughout
this session for tracer): `ssh -f -N -L 15433:127.0.0.1:5433 ec2-user@<host>`,
then CSPULSE_DB_PASSWORD in the environment.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import psycopg2


def _connect(db_password: str, db_port: int = 15433):
    return psycopg2.connect(
        host='localhost', port=db_port, dbname='cs_pulse',
        user='cspulse', password=db_password,
    )


def fetch_live_edges(customer_id: int, db_password: str, db_port: int = 15433) -> list:
    """Every edge for this customer, joined to both endpoints' node_subtype,
    node_type, and account_id. This is the platform's raw causal-graph
    output — no filtering yet."""
    conn = _connect(db_password, db_port)
    cur = conn.cursor()
    cur.execute("""
        SELECT e.edge_id, e.edge_type, e.confidence, e.source_platform, e.source,
               n1.node_id AS from_id, n1.node_type AS from_type, n1.node_subtype AS from_subtype,
               n2.node_id AS to_id, n2.node_type AS to_type, n2.node_subtype AS to_subtype,
               n1.account_id
        FROM context_edges e
        JOIN context_nodes n1 ON e.from_node_id = n1.node_id
        JOIN context_nodes n2 ON e.to_node_id = n2.node_id
        WHERE e.customer_id = %s
    """, (customer_id,))
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    cur.close(); conn.close()
    return rows


def fetch_live_nodes(customer_id: int, db_password: str, db_port: int = 15433) -> list:
    conn = _connect(db_password, db_port)
    cur = conn.cursor()
    cur.execute("""
        SELECT node_id, node_type, node_subtype, account_id, source, source_platform
        FROM context_nodes WHERE customer_id = %s
    """, (customer_id,))
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    cur.close(); conn.close()
    return rows


def score_live_tenant(customer_id: int, ground_truth_path: str,
                       db_password: str, db_port: int = 15433) -> dict:
    gt = json.loads(Path(ground_truth_path).read_text())
    vocab = set(gt['dag'][0].keys()) if False else None  # placeholder, unused
    signal_types = set()
    outcome_types = set()
    for e in gt['dag']:
        if not e.get('latent_edge'):
            signal_types.add(e['from']); signal_types.add(e['to'])
    true_edges = {
        frozenset((e['from'], e['to'])) for e in gt['dag'] if not e.get('latent_edge')
    }
    my_vocab = signal_types

    nodes = fetch_live_nodes(customer_id, db_password, db_port)
    edges = fetch_live_edges(customer_id, db_password, db_port)

    grounded_node_count = sum(1 for n in nodes if n['node_subtype'] in my_vocab)
    ungrounded_node_count = len(nodes) - grounded_node_count

    grounded_edges = [
        e for e in edges
        if e['from_subtype'] in my_vocab and e['to_subtype'] in my_vocab
    ]
    template_shaped_edges = [e for e in edges if e not in grounded_edges]

    live_edge_set = {frozenset((e['from_subtype'], e['to_subtype'])) for e in grounded_edges}
    tp = len(live_edge_set & true_edges)
    fp = len(live_edge_set - true_edges)
    fn = len(true_edges - live_edge_set)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    # Which true edges were found, and which were missed entirely — the
    # concrete, actionable half of this report.
    found_true_edges = [sorted(e) for e in (live_edge_set & true_edges)]
    missed_true_edges = [sorted(e) for e in (true_edges - live_edge_set)]

    # DECISION/SIGNAL subtypes never in this world's vocabulary at all —
    # the platform's own synthesized structure, not traceable to anything
    # in ground_truth.json.
    ungrounded_subtypes = sorted({
        n['node_subtype'] for n in nodes
        if n['node_subtype'] not in my_vocab and n['node_type'] in ('DECISION', 'SIGNAL')
    })

    return {
        'customer_id': customer_id,
        'world_id': gt['world_id'],
        'seed': gt['seed'],
        'live_node_count': len(nodes),
        'live_edge_count': len(edges),
        'grounded_node_count': grounded_node_count,
        'ungrounded_node_count': ungrounded_node_count,
        'ungrounded_node_fraction': round(ungrounded_node_count / len(nodes), 4) if nodes else 0.0,
        'grounded_edge_count': len(grounded_edges),
        'template_shaped_edge_count': len(template_shaped_edges),
        'template_shaped_edge_fraction': round(len(template_shaped_edges) / len(edges), 4) if edges else 0.0,
        'true_edge_count': len(true_edges),
        'structure_recovery': {
            'precision': round(precision, 4),
            'recall': round(recall, 4),
            'f1': round(f1, 4),
            'found_true_edges': found_true_edges,
            'missed_true_edges': missed_true_edges,
        },
        'ungrounded_decision_signal_subtypes': ungrounded_subtypes,
    }


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Score a live eval-profile tenant against ground_truth.json')
    parser.add_argument('--customer-id', type=int, required=True)
    parser.add_argument('--ground-truth', required=True)
    parser.add_argument('--db-password', default=os.getenv('CSPULSE_DB_PASSWORD'))
    parser.add_argument('--db-port', type=int, default=15433)
    args = parser.parse_args()
    if not args.db_password:
        raise SystemExit('--db-password or CSPULSE_DB_PASSWORD required')
    result = score_live_tenant(args.customer_id, args.ground_truth, args.db_password, args.db_port)
    print(json.dumps(result, indent=2, default=str))
