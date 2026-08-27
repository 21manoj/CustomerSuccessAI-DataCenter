"""Scoring harness for a generated eval-profile tenant (fix-load-generator-
prompt-v2.md: "Provide score_run.py taking a generated tenant plus
ground_truth.json, reporting per spec section 3, plus: abstention-reason
accuracy against the absence taxonomy, and the revenue-to-ARR ratio per
account.")

Implements the two scoring dimensions computable purely from generated data
+ discovery.py's PC/FCI (Structure recovery, Template comparison). The other
three dimensions in generator-ground-truth-spec.md section 3 — Provenance
discipline (evidence_tier), Abstention (did the LIVE system decline or
force), Coverage estimation (the LIVE system's own coverage estimate) — score
the PLATFORM's actual behavior on uploaded data, not the generator's output,
and need infrastructure that doesn't exist yet (WS-2 2a's data_origin schema,
Wizard A's abstention mechanism). Their scoring FUNCTIONS are stubbed below
with the shape they'll need, not faked with placeholder numbers.
"""
import csv
import json
from pathlib import Path

import numpy as np

import discovery


def _load_tenant(tenant_dir: str):
    tenant_dir = Path(tenant_dir)
    with open(tenant_dir / 'ground_truth.json') as f:
        gt = json.load(f)
    signals = list(csv.DictReader(open(tenant_dir / 'qualitative_signals.csv')))
    outcomes = list(csv.DictReader(open(tenant_dir / 'outcomes.csv')))
    accounts = list(csv.DictReader(open(tenant_dir / 'account_details.csv')))
    return gt, signals, outcomes, accounts


def build_presence_matrix(gt: dict, signals: list, outcomes: list, accounts: list):
    """One row per account, one column per observed_vocabulary event type,
    binary presence indicator. This is the g_square-compatible data shape
    discovery.py's PC/FCI expect."""
    account_ids = sorted({int(a['source_account_id']) for a in accounts})
    idx_of = {aid: i for i, aid in enumerate(account_ids)}

    all_types = set()
    for row in signals + outcomes:
        key = 'signal_type' if 'signal_type' in row else 'outcome_type'
        all_types.add(row[key])
    names = sorted(all_types)
    name_idx = {n: i for i, n in enumerate(names)}

    X = np.zeros((len(account_ids), len(names)), dtype=np.int64)
    for row in signals:
        aid, t = int(row['source_account_id']), row['signal_type']
        X[idx_of[aid], name_idx[t]] = 1
    for row in outcomes:
        aid, t = int(row['source_account_id']), row['outcome_type']
        X[idx_of[aid], name_idx[t]] = 1
    return X, names, account_ids


def score_structure_recovery(gt: dict, X, names, alpha=0.05, max_k=3):
    """Adjacency precision/recall/F1 vs true_dag, orientation correctness,
    and whether FCI (not PC) correctly marks each latent-confounded pair."""
    name_idx = {n: i for i, n in enumerate(names)}
    true_edges = set()
    for e in gt['dag']:
        if e.get('latent_edge'):
            continue  # latent's endpoint is never itself an observed variable
        if e['from'] in name_idx and e['to'] in name_idx:
            true_edges.add(frozenset((name_idx[e['from']], name_idx[e['to']])))

    pc_adj, pc_sep, pc_marks, pc_vs, _ = discovery.run_pc(X, alpha, max_k)
    fci_adj, fci_sep, fci_marks, fci_vs, _, fci_removed = discovery.run_fci(X, alpha, max_k)

    def edge_set(adj):
        out = set()
        for i in adj:
            for j in adj[i]:
                out.add(frozenset((i, j)))
        return out

    pc_edges = edge_set(pc_adj)
    tp = len(pc_edges & true_edges)
    fp = len(pc_edges - true_edges)
    fn = len(true_edges - pc_edges)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    confounded_pairs = []
    for absence in gt['absences']:
        if absence['kind'] != 'latent_common_cause':
            continue
        a_type, b_type = absence['pair']
        if a_type not in name_idx or b_type not in name_idx:
            continue
        ai, bi = name_idx[a_type], name_idx[b_type]
        pc_asserts_direct = frozenset((ai, bi)) in pc_edges
        fci_marks_it = frozenset((ai, bi)) in edge_set(fci_adj) or frozenset((ai, bi)) in fci_removed
        confounded_pairs.append({
            'pair': [a_type, b_type],
            'pc_asserted_direct_edge': pc_asserts_direct,   # AT-2: should be True (PC's blind spot)
            'fci_flagged_or_removed': fci_marks_it,
        })

    return {
        'adjacency_precision': round(precision, 4),
        'adjacency_recall': round(recall, 4),
        'adjacency_f1': round(f1, 4),
        'true_edge_count': len(true_edges),
        'pc_edge_count': len(pc_edges),
        'confounded_pairs': confounded_pairs,
    }


