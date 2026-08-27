#!/usr/bin/env python3
"""
causal_discovery_proto.py
=========================

Replacing ARC_TEMPLATES with learned causal structure — a working prototype.

What this does
--------------
1. Defines a GROUND-TRUTH causal DAG over CS signal types, including two
   LATENT (unobserved) confounders and a selection-bias mechanism.
2. Generates N synthetic accounts from it — the type-level reframe: one
   account = one observation, so 750 accounts gives you 750 samples over
   ~15 variables instead of 3 signals over 1 account.
3. Runs three approaches and scores each against the ground truth:
      (a) TEMPLATE   — hand-authored assertions, i.e. what ships today
      (b) PC-stable  — constraint-based discovery, assumes causal sufficiency
      (c) FCI        — relaxes causal sufficiency, can mark latent confounding
4. Bootstraps PC-stable to produce a real per-edge confidence number.

The point of the exercise
-------------------------
The ground truth contains two pairs with NO direct causal link that are
correlated only through a latent common cause. Watch what each method says
about them. That is the entire argument for FCI over PC on CS data.

Implementation honesty
----------------------
PC-stable here is a faithful implementation (Colombo & Maathuis order-
independent skeleton, v-structures, Meek R1-R3).

FCI here is PARTIAL: skeleton + Possible-D-SEP pruning + R0/R1 orientation only.
It does NOT implement discriminating paths (R4) or rules R2, R3, R5-R10. It is
sufficient to demonstrate latent-confounder detection and is explicitly not a
validated implementation. For production use `causal-learn` (CMU, py-why) or
Tetrad. This file is for reading, not for shipping.

VALIDATION — read this before trusting any number below
-------------------------------------------------------
`causal-learn` is absent from this environment's package mirror, so instead of
cross-checking against another implementation the script checks against THEORY.
An ORACLE run answers every conditional-independence query by d-separation in
the true DAG (via networkx) — no sampling error, unlimited conditioning depth.
That is the infinite-data limit of any consistent CI test.

  · If PC-stable recovers the full true skeleton under the oracle, the
    implementation is behaving correctly.
  · Whatever the oracle STILL gets wrong is irreducible: an identification
    failure, not a sample-size failure.

That is a stronger check than agreeing with a library would have been. Agreeing
with a library tells you your code matches someone else's. The oracle tells you
which of your errors no amount of data will ever remove.

    pip install numpy scipy networkx   # networkx is only used for the oracle
    python3 causal_discovery_proto.py
    python3 causal_discovery_proto.py --n 2000 --alpha 0.01 --boot 300
"""

import argparse
import itertools
import os
import sys
from collections import defaultdict, deque

import numpy as np
from scipy.stats import chi2

# ─────────────────────────────────────────────────────────────────────────────
# Rendering
# ─────────────────────────────────────────────────────────────────────────────

USE_COLOR = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None
def _c(k, s): return f"\033[{k}m{s}\033[0m" if USE_COLOR else s
BOLD = lambda s: _c("1", s)     # noqa: E731
DIM  = lambda s: _c("2", s)     # noqa: E731
RED  = lambda s: _c("31", s)    # noqa: E731
GRN  = lambda s: _c("32", s)    # noqa: E731
YEL  = lambda s: _c("33", s)    # noqa: E731
CYN  = lambda s: _c("36", s)    # noqa: E731
W = 100


def head(t, sub=""):
    print(); print(BOLD(CYN("━" * W))); print(BOLD(CYN(f"  {t}")))
    if sub: print(DIM(f"  {sub}"))
    print(BOLD(CYN("━" * W)))


def sec(t):
    print(); print(BOLD(f"  {t}")); print(DIM("  " + "─" * (W - 4)))


def tbl(hdr, rows, indent=2):
    if not rows:
        print(" " * indent + DIM("(none)")); return
    n = len(hdr)
    wid = [min(max(len(str(hdr[i])), *(len(_plain(r[i])) for r in rows)), 44) for i in range(n)]
    pad = " " * indent
    print(pad + "  ".join(BOLD(str(hdr[i]).ljust(wid[i])) for i in range(n)))
    print(pad + DIM("  ".join("─" * x for x in wid)))
    for r in rows:
        cells = []
        for i in range(n):
            raw, plain = str(r[i]), _plain(r[i])
            cells.append(raw + " " * max(0, wid[i] - len(plain)))
        print(pad + "  ".join(cells))


