"""Build the TRUE event sequence from a world's DAG, then apply observation
dropout — in that order (fix-load-generator-prompt-v2.md, "GENERATION ORDER").

If a generator only ever creates observed events, there are no hidden events
for the unobserved_intermediate absences to reference and §4 becomes
decorative. This module always generates the full TRUE set first; dropout is
a second, explicit pass over it, and every drop is recorded.

Determinism: every random draw comes from a random.Random(seed) derived per
(account_idx, edge_id) — never the global `random` module (see commit
951d9f380 for why that class of bug is easy to introduce and hard to notice).
"""
from __future__ import annotations

import random
import zlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta


DEFAULT_OBSERVATION_RATE = 0.7
# Per-type overrides layered on top of the global rate. Matches the real
# asymmetry the prompt calls out: incidents get logged, disengagement doesn't.
DEFAULT_PER_TYPE_OBSERVATION_RATE = {
    'expansion_review_cancelled': 0.15,
    'usage_decline': 0.15,
}


def _rng_for(seed: int, *parts) -> random.Random:
    key = seed
    for p in parts:
        key += zlib.crc32(str(p).encode())
    return random.Random(key)


@dataclass
class TrueEvent:
    account_idx: int
    event_type: str
    timestamp: datetime
    edge_id: str | None      # which DAG edge produced this event (None for a root)
    source_system: str | None
    observed: bool = True
    drop_reason: str | None = None


@dataclass
class Account:
    account_idx: int
    archetype_id: str
    arr: float
    true_events: list = field(default_factory=list)


def _pick_archetype(world: dict, rng: random.Random) -> dict:
    archetypes = world['account_archetypes']
    weights = [a['weight'] for a in archetypes]
    return rng.choices(archetypes, weights=weights, k=1)[0]


def _edges_by_id(world: dict) -> dict:
    return {e['edge_id']: e for e in world['dag']}


def generate_accounts(world: dict, seed: int, account_count: int,
                       start_date: datetime) -> list[Account]:
    """Instantiate account_count accounts by weighted archetype sampling,
    then walk each account's active DAG edges to build its TRUE event chain.
    A latent edge's 'from' is a hidden variable — it never emits an event
    itself, but its (deterministic, seeded) activation gates whether BOTH
    downstream latent-edges for that account fire, producing the correlated
    endpoints a latent common cause implies."""
    edges = _edges_by_id(world)
    accounts = []

    for idx in range(account_count):
        acct_rng = _rng_for(seed, 'account', idx)
        archetype = _pick_archetype(world, acct_rng)
        arr = acct_rng.uniform(*archetype['arr_range'])
        acct = Account(account_idx=idx, archetype_id=archetype['archetype_id'], arr=round(arr, 2))

        # Group this archetype's active edges by their root ('from' that is
        # never any other active edge's 'to' within this archetype, OR a
        # latent) so multi-hop chains anchor to one timestamp per chain.
        active = [edges[eid] for eid in archetype['active_edges']]
        tos = {e['to'] for e in active}
        latent_roots = {}  # latent name -> whether it fired for this account

        for e in active:
            is_root = e['from'] not in tos and 'latent_edge' not in e
            is_latent_edge = e.get('latent_edge', False)

            if is_latent_edge:
                latent = e['from']
                if latent not in latent_roots:
                    latent_rng = _rng_for(seed, 'latent', idx, latent)
                    latent_roots[latent] = latent_rng.random() < 0.85
                if not latent_roots[latent]:
                    continue
                anchor = start_date + timedelta(days=int(acct_rng.uniform(10, 40)))
                lag_rng = _rng_for(seed, 'edge', idx, e['edge_id'])
                lag = max(0.0, lag_rng.gauss(e['lag_days_mean'], e['lag_days_std']))
                ts = anchor + timedelta(days=lag)
                acct.true_events.append(TrueEvent(
                    account_idx=idx, event_type=e['to'], timestamp=ts,
                    edge_id=e['edge_id'], source_system=e.get('source_system'),
                ))
                continue

            if is_root:
                anchor_rng = _rng_for(seed, 'root', idx, e['from'])
                anchor = start_date + timedelta(days=int(anchor_rng.uniform(10, 40)))
                acct.true_events.append(TrueEvent(
                    account_idx=idx, event_type=e['from'], timestamp=anchor,
                    edge_id=None, source_system=e.get('source_system'),
                ))

        # Second pass: walk edges in declaration order, propagating from
        # whatever timestamp the 'from' type landed at for this account
        # (root or upstream edge output), respecting per-edge strength as
        # the probability the downstream event actually fires.
        by_type = {ev.event_type: ev for ev in acct.true_events}
        changed = True
        while changed:
            changed = False
            for e in active:
                if e.get('latent_edge') or e['to'] in by_type:
                    continue
                if e['from'] not in by_type:
                    continue
                fire_rng = _rng_for(seed, 'fire', idx, e['edge_id'])
                if fire_rng.random() > e['strength']:
                    continue
                lag_rng = _rng_for(seed, 'edge', idx, e['edge_id'])
                lag = max(0.0, lag_rng.gauss(e['lag_days_mean'], e['lag_days_std']))
                ts = by_type[e['from']].timestamp + timedelta(days=lag)
                new_ev = TrueEvent(
                    account_idx=idx, event_type=e['to'], timestamp=ts,
                    edge_id=e['edge_id'], source_system=e.get('source_system'),
                )
                acct.true_events.append(new_ev)
                by_type[e['to']] = new_ev
                changed = True

        accounts.append(acct)

    return accounts


def apply_dropout(accounts: list[Account], seed: int, observation_rate: float,
                   per_type_observation_rate: dict) -> None:
    """Second pass, explicit and separate from generation. Mutates each
    TrueEvent's .observed/.drop_reason in place. Root events (no edge_id) are
    always observed — a root with zero events isn't a data-quality problem to
    model, it's an account with nothing to say."""
    for acct in accounts:
        for ev in acct.true_events:
            if ev.edge_id is None:
                continue
            rate = per_type_observation_rate.get(ev.event_type, observation_rate)
            drop_rng = _rng_for(seed, 'dropout', acct.account_idx, ev.event_type)
            # observed with probability `rate` — AT-3 caught this inverted
            # (was `>= rate`, which made HIGHER observation_rate produce
            # FEWER observed events; observed counts rose as the rate fell).
            if drop_rng.random() < rate:
                ev.observed = True
            else:
                ev.observed = False
                ev.drop_reason = 'per_type_observation_rate'


def apply_lag_window(accounts: list[Account], world: dict) -> None:
    """Mark events reached only via an edge whose TRUE lag exceeds
    admission_lag_window_days as observed-but-inadmissible — the platform
    would see the event, just not within the window the admission function
    checks. This is a separate concept from dropout: the data exists, the
    window excludes it."""
    window = world.get('admission_lag_window_days', 30)
    edges = _edges_by_id(world)
    for acct in accounts:
        by_type = {ev.event_type: ev for ev in acct.true_events}
        for ev in acct.true_events:
            if ev.edge_id is None:
                continue
            edge = edges[ev.edge_id]
            if edge['from'] in by_type and edge.get('latent_edge') is not True:
                from_ev = by_type[edge['from']]
                true_lag = (ev.timestamp - from_ev.timestamp).days
                if true_lag > window:
                    ev.drop_reason = ev.drop_reason or 'beyond_lag_window'
