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
import random
import zlib


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


def emit_kpi_measurements_csv(accounts: list) -> str:
    """Eval profile's focus is the qualitative-signal/outcome causal
    structure, not KPI trend shape — one flat baseline point per account so
    the file exists and passes ingest, honestly minimal rather than pretending
    depth this generator doesn't model. Track D's own KPI-trajectory
    determinism was already fixed separately (commit 951d9f380); this does
    not duplicate that generator."""
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow([
        'source_account_id', 'kpi_code', 'kpi_name', 'pillar',
        'measured_at', 'value', 'target', 'weight', 'unit', 'status',
    ])
    for a in accounts:
        aid = _account_id(a.account_idx)
        w.writerow([aid, 'EVAL-KPI1', 'Eval Profile Placeholder', 'P1',
                    '2026-01-01', 70, 85, 1.0, '%', 'at_risk'])
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