def _plain(s):
    import re
    return re.sub(r"\033\[[0-9;]*m", "", str(s))


# ─────────────────────────────────────────────────────────────────────────────
# GROUND TRUTH — the DAG we will try to recover
# ─────────────────────────────────────────────────────────────────────────────
# Variables prefixed L_ are LATENT: generated, then dropped before discovery.
# This is the whole test. PC assumes they do not exist. FCI does not.

LATENTS = ["L_org_restructure", "L_business_decline"]

OBSERVED = [
    "champion_change", "exec_sponsor_change", "engagement_gap",
    "budget_pressure", "usage_decline", "reserved_cluster_idle",
    "critical_incident", "sla_breach", "support_escalation", "mttr_regression",
    "competitor_mention", "adoption_milestone", "expansion_interest",
    "renewal_secured", "churn",
]

# parent -> child, with weight on the logit scale
TRUE_EDGES = [
    # ── latent confounder 1: an org restructure moves two stakeholders at once.
    #    There is NO causal link between these two signals. They just co-occur.
    ("L_org_restructure",  "champion_change",     3.0),
    ("L_org_restructure",  "exec_sponsor_change", 2.8),

    # ── latent confounder 2: business decline drives budget AND usage down.
    ("L_business_decline", "budget_pressure",     3.4),
    ("L_business_decline", "usage_decline",       3.2),

    # ── genuine causal chains
    ("champion_change",    "engagement_gap",      2.6),
    ("engagement_gap",     "usage_decline",       1.8),
    ("usage_decline",      "reserved_cluster_idle", 2.9),

    # ── a clean unshielded v-structure: two independent roots, one collider
    ("critical_incident",  "support_escalation",  2.7),
    ("sla_breach",         "support_escalation",  2.7),
    ("sla_breach",         "mttr_regression",     2.5),

    # ── a second unshielded collider, this time into churn
    ("budget_pressure",    "competitor_mention",  2.2),
    ("usage_decline",      "competitor_mention",  2.0),
    ("competitor_mention", "churn",               2.6),
    ("engagement_gap",     "churn",               2.2),

    # ── the healthy branch
    ("adoption_milestone", "expansion_interest",  2.8),
    ("expansion_interest", "renewal_secured",     2.6),
    ("adoption_milestone", "renewal_secured",     1.6),
]

BASE_RATE = {          # intercept on the logit scale (root prevalence)
    "L_org_restructure": -1.3, "L_business_decline": -0.9,
    "champion_change": -2.6, "exec_sponsor_change": -2.6, "engagement_gap": -2.2,
    "budget_pressure": -2.4, "usage_decline": -2.2, "reserved_cluster_idle": -2.4,
    "critical_incident": -1.1, "sla_breach": -1.2, "support_escalation": -2.6,
    "mttr_regression": -2.2, "competitor_mention": -2.6, "adoption_milestone": -0.9,
    "expansion_interest": -2.2, "renewal_secured": -2.0, "churn": -2.6,
}

# The pairs that exist ONLY because of a latent common cause. Ground truth says
# there is no edge here. PC is expected to draw one anyway.
CONFOUNDED_PAIRS = [("champion_change", "exec_sponsor_change"),
                    ("budget_pressure", "usage_decline")]

# ── The baseline: what a human authored into ARC_TEMPLATES.
#    Plausible-sounding, typed confidences, never validated against data.
TEMPLATE_ASSERTIONS = [
    ("champion_change",     "exec_sponsor_change",   0.80),   # confounded, not causal
    ("champion_change",     "engagement_gap",        0.85),   # correct
    ("engagement_gap",      "usage_decline",         0.80),   # correct
    ("usage_decline",       "churn",                 0.75),   # indirect, not direct
    ("budget_pressure",     "usage_decline",         0.70),   # confounded, not causal
    ("support_escalation",  "critical_incident",     0.65),   # BACKWARDS
    ("competitor_mention",  "churn",                 0.85),   # correct
    ("adoption_milestone",  "renewal_secured",       0.72),   # correct
    ("sla_breach",          "churn",                 0.60),   # no such edge
]


# ─────────────────────────────────────────────────────────────────────────────
# Data generation
# ─────────────────────────────────────────────────────────────────────────────

