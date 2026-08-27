"""PC-stable + FCI causal discovery — ported from
~/Downloads/cspulse-work-new-by-cc/reference-code/causal_discovery_proto.py
(fix-load-generator-prompt-v2.md: "causal_discovery_proto.py already
implements most structure-recovery scoring against a hardcoded DAG. Adapt it
to read ground_truth.json rather than rewriting it.")

This module is the "rather than rewriting it" half — the algorithm core
(g_square, pc_skeleton, orient_vstructures, meek_rules, run_pc,
possible_d_sep, run_fci) is ported VERBATIM from the reference script, not
reimplemented, because re-deriving a constraint-based discovery algorithm's
math from scratch is exactly the kind of place a subtle, hard-to-notice bug
belongs. score_run.py is the genuinely new half: it builds the data matrix
from a generated eval-profile tenant's real CSVs + ground_truth.json instead
of the reference script's own generate()/build_true_dag()/hardcoded truth.

Implementation honesty (unchanged from the source): PC-stable is a faithful
implementation (Colombo & Maathuis order-independent skeleton, v-structures,
Meek R1-R3). FCI is PARTIAL — skeleton + Possible-D-SEP pruning + R0/R1
orientation only, no discriminating paths (R4) or R2/R3/R5-R10. Sufficient to
demonstrate latent-confounder marking; not a validated implementation. For
production use causal-learn or Tetrad.
"""
import itertools
from collections import deque

import numpy as np
from scipy.stats import chi2


def g_square(X, x, y, S, alpha):
    """Return (p_value, independent?) for X_x _||_ X_y | X_S. Binary data."""
    n = X.shape[0]
    if len(S) == 0:
        strata = [np.ones(n, dtype=bool)]
    else:
        cols = X[:, list(S)]
        codes = np.zeros(n, dtype=np.int64)
        for j in range(cols.shape[1]):
            codes = codes * 2 + cols[:, j]
        strata = [codes == c for c in np.unique(codes)]

    g, df = 0.0, 0
    for m in strata:
        ns = int(m.sum())
        if ns < 5:
            continue
        xv, yv = X[m, x], X[m, y]
        obs = np.zeros((2, 2), dtype=float)
        for a in (0, 1):
            for b in (0, 1):
                obs[a, b] = np.sum((xv == a) & (yv == b))
        rows, colsum = obs.sum(1), obs.sum(0)
        if np.any(rows == 0) or np.any(colsum == 0):
            continue
        exp = np.outer(rows, colsum) / ns
        nz = obs > 0
        g += 2.0 * np.sum(obs[nz] * np.log(obs[nz] / exp[nz]))
        df += 1
    if df == 0:
        return 1.0, True
    p = float(chi2.sf(g, df))
    return p, p > alpha


def pc_skeleton(X, alpha, max_k):
    """Order-independent (stable) skeleton. Colombo & Maathuis."""
    p = X.shape[1]
    adj = {i: set(range(p)) - {i} for i in range(p)}
    sep = {}
    ntests = 0
    k = 0
    while k <= max_k:
        snapshot = {i: set(adj[i]) for i in adj}
        progressed = False
        for i in range(p):
            for j in sorted(adj[i]):
                if j not in adj[i]:
                    continue
                cand = sorted(snapshot[i] - {j})
                if len(cand) < k:
                    continue
                progressed = True
                for Sset in itertools.combinations(cand, k):
                    ntests += 1
                    _pv, indep = g_square(X, i, j, Sset, alpha)
                    if indep:
                        adj[i].discard(j); adj[j].discard(i)
                        sep[(i, j)] = set(Sset); sep[(j, i)] = set(Sset)
                        break
        if not progressed:
            break
        k += 1
    return adj, sep, ntests


def orient_vstructures(adj, sep, marks):
    """X *-> Z <-* Y for unshielded triples where Z is not in sepset(X,Y)."""
    found = []
    for z in adj:
        for x, y in itertools.combinations(sorted(adj[z]), 2):
            if y in adj[x]:
                continue
            if z not in sep.get((x, y), set()):
                marks[(x, z)] = ">"
                marks[(y, z)] = ">"
                found.append((x, z, y))
    return found