def score_template_comparison(gt: dict, X, names, alpha=0.05, max_k=3):
    """Classify every declared template_disagreements entry as SUPPORTED /
    UNSUPPORTED / REVERSED / CONFOUNDED / UNTESTABLE against what PC actually
    recovered from this world's data — AT-1's literal check."""
    name_idx = {n: i for i, n in enumerate(names)}
    pc_adj, pc_sep, pc_marks, _, _ = discovery.run_pc(X, alpha, max_k)

    results = []
    for td in gt.get('template_disagreements', []):
        a_type, b_type = td['edge']
        if a_type not in name_idx or b_type not in name_idx:
            results.append({**td, 'verdict': 'UNTESTABLE'})
            continue
        ai, bi = name_idx[a_type], name_idx[b_type]
        adjacent = bi in pc_adj.get(ai, set())
        if not adjacent:
            verdict = 'UNSUPPORTED' if td['disagreement_type'] == 'reversed' else 'SUPPORTED'
        else:
            a_to_b = pc_marks.get((ai, bi)) == '>' and pc_marks.get((bi, ai)) == '-'
            b_to_a = pc_marks.get((bi, ai)) == '>' and pc_marks.get((ai, bi)) == '-'
            if td['disagreement_type'] == 'reversed':
                verdict = 'REVERSED' if b_to_a else ('SUPPORTED' if a_to_b else 'UNTESTABLE')
            else:
                verdict = 'SUPPORTED'
        results.append({**td, 'verdict': verdict})
    return results


def score_revenue_ratio_per_account(gt: dict, accounts: list):
    arr_by_account = {int(a['source_account_id']): float(a['arr'] or 0) for a in accounts}
    # outcomes.csv already carries the enforced dollars; re-derive per account.
    return {
        'per_account_bound': gt['revenue_model']['per_account_bound'],
        'portfolio_ratio_to_arr': gt['revenue_model']['ratio_to_arr'],
        'violations': gt['revenue_model']['violations'],
    }


def score_abstention_reason_accuracy_STUB(gt: dict):
    """AT-4b's scoring shape, forward-declared. Needs Wizard A's real
    abstention-with-reasons output for a LIVE tenant this data was uploaded
    to — not computable from the generator's own output alone. Returns the
    taxonomy this WOULD be scored against, so the function has a stable
    signature ready for whoever wires up the live half."""
    return {
        'status': 'BLOCKED — Wizard A abstention-with-reasons mechanism not built yet',
        'absence_taxonomy_to_score_against': [
            {'pair': a['pair'], 'kind': a['kind']} for a in gt['absences']
        ],
    }


def score_run(tenant_dir: str, alpha: float = 0.05, max_k: int = 3) -> dict:
    gt, signals, outcomes, accounts = _load_tenant(tenant_dir)
    X, names, account_ids = build_presence_matrix(gt, signals, outcomes, accounts)
    return {
        'world_id': gt['world_id'],
        'seed': gt['seed'],
        'n_accounts': len(account_ids),
        'n_variables': len(names),
        'structure_recovery': score_structure_recovery(gt, X, names, alpha, max_k),
        'template_comparison': score_template_comparison(gt, X, names, alpha, max_k),
        'revenue_ratio_per_account': score_revenue_ratio_per_account(gt, accounts),
        'abstention_reason_accuracy': score_abstention_reason_accuracy_STUB(gt),
    }


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Score a generated eval-profile tenant')
    parser.add_argument('--tenant-dir', required=True)
    parser.add_argument('--alpha', type=float, default=0.05)
    parser.add_argument('--max-k', type=int, default=3)
    args = parser.parse_args()
    result = score_run(args.tenant_dir, args.alpha, args.max_k)
    print(json.dumps(result, indent=2, default=str))