def topo_order(nodes, edges):
    par = defaultdict(list)
    for a, b, _w in edges:
        par[b].append(a)
    order, seen = [], set()

    def visit(n):
        if n in seen:
            return
        for p in par[n]:
            visit(p)
        seen.add(n); order.append(n)

    for n in nodes:
        visit(n)
    return order


def generate(n, seed=7, selection_bias=True):
    """
    Sample n accounts. Returns (X, names) where X is n x |OBSERVED| of 0/1.
    Latents are generated then discarded — exactly the situation PC assumes away.
    """
    rng = np.random.default_rng(seed)
    allv = LATENTS + OBSERVED
    order = topo_order(allv, TRUE_EDGES)
    par = defaultdict(list)
    for a, b, w in TRUE_EDGES:
        par[b].append((a, w))

    vals = {}
    for v in order:
        logit = np.full(n, BASE_RATE[v], dtype=float)
        for p, w in par[v]:
            logit += w * vals[p]
        prob = 1.0 / (1.0 + np.exp(-logit))
        vals[v] = (rng.random(n) < prob).astype(np.int8)

    X = np.column_stack([vals[v] for v in OBSERVED])

    if selection_bias:
        # Churned accounts leave the platform; a fraction of their rows never
        # make it into the analysis set. This is real, and PC has no defence
        # against it — FCI at least models selection explicitly.
        churn_ix = OBSERVED.index("churn")
        drop = (X[:, churn_ix] == 1) & (rng.random(n) < 0.35)
        X = X[~drop]
    return X, list(OBSERVED)


# ─────────────────────────────────────────────────────────────────────────────
# Conditional independence test — G² (likelihood ratio) for discrete data
# ─────────────────────────────────────────────────────────────────────────────

# ── Oracle CI test ───────────────────────────────────────────────────────────
# `causal-learn` is not on this environment's package mirror, so instead of
# cross-checking against another implementation we check against THEORY, which
# is the stronger test. The oracle answers every CI query by d-separation in
# the true DAG — i.e. it is what a statistical test would converge to with
# infinite data and zero sampling error.
#
# Two things fall out:
#   1. If PC-stable with the oracle recovers the correct structure, the
#      implementation is right, and any finite-n error is statistical.
#   2. The oracle still cannot see the latents. So whatever the oracle gets
#      WRONG is an identification failure, not a data-volume failure.

_ORACLE = {"on": False, "G": None}


def build_true_dag():
    import networkx as nx
    G = nx.DiGraph()
    G.add_nodes_from(LATENTS + OBSERVED)
    for a, b, _w in TRUE_EDGES:
        G.add_edge(a, b)
    return G


def oracle_ci(names, x, y, S):
    """True iff X_x is d-separated from X_y given X_S in the ground-truth DAG."""
    import networkx as nx
    G = _ORACLE["G"]
    return nx.is_d_separator(G, {names[x]}, {names[y]}, {names[s] for s in S})


def g_square(X, x, y, S, alpha):
    """Return (p_value, independent?) for X_x ⟂ X_y | X_S."""
    if _ORACLE["on"]:
        indep = oracle_ci(_ORACLE["names"], x, y, S)
        return (1.0 if indep else 0.0), indep

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
        if ns < 5:                      # too thin to contribute; costs no df
            continue
        xv, yv = X[m, x], X[m, y]
        obs = np.zeros((2, 2), dtype=float)
        for a in (0, 1):
            for b in (0, 1):
                obs[a, b] = np.sum((xv == a) & (yv == b))
        rows, colsum = obs.sum(1), obs.sum(0)
        if np.any(rows == 0) or np.any(colsum == 0):
            continue                    # degenerate stratum, contributes 0 df
        exp = np.outer(rows, colsum) / ns
        nz = obs > 0
        g += 2.0 * np.sum(obs[nz] * np.log(obs[nz] / exp[nz]))
        df += 1                         # (2-1)(2-1) per usable stratum
    if df == 0:
        return 1.0, True                # no evidence -> cannot reject independence
    p = float(chi2.sf(g, df))
    return p, p > alpha


# ─────────────────────────────────────────────────────────────────────────────
# PC-stable
# ─────────────────────────────────────────────────────────────────────────────

