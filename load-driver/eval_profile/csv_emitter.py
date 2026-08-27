"""Convert observed (post-dropout) events into the SAME CSV shapes
process_data() already ingests — the canonical 4-file onboarding pattern
(account_details.csv, kpi_measurements.csv, qualitative_signals.csv,
outcomes.csv). No parallel path, no mock schema.

Revenue realism (§6 / AT-8) is enforced HERE, at write time — the generator
refuses to emit outcome dollars beyond the declared bound, rather than only
being caught by an external audit after the fact. utils/outcome_revenue_
plausibility (the tracer probe shipped 2026-08-25) stays as the independent
detection-side check; this is the prevention side.
"""
import csv
import io
import json
import random
import zlib
from pathlib import Path

_BACKEND_CONFIG = Path(__file__).resolve().parent.parent.parent / 'kpi-dashboard' / 'backend' / 'config'


def _load_kpi_catalog(vertical: str) -> dict:
    path = _BACKEND_CONFIG / f'{vertical}_kpi_catalog.json'
    with open(path) as f:
        return json.load(f)['kpis']


def _health_to_kpi_value(target_health: float, target_val: float, ranges: dict,
                          higher_is_better: bool) -> float:
    """Ported verbatim from scenarios/scenario_manifest.py's
    _health_to_kpi_value (same math the demo generator uses) — reverse-
    engineers a KPI value that scores approximately target_health through
    the real generic scorer, rather than a placeholder value the scorer
    can't interpret at all."""
    healthy = ranges.get('healthy', {})
    risk = ranges.get('risk', {})
    critical = ranges.get('critical', {})

    if not healthy or not risk:
        factor = 0.4 + 0.6 * (target_health / 100.0) ** 0.7
        if not higher_is_better:
            factor = 1.0 / factor
        return target_val * factor

    if higher_is_better:
        h_min = healthy.get('min', target_val * 0.8)
        h_max = healthy.get('max', target_val * 1.2)
        r_min = risk.get('min', target_val * 0.5)
        r_max = risk.get('max', h_min)
        c_min = critical.get('min', 0)
        c_max = critical.get('max', r_min)
        if target_health >= 70:
            t = (target_health - 70) / 30.0
            return h_min + t * (h_max - h_min)
        elif target_health >= 50:
            t = (target_health - 50) / 20.0
            return r_min + t * (r_max - r_min)
        else:
            t = target_health / 50.0
            return c_min + t * (c_max - c_min)
    else:
        h_min = healthy.get('min', target_val * 0.5)
        h_max = healthy.get('max', target_val)
        r_min = risk.get('min', h_max)
        r_max = risk.get('max', target_val * 1.5)
        c_min = critical.get('min', r_max)
        c_max = critical.get('max', target_val * 3.0)
        if target_health >= 70:
            t = (target_health - 70) / 30.0
            return h_max - t * (h_max - h_min)
        elif target_health >= 50:
            t = (target_health - 50) / 20.0
            return r_max - t * (r_max - r_min)
        else:
            t = target_health / 50.0
            return c_max - t * (c_max - c_min)


