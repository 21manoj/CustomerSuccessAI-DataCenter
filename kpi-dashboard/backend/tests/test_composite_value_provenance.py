"""
Composite-site value-provenance wiring — Track A (state-of-play.md).

The two composite sites named by the plan (`_build_layered_story`,
`nrr_waterfall.roi_x`) blend sub-values of different provenance tiers into
one displayed number. Per the display-treatment convention, the honest
label for a blend is most_conservative() of its inputs — a ROI is only as
grounded as the weaker of its numerator and denominator.

Expected tiers, from what actually feeds each number:
  Layer 1 (Already Delivered): PlaybookExecutionV2 rows both sides
      -> measured
  Layer 2 (Still Protectable): value = real health/ARR through
      health_to_annual_churn_prob (derived); cost = fixed 4560/account
      cost-bridge constant (benchmark) -> benchmark
  Layer 3 (Growth Po1): deck benchmarks both sides -> benchmark
  Blended totals: weakest of all six inputs -> benchmark
  nrr_waterfall.roi_x: derived / benchmark -> benchmark

No Flask/DB needed — _build_layered_story is a pure function.
"""
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from executive_dashboard_api import _build_layered_story  # noqa: E402
from utils import value_provenance as vp  # noqa: E402


def _story(**overrides):
    kwargs = dict(
        proof_data={'revenue_protected': 100_000, 'revenue_expanded': 50_000, 'total_cost': 30_000},
        total_arr=10_000_000,
        wf_protectable=200_000,
        wf_expandable=80_000,
        wf_cost=45_600,
        power_of_1_metrics=[
            {'metric_id': 'NRR', 'dollar_impact': 105_000},
            {'metric_id': 'GRR', 'dollar_impact': 100_000},
        ],
    )
    kwargs.update(overrides)
    return _build_layered_story(**kwargs)


def test_per_layer_tiers():
    story = _story()
    by_name = {l['name']: l for l in story['layers']}
    assert by_name['Already Delivered']['data_source'] == vp.MEASURED
    assert by_name['Still Protectable']['data_source'] == vp.BENCHMARK, (
        "layer 2's cost is the fixed cost-bridge constant — its ROI must "
        "not be labeled 'derived' just because the numerator is"
    )
    assert by_name['Growth (Po1 1%)']['data_source'] == vp.BENCHMARK


def test_blended_totals_carry_weakest_input_tier():
    story = _story()
    assert story['data_source'] == vp.BENCHMARK
    # and it's a valid tier, not an arbitrary string
    assert vp.is_valid(story['data_source'])


def test_every_layer_declares_a_valid_tier():
    story = _story()
    for layer in story['layers']:
        assert vp.is_valid(layer.get('data_source')), (
            f"layer {layer['name']!r} missing or invalid data_source"
        )


def test_most_conservative_derived_benchmark_is_benchmark():
    """Pins the exact blend nrr_waterfall.roi_x declares inline."""
    assert vp.most_conservative([vp.DERIVED, vp.BENCHMARK]) == vp.BENCHMARK


def test_po1_benchmark_fallback_metrics_carry_explicit_benchmark_tier():
    """_get_po1_benchmark_metrics builds cards purely from ARR-scaled deck
    constants — every entry must say so explicitly, not just via the legacy
    `estimated` boolean."""
    from executive_dashboard_api import _get_po1_benchmark_metrics

    metrics = _get_po1_benchmark_metrics(10_000_000)
    assert metrics, "expected benchmark metrics for a nonzero ARR"
    for m in metrics:
        assert m['data_source'] == vp.BENCHMARK, m['metric_id']
        assert m['estimated'] is True  # legacy flag kept for back-compat


def test_snapshot_format_b_blend_is_default_tier():
    """Format B (snapshot forward_metrics) synthesizes baseline/current from
    the default_baselines constants while dollar_impact is snapshot-derived —
    the per-card blend must carry the weaker tier."""
    assert vp.most_conservative([vp.DERIVED, vp.DEFAULT]) == vp.DEFAULT


def test_nrr_waterfall_response_block_declares_the_blend():
    """Source-level guard: the nrr_waterfall dict in the CFO response must
    carry a data_source computed via most_conservative, not a bare literal
    that can silently drift from the components it describes."""
    import inspect
    import executive_dashboard_api as api

    src = inspect.getsource(api)
    wf_start = src.index("'nrr_waterfall': {")
    wf_block = src[wf_start:wf_start + 900]
    assert "'data_source': _vp.most_conservative(" in wf_block, (
        "nrr_waterfall must declare its provenance via most_conservative() "
        "over its components' tiers"
    )


# ═════════════════════════════════════════════════════════════════════
# Item 25 — Po1 re-tiering: _get_po1_benchmark_metrics per-metric tiers
# ═════════════════════════════════════════════════════════════════════
# Everything below needs a real DB (Customer/Account/ContextNode rows) to
# exercise the promotion path, unlike the pure-function tests above.


def _po1_db_setup():
    """Import Flask app/db/models and refuse to run against anything that
    doesn't look like a local test database. Same DB-name guard as
    tests/test_context_graph_invariants.py, minus the drop_all risk since
    this module never calls it — cleanup is scoped to the rows it creates.
    """
    import os
    from app_v3_minimal import app, db
    from models import Account, ContextNode, Customer, CustomerConfig

    db_uri = os.environ.get(
        'DATABASE_URL', 'postgresql://manojgupta@localhost:5432/cs_pulse_test'
    )
    db_name = db_uri.rsplit('/', 1)[-1].split('?', 1)[0]
    if 'test' not in db_name.lower():
        pytest.skip(
            f"skipping DB-backed item-25 test: {db_name!r} doesn't look "
            f"like a test database (must contain 'test' — see "
            f"feedback_destructive_test_fixture.md)"
        )
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
    return app, db, Account, ContextNode, Customer, CustomerConfig