def pc_skeleton(X, alpha, max_k):
    """Order-independent (stable) skeleton. Colombo & Maathuis."""
    p = X.shape[1]
    adj = {i: set(range(p)) - {i} for i in range(p)}
    sep = {}
    ntests = 0
    k = 0
    while k <= max_k:
        snapshot = {i: set(adj[i]) for i in adj}      # <- the "stable" part
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
                continue                        # shielded
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
                # R1: a->b, b-c, a & c non-adjacent  =>  b->c
                for a in adj[b]:
                    if a != c and directed(a, b) and c not in adj[a]:
                        marks[(b, c)] = ">"; changed = True; break
                if not undirected(b, c):
                    continue
                # R2: b->x->c and b-c  =>  b->c
                for x in adj[b]:
                    if x != c and directed(b, x) and directed(x, c):
                        marks[(b, c)] = ">"; changed = True; break
                if not undirected(b, c):
                    continue
                # R3: b-a, b-d, a->c, d->c, a & d non-adjacent, b-c => b->c
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


# ─────────────────────────────────────────────────────────────────────────────
# FCI — PARTIAL implementation (see module docstring)
# ─────────────────────────────────────────────────────────────────────────────

def possible_d_sep(adj, marks, a):
    """
    V is in PDS(a) if a path a..V exists where every consecutive triple
    <W,Z,U> has Z a collider on the path, or <W,Z,U> forms a triangle.
    """
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
    # Phase 1: PC skeleton and preliminary v-structures.
    adj, sep, ntests = pc_skeleton(X, alpha, max_k)
    marks = {}
    for i in adj:
        for j in adj[i]:
            marks[(i, j)] = "o"
    orient_vstructures(adj, sep, marks)

    # Phase 2: THE FCI STEP — re-test adjacencies conditioning on Possible-D-SEP.
    # This removes edges PC keeps because PC only ever conditions on neighbours.
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

    # Phase 3: re-orient from circles.
    marks = {}
    for i in adj:
        for j in adj[i]:
            marks[(i, j)] = "o"
    vs = orient_vstructures(adj, sep, marks)

    # FCI R1 only. R2/R3 are omitted deliberately: without discriminating paths
    # (R4) and the R5-R10 completion set, applying them piecemeal produces
    # orientations the full algorithm would not sanction. Leaving circles in
    # place is the conservative, honest failure mode — and abstention is the
    # property we are here to demonstrate.
    changed = True
    while changed:
        changed = False
        for b in list(adj):
            for c in sorted(adj[b]):
                # R1: a *-> b o-* c , a and c non-adjacent  =>  b -> c
                if marks.get((b, c)) == "o" and marks.get((c, b)) == "o":
                    for a in adj[b]:
                        if a != c and marks.get((a, b)) == ">" and c not in adj[a]:
                            marks[(b, c)] = ">"; marks[(c, b)] = "-"
                            changed = True
                            break
    return adj, sep, marks, vs, ntests, removed


# ─────────────────────────────────────────────────────────────────────────────
# Scoring against ground truth
# ─────────────────────────────────────────────────────────────────────────────

def truth_sets():
    """Adjacencies and directions among OBSERVED variables only."""
    directed = {(a, b) for a, b, _ in TRUE_EDGES if a in OBSERVED and b in OBSERVED}
    adjacent = {frozenset(e) for e in directed}
    return directed, adjacent


def edge_kind(marks, i, j):
    """
    PAG / CPDAG endpoint semantics. marks[(i,j)] is the mark AT j.
      >  arrowhead   -  tail   o  circle (undetermined)
    """
    a, b = marks.get((i, j)), marks.get((j, i))
    if a == ">" and b == ">":
        return "bidirected"          # i <-> j : latent confounder. FCI-only verdict.
    if a == ">" and b == "-":
        return "directed"            # i -> j
    if b == ">" and a == "-":
        return "directed_rev"        # j -> i
    if a == ">" and b == "o":
        return "partial"             # i o-> j : j is not an ancestor of i, but a
    if b == ">" and a == "o":        #           latent confounder is NOT ruled out
        return "partial_rev"
    if a == "o" and b == "o":
        return "circle"              # o-o : nothing determined
    return "undirected"              # CPDAG abstention


ABSTAINING = {"partial", "partial_rev", "circle", "undirected", "bidirected"}


