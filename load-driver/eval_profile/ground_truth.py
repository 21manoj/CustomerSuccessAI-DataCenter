"""Assemble ground_truth.json + run_manifest.json from a world + its
generated (and dropout-applied) accounts.

§5's two knobs with no prior generator support:
  distinct_sources  — the world models >1 source system per edge; computed
                       here as the count of unique source_system values
                       recorded across the edge's endpoint event types,
                       platform-wide (not per-instance — a source-system
                       assignment is a property of the world, not a draw).
  edge_stability     — bootstrap resampling over the generated accounts.
                       Defined here (no prior spec pinned an exact formula):
                       resample the eligible-account set with replacement,
                       B=200 times, each time computing the OBSERVED firing
                       rate of the edge among accounts whose archetype could
                       exhibit it; edge_stability = the mean of those B rates.
                       High when the edge reliably fires across resamples,
                       low when a handful of accounts are doing all the work.
                       Seeded — the exact resampling algorithm here is what
                       "the value it computed" refers to if this needs
                       reproducing later.
"""
import random
import zlib
from collections import defaultdict

from event_engine import Account, TrueEvent  # noqa: F401 (type hints only)


def _rng_for(seed: int, *parts) -> random.Random:
    key = seed
    for p in parts:
        key += zlib.crc32(str(p).encode())
    return random.Random(key)


def _edges_by_id(world: dict) -> dict:
    return {e['edge_id']: e for e in world['dag']}


def _distinct_sources_for_pair(world: dict, from_type: str, to_type: str) -> int:
    sources = set()
    for e in world['dag']:
        if e['from'] in (from_type, to_type) or e['to'] in (from_type, to_type):
            if e.get('source_system'):
                sources.add(e['source_system'])
    return max(len(sources), 1)


def _edge_stability(world: dict, accounts: list, edge_id: str, seed: int,
                     bootstrap_n: int = 200) -> float:
    eligible = [
        a for a in accounts
        if any(arche['archetype_id'] == a.archetype_id and edge_id in arche['active_edges']
               for arche in world['account_archetypes'])
    ]
    if not eligible:
        return 0.0

    rates = []
    for b in range(bootstrap_n):
        boot_rng = _rng_for(seed, 'bootstrap', edge_id, b)
        sample = [boot_rng.choice(eligible) for _ in eligible]
        observed_count = sum(
            1 for a in sample
            if any(ev.edge_id == edge_id and ev.observed for ev in a.true_events)
        )
        rates.append(observed_count / len(sample))
    return round(sum(rates) / len(rates), 4)


def _instances_for_edge(accounts: list, edge_id: str) -> list:
    out = []
    for a in accounts:
        for ev in a.true_events:
            if ev.edge_id == edge_id:
                out.append((a, ev))
    return out


def build_admission_inputs(world: dict, accounts: list, seed: int) -> dict:
    """One entry per (account, edge) OBSERVED instance where truth=REAL_EDGE,
    plus one entry per declared absence per account where the pair's
    endpoints both exist for that account's archetype (truth=NO_EDGE) — a
    ratchet fixture set needs negative examples, not just positives."""
    out = {}
    edges = _edges_by_id(world)

    for edge_id, edge in edges.items():
        instances = _instances_for_edge(accounts, edge_id)
        observed_instances = [(a, ev) for a, ev in instances if ev.observed]
        if not observed_instances:
            continue

        stability = _edge_stability(world, accounts, edge_id, seed)
        distinct_sources = _distinct_sources_for_pair(world, edge['from'], edge['to'])
        is_beyond_lag = any(ev.drop_reason == 'beyond_lag_window' for _, ev in instances)

        for acct, ev in observed_instances:
            by_type = {e2.event_type: e2 for e2 in acct.true_events}
            from_ev = by_type.get(edge['from'])
            lag_days = (ev.timestamp - from_ev.timestamp).days if from_ev else edge['lag_days_mean']
            key = f"{acct.account_idx}:{edge['from']}->{edge['to']}"
            out[key] = {
                'supporting_events': 1,
                'lag_days': lag_days,
                'separation_hours': lag_days * 24,
                'outcome_in_window': lag_days <= world.get('admission_lag_window_days', 30),
                'distinct_sources': distinct_sources,
                'edge_stability': stability,
                'truth': 'NO_EDGE' if is_beyond_lag else 'REAL_EDGE',
            }

    # Negative examples from declared absences: for each no_relationship /
    # latent_common_cause pair, emit a NO_EDGE fixture per account whose
    # archetype has BOTH endpoint types present as true (possibly unobserved)
    # events but with no direct edge connecting them in this world's DAG.
    vocab_edges_by_type_pair = {(e['from'], e['to']) for e in world['dag']}
    for absence in world['absences']:
        if absence['kind'] not in ('no_relationship', 'latent_common_cause'):
            continue
        a_type, b_type = absence['pair']
        if (a_type, b_type) in vocab_edges_by_type_pair or (b_type, a_type) in vocab_edges_by_type_pair:
            continue  # only a true non-edge counts as a negative example
        for acct in accounts:
            by_type = {e2.event_type: e2 for e2 in acct.true_events if e2.observed}
            if a_type in by_type and b_type in by_type:
                key = f"{acct.account_idx}:{a_type}->{b_type}"
                distinct_sources = _distinct_sources_for_pair(world, a_type, b_type)
                out[key] = {
                    'supporting_events': 0,
                    'lag_days': None,
                    'separation_hours': None,
                    'outcome_in_window': False,
                    'distinct_sources': distinct_sources,
                    'edge_stability': 0.0,
                    'truth': 'NO_EDGE',
                }
    return out