def meek_rules(adj, marks):
    """R1-R3. Operates on CPDAG marks: '-' tail, '>' arrowhead."""
    def directed(a, b):
        return marks.get((a, b)) == ">" and marks.get((b, a)) == "-"

    def undirected(a, b):
        return marks.get((a, b)) == "-" and marks.get((b, a)) == "-"

    changed = True
    while changed:
        changed = False
        for b in adj:
            for c in sorted(adj[b]):
                if not undirected(b, c):
                    continue
                for a in adj[b]:
                    if a != c and directed(a, b) and c not in adj[a]:
                        marks[(b, c)] = ">"; changed = True; break
                if not undirected(b, c):
                    continue
                for x in adj[b]:
                    if x != c and directed(b, x) and directed(x, c):
                        marks[(b, c)] = ">"; changed = True; break
                if not undirected(b, c):
                    continue
                cand = [a for a in adj[b] if a != c and undirected(b, a) and directed(a, c)]
                done = False
                for a, d in itertools.combinations(cand, 2):
                    if d not in adj[a]:
                        marks[(b, c)] = ">"; changed = True; done = True; break
                if done:
                    continue
    return marks


def run_pc(X, alpha, max_k):
    adj, sep, ntests = pc_skeleton(X, alpha, max_k)
    marks = {}
    for i in adj:
        for j in adj[i]:
            marks[(i, j)] = "-"
    vs = orient_vstructures(adj, sep, marks)
    meek_rules(adj, marks)
    return adj, sep, marks, vs, ntests


def possible_d_sep(adj, marks, a):
    """V is in PDS(a) if a path a..V exists where every consecutive triple
    <W,Z,U> has Z a collider on the path, or <W,Z,U> forms a triangle."""
    out, seen = set(), set()
    q = deque((a, b) for b in adj[a])
    seen |= set(q)
    while q:
        prev, node = q.popleft()
        out.add(node)
        for nxt in adj[node]:
            if nxt == prev:
                continue
            triangle = nxt in adj[prev]
            collider = marks.get((prev, node)) == ">" and marks.get((nxt, node)) == ">"
            if (triangle or collider) and (node, nxt) not in seen:
                seen.add((node, nxt)); q.append((node, nxt))
    out.discard(a)
    return out


def run_fci(X, alpha, max_k):
    adj, sep, ntests = pc_skeleton(X, alpha, max_k)
    marks = {}
    for i in adj:
        for j in adj[i]:
            marks[(i, j)] = "o"
    orient_vstructures(adj, sep, marks)

    removed = []
    for i in list(adj):
        for j in sorted(adj[i]):
            if j not in adj[i]:
                continue
            pds = sorted((possible_d_sep(adj, marks, i) | possible_d_sep(adj, marks, j)) - {i, j})
            if not pds:
                continue
            for k in range(0, min(max_k, len(pds)) + 1):
                hit = False
                for Sset in itertools.combinations(pds, k):
                    ntests += 1
                    _pv, indep = g_square(X, i, j, Sset, alpha)
                    if indep:
                        adj[i].discard(j); adj[j].discard(i)
                        sep[(i, j)] = set(Sset); sep[(j, i)] = set(Sset)
                        removed.append((i, j)); hit = True; break
                if hit:
                    break

    marks = {}
    for i in adj:
        for j in adj[i]:
            marks[(i, j)] = "o"
    vs = orient_vstructures(adj, sep, marks)

    changed = True
    while changed:
        changed = False
        for b in list(adj):
            for c in sorted(adj[b]):
                if marks.get((b, c)) == "o" and marks.get((c, b)) == "o":
                    for a in adj[b]:
                        if a != c and marks.get((a, b)) == ">" and c not in adj[a]:
                            marks[(b, c)] = ">"; marks[(c, b)] = "-"
                            changed = True
                            break
    return adj, sep, marks, vs, ntests, removed


def bootstrap_stability(X, names, alpha, max_k, B, seed=11):
    """Per-edge presence rate across B bootstrap resamples of the PC skeleton.
    Returns {(name_i, name_j): rate}."""
    n = X.shape[0]
    rng = np.random.default_rng(seed)
    counts = {}
    for _ in range(B):
        idx = rng.integers(0, n, size=n)
        Xb = X[idx]
        adj, _sep, _nt = pc_skeleton(Xb, alpha, max_k)
        for i in adj:
            for j in adj[i]:
                if i < j:
                    key = (names[i], names[j])
                    counts[key] = counts.get(key, 0) + 1
    return {k: v / B for k, v in counts.items()}