def _make_po1_customer(db, Customer, Account, CustomerConfig, *, name, data_origin=None):
    """Create a customer + one account + a dc2_s CustomerConfig row."""
    import uuid

    customer = Customer(
        customer_name=name,
        email=f'item25_{uuid.uuid4().hex[:10]}@test.com',
        data_origin=data_origin,
    )
    db.session.add(customer)
    db.session.commit()

    db.session.add(CustomerConfig(customer_id=customer.customer_id, vertical='dc2_s'))
    account = Account(
        customer_id=customer.customer_id,
        account_name=f'{name} Account',
        revenue=5_000_000,
        external_account_id=f'ITEM25-{uuid.uuid4().hex[:8]}',
        account_status='active',
    )
    db.session.add(account)
    db.session.commit()
    return customer, account


def _cleanup_po1_customer(db, Customer, Account, CustomerConfig, ContextNode, customer_id):
    ContextNode.query.filter_by(customer_id=customer_id).delete()
    Account.query.filter_by(customer_id=customer_id).delete()
    CustomerConfig.query.filter_by(customer_id=customer_id).delete()
    Customer.query.filter_by(customer_id=customer_id).delete()
    db.session.commit()


def test_po1_benchmark_fallback_synthetic_customer_stays_all_benchmark():
    """Customer.data_origin='synthetic_eval_profile' must cap every
    fallback metric at BENCHMARK even when the graph carries an
    OBSERVED-tier node tagged with a pillar that maps to a Po1 metric —
    the data_origin gate is unconditional and customer-level, overriding
    whatever the pillar-evidence check would otherwise find."""
    from datetime import datetime

    from executive_dashboard_api import _get_po1_benchmark_metrics

    app, db, Account, ContextNode, Customer, CustomerConfig = _po1_db_setup()
    with app.app_context():
        db.create_all()
        customer, account = _make_po1_customer(
            db, Customer, Account, CustomerConfig,
            name='Item25 Synthetic Test Co', data_origin='synthetic_eval_profile',
        )
        try:
            db.session.add(ContextNode(
                customer_id=customer.customer_id, account_id=account.account_id,
                node_type='SIGNAL', node_subtype='ticket',
                title='Real-looking ticket signal',
                source='observed', source_platform='csv_import',
                occurred_at=datetime(2026, 1, 1), tier=2,
                properties={'pillar_code': 'P2'},  # dc2_s P2 -> ticket_resolution_time
            ))
            db.session.commit()

            metrics = _get_po1_benchmark_metrics(5_000_000, customer.customer_id)
            assert metrics, "expected benchmark metrics for a nonzero ARR"
            for m in metrics:
                assert m['data_source'] == vp.BENCHMARK, (
                    f"{m['metric_id']} promoted above BENCHMARK for a "
                    f"synthetic customer"
                )
                assert m['estimated'] is True
        finally:
            _cleanup_po1_customer(
                db, Customer, Account, CustomerConfig, ContextNode, customer.customer_id,
            )


def test_po1_benchmark_fallback_promotes_metric_with_observed_pillar_evidence():
    """A real (non-synthetic) customer whose context graph has an
    OBSERVED-tier node tagged pillar_code='P2' gets ticket_resolution_time
    (dc2_s's P2 -> metric mapping, via outcome_roi_api.POWER_OF_1_PILLAR_MAPS)
    promoted to DERIVED, while every other fallback metric stays BENCHMARK —
    the promotion is per-metric, not all-or-nothing."""
    from datetime import datetime

    from executive_dashboard_api import _get_po1_benchmark_metrics

    app, db, Account, ContextNode, Customer, CustomerConfig = _po1_db_setup()
    with app.app_context():
        db.create_all()
        customer, account = _make_po1_customer(
            db, Customer, Account, CustomerConfig,
            name='Item25 Real Evidence Test Co',
        )
        try:
            db.session.add(ContextNode(
                customer_id=customer.customer_id, account_id=account.account_id,
                node_type='SIGNAL', node_subtype='ticket',
                title='Real ticket signal feeding P2',
                source='observed', source_platform='csv_import',
                occurred_at=datetime(2026, 1, 1), tier=2,
                properties={'pillar_code': 'P2'},
            ))
            db.session.commit()

            metrics = _get_po1_benchmark_metrics(5_000_000, customer.customer_id)
            by_id = {m['metric_id']: m for m in metrics}
            assert 'ticket_resolution_time' in by_id
            assert by_id['ticket_resolution_time']['data_source'] == vp.DERIVED
            assert by_id['ticket_resolution_time']['estimated'] is False

            other_metrics = {mid: m for mid, m in by_id.items() if mid != 'ticket_resolution_time'}
            assert other_metrics, "expected other Po1 metrics besides ticket_resolution_time"
            for mid, m in other_metrics.items():
                assert m['data_source'] == vp.BENCHMARK, (
                    f"{mid} unexpectedly promoted — only the pillar with "
                    f"observed evidence should be promoted"
                )
                assert m['estimated'] is True
        finally:
            _cleanup_po1_customer(
                db, Customer, Account, CustomerConfig, ContextNode, customer.customer_id,
            )


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