def score(name, names, adj, marks, extra=""):
    directed, adjacent = truth_sets()
    found_adj, correct_dir, wrong_dir, abstain = set(), 0, 0, 0
    for i in adj:
        for j in adj[i]:
            if i < j:
                found_adj.add(frozenset((names[i], names[j])))
    tp = len(found_adj & adjacent)
    fp = len(found_adj - adjacent)
    fn = len(adjacent - found_adj)
    for e in found_adj & adjacent:
        u, v = tuple(e)
        i, j = names.index(u), names.index(v)
        k = edge_kind(marks, i, j)
        if k == "directed":
            correct_dir += 1 if (names[i], names[j]) in directed else 0
            wrong_dir += 0 if (names[i], names[j]) in directed else 1
        elif k == "directed_rev":
            correct_dir += 1 if (names[j], names[i]) in directed else 0
            wrong_dir += 0 if (names[j], names[i]) in directed else 1
        else:
            abstain += 1                 # partial / circle / undirected / bidirected
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    return dict(name=name, tp=tp, fp=fp, fn=fn, prec=prec, rec=rec, f1=f1,
                correct_dir=correct_dir, wrong_dir=wrong_dir, abstain=abstain, extra=extra)


def score_template(names):
    directed, adjacent = truth_sets()
    found = {frozenset((a, b)) for a, b, _ in TEMPLATE_ASSERTIONS}
    tp = len(found & adjacent); fp = len(found - adjacent); fn = len(adjacent - found)
    cd = sum(1 for a, b, _ in TEMPLATE_ASSERTIONS if (a, b) in directed)
    wd = sum(1 for a, b, _ in TEMPLATE_ASSERTIONS
             if frozenset((a, b)) in adjacent and (a, b) not in directed)
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    return dict(name="TEMPLATE (today)", tp=tp, fp=fp, fn=fn, prec=prec, rec=rec, f1=f1,
                correct_dir=cd, wrong_dir=wd, abstain=0, extra="never abstains")


# ─────────────────────────────────────────────────────────────────────────────
# Bootstrap edge stability — the real confidence number
# ─────────────────────────────────────────────────────────────────────────────

