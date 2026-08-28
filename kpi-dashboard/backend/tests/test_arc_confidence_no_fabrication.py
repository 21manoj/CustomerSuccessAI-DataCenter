"""
push_intelligence_subscriber.py no longer fabricates arc_confidence=0.5 for a
not-yet-classified account (state-of-play.md item 32, 2026-08-27).

Account.arc_confidence is set only by Wizard A (wizards/wizard_a_journey_db.py).
account_details.csv's loader never sets it, so every account starts NULL until
Wizard A runs. evaluate_playbook_trigger_for_account() previously defaulted a
NULL arc_confidence to 0.5 -- a value indistinguishable from a real 50%
classification -- and fed it into a live auto-trigger decision
(PlaybookTriggerValidator.validate_trigger's trigger_context, and the
rule-based fallback's confidence >= 0.7 / < 0.7 branching). Confirmed via the
pipeline order in _process_data_impl that this fires structurally, not rarely:
calculate_health_scores() -> publish_health_events() happens ~280 lines before
run_wizard_a() sets the real value.

Fix: NULL arc_confidence (with a resolved arc_type) now defers the evaluation
(returns None) instead of fabricating a value. Same treatment for the
ContextNode arc_detection fallback path when its own properties lack a
confidence key.

Run against a dedicated postgres test DB:
    DATABASE_URL="postgresql://manojgupta@localhost:5432/cs_pulse_test" \\
        python3 -m pytest tests/test_arc_confidence_no_fabrication.py -v
"""
import os
import sys
import uuid
from datetime import datetime, timedelta

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_v3_minimal import app, db
from models import Account, ContextNode, Customer
from push_intelligence_subscriber import evaluate_playbook_trigger_for_account


def _assert_isolated_test_db(uri: str) -> None:
    """See tests/test_context_graph_invariants.py — same guard, same reason."""
    if os.environ.get('ALLOW_DESTRUCTIVE_TEST_DB') == '1':
        return
    db_name = uri.rsplit('/', 1)[-1].split('?', 1)[0]
    if 'test' not in db_name.lower():
        raise RuntimeError(
            f"test_arc_confidence_no_fabrication.py refuses to run "
            f"db.drop_all() against database {db_name!r} — its name "
            f"doesn't contain 'test'."
        )


@pytest.fixture(scope='module')
def ctx():
    app.config['TESTING'] = True
    db_uri = os.environ.get(
        'DATABASE_URL', 'postgresql://manojgupta@localhost:5432/cs_pulse_test'
    )
    _assert_isolated_test_db(db_uri)
    app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
    with app.app_context():
        db.create_all()
        unique_email = f'arc_conf_{uuid.uuid4().hex[:8]}@test.com'
        customer = Customer(customer_name='Arc Confidence Test Co', email=unique_email)
        db.session.add(customer)
        db.session.commit()
        yield {'customer_id': customer.customer_id}
        db.session.remove()
        db.drop_all()


def _make_account(ctx, *, arc_type=None, arc_confidence=None, name):
    account = Account(
        customer_id=ctx['customer_id'],
        account_name=name,
        revenue=1_000_000,
        external_account_id=f'ARC-{uuid.uuid4().hex[:8]}',
        account_status='at_risk',
        arc_type=arc_type,
        arc_confidence=arc_confidence,
    )
    db.session.add(account)
    db.session.commit()
    return account


class TestNoFabricationOnAccountArcConfidence:
    def test_arc_type_set_confidence_null_defers_not_fabricates(self, ctx):
        """Account.arc_type resolved (Wizard A partially ran / set type but not
        confidence — defensive case) but arc_confidence is NULL: must defer
        (return None), never substitute 0.5."""
        with app.app_context():
            account = _make_account(
                ctx, arc_type='crisis_recovery', arc_confidence=None,
                name='Type-set-confidence-null Co',
            )
            result = evaluate_playbook_trigger_for_account(
                ctx['customer_id'], account.account_id, health_score=35.0,
            )
            assert result is None, (
                "expected deferral (None) for NULL arc_confidence, not a "
                "fabricated-0.5-driven decision"
            )

    def test_arc_type_and_confidence_null_defers_via_existing_path(self, ctx):
        """Both NULL (the pre-Wizard-A default state) and no fallback
        ContextNode exists: must defer via the existing 'no arc signal at
        all' path — confirms the fix didn't disturb this case."""
        with app.app_context():
            account = _make_account(
                ctx, arc_type=None, arc_confidence=None,
                name='Fully-unclassified Co',
            )
            result = evaluate_playbook_trigger_for_account(
                ctx['customer_id'], account.account_id, health_score=35.0,
            )
            assert result is None

    def test_fallback_contextnode_without_confidence_key_defers(self, ctx):
        """Account.arc_type is NULL, but a fallback arc_detection ContextNode
        exists whose properties lack a 'confidence' key entirely — must defer,
        not fabricate 0.5 from the node's properties either."""
        with app.app_context():
            account = _make_account(
                ctx, arc_type=None, arc_confidence=None,
                name='Node-fallback-no-confidence Co',
            )
            db.session.add(ContextNode(
                customer_id=ctx['customer_id'], account_id=account.account_id,
                node_type='SIGNAL', node_subtype='arc_detection',
                title='Arc detected', source='observed', source_platform='wizard_a',
                occurred_at=datetime.utcnow(), tier=1,
                properties={'arc_type': 'exec_sponsor_change'},  # no 'confidence' key
            ))
            db.session.commit()

            result = evaluate_playbook_trigger_for_account(
                ctx['customer_id'], account.account_id, health_score=35.0,
            )
            assert result is None

    def test_real_confidence_proceeds_to_a_real_decision(self, ctx):
        """A genuinely classified account (Wizard A has run, real
        arc_confidence set) must still proceed normally — this fix must not
        make every evaluation defer."""
        with app.app_context():
            account = _make_account(
                ctx, arc_type='crisis_recovery', arc_confidence=0.85,
                name='Genuinely-classified Co',
            )
            result = evaluate_playbook_trigger_for_account(
                ctx['customer_id'], account.account_id, health_score=35.0,
            )
            assert result is not None, (
                "a real arc_confidence must still produce a decision, "
                "not defer"
            )
            assert result.get('decision') in (
                'auto_approved', 'pending_manual_approval', 'auto_rejected',
                'skipped_dedup',
            )


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