def build_absences_realized(world: dict, accounts: list) -> list:
    """Copy the world's declared absences through, augmented with concrete
    per-account evidence of what actually happened (which instances got
    dropped, for which accounts the latent fired, etc.) — not just the
    world-level declaration, but proof it was actually enacted."""
    realized = []
    for absence in world['absences']:
        entry = dict(absence)
        if absence['kind'] == 'unobserved_intermediate':
            hidden = absence['hidden_event']
            dropped_accounts = [
                a.account_idx for a in accounts
                for ev in a.true_events
                if ev.event_type == hidden and not ev.observed
            ]
            entry['dropped_for_accounts'] = dropped_accounts
            entry['dropped_instance_count'] = len(dropped_accounts)
        elif absence['kind'] == 'beyond_lag_window':
            beyond_accounts = [
                a.account_idx for a in accounts
                for ev in a.true_events
                if ev.drop_reason == 'beyond_lag_window'
            ]
            entry['realized_for_accounts'] = beyond_accounts
        realized.append(entry)
    return realized


def build_revenue_model(world: dict, accounts: list, outcome_dollars_by_account: dict) -> dict:
    """AT-8's invariant, enforced not just asserted: outcome_dollars_by_account
    values are expected to already be capped by the caller at
    per_account_bound x ARR (see csv_emitter.assign_outcome_dollars); this
    just reports the realized ratios so the cap is independently checkable."""
    bound = world['revenue_model']['per_account_bound']
    arr_total = sum(a.arr for a in accounts)
    dollars_total = sum(outcome_dollars_by_account.values())
    violations = [
        (a.account_idx, outcome_dollars_by_account.get(a.account_idx, 0.0), a.arr)
        for a in accounts
        if outcome_dollars_by_account.get(a.account_idx, 0.0) > bound * a.arr
    ]
    return {
        'account_arr_total': round(arr_total, 2),
        'outcome_dollars_total': round(dollars_total, 2),
        'ratio_to_arr': round(dollars_total / arr_total, 4) if arr_total else 0.0,
        'per_account_bound': bound,
        'note': world['revenue_model'].get('note', ''),
        'violations': violations,  # must be empty; AT-8 asserts this
    }


def build_ground_truth(world: dict, accounts: list, seed: int, knobs: dict,
                        outcome_dollars_by_account: dict) -> dict:
    # with_no_arc is a property of the DECLARED archetype (active_edges==[]),
    # not of what randomly happened to fire this run — an account whose
    # archetype has real edges that simply didn't probabilistically fire is a
    # different thing (weak/undeveloped story) from a true no-arc account
    # (AT-4's target), and conflating them would make with_no_arc's size vary
    # with the RNG instead of with the world's own archetype weights.
    no_arc_archetype_ids = {
        arche['archetype_id'] for arche in world['account_archetypes']
        if not arche['active_edges']
    }
    accounts_with_no_arc = [
        a.account_idx for a in accounts if a.archetype_id in no_arc_archetype_ids
    ]
    return {
        'world_id': world['world_id'],
        'vertical': world['vertical'],
        'seed': seed,
        'knobs': knobs,
        'dag': world['dag'],
        'latents': world.get('latents', []),
        'template_disagreements': world.get('template_disagreements', []),
        'absences': build_absences_realized(world, accounts),
        'admission_inputs': build_admission_inputs(world, accounts, seed),
        'revenue_model': build_revenue_model(world, accounts, outcome_dollars_by_account),
        'accounts': {
            'count': len(accounts),
            'with_no_arc': accounts_with_no_arc,
            'by_archetype': {
                arche['archetype_id']: [a.account_idx for a in accounts if a.archetype_id == arche['archetype_id']]
                for arche in world['account_archetypes']
            },
        },
        'data_origin': 'synthetic_eval_profile',
        # WS-2 2a: matches customers.data_origin, which cs_pulse_driver.py's
        # run_eval_profile() sets via register_customer(data_origin=...) for
        # any --register run (fix-load-generator-prompt-v2.md §7). Carried
        # here too so ground_truth.json is self-describing for scoring even
        # when a tenant was only generated to disk, never registered live.
    }


def build_run_manifest(world_id: str, seed: int, knobs: dict, generator_version: str) -> dict:
    return {
        'world_id': world_id,
        'generator_version': generator_version,
        'seed': seed,
        'knobs': knobs,
    }