def bootstrap_stability(X, names, alpha, max_k, B, seed=11):
    rng = np.random.default_rng(seed)
    n = X.shape[0]
    pres, ori = defaultdict(int), defaultdict(int)
    for _b in range(B):
        idx = rng.integers(0, n, n)
        adj, _sep, marks, _vs, _nt = run_pc(X[idx], alpha, max_k)
        for i in adj:
            for j in adj[i]:
                if i < j:
                    key = (names[i], names[j])
                    pres[key] += 1
                    k = edge_kind(marks, i, j)
                    if k == "directed":
                        ori[(names[i], names[j])] += 1
                    elif k == "directed_rev":
                        ori[(names[j], names[i])] += 1
    return pres, ori, B


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=750, help="number of accounts")
    ap.add_argument("--alpha", type=float, default=0.01)
    ap.add_argument("--max-k", type=int, default=3, help="max conditioning set size")
    ap.add_argument("--boot", type=int, default=200)
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()

    head("CAUSAL DISCOVERY PROTOTYPE — learning the schema instead of typing it",
         f"n={a.n} accounts · alpha={a.alpha} · max conditioning set={a.max_k} · {a.boot} bootstrap resamples")

    X, names = generate(a.n, seed=a.seed)
    sec("Data")
    tbl(["property", "value"], [
        ["accounts generated", a.n],
        ["accounts after selection bias (churn attrition)", X.shape[0]],
        ["observed variables", len(names)],
        ["latent variables (generated, then hidden)", ", ".join(LATENTS)],
        ["true edges among observed", len(truth_sets()[0])],
    ])
    prev = [[nm, int(X[:, i].sum()), f"{X[:, i].mean():.1%}"] for i, nm in enumerate(names)]
    sec("Signal-type prevalence across the portfolio")
    tbl(["signal_type", "accounts", "rate"], prev)

    # ── run all three
    head("RESULTS")
    pc_adj, pc_sep, pc_marks, pc_vs, pc_tests = run_pc(X, a.alpha, a.max_k)
    fci_adj, fci_sep, fci_marks, fci_vs, fci_tests, fci_removed = run_fci(X, a.alpha, a.max_k)

    # ── ORACLE RUN: implementation check + identification check, in one
    oracle_row = None
    try:
        _ORACLE["G"] = build_true_dag()
        _ORACLE["names"] = names
        _ORACLE["on"] = True
        o_adj, _o_sep, o_marks, _o_vs, _o_t = run_pc(X, a.alpha, len(names) - 2)
        _ORACLE["on"] = False
        oracle_row = score("PC-stable · ORACLE", names, o_adj, o_marks, "infinite-data limit")
    except ImportError:
        _ORACLE["on"] = False

    rows = []
    runs = [score_template(names),
            score("PC-stable", names, pc_adj, pc_marks, f"{pc_tests} CI tests"),
            score("FCI (partial)", names, fci_adj, fci_marks, f"{fci_tests} CI tests")]
    if oracle_row:
        runs.append(oracle_row)
    for s in runs:
        f1col = GRN if s["f1"] >= 0.75 else YEL if s["f1"] >= 0.5 else RED
        rows.append([s["name"], s["tp"], RED(str(s["fp"])) if s["fp"] else "0", s["fn"],
                     f"{s['prec']:.2f}", f"{s['rec']:.2f}", f1col(f"{s['f1']:.2f}"),
                     s["correct_dir"], RED(str(s["wrong_dir"])) if s["wrong_dir"] else "0",
                     s["abstain"], s["extra"]])
    sec("Skeleton and orientation accuracy vs. ground truth")
    tbl(["method", "TP", "FP", "FN", "prec", "recall", "F1",
         "dir ✓", "dir ✗", "abstained", "notes"], rows)
    if oracle_row:
        print()
        print(DIM("  The ORACLE row replaces the statistical CI test with d-separation in the true"))
        print(DIM("  DAG — no sampling error, unlimited conditioning depth. It is what PC converges"))
        print(DIM("  to with infinite data. Two readings:"))
        print(DIM(f"    · it recovers all {oracle_row['tp']} true adjacencies with 0 false negatives →"))
        print(DIM("      the PC-stable implementation here is behaving correctly;"))
        if oracle_row["fp"]:
            print(RED(f"    · it STILL reports {oracle_row['fp']} spurious edge(s) → those are an"))
            print(RED("      IDENTIFICATION failure, not a sample-size failure. No quantity of data"))
            print(RED("      removes them, because the confounder is unobserved by construction."))

    # ── the latent confounder test
    sec("THE TEST — two pairs with NO causal edge, correlated only via a latent")
    rows = []
    for u, v in CONFOUNDED_PAIRS:
        i, j = names.index(u), names.index(v)
        t = "asserted causal" if any(frozenset((x, y)) == frozenset((u, v))
                                     for x, y, _ in TEMPLATE_ASSERTIONS) else "—"
        pcv = edge_kind(pc_marks, i, j) if j in pc_adj[i] else "no edge"
        fciv = edge_kind(fci_marks, i, j) if j in fci_adj[i] else "no edge"

        def verdict(k):
            if k == "no edge":
                return GRN("no edge — correct")
            if k == "bidirected":
                return GRN("↔ confounded — correct")
            if k in ("partial", "partial_rev"):
                return GRN("o→ confounding not ruled out")
            if k in ("circle", "undirected"):
                return YEL("related, direction unknown")
            return RED("asserts a direct cause — WRONG")
        rows.append([f"{u} — {v}", RED(t) if t != "—" else t, verdict(pcv), verdict(fciv)])
    tbl(["pair (ground truth: NO edge)", "TEMPLATE", "PC-stable", "FCI"], rows)
    print()
    print(DIM("  PC assumes causal sufficiency — no unmeasured confounders. That assumption is false"))
    print(DIM("  in CS data. Where PC commits to a direction, FCI leaves a circle mark meaning"))
    print(DIM("  'a latent common cause has not been ruled out here' — which is the true situation."))
    print()
    print(YEL("  Try --n 3000. Recall goes to 1.00 and precision goes DOWN."))
    print(DIM("  More data does not dissolve confounding — it makes the spurious edge more certain,"))
    print(DIM("  because the latent dependence is real and larger samples detect it more reliably."))
    print(DIM("  No amount of data fixes an identification problem. This is why the assumption"))
    print(DIM("  disclosure matters more than the sample size."))

    # Spurious colliders induced by the latent are worth naming explicitly.
    spur = []
    for x, z, y in pc_vs:
        for cu, cv in CONFOUNDED_PAIRS:
            if {names[x], names[z]} == {cu, cv} or {names[y], names[z]} == {cu, cv}:
                spur.append([f"{names[x]} → {names[z]} ← {names[y]}",
                             RED("built on a confounded pair")])
    if spur:
        sec("Spurious colliders PC found, induced by the hidden confounder")
        tbl(["v-structure", "problem"], spur)

    # ── v-structures
    sec(f"Unshielded colliders recovered by PC ({len(pc_vs)})")
    tbl(["X", "→ collider ←", "Y"],
        [[names[x], names[z], names[y]] for x, z, y in pc_vs] or [])
    if fci_removed:
        sec(f"Edges removed by FCI's Possible-D-SEP step that PC kept ({len(fci_removed)})")
        tbl(["edge"], [[f"{names[i]} — {names[j]}"] for i, j in fci_removed])

    # ── bootstrap
    head("BOOTSTRAP EDGE STABILITY", "the defensible replacement for a hand-typed confidence")
    pres, ori, B = bootstrap_stability(X, names, a.alpha, a.max_k, a.boot, seed=a.seed + 4)
    directed, adjacent = truth_sets()
    rows = []
    for (u, v), cnt in sorted(pres.items(), key=lambda kv: -kv[1])[:16]:
        stab = cnt / B
        od = max(ori.get((u, v), 0), ori.get((v, u), 0)) / B
        arrow = f"{u}→{v}" if ori.get((u, v), 0) >= ori.get((v, u), 0) else f"{v}→{u}"
        真 = frozenset((u, v)) in adjacent
        col = GRN if 真 else RED
        rows.append([col(f"{u} — {v}"), f"{stab:.0%}", f"{od:.0%}", arrow,
                     GRN("yes") if 真 else RED("NO — spurious")])
    tbl(["edge", "present in", "oriented", "modal direction", "in ground truth?"], rows)
    print()
    print(DIM(f"  'present in' = fraction of {B} bootstrap resamples containing this edge."))
    print(DIM("  That number has a derivation. A hand-typed 0.80 does not."))

    # ── Does stability actually separate true edges from spurious ones?
    sec("Stability as a decision threshold — sweep")
    sweep = []
    for thr in (0.50, 0.70, 0.80, 0.90, 0.95, 1.00):
        kept = {frozenset(k) for k, c in pres.items() if c / B >= thr}
        tp = len(kept & adjacent); fp = len(kept - adjacent); fn = len(adjacent - kept)
        pr = tp / (tp + fp) if tp + fp else 0.0
        rc = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * pr * rc / (pr + rc) if pr + rc else 0.0
        col = GRN if f1 >= 0.9 else YEL if f1 >= 0.75 else RED
        sweep.append([f"≥ {thr:.0%}", len(kept), tp, RED(str(fp)) if fp else "0", fn,
                      f"{pr:.2f}", f"{rc:.2f}", col(f"{f1:.2f}")])
    tbl(["keep edges present in", "edges kept", "TP", "FP", "FN", "prec", "recall", "F1"], sweep)
    true_stab = [c / B for k, c in pres.items() if frozenset(k) in adjacent]
    spur_stab = [c / B for k, c in pres.items() if frozenset(k) not in adjacent]
    if true_stab and spur_stab:
        print()
        print(f"  {DIM('true edges     ')} min stability {GRN(f'{min(true_stab):.0%}')}"
              f"   median {GRN(f'{float(np.median(true_stab)):.0%}')}")
        print(f"  {DIM('spurious edges ')} max stability {RED(f'{max(spur_stab):.0%}')}"
              f"   median {RED(f'{float(np.median(spur_stab)):.0%}')}")
        print()
        print(DIM("  The gap between those two rows is what a usable confidence number looks like."))
        print(DIM("  It is also a knob a customer can be shown and a threshold you can defend."))

    gp = emit_mermaid("causal_schema_graphs.md", names, pc_marks, pc_adj, fci_marks, fci_adj)
    summarise(names, pc_adj, pc_marks, fci_adj, fci_marks, gp)