def emit_kpi_measurements_csv(world: dict, accounts: list, seed: int) -> str:
    """Real catalog KPI codes with values reverse-engineered from each
    account's archetype-derived target health, using the same
    _health_to_kpi_value math the demo generator uses — so the platform's
    generic scorer (utils/generic_scorer.score_account_health) actually has
    something to compute against, instead of a made-up code it can't match
    to any catalog entry (which silently produced health_score=0.0 for
    every account — caught live via reviewer feedback on customer_id=405,
    2026-08-27, not something this generator's own local tests could catch
    since they never exercise the live scorer)."""
    catalog = _load_kpi_catalog(world['vertical'])
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow([
        'source_account_id', 'kpi_code', 'kpi_name', 'pillar',
        'measured_at', 'value', 'target', 'weight', 'unit', 'status',
    ])
    for a in accounts:
        aid = _account_id(a.account_idx)
        archetype = next(ar for ar in world['account_archetypes']
                          if ar['archetype_id'] == a.archetype_id)
        n_edges = len(archetype['active_edges'])
        base_health = 78.0 if n_edges == 0 else max(20.0, 68.0 - n_edges * 11.0)
        health_rng = _rng_for(seed, 'target_health', a.account_idx)
        target_health = max(5.0, min(95.0, base_health + health_rng.uniform(-8, 8)))
        status = 'healthy' if target_health >= 70 else ('at_risk' if target_health >= 50 else 'critical')

        # Reviewer finding, live on eval-profile customer_id=405/406/407
        # (2026-08-27): pillar_scores were near-duplicate across P1/P2/P3/P4/
        # P6 (only P5 diverged). Root cause: every KPI in every pillar was
        # reverse-engineered from the SAME single account-level target_health
        # with no pillar- or KPI-level variance at all, so pillars trivially
        # converge to ~target_health regardless of pillar identity. Real
        # accounts don't move all pillars in lockstep — a per-pillar offset
        # (which pillar this account happens to be weak/strong in) plus a
        # smaller per-KPI offset (noise within a pillar) fixes this: pillars
        # diverge from each other, KPIs within a pillar still cluster.
        pillar_offsets = {}
        for kpi_code, meta in catalog.items():
            target_val = meta.get('target', {})
            target_val = target_val.get('value', 85.0) if isinstance(target_val, dict) else (target_val or 85.0)
            higher_is_better = meta.get('higher_is_better', True)
            pillar = meta.get('pillar', kpi_code.split('-')[0])

            if pillar not in pillar_offsets:
                pillar_rng = _rng_for(seed, 'pillar_jitter', a.account_idx, pillar)
                pillar_offsets[pillar] = pillar_rng.uniform(-10.0, 10.0)
            kpi_rng = _rng_for(seed, 'kpi_jitter', a.account_idx, kpi_code)
            kpi_offset = kpi_rng.uniform(-3.0, 3.0)
            effective_health = max(2.0, min(98.0, target_health + pillar_offsets[pillar] + kpi_offset))

            value = _health_to_kpi_value(effective_health, target_val, meta.get('ranges', {}), higher_is_better)
            w.writerow([
                aid, kpi_code, meta.get('name', kpi_code), pillar,
                '2026-01-01', round(value, 2), target_val, meta.get('weight_l1', 0.25),
                meta.get('unit', '%'), status,
            ])
    return out.getvalue()


def _rng_for(seed: int, *parts) -> random.Random:
    key = seed
    for p in parts:
        key += zlib.crc32(str(p).encode())
    return random.Random(key)


_POLARITY_SIGN = {'at_risk': -1, 'lost': -1, 'expansion': 1, 'protected': 1}
_POLARITY_MAGNITUDE = {'at_risk': (0.03, 0.12), 'lost': (0.05, 0.20),
                       'expansion': (0.02, 0.10), 'protected': (0.02, 0.08)}


def assign_outcome_dollars(world: dict, accounts: list, seed: int) -> dict:
    """One $ figure per (account, observed OUTCOME-type event), signed by
    polarity, magnitude drawn as a fraction of that account's ARR — then
    HARD-CAPPED so the account's total never exceeds per_account_bound x ARR
    (AT-8, enforced not just measured). Returns {account_idx: {event_id: $}}."""
    outcome_polarity = world['observed_vocabulary']['outcome_types']
    bound = world['revenue_model']['per_account_bound']
    by_account = {}

    for a in accounts:
        outcome_events = [ev for ev in a.true_events if ev.observed and ev.event_type in outcome_polarity]
        dollars = {}
        for ev in outcome_events:
            polarity = outcome_polarity[ev.event_type]
            sign = _POLARITY_SIGN[polarity]
            lo, hi = _POLARITY_MAGNITUDE[polarity]
            dollar_rng = _rng_for(seed, 'dollars', a.account_idx, ev.event_type)
            magnitude = dollar_rng.uniform(lo, hi) * a.arr
            dollars[id(ev)] = sign * magnitude

        total_abs = sum(abs(v) for v in dollars.values())
        cap = bound * a.arr
        if total_abs > cap and total_abs > 0:
            scale = cap / total_abs
            dollars = {k: v * scale for k, v in dollars.items()}

        by_account[a.account_idx] = dollars

    return by_account


def _account_id(idx: int) -> int:
    return 1001 + idx


_ACCOUNT_DETAILS_COLUMNS = [
    'source_account_id', 'customer_id', 'account_name', 'industry', 'region',
    'vertical', 'tier', 'arr', 'revenue', 'contract_start', 'contract_end',
    'renewal_date', 'csm_name', 'csm_email', 'account_status', 'uuid',
    'csm_manager', 'executive_sponsor',
    'primary_champion_name', 'primary_champion_title',
    'primary_champion_email', 'primary_champion_engagement_score',
    'products', 'product_count', 'stakeholder_count',
    'employee_count', 'founded_year', 'headquarters', 'website', 'description',
]