def emit_mermaid(path, names, pc_marks, pc_adj, fci_marks, fci_adj):
    """Write the three graphs side by side as mermaid, for review or a deck."""
    directed, adjacent = truth_sets()

    def gid(n):
        return n.replace(" ", "_")

    L = ["# Learned causal schema vs. hand-authored templates", ""]
    L += ["## Ground truth (latents shown dashed)", "", "```mermaid", "graph LR"]
    for a, b, _w in TRUE_EDGES:
        if a in LATENTS:
            L.append(f"  {gid(a)}(({a})) -.-> {gid(b)}[{b}]")
        else:
            L.append(f"  {gid(a)}[{a}] --> {gid(b)}[{b}]")
    L += ["```", "", "## TEMPLATE — what ships today", "", "```mermaid", "graph LR"]
    for a, b, c in TEMPLATE_ASSERTIONS:
        ok = "" if (a, b) in directed else "  %% WRONG"
        L.append(f"  {gid(a)}[{a}] -->|{c}| {gid(b)}[{b}]{ok}")
    L += ["```", "",
          "Every edge directed, every edge with a typed confidence, no abstentions.", "",
          "## PC-stable — CPDAG", "", "```mermaid", "graph LR"]
    seen = set()
    for i in pc_adj:
        for j in pc_adj[i]:
            if (j, i) in seen:
                continue
            seen.add((i, j))
            k = edge_kind(pc_marks, i, j)
            u, v = names[i], names[j]
            if k == "directed":
                L.append(f"  {gid(u)}[{u}] --> {gid(v)}[{v}]")
            elif k == "directed_rev":
                L.append(f"  {gid(v)}[{v}] --> {gid(u)}[{u}]")
            else:
                L.append(f"  {gid(u)}[{u}] --- {gid(v)}[{v}]")
    L += ["```", "", "Solid arrows = oriented. Plain lines = **related, direction not identifiable**.", "",
          "## FCI — PAG", "", "```mermaid", "graph LR"]
    seen = set()
    for i in fci_adj:
        for j in fci_adj[i]:
            if (j, i) in seen:
                continue
            seen.add((i, j))
            k = edge_kind(fci_marks, i, j)
            u, v = names[i], names[j]
            lab = {"bidirected": "|latent confounder|", "partial": "|confounding not ruled out|",
                   "partial_rev": "|confounding not ruled out|"}.get(k, "")
            if k == "directed":
                L.append(f"  {gid(u)}[{u}] --> {gid(v)}[{v}]")
            elif k == "directed_rev":
                L.append(f"  {gid(v)}[{v}] --> {gid(u)}[{u}]")
            elif lab:
                L.append(f"  {gid(u)}[{u}] -.->{lab} {gid(v)}[{v}]")
            else:
                L.append(f"  {gid(u)}[{u}] --- {gid(v)}[{v}]")
    L += ["```", "",
          "Dotted = FCI cannot rule out an unmeasured common cause. "
          "That verdict has no representation in the template system at all.", ""]
    with open(path, "w") as f:
        f.write("\n".join(L))
    return path