def emit_account_details_csv(world: dict, accounts: list, customer_name: str) -> str:
    """Column values are built as a {column_name: value} dict and read back
    through _ACCOUNT_DETAILS_COLUMNS — a positional list here previously
    drifted by one (an extra blank pushed product_count's slot to receive
    the string '[]' meant for 'products', and shifted every int-typed field
    after it into blanks pandas reads as NaN server-side: 'cannot convert
    float NaN to integer' on /api/onboarding/process-data, caught live on
    customer_id=404, 2026-08-27). Int-typed columns get 0, never '', to
    close off that whole failure class rather than just this one instance."""
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(_ACCOUNT_DETAILS_COLUMNS)
    for a in accounts:
        aid = _account_id(a.account_idx)
        row = {
            'source_account_id': aid, 'customer_id': '',
            'account_name': f'{customer_name} Account {aid}',
            'industry': 'Technology', 'region': 'North America',
            'vertical': world['vertical'],
            'tier': 'Enterprise' if a.arr >= 5_000_000 else 'Mid-Market',
            'arr': round(a.arr), 'revenue': round(a.arr),
            'contract_start': '2025-01-01', 'contract_end': '2026-01-01',
            'renewal_date': '2026-01-01',
            'csm_name': 'Eval CSM', 'csm_email': 'eval-csm@example.com',
            'account_status': 'active', 'uuid': '',
            'csm_manager': 'Eval Manager', 'executive_sponsor': '',
            'primary_champion_name': '', 'primary_champion_title': '',
            'primary_champion_email': '', 'primary_champion_engagement_score': '',
            'products': '[]', 'product_count': 0, 'stakeholder_count': 0,
            'employee_count': 0, 'founded_year': 0,
            'headquarters': '', 'website': '',
            'description': f'Eval-profile account, archetype={a.archetype_id}',
        }
        assert set(row.keys()) == set(_ACCOUNT_DETAILS_COLUMNS), (
            set(row.keys()) ^ set(_ACCOUNT_DETAILS_COLUMNS)
        )
        w.writerow([row[col] for col in _ACCOUNT_DETAILS_COLUMNS])
    return out.getvalue()


def emit_qualitative_signals_csv(world: dict, accounts: list) -> str:
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow([
        'signal_id', 'source_account_id', 'signal_date', 'signal_type',
        'content', 'sentiment', 'sentiment_score',
        'stakeholder_name', 'stakeholder_title',
        'arc_id', 'story_phase', 'linked_node_id', 'signal_ref',
    ])
    signal_types = set(world['observed_vocabulary']['signal_types'])
    sig_id = 1
    for a in accounts:
        aid = _account_id(a.account_idx)
        for ev in a.true_events:
            if not ev.observed or ev.event_type not in signal_types:
                continue
            w.writerow([
                sig_id, aid, ev.timestamp.strftime('%Y-%m-%d'), ev.event_type,
                f'Eval-profile signal: {ev.event_type} (archetype={a.archetype_id})',
                'negative', -0.5,
                '', '', '', '', '', f'signal:{sig_id}',
            ])
            sig_id += 1
    return out.getvalue()


def emit_outcomes_csv(world: dict, accounts: list, dollars_by_account: dict) -> str:
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow([
        'source_account_id', 'outcome_date', 'outcome_type', 'title',
        'description', 'revenue_value', 'status', 'linked_signal_id',
    ])
    outcome_polarity = world['observed_vocabulary']['outcome_types']
    for a in accounts:
        aid = _account_id(a.account_idx)
        acct_dollars = dollars_by_account.get(a.account_idx, {})
        for ev in a.true_events:
            if not ev.observed or ev.event_type not in outcome_polarity:
                continue
            value = acct_dollars.get(id(ev), 0.0)
            w.writerow([
                aid, ev.timestamp.strftime('%Y-%m-%d'), ev.event_type,
                f'{ev.event_type.replace("_", " ").title()}',
                f'Eval-profile outcome: {ev.event_type} (archetype={a.archetype_id})',
                round(value, 2), 'realized', '',
            ])
    return out.getvalue()