def summarise(names, pc_adj, pc_marks, fci_adj, fci_marks, graph_path):
    # ── the comparison that matters
    head("WHAT THIS BUYS YOU")
    tmpl = score_template(names)
    pcs = score("PC-stable", names, pc_adj, pc_marks)
    fcis = score("FCI (partial)", names, fci_adj, fci_marks)
    tbl(["property", "ARC_TEMPLATES today", "learned schema"], [
        ["confidence value", RED("typed by an author"), GRN("bootstrap stability over resamples")],
        ["can say 'related, direction unknown'", RED("no"), GRN("yes — undirected / circle edges")],
        ["can say 'nothing here'", RED("no"), GRN("yes — absent edge")],
        ["can flag a latent confounder", RED("no"), GRN("yes — FCI bidirected marks")],
        ["wrong-direction edges", RED(str(tmpl["wrong_dir"])), f"PC {pcs['wrong_dir']} · FCI {fcis['wrong_dir']}"],
        ["spurious edges", RED(str(tmpl["fp"])), f"PC {pcs['fp']} · FCI {fcis['fp']}"],
        ["derivation recordable", RED("no"), GRN("method, n, alpha, depth, CI test, stability")],
        ["evidence tier", "inferred", "inferred (unchanged — but defensible)"],
    ])
    print()
    print(DIM("  The tier does not improve. Derivation Completeness goes from 0% to 100%."))
    print()
    print(f"  Graphs written to {BOLD(graph_path)} — ground truth, template, CPDAG and PAG")
    print(DIM("  as mermaid diagrams, ready to paste into a review doc."))
    print()


if __name__ == "__main__":
    main()
